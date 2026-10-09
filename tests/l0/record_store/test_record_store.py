import pytest

from project_manager.l0.record_store import RecordStore


def test_numbering_per_project_and_kind_and_idempotent_add(tmp_path):
    store = RecordStore()
    p, q = RecordStore.project_key(str(tmp_path / 'a')), RecordStore.project_key(str(tmp_path / 'b'))
    d1 = store.add(p, 'D', '가격은 새 값으로', tab_id='t', item_id='1S-2-1')
    w1 = store.add(p, 'W', '사안: 결정 단위', tab_id='t', item_id='1S-2-2')
    d2 = store.add(p, 'D', '로그는 INFO', tab_id='t', item_id='1S-2-3')
    other = store.add(q, 'D', '다른 프로젝트', tab_id='u', item_id='1S-1-1')
    assert [d1['ref'], w1['ref'], d2['ref'], other['ref']] == ['D-1', 'W-1', 'D-2', 'D-1']
    # 같은 사안을 다시 보내도 새 기록이 생기지 않는다
    assert store.add(p, 'D', '가격은 새 값으로', tab_id='t', item_id='1S-2-1')['ref'] == 'D-1'
    assert RecordStore.project_key('c:\\projects\\A') == RecordStore.project_key('C:/Projects/a')
    # 기록 하나가 파일 하나. 폴더는 git 에서 스스로 빠진다
    assert sorted(f.name for f in (tmp_path / 'a' / '.overseer' / 'records').iterdir()) == ['D-1.md', 'D-2.md', 'W-1.md']
    assert (tmp_path / 'a' / '.overseer' / '.gitignore').read_text(encoding='utf-8') == '*\n'


def test_file_round_trip_keeps_multiline_and_quoted_values(tmp_path):
    store = RecordStore()
    p = RecordStore.project_key(str(tmp_path))
    store.add(p, 'D', '"따옴표"로 시작하는 결정', body='근거: #1S-1-1\n\n본문 둘째 줄', note='한 줄\n두 줄', tab_id='t', item_id='1S-1-2')
    rec = store.find(p, 'D-1')
    assert (rec['text'], rec['note'], rec['body']) == ('"따옴표"로 시작하는 결정', '한 줄\n두 줄', '근거: #1S-1-1\n\n본문 둘째 줄')
    assert (rec['item_id'], rec['tab_id'], rec['status'], rec['replaces']) == ('1S-1-2', 't', 'active', None)
    text = (tmp_path / '.overseer' / 'records' / 'D-1.md').read_text(encoding='utf-8')
    assert text.startswith('---\ntext: "\\"따옴표\\"로 시작하는 결정"\nstatus: active\n')


def test_replace_marks_old_and_briefing_shows_only_active(tmp_path):
    store = RecordStore()
    p = RecordStore.project_key(str(tmp_path / 'p'))
    store.add(p, 'D', '가격은 새 값으로', tab_id='t', item_id='1S-1-1')
    store.add(p, 'W', '사안: 결정 단위', note='카드와 섞지 말 것', tab_id='t', item_id='1S-1-2')
    new = store.add(p, 'D', '가격은 기존 값 유지', tab_id='t', item_id='1S-3-1', replaces='D-1')
    old = store.find(p, 'D-1')
    assert (old['status'], old['replaced_by'], new['replaces']) == ('replaced', 'D-2', 'D-1')
    # 다른 종류나 이미 대체된 기록은 대체하지 않는다
    assert store.add(p, 'D', 'x', tab_id='t', item_id='1S-4-1', replaces='W-1')['replaces'] is None
    assert store.add(p, 'D', 'y', tab_id='t', item_id='1S-4-2', replaces='D-1')['replaces'] is None

    text = store.briefing(p)
    assert '- D-2 가격은 기존 값 유지' in text
    assert '- W-1 사안: 결정 단위 (메모: 카드와 섞지 말 것)' in text
    assert 'D-1 ' not in text
    assert store.briefing(RecordStore.project_key(str(tmp_path / 'empty'))) == ''
    with pytest.raises(ValueError):
        store.add(p, 'X', 'z')


def test_notice_lists_records_after_seen_point_from_other_tabs(tmp_path):
    store = RecordStore()
    p = RecordStore.project_key(str(tmp_path))
    assert store.last_mark(p) == ''
    store.add(p, 'D', '가격은 새 값으로', tab_id='a', item_id='1S-1-1')
    seen = store.last_mark(p)
    assert store.notice(p, seen) == ''
    store.add(p, 'W', '사안: 결정 단위', tab_id='b', item_id='2S-1-1')
    store.add(p, 'D', '가격은 유지', tab_id='b', item_id='2S-1-2', replaces='D-1')
    store.add(p, 'D', '내 탭 결정', tab_id='a', item_id='3S-1-1')
    text = store.notice(p, seen, exclude_tab='a')
    assert '- 추가: W-1 사안: 결정 단위' in text
    assert '- 변경: D-1 가격은 새 값으로 → D-2 가격은 유지' in text
    assert '내 탭 결정' not in text
    assert store.notice(p, store.last_mark(p), exclude_tab='a') == ''


def test_parent_folder_records_apply_to_child_projects(tmp_path):
    store = RecordStore()
    group = RecordStore.project_key(str(tmp_path / 'gatesplan'))
    child = RecordStore.project_key(str(tmp_path / 'gatesplan' / 'mathgate'))
    sibling = RecordStore.project_key(str(tmp_path / 'other'))
    store.add(group, 'D', '약관 원문은 마크다운', tab_id='g', item_id='1S-1-1')
    store.add(child, 'D', '채점은 서버에서', tab_id='m', item_id='1S-1-1')
    store.add(sibling, 'D', '관계없는 결정', tab_id='o', item_id='1S-1-1')

    refs = [r['ref'] for r in store.records_in_scope(child)]
    assert refs == ['D-1', 'gatesplan/D-1']
    text = store.briefing(child)
    assert '- D-1 채점은 서버에서' in text and '- gatesplan/D-1 약관 원문은 마크다운' in text
    assert '관계없는 결정' not in text
    # 상위 폴더 기록은 폴더 이름으로 찾는다
    assert store.find(child, 'gatesplan/D-1')['text'] == '약관 원문은 마크다운'
    assert store.find(child, 'D-1')['text'] == '채점은 서버에서'
    # 상위 폴더에서는 하위 기록이 보이지 않는다
    assert [r['ref'] for r in store.records_in_scope(group)] == ['D-1']
    # 변경 고지도 상위 폴더 기록까지
    seen = store.last_mark(child)
    store.add(group, 'W', '판: 문서 버전', tab_id='g', item_id='2S-1-1')
    assert '- 추가: gatesplan/W-1 판: 문서 버전' in store.notice(child, seen, exclude_tab='m')
