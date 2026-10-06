from project_manager.l0.decision_store import DecisionStore


def test_tabs_messages_decisions_and_drafts(tmp_path):
    store = DecisionStore(tmp_path / 'o.db')
    store.add_tab('t1', 'C:/p', '--x')
    store.add_tab('t2', 'C:/q')
    store.close_tab('t2')
    assert [t['id'] for t in store.open_tabs()] == ['t1']

    store.add_message('t1', '첫 메시지', [('1-1', 'hold', ''), ('1-2', 'reject', '범위 밖')])
    store.add_message('t1', '둘째', [('1-1', 'approve', '')])
    assert store.sent('t1') == {'1-1': {'action': 'approve', 'note': ''}, '1-2': {'action': 'reject', 'note': '범위 밖'}}
    assert store.last_message('t1')['text'] == '둘째'
    assert store.sent('t2') == {}

    assert store.draft('t1') == {}
    store.save_draft('t1', {'extra': '가'})
    store.save_draft('t1', {'extra': '나'})
    assert store.draft('t1') == {'extra': '나'}
