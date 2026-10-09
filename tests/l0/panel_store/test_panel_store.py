from project_manager.l0.panel_store import PanelStore


def test_tabs_messages_and_drafts(tmp_path):
    store = PanelStore(tmp_path / 'o.db')
    store.add_tab('t1', 'C:/p', '--x')
    store.add_tab('t2', 'C:/q')
    store.close_tab('t2')
    assert [t['id'] for t in store.open_tabs()] == ['t1']
    assert [t['id'] for t in store.tabs()] == ['t1', 't2']

    first = store.add_message('t1', '첫 메시지')
    second = store.add_message('t1', '둘째')
    assert second > first
    assert store.last_message('t1')['text'] == '둘째'
    assert store.last_message('t2') is None

    assert store.draft('t1') == {}
    store.save_draft('t1', {'extra': '가'})
    store.save_draft('t1', {'extra': '나'})
    assert store.draft('t1') == {'extra': '나'}
