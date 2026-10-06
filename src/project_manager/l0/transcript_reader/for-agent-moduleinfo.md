---
sources:
  transcript_reader.py: bd62dfdb4bd0
---
# transcript_reader

Claude Code 대화 기록 JSONL(`~/.claude/projects/<proj>/<session>.jsonl`)에서 마지막 턴의 응답 텍스트를 꺼낸다.
Stop 훅 입력에 `last_assistant_message`가 없는 버전을 위한 대체 경로다.

## TranscriptReader

### __init__
__init__(path: str | Path)

### Methods

last_turn_text() -> str
    raise OSError
    마지막 사용자 프롬프트 뒤의 assistant text 블록을 빈 줄로 이어 반환한다.
    사용자 프롬프트 판정: type=user 이고 isMeta, isSidechain 이 아니며 tool_result 를 담지 않은 항목.
    thinking, tool_use 블록과 서브에이전트(isSidechain) 응답은 제외한다.
    파싱 안 되는 줄(기록 중 잘린 마지막 줄)은 건너뛴다.

turn_prompts() -> list[str]
    raise OSError
    이번 턴에 실제로 전달된 사용자 입력들. 직전 턴 끝(type=system, subtype=turn_duration) 뒤의 사용자 프롬프트다.
    Stop 훅 시점에는 이번 턴의 turn_duration 이 아직 기록되지 않아 이전 턴 끝이 경계가 된다.
    중단된 입력은 다음 턴에 함께 들어간다. `[Request interrupted …]` 표시는 뺀다.
    입력 훅(UserPromptSubmit)은 작업 중 대기열에 넣는 순간 불려 어느 턴 입력인지 알 수 없어서 이것으로 정한다.
