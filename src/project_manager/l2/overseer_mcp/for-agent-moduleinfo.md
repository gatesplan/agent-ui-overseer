---
sources:
  overseer_mcp.py: c3ab044546f8
---
# overseer_mcp

결정 아카이브 조회를 MCP 도구로 내놓는 읽기 전용 서버(stdio). 실행 스크립트 `scripts/overseer_mcp.py`.
패널이 탭마다 `data/mcp/<탭 ID>.json` 을 쓰고 claude 를 `--mcp-config <그 파일> --allowedTools mcp__overseer` 로 띄운다.
환경변수 OVERSEER_DATA(기록 폴더), OVERSEER_PROJECT(프로젝트 폴더)로 조회 대상을 정한다.

## OverseerMcp

### __init__
__init__(query: ArchiveQuery)
    MCPServer(mcp 2.x) 에 도구 세 개를 read_only 표시로 등록한다. 서버 instructions 에 언제 쓰는지 적는다.

### Methods

records(query: str = '', kind: str = '', include_replaced: bool = False) -> str    # 도구 records
record(ref: str) -> str                                                            # 도구 record
decisions(query: str = '', action: str = '', limit: int = 20) -> str               # 도구 decisions
run() -> None
    stdio 로 돈다. claude 가 띄우고 끝낸다.

## 설계 이유

- 쓰기 도구가 없다. 영속 지식은 사용자 승인으로만 생긴다(개발계획 5번 쓰기 경로 차단).
- 패널 세션에만 --mcp-config 로 붙인다. 전역 설정이나 프로젝트 .mcp.json 을 건드리지 않는다.
