---
sources:
  capture_hook.py: d29b03dec983
---
# capture_hook

Claude Code Stop 훅 진입점. 턴이 끝날 때마다 응답을 사안 단위로 나눠 세션별 JSONL 에 한 줄씩 쌓는다.
실행 스크립트는 `scripts/capture_hook.py`. 저장 위치 `data/captures/<session_id>.jsonl`, 로그 `data/logs/`.

## CaptureHook

### __init__
__init__(store_dir: str | Path)

### Methods

run(hook_input: dict) -> dict
    raise OSError
    hook_input 은 Stop 훅 stdin JSON.
    응답 텍스트는 `last_assistant_message`(2.1.x 에서 확인)를 우선 쓰고, 없으면 transcript_path 를 TranscriptReader 로 읽는다.
    저장 레코드: captured_at, session_id, cwd, source(hook|transcript|none), text, preamble, items.
    턴 번호는 레코드 순서로 정한다. 사안 ID(`턴-순번`) 부여는 소비하는 쪽 몫.

## 설계 이유

- 훅은 예외를 삼키고 항상 0 으로 끝난다(스크립트 쪽). 캡처 실패가 에이전트 세션을 막으면 안 된다.
- Claude Code 바이너리나 인증은 건드리지 않는다. 훅 입력과 대화 기록만 읽는다.
