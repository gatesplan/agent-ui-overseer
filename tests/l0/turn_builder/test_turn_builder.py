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
