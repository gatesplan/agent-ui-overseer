---
sources:
  record_store.py: 1cbb8ac9f9c9
---
# record_store

프로젝트 결정 아카이브. 사용자가 승인한 보존 사안([D] 결정 기록, [W] 용어)을 프로젝트별로 `D-n`, `W-n` 번호를 붙여 둔다.
기록 하나가 `<프로젝트>/.overseer/records/D-3.md` 파일 하나다. 머리(`---` 사이)에 text, status(active | replaced | retired), replaces, replaced_by, item, tab, note, created, retired, reason.
값은 한 줄이고, 줄바꿈이 있거나 따옴표로 시작하면 JSON 문자열로 쓴다. 본문은 원래 사안 본문. 훅(SessionStart)도 읽는다.

## RecordStore

### __init__
RecordStore()    # 상태 없음. project 인자는 ProjectKey.of 로 만든 키이고 곧 폴더 경로

### Methods

add(project: str, kind: str, text: str, body: str = '', note: str = '', tab_id: str | None = None, item_id: str | None = None, replaces: str | None = None) -> dict
    raise ValueError    # kind 가 D, W 가 아닐 때
    번호는 프로젝트 안 종류별로 1부터. 같은 사안(item_id)으로 이미 있으면 새로 만들지 않고 그것을 돌려준다.
    replaces('D-3')가 같은 종류의 유효한 기록이면 그 기록을 replaced 로 바꾸고 서로 잇는다(replaces, replaced_by 에 'D-3' 같은 ID). 아니면 대체하지 않는다.
    반환 dict 에 ref('D-3')가 붙는다.
retire(project: str, ref: str, reason: str = '') -> dict | None
    그 프로젝트의 유효한 기록('D-3', 폴더 이름 없이)을 retired 로 바꾸고 retired_at, retired_reason 을 단다. 파일은 남는다.
    없거나 유효하지 않거나 상위 폴더 기록이면 None.
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
last_mark(project: str) -> str
    그 프로젝트와 상위 폴더 기록의 가장 늦은 created 나 retired. 세션이 목록을 어디까지 받았는지(records_seen) 표시한다. 없으면 빈 문자열.
notice(project: str, after: str, exclude_tab: str | None = None) -> str
    after 뒤의 기록 변경(상위 폴더 포함) 고지. `- 추가: W-2 …`, 대체면 `- 변경: D-1 옛 → D-3 새`, 폐기면 `- 폐기: D-1 … (사유: …)`.
    추가와 대체는 자기 탭(exclude_tab) 기록을 뺀다. 폐기는 패널에서 한 것이라 모두 넣는다. 없으면 빈 문자열.

## 설계 이유

- 상위 폴더 기록은 하위 프로젝트에 적용된다. 묶음 폴더(gatesplan)에서 정한 결정이 그 안의 프로젝트(gatesplan/mathgate) 세션에도 들어가게 하려는 것.
  대체는 같은 폴더 안에서만 한다. 하위에서 상위 결정을 바꾸면 형제 프로젝트에까지 영향이 간다.
- 기록은 지우지 않는다. 대체된 기록도 남아야 이력과 이유를 거슬러 볼 수 있다(개발계획 5번).
  대체할 결정 없이 더는 맞지 않는 기록은 폐기(retired)한다. 세션 목록에서만 빠지고 이력은 남는다.
- 폐기도 같은 폴더 안에서만 한다. 상위 폴더 기록을 하위 탭에서 폐기하면 형제 프로젝트에서도 빠진다.
- 에이전트는 이 표를 쓰지 않는다. 사용자가 보낸 승인만 AgentTab.sync_records 가 옮긴다.
