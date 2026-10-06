# 프로젝트 프로토콜

## 구조 및 코딩 규칙

프로토콜 문서는 프로젝트 루트 기준 `.claude/`에서 찾는다.

- Ln 구조: `@.claude/for-agent-codingprotocol-ln-structure.md` 참조
- Python 코딩: `@.claude/for-agent-codingprotocol-python.md` 참조

`lnt check`, `lnt doc` 이 규칙과 문서를 검사한다. 훅이 편집마다 자동 실행된다.

## 프로젝트 설명

여러 CLI 에이전트(Claude Code 등) 세션을 탭으로 다루고, 응답을 사안 단위 블록으로 쪼개 답변·보류·기각으로 처리하는 개인용 UI.
공식 CLI 바이너리를 그대로 띄우고 훅과 대화 기록만 읽는다. 구독 토큰을 꺼내거나 바이너리를 고치지 않는다.

- 사안 출력 규약: `docs/item-protocol.md` (에이전트 세션의 CLAUDE.md 에 넣는다)
- 캡처: Stop 훅 `scripts/capture_hook.py` → `data/captures/<session_id>.jsonl`

## 추가 규칙

[프로젝트 특수 규칙이 있다면 여기에 작성]
