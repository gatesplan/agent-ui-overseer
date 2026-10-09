---
sources:
  panel_store.py: 0
---
# panel_store

이 컴퓨터의 패널 상태. SQLite 한 파일(WAL)에 탭, 보낸 메시지, 작성 중 초안을 둔다.
사안과 결정은 프로젝트의 것이라 여기 두지 않는다. 각 프로젝트의 `.overseer/`(ProjectJournal)에 있다.

## PanelStore

### __init__
__init__(path: str | Path)
    파일과 표가 없으면 만든다. 예전 decisions, records 표가 있으면 그대로 둔다(이전 스크립트만 읽는다).

### Methods

add_tab(tab_id: str, cwd: str, claude_args: str = '') -> None
close_tab(tab_id: str) -> None
    닫은 시각만 남긴다. 기록은 지우지 않는다.
tabs() -> list[dict]
    닫은 탭까지 전부.
open_tabs() -> list[dict]
    닫지 않은 탭. 패널을 다시 켤 때 복원에 쓴다.
add_message(tab_id: str, text: str) -> int
    보낸 메시지를 남기고 메시지 ID 를 돌려준다. 거기 담긴 결정은 ProjectJournal.add_decisions 에 이 ID 와 함께 쓴다.
last_message(tab_id: str) -> dict | None
save_draft(tab_id: str, data: dict) -> None
draft(tab_id: str) -> dict
    화면이 작성 중인 처리, 의견, 추가 지시. 형식은 화면이 정한다.
