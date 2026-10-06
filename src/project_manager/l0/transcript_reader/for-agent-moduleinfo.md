---
sources:
  transcript_reader.py: 6d92a04e3cfa
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
