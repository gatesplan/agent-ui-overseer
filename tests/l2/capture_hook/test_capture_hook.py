import json

from project_manager.l2.capture_hook import CaptureHook


def test_events_append_to_tab_file_and_session_start_returns_protocol(tmp_path):
    protocol = tmp_path / 'protocol.md'
    protocol.write_text('## 규약', encoding='utf-8')
    hook = CaptureHook(tmp_path / 'cap', protocol)

    out = hook.run({'hook_event_name': 'SessionStart', 'session_id': 's', 'source': 'startup', 'cwd': str(tmp_path / 'p')}, 'tab1')
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
    from project_manager.l0.project_key import ProjectKey
    from project_manager.l0.record_store import RecordStore
    protocol = tmp_path / 'protocol.md'
    protocol.write_text('## 규약', encoding='utf-8')
    records = RecordStore()
    records.add(ProjectKey.of(str(tmp_path / 'proj')), 'D', '로그는 INFO')
    hook = CaptureHook(tmp_path / 'cap', protocol, records=records)
    out = hook.run({'hook_event_name': 'SessionStart', 'session_id': 's', 'source': 'startup', 'cwd': str(tmp_path / 'proj')}, 'tab')
    assert out.startswith('## 규약') and '- D-1 로그는 INFO' in out
    # 다른 프로젝트에는 넣지 않는다
    out = hook.run({'hook_event_name': 'SessionStart', 'session_id': 's', 'source': 'startup', 'cwd': str(tmp_path / 'other')}, 'tab')
    assert out == '## 규약'


def test_prompt_gets_notice_of_records_added_by_other_tabs_once(tmp_path):
    from project_manager.l0.project_key import ProjectKey
    from project_manager.l0.record_store import RecordStore
    records = RecordStore()
    cwd = str(tmp_path / 'proj')
    project = ProjectKey.of(cwd)
    records.add(project, 'D', '처음 결정', tab_id='other', item_id='1S-1-1')
    hook = CaptureHook(tmp_path / 'cap', records=records)
    start = {'hook_event_name': 'SessionStart', 'session_id': 's', 'source': 'startup', 'cwd': cwd}
    prompt = {'hook_event_name': 'UserPromptSubmit', 'session_id': 's', 'prompt': '다음', 'cwd': cwd}
    assert '처음 결정' in hook.run(start, 'tab')
    assert hook.run(prompt, 'tab') == ''
    records.add(project, 'D', '바뀐 결정', tab_id='other', item_id='1S-2-1', replaces='D-1')
    out = hook.run(prompt, 'tab')
    assert '- 변경: D-1 처음 결정 → D-2 바뀐 결정' in out
    # 한 번만 알린다
    assert hook.run(prompt, 'tab') == ''


def test_prompt_in_session_started_before_feature_gets_no_backlog(tmp_path):
    from project_manager.l0.project_key import ProjectKey
    from project_manager.l0.record_store import RecordStore
    records = RecordStore()
    cwd = str(tmp_path / 'proj')
    records.add(ProjectKey.of(cwd), 'D', '예전 결정', tab_id='other', item_id='1S-1-1')
    hook = CaptureHook(tmp_path / 'cap', records=records)
    # 이 기능 전 버전의 시작 기록(records_seen 없음)
    (tmp_path / 'cap').mkdir(exist_ok=True)
    (tmp_path / 'cap' / 'tab.jsonl').write_text('{"event": "session_start", "session_id": "old"}\n', encoding='utf-8')
    assert hook.run({'hook_event_name': 'UserPromptSubmit', 'session_id': 'old', 'prompt': 'x', 'cwd': cwd}, 'tab') == ''


def test_prompt_recovers_protocol_when_session_start_failed(tmp_path):
    from project_manager.l0.project_key import ProjectKey
    from project_manager.l0.record_store import RecordStore
    protocol = tmp_path / 'protocol.md'
    protocol.write_text('## 규약', encoding='utf-8')
    records = RecordStore()
    cwd = str(tmp_path / 'proj')
    records.add(ProjectKey.of(cwd), 'D', '로그는 INFO')
    hook = CaptureHook(tmp_path / 'cap', protocol, records=records)
    prompt = {'hook_event_name': 'UserPromptSubmit', 'session_id': 's', 'prompt': '이슈 확인', 'cwd': cwd}
    out = hook.run(prompt, 'tab')
    assert out.startswith('## 규약') and '- D-1 로그는 INFO' in out
    rows = [json.loads(line) for line in (tmp_path / 'cap' / 'tab.jsonl').read_text(encoding='utf-8').splitlines()]
    assert [(r['event'], r.get('source')) for r in rows] == [('session_start', 'recovered'), ('prompt', None)]
    # 한 번만 넣는다
    assert hook.run(prompt, 'tab') == ''


def test_session_numbers_come_from_the_project(tmp_path):
    from project_manager.l0.project_journal import ProjectJournal
    hook = CaptureHook(tmp_path / 'cap')
    proj = str(tmp_path / 'proj')

    def start(sid, source, tab='tab', cwd=proj, project=None):
        hook.run({'hook_event_name': 'SessionStart', 'session_id': sid, 'source': source, 'cwd': cwd}, tab, project)
        rows = [json.loads(line) for line in (tmp_path / 'cap' / f'{tab}.jsonl').read_text(encoding='utf-8').splitlines()]
        return rows[-1]['session']

    assert start('a', 'startup') == 1
    # compact 는 같은 claude 세션이라 같은 번호
    assert start('a', 'compact') == 1
    # /clear 는 새 번호
    assert start('b', 'clear') == 2
    # resume 이 새 claude 세션 ID 로 떠도 이 탭의 마지막 세션을 잇는다
    assert start('b2', 'resume') == 2
    assert ProjectJournal(proj).session_of('b2') == 2
    # 다른 탭에서 연 세션은 프로젝트 안에서 이어 매긴다
    assert start('c', 'startup', tab='other') == 3
    # 패널이 넘긴 프로젝트 폴더가 훅 입력의 cwd 보다 앞선다
    assert start('d', 'startup', tab='third', cwd=str(tmp_path / 'proj' / 'sub'), project=proj) == 4
    assert not (tmp_path / 'proj' / 'sub').exists()
    assert ProjectJournal(proj).owner(4) == 'third'


