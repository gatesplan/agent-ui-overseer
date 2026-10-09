import json

from project_manager.l0.decision_store import DecisionStore
from project_manager.l0.record_store import RecordStore
from project_manager.l1.archive_query import ArchiveQuery


def setup(tmp_path):
    captures = tmp_path / 'captures'
    captures.mkdir()
    cwd = str(tmp_path / 'proj')
    items = [
        {'kind': '질문', 'title': '같은 이름 추가 시 가격', 'body': 'A: 유지\nB: 덮어쓰기'},
        {'kind': '제안', 'title': '전역 상태를 클래스로', 'body': '범위가 크다'},
        {'kind': '제안', 'tag': 'D', 'title': '가격은 새 값으로', 'body': '근거: #1S-1-1'},
    ]
    (captures / 't1.jsonl').write_text(json.dumps({'event': 'turn', 'session_id': 's', 'text': 'x', 'items': items}, ensure_ascii=False) + '\n',
                                       encoding='utf-8')
    store, records = DecisionStore(tmp_path / 'o.db'), RecordStore(tmp_path / 'o.db')
    store.add_tab('t1', cwd)
    store.add_tab('other', str(tmp_path / 'elsewhere'))
    store.add_message('t1', 'm', [('1S-1-1', 'answer', 'B. 새 가격'), ('1S-1-2', 'reject', '지금은 범위 밖'), ('1S-1-3', 'approve', '')])
    project = RecordStore.project_key(cwd)
    records.add(project, 'D', '가격은 새 값으로', body='근거: #1S-1-1', tab_id='t1', item_id='1S-1-3')
    records.add(project, 'D', '가격은 기존 값 유지', tab_id='t9', item_id='1S-5-1', replaces='D-1')
    records.add(project, 'W', '사안: 결정 단위', note='카드와 섞지 말 것')
    return ArchiveQuery(store, records, captures, cwd)


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
    assert q.record('D-9') == 'D-9 기록이 없다.'


def test_decisions_search_and_rejected_only(tmp_path):
    q = setup(tmp_path)
    rejected = q.decisions(action='reject')
    assert '#1S-1-2 [제안] 전역 상태를 클래스로 → 기각: 지금은 범위 밖' in rejected
    assert '#1S-1-1' not in rejected
    assert '#1S-1-1' in q.decisions(query='가격')
    assert q.decisions(query='없는말') == '맞는 사안이 없다.'


def test_child_project_sees_parent_records_and_decisions(tmp_path):
    captures = tmp_path / 'captures'
    captures.mkdir()
    group, child = tmp_path / 'gatesplan', tmp_path / 'gatesplan' / 'mathgate'
    items = [{'kind': '제안', 'title': '약관을 각 서비스에 복사', 'body': ''}]
    (captures / 'g.jsonl').write_text(json.dumps({'event': 'turn', 'session_id': 's', 'text': 'x', 'items': items}, ensure_ascii=False) + '\n',
                                      encoding='utf-8')
    store, records = DecisionStore(tmp_path / 'o.db'), RecordStore(tmp_path / 'o.db')
    store.add_tab('g', str(group))
    store.add_message('g', 'm', [('1S-1-1', 'reject', '중앙에서 관리')])
    records.add(RecordStore.project_key(str(group)), 'D', '약관은 auth 가 중앙 관리')
    q = ArchiveQuery(store, records, captures, str(child))
    assert q.list_records() == '- gatesplan/D-1 약관은 auth 가 중앙 관리'
    assert q.record('gatesplan/D-1').startswith('# gatesplan/D-1 (유효)')
    assert '약관을 각 서비스에 복사 → 기각: 중앙에서 관리' in q.decisions(action='reject')
