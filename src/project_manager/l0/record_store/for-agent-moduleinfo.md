---
sources:
  record_store.py: 1cbb8ac9f9c9
---
# record_store

프로젝트 결정 아카이브. 사용자가 승인한 보존 사안([D] 결정 기록, [W] 용어)을 프로젝트별로 `D-n`, `W-n` 번호를 붙여 둔다.
DecisionStore 와 같은 SQLite 파일(`data/overseer.db`)의 records 표를 쓴다. 훅(SessionStart)도 따로 열어 읽는다.

## RecordStore

### __init__
__init__(path: str | Path)

### Methods

project_key(path: str) -> str    # staticmethod
    프로젝트 구분 키. 절대 경로를 normcase 한 것. 같은 폴더면 대소문자, 구분자가 달라도 같다.

add(project: str, kind: str, text: str, body: str = '', note: str = '', tab_id: str | None = None, item_id: str | None = None, replaces: str | None = None) -> dict
    raise ValueError    # kind 가 D, W 가 아닐 때
    번호는 프로젝트 안 종류별로 1부터. 같은 사안(tab_id, item_id)으로 이미 있으면 새로 만들지 않고 그것을 돌려준다.
    replaces('D-3')가 같은 종류의 유효한 기록이면 그 기록을 replaced 로 바꾸고 서로 잇는다(replaces, replaced_by). 아니면 대체하지 않는다.
    반환 dict 에 ref('D-3')가 붙는다.
records(project: str, active_only: bool = False) -> list[dict]
    그 프로젝트 자체의 기록.
records_in_scope(project: str, active_only: bool = False) -> list[dict]
    그 프로젝트에 적용되는 기록: 자기 기록과 상위 폴더(scopes)의 기록. 가까운 폴더부터.
    상위 폴더 기록은 inherited=True, scope(폴더 이름), ref 앞에 폴더 이름(`gatesplan/D-1`).
scopes(project: str) -> list[str]
    프로젝트 자신과 상위 폴더들의 키. 가까운 것부터 드라이브 루트까지.
find(project: str, ref: str) -> dict | None
    'D-3' 은 그 프로젝트, 'gatesplan/D-3' 은 그 이름의 상위 폴더에서 찾는다.
briefing(project: str) -> str
    세션 시작 때 넣을 목록. 유효한 기록만 `- D-3 결정 (메모: …)` 한 줄씩, 상위 폴더 기록은 따로 묶는다. 없으면 빈 문자열.
last_id(project: str) -> int
    그 프로젝트와 상위 폴더 기록의 가장 큰 내부 id. 세션이 목록을 어디까지 받았는지(records_seen) 표시한다.
notice(project: str, after_id: int, exclude_tab: str | None = None) -> str
    after_id 뒤에 생긴 기록(상위 폴더 포함)의 변경 고지. `- 추가: W-2 …`, 대체면 `- 변경: D-1 옛 → D-3 새`. 자기 탭(exclude_tab) 기록은 뺀다. 없으면 빈 문자열.

## 설계 이유

- 상위 폴더 기록은 하위 프로젝트에 적용된다. 묶음 폴더(gatesplan)에서 정한 결정이 그 안의 프로젝트(gatesplan/mathgate) 세션에도 들어가게 하려는 것.
  대체는 같은 폴더 안에서만 한다. 하위에서 상위 결정을 바꾸면 형제 프로젝트에까지 영향이 간다.
- 기록은 지우지 않는다. 대체된 기록도 남아야 이력과 이유를 거슬러 볼 수 있다(개발계획 5번).
- 에이전트는 이 표를 쓰지 않는다. 사용자가 보낸 승인만 AgentTab.sync_records 가 옮긴다.
