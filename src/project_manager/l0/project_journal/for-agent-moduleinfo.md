---
sources:
  project_journal.py: 0
---
# project_journal

한 프로젝트의 세션 이력. `<프로젝트>/.overseer/sessions/<번호>.jsonl` 세션 하나에 파일 하나.
폴더 안 `.gitignore`(`*`)로 git 에서 스스로 빠진다.

줄 종류(type):
- session: 첫 줄. {session, session_id, tab, source, at}. 그 세션을 연 탭이 주인이다
- attach: resume 이 새 claude 세션 ID 로 떴을 때 이 세션에 잇는 줄
- turn: 턴 하나 {id, session, turn, at, after, prompt, preamble, items, files}. 같은 턴이 다시 쓰이면 마지막 줄이 그 턴
- decision: {item, action, note, message, at}. 사안이 난 세션의 파일에 쓴다(뒤 세션에서 내린 결정도)
- module: 책임 변경 {module, before, after, request, turn, at}. before None 은 새 모듈, request 는 사용자가 보낸 책임

## ProjectJournal

### __init__
__init__(project: str | Path)

### Methods

ensure() -> None
sessions() -> list[int]
open_session(session_id, tab_id, source=None) -> int
    다음 번호(가장 큰 번호 + 1)로 파일을 배타적으로 만든다. 두 쪽이 같은 번호를 받지 않는다.
session_of(session_id) -> int | None
owner(n) -> str | None
attach(n, session_id, source=None) -> None
write_turn(turn) -> bool
    지난번에 쓴 내용(TURN_KEYS 만)과 같으면 쓰지 않는다. 다시 연 객체도 파일에서 읽어 비교한다.
add_decisions(decisions: list[(사안 ID, 처리, 사유)], message=None) -> None
add_module_change(n, event) -> None
decisions(sessions=None) -> list[dict]
sent(sessions=None) -> dict[str, dict]
    사안마다 마지막 결정 {action, note, at}.
history(item_id) -> list[dict]
turns(n) -> list[dict]
items() -> dict[str, dict]
module_history() -> dict[str, list[dict]]
session_number(item_id) -> int | None    # staticmethod. `5S-3-2`, `sum-5S-3` 의 5
