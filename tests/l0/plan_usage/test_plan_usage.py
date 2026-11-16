import json
import sys

from project_manager.l0.plan_usage import PlanUsage


# 가짜 claude: 헤드리스 인자와 get_usage 요청을 확인하고 정해 둔 응답을 낸다
def fake_claude(tmp_path, response: dict | None, stderr: str = '') -> PlanUsage:
    lines = []
    if response is not None:
        lines.append({'type': 'system', 'subtype': 'hook_started'})
        lines.append({'type': 'control_response', 'response': {'request_id': 'other', 'subtype': 'success'}})
        lines.append({'type': 'control_response', 'response': {'request_id': 'overseer-usage', **response}})
    script = tmp_path / 'fake_claude.py'
    script.write_text(
        'import json, sys\n'
        "assert '-p' in sys.argv and '--no-session-persistence' in sys.argv, sys.argv\n"
        'request = json.loads(sys.stdin.readline())\n'
        "assert request['request'] == {'subtype': 'get_usage', 'skip_behaviors': True}, request\n"
        f'for line in {json.dumps([json.dumps(x, ensure_ascii=False) for x in lines])}:\n'
        '    print(line)\n'
        f'sys.stderr.write({stderr!r})\n',
        encoding='utf-8')
    return PlanUsage(command=[sys.executable, str(script)])


def ok(rate_limits: dict) -> dict:
    return {'subtype': 'success', 'response': {'rate_limits_available': True, 'rate_limits': rate_limits}}


def test_limit_rows_follow_the_server_order_and_severity(tmp_path):
    rate = {'seven_day': {'utilization': 76}, 'limits': [
        {'kind': 'weekly_all', 'group': 'weekly', 'percent': 76, 'severity': 'warning', 'resets_at': '2026-11-16T20:00:00+00:00'},
        {'kind': 'weekly_scoped', 'group': 'weekly', 'percent': 100, 'severity': 'critical', 'resets_at': '2026-11-16T20:00:00+00:00',
         'scope': {'model': {'id': None, 'display_name': 'Fable'}}},
    ]}
    result = fake_claude(tmp_path, ok(rate)).fetch()
    assert result['status'] == 'ok'
    assert result['limits'] == [
        {'kind': 'weekly_all', 'label': '주간 전체', 'percent': 76.0, 'resets_at': '2026-11-16T20:00:00+00:00', 'severity': 'warning'},
        {'kind': 'weekly_scoped', 'label': '주간 Fable', 'percent': 100.0, 'resets_at': '2026-11-16T20:00:00+00:00', 'severity': 'critical'},
    ]


# limits[] 가 없는 응답(예전 판)은 창별 값과 모델별 주간 창으로 만든다. 빈 창은 뺀다
def test_without_limit_rows_builds_rows_from_windows(tmp_path):
    rate = {'five_hour': {'utilization': 12, 'resets_at': 'a'}, 'seven_day': {'utilization': 80, 'resets_at': 'b'},
            'seven_day_opus': None, 'model_scoped': [{'display_name': 'Fable', 'utilization': 95, 'resets_at': 'c'}]}
    rows = fake_claude(tmp_path, ok(rate)).fetch()['limits']
    assert [(r['label'], r['percent'], r['severity']) for r in rows] == [
        ('5시간', 12.0, 'normal'), ('주간 전체', 80.0, 'warning'), ('주간 Fable', 95.0, 'critical')]


def test_login_without_plan_limits_is_unavailable(tmp_path):
    response = {'subtype': 'success', 'response': {'rate_limits_available': False, 'rate_limits': None}}
    assert fake_claude(tmp_path, response).fetch()['status'] == 'unavailable'


def test_no_answer_is_an_error_with_stderr(tmp_path):
    result = fake_claude(tmp_path, None, stderr='not logged in').fetch()
    assert (result['status'], result['limits'], result['message']) == ('error', [], 'not logged in')


def test_error_answer_is_an_error(tmp_path):
    result = fake_claude(tmp_path, {'subtype': 'error', 'error': 'Unknown request'}).fetch()
    assert (result['status'], result['message']) == ('error', 'Unknown request')


def test_missing_command(tmp_path):
    result = PlanUsage(command=[str(tmp_path / 'no-claude')]).fetch()
    assert result['status'] == 'missing'
