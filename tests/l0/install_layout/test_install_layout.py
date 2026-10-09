from project_manager.l0.install_layout import InstallLayout


def test_repository_layout_points_to_web_docs_scripts():
    layout = InstallLayout()
    assert not layout.installed
    assert (layout.web / 'index.html').is_file()
    assert layout.protocol.name == 'item-protocol.md' and layout.protocol.is_file()
    assert layout.hook_script.is_file() and layout.mcp_script.is_file()


def test_installed_layout_uses_assets_inside_package(tmp_path):
    package = tmp_path / 'site-packages' / 'project_manager'
    (package / '_assets' / 'web').mkdir(parents=True)
    layout = InstallLayout(package)
    assert layout.installed
    assert layout.web == package / '_assets' / 'web'
    assert layout.protocol == package / '_assets' / 'item-protocol.md'
    assert layout.hook_script == package / '_assets' / 'scripts' / 'capture_hook.py'


def test_data_folder_from_env_or_home(monkeypatch, tmp_path):
    monkeypatch.setenv('OVERSEER_DATA', str(tmp_path))
    assert InstallLayout.data() == tmp_path
    monkeypatch.delenv('OVERSEER_DATA')
    assert InstallLayout.data().name == '.overseer'
