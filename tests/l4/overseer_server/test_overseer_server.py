import asyncio
import json
import os
from pathlib import Path

import pytest
from aiohttp import web
from aiohttp.test_utils import make_mocked_request

from project_manager.l4.overseer_server import OverseerServer

ROW = {'kind': 'weekly_all', 'label': '주간 전체', 'percent': 76.0, 'resets_at': None, 'severity': 'warning'}


# 정해 둔 결과를 차례로 내는 가짜 사용량 조회. 부른 횟수를 센다
class FakePlan:
    def __init__(self, *results):
        self.results = list(results)
        self.calls = 0

    def fetch(self):
        self.calls += 1
        return self.results.pop(0)


class FakeTab:
    def __init__(self, tab_id, answers):
        self.id = tab_id
        self.answers = answers


def server_with(tmp_path, plan):
    server = OverseerServer(tmp_path)
    server.plan = plan
    sent = []

    async def broadcast(message):
        sent.append(message)

    async def announce(tab):
        pass

    server._broadcast = broadcast
    server._announce = announce
    return server, sent


# 받기 전에 온 요청은 그 받기로 채운다. 받는 중에 온 요청은 끝난 뒤 한 번만 더 받는다
# 실패하면 지난 막대를 남기고 실패만 표시한다
def test_usage_requests_coalesce_and_failure_keeps_last_rows(tmp_path):
    plan = FakePlan({'status': 'ok', 'limits': [ROW], 'at': 't1', 'message': ''},
                    {'status': 'error', 'limits': [], 'at': 't2', 'message': '시간 초과'})
    server, sent = server_with(tmp_path, plan)

    async def scenario():
        server._check_usage()
        server._check_usage()
        # 받기 작업이 CLI 를 띄우고 기다리는 중
        await asyncio.sleep(0)
        server._check_usage()
        server._check_usage()
        await server._usage_task

    asyncio.run(scenario())
    assert plan.calls == 2
    assert [m['type'] for m in sent] == ['usage', 'usage']
    assert server.usage['claude'] == {'status': 'error', 'limits': [ROW], 'at': 't1', 'message': '시간 초과'}


# 응답 수가 는 탭이 있을 때만 다시 받는다. 입력만 붙은 알림이나 처음 보는 빈 탭에는 받지 않는다
def test_usage_is_fetched_after_an_answer_ends(tmp_path):
    plan = FakePlan(*[{'status': 'ok', 'limits': [ROW], 'at': 't', 'message': ''}] * 3)
    server, sent = server_with(tmp_path, plan)
    server._answers = {'a': 2}
    changed = []
    server.tabs.poll = lambda: changed

    async def tick(*tabs):
        changed[:] = tabs
        await server._poll_once()
        if server._usage_task:
            await server._usage_task

    asyncio.run(tick(FakeTab('a', 2), FakeTab('new', 0)))
    assert plan.calls == 0
    asyncio.run(tick(FakeTab('a', 3)))
    assert plan.calls == 1
    asyncio.run(tick(FakeTab('a', 3)))
    assert plan.calls == 1


class SpecTab:
    def __init__(self, cwd):
        self.id = 't1'
        self.cwd = str(cwd)


def spec_server(tmp_path):
    project = tmp_path / 'shop'
    project.mkdir()
    server = OverseerServer(tmp_path / 'data')
    tab = SpecTab(project)
    server._tab = lambda request: tab
    return server, project


async def resolve(server, path):
    request = make_mocked_request('GET', path, app=server.app)
    match = await server.app.router.resolve(request)
    request._match_info = match
    return match, request


# 스펙 패널은 탭 프로젝트의 spec.json 을 받는다. 그 뒤 파일이 바뀌거나 지워지면 바뀐 것만 알림으로 간다
def test_spec_route_and_changes_after_first_read(tmp_path):
    server, project = spec_server(tmp_path)
    (project / 'spec.json').write_text(json.dumps({'title': '가게'}, ensure_ascii=False), encoding='utf-8')

    async def scenario():
        match, request = await resolve(server, '/api/tabs/t1/spec')
        body = json.loads((await match.handler(request)).text)
        assert body == {'cwd': str(project), 'spec': {'status': 'ok', 'spec': {'title': '가게'}}}
        assert server._spec_changes([str(project)]) == []
        (project / 'spec.json').write_text(json.dumps({'title': '가게 2호점'}, ensure_ascii=False), encoding='utf-8')
        os.utime(project / 'spec.json', ns=(1, 1))
        assert server._spec_changes([str(project)]) == [(str(project), {'status': 'ok', 'spec': {'title': '가게 2호점'}})]
        assert server._spec_changes([str(project)]) == []
        (project / 'spec.json').unlink()
        assert server._spec_changes([str(project)]) == [(str(project), {'status': 'none'})]
        # 탭이 닫힌 프로젝트는 그만 본다
        assert server._spec_changes([]) == []
        assert server.specs == {}

    asyncio.run(scenario())


