import os
import re
import string
from pathlib import Path

# 폴더 이름에 쓸 수 없는 글자(Windows)
BAD_NAME = re.compile(r'[\\/:*?"<>|]')


# 드라이브마다 루트의 Projects 폴더를 찾아 그 안의 프로젝트 폴더를 보여 준다. 새 프로젝트 폴더도 여기서 만든다
class ProjectFinder:
    def __init__(self, folder: str = 'Projects', drives: list[str] | None = None):
        self.folder = folder
        self.drives = drives if drives is not None else [f'{d}:\\' for d in string.ascii_uppercase]

    def roots(self) -> list[Path]:
        return [Path(d) / self.folder for d in self.drives if (Path(d) / self.folder).is_dir()]

    # 새 폴더를 만들 기본 위치. Projects 가 하나도 없으면 첫 드라이브(보통 C:)에 만들 자리
    def default_root(self) -> Path:
        roots = self.roots()
        return roots[0] if roots else Path(self.drives[0]) / self.folder

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
            raise ValueError(f'Projects 폴더가 아니다: {root}')
        path = base / name
        path.mkdir(parents=True, exist_ok=True)
        return path
