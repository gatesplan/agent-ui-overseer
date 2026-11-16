import json

from project_manager.l1.hook_installer import HookInstaller


def _installer(settings, version):
    installer = HookInstaller(settings=settings)
    installer._version = version
    return installer


def test_write_hooks_keeps_others_and_registers_once(tmp_path):
    settings = tmp_path / 'settings.json'
    other = {'hooks': [{'type': 'command', 'command': 'lnt hook session-start'}]}
    settings.write_text(json.dumps({'model': 'x', 'hooks': {'SessionStart': [other]}}), encoding='utf-8')
    installer = _installer(settings, (2, 1, 325))
    installer.write_hooks(remove=False)
    installer.write_hooks(remove=False)
    data = json.loads(settings.read_text(encoding='utf-8'))
    assert data['model'] == 'x'
    start = data['hooks']['SessionStart']
    assert start[0] == other and len(start) == 2
    assert 'capture_hook.py' in start[1]['hooks'][0]['command']
    assert data['hooks']['PermissionRequest'][0]['hooks'][0]['timeout'] == 1800
    assert data['hooks']['Stop'][0]['hooks'][0]['timeout'] == 30
    assert 'capture_hook.py' in data['hooks']['StopFailure'][0]['hooks'][0]['command']
    assert (tmp_path / 'settings.json.bak-overseer').exists()

    installer.write_hooks(remove=True)
    data = json.loads(settings.read_text(encoding='utf-8'))
    assert data['hooks'] == {'SessionStart': [other]}


def test_stop_failure_only_on_versions_that_know_it(tmp_path):
    # 2.1.78 전 판은 모르는 훅 이름이 있으면 설정 파일 전체를 무시한다. 예전에 건 우리 StopFailure 는 지운다
    settings = tmp_path / 'settings.json'
    _installer(settings, (2, 1, 325)).write_hooks(remove=False)
    for version in ((2, 1, 50), ()):
        _installer(settings, version).write_hooks(remove=False)
        hooks = json.loads(settings.read_text(encoding='utf-8'))['hooks']
        assert 'StopFailure' not in hooks and 'Stop' in hooks


def test_hook_command_uses_console_python_not_pythonw(tmp_path, monkeypatch):
    import sys
    monkeypatch.setattr(sys, 'executable', str(tmp_path / 'Scripts' / 'pythonw.exe'))
    assert HookInstaller(settings=tmp_path / 's.json').python == tmp_path / 'Scripts' / 'python.exe'
