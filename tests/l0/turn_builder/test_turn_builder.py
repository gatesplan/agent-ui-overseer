from project_manager.l0.turn_builder import TurnBuilder


def turn(text, items=()):
    return {'event': 'turn', 'session_id': 's1', 'text': text, 'preamble': '', 'items': [dict(i) for i in items]}


def test_turns_get_numbered_ids_and_prompts():
    events = [
        {'event': 'session_start', 'session_id': 's1', 'source': 'startup'},
        {'event': 'prompt', 'prompt': '검토해 줘'},
        turn('### [질문] a\n### [제안] b', [{'kind': '질문', 'title': 'a'}, {'kind': '제안', 'title': 'b'}]),
        {'event': 'prompt', 'prompt': '#1S-1-1 답변: 예'},
        turn('### [보고] c', [{'kind': '보고', 'title': 'c'}]),
    ]
    built = TurnBuilder().build(events)
    assert [t['prompt'] for t in built['turns']] == ['검토해 줘', '#1S-1-1 답변: 예']
    assert [i['id'] for i in built['turns'][0]['items']] == ['1S-1-1', '1S-1-2']
    assert built['turns'][1]['items'][0]['id'] == '1S-2-1'
    assert [t['id'] for t in built['turns']] == ['1S-1', '1S-2']
    assert built['pending'] is None
    assert built['session_id'] == 's1'


def test_queued_prompt_response_joins_the_same_turn():
    # 작업 중에 넣은 입력은 입력 훅이 먼저 불린다. 응답이 끝날 때 대기열이 남아 있으면 다음 응답은 같은 턴이다
    events = [
        {'event': 'prompt', 'prompt': '상태 확인'},
        {'event': 'prompt', 'prompt': '계속해봐'},
        {'event': 'prompt', 'prompt': '이거 UI 때문이야?'},
        {**turn('### [보고] a\n### [제안] b', [{'kind': '보고', 'title': 'a'}, {'kind': '제안', 'title': 'b'}]),
         'preamble': '앞말 1', 'prompts': ['상태 확인', '계속해봐']},
    ]
    built = TurnBuilder().build(events)
    assert built['turns'][0]['prompt'] == '상태 확인\n\n계속해봐'
    assert built['pending'] == '이거 UI 때문이야?'

    second = {**turn('### [보고] c', [{'kind': '보고', 'title': 'c'}]), 'preamble': '앞말 2', 'prompts': ['이거  UI 때문이야?']}
    built = TurnBuilder().build(events + [second])
    assert len(built['turns']) == 1
    t = built['turns'][0]
    assert [i['id'] for i in t['items']] == ['1S-1-1', '1S-1-2', '1S-1-3']
    assert t['prompt'] == '상태 확인\n\n계속해봐\n\n이거  UI 때문이야?'
    assert t['preamble'] == '앞말 1\n\n앞말 2'
    assert t['parts'] == 2
    assert built['pending'] is None

    # 응답이 끝난 뒤 들어온 입력은 새 턴
    built = TurnBuilder().build(events + [second, {'event': 'prompt', 'prompt': '다음'}, {**turn('d'), 'prompts': ['다음']}])
    assert [x['turn'] for x in built['turns']] == [1, 2]
    assert built['turns'][1]['prompt'] == '다음'


def test_idle_notice_moves_leftover_prompt_into_last_turn():
    # 흡수된 입력을 기록에서 못 읽어 대기로 남아도, 입력 대기 알림이 오면 앞 턴 입력으로 옮기고 작업 중을 푼다
    events = [
        {'event': 'prompt', 'prompt': '변경사항 확인'},
        {'event': 'prompt', 'prompt': '유료 API 부르나?'},
        {**turn('응답'), 'prompts': ['변경사항 확인']},
    ]
    assert TurnBuilder().build(events)['pending'] == '유료 API 부르나?'
    built = TurnBuilder().build(events + [{'event': 'notification', 'kind': 'idle_prompt', 'message': 'waiting'}])
    assert built['pending'] is None
    assert built['attention'] is None
    assert built['turns'][0]['prompt'] == '변경사항 확인\n\n유료 API 부르나?'
    # 다음 응답은 새 턴이다
    built = TurnBuilder().build(events + [{'event': 'notification', 'kind': 'idle_prompt'}, {'event': 'prompt', 'prompt': '다음'},
                                          {**turn('d'), 'prompts': ['다음']}])
    assert [x['turn'] for x in built['turns']] == [1, 2]


