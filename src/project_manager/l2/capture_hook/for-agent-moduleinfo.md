---
sources:
  capture_hook.py: fc6cfd353856
---
# capture_hook

패널이 띄운 claude 세션의 훅 진입점. 실행 스크립트는 `scripts/capture_hook.py`, 등록은 `scripts/install_hooks.py`(전역 설정).
스크립트는 환경변수 OVERSEER_TAB 이 없으면 import 전에 바로 끝난다. 다른 세션에는 영향이 없다.
저장 위치 `data/captures/<탭 ID>.jsonl`, 로그 `data/logs/capture_hook.log`.

## CaptureHook

### __init__
__init__(store_dir: str | Path, protocol_path: str | Path | None = None)
    protocol_path: SessionStart 에 돌려줄 사안 규약 파일(docs/item-protocol.md).

### Methods

run(hook_input: dict, tab_id: str) -> str
    raise OSError
    hook_input 은 훅 stdin JSON. hook_event_name 으로 나눈다. 반환값은 훅 stdout 으로 쓴다.
    SessionStart: {event: session_start, source, cwd} 기록. 규약 본문 반환(세션 컨텍스트에 들어간다)
    UserPromptSubmit: {event: prompt, prompt} 기록
    Stop: {event: turn, source, text, preamble, items} 기록. 응답은 `last_assistant_message`(2.1.x) 우선, 없으면 transcript
    모든 기록에 at, session_id 가 붙는다. 턴 조립은 TurnBuilder 몫.

## 설계 이유

- 훅은 예외를 삼키고 항상 0 으로 끝난다(스크립트 쪽). 캡처 실패가 에이전트 세션을 막으면 안 된다.
- 기록을 claude 세션이 아니라 패널 탭 단위로 모은다. /clear 로 세션 ID 가 바뀌어도 한 탭의 흐름으로 이어진다.
- Claude Code 바이너리나 인증은 건드리지 않는다. 훅 입력과 대화 기록만 읽는다.
