import os

from project_manager.l2.agent_tab import AgentTab


def test_child_env_drops_session_markers_and_uv_venv():
    venv = os.path.join('C:\\', 'Projects', 'project-manager', '.venv')
    conda = os.path.join('C:\\', 'conda', 'envs', 'py310')
    environ = {
        'PATH': os.pathsep.join([os.path.join(venv, 'Scripts'), conda, os.path.join('C:\\', 'Windows')]),
        'VIRTUAL_ENV': venv, 'UV': 'uv.exe', 'UV_RUN_RECURSION_DEPTH': '1',
        'CLAUDECODE': '1', 'CLAUDE_CODE_CHILD_SESSION': '1',
        'CONDA_DEFAULT_ENV': 'py310', 'HOME': 'h',
    }
    env = AgentTab.child_env(environ, 'tab1')
    assert env['PATH'].split(os.pathsep) == [conda, os.path.join('C:\\', 'Windows')]
    for key in ('VIRTUAL_ENV', 'UV', 'UV_RUN_RECURSION_DEPTH', 'CLAUDECODE', 'CLAUDE_CODE_CHILD_SESSION'):
        assert key not in env
    assert env['CONDA_DEFAULT_ENV'] == 'py310'
    assert env['OVERSEER_TAB'] == 'tab1'
    # 원래 환경은 건드리지 않는다
    assert 'VIRTUAL_ENV' in environ


def test_child_env_without_venv_keeps_path():
    env = AgentTab.child_env({'PATH': 'a;b'}, 't')
    assert env['PATH'] == 'a;b'


def test_sync_records_moves_approved_keep_items_once(tmp_path):
    import json
    from project_manager.l0.decision_store import DecisionStore
    from project_manager.l0.record_store import RecordStore
    captures = tmp_path / 'captures'
    captures.mkdir()
    items = [
        {'kind': '제안', 'tag': 'D', 'title': '가격은 새 값으로', 'body': '근거: #1-1'},
        {'kind': 'W', 'title': '사안: 결정 단위', 'body': ''},                      # 예전 형식
        {'kind': '제안', 'tag': 'D', 'title': '기각될 기록', 'body': ''},
        {'kind': '제안', 'title': '보통 제안', 'body': ''},
        {'kind': '제안', 'tag': 'D', 'title': '가격은 유지', 'body': '근거: #1-2\n대체: D-1'},
    ]
    (captures / 't.jsonl').write_text(json.dumps({'event': 'turn', 'session_id': 's', 'text': 'x', 'items': items}, ensure_ascii=False) + '\n',
                                      encoding='utf-8')
    store, records = DecisionStore(tmp_path / 'o.db'), RecordStore(tmp_path / 'o.db')
    store.add_message('t', 'm', [('1-1', 'approve', ''), ('1-2', 'answer', '카드와 섞지 말 것'), ('1-3', 'reject', '아님'), ('1-4', 'approve', '')])
    tab = AgentTab('t', str(tmp_path / 'proj'), '', store, captures, records)
    assert [(r['ref'], r['text'], r['note']) for r in tab.state()['records']] == [('D-1', '가격은 새 값으로', ''), ('W-1', '사안: 결정 단위', '카드와 섞지 말 것')]

    store.add_message('t', 'm2', [('1-5', 'approve', '')])
    tab.sync_records()
    tab.sync_records()
    rows = {r['ref']: r for r in tab.state()['records']}
    assert set(rows) == {'D-1', 'W-1', 'D-2'}
    assert rows['D-1']['status'] == 'replaced' and rows['D-2']['replaces'] == rows['D-1']['id']


def test_close_held_and_takeover_of_held_item(tmp_path):
    import json
    from project_manager.l0.decision_store import DecisionStore
    captures = tmp_path / 'captures'
    captures.mkdir()
    turn1 = [{'kind': '제안', 'title': '전역 상태 분리', 'body': ''}, {'kind': '질문', 'title': '로그 위치', 'body': ''}]
    turn2 = [{'kind': '제안', 'title': '전역 상태 분리, 범위 줄여서', 'body': '', 'parent': '1-1'}]
    rows = [{'event': 'turn', 'session_id': 's', 'text': 'x', 'items': turn1},
            {'event': 'turn', 'session_id': 's', 'text': 'y', 'items': turn2}]
    (captures / 't.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows), encoding='utf-8')
    store = DecisionStore(tmp_path / 'o.db')
    store.add_message('t', 'm', [('1-1', 'hold', ''), ('1-2', 'hold', '')])
    tab = AgentTab('t', str(tmp_path), '', store, captures)
    assert tab.held() == {'1-1', '1-2'}

    # 이어받은 사안을 처리하면 원래 보류 사안을 닫는다
    assert tab.takeovers([('2-1', 'approve', '')]) == [('1-1', 'close', '#2-1 로 이어짐')]
    # 보류 사안 자체를 같이 처리하면 닫지 않는다
    assert tab.takeovers([('2-1', 'approve', ''), ('1-1', 'reject', '')]) == []

    # 보류함에서 닫기는 보류 중인 것만
    assert tab.close_held(['1-2', '2-1']) == ['1-2']
    assert store.sent('t')['1-2'] == {'action': 'close', 'note': ''}
    assert tab.held() == {'1-1'}


def test_clear_saves_decisions_locally_holds_rest_and_types_clear(tmp_path):
    import asyncio
    import json
    from project_manager.l0.decision_store import DecisionStore
    from project_manager.l0.record_store import RecordStore
    captures = tmp_path / 'captures'
    captures.mkdir()
    items = [{'kind': '제안', 'tag': 'D', 'title': '이전 판도 계속 공개', 'body': '근거: #1-1'},
             {'kind': '제안', 'tag': 'W', 'title': '판: 게시 시각 번호', 'body': ''},
             {'kind': '제안', 'title': '/clear 권함', 'body': ''}]
    (captures / 't.jsonl').write_text(json.dumps({'event': 'turn', 'session_id': 's', 'text': 'x', 'items': items}, ensure_ascii=False) + '\n',
                                      encoding='utf-8')
    store, records = DecisionStore(tmp_path / 'o.db'), RecordStore(tmp_path / 'o.db')
    tab = AgentTab('t', str(tmp_path / 'proj'), '', store, captures, records)

    class FakePty:
        alive = True
        typed = []

        def write(self, data):
            self.typed.append(data)

    tab.pty = FakePty()
    held = asyncio.run(tab.clear([('1-1', 'approve', ''), ('1-3', 'approve', '')]))
    # 처리하지 않은 사안은 보류로 넘긴다
    assert held == ['1-2']
    assert store.sent('t') == {'1-1': {'action': 'approve', 'note': ''}, '1-3': {'action': 'approve', 'note': ''},
                               '1-2': {'action': 'hold', 'note': ''}}
    # 에이전트에게 메시지는 가지 않는다
    assert store.last_message('t') is None
    # 승인한 보존 사안은 기록이 된다
    assert [r['ref'] for r in tab.state()['records']] == ['D-1']
    assert FakePty.typed == ['/clear', '\r']
