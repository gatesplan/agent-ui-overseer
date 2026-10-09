import json
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger

from ...l0.permission_gate import PermissionGate
from ...l0.record_store import RecordStore
from ...l0.transcript_reader import TranscriptReader
from ...l1.item_splitter import ItemSplitter

# 권한 요청 기록에 남길 도구 입력 문자열 길이. Write 본문 같은 큰 입력을 다 남기지 않는다
INPUT_PREVIEW = 2000


# 패널이 띄운 세션의 훅 진입점. 세션 시작, 입력, 턴 끝, 사용자 확인 요청을 탭별 JSONL 에 쌓는다
# SessionStart 에는 사안 규약을 돌려줘 세션 컨텍스트에 넣는다
class CaptureHook:
    # gate: 권한 요청을 패널 화면에 넘겨 결정을 받는다. 없으면 권한 요청은 그대로 터미널 확인 창으로 간다
    # records: 프로젝트 결정 아카이브. 있으면 SessionStart 에 그 프로젝트의 유효한 기록 목록을 함께 넣는다
    def __init__(self, store_dir: str | Path, protocol_path: str | Path | None = None, gate: PermissionGate | None = None,
                 records: RecordStore | None = None):
        self.store_dir = Path(store_dir)
        self.protocol_path = Path(protocol_path) if protocol_path else None
        self.gate = gate
        self.records = records
        self.splitter = ItemSplitter()

    def run(self, hook_input: dict, tab_id: str) -> str:
        event = hook_input.get('hook_event_name') or 'Stop'
        session_id = hook_input.get('session_id') or 'unknown'
        logger.info(f"hook 시작: event={event}, tab={tab_id}, session={session_id}")
        base = {'at': datetime.now(timezone.utc).isoformat(), 'session_id': session_id}

        if event == 'SessionStart':
            # records_seen: 이 세션이 받은 기록 목록의 끝. 이후 생긴 기록은 다음 입력 때 변경 고지로 알린다
            self._append(tab_id, {**base, 'event': 'session_start', 'source': hook_input.get('source'), 'cwd': hook_input.get('cwd'),
                                  'transcript_rows': self._rows(hook_input.get('transcript_path')),
                                  'records_seen': self._records_last(hook_input.get('cwd'))})
            return '\n\n'.join(p for p in (self._protocol(), self._briefing(hook_input.get('cwd'))) if p)
        if event == 'UserPromptSubmit':
            cwd = hook_input.get('cwd')
            if not self._started(tab_id, session_id):
                # 시작 훅이 실패해 규약을 못 받은 세션. 이번 입력에 규약과 기록 목록을 넣고 시작 기록을 남긴다
                seen = self._records_last(cwd)
                self._append(tab_id, {**base, 'event': 'session_start', 'source': 'recovered', 'cwd': cwd, 'records_seen': seen})
                self._append(tab_id, {**base, 'event': 'prompt', 'prompt': hook_input.get('prompt') or '', 'records_seen': seen})
                logger.info(f"세션 시작 기록이 없어 규약을 입력과 함께 넣는다: tab={tab_id}, session={session_id}")
                return '\n\n'.join(p for p in (self._protocol(), self._briefing(cwd)) if p)
            notice, seen = self._notice(cwd, tab_id, session_id)
            self._append(tab_id, {**base, 'event': 'prompt', 'prompt': hook_input.get('prompt') or '', 'records_seen': seen})
            return notice
        if event == 'Stop':
            self._append(tab_id, {**base, 'event': 'turn', **self._turn(hook_input, tab_id, session_id)})
            return ''
        if event == 'Notification':
            # 권한 확인 등 터미널에서 사용자 응답을 기다린다는 알림. 화면이 탭에 띄운다
            self._append(tab_id, {**base, 'event': 'notification', 'message': hook_input.get('message') or '',
                                  'kind': hook_input.get('notification_type')})
            return ''
        if event == 'PermissionRequest':
            return self._permission(hook_input, tab_id, base)
        logger.debug(f"처리하지 않는 이벤트: {event}")
        return ''

    # 권한 요청을 기록하고 패널 화면의 결정을 기다린다. 패널이 받을 수 없으면 기다리지 않는다
    def _permission(self, hook_input: dict, tab_id: str, base: dict) -> str:
        if not self.gate or not self.gate.ready():
            logger.info("패널이 권한 결정을 받을 수 없다. 터미널 확인 창으로 넘긴다")
            return ''
        request_id = self.gate.new_id()
        self._append(tab_id, {**base, 'event': 'permission', 'request_id': request_id,
                              'tool_name': hook_input.get('tool_name'), 'tool_input': self._preview(hook_input.get('tool_input'))})
        decision = self.gate.wait(request_id)
        behavior = decision['behavior'] if decision else 'timeout'
        self._append(tab_id, {**base, 'at': datetime.now(timezone.utc).isoformat(), 'event': 'permission_done',
                              'request_id': request_id, 'behavior': behavior})
        logger.info(f"권한 결정: tool={hook_input.get('tool_name')}, behavior={behavior}")
        return self.gate.hook_output(decision)

    def _preview(self, value):
        if isinstance(value, str):
            return value if len(value) <= INPUT_PREVIEW else value[:INPUT_PREVIEW] + '…'
        if isinstance(value, dict):
            return {k: self._preview(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self._preview(v) for v in value[:50]]
        return value

    def _turn(self, hook_input: dict, tab_id: str, session_id: str) -> dict:
        transcript_path = hook_input.get('transcript_path')
        text, source = self._text(hook_input, transcript_path)
        preamble, items = self.splitter.split(text)
        record = {'source': source, 'text': text, 'preamble': preamble, 'items': [item.to_dict() for item in items],
                  'prompts': None, 'usage': None, 'files': None, 'transcript_rows': None}
        # 입력, 토큰 사용량, 고친 파일은 기록 파일에서 읽는다. 실패해도 응답 기록은 남긴다
        if transcript_path and Path(transcript_path).exists():
            try:
                reader = TranscriptReader(transcript_path)
                since = self._since(tab_id, session_id)
                record['prompts'] = reader.turn_prompts(since)
                record['usage'] = reader.turn_usage(since)
                record['files'] = reader.turn_files(since)
                record['transcript_rows'] = reader.row_count()
            except Exception:
                logger.exception("기록 파일 읽기 실패")
        logger.info(f"turn 캡처: source={source}, items={len(items)}, text_len={len(text)}, usage={record['usage']}")
        return record

    # 이 세션에서 훅이 지난번에 남긴 기록 파일 길이. 이번 턴은 그 뒤에서 시작한다
    def _since(self, tab_id: str, session_id: str) -> int | None:
        return self._last_value(tab_id, session_id, 'transcript_rows')

    # 이 세션의 시작 기록이 있는지. 없으면 시작 훅이 실패해 규약을 못 받은 것이다
    def _started(self, tab_id: str, session_id: str) -> bool:
        path = self.store_dir / f'{tab_id}.jsonl'
        if not path.exists():
            return False
        for line in path.open(encoding='utf-8'):
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get('event') == 'session_start' and row.get('session_id') == session_id:
                return True
        return False

    # 이 세션의 훅 기록에서 key 의 마지막 값
    def _last_value(self, tab_id: str, session_id: str, key: str):
        path = self.store_dir / f'{tab_id}.jsonl'
        if not path.exists():
            return None
        value = None
        for line in path.open(encoding='utf-8'):
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get('session_id') == session_id and row.get(key) is not None:
                value = row[key]
        return value

    def _records_last(self, cwd: str | None) -> int | None:
        if not self.records or not cwd:
            return None
        try:
            return self.records.last_id(RecordStore.project_key(cwd))
        except Exception:
            logger.exception("기록 목록 읽기 실패")
            return None

    # 이 세션이 마지막으로 받은 뒤 다른 탭에서 생긴 기록의 변경 고지와, 이제 받은 끝
    # 받은 끝이 기록되지 않은 세션(이 기능 전에 뜬 세션)은 지금 끝부터 센다. 지난 기록을 한꺼번에 쏟지 않게
    def _notice(self, cwd: str | None, tab_id: str, session_id: str) -> tuple[str, int | None]:
        last = self._records_last(cwd)
        if last is None:
            return '', None
        seen = self._last_value(tab_id, session_id, 'records_seen')
        if seen is None:
            return '', last
        try:
            return self.records.notice(RecordStore.project_key(cwd), seen, exclude_tab=tab_id), last
        except Exception:
            logger.exception("변경 고지 만들기 실패")
            return '', seen

    def _rows(self, transcript_path: str | None) -> int | None:
        if not transcript_path:
            return None
        if not Path(transcript_path).exists():
            return 0
        try:
            return TranscriptReader(transcript_path).row_count()
        except Exception:
            logger.exception("기록 파일 읽기 실패")
            return None

    def _text(self, hook_input: dict, transcript_path: str | None) -> tuple[str, str]:
        # 2.1.x 의 Stop 훅은 마지막 응답을 직접 준다. 없는 버전만 기록 파일에서 읽는다
        if hook_input.get('last_assistant_message'):
            return hook_input['last_assistant_message'], 'hook'
        if transcript_path and Path(transcript_path).exists():
            return TranscriptReader(transcript_path).last_turn_text(), 'transcript'
        return '', 'none'

    # 이 프로젝트의 유효한 결정 기록과 용어. 읽지 못해도 규약 주입은 막지 않는다
    def _briefing(self, cwd: str | None) -> str:
        if not self.records or not cwd:
            return ''
        try:
            return self.records.briefing(RecordStore.project_key(cwd))
        except Exception:
            logger.exception("기록 목록 읽기 실패")
            return ''

    def _protocol(self) -> str:
        if self.protocol_path and self.protocol_path.exists():
            return self.protocol_path.read_text(encoding='utf-8')
        return ''

    def _append(self, tab_id: str, record: dict) -> None:
        self.store_dir.mkdir(parents=True, exist_ok=True)
        with (self.store_dir / f'{tab_id}.jsonl').open('a', encoding='utf-8') as f:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
