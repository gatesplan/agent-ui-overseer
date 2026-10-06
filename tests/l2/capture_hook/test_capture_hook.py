import json

from project_manager.l2.capture_hook import CaptureHook


def test_events_append_to_tab_file_and_session_start_returns_protocol(tmp_path):
    protocol = tmp_path / 'protocol.md'
    protocol.write_text('## 규약', encoding='utf-8')
    hook = CaptureHook(tmp_path / 'cap', protocol)

    out = hook.run({'hook_event_name': 'SessionStart', 'session_id': 's', 'source': 'startup', 'cwd': 'C:/p'}, 'tab1')
    assert out == '## 규약'
    assert hook.run({'hook_event_name': 'UserPromptSubmit', 'session_id': 's', 'prompt': '해 줘'}, 'tab1') == ''
    hook.run({'hook_event_name': 'Stop', 'session_id': 's', 'last_assistant_message': '앞말\n### [제안][D] 규칙\n본문'}, 'tab1')

    rows = [json.loads(line) for line in (tmp_path / 'cap' / 'tab1.jsonl').read_text(encoding='utf-8').splitlines()]
    assert [r['event'] for r in rows] == ['session_start', 'prompt', 'turn']
    assert rows[1]['prompt'] == '해 줘'
    assert rows[2]['preamble'] == '앞말'
    assert rows[2]['items'][0]['tag'] == 'D'
