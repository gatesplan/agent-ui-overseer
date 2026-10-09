# for-agent-layerinfo.md

<!-- lnt:generated:start -->
## l0
- capture_log: 탭마다 훅이 남긴 캡처 기록을 맡는다
- install_layout: overseer 가 놓인 자리에서 화면, 규약, 실행 스크립트, 기록 폴더를 찾아 준다
- item: 사안 하나가 무엇인지 정한다
- module_map: 프로젝트의 모듈 지도를 lnt 에게서 받아 온다
- panel_store: 이 컴퓨터의 패널 상태(탭, 보낸 메시지, 작성 중인 처리)를 지킨다
- permission_gate: 에이전트의 권한 요청을 패널 사용자에게 넘기고 답을 돌려준다
- project_finder: 새 세션을 열 수 있는 프로젝트 폴더를 찾아 준다
- project_journal: 프로젝트의 세션 이력(사안, 결정, 책임 변경)을 그 프로젝트 폴더에 지킨다
- record_store: 프로젝트의 영속 지식(결정 기록과 용어)을 지킨다
- transcript_reader: Claude Code 대화 기록에서 턴의 사실을 읽어 낸다
- turn_builder: 캡처 기록을 턴과 사안의 흐름으로 엮는다

## l1
- archive_query: 결정 아카이브에 대한 물음에 답한다
- hook_installer: Claude Code 에 패널 훅을 걸고 풀며 설치 상태를 점검한다
- item_splitter: 에이전트 응답을 사안 단위로 나눈다
- map_watcher: 화면이 연 프로젝트들의 모듈 지도를 최신으로 지킨다
- pty_session: 공식 CLI 프로세스 하나를 터미널째로 붙잡는다

## l2
- agent_tab: 세션 탭 하나의 상태와 행동을 맡는다
- capture_hook: Claude Code 훅으로 들어온 사건을 패널 기록으로 남긴다
- overseer_mcp: 에이전트에게 결정 아카이브를 읽기 전용으로 내준다

## l3
- tab_manager: 열린 탭들의 생애를 맡는다

## l4
- overseer_server: 패널 화면과 탭들을 잇는다
<!-- lnt:generated:end -->

## Notes

