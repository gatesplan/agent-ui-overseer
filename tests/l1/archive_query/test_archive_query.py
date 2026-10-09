from project_manager.l0.project_journal import ProjectJournal
from project_manager.l0.record_store import RecordStore
from project_manager.l1.archive_query import ArchiveQuery


def write_session(project, items, decisions):
    j = ProjectJournal(project)
    n = j.open_session('s', 't1', 'startup')
    j.write_turn({'id': f'{n}S-1', 'session': n, 'turn': 1, 'at': '2026-10-09T01:00', 'prompt': '', 'preamble': '', 'files': [],
                  'items': [{**i, 'id': f'{n}S-1-{k}'} for k, i in enumerate(items, 1)]})
    j.add_decisions(decisions, 1)
    return j


def setup(tmp_path):
    cwd = str(tmp_path / 'proj')
    project = RecordStore.project_key(cwd)
    items = [
        {'kind': '질문', 'title': '같은 이름 추가 시 가격', 'body': 'A: 유지\nB: 덮어쓰기'},
        {'kind': '제안', 'title': '전역 상태를 클래스로', 'body': '범위가 크다'},
        {'kind': '제안', 'tag': 'D', 'title': '가격은 새 값으로', 'body': '근거: #1S-1-1'},
    ]
    write_session(project, items, [('1S-1-1', 'answer', 'B. 새 가격'), ('1S-1-2', 'reject', '지금은 범위 밖'), ('1S-1-3', 'approve', '')])
    records = RecordStore()
    records.add(project, 'D', '가격은 새 값으로', body='근거: #1S-1-1', tab_id='t1', item_id='1S-1-3')
    records.add(project, 'D', '가격은 기존 값 유지', tab_id='t9', item_id='1S-5-1', replaces='D-1')
    records.add(project, 'W', '사안: 결정 단위', note='카드와 섞지 말 것')
    return ArchiveQuery(records, cwd)


def test_list_records_filters(tmp_path):
    q = setup(tmp_path)
    assert q.list_records() == '- D-2 가격은 기존 값 유지\n- W-1 사안: 결정 단위 (메모: 카드와 섞지 말 것)'
    assert 'D-1 [대체됨]' in q.list_records(include_replaced=True)
    assert q.list_records(query='카드') == '- W-1 사안: 결정 단위 (메모: 카드와 섞지 말 것)'
    assert q.list_records(kind='w').startswith('- W-1')
    assert q.list_records(query='없는말') == '맞는 기록이 없다.'


def test_record_shows_chain_source_and_basis(tmp_path):
    q = setup(tmp_path)
    text = q.record('D-1')
    assert text.startswith('# D-1 (대체됨)')
    assert '- D-1 가격은 새 값으로 ← 지금' in text and '- D-2 가격은 기존 값 유지 [유효]' in text
    assert '## 원래 사안 #1S-1-3' in text
    assert '- #1S-1-1 [질문] 같은 이름 추가 시 가격 → 답변: B. 새 가격' in text
    assert q.record('D-2').count('← 지금') == 1
    assert q.record('D-9') == 'D-9 기록이 없다.'


def test_decisions_search_and_rejected_only(tmp_path):
    q = setup(tmp_path)
    rejected = q.decisions(action='reject')
    assert '#1S-1-2 [제안] 전역 상태를 클래스로 → 기각: 지금은 범위 밖' in rejected
    assert '#1S-1-1' not in rejected
    assert '#1S-1-1' in q.decisions(query='가격')
    assert q.decisions(query='없는말') == '맞는 사안이 없다.'


def test_child_project_sees_parent_records_and_decisions(tmp_path):
    group, child = tmp_path / 'gatesplan', tmp_path / 'gatesplan' / 'mathgate'
    write_session(RecordStore.project_key(str(group)), [{'kind': '제안', 'title': '약관을 각 서비스에 복사', 'body': ''}],
                  [('1S-1-1', 'reject', '중앙에서 관리')])
    records = RecordStore()
    records.add(RecordStore.project_key(str(group)), 'D', '약관은 auth 가 중앙 관리')
    q = ArchiveQuery(records, str(child))
    assert q.list_records() == '- gatesplan/D-1 약관은 auth 가 중앙 관리'
    assert q.record('gatesplan/D-1').startswith('# gatesplan/D-1 (유효)')
    assert '#gatesplan/1S-1-1 [제안] 약관을 각 서비스에 복사 → 기각: 중앙에서 관리' in q.decisions(action='reject')


def test_module_history_and_mentioning_records(tmp_path):
    cwd = str(tmp_path / 'proj')
    project = RecordStore.project_key(cwd)
    j = ProjectJournal(project)
    n = j.open_session('s', 't', 'startup')
    j.add_module_change(n, {'module': 'l1.item_splitter', 'before': None, 'after': '응답을 나눈다', 'request': None, 'turn': None})
    j.add_module_change(n, {'module': 'l1.item_splitter', 'before': '응답을 나눈다', 'after': '응답을 사안 단위로 나눈다',
                            'request': '응답을 사안 단위로 나눈다', 'turn': '1S-2'})
    records = RecordStore()
    records.add(project, 'D', 'item_splitter 는 제목 줄만 본다')
    q = ArchiveQuery(records, cwd)
    text = q.module('item_splitter')
    assert '# l1.item_splitter 책임 이력' in text
    assert '(새 모듈) → 응답을 나눈다 [에이전트나 직접 편집]' in text
    assert '1S-2 뒤: 응답을 나눈다 → 응답을 사안 단위로 나눈다 [사용자 요청: 응답을 사안 단위로 나눈다]' in text
    assert '- D-1 item_splitter 는 제목 줄만 본다' in text
    assert q.module('없는모듈') == '없는모듈 에 대한 책임 이력과 기록이 없다.'
