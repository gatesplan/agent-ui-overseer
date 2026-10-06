import argparse
import asyncio
import json
from pathlib import Path

from aiohttp import WSMsgType, web
from loguru import logger

from project_manager.l0.decision_store import DecisionStore
from project_manager.l0.project_finder import ProjectFinder
from project_manager.l3.tab_manager import TabManager

ROOT = Path(__file__).resolve().parents[4]
POLL_INTERVAL = 0.4


# 패널 서버. 화면 파일(web/), API, 상태 알림과 터미널 WebSocket 을 한 포트에서 맡는다
class OverseerServer:
    def __init__(self, data_dir: Path, claude_args: str = ''):
        self.store = DecisionStore(data_dir / 'overseer.db')
        self.tabs = TabManager(self.store, data_dir / 'captures', claude_args)
        self.finder = ProjectFinder()
        self.clients: set[web.WebSocketResponse] = set()
        self.app = web.Application(middlewares=[self._no_cache])
        self.app.add_routes([
            web.get('/', self._index),
            web.get('/api/projects', self._projects),
            web.get('/api/tabs', self._list),
            web.post('/api/tabs', self._open),
            web.post('/api/tabs/{id}/resume', self._resume),
            web.delete('/api/tabs/{id}', self._close),
            web.post('/api/tabs/{id}/send', self._send),
            web.put('/api/tabs/{id}/draft', self._draft),
            web.get('/ws/events', self._events),
            web.get('/ws/term/{id}', self._term),
        ])
        self.app.router.add_static('/', ROOT / 'web')
        self.app.on_startup.append(self._startup)
        self.app.on_cleanup.append(self._cleanup)

    @staticmethod
    def cli() -> None:
        parser = argparse.ArgumentParser(prog='overseer', description='Overseer 패널 서버')
        parser.add_argument('--host', default='127.0.0.1')
        parser.add_argument('--port', type=int, default=47310)
        parser.add_argument('--claude-args', default='', help='새 탭의 claude 실행 인자. 예: "--dangerously-skip-permissions"')
        parser.add_argument('--data', type=Path, default=ROOT / 'data')
        args = parser.parse_args()
        logger.add(args.data / 'logs' / 'overseer.log', rotation='1 MB', encoding='utf-8')
        server = OverseerServer(args.data, args.claude_args)
        print(f'Overseer: http://{args.host}:{args.port}/', flush=True)
        web.run_app(server.app, host=args.host, port=args.port, print=None)

    async def _startup(self, app: web.Application) -> None:
        self.tabs.restore()
        app['poller'] = asyncio.create_task(self._poll_loop())

    async def _cleanup(self, app: web.Application) -> None:
        app['poller'].cancel()
        self.tabs.shutdown()

    # 훅 기록과 프로세스 종료를 살펴 바뀐 탭 상태를 알린다
    async def _poll_loop(self) -> None:
        while True:
            await asyncio.sleep(POLL_INTERVAL)
            try:
                for tab in self.tabs.poll():
                    await self._broadcast({'type': 'tab', 'tab': tab.state()})
            except Exception:
                logger.exception("poll 실패")

    async def _broadcast(self, message: dict) -> None:
        data = json.dumps(message, ensure_ascii=False)
        for ws in list(self.clients):
            try:
                await ws.send_str(data)
            except ConnectionError:
                self.clients.discard(ws)

    @web.middleware
    async def _no_cache(self, request: web.Request, handler):
        response = await handler(request)
        # 화면 파일을 고친 뒤 새로고침만으로 반영되게 한다
        if not isinstance(response, web.WebSocketResponse):
            response.headers['Cache-Control'] = 'no-store'
        return response

    async def _index(self, request: web.Request) -> web.FileResponse:
        return web.FileResponse(ROOT / 'web' / 'index.html')

    async def _list(self, request: web.Request) -> web.Response:
        return web.json_response([tab.state() for tab in self.tabs.tabs.values()])

    # 새 세션 창의 폴더 목록: 드라이브마다 루트 Projects 폴더 안의 프로젝트
    async def _projects(self, request: web.Request) -> web.Response:
        return web.json_response({'roots': self.finder.scan(), 'default_root': str(self.finder.default_root())})

    # 새 탭: {cwd} 로 기존 폴더를 열거나, {create: {root, name}} 으로 Projects 안에 폴더를 만들어 연다
    async def _open(self, request: web.Request) -> web.Response:
        body = await request.json()
        try:
            cwd = body.get('cwd', '')
            if body.get('create'):
                cwd = str(self.finder.create(body['create'].get('root', ''), body['create'].get('name', '')))
            tab = self.tabs.open(cwd, body.get('rows', 40), body.get('cols', 120), bool(body.get('skip_permissions')))
        except ValueError as e:
            return web.json_response({'error': str(e)}, status=400)
        await self._broadcast({'type': 'tab', 'tab': tab.state()})
        return web.json_response(tab.state())

    async def _resume(self, request: web.Request) -> web.Response:
        body = await request.json() if request.can_read_body else {}
        tab = self.tabs.resume(request.match_info['id'], body.get('rows', 40), body.get('cols', 120))
        await self._broadcast({'type': 'tab', 'tab': tab.state()})
        return web.json_response(tab.state())

    async def _close(self, request: web.Request) -> web.Response:
        tab_id = request.match_info['id']
        self.tabs.close(tab_id)
        await self._broadcast({'type': 'closed', 'id': tab_id})
        return web.json_response({'ok': True})

    # 전송: message 는 화면이 조립한 전송 시안, decisions 는 [{id, action, note}]
    async def _send(self, request: web.Request) -> web.Response:
        tab = self.tabs.get(request.match_info['id'])
        body = await request.json()
        decisions = [(d['id'], d['action'], d.get('note', '')) for d in body.get('decisions', [])]
        try:
            await tab.send(body['message'], decisions)
        except RuntimeError as e:
            return web.json_response({'error': str(e)}, status=409)
        await self._broadcast({'type': 'tab', 'tab': tab.state()})
        return web.json_response(tab.state())

    async def _draft(self, request: web.Request) -> web.Response:
        self.store.save_draft(request.match_info['id'], await request.json())
        return web.json_response({'ok': True})

    async def _events(self, request: web.Request) -> web.WebSocketResponse:
        ws = web.WebSocketResponse(heartbeat=20)
        await ws.prepare(request)
        self.clients.add(ws)
        try:
            async for _ in ws:
                pass
        finally:
            self.clients.discard(ws)
        return ws

    # 터미널: 붙으면 남은 출력을 먼저 보내고 이어서 실시간 출력을 흘린다. 받은 글자는 그대로 PTY 에 쓴다
    async def _term(self, request: web.Request) -> web.WebSocketResponse:
        tab = self.tabs.get(request.match_info['id'])
        ws = web.WebSocketResponse(heartbeat=20)
        await ws.prepare(request)
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[str] = asyncio.Queue()

        def listener(data: str) -> None:
            loop.call_soon_threadsafe(queue.put_nowait, data)

        async def pump() -> None:
            while True:
                await ws.send_str(await queue.get())

        if tab.pty:
            await ws.send_str(tab.pty.history())
        tab.listeners.append(listener)
        sender = asyncio.create_task(pump())
        try:
            async for msg in ws:
                if msg.type != WSMsgType.TEXT or not tab.pty:
                    continue
                data = json.loads(msg.data)
                if data.get('type') == 'input':
                    tab.pty.write(data['data'])
                elif data.get('type') == 'resize':
                    tab.pty.resize(int(data['rows']), int(data['cols']))
        finally:
            sender.cancel()
            tab.listeners.remove(listener)
        return ws