def test_system_prompt_response_joins_previous_turn():
    # 백그라운드 작업 알림도 입력 훅이 불린다. 작업 중 알림은 대기로 남기지 않고, 알림에 대한 응답은 앞 턴에 붙인다
    note = '<task-notification>\n<task-id>b1</task-id>\n</task-notification>'
    events = [
        {'event': 'prompt', 'prompt': '실측해 봐'},
        {'event': 'prompt', 'prompt': note},
        {'event': 'prompt', 'prompt': note},
        {**turn('### [보고] a', [{'kind': '보고', 'title': 'a'}]), 'prompts': ['실측해 봐']},
    ]
    built = TurnBuilder().build(events)
    assert built['pending'] is None
    built = TurnBuilder().build(events + [{'event': 'notification', 'kind': 'idle_prompt'}])
    assert built['turns'][0]['prompt'] == '실측해 봐'

    # 예전 훅은 알림을 턴 입력으로 남겼다. 그래도 사용자 입력이 없는 응답이다
    later = [{'event': 'notification', 'kind': 'idle_prompt'}, {'event': 'prompt', 'prompt': note},
             {**turn('### [보고] b', [{'kind': '보고', 'title': 'b'}]), 'prompts': [note]}]
    built = TurnBuilder().build(events + later)
    assert len(built['turns']) == 1
    t = built['turns'][0]
    assert [i['id'] for i in t['items']] == ['1S-1-1', '1S-1-2']
    assert t['prompt'] == '실측해 봐'
    assert t['parts'] == 2
    assert built['pending'] is None

    # /clear 뒤 첫 응답은 입력이 없어도 새 턴
    built = TurnBuilder().build(events + [{'event': 'session_start', 'source': 'clear'}, {**turn('c'), 'prompts': []}])
    assert [x['id'] for x in built['turns']] == ['1S-1', '2S-1']


def test_clear_starts_a_new_session_number():
    # /clear 마다 세션 번호가 오르고 턴 번호는 1부터. compact 는 맥락을 이어 가므로 세션을 나누지 않는다
    events = [{'event': 'prompt', 'prompt': 'a'}, {**turn('### [질문] a', [{'kind': '질문', 'title': 'a'}]), 'prompts': ['a']}]
    assert TurnBuilder().build(events)['session'] == 1
    events += [{'event': 'session_start', 'source': 'clear'}]
    assert TurnBuilder().build(events)['session'] == 2
    events += [{'event': 'prompt', 'prompt': 'b'}, {**turn('### [제안] b', [{'kind': '제안', 'title': 'b'}]), 'prompts': ['b']},
               {'event': 'session_start', 'source': 'compact'},
               {'event': 'prompt', 'prompt': 'c'}, {**turn('c'), 'prompts': ['c']}]
    built = TurnBuilder().build(events)
    assert built['session'] == 2
    assert [(t['id'], t['session'], t['turn']) for t in built['turns']] == [('1S-1', 1, 1), ('2S-1', 2, 1), ('2S-2', 2, 2)]
    assert built['turns'][1]['items'][0]['id'] == '2S-1-1'


def test_session_number_from_the_hook_wins():
    # 훅이 프로젝트에서 받은 번호를 적었으면 그것을 쓴다. resume, compact 로 같은 번호가 다시 오면 턴 번호를 이어 간다
    events = [{'event': 'session_start', 'source': 'startup', 'session': 7},
              {'event': 'prompt', 'prompt': 'a'}, {**turn('a'), 'prompts': ['a']},
              {'event': 'session_start', 'source': 'resume', 'session': 7},
              {'event': 'prompt', 'prompt': 'b'}, {**turn('b', [{'kind': '보고', 'title': 'b'}]), 'prompts': ['b']},
              {'event': 'session_start', 'source': 'clear', 'session': 9},
              {'event': 'prompt', 'prompt': 'c'}, {**turn('c'), 'prompts': ['c']}]
    built = TurnBuilder().build(events)
    assert [t['id'] for t in built['turns']] == ['7S-1', '7S-2', '9S-1']
    assert built['turns'][1]['items'][0]['id'] == '7S-2-1'
    assert built['session'] == 9


