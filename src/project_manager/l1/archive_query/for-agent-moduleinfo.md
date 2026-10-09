---
sources:
  archive_query.py: 8c5f2d1f0028
---
# archive_query

한 프로젝트의 결정 아카이브 조회. 결정 기록과 용어(RecordStore), 지난 사안과 사용자 결정, 모듈 책임 이력(ProjectJournal)을
에이전트가 읽기 좋은 짧은 글로 돌려준다. 그 프로젝트와 상위 폴더의 `.overseer/` 만 읽는다. 쓰지 않는다. MCP 도구(l2/overseer_mcp)가 감싼다.

## ArchiveQuery

### __init__
__init__(records: RecordStore, project_cwd: str)
    프로젝트는 project_cwd 의 project_key. 그 프로젝트와 상위 폴더의 세션 이력에서 사안을 본다.
    기록도 상위 폴더 것까지 보고, 상위 폴더 기록은 `gatesplan/D-1` 처럼 폴더 이름을 붙여 보인다.

### Methods

list_records(query: str = '', kind: str = '', include_replaced: bool = False) -> str
    `- D-3 결정 (메모: …)` 한 줄씩. query 는 내용, 메모, 본문에서 찾는다(대소문자 무시). kind 는 D | W.
record(ref: str) -> str
    기록 하나. 대체 이력 전체(오래된 것부터), 원래 사안 본문(BODY_LIMIT 자), `근거:` 사안과 그에 대한 사용자 결정.
decisions(query: str = '', action: str = '', limit: int = 20) -> str
    지난 사안과 사용자가 보낸 마지막 결정을 최근 순으로. action 으로 처리 종류(reject 면 기각된 것과 사유만).
    한 줄: `- 날짜 #<사안> [종류][D] 제목 → 처리: 의견`. 상위 폴더 사안은 `#gatesplan/5S-2-1`. limit 를 넘으면 남은 건수를 알린다.
module(name: str) -> str
    모듈 하나(`l1.item_splitter` 나 끝 이름)의 책임 변경 이력과 그 이름을 언급한 유효한 결정 기록.

## 설계 이유

- 결과를 글로 돌려준다. 에이전트가 바로 읽고, 길이를 BODY_LIMIT, limit 로 묶어 컨텍스트를 아낀다.
- 사안 ID 는 프로젝트 안에서 겹치지 않으니 탭을 가리지 않는다.
