import asyncio
import json
import os

import pytest

from project_manager.l0.panel_store import PanelStore
from project_manager.l0.project_journal import ProjectJournal
from project_manager.l0.record_store import RecordStore
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
    env = AgentTab.child_env(environ, 'tab1', 'C:\\p')
    assert env['PATH'].split(os.pathsep) == [conda, os.path.join('C:\\', 'Windows')]
    for key in ('VIRTUAL_ENV', 'UV', 'UV_RUN_RECURSION_DEPTH', 'CLAUDECODE', 'CLAUDE_CODE_CHILD_SESSION'):
        assert key not in env
    assert env['CONDA_DEFAULT_ENV'] == 'py310'
    assert (env['OVERSEER_TAB'], env['OVERSEER_PROJECT']) == ('tab1', 'C:\\p')
    # 원래 환경은 건드리지 않는다
    assert 'VIRTUAL_ENV' in environ


def test_child_env_without_venv_keeps_path():
    env = AgentTab.child_env({'PATH': 'a;b'}, 't')
    assert env['PATH'] == 'a;b'
    assert 'OVERSEER_PROJECT' not in env


# 탭 't' 가 프로젝트에서 세션 1 을 받고, 응답(turns)이 온 캡처 기록
def setup(tmp_path, *turns):
    captures = tmp_path / 'captures'
    captures.mkdir()
    project = tmp_path / 'proj'
    project.mkdir()
    n = ProjectJournal(RecordStore.project_key(str(project))).open_session('s', 't', 'startup')
    rows = [{'event': 'session_start', 'session_id': 's', 'source': 'startup', 'session': n}]
    rows += [{'event': 'turn', 'session_id': 's', 'text': 'x', 'items': items, 'at': f'2001-01-0{k}T00:00:00+00:00'}
             for k, items in enumerate(turns, 1)]
    (captures / 't.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows), encoding='utf-8')
    return captures, str(project), PanelStore(tmp_path / 'o.db')


class FakePty:
    alive = True

    def __init__(self):
        self.typed = []

    def write(self, data):
        self.typed.append(data)

    def paste(self, text):
        self.typed.append(text)


def test_turns_and_decisions_go_to_the_project_journal(tmp_path):
    captures, project, store = setup(tmp_path, [{'kind': '제안', 'title': '가', 'body': ''}])
    tab = AgentTab('t', project, '', store, captures)
    journal = ProjectJournal(RecordStore.project_key(project))
    assert [t['id'] for t in journal.turns(1)] == ['1S-1']
    tab.pty = FakePty()
    asyncio.run(tab.send('보낸 말', [('1S-1-1', 'approve', '좋다')]))
    assert journal.sent() == {'1S-1-1': {'action': 'approve', 'note': '좋다', 'at': journal.sent()['1S-1-1']['at']}}
    assert journal.decisions()[0]['message'] == store.last_message('t')['id']
    assert tab.state()['sent']['1S-1-1']['action'] == 'approve'


def test_turns_of_a_session_this_tab_did_not_open_are_not_written(tmp_path):
    captures, project, store = setup(tmp_path, [{'kind': '제안', 'title': '가', 'body': ''}])
    # 번호를 받지 못한 훅 기록: 세션 번호가 없어 /clear 를 세어 2 가 된다. 세션 2 는 다른 탭의 것
    ProjectJournal(RecordStore.project_key(project)).open_session('other', 'u', 'startup')
    with (captures / 't.jsonl').open('a', encoding='utf-8') as f:
        f.write(json.dumps({'event': 'session_start', 'session_id': 's2', 'source': 'clear'}) + '\n')
        f.write(json.dumps({'event': 'turn', 'session_id': 's2', 'text': 'y', 'items': [{'kind': '보고', 'title': '나', 'body': ''}]}) + '\n')
    AgentTab('t', project, '', store, captures)
    assert ProjectJournal(RecordStore.project_key(project)).turns(2) == []


def test_sync_records_moves_approved_keep_items_once(tmp_path):
    items = [
        {'kind': '제안', 'tag': 'D', 'title': '가격은 새 값으로', 'body': '근거: #1S-1-1'},
        {'kind': 'W', 'title': '사안: 결정 단위', 'body': ''},                      # 예전 형식
        {'kind': '제안', 'tag': 'D', 'title': '기각될 기록', 'body': ''},
        {'kind': '제안', 'title': '보통 제안', 'body': ''},
        {'kind': '제안', 'tag': 'D', 'title': '가격은 유지', 'body': '근거: #1S-1-2\n대체: D-1'},
    ]
    captures, project, store = setup(tmp_path, items)
    journal = ProjectJournal(RecordStore.project_key(project))
    journal.add_decisions([('1S-1-1', 'approve', ''), ('1S-1-2', 'answer', '카드와 섞지 말 것'), ('1S-1-3', 'reject', '아님'), ('1S-1-4', 'approve', '')])
    tab = AgentTab('t', project, '', store, captures, RecordStore())
    assert [(r['ref'], r['text'], r['note']) for r in tab.state()['records']] == [('D-1', '가격은 새 값으로', ''), ('W-1', '사안: 결정 단위', '카드와 섞지 말 것')]

    journal.add_decisions([('1S-1-5', 'approve', '')])
    tab.sync_records()
    tab.sync_records()
    rows = {r['ref']: r for r in tab.state()['records']}
    assert set(rows) == {'D-1', 'W-1', 'D-2'}
    assert rows['D-1']['status'] == 'replaced' and rows['D-2']['replaces'] == 'D-1'
    assert rows['D-2']['item_id'] == '1S-1-5' and rows['D-2']['tab_id'] == 't'


def test_close_held_and_takeover_of_held_item(tmp_path):
    turn1 = [{'kind': '제안', 'title': '전역 상태 분리', 'body': ''}, {'kind': '질문', 'title': '로그 위치', 'body': ''}]
    turn2 = [{'kind': '제안', 'title': '전역 상태 분리, 범위 줄여서', 'body': '', 'parent': '1S-1-1'}]
    captures, project, store = setup(tmp_path, turn1, turn2)
    tab = AgentTab('t', project, '', store, captures)
    tab.journal.add_decisions([('1S-1-1', 'hold', ''), ('1S-1-2', 'hold', '')])
    assert tab.held() == {'1S-1-1', '1S-1-2'}

    # 이어받은 사안을 처리하면 원래 보류 사안을 닫는다
    assert tab.takeovers([('1S-2-1', 'approve', '')]) == [('1S-1-1', 'close', '#1S-2-1 로 이어짐')]
    # 보류 사안 자체를 같이 처리하면 닫지 않는다
    assert tab.takeovers([('1S-2-1', 'approve', ''), ('1S-1-1', 'reject', '')]) == []

    # 보류함에서 닫기는 보류 중인 것만
    assert tab.close_held(['1S-1-2', '1S-2-1']) == ['1S-1-2']
    assert tab.sent()['1S-1-2']['action'] == 'close'
    assert tab.held() == {'1S-1-1'}


def test_clear_saves_decisions_locally_holds_rest_and_types_clear(tmp_path):
    items = [{'kind': '제안', 'tag': 'D', 'title': '이전 판도 계속 공개', 'body': '근거: #1S-1-1'},
             {'kind': '제안', 'tag': 'W', 'title': '판: 게시 시각 번호', 'body': ''},
             {'kind': '제안', 'title': '/clear 권함', 'body': ''}]
    captures, project, store = setup(tmp_path, items)
    tab = AgentTab('t', project, '', store, captures, RecordStore())
    tab.pty = FakePty()
    held = asyncio.run(tab.clear([('1S-1-1', 'approve', ''), ('1S-1-3', 'approve', '')]))
    # 처리하지 않은 사안은 보류로 넘긴다
    assert held == ['1S-1-2']
    assert {k: v['action'] for k, v in tab.sent().items()} == {'1S-1-1': 'approve', '1S-1-3': 'approve', '1S-1-2': 'hold'}
    # 에이전트에게 메시지는 가지 않는다
    assert store.last_message('t') is None
    # 승인한 보존 사안은 기록이 된다
    assert [r['ref'] for r in tab.state()['records']] == ['D-1']
    assert tab.pty.typed == ['/clear', '\r']


def test_note_map_records_responsibility_changes_and_user_requests(tmp_path):
    captures, project, store = setup(tmp_path, [{'kind': '보고', 'title': '가', 'body': ''}])
    tab = AgentTab('t', project, '', store, captures)

    def result(**resp):
        return {'status': 'ok', 'map': {'modules': [{'name': k.replace('_', '.', 1), 'responsibility': v} for k, v in resp.items()]}}

    before = result(l1_a='옛 책임', l1_b='그대로', l0_c='')
    # 지도를 처음 받은 때(앞 지도 없음)나 읽지 못한 지도는 비교하지 않는다
    assert tab.note_map(None, before) == [] and tab.note_map(before, {'status': 'error'}) == []
    # 마지막 턴보다 앞에 보낸 메시지는 이번 변경의 요청이 아니다
    store.db.execute("insert into messages (tab_id, text, created_at) values ('t', '[책임 수정] l1.a: 옛 요청', '2000-01-01T00:00:00+00:00')")
    store.db.commit()
    events = tab.note_map(before, result(l1_a='새 책임', l1_b='그대로', l0_c=''))
    assert [(e['module'], e['before'], e['after'], e['request'], e['turn']) for e in events] == [('l1.a', '옛 책임', '새 책임', None, '1S-1')]

    store.add_message('t', '확인: #1S-1-1 사안 종료됨.\n[책임 수정] l1.a: 더 새 책임\n[새 책임 카드] d: 새 일을 맡는다 → 타당성을 [제안]으로 올린다')
    events = tab.note_map(result(l1_a='새 책임', l1_b='그대로', l0_c=''),
                          result(l1_a='더 새 책임', l1_b='그대로', l0_c='', l2_d='새 일을 맡는다', l2_e=''))
    assert [(e['module'], e['before'], e['request']) for e in events] == [('l1.a', '새 책임', '더 새 책임'), ('l2.d', None, '새 일을 맡는다')]
    history = tab.state()['moduleHistory']
    assert [e['after'] for e in history['l1.a']] == ['새 책임', '더 새 책임']


def test_starting_until_session_start_after_launch_blocks_send(tmp_path):
    captures, project, store = setup(tmp_path)
    log = captures / 't.jsonl'
    tab = AgentTab('t', project, '', store, captures)

    # 띄우기 전(복원 직후)은 시작 중이 아니다
    tab.pty = FakePty()
    assert tab.starting is False
    tab.log.poll()
    tab._start_seq = len(tab.log.events)
    assert tab.state()['starting'] is True
    with pytest.raises(RuntimeError):
        asyncio.run(tab.send('hi', []))
    with pytest.raises(RuntimeError):
        asyncio.run(tab.clear([]))
    assert tab.pty.typed == []

    with log.open('a', encoding='utf-8') as f:
        f.write(json.dumps({'event': 'session_start', 'session_id': 's', 'source': 'resume', 'session': 1}) + '\n')
    tab.poll()
    assert tab.starting is False
    asyncio.run(tab.send('hi', []))
    assert tab.pty.typed == ['hi', '\r']