def test_legacy_refs_are_relabeled_to_session_ids():
    # 예전 ID 는 탭 전체에서 이어진 턴 번호였다. 본문, 입력, 출처의 `#n-k` 를 n 번째 턴의 새 ID 로 바꾼다
    events = [
        {'event': 'prompt', 'prompt': 'a'},
        {**turn('### [질문] a', [{'kind': '질문', 'title': 'a', 'body': ''}]), 'prompts': ['a']},
        {'event': 'session_start', 'source': 'clear'},
        {'event': 'prompt', 'prompt': '#1-1 답변: 예'},
        {**turn('### [제안] b (← #1-1)', [{'kind': '제안', 'title': 'b', 'body': '근거: #1-1, #2-1, #9-1', 'parent': '1-1'}]),
         'prompts': ['#1-1 답변: 예']},
    ]
    t = TurnBuilder().build(events)['turns'][1]
    assert t['prompt'] == '#1S-1-1 답변: 예'
    assert t['text'] == '### [제안] b (← #1S-1-1)'
    item = t['items'][0]
    assert item['parent'] == '1S-1-1'
    # 없는 턴을 가리키면 그대로 둔다
    assert item['body'] == '근거: #1S-1-1, #2S-1-1, #9-1'


def test_unmatched_older_prompts_are_dropped_when_later_one_matches():
    events = [
        {'event': 'prompt', 'prompt': '/clear'},
        {'event': 'prompt', 'prompt': '진짜 입력'},
        {**turn('응답'), 'prompts': ['진짜 입력']},
    ]
    assert TurnBuilder().build(events)['pending'] is None


def test_pending_prompt_and_clear_mark_and_empty_turn_skipped():
    events = [
        {'event': 'prompt', 'prompt': '첫'},
        turn(''),
        turn('응답'),
        {'event': 'session_start', 'session_id': 's2', 'source': 'clear'},
        {'event': 'prompt', 'prompt': '다음'},
    ]
    built = TurnBuilder().build(events)
    assert len(built['turns']) == 1
    assert built['pending'] == '다음'
    assert built['session_id'] == 's2'

    built = TurnBuilder().build(events + [turn('두 번째')])
    assert built['turns'][1]['after'] == 'clear'
    assert built['turns'][0]['after'] is None


def test_open_permission_and_attention_and_usage_sum():
    u = lambda c, o: {'calls': c, 'tools': 0, 'input_tokens': 0, 'cache_creation_input_tokens': 0, 'cache_read_input_tokens': 0, 'output_tokens': o}
    events = [
        {'event': 'prompt', 'prompt': 'a'},
        {'event': 'prompt', 'prompt': 'b'},
        {**turn('응답 1'), 'prompts': ['a'], 'usage': u(2, 10)},
        {**turn('응답 2'), 'prompts': ['b'], 'usage': u(3, 5)},
        {'event': 'prompt', 'prompt': 'rm 해 줘'},
        {'event': 'permission', 'request_id': 'r1', 'tool_name': 'Bash', 'tool_input': {'command': 'rm -rf x'}},
    ]
    built = TurnBuilder().build(events)
    assert built['turns'][0]['usage']['calls'] == 5 and built['turns'][0]['usage']['output_tokens'] == 15
    assert built['permission']['tool_input'] == {'command': 'rm -rf x'}

    done = events + [{'event': 'permission_done', 'request_id': 'r1', 'behavior': 'terminal'},
                     {'event': 'notification', 'message': 'Claude needs your permission to use Bash', 'kind': 'permission_prompt'}]
    built = TurnBuilder().build(done)
    assert built['permission'] is None
    assert built['attention']['kind'] == 'permission_prompt'

    # 대기 알림은 띄우지 않고, 턴이 끝나면 확인 알림도 끝난다
    assert TurnBuilder().build(done + [{**turn('끝'), 'prompts': ['rm 해 줘']}])['attention'] is None
    assert TurnBuilder().build(events[:3] + [{'event': 'notification', 'message': 'waiting', 'kind': 'idle_prompt'}])['attention'] is None


def test_files_edited_in_turn_are_kept_and_joined_without_duplicates():
    events = [
        {'event': 'prompt', 'prompt': '고쳐 줘'},
        {'event': 'prompt', 'prompt': '이것도'},
        {**turn('### [보고] a', [{'kind': '보고', 'title': 'a'}]), 'prompts': ['고쳐 줘'], 'files': ['C:/p/a.py', 'C:/p/b.py']},
        {**turn('### [보고] b', [{'kind': '보고', 'title': 'b'}]), 'prompts': ['이것도'], 'files': ['C:/p/b.py', 'C:/p/c.py']},
        {'event': 'prompt', 'prompt': '다음'},
        turn('### [보고] c', [{'kind': '보고', 'title': 'c'}]),
    ]
    turns = TurnBuilder().build(events)['turns']
    assert turns[0]['files'] == ['C:/p/a.py', 'C:/p/b.py', 'C:/p/c.py']
    # 예전 훅 기록에는 files 가 없다
    assert turns[1]['files'] == []
