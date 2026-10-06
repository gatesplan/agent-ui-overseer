---
sources:
  overseer_server.py: 474877a566ed
---
# overseer_server

패널 서버(aiohttp). 화면 파일(`web/`), API, 상태 알림과 터미널 WebSocket 을 한 포트에서 맡는다.
실행: `uv run overseer [--port 47310] [--projects DIR ...] [--claude-args "..."] [--data data/]`
--projects 가 없으면 환경변수 OVERSEER_PROJECTS(os.pathsep 구분), 그것도 없으면 드라이브마다 루트의 Projects 폴더.

## OverseerServer

### __init__
__init__(data_dir: Path, claude_args: str = '', project_roots: list[str] | None = None)
    data_dir/overseer.db, data_dir/captures/ 를 쓴다. project_roots 는 ProjectFinder 에 넘긴다.

### Methods

cli() -> None    # staticmethod. pyproject 의 overseer 명령

### HTTP
GET    /api/tabs                탭 상태 목록
GET    /api/health              {ok, permissions} 훅이 권한 결정을 맡겨도 되는지 묻는다
POST   /api/tabs/{id}/permission {request_id, behavior: allow | deny | terminal, message} 화면의 권한 결정
GET    /api/projects            {roots: [{root, dirs: [{name, path}]}], default_root} 새 세션 창 폴더 목록
POST   /api/tabs                {cwd | create: {root, name}, rows, cols, skip_permissions} 새 탭. create 면 Projects 안에 폴더를 만들어 연다
POST   /api/tabs/{id}/resume    {rows, cols} 이어서 띄우기
DELETE /api/tabs/{id}           세션 끝내고 탭 닫기
POST   /api/tabs/{id}/send      {message, decisions: [{id, action, note}]} 결정 저장 후 붙여넣기 전송
PUT    /api/tabs/{id}/draft     작성 중 초안 저장

### WebSocket
/ws/events      서버 → 화면: {type: 'tab', tab} | {type: 'closed', id}
/ws/term/{id}   붙으면 남은 출력부터 보낸다. 화면 → 서버: {type: 'input', data} | {type: 'resize', rows, cols}
                입력이 들어오면 떠 있던 확인 알림을 내린다(AgentTab.acknowledge)

탭에 붙이는 MCP 서버는 이 서버와 같은 파이썬(sys.executable)으로 scripts/overseer_mcp.py 를 띄운다.
cli 는 OVERSEER_PORT, OVERSEER_DATA 를 환경에 넣는다. 자식 claude 의 훅이 이것으로 서버와 기록 폴더를 찾는다.

## 설계 이유

- 훅 기록은 파일 poll(POLL_INTERVAL)로 본다. 훅이 서버에 알리는 경로를 두지 않아 서버가 꺼져 있어도 기록은 쌓인다.
- 응답에 Cache-Control: no-store 를 붙인다. web/ 를 고치고 새로고침만 하면 반영된다.
