# 프로젝트 프로토콜

## 구조 및 코딩 규칙

프로토콜 문서는 프로젝트 루트 기준 `.claude/`에서 찾는다.

- Ln 구조: `@.claude/for-agent-codingprotocol-ln-structure.md` 참조
- Python 코딩: `@.claude/for-agent-codingprotocol-python.md` 참조

`lnt check`, `lnt doc` 이 규칙과 문서를 검사한다. 훅이 편집마다 자동 실행된다.

## 프로젝트 설명

여러 CLI 에이전트(Claude Code 등) 세션을 탭으로 다루고, 응답을 사안 단위 블록으로 쪼개 답변·보류·기각으로 처리하는 개인용 UI.
공식 CLI 바이너리를 그대로 띄우고 훅과 대화 기록만 읽는다. 구독 토큰을 꺼내거나 바이너리를 고치지 않는다.

- 개발 의도와 방향: `개발계획.md` (작업 전에 읽는다)
- 사안 출력 규약: `docs/item-protocol.md` (에이전트 세션의 CLAUDE.md 에 넣는다)
- 실행: `uv sync` 후 `uv run overseer` (http://127.0.0.1:47310/). 훅 등록은 `uv run python scripts/install_hooks.py` (전역 설정, 한 번)
- 캡처: 훅 `scripts/capture_hook.py`(SessionStart, UserPromptSubmit, Stop) → `data/captures/<탭 ID>.jsonl`. 패널이 띄운 세션(OVERSEER_TAB)에서만 동작
- 저장: `data/overseer.db` (탭, 보낸 메시지, 사안 결정, 초안)
- 목업만 볼 때: `python scripts/serve_mock.py` (http://127.0.0.1:47311/)

## 추가 규칙

[프로젝트 특수 규칙이 있다면 여기에 작성]
