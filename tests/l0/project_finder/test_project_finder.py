import os
import time

import pytest

from project_manager.l0.project_finder import ProjectFinder


def drive(tmp_path, name):
    d = tmp_path / name
    d.mkdir()
    return str(d)


def test_scan_lists_projects_roots_recent_first(tmp_path):
    a, b = drive(tmp_path, 'A'), drive(tmp_path, 'B')
    root = tmp_path / 'A' / 'Projects'
    for i, n in enumerate(['old', 'new', '.hidden']):
        (root / n).mkdir(parents=True)
        os.utime(root / n, (time.time() - 100 + i * 10,) * 2)
    finder = ProjectFinder(drives=[a, b])
    assert finder.roots() == [root]
    assert [d['name'] for d in finder.scan()[0]['dirs']] == ['new', 'old']


def test_create_inside_root_and_default_root_when_none(tmp_path):
    a = drive(tmp_path, 'A')
    finder = ProjectFinder(drives=[a])
    assert finder.scan() == []
    # Projects 가 없으면 첫 드라이브에 만든다
    path = finder.create(str(finder.default_root()), '새 프로젝트')
    assert path.is_dir() and path.parent.name == 'Projects'
    assert finder.create(str(finder.default_root()), '새 프로젝트') == path

    with pytest.raises(ValueError):
        finder.create(str(finder.default_root()), '../밖')
    with pytest.raises(ValueError):
        finder.create(str(tmp_path), 'x')
