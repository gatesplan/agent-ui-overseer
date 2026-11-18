import json
import sys

from project_manager.l0.model_catalog import ModelCatalog


# 가짜 claude: 헤드리스 인자와 initialize 요청을 확인하고 정해 둔 응답을 낸다
def fake_claude(tmp_path, response: dict | None, stderr: str = '') -> ModelCatalog:
    lines = []
    if response is not None:
        lines.append({'type': 'system', 'subtype': 'hook_started'})
        lines.append({'type': 'control_response', 'response': {'request_id': 'other', 'subtype': 'success'}})
        lines.append({'type': 'control_response', 'response': {'request_id': 'overseer-models', **response}})
    script = tmp_path / 'fake_claude.py'
    script.write_text(
        'import json, sys\n'
        # 진짜 claude 처럼 UTF-8 로 낸다. 가짜 파이썬의 기본 출력은 콘솔 코드 페이지라 '·' 가 깨진다
        "sys.stdout.reconfigure(encoding='utf-8')\n"
        "assert '-p' in sys.argv and '--no-session-persistence' in sys.argv, sys.argv\n"
        'request = json.loads(sys.stdin.readline())\n'
        "assert request['request'] == {'subtype': 'initialize'}, request\n"
        f'for line in {json.dumps([json.dumps(x, ensure_ascii=False) for x in lines])}:\n'
        '    print(line)\n'
        f'sys.stderr.write({stderr!r})\n',
        encoding='utf-8')
    return ModelCatalog(command=[sys.executable, str(script)])


def ok(models) -> dict:
    return {'subtype': 'success', 'response': {'commands': [], 'models': models}}


# CLI 가 준 순서 그대로, 화면이 쓰는 칸만 남긴다
def test_models_keep_cli_order_and_only_display_fields(tmp_path):
    models = [
        {'value': 'default', 'resolvedModel': 'claude-opus-5-5', 'displayName': 'Default (recommended)',
         'description': 'Opus 5.5 · Best for everyday, complex tasks', 'supportsEffort': True},
        {'value': 'fable', 'resolvedModel': 'claude-fable-5-2', 'displayName': 'Fable 5.2', 'description': 'For your toughest challenges'},
        {'value': 'claude-opus-4-8', 'resolvedModel': 'claude-opus-4-8', 'displayName': 'Opus 4.8', 'description': ''},
    ]
    result = fake_claude(tmp_path, ok(models)).fetch()
    assert result['status'] == 'ok' and result['message'] == ''
    assert result['models'] == [
        {'value': 'default', 'resolvedModel': 'claude-opus-5-5', 'displayName': 'Default (recommended)',
         'description': 'Opus 5.5 · Best for everyday, complex tasks'},
        {'value': 'fable', 'resolvedModel': 'claude-fable-5-2', 'displayName': 'Fable 5.2', 'description': 'For your toughest challenges'},
        {'value': 'claude-opus-4-8', 'resolvedModel': 'claude-opus-4-8', 'displayName': 'Opus 4.8', 'description': ''},
    ]


# 값이 없는 항목은 버리고, 가리키는 모델이나 이름이 없으면 값으로 채운다
def test_models_skip_rows_without_value_and_fill_missing_names():
    assert ModelCatalog.models([{'displayName': '값 없음'}, 'x', {'value': 'claude-x-1'}]) == [
        {'value': 'claude-x-1', 'resolvedModel': 'claude-x-1', 'displayName': 'claude-x-1', 'description': ''}]
    assert ModelCatalog.models(None) == []


def test_errors_carry_reason(tmp_path):
    assert fake_claude(tmp_path, ok([])).fetch()['status'] == 'error'
    failed = fake_claude(tmp_path, {'subtype': 'error', 'error': 'not logged in'}).fetch()
    assert failed['status'] == 'error' and 'not logged in' in failed['message']
    silent = fake_claude(tmp_path, None, stderr='boom').fetch()
    assert silent['status'] == 'error' and silent['message'] == 'boom'


def test_missing_cli_is_missing():
    result = ModelCatalog(command=['no-such-claude-binary']).fetch()
    assert result['status'] == 'missing' and result['models'] == []
