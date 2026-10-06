---
sources:
  capture_hook.py: a932a2920ebf
---
# capture_hook

패널이 띄운 claude 세션의 훅 진입점. 실행 스크립트는 `scripts/capture_hook.py`, 등록, 점검, 제거는 `scripts/setup.py`(전역 설정).
스크립트는 환경변수 OVERSEER_TAB 이 없으면 import 전에 바로 끝난다. 다른 세션에는 영향이 없다.
저장 위치 `data/captures/<탭 ID>.jsonl`, 로그 `data/logs/capture_hook.log`.

## CaptureHook

### __init__
__init__(store_dir: str | Path, protocol_path: str | Path | None = None, gate: PermissionGate | None = None)
    protocol_path: SessionStart 에 돌려줄 사안 규약 파일(docs/item-protocol.md).
    gate: 권한 요청을 패널 화면에 넘긴다. 없으면 권한 요청은 그대로 터미널 확인 창으로 간다.
    records: 결정 아카이브. 있으면 SessionStart 에 그 프로젝트(cwd)의 유효한 기록 목록을 규약 뒤에 붙인다. 스크립트는 SessionStart 일 때만 연다.

### Methods

run(hook_input: dict, tab_id: str) -> str
    raise OSError
    hook_input 은 훅 stdin JSON. hook_event_name 으로 나눈다. 반환값은 훅 stdout 으로 쓴다.
    SessionStart: {event: session_start, source, cwd, transcript_rows, records_seen} 기록. 규약 본문 반환(세션 컨텍스트에 들어간다)
    UserPromptSubmit: {event: prompt, prompt, records_seen} 기록. 이 세션이 받은 뒤 다른 탭에서 생긴 기록이 있으면 변경 고지를 돌려준다(입력과 함께 컨텍스트에 들어간다).
      records_seen 이 없는 세션(이 기능 전에 뜬 세션)은 지금 끝부터 센다
      그 세션의 시작 기록이 아예 없으면(시작 훅 실패) 규약과 기록 목록을 이 입력과 함께 넣고 {event: session_start, source: recovered} 를 남긴다
    Stop: {event: turn, source, text, preamble, items, prompts} 기록. 응답은 `last_assistant_message`(2.1.x) 우선, 없으면 transcript
      prompts: 이 턴이 실제로 받은 입력(TranscriptReader.turn_prompts). 기록 파일이 없으면 None
      usage: 이 턴의 토큰 사용량 {model, calls, tools, input_tokens, cache_creation_input_tokens, cache_read_input_tokens, output_tokens}
      transcript_rows: 이 시점의 기록 파일 줄 수. 다음 턴은 이 뒤에서 시작한다(since). SessionStart 도 남긴다
      기록 파일 읽기가 실패해도 응답 기록은 남긴다(prompts, usage 는 None)
    Notification: {event: notification, message, kind} 기록. kind 는 notification_type(permission_prompt, idle_prompt …)
    PermissionRequest: 패널이 결정을 받을 수 있으면(gate.ready) {event: permission, request_id, tool_name, tool_input} 을 기록하고
      화면의 결정을 기다린 뒤 {event: permission_done, request_id, behavior(allow|deny|terminal|timeout)} 를 기록, 결정 JSON 을 돌려준다.
      tool_input 문자열은 INPUT_PREVIEW 자로 자른다. 받을 수 없으면 아무것도 기록하지 않고 빈 문자열(터미널 확인 창)
    모든 기록에 at, session_id 가 붙는다. 턴 조립은 TurnBuilder 몫.

## 설계 이유

- 훅은 예외를 삼키고 항상 0 으로 끝난다(스크립트 쪽). 캡처 실패가 에이전트 세션을 막으면 안 된다.
- 기록을 claude 세션이 아니라 패널 탭 단위로 모은다. /clear 로 세션 ID 가 바뀌어도 한 탭의 흐름으로 이어진다.
- Claude Code 바이너리나 인증은 건드리지 않는다. 훅 입력과 대화 기록만 읽는다.
