import json
import threading

import pytest

from project_manager.l0.permission_gate import PermissionGate


def test_wait_returns_decision_written_by_server(tmp_path):
    gate = PermissionGate(tmp_path, port=None, timeout=5, interval=0.05)
    rid = gate.new_id()
    threading.Timer(0.2, gate.decide, args=(rid, 'deny', '지우지 마')).start()
    decision = gate.wait(rid)
    assert decision == {'behavior': 'deny', 'message': '지우지 마'}
    assert not list(tmp_path.iterdir())
    out = json.loads(gate.hook_output(decision))
    assert out['hookSpecificOutput'] == {'hookEventName': 'PermissionRequest', 'decision': {'behavior': 'deny', 'message': '지우지 마'}}


def test_timeout_terminal_and_allow_outputs(tmp_path):
    gate = PermissionGate(tmp_path, port=None, timeout=0.2, interval=0.05)
    assert gate.wait(gate.new_id()) is None
    assert gate.hook_output(None) == ''
    assert gate.hook_output({'behavior': 'terminal'}) == ''
    assert json.loads(gate.hook_output({'behavior': 'allow'}))['hookSpecificOutput']['decision'] == {'behavior': 'allow'}


def test_not_ready_without_server_and_bad_input(tmp_path):
    assert PermissionGate(tmp_path, port=None).ready() is False
    assert PermissionGate(tmp_path, port=1).ready() is False
    gate = PermissionGate(tmp_path, port=None)
    with pytest.raises(ValueError):
        gate.decide('../x', 'allow')
    with pytest.raises(ValueError):
        gate.decide(gate.new_id(), 'maybe')
