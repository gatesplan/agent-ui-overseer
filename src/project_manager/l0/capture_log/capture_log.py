import json
from pathlib import Path


# 탭 하나의 훅 기록(JSONL)을 이어서 읽는다. 읽은 위치를 기억해 새로 붙은 줄만 더한다
class CaptureLog:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.events: list[dict] = []
        self._offset = 0

    # 새 줄이 있으면 events 에 더하고 True. 쓰는 중이라 줄바꿈이 없는 마지막 줄은 다음에 읽는다
    def poll(self) -> bool:
        if not self.path.exists():
            return False
        with self.path.open('rb') as f:
            f.seek(self._offset)
            chunk = f.read()
        end = chunk.rfind(b'\n')
        if end < 0:
            return False
        self._offset += end + 1
        added = False
        for line in chunk[:end].decode('utf-8').splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                self.events.append(json.loads(line))
                added = True
            except json.JSONDecodeError:
                continue
        return added
