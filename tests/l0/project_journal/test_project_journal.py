from project_manager.l0.project_journal import ProjectJournal


def turn(session, n, items, prompt='p'):
    return {'id': f'{session}S-{n}', 'session': session, 'turn': n, 'at': f'2026-10-09T0{n}:00', 'after': None,
            'prompt': prompt, 'preamble': '', 'files': [], 'usage': {'calls': 1}, 'session_id': 'x',
            'items': [{'id': f'{session}S-{n}-{k}', 'kind': '제안', 'tag': None, 'title': t, 'body': '', 'parent': None}
                      for k, t in enumerate(items, 1)]}


def test_sessions_are_numbered_per_project_and_folder_ignores_itself(tmp_path):
    j = ProjectJournal(tmp_path)
    assert j.sessions() == []
    assert j.open_session('sid-a', 'tab1', 'startup') == 1
    assert j.open_session('sid-b', 'tab1', 'clear') == 2
    # 다른 탭(다른 날)에서 열어도 프로젝트 안에서 이어 매긴다
    assert ProjectJournal(tmp_path).open_session('sid-c', 'tab2', 'startup') == 3
    assert (tmp_path / '.overseer' / '.gitignore').read_text(encoding='utf-8') == '*\n'
    assert (tmp_path / '.overseer' / 'sessions' / '2.jsonl').exists()
    assert j.session_of('sid-b') == 2 and j.session_of('nope') is None
    assert (j.owner(1), j.owner(3), j.owner(9)) == ('tab1', 'tab2', None)
    # resume 이 새 세션 ID 로 뜨면 그 세션에 잇는다
    j.attach(2, 'sid-b2', 'resume')
    assert j.session_of('sid-b2') == 2


def test_turns_are_written_once_and_last_line_wins(tmp_path):
    j = ProjectJournal(tmp_path)
    j.open_session('s', 't', 'startup')
    t = turn(1, 1, ['가'])
    assert j.write_turn(t) is True
    assert j.write_turn(t) is False
    # 실행 정보만 바뀐 것은 다시 쓰지 않는다
    assert j.write_turn({**t, 'usage': {'calls': 2}}) is False
    # 이어 붙은 응답으로 사안이 늘면 다시 쓴다. 다시 연 기록도 같은 것을 또 쓰지 않는다
    assert j.write_turn(turn(1, 1, ['가', '나'])) is True
    assert ProjectJournal(tmp_path).write_turn(turn(1, 1, ['가', '나'])) is False
    j.write_turn(turn(1, 2, ['다']))
    assert [x['id'] for x in j.turns(1)] == ['1S-1', '1S-2']
    assert [i['title'] for i in j.turns(1)[0]['items']] == ['가', '나']
    assert 'usage' not in j.turns(1)[0]
    assert set(j.items()) == {'1S-1-1', '1S-1-2', '1S-2-1'}


def test_decisions_go_to_the_items_session(tmp_path):
    j = ProjectJournal(tmp_path)
    j.open_session('a', 't', 'startup')
    j.open_session('b', 't', 'clear')
    j.add_decisions([('1S-2-1', 'hold', ''), ('2S-1-1', 'reject', '범위 밖'), ('sum-2S-1', 'feedback', '좋음'), ('엉뚱', 'x', '')], 7)
    j.add_decisions([('1S-2-1', 'approve', '')])
    assert j.sent() == {
        '1S-2-1': {'action': 'approve', 'note': '', 'at': j.sent()['1S-2-1']['at']},
        '2S-1-1': {'action': 'reject', 'note': '범위 밖', 'at': j.sent()['2S-1-1']['at']},
        'sum-2S-1': {'action': 'feedback', 'note': '좋음', 'at': j.sent()['sum-2S-1']['at']},
    }
    assert set(j.sent([2])) == {'2S-1-1', 'sum-2S-1'}
    assert [d['action'] for d in j.history('1S-2-1')] == ['hold', 'approve']
    assert j.decisions([1])[0]['message'] == 7


def test_module_history(tmp_path):
    j = ProjectJournal(tmp_path)
    n = j.open_session('a', 't', 'startup')
    j.add_module_change(n, {'module': 'l1.x', 'before': '옛', 'after': '새', 'request': '새', 'turn': '1S-1'})
    j.add_module_change(n, {'module': 'l1.x', 'before': '새', 'after': '더 새', 'request': None, 'turn': '1S-2'})
    history = j.module_history()
    assert [e['after'] for e in history['l1.x']] == ['새', '더 새']
    assert history['l1.x'][0]['session'] == 1 and history['l1.x'][0]['at']


def test_rows_read_only_the_appended_tail(tmp_path):
    j = ProjectJournal(tmp_path)
    j.open_session('s', 't', 'startup')
    j.add_decisions([('1S-1-1', 'approve', '')])
    first = j.decisions()
    # 다른 쪽(훅, 다른 인스턴스)이 덧붙인 줄도 읽는다. 앞서 돌려준 목록은 그대로다
    ProjectJournal(tmp_path).add_decisions([('1S-1-2', 'reject', '아님')])
    assert [d['item'] for d in j.decisions()] == ['1S-1-1', '1S-1-2']
    assert [d['item'] for d in first] == ['1S-1-1']
    # 줄바꿈이 없는 쓰다 만 줄은 다음에 읽는다
    path = tmp_path / '.overseer' / 'sessions' / '1.jsonl'
    with path.open('a', encoding='utf-8') as f:
        f.write('{"type": "decision", "item": "1S-1-3", "action": "hold"')
    assert len(j.decisions()) == 2
    with path.open('a', encoding='utf-8') as f:
        f.write(', "note": ""}\n')
    assert [d['item'] for d in j.decisions()] == ['1S-1-1', '1S-1-2', '1S-1-3']
    # 파일이 줄면 처음부터 다시 읽는다
    path.write_text('{"type": "session", "session": 1, "tab": "t2"}\n', encoding='utf-8')
    assert j.decisions() == [] and j.owner(1) == 't2'