# 스펙 패널에서 사용자가 고치거나 더한 것은 spec.json 에 쓰고 바뀐 스펙을 돌려준다. 안 되면 까닭을 409 로 알린다
def test_spec_write_route_edits_and_adds(tmp_path):
    server, project = spec_server(tmp_path)
    (project / 'spec.json').write_text(json.dumps({'title': '가게', 'components': [{'name': '장바구니'}]}, ensure_ascii=False), encoding='utf-8')

    async def post(body):
        request = make_mocked_request('POST', '/api/tabs/t1/spec', app=server.app)
        match = await server.app.router.resolve(request)
        request._match_info = match

        async def read_json():
            return body
        request.json = read_json
        response = await match.handler(request)
        return response.status, json.loads(response.text)

    async def scenario():
        status, body = await post({'op': 'add', 'path': ['components', 0], 'expect': '장바구니', 'kind': 'do', 'text': '상품을 담는다'})
        assert status == 200
        assert body['path'] == ['components', 0, 'does', 0]
        assert body['spec'] == {'status': 'ok', 'spec': {'title': '가게', 'components': [{'name': '장바구니', 'does': ['상품을 담는다']}]}}
        status, body = await post({'op': 'edit', 'changes': [{'path': ['components', 0, 'name'], 'old': '장바구니', 'new': '카트'}]})
        assert status == 200 and body['spec']['spec']['components'][0]['name'] == '카트'
        assert json.loads((project / 'spec.json').read_text(encoding='utf-8'))['components'][0]['name'] == '카트'
        status, body = await post({'op': 'edit', 'changes': [{'path': ['components', 0, 'name'], 'old': '장바구니', 'new': '바구니'}]})
        assert status == 409 and '바뀌었다' in body['error']
        status, body = await post({'op': 'remove', 'path': ['components', 0, 'does', 0], 'expect': '상품을 담는다'})
        assert status == 200 and body['spec']['spec'] == {'title': '가게', 'components': [{'name': '카트'}]}
        # 실행취소로 지운 개체를 되살릴 때는 순번(at)에 끼운다
        await post({'op': 'add', 'path': ['components', 0], 'expect': '카트', 'kind': 'do', 'text': '수량을 합친다'})
        status, body = await post({'op': 'add', 'path': ['components', 0], 'expect': '카트', 'kind': 'do', 'text': '상품을 담는다', 'at': 0})
        assert status == 200 and body['path'] == ['components', 0, 'does', 0]
        assert body['spec']['spec']['components'][0]['does'] == ['상품을 담는다', '수량을 합친다']
        # 끌어서 다른 개체 아래로 옮긴다. 기능을 기능 위에 놓으면 이어서 기능이 된다
        status, body = await post({'op': 'move', 'path': ['components', 0, 'does', 1], 'expect': '수량을 합친다',
                                   'to': ['components', 0, 'does', 0], 'toExpect': '상품을 담는다'})
        assert status == 200 and body['path'] == ['components', 0, 'does', 0, 'then', 0]
        assert body['spec']['spec']['components'][0]['does'] == [{'text': '상품을 담는다', 'then': ['수량을 합친다']}]
        status, body = await post({'op': 'move', 'path': ['components', 0], 'expect': '카트', 'to': ['components', 0, 'does', 0], 'toExpect': '상품을 담는다'})
        assert status == 409
        status, body = await post({'op': 'rename'})
        assert status == 400

    asyncio.run(scenario())


# 목업 라벨의 프로젝트 안 파일은 경로째 내준다. 상대 경로로 읽는 css 도 같은 자리에서 풀린다
def test_file_route_serves_project_files_only(tmp_path):
    server, project = spec_server(tmp_path)
    (project / 'web').mkdir()
    (project / 'web' / 'mock.html').write_text('<link rel="stylesheet" href="style.css">', encoding='utf-8')
    (project / '.env').write_text('KEY=1', encoding='utf-8')

    async def scenario():
        match, request = await resolve(server, '/api/tabs/t1/files/web/mock.html')
        response = await match.handler(request)
        assert Path(response._path) == (project / 'web' / 'mock.html').resolve()
        match, request = await resolve(server, '/api/tabs/t1/files/.env')
        with pytest.raises(web.HTTPNotFound):
            await match.handler(request)

    asyncio.run(scenario())


MODEL = {'value': 'fable', 'resolvedModel': 'claude-fable-5-2', 'displayName': 'Fable 5.2', 'description': ''}


# 모델 목록은 받는 대로 알린다. 받지 못하면 지난 목록을 남기고 실패만 표시한다
def test_models_fetch_announces_and_failure_keeps_last_list(tmp_path):
    server, sent = server_with(tmp_path, FakePlan())
    server.catalog = FakePlan({'status': 'ok', 'models': [MODEL], 'at': 't1', 'message': ''},
                              {'status': 'error', 'models': [], 'at': 't2', 'message': '시간 초과'})

    async def scenario():
        server._check_models()
        # 받는 중에 온 요청은 더 띄우지 않는다
        server._check_models()
        await server._models_task
        server._check_models()
        await server._models_task

    asyncio.run(scenario())
    assert server.catalog.calls == 2
    assert [m['type'] for m in sent] == ['models', 'models']
    assert server.models['claude'] == {'status': 'error', 'models': [MODEL], 'at': 't1', 'message': '시간 초과'}


class ModelTab:
    id = 't1'

    def __init__(self, error=None):
        self.error = error
        self.values = []

    async def set_model(self, value):
        if self.error:
            raise self.error
        self.values.append(value)


# 모델 교체는 CLI 가 알려 준 목록의 값만 탭에 넘긴다. 탭이 작업 중이면 409
def test_model_route_passes_only_listed_values(tmp_path):
    server, sent = server_with(tmp_path, FakePlan())
    server.models['claude'] = {'status': 'ok', 'models': [MODEL]}
    tab = ModelTab()
    server._tab = lambda request: tab

    async def post(value):
        request = make_mocked_request('POST', '/api/tabs/t1/model', app=server.app)
        match = await server.app.router.resolve(request)
        request._match_info = match

        async def read_json():
            return {'value': value}
        request.json = read_json
        response = await match.handler(request)
        return response.status, json.loads(response.text)

    async def scenario():
        assert (await post('fable'))[0] == 200
        status, body = await post('opus')
        assert status == 400 and '목록에 없는' in body['error']
        tab.error = RuntimeError('에이전트가 작업 중이다')
        assert (await post('fable'))[0] == 409

    asyncio.run(scenario())
    assert tab.values == ['fable']
