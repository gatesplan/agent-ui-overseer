import json
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger

from project_manager.l0.transcript_reader import TranscriptReader
from project_manager.l1.item_splitter import ItemSplitter


# 패널이 띄운 세션의 훅 진입점. 세션 시작, 입력, 턴 끝을 탭별 JSONL 에 쌓는다
# SessionStart 에는 사안 규약을 돌려줘 세션 컨텍스트에 넣는다
class CaptureHook:
    def __init__(self, store_dir: str | Path, protocol_path: str | Path | None = None):
        self.store_dir = Path(store_dir)
        self.protocol_path = Path(protocol_path) if protocol_path else None
        self.splitter = ItemSplitter()

    def run(self, hook_input: dict, tab_id: str) -> str:
        event = hook_input.get('hook_event_name') or 'Stop'
        session_id = hook_input.get('session_id') or 'unknown'
        logger.info(f"hook 시작: event={event}, tab={tab_id}, session={session_id}")
        base = {'at': datetime.now(timezone.utc).isoformat(), 'session_id': session_id}

        if event == 'SessionStart':
            self._append(tab_id, {**base, 'event': 'session_start', 'source': hook_input.get('source'), 'cwd': hook_input.get('cwd')})
            return self._protocol()
        if event == 'UserPromptSubmit':
            self._append(tab_id, {**base, 'event': 'prompt', 'prompt': hook_input.get('prompt') or ''})
            return ''
        if event == 'Stop':
            self._append(tab_id, {**base, 'event': 'turn', **self._turn(hook_input)})
            return ''
        logger.debug(f"처리하지 않는 이벤트: {event}")
        return ''

    def _turn(self, hook_input: dict) -> dict:
        transcript_path = hook_input.get('transcript_path')
        text, source = self._text(hook_input, transcript_path)
        preamble, items = self.splitter.split(text)
        # 이 턴이 실제로 받은 입력. 기록 파일이 없으면 None 이고 입력 훅 기록으로 대신한다
        prompts = TranscriptReader(transcript_path).turn_prompts() if transcript_path and Path(transcript_path).exists() else None
        logger.info(f"turn 캡처: source={source}, items={len(items)}, text_len={len(text)}, prompts={None if prompts is None else len(prompts)}")
        return {'source': source, 'text': text, 'preamble': preamble, 'items': [item.to_dict() for item in items], 'prompts': prompts}

    def _text(self, hook_input: dict, transcript_path: str | None) -> tuple[str, str]:
        # 2.1.x 의 Stop 훅은 마지막 응답을 직접 준다. 없는 버전만 기록 파일에서 읽는다
        if hook_input.get('last_assistant_message'):
            return hook_input['last_assistant_message'], 'hook'
        if transcript_path and Path(transcript_path).exists():
            return TranscriptReader(transcript_path).last_turn_text(), 'transcript'
        return '', 'none'

    def _protocol(self) -> str:
        if self.protocol_path and self.protocol_path.exists():
            return self.protocol_path.read_text(encoding='utf-8')
        return ''

    def _append(self, tab_id: str, record: dict) -> None:
        self.store_dir.mkdir(parents=True, exist_ok=True)
        with (self.store_dir / f'{tab_id}.jsonl').open('a', encoding='utf-8') as f:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
