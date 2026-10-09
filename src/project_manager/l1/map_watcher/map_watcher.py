import os
import threading
from pathlib import Path

from ...l0.module_map import ModuleMap


# 화면이 한 번이라도 연 프로젝트들의 모듈 지도를 최신으로 지킨다. 소스가 바뀌면 다시 받아 바뀐 것만 돌려준다
# 같은 폴더를 여러 탭이 열어도 지도는 하나다. 키는 대소문자를 가리지 않는 절대 경로
class MapWatcher:
    def __init__(self, maps: ModuleMap):
        self.maps = maps
        self.cache: dict[str, dict] = {}
        self.lock = threading.Lock()

    # 지도. 처음이면 지금 받고 그 뒤로 지켜본다
    def get(self, cwd: str) -> dict:
        key = self._key(cwd)
        with self.lock:
            if key not in self.cache:
                self.cache[key] = {'cwd': cwd, 'sig': self.maps.signature(cwd), 'result': self.maps.scan(cwd)}
            return self.cache[key]['result']

    # 서명이 바뀐 폴더만 다시 받는다. (폴더, 새 지도) 목록
    def changed(self) -> list[tuple[str, dict]]:
        out = []
        with self.lock:
            for entry in self.cache.values():
                sig = self.maps.signature(entry['cwd'])
                if sig == entry['sig']:
                    continue
                entry['sig'] = sig
                entry['result'] = self.maps.scan(entry['cwd'])
                out.append((entry['cwd'], entry['result']))
        return out

    # 더 볼 탭이 없는 폴더는 지켜보지 않는다
    def keep_only(self, cwds: list[str]) -> None:
        keep = {self._key(c) for c in cwds}
        with self.lock:
            for key in [k for k in self.cache if k not in keep]:
                del self.cache[key]

    @staticmethod
    def _key(cwd: str) -> str:
        return os.path.normcase(str(Path(cwd).resolve()))
