import json
from pathlib import Path


# Claude Code 대화 기록(JSONL)에서 마지막 턴의 응답 텍스트를 꺼낸다
class TranscriptReader:
    def __init__(self, path: str | Path):
        self.path = Path(path)

    def last_turn_text(self) -> str:
        rows = self._rows()
        start = self._last_prompt_index(rows)
        texts = []
        for row in rows[start + 1:]:
            if row.get('type') != 'assistant' or row.get('isSidechain'):
                continue
            for block in self._blocks(row):
                if block.get('type') == 'text' and block.get('text'):
                    texts.append(block['text'])
        return '\n\n'.join(texts)

    def _rows(self) -> list[dict]:
        rows = []
        with self.path.open(encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    # 기록 중인 마지막 줄은 잘려 있을 수 있다
                    continue
        return rows

    def _last_prompt_index(self, rows: list[dict]) -> int:
        for i in range(len(rows) - 1, -1, -1):
            if self._is_prompt(rows[i]):
                return i
        return -1

    def _is_prompt(self, row: dict) -> bool:
        # 사용자가 직접 입력한 메시지만. tool_result, 메타 주입은 제외
        if row.get('type') != 'user' or row.get('isSidechain') or row.get('isMeta'):
            return False
        content = (row.get('message') or {}).get('content')
        if isinstance(content, str):
            return True
        if isinstance(content, list):
            return not any(b.get('type') == 'tool_result' for b in content if isinstance(b, dict))
        return False

    def _blocks(self, row: dict) -> list[dict]:
        content = (row.get('message') or {}).get('content')
        if isinstance(content, list):
            return [b for b in content if isinstance(b, dict)]
        if isinstance(content, str):
            return [{'type': 'text', 'text': content}]
        return []
