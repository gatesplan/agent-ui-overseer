import os

from project_manager.l0.project_key import ProjectKey


def test_same_folder_same_key(tmp_path, monkeypatch):
    assert ProjectKey.of('c:\\projects\\A') == ProjectKey.of('C:/Projects/a')
    # 상대 경로도 지금 폴더 기준의 같은 키가 된다
    monkeypatch.chdir(tmp_path)
    assert ProjectKey.of('a') == ProjectKey.of(str(tmp_path / 'a'))
    assert ProjectKey.of(str(tmp_path / 'a')) != ProjectKey.of(str(tmp_path / 'b'))
    assert os.path.isabs(ProjectKey.of('a'))
