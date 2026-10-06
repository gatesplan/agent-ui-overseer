---
sources:
  overseer_server.py: c34260039c91
---
# overseer_server

패널 서버(aiohttp). 화면 파일(`web/`), API, 상태 알림과 터미널 WebSocket 을 한 포트에서 맡는다.
실행: `uv run overseer [--port 47310] [--claude-args "..."] [--data data/]`

## OverseerServer

### __init__
__init__(data_dir: Path, claude_args: str = '')
    data_dir/overseer.db, data_dir/captures/ 를 쓴다.

### Methods

cli() -> None    # staticmethod. pyproject 의 overseer 명령

### HTTP
GET    /api/tabs                탭 상태 목록
GET    /api/projects            {roots: [{root, dirs: [{name, path}]}], default_root} 새 세션 창 폴더 목록
POST   /api/tabs                {cwd | create: {root, name}, rows, cols, skip_permissions} 새 탭. create 면 Projects 안에 폴더를 만들어 연다
POST   /api/tabs/{id}/resume    {rows, cols} 이어서 띄우기
DELETE /api/tabs/{id}           세션 끝내고 탭 닫기
POST   /api/tabs/{id}/send      {message, decisions: [{id, action, note}]} 결정 저장 후 붙여넣기 전송
PUT    /api/tabs/{id}/draft     작성 중 초안 저장

### WebSocket
/ws/events      서버 → 화면: {type: 'tab', tab} | {type: 'closed', id}
/ws/term/{id}   붙으면 남은 출력부터 보낸다. 화면 → 서버: {type: 'input', data} | {type: 'resize', rows, cols}

## 설계 이유

- 훅 기록은 파일 poll(POLL_INTERVAL)로 본다. 훅이 서버에 알리는 경로를 두지 않아 서버가 꺼져 있어도 기록은 쌓인다.
- 응답에 Cache-Control: no-store 를 붙인다. web/ 를 고치고 새로고침만 하면 반영된다.
