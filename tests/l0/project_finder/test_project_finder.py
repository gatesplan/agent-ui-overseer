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
    assert all(d['group'] is None for d in finder.scan()[0]['dirs'])


def test_fixed_roots_replace_drive_scan(tmp_path):
    a = drive(tmp_path, 'A')
    (tmp_path / 'A' / 'Projects' / 'x').mkdir(parents=True)
    code = tmp_path / 'code'
    (code / 'mine').mkdir(parents=True)
    finder = ProjectFinder(drives=[a], roots=[str(code), str(tmp_path / 'none')])
    assert finder.roots() == [code]
    assert [d['name'] for d in finder.scan()[0]['dirs']] == ['mine']
    assert finder.create(str(code), 'new') == code / 'new'

    # 정한 루트가 아직 없으면 첫 루트에 만든다
    later = tmp_path / 'later'
    finder = ProjectFinder(drives=[a], roots=[str(later)])
    assert finder.default_root() == later
    assert finder.create(str(later), 'p').is_dir()


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


def test_group_folder_lists_projects_inside(tmp_path):
    a = drive(tmp_path, 'A')
    root = tmp_path / 'A' / 'Projects'
    (root / 'solo' / '.git').mkdir(parents=True)
    (root / 'gatesplan' / 'mathgate' / '.git').mkdir(parents=True)
    (root / 'gatesplan' / 'auth').mkdir()
    (root / 'gatesplan' / 'auth' / 'CLAUDE.md').write_text('x', encoding='utf-8')
    (root / 'gatesplan' / 'labs').mkdir()                      # 표식 없음: 묶음 안에서는 보이지 않는다
    (root / 'solo' / 'inner' / '.git').mkdir(parents=True)     # 프로젝트 안은 들여다보지 않는다
    dirs = ProjectFinder(drives=[a]).scan()[0]['dirs']
    entries = {(d['group'], d['name']) for d in dirs}
    assert entries == {(None, 'solo'), (None, 'gatesplan'), ('gatesplan', 'mathgate'), ('gatesplan', 'auth')}
    # 묶음 폴더 바로 뒤에 그 안의 프로젝트가 온다
    names = [d['name'] for d in dirs]
    assert names.index('gatesplan') < names.index('mathgate') and names.index('gatesplan') < names.index('auth')
