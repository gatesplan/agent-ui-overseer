import json
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger

from project_manager.l0.transcript_reader import TranscriptReader
from project_manager.l1.item_splitter import ItemSplitter


# Stop 훅 진입점. 턴이 끝날 때 응답을 사안 단위로 쪼개 세션별 JSONL에 쌓는다
class CaptureHook:
    def __init__(self, store_dir: str | Path):
        self.store_dir = Path(store_dir)
        self.splitter = ItemSplitter()

    def run(self, hook_input: dict) -> dict:
        transcript_path = hook_input.get('transcript_path')
        session_id = hook_input.get('session_id') or 'unknown'
        logger.info(f"capture 시작: session={session_id}")

        text, source = self._text(hook_input, transcript_path)
        preamble, items = self.splitter.split(text)

        record = {
            'captured_at': datetime.now(timezone.utc).isoformat(),
            'session_id': session_id,
            'cwd': hook_input.get('cwd'),
            'source': source,
            'text': text,
            'preamble': preamble,
            'items': [item.to_dict() for item in items],
        }

        self.store_dir.mkdir(parents=True, exist_ok=True)
        with (self.store_dir / f'{session_id}.jsonl').open('a', encoding='utf-8') as f:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
        logger.info(f"capture 완료: source={source}, items={len(items)}, text_len={len(text)}")
        return record

    def _text(self, hook_input: dict, transcript_path: str | None) -> tuple[str, str]:
        # 2.1.x 의 Stop 훅은 마지막 응답을 직접 준다. 없는 버전만 기록 파일에서 읽는다
        if hook_input.get('last_assistant_message'):
            return hook_input['last_assistant_message'], 'hook'
        if transcript_path and Path(transcript_path).exists():
            return TranscriptReader(transcript_path).last_turn_text(), 'transcript'
        return '', 'none'
