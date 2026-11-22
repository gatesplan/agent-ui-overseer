import json
from pathlib import Path

# 파일 내용을 바꾸는 도구
EDIT_TOOLS = ('Edit', 'Write', 'MultiEdit', 'NotebookEdit')


# Claude Code 대화 기록(JSONL)에서 턴의 입력, 응답, 사용량, 고친 파일을 꺼낸다. 패널 훅이 남기지 못한 끝난 턴도 찾는다
# 기록은 수백 MB 까지 자라므로 파일은 처음 물을 때 한 번만 읽는다. 그 뒤로 붙은 줄을 보려면 새로 만든다
class TranscriptReader:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self._cache: list[dict] | None = None

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
        return self._prompts(rows[start:])

    # 이번 턴에 전달된 시스템 입력(예약 깨우기 같은 것). 입력 훅도 불려 대기 입력으로 남으니 이것으로 지운다
    # 경계는 turn_prompts 와 같다. 경계를 모르면 None
    def turn_system_prompts(self, since: int | None = None) -> list[str] | None:
        rows = self._rows()
        start = self._turn_start(rows, since)
        if start is None:
            return None
        return self._system_prompts(rows[start:])

    # 메타 주입(isMeta)이어도 시스템이 넣은 입력이면 넣는다. 예약 깨우기는 isMeta, promptSource=system 으로 남는다
    def _system_prompts(self, rows: list[dict]) -> list[str]:
        out = []
        for row in rows:
            if row.get('type') != 'user' or row.get('isSidechain') or not self._is_system(row):
                continue
            blocks = self._blocks(row)
            if any(b.get('type') == 'tool_result' for b in blocks):
                continue
            text = '\n'.join(b['text'] for b in blocks if b.get('type') == 'text' and b.get('text')).strip()
            if text:
                out.append(text)
        return out

    def _prompts(self, rows: list[dict]) -> list[str]:
        prompts = []
        for row in rows:
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
        return self._usage(rows[start:])

    def _usage(self, rows: list[dict]) -> dict:
        calls: dict[str, dict] = {}
        model = None
        tools = 0
        for row in rows:
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

    # 이번 턴에 고친 파일. 파일 편집 도구(Edit, Write, MultiEdit, NotebookEdit)가 받은 경로를 처음 나온 순서로
    # 서브에이전트가 고친 것도 코드가 바뀐 것이라 넣는다. 셸로 고친 파일은 알 수 없다. 경계를 모르면 None
    def turn_files(self, since: int | None = None) -> list[str] | None:
        rows = self._rows()
        start = self._turn_start(rows, since)
        if start is None:
            return None
        return self._files(rows[start:])

    def _files(self, rows: list[dict]) -> list[str]:
        files: dict[str, None] = {}
        for row in rows:
            if row.get('type') != 'assistant':
                continue
            for b in self._blocks(row):
                if b.get('type') != 'tool_use' or b.get('name') not in EDIT_TOOLS:
                    continue
                args = b.get('input') or {}
                path = args.get('file_path') or args.get('notebook_path')
                if isinstance(path, str) and path:
                    files[path] = None
        return list(files)

    # 기록 줄 수. 훅이 남겨 두었다가 다음 턴의 since 로 넘긴다
    def row_count(self) -> int:
        return len(self._rows())

    # since 뒤에 끝 표시(turn_duration)까지 붙은 턴들. 훅이 그 턴을 남기지 못한 것이다(시간 초과, API 오류로 Stop 훅 없음)
    # since 는 훅이 지난번에 남긴 기록 길이라, 바로 뒤에는 그 턴의 끝 표시가 온다. 입력도 응답도 없는 구간은 턴이 아니라 뺀다
    # 각 턴: prompts, system_prompts, text(마지막 응답 메시지의 글. Stop 훅이 주는 것과 같다), usage, files, transcript_rows(끝 표시 앞까지의 길이)
    def ended_turns(self, since: int) -> list[dict]:
        rows = self._rows()
        turns = []
        start = since
        for i in range(since, len(rows)):
            if not self._turn_end(rows[i]):
                continue
            part, start = rows[start:i], i + 1
            prompts = self._prompts(part)
            if not prompts and not self._has_reply(part):
                continue
            turns.append({'prompts': prompts, 'system_prompts': self._system_prompts(part), 'text': self._last_text(part),
                          'usage': self._usage(part), 'files': self._files(part), 'transcript_rows': i})
        return turns

    # 마지막 끝 표시 뒤에 진행 중인 턴이 있는지. 입력(시스템 입력 포함)이나 응답이 하나라도 있으면 있다
    def open_turn(self, since: int | None = None) -> bool:
        rows = self._rows()
        start = self._turn_start(rows, since) or 0
        return any(self._is_prompt(r) or self._absorbed_prompt(r) or (r.get('type') == 'assistant' and not r.get('isSidechain'))
                   for r in rows[start:])

    def _turn_end(self, row: dict) -> bool:
        return row.get('type') == 'system' and row.get('subtype') == 'turn_duration' and not row.get('isSidechain')

    # 응답 글이 있는지. API 오류 문구는 응답으로 치지 않는다(오류 턴은 입력이 있어야 턴이다)
    def _has_reply(self, rows: list[dict]) -> bool:
        return any(r.get('type') == 'assistant' and not r.get('isSidechain') and not r.get('isApiErrorMessage')
                   and any(b.get('type') == 'text' and b.get('text') for b in self._blocks(r)) for r in rows)

    # 마지막 응답 메시지의 글. 한 메시지가 여러 줄로 기록되니 같은 메시지 ID 의 글을 모은다. API 오류면 그 문구다
    def _last_text(self, rows: list[dict]) -> str:
        main = [r for r in rows if r.get('type') == 'assistant' and not r.get('isSidechain')]
        for row in reversed(main):
            if not any(b.get('type') == 'text' and b.get('text') for b in self._blocks(row)):
                continue
            mid = (row.get('message') or {}).get('id')
            same = [r for r in main if mid and (r.get('message') or {}).get('id') == mid] or [row]
            return '\n\n'.join(b['text'] for r in same for b in self._blocks(r) if b.get('type') == 'text' and b.get('text'))
        return ''

    # 이번 턴이 시작되는 줄. 마지막 turn_duration 다음과 since 중 늦은 쪽
    # 둘 다 없으면 앞선 응답이 없을 때만 처음부터. 있으면 경계를 모르므로 None
    def _turn_start(self, rows: list[dict], since: int | None = None) -> int | None:
        bounds = [since] if since is not None else []
        for i in range(len(rows) - 1, -1, -1):
            if self._turn_end(rows[i]):
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
        if self._cache is None:
            self._cache = self._read()
        return self._cache

    def _read(self) -> list[dict]:
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
