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

    # 이번 턴에 실제로 전달된 입력들. 직전 턴 끝(turn_duration) 뒤의 사용자 입력이다
    # 입력 훅은 대기열에 넣는 순간 불려서 어느 턴 입력인지 모른다. 기록 파일은 전달된 순서대로 남는다
    # 중단된 입력은 다음 턴에 함께 들어간다. 중단 표시 자체는 뺀다
    # 시스템이 넣은 입력(백그라운드 작업 알림)은 사용자 입력이 아니라 뺀다
    # 턴 끝 표시가 없는 Claude Code 버전에서 첫 턴이 아니면 경계를 모르므로 None
    # since: 이번 턴이 시작될 수 있는 가장 이른 줄(훅이 지난번에 남긴 기록 길이). 턴 끝 표시와 함께 경계로 쓴다
    def turn_prompts(self, since: int | None = None) -> list[str] | None:
        rows = self._rows()
        start = self._turn_start(rows, since)
        if start is None:
            return None
        prompts = []
        for row in rows[start:]:
            absorbed = self._absorbed_prompt(row)
            if absorbed:
                prompts.append(absorbed)
                continue
            if not self._is_prompt(row) or self._is_system(row):
                continue
            text = '\n'.join(b['text'] for b in self._blocks(row) if b.get('type') == 'text' and b.get('text')).strip()
            if text and not text.startswith('[Request interrupted'):
                prompts.append(text)
        return prompts

    # 이번 턴의 토큰 사용량. 직전 턴 끝 뒤의 API 호출을 더한다. 한 응답이 여러 줄로 기록되므로 메시지 ID 로 한 번씩만 센다
    # 서브에이전트(isSidechain) 호출은 넣지 않는다. 경계를 모르면 None
    def turn_usage(self, since: int | None = None) -> dict | None:
        rows = self._rows()
        start = self._turn_start(rows, since)
        if start is None:
            return None
        calls: dict[str, dict] = {}
        model = None
        tools = 0
        for row in rows[start:]:
            if row.get('type') != 'assistant' or row.get('isSidechain'):
                continue
            message = row.get('message') or {}
            model = message.get('model') or model
            if message.get('id') and isinstance(message.get('usage'), dict):
                calls[message['id']] = message['usage']
            tools += sum(1 for b in self._blocks(row) if b.get('type') == 'tool_use')
        keys = ('input_tokens', 'cache_creation_input_tokens', 'cache_read_input_tokens', 'output_tokens')
        usage = {k: sum(int(c.get(k) or 0) for c in calls.values()) for k in keys}
        return {'model': model, 'calls': len(calls), 'tools': tools, **usage}

    # 기록 줄 수. 훅이 남겨 두었다가 다음 턴의 since 로 넘긴다
    def row_count(self) -> int:
        return len(self._rows())

    # 이번 턴이 시작되는 줄. 마지막 turn_duration 다음과 since 중 늦은 쪽
    # 둘 다 없으면 앞선 응답이 없을 때만 처음부터. 있으면 경계를 모르므로 None
    def _turn_start(self, rows: list[dict], since: int | None = None) -> int | None:
        bounds = [since] if since is not None else []
        for i in range(len(rows) - 1, -1, -1):
            if rows[i].get('type') == 'system' and rows[i].get('subtype') == 'turn_duration':
                bounds.append(i + 1)
                break
        if bounds:
            return max(bounds)
        return None if self._has_earlier_reply(rows) else 0

    # 마지막 입력보다 앞에 끝난 응답(text)이 있는지. 있으면 이전 턴이 있었다는 뜻
    def _has_earlier_reply(self, rows: list[dict]) -> bool:
        last = self._last_prompt_index(rows)
        return any(r.get('type') == 'assistant' and not r.get('isSidechain')
                   and any(b.get('type') == 'text' for b in self._blocks(r)) for r in rows[:max(last, 0)])

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

    # 시스템이 넣은 입력. 백그라운드 작업 알림 같은 것도 user 줄로 남고 새 응답을 부르지만 사용자가 친 것이 아니다
    # 사용자 입력은 origin.kind=human, promptSource=typed 로 남는다. 표시가 없는 예전 기록은 사용자 입력으로 본다
    def _is_system(self, row: dict) -> bool:
        origin = row.get('origin')
        if isinstance(origin, dict) and origin.get('kind') not in (None, 'human'):
            return True
        return row.get('promptSource') == 'system'

    # 작업 중에 넣은 입력. 새 턴을 열지 않고 진행 중인 턴에 흡수되어 user 줄이 아니라 queued_command 첨부로 남는다
    # 응답 텍스트의 경계(_last_prompt_index)로는 쓰지 않는다. 흡수 앞뒤의 응답이 한 턴이다
    def _absorbed_prompt(self, row: dict) -> str | None:
        attachment = row.get('attachment')
        if row.get('type') != 'attachment' or row.get('isSidechain') or not isinstance(attachment, dict):
            return None
        if attachment.get('type') != 'queued_command' or attachment.get('commandMode', 'prompt') != 'prompt':
            return None
        prompt = attachment.get('prompt')
        if isinstance(prompt, list):
            prompt = '\n'.join(b.get('text', '') for b in prompt if isinstance(b, dict) and b.get('type') == 'text')
        return prompt.strip() if isinstance(prompt, str) and prompt.strip() else None

    def _blocks(self, row: dict) -> list[dict]:
        content = (row.get('message') or {}).get('content')
        if isinstance(content, list):
            return [b for b in content if isinstance(b, dict)]
        if isinstance(content, str):
            return [{'type': 'text', 'text': content}]
        return []
