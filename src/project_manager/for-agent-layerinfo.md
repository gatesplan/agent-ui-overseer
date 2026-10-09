# for-agent-layerinfo.md

<!-- lnt:generated:start -->
## l0
- capture_log: 탭 하나의 훅 기록 JSONL(data/captures/<탭 ID>.jsonl)을 이어서 읽는다
- decision_store: 패널 저장소(SQLite). 탭, 보낸 메시지, 사안 결정, 작성 중 초안
- item: 응답에서 분리한 사안 하나의 데이터 객체
- permission_gate: 권한 요청 훅과 패널 화면 사이의 결정 전달(결정 파일)
- project_finder: 새 세션 창의 프로젝트 폴더 목록과 새 폴더 만들기
- record_store: 프로젝트 결정 아카이브. 승인된 보존 사안([D] 결정 기록, [W] 용어)
- transcript_reader: Claude Code 대화 기록 JSONL 에서 턴 응답, 입력, 사용량을 꺼낸다
- turn_builder: 훅 기록을 화면이 쓰는 턴 목록으로 조립한다

## l1
- archive_query: 한 프로젝트의 결정 아카이브 조회(읽기 전용). 에이전트용 짧은 글로 돌려준다
- item_splitter: 응답 텍스트를 `### [종류] 제목` 단위 사안으로 나눈다
- pty_session: pywinpty(ConPTY)로 띄운 프로세스 하나의 입출력

## l2
- agent_tab: 패널 탭 하나. claude 프로세스, 훅 기록, 결정 저장을 묶어 화면 상태를 만든다
- capture_hook: 패널이 띄운 claude 세션의 훅 진입점
- overseer_mcp: 결정 아카이브 조회를 MCP 도구로 내놓는 읽기 전용 서버(stdio)

## l3
- tab_manager: 열린 탭 목록. 띄우기, 복원, 이어서 띄우기, 닫기

## l4
- overseer_server: 패널 서버(aiohttp). 화면 파일, API, 상태 알림과 터미널 WebSocket
<!-- lnt:generated:end -->

## Notes

