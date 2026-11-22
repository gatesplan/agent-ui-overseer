---
sources:
  overseer_mcp.py: aa5e39ee4dec
---
# overseer_mcp

결정 아카이브 조회(읽기 전용)와 프로젝트 스펙 다루기를 MCP 도구로 내놓는 서버(stdio). 실행 스크립트 `scripts/overseer_mcp.py`.
패널이 탭마다 `data/mcp/<탭 ID>.json` 을 쓰고 claude 를 `--mcp-config <그 파일> --allowedTools mcp__overseer` 로 띄운다.
환경변수 OVERSEER_DATA(기록 폴더), OVERSEER_PROJECT(프로젝트 폴더)로 조회 대상과 스펙(그 폴더의 spec.json)을 정한다.

## OverseerMcp

### __init__
__init__(query: ArchiveQuery, spec: ProjectSpec | None = None)
    MCPServer(mcp 2.x) 에 결정 아카이브 도구 넷을 read_only 표시로, spec 이 있으면 스펙 도구 다섯을 등록한다. 서버 instructions 에 언제 쓰는지 적는다.

### Methods

records(query: str = '', kind: str = '', include_replaced: bool = False) -> str    # 도구 records
record(ref: str) -> str                                                            # 도구 record
decisions(query: str = '', action: str = '', limit: int = 20) -> str               # 도구 decisions
module(name: str) -> str                                                           # 도구 module
spec_view(at: str = '') -> str                                                     # 도구 spec_view. 개체 번호가 붙은 들여쓰기 글
spec_add(parent: str, kind: str, text: str) -> str                                # 도구 spec_add. kind: component | desc | do | dont | term | mock
spec_edit(id: str, text: str) -> str                                              # 도구 spec_edit. id 는 개체 번호나 title, summary
spec_remove(id: str) -> str                                                       # 도구 spec_remove. 자식 없는 개체만
spec_move(id: str, parent: str) -> str                                            # 도구 spec_move. 자식째 parent 아래 목록 끝으로
    스펙 도구는 실패를 예외 대신 `실패: 까닭` 글로 돌려준다. 개체 번호: c 구성요소, w 용어, d 설명, f 기능, n 하지 않는 것, m 목업. 점으로 잇고 1부터(c1.c2.f1).
    용어 글은 `낱말: 뜻`, 목업 글은 `이름 | 경로나 URL`.
run() -> None
    stdio 로 돈다. claude 가 띄우고 끝낸다.

## 설계 이유

- 결정 아카이브에는 쓰기 도구가 없다. 영속 지식은 사용자 승인으로만 생긴다(개발계획 5번 쓰기 경로 차단).
- 스펙은 쓰기 도구가 있다. spec.json 은 git 이 추적하는 프로젝트 파일이고, 에이전트가 통째로 읽고 쓰지 않고 번호로 필요한 부분만 다루게 하려는 것이다.
  읽고 고치는 검사는 ProjectSpec 이 사용자가 패널에서 고칠 때와 똑같이 한다. `--allowedTools mcp__overseer` 라 권한 확인 없이 쓴다.
- 패널 세션에만 --mcp-config 로 붙인다. 전역 설정이나 프로젝트 .mcp.json 을 건드리지 않는다.
