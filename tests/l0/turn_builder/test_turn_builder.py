from project_manager.l0.turn_builder import TurnBuilder


def turn(text, items=()):
    return {'event': 'turn', 'session_id': 's1', 'text': text, 'preamble': '', 'items': [dict(i) for i in items]}


def test_turns_get_numbered_ids_and_prompts():
    events = [
        {'event': 'session_start', 'session_id': 's1', 'source': 'startup'},
        {'event': 'prompt', 'prompt': '검토해 줘'},
        turn('### [질문] a\n### [제안] b', [{'kind': '질문', 'title': 'a'}, {'kind': '제안', 'title': 'b'}]),
        {'event': 'prompt', 'prompt': '#1-1 답변: 예'},
        turn('### [보고] c', [{'kind': '보고', 'title': 'c'}]),
    ]
    built = TurnBuilder().build(events)
    assert [t['prompt'] for t in built['turns']] == ['검토해 줘', '#1-1 답변: 예']
    assert [i['id'] for i in built['turns'][0]['items']] == ['1-1', '1-2']
    assert built['turns'][1]['items'][0]['id'] == '2-1'
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
    assert [i['id'] for i in t['items']] == ['1-1', '1-2', '1-3']
    assert t['prompt'] == '상태 확인\n\n계속해봐\n\n이거  UI 때문이야?'
    assert t['preamble'] == '앞말 1\n\n앞말 2'
    assert t['parts'] == 2
    assert built['pending'] is None

    # 응답이 끝난 뒤 들어온 입력은 새 턴
    built = TurnBuilder().build(events + [second, {'event': 'prompt', 'prompt': '다음'}, {**turn('d'), 'prompts': ['다음']}])
    assert [x['turn'] for x in built['turns']] == [1, 2]
    assert built['turns'][1]['prompt'] == '다음'


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
