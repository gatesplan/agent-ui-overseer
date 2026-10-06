---
sources:
  decision_store.py: beec96319f25
---
# decision_store

패널 저장소. SQLite 한 파일(WAL)에 탭, 보낸 메시지, 사안 결정, 작성 중 초안을 둔다.
원문(응답, 입력)은 훅 기록 JSONL 에 있고 여기는 그 위의 사용자 결정만 쌓는다.

## DecisionStore

### __init__
__init__(path: str | Path)
    파일과 표가 없으면 만든다.

### Methods

add_tab(tab_id: str, cwd: str, claude_args: str = '') -> None
close_tab(tab_id: str) -> None
    닫은 시각만 남긴다. 기록은 지우지 않는다.
tabs() -> list[dict]
    닫은 탭까지 전부.
history(tab_id: str, item_id: str) -> list[dict]
    사안 하나에 보낸 결정 이력 [{action, note, created_at}].
open_tabs() -> list[dict]
    닫지 않은 탭. 패널을 다시 켤 때 복원에 쓴다.

add_message(tab_id: str, text: str, decisions: list[tuple[str, str, str]]) -> int
    보낸 메시지와 거기 담긴 결정(사안 ID, 처리, 사유)을 한 트랜잭션으로 남긴다. 메시지 ID 반환.
    처리: answer, approve, hold, reject, confirm. 종합 의견 피드백은 사안 ID `sum-<턴>`, 처리 feedback.
add_local(tab_id: str, decisions: list[tuple[str, str, str]]) -> None
    에이전트에게 보내지 않고 패널에서만 내린 결정(보류 닫기 close). 메시지 ID 0.
sent(tab_id: str) -> dict[str, dict]
    사안마다 마지막으로 보낸 결정 {action, note}.
last_message(tab_id: str) -> dict | None

save_draft(tab_id: str, data: dict) -> None
draft(tab_id: str) -> dict
    화면이 작성 중인 처리, 의견, 추가 지시. 형식은 화면이 정한다.

## 설계 이유

- 결정은 덮어쓰지 않고 이벤트로 쌓는다. 보류에서 승인으로 바뀐 이력도 남는다(개발계획 2번 결정 이력 조회의 바탕).