END = {'type': 'system', 'subtype': 'turn_duration'}


def _say(text):
    return {'type': 'assistant', 'message': {'content': [{'type': 'text', 'text': text}]}}


def _ask(text):
    return {'type': 'user', 'message': {'content': text}}


class _Session:
    # 탭 하나의 대화 기록 파일과 훅. 기록 파일에 줄을 붙이고 훅을 부른다
    def __init__(self, tmp_path):
        self.cap = tmp_path / 'cap'
        self.transcript = tmp_path / 's.jsonl'
        self.rows = []
        self.hook = CaptureHook(self.cap)
        self.add()
        self.run('SessionStart', source='startup')

    def add(self, *rows):
        self.rows += rows
        self.transcript.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in self.rows), encoding='utf-8')

    def run(self, event, **kw):
        self.hook.run({'hook_event_name': event, 'session_id': 's', 'transcript_path': str(self.transcript), **kw}, 'tab')

    def records(self):
        return [json.loads(line) for line in (self.cap / 'tab.jsonl').read_text(encoding='utf-8').splitlines()]


def test_stop_recovers_turn_whose_stop_hook_timed_out(tmp_path):
    s = _Session(tmp_path)
    s.add(_ask('A'), _say('### [보고] A'))
    s.run('Stop', last_assistant_message='### [보고] A')
    # B 의 Stop 훅은 시간 초과로 끊겨 기록이 없다. 기록 파일에는 B 의 끝 표시가 붙는다
    s.add(END, _ask('B'), _say('### [보고] B'), {'type': 'attachment', 'attachment': {'type': 'hook_cancelled'}}, END)
    s.add(_ask('C'), _say('### [보고] C'))
    s.run('Stop', last_assistant_message='### [보고] C')
    turns = [r for r in s.records() if r['event'] == 'turn']
    assert [(t['source'], t['prompts'], t['items'][0]['title']) for t in turns] == [
        ('hook', ['A'], 'A'), ('recovered', ['B'], 'B'), ('hook', ['C'], 'C')]
    # 다음 Stop 은 되살린 턴을 다시 남기지 않는다
    s.add(END, _ask('D'), _say('D'))
    s.run('Stop', last_assistant_message='D')
    assert [r['source'] for r in s.records() if r['event'] == 'turn'] == ['hook', 'recovered', 'hook', 'hook']


def test_idle_notice_recovers_missed_turn_before_the_notice(tmp_path):
    s = _Session(tmp_path)
    s.add(_ask('A'), _say('### [보고] A'), END)
    s.run('Notification', notification_type='idle_prompt', message='Claude is waiting for your input')
    assert [(r['event'], r.get('source'), r.get('prompts')) for r in s.records()][1:] == [
        ('turn', 'recovered', ['A']), ('notification', None, None)]
    # 권한 확인 같은 다른 알림에서는 찾지 않는다
    s.add(_ask('B'), _say('B'), END)
    s.run('Notification', notification_type='permission_prompt', message='needs permission')
    assert [r['event'] for r in s.records()][-1] == 'notification' and len(s.records()) == 4


def test_stop_failure_records_error_as_the_turn(tmp_path):
    s = _Session(tmp_path)
    error = {'type': 'assistant', 'isApiErrorMessage': True, 'message': {'content': [{'type': 'text', 'text': "You've hit your limit"}]}}
    s.add(_ask('해 줘'), error)
    s.run('StopFailure', error='rate_limit', last_assistant_message="You've hit your limit")
    turn = s.records()[-1]
    assert (turn['source'], turn['error'], turn['text'], turn['prompts']) == ('stop_failure', 'rate_limit', "You've hit your limit", ['해 줘'])
    assert turn['items'] == [] and turn['preamble'] == "You've hit your limit"
    # 끝 표시가 붙은 뒤에 다음 Stop 이 와도 오류 턴을 다시 되살리지 않는다
    s.add(END, _ask('다시'), _say('됐다'))
    s.run('Stop', last_assistant_message='됐다')
    assert [r['source'] for r in s.records() if r['event'] == 'turn'] == ['stop_failure', 'hook']


def test_stop_failure_after_turn_end_marker_is_not_doubled(tmp_path):
    # 오류 턴의 끝 표시가 StopFailure 훅보다 먼저 붙었어도 그 턴은 한 번만 남는다
    s = _Session(tmp_path)
    s.add(_ask('해 줘'), {'type': 'assistant', 'isApiErrorMessage': True, 'message': {'content': [{'type': 'text', 'text': 'Login expired'}]}}, END)
    s.run('StopFailure', error='authentication_failed', last_assistant_message='Login expired')
    turns = [r for r in s.records() if r['event'] == 'turn']
    assert [(t['source'], t['prompts'], t['text']) for t in turns] == [('stop_failure', ['해 줘'], 'Login expired')]
