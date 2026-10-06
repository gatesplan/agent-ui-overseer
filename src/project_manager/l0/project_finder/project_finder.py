import os
import re
import string
from pathlib import Path

# 폴더 이름에 쓸 수 없는 글자(Windows)
BAD_NAME = re.compile(r'[\\/:*?"<>|]')


# 새 세션 창의 폴더 목록. 프로젝트 루트(기본: 드라이브마다 루트의 Projects 폴더) 안의 폴더를 보여 주고 새 폴더를 만든다
class ProjectFinder:
    def __init__(self, folder: str = 'Projects', drives: list[str] | None = None, roots: list[str] | None = None):
        self.folder = folder
        self.drives = drives if drives is not None else [f'{d}:\\' for d in string.ascii_uppercase]
        # 직접 정한 프로젝트 루트. 있으면 드라이브를 훑지 않는다
        self.fixed = [Path(r).expanduser() for r in roots] if roots else None

    def roots(self) -> list[Path]:
        if self.fixed is not None:
            return [r for r in self.fixed if r.is_dir()]
        return [Path(d) / self.folder for d in self.drives if (Path(d) / self.folder).is_dir()]

    # 새 폴더를 만들 기본 위치. 루트가 하나도 없으면 첫 후보(정한 루트, 아니면 첫 드라이브의 Projects)에 만들 자리
    def default_root(self) -> Path:
        roots = self.roots()
        if roots:
            return roots[0]
        return self.fixed[0] if self.fixed else Path(self.drives[0]) / self.folder

    # [{root, dirs: [{name, path}]}]. 폴더는 최근 수정 순, 점으로 시작하는 폴더는 뺀다
    def scan(self) -> list[dict]:
        result = []
        for root in self.roots():
            try:
                entries = [e for e in os.scandir(root) if e.is_dir() and not e.name.startswith('.')]
            except OSError:
                continue
            entries.sort(key=lambda e: e.stat().st_mtime, reverse=True)
            result.append({'root': str(root), 'dirs': [{'name': e.name, 'path': e.path} for e in entries]})
        return result

    def create(self, root: str, name: str) -> Path:
        name = name.strip()
        if not name or name in ('.', '..') or BAD_NAME.search(name):
            raise ValueError(f'폴더 이름으로 쓸 수 없다: {name}')
        base = Path(root)
        allowed = [str(r) for r in self.roots()] + [str(self.default_root())]
        if str(base) not in allowed:
            raise ValueError(f'프로젝트 루트가 아니다: {root}')
        path = base / name
        path.mkdir(parents=True, exist_ok=True)
        return path
