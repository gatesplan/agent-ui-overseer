import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from aiohttp import WSMsgType, web
from loguru import logger

from project_manager.l0.decision_store import DecisionStore
from project_manager.l0.project_finder import ProjectFinder
from project_manager.l0.record_store import RecordStore
from project_manager.l3.tab_manager import TabManager

ROOT = Path(__file__).resolve().parents[4]
POLL_INTERVAL = 0.4


# 패널 서버. 화면 파일(web/), API, 상태 알림과 터미널 WebSocket 을 한 포트에서 맡는다
class OverseerServer:
    # project_roots: 새 세션 창에 보일 프로젝트 루트들. 없으면 드라이브마다 루트의 Projects 폴더
    def __init__(self, data_dir: Path, claude_args: str = '', project_roots: list[str] | None = None):
        self.store = DecisionStore(data_dir / 'overseer.db')
        self.records = RecordStore(data_dir / 'overseer.db')
        # 결정 아카이브 조회 MCP 서버. 이 서버와 같은 파이썬으로 띄운다
        mcp = {'command': sys.executable, 'args': [str(ROOT / 'scripts' / 'overseer_mcp.py')]}
        self.tabs = TabManager(self.store, data_dir / 'captures', claude_args, self.records, mcp)
        self.finder = ProjectFinder(roots=project_roots)
        self.clients: set[web.WebSocketResponse] = set()
        self.app = web.Application(middlewares=[self._no_cache])
        self.app.add_routes([
            web.get('/', self._index),
            web.get('/api/health', self._health),
            web.get('/api/projects', self._projects),
            web.post('/api/tabs/{id}/permission', self._permission),
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
        parser.add_argument('--projects', action='append', metavar='DIR',
                            help='새 세션 창에 보일 프로젝트 루트. 여러 번 줄 수 있다. 환경변수 OVERSEER_PROJECTS(; 로 구분)로도 된다. '
                                 '없으면 드라이브마다 루트의 Projects 폴더')
        args = parser.parse_args()
        env_roots = [p for p in os.environ.get('OVERSEER_PROJECTS', '').split(os.pathsep) if p.strip()]
        roots = args.projects or env_roots or None
        logger.add(args.data / 'logs' / 'overseer.log', rotation='1 MB', encoding='utf-8')
        # 자식 claude 의 훅이 권한 결정을 물을 곳(이 서버)과 기록 폴더. child_env 가 환경을 그대로 넘긴다
        os.environ['OVERSEER_PORT'] = str(args.port)
        os.environ['OVERSEER_DATA'] = str(args.data.resolve())
        server = OverseerServer(args.data, args.claude_args, roots)
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

    # 훅이 권한 결정을 맡겨도 되는지 묻는다. permissions 가 없는 예전 서버면 훅은 기다리지 않는다
    async def _health(self, request: web.Request) -> web.Response:
        return web.json_response({'ok': True, 'permissions': True})

    # 화면의 권한 결정: {request_id, behavior: allow | deny | terminal, message}
    async def _permission(self, request: web.Request) -> web.Response:
        tab = self.tabs.get(request.match_info['id'])
        body = await request.json()
        try:
            tab.decide_permission(body.get('request_id', ''), body.get('behavior', ''), body.get('message', ''))
        except ValueError as e:
            return web.json_response({'error': str(e)}, status=400)
        return web.json_response({'ok': True})

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
                    # 터미널에서 응답했으면 떠 있던 확인 알림을 내린다
                    if tab.acknowledge():
                        await self._broadcast({'type': 'tab', 'tab': tab.state()})
                elif data.get('type') == 'resize':
                    tab.pty.resize(int(data['rows']), int(data['cols']))
        finally:
            sender.cancel()
            tab.listeners.remove(listener)
        return ws
