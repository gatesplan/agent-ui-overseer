import asyncio

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
