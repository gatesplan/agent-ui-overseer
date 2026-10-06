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


def test_turn_uses_transcript_rows_left_at_session_start_and_records_usage(tmp_path):
    transcript = tmp_path / 's.jsonl'

    def write(rows):
        transcript.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows), encoding='utf-8')

    old = [
        {'type': 'user', 'message': {'content': '예전 입력'}},
        {'type': 'assistant', 'message': {'id': 'm0', 'usage': {'output_tokens': 99}, 'content': [{'type': 'text', 'text': '예전 응답'}]}},
    ]
    write(old)
    hook = CaptureHook(tmp_path / 'cap')
    hook.run({'hook_event_name': 'SessionStart', 'session_id': 's', 'source': 'resume', 'transcript_path': str(transcript)}, 'tab')
    # 턴 끝 표시가 없어도 세션 시작 때 남긴 길이 뒤부터 센다. 중단된 입력도 함께 들어온다
    write(old + [
        {'type': 'user', 'message': {'content': '첫 입력'}},
        {'type': 'assistant', 'message': {'id': 'm1', 'usage': {'output_tokens': 3}, 'content': [{'type': 'text', 'text': '중간'}]}},
        {'type': 'user', 'message': {'content': [{'type': 'text', 'text': '[Request interrupted by user]'}]}},
        {'type': 'user', 'message': {'content': '계속'}},
        {'type': 'assistant', 'message': {'id': 'm2', 'usage': {'output_tokens': 4}, 'content': [{'type': 'text', 'text': '끝'}]}},
    ])
    hook.run({'hook_event_name': 'Stop', 'session_id': 's', 'last_assistant_message': '끝', 'transcript_path': str(transcript)}, 'tab')
    hook.run({'hook_event_name': 'Notification', 'session_id': 's', 'message': 'Claude needs your permission to use Bash',
              'notification_type': 'permission_prompt'}, 'tab')

    rows = [json.loads(line) for line in (tmp_path / 'cap' / 'tab.jsonl').read_text(encoding='utf-8').splitlines()]
    assert rows[0]['transcript_rows'] == 2
    assert rows[1]['prompts'] == ['첫 입력', '계속']
    assert (rows[1]['usage']['calls'], rows[1]['usage']['output_tokens']) == (2, 7)
    assert rows[1]['transcript_rows'] == 7
    assert rows[2] == {**rows[2], 'event': 'notification', 'kind': 'permission_prompt'}


def test_turn_record_survives_unreadable_transcript(tmp_path):
    bad = tmp_path / 'bad.jsonl'
    bad.write_bytes(b'\xff\xfe not utf8')
    hook = CaptureHook(tmp_path / 'cap')
    hook.run({'hook_event_name': 'Stop', 'session_id': 's', 'last_assistant_message': '### [보고] a', 'transcript_path': str(bad)}, 'tab')
    row = json.loads((tmp_path / 'cap' / 'tab.jsonl').read_text(encoding='utf-8'))
    assert row['items'][0]['title'] == 'a' and row['usage'] is None


def test_session_start_injects_active_records_of_project(tmp_path):
    from project_manager.l0.record_store import RecordStore
    protocol = tmp_path / 'protocol.md'
    protocol.write_text('## 규약', encoding='utf-8')
    records = RecordStore(tmp_path / 'o.db')
    records.add(RecordStore.project_key(str(tmp_path / 'proj')), 'D', '로그는 INFO')
    hook = CaptureHook(tmp_path / 'cap', protocol, records=records)
    out = hook.run({'hook_event_name': 'SessionStart', 'session_id': 's', 'source': 'startup', 'cwd': str(tmp_path / 'proj')}, 'tab')
    assert out.startswith('## 규약') and '- D-1 로그는 INFO' in out
    # 다른 프로젝트에는 넣지 않는다
    out = hook.run({'hook_event_name': 'SessionStart', 'session_id': 's', 'source': 'startup', 'cwd': str(tmp_path / 'other')}, 'tab')
    assert out == '## 규약'


def test_prompt_gets_notice_of_records_added_by_other_tabs_once(tmp_path):
    from project_manager.l0.record_store import RecordStore
    records = RecordStore(tmp_path / 'o.db')
    cwd = str(tmp_path / 'proj')
    project = RecordStore.project_key(cwd)
    records.add(project, 'D', '처음 결정', tab_id='other', item_id='1-1')
    hook = CaptureHook(tmp_path / 'cap', records=records)
    start = {'hook_event_name': 'SessionStart', 'session_id': 's', 'source': 'startup', 'cwd': cwd}
    prompt = {'hook_event_name': 'UserPromptSubmit', 'session_id': 's', 'prompt': '다음', 'cwd': cwd}
    assert '처음 결정' in hook.run(start, 'tab')
    assert hook.run(prompt, 'tab') == ''
    records.add(project, 'D', '바뀐 결정', tab_id='other', item_id='2-1', replaces='D-1')
    out = hook.run(prompt, 'tab')
    assert '- 변경: D-1 처음 결정 → D-2 바뀐 결정' in out
    # 한 번만 알린다
    assert hook.run(prompt, 'tab') == ''


def test_prompt_in_session_started_before_feature_gets_no_backlog(tmp_path):
    from project_manager.l0.record_store import RecordStore
    records = RecordStore(tmp_path / 'o.db')
    cwd = str(tmp_path / 'proj')
    records.add(RecordStore.project_key(cwd), 'D', '예전 결정', tab_id='other', item_id='1-1')
    hook = CaptureHook(tmp_path / 'cap', records=records)
    # 이 기능 전 버전의 시작 기록(records_seen 없음)
    (tmp_path / 'cap').mkdir(exist_ok=True)
    (tmp_path / 'cap' / 'tab.jsonl').write_text('{"event": "session_start", "session_id": "old"}\n', encoding='utf-8')
    assert hook.run({'hook_event_name': 'UserPromptSubmit', 'session_id': 'old', 'prompt': 'x', 'cwd': cwd}, 'tab') == ''


def test_prompt_recovers_protocol_when_session_start_failed(tmp_path):
    from project_manager.l0.record_store import RecordStore
    protocol = tmp_path / 'protocol.md'
    protocol.write_text('## 규약', encoding='utf-8')
    records = RecordStore(tmp_path / 'o.db')
    cwd = str(tmp_path / 'proj')
    records.add(RecordStore.project_key(cwd), 'D', '로그는 INFO')
    hook = CaptureHook(tmp_path / 'cap', protocol, records=records)
    prompt = {'hook_event_name': 'UserPromptSubmit', 'session_id': 's', 'prompt': '이슈 확인', 'cwd': cwd}
    out = hook.run(prompt, 'tab')
    assert out.startswith('## 규약') and '- D-1 로그는 INFO' in out
    rows = [json.loads(line) for line in (tmp_path / 'cap' / 'tab.jsonl').read_text(encoding='utf-8').splitlines()]
    assert [(r['event'], r.get('source')) for r in rows] == [('session_start', 'recovered'), ('prompt', None)]
    # 한 번만 넣는다
    assert hook.run(prompt, 'tab') == ''
