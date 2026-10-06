import pytest

from project_manager.l0.record_store import RecordStore


def test_numbering_per_project_and_kind_and_idempotent_add(tmp_path):
    store = RecordStore(tmp_path / 'o.db')
    p, q = RecordStore.project_key('C:/Projects/a'), RecordStore.project_key('C:/Projects/b')
    d1 = store.add(p, 'D', '가격은 새 값으로', tab_id='t', item_id='2-1')
    w1 = store.add(p, 'W', '사안: 결정 단위', tab_id='t', item_id='2-2')
    d2 = store.add(p, 'D', '로그는 INFO', tab_id='t', item_id='2-3')
    other = store.add(q, 'D', '다른 프로젝트', tab_id='u', item_id='1-1')
    assert [d1['ref'], w1['ref'], d2['ref'], other['ref']] == ['D-1', 'W-1', 'D-2', 'D-1']
    # 같은 사안을 다시 보내도 새 기록이 생기지 않는다
    assert store.add(p, 'D', '가격은 새 값으로', tab_id='t', item_id='2-1')['id'] == d1['id']
    assert RecordStore.project_key('c:\\projects\\A') == RecordStore.project_key('C:/Projects/a')


def test_replace_marks_old_and_briefing_shows_only_active(tmp_path):
    store = RecordStore(tmp_path / 'o.db')
    p = RecordStore.project_key('C:/p')
    store.add(p, 'D', '가격은 새 값으로', tab_id='t', item_id='1-1')
    store.add(p, 'W', '사안: 결정 단위', note='카드와 섞지 말 것', tab_id='t', item_id='1-2')
    new = store.add(p, 'D', '가격은 기존 값 유지', tab_id='t', item_id='3-1', replaces='D-1')
    old = store.find(p, 'D-1')
    assert (old['status'], old['replaced_by'], new['replaces']) == ('replaced', new['id'], old['id'])
    # 다른 종류나 이미 대체된 기록은 대체하지 않는다
    assert store.add(p, 'D', 'x', tab_id='t', item_id='4-1', replaces='W-1')['replaces'] is None
    assert store.add(p, 'D', 'y', tab_id='t', item_id='4-2', replaces='D-1')['replaces'] is None

    text = store.briefing(p)
    assert '- D-2 가격은 기존 값 유지' in text
    assert '- W-1 사안: 결정 단위 (메모: 카드와 섞지 말 것)' in text
    assert 'D-1 ' not in text
    assert store.briefing(RecordStore.project_key('C:/empty')) == ''
    with pytest.raises(ValueError):
        store.add(p, 'X', 'z')
