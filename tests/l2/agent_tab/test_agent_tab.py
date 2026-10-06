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
