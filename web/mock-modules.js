// 목업용 모듈 지도(lnt map --json format 2). honetnest 와 project_manager 를 스캔한 결과에 소스 없는 패키지 webapp 을 더했다
window.MOCK_MODULES = {
 "format": 2,
 "packages": [
  {
   "package": "honetnest",
   "package_root": "src/honetnest",
   "modules": [
    {
     "name": "l0.text_decoder",
     "scope": "",
     "layer": 0,
     "computed": 0,
     "nested": false,
     "external": false,
     "path": "src/honetnest/l0/text_decoder",
     "responsibility": "바이트 → 문자열. BOM/UTF-16/UTF-8/cp949 판별, 예외 없음"
    },
    {
     "name": "l0.text_normalizer",
     "scope": "",
     "layer": 0,
     "computed": 0,
     "nested": false,
     "external": false,
     "path": "src/honetnest/l0/text_normalizer",
     "responsibility": "서로게이트·BOM·제어문자 제거, CRLF→LF, NFC"
    },
    {
     "name": "l1.cli_io",
     "scope": "",
     "layer": 1,
     "computed": 1,
     "nested": false,
     "external": true,
     "path": "src/honetnest/l1/cli_io",
     "responsibility": "셸 공통 처리. 콘솔 인코딩 방어(guard_console), loguru 수준(setup_logging), --text/--file/--stdin 본문 읽기(read_text)"
    },
    {
     "name": "l1.env_loader",
     "scope": "",
     "layer": 1,
     "computed": 1,
     "nested": false,
     "external": true,
     "path": "src/honetnest/l1/env_loader",
     "responsibility": "cwd .env → ~/.honetnest/.env 순으로 환경변수 로딩 (기존 값은 덮지 않음)"
    },
    {
     "name": "l2.discord_plug",
     "scope": "",
     "layer": 2,
     "computed": 2,
     "nested": true,
     "external": true,
     "path": "src/honetnest/l2/discord_plug",
     "responsibility": "DiscordPlug. Discord webhook 전송, 2000자 자동 분할. 명령 `discord-plug`"
    },
    {
     "name": "l2.gdrive_plug",
     "scope": "",
     "layer": 2,
     "computed": 2,
     "nested": true,
     "external": true,
     "path": "src/honetnest/l2/gdrive_plug",
     "responsibility": "GdrivePlug. rclone으로 구글 드라이브 업로드 후 공유 링크, 만료 공유 정리. 명령 `gdrive-plug`"
    },
    {
     "name": "l2.kakao_plug",
     "scope": "",
     "layer": 2,
     "computed": 2,
     "nested": true,
     "external": true,
     "path": "src/honetnest/l2/kakao_plug",
     "responsibility": "KakaoPlug. PC 카카오톡 창 조작으로 채팅방 전송, honetnest 서명. 명령 `kakao-plug`"
    },
    {
     "name": "l2.discord_plug.l0.message_chunker",
     "scope": "l2.discord_plug",
     "layer": 0,
     "computed": 0,
     "nested": false,
     "external": false,
     "path": "src/honetnest/l2/discord_plug/l0/message_chunker",
     "responsibility": null
    },
    {
     "name": "l2.discord_plug.l1.webhook_client",
     "scope": "l2.discord_plug",
     "layer": 1,
     "computed": 1,
     "nested": false,
     "external": true,
     "path": "src/honetnest/l2/discord_plug/l1/webhook_client",
     "responsibility": null
    },
    {
     "name": "l2.discord_plug.l2.cli",
     "scope": "l2.discord_plug",
     "layer": 2,
     "computed": 0,
     "nested": false,
     "external": false,
     "path": "src/honetnest/l2/discord_plug/l2/cli",
     "responsibility": null
    },
    {
     "name": "l2.discord_plug.l3.plug",
     "scope": "l2.discord_plug",
     "layer": 3,
     "computed": 3,
     "nested": false,
     "external": true,
     "path": "src/honetnest/l2/discord_plug/l3/plug",
     "responsibility": null
    },
    {
     "name": "l2.gdrive_plug.l0.share_namer",
     "scope": "l2.gdrive_plug",
     "layer": 0,
     "computed": 0,
     "nested": false,
     "external": false,
     "path": "src/honetnest/l2/gdrive_plug/l0/share_namer",
     "responsibility": null
    },
    {
     "name": "l2.gdrive_plug.l1.rclone_runner",
     "scope": "l2.gdrive_plug",
     "layer": 1,
     "computed": 1,
     "nested": false,
     "external": true,
     "path": "src/honetnest/l2/gdrive_plug/l1/rclone_runner",
     "responsibility": null
    },
    {
     "name": "l2.gdrive_plug.l2.cli",
     "scope": "l2.gdrive_plug",
     "layer": 2,
     "computed": 0,
     "nested": false,
     "external": false,
     "path": "src/honetnest/l2/gdrive_plug/l2/cli",
     "responsibility": null
    },
    {
     "name": "l2.gdrive_plug.l3.plug",
     "scope": "l2.gdrive_plug",
     "layer": 3,
     "computed": 3,
     "nested": false,
     "external": true,
     "path": "src/honetnest/l2/gdrive_plug/l3/plug",
     "responsibility": null
    },
    {
     "name": "l2.kakao_plug.l0.message_composer",
     "scope": "l2.kakao_plug",
     "layer": 0,
     "computed": 0,
     "nested": false,
     "external": false,
     "path": "src/honetnest/l2/kakao_plug/l0/message_composer",
     "responsibility": null
    },
    {
     "name": "l2.kakao_plug.l1.kakao_window",
     "scope": "l2.kakao_plug",
     "layer": 1,
     "computed": 1,
     "nested": false,
     "external": true,
     "path": "src/honetnest/l2/kakao_plug/l1/kakao_window",
     "responsibility": null
    },
    {
     "name": "l2.kakao_plug.l2.cli",
     "scope": "l2.kakao_plug",
     "layer": 2,
     "computed": 0,
     "nested": false,
     "external": false,
     "path": "src/honetnest/l2/kakao_plug/l2/cli",
     "responsibility": null
    },
    {
     "name": "l2.kakao_plug.l3.plug",
     "scope": "l2.kakao_plug",
     "layer": 3,
     "computed": 3,
     "nested": false,
     "external": true,
     "path": "src/honetnest/l2/kakao_plug/l3/plug",
     "responsibility": null
    }
   ],
   "edges": [
    {
     "src": "l1.cli_io",
     "dst": "l0.text_decoder",
     "kind": "runtime",
     "file": "src/honetnest/l1/cli_io/CliIO.py",
     "line": 6
    },
    {
     "src": "l2.discord_plug.l2.cli",
     "dst": "l1.cli_io",
     "kind": "runtime",
     "file": "src/honetnest/l2/discord_plug/l2/cli/Cli.py",
     "line": 5
    },
    {
     "src": "l2.discord_plug.l3.plug",
     "dst": "l0.text_decoder",
     "kind": "runtime",
     "file": "src/honetnest/l2/discord_plug/l3/plug/DiscordPlug.py",
     "line": 6
    },
    {
     "src": "l2.discord_plug.l3.plug",
     "dst": "l0.text_normalizer",
     "kind": "runtime",
     "file": "src/honetnest/l2/discord_plug/l3/plug/DiscordPlug.py",
     "line": 6
    },
    {
     "src": "l2.discord_plug.l3.plug",
     "dst": "l1.env_loader",
     "kind": "runtime",
     "file": "src/honetnest/l2/discord_plug/l3/plug/DiscordPlug.py",
     "line": 7
    },
    {
     "src": "l2.discord_plug.l3.plug",
     "dst": "l2.discord_plug.l0.message_chunker",
     "kind": "runtime",
     "file": "src/honetnest/l2/discord_plug/l3/plug/DiscordPlug.py",
     "line": 8
    },
    {
     "src": "l2.discord_plug.l3.plug",
     "dst": "l2.discord_plug.l1.webhook_client",
     "kind": "runtime",
     "file": "src/honetnest/l2/discord_plug/l3/plug/DiscordPlug.py",
     "line": 9
    },
    {
     "src": "l2.discord_plug.l3.plug",
     "dst": "l2.discord_plug.l2.cli",
     "kind": "runtime",
     "file": "src/honetnest/l2/discord_plug/l3/plug/DiscordPlug.py",
     "line": 10
    },
    {
     "src": "l2.gdrive_plug.l2.cli",
     "dst": "l1.cli_io",
     "kind": "runtime",
     "file": "src/honetnest/l2/gdrive_plug/l2/cli/Cli.py",
     "line": 5
    },
    {
     "src": "l2.gdrive_plug.l3.plug",
     "dst": "l1.env_loader",
     "kind": "runtime",
     "file": "src/honetnest/l2/gdrive_plug/l3/plug/GdrivePlug.py",
     "line": 7
    },
    {
     "src": "l2.gdrive_plug.l3.plug",
     "dst": "l2.gdrive_plug.l0.share_namer",
     "kind": "runtime",
     "file": "src/honetnest/l2/gdrive_plug/l3/plug/GdrivePlug.py",
     "line": 8
    },
    {
     "src": "l2.gdrive_plug.l3.plug",
     "dst": "l2.gdrive_plug.l1.rclone_runner",
     "kind": "runtime",
     "file": "src/honetnest/l2/gdrive_plug/l3/plug/GdrivePlug.py",
     "line": 9
    },
    {
     "src": "l2.gdrive_plug.l3.plug",
     "dst": "l2.gdrive_plug.l2.cli",
     "kind": "runtime",
     "file": "src/honetnest/l2/gdrive_plug/l3/plug/GdrivePlug.py",
     "line": 10
    },
    {
     "src": "l2.kakao_plug.l2.cli",
     "dst": "l1.cli_io",
     "kind": "runtime",
     "file": "src/honetnest/l2/kakao_plug/l2/cli/Cli.py",
     "line": 5
    },
    {
     "src": "l2.kakao_plug.l3.plug",
     "dst": "l0.text_decoder",
     "kind": "runtime",
     "file": "src/honetnest/l2/kakao_plug/l3/plug/KakaoPlug.py",
     "line": 6
    },
    {
     "src": "l2.kakao_plug.l3.plug",
     "dst": "l0.text_normalizer",
     "kind": "runtime",
     "file": "src/honetnest/l2/kakao_plug/l3/plug/KakaoPlug.py",
     "line": 6
    },
    {
     "src": "l2.kakao_plug.l3.plug",
     "dst": "l1.env_loader",
     "kind": "runtime",
     "file": "src/honetnest/l2/kakao_plug/l3/plug/KakaoPlug.py",
     "line": 7
    },
    {
     "src": "l2.kakao_plug.l3.plug",
     "dst": "l2.kakao_plug.l0.message_composer",
     "kind": "runtime",
     "file": "src/honetnest/l2/kakao_plug/l3/plug/KakaoPlug.py",
     "line": 8
    },
    {
     "src": "l2.kakao_plug.l3.plug",
     "dst": "l2.kakao_plug.l1.kakao_window",
     "kind": "runtime",
     "file": "src/honetnest/l2/kakao_plug/l3/plug/KakaoPlug.py",
     "line": 9
    },
    {
     "src": "l2.kakao_plug.l3.plug",
     "dst": "l2.kakao_plug.l2.cli",
     "kind": "runtime",
     "file": "src/honetnest/l2/kakao_plug/l3/plug/KakaoPlug.py",
     "line": 10
    }
   ],
   "violations": [
    {
     "code": "C3",
     "module": "l2.discord_plug.l2.cli",
     "file": "src/honetnest/l2/discord_plug/l2/cli/__init__.py",
     "line": 0,
     "message": "선언 l2, 계산 l0. lnt move l2.discord_plug.l2.cli l0"
    },
    {
     "code": "C3",
     "module": "l2.gdrive_plug.l2.cli",
     "file": "src/honetnest/l2/gdrive_plug/l2/cli/__init__.py",
     "line": 0,
     "message": "선언 l2, 계산 l0. lnt move l2.gdrive_plug.l2.cli l0"
    },
    {
     "code": "C3",
     "module": "l2.kakao_plug.l2.cli",
     "file": "src/honetnest/l2/kakao_plug/l2/cli/__init__.py",
     "line": 0,
     "message": "선언 l2, 계산 l0. lnt move l2.kakao_plug.l2.cli l0"
    }
   ],
   "orphans": [],
   "language": "python"
  },
  {
   "package": "project_manager",
   "package_root": "src/project_manager",
   "language": "python",
   "modules": [
    {
     "name": "l0.capture_log",
     "scope": "",
     "layer": 0,
     "computed": 0,
     "nested": false,
     "external": false,
     "path": "src/project_manager/l0/capture_log",
     "responsibility": "탭마다 훅이 남긴 캡처 기록을 맡는다"
    },
    {
     "name": "l0.conda_envs",
     "scope": "",
     "layer": 0,
     "computed": 0,
     "nested": false,
     "external": false,
     "path": "src/project_manager/l0/conda_envs",
     "responsibility": "이 컴퓨터의 conda 환경 목록을 알려 준다"
    },
    {
     "name": "l0.install_layout",
     "scope": "",
     "layer": 0,
     "computed": 0,
     "nested": false,
     "external": false,
     "path": "src/project_manager/l0/install_layout",
     "responsibility": "overseer 가 놓인 자리에서 화면, 규약, 실행 스크립트, 기록 폴더를 찾아 준다"
    },
    {
     "name": "l0.item",
     "scope": "",
     "layer": 0,
     "computed": 0,
     "nested": false,
     "external": false,
     "path": "src/project_manager/l0/item",
     "responsibility": "사안 하나가 무엇인지 정한다"
    },
    {
     "name": "l0.launch_env",
     "scope": "",
     "layer": 0,
     "computed": 0,
     "nested": false,
     "external": false,
     "path": "src/project_manager/l0/launch_env",
     "responsibility": "프로젝트의 탭 실행 환경을 그 프로젝트 폴더에 지킨다"
    },
    {
     "name": "l0.module_map",
     "scope": "",
     "layer": 0,
     "computed": 0,
     "nested": false,
     "external": false,
     "path": "src/project_manager/l0/module_map",
     "responsibility": "프로젝트의 모듈 지도를 lnt 에게서 받아 온다"
    },
    {
     "name": "l0.panel_store",
     "scope": "",
     "layer": 0,
     "computed": 0,
     "nested": false,
     "external": false,
     "path": "src/project_manager/l0/panel_store",
     "responsibility": "이 컴퓨터의 패널 상태(탭, 보낸 메시지, 작성 중인 처리)를 지킨다"
    },
    {
     "name": "l0.permission_gate",
     "scope": "",
     "layer": 0,
     "computed": 0,
     "nested": false,
     "external": false,
     "path": "src/project_manager/l0/permission_gate",
     "responsibility": "에이전트의 권한 요청을 패널 사용자에게 넘기고 답을 돌려준다"
    },
    {
     "name": "l0.project_finder",
     "scope": "",
     "layer": 0,
     "computed": 0,
     "nested": false,
     "external": false,
     "path": "src/project_manager/l0/project_finder",
     "responsibility": "새 세션을 열 수 있는 프로젝트 폴더를 찾아 준다"
    },
    {
     "name": "l0.project_journal",
     "scope": "",
     "layer": 0,
     "computed": 0,
     "nested": false,
     "external": false,
     "path": "src/project_manager/l0/project_journal",
     "responsibility": "프로젝트의 세션 이력(사안, 결정, 책임 변경)을 그 프로젝트 폴더에 지킨다"
    },
    {
     "name": "l0.record_store",
     "scope": "",
     "layer": 0,
     "computed": 0,
     "nested": false,
     "external": false,
     "path": "src/project_manager/l0/record_store",
     "responsibility": "프로젝트의 영속 지식(결정 기록과 용어)을 지킨다"
    },
    {
     "name": "l0.transcript_reader",
     "scope": "",
     "layer": 0,
     "computed": 0,
     "nested": false,
     "external": false,
     "path": "src/project_manager/l0/transcript_reader",
     "responsibility": "Claude Code 대화 기록에서 턴의 사실을 읽어 낸다"
    },
    {
     "name": "l0.turn_builder",
     "scope": "",
     "layer": 0,
     "computed": 0,
     "nested": false,
     "external": false,
     "path": "src/project_manager/l0/turn_builder",
     "responsibility": "캡처 기록을 턴과 사안의 흐름으로 엮는다"
    },
    {
     "name": "l1.archive_query",
     "scope": "",
     "layer": 1,
     "computed": 1,
     "nested": false,
     "external": false,
     "path": "src/project_manager/l1/archive_query",
     "responsibility": "결정 아카이브에 대한 물음에 답한다"
    },
    {
     "name": "l1.hook_installer",
     "scope": "",
     "layer": 1,
     "computed": 1,
     "nested": false,
     "external": false,
     "path": "src/project_manager/l1/hook_installer",
     "responsibility": "Claude Code 에 패널 훅을 걸고 풀며 설치 상태를 점검한다"
    },
    {
     "name": "l1.item_splitter",
     "scope": "",
     "layer": 1,
     "computed": 1,
     "nested": false,
     "external": false,
     "path": "src/project_manager/l1/item_splitter",
     "responsibility": "에이전트 응답을 사안 단위로 나눈다"
    },
    {
     "name": "l1.map_watcher",
     "scope": "",
     "layer": 1,
     "computed": 1,
     "nested": false,
     "external": false,
     "path": "src/project_manager/l1/map_watcher",
     "responsibility": "화면이 연 프로젝트들의 모듈 지도를 최신으로 지킨다"
    },
    {
     "name": "l1.pty_session",
     "scope": "",
     "layer": 1,
     "computed": 1,
     "nested": false,
     "external": true,
     "path": "src/project_manager/l1/pty_session",
     "responsibility": "공식 CLI 프로세스 하나를 터미널째로 붙잡는다"
    },
    {
     "name": "l2.agent_tab",
     "scope": "",
     "layer": 2,
     "computed": 2,
     "nested": false,
     "external": true,
     "path": "src/project_manager/l2/agent_tab",
     "responsibility": "세션 탭 하나의 상태와 행동을 맡는다"
    },
    {
     "name": "l2.capture_hook",
     "scope": "",
     "layer": 2,
     "computed": 2,
     "nested": false,
     "external": true,
     "path": "src/project_manager/l2/capture_hook",
     "responsibility": "Claude Code 훅으로 들어온 사건을 패널 기록으로 남긴다"
    },
    {
     "name": "l2.overseer_mcp",
     "scope": "",
     "layer": 2,
     "computed": 2,
     "nested": false,
     "external": true,
     "path": "src/project_manager/l2/overseer_mcp",
     "responsibility": "에이전트에게 결정 아카이브를 읽기 전용으로 내준다"
    },
    {
     "name": "l3.tab_manager",
     "scope": "",
     "layer": 3,
     "computed": 3,
     "nested": false,
     "external": true,
     "path": "src/project_manager/l3/tab_manager",
     "responsibility": "열린 탭들의 생애를 맡는다"
    },
    {
     "name": "l4.overseer_server",
     "scope": "",
     "layer": 4,
     "computed": 4,
     "nested": false,
     "external": true,
     "path": "src/project_manager/l4/overseer_server",
     "responsibility": "패널 화면과 탭들을 잇는다"
    }
   ],
   "edges": [
    {
     "src": "l1.archive_query",
     "dst": "l0.project_journal",
     "kind": "runtime",
     "file": "src/project_manager/l1/archive_query/archive_query.py",
     "line": 5
    },
    {
     "src": "l1.archive_query",
     "dst": "l0.record_store",
     "kind": "runtime",
     "file": "src/project_manager/l1/archive_query/archive_query.py",
     "line": 6
    },
    {
     "src": "l1.hook_installer",
     "dst": "l0.install_layout",
     "kind": "runtime",
     "file": "src/project_manager/l1/hook_installer/hook_installer.py",
     "line": 11
    },
    {
     "src": "l1.item_splitter",
     "dst": "l0.item",
     "kind": "runtime",
     "file": "src/project_manager/l1/item_splitter/item_splitter.py",
     "line": 3
    },
    {
     "src": "l1.map_watcher",
     "dst": "l0.module_map",
     "kind": "runtime",
     "file": "src/project_manager/l1/map_watcher/map_watcher.py",
     "line": 5
    },
    {
     "src": "l2.agent_tab",
     "dst": "l0.capture_log",
     "kind": "runtime",
     "file": "src/project_manager/l2/agent_tab/agent_tab.py",
     "line": 11
    },
    {
     "src": "l2.agent_tab",
     "dst": "l0.launch_env",
     "kind": "runtime",
     "file": "src/project_manager/l2/agent_tab/agent_tab.py",
     "line": 12
    },
    {
     "src": "l2.agent_tab",
     "dst": "l0.module_map",
     "kind": "runtime",
     "file": "src/project_manager/l2/agent_tab/agent_tab.py",
     "line": 13
    },
    {
     "src": "l2.agent_tab",
     "dst": "l0.panel_store",
     "kind": "runtime",
     "file": "src/project_manager/l2/agent_tab/agent_tab.py",
     "line": 14
    },
    {
     "src": "l2.agent_tab",
     "dst": "l0.permission_gate",
     "kind": "runtime",
     "file": "src/project_manager/l2/agent_tab/agent_tab.py",
     "line": 15
    },
    {
     "src": "l2.agent_tab",
     "dst": "l0.project_journal",
     "kind": "runtime",
     "file": "src/project_manager/l2/agent_tab/agent_tab.py",
     "line": 16
    },
    {
     "src": "l2.agent_tab",
     "dst": "l0.record_store",
     "kind": "runtime",
     "file": "src/project_manager/l2/agent_tab/agent_tab.py",
     "line": 17
    },
    {
     "src": "l2.agent_tab",
     "dst": "l0.turn_builder",
     "kind": "runtime",
     "file": "src/project_manager/l2/agent_tab/agent_tab.py",
     "line": 18
    },
    {
     "src": "l2.agent_tab",
     "dst": "l1.pty_session",
     "kind": "runtime",
     "file": "src/project_manager/l2/agent_tab/agent_tab.py",
     "line": 19
    },
    {
     "src": "l2.capture_hook",
     "dst": "l0.permission_gate",
     "kind": "runtime",
     "file": "src/project_manager/l2/capture_hook/capture_hook.py",
     "line": 7
    },
    {
     "src": "l2.capture_hook",
     "dst": "l0.project_journal",
     "kind": "runtime",
     "file": "src/project_manager/l2/capture_hook/capture_hook.py",
     "line": 8
    },
    {
     "src": "l2.capture_hook",
     "dst": "l0.record_store",
     "kind": "runtime",
     "file": "src/project_manager/l2/capture_hook/capture_hook.py",
     "line": 9
    },
    {
     "src": "l2.capture_hook",
     "dst": "l0.transcript_reader",
     "kind": "runtime",
     "file": "src/project_manager/l2/capture_hook/capture_hook.py",
     "line": 10
    },
    {
     "src": "l2.capture_hook",
     "dst": "l1.item_splitter",
     "kind": "runtime",
     "file": "src/project_manager/l2/capture_hook/capture_hook.py",
     "line": 11
    },
    {
     "src": "l2.overseer_mcp",
     "dst": "l1.archive_query",
     "kind": "runtime",
     "file": "src/project_manager/l2/overseer_mcp/overseer_mcp.py",
     "line": 4
    },
    {
     "src": "l3.tab_manager",
     "dst": "l0.panel_store",
     "kind": "runtime",
     "file": "src/project_manager/l3/tab_manager/tab_manager.py",
     "line": 7
    },
    {
     "src": "l3.tab_manager",
     "dst": "l0.record_store",
     "kind": "runtime",
     "file": "src/project_manager/l3/tab_manager/tab_manager.py",
     "line": 8
    },
    {
     "src": "l3.tab_manager",
     "dst": "l2.agent_tab",
     "kind": "runtime",
     "file": "src/project_manager/l3/tab_manager/tab_manager.py",
     "line": 9
    },
    {
     "src": "l4.overseer_server",
     "dst": "l0.conda_envs",
     "kind": "runtime",
     "file": "src/project_manager/l4/overseer_server/overseer_server.py",
     "line": 11
    },
    {
     "src": "l4.overseer_server",
     "dst": "l0.install_layout",
     "kind": "runtime",
     "file": "src/project_manager/l4/overseer_server/overseer_server.py",
     "line": 12
    },
    {
     "src": "l4.overseer_server",
     "dst": "l0.launch_env",
     "kind": "runtime",
     "file": "src/project_manager/l4/overseer_server/overseer_server.py",
     "line": 13
    },
    {
     "src": "l4.overseer_server",
     "dst": "l0.module_map",
     "kind": "runtime",
     "file": "src/project_manager/l4/overseer_server/overseer_server.py",
     "line": 14
    },
    {
     "src": "l4.overseer_server",
     "dst": "l0.panel_store",
     "kind": "runtime",
     "file": "src/project_manager/l4/overseer_server/overseer_server.py",
     "line": 15
    },
    {
     "src": "l4.overseer_server",
     "dst": "l0.project_finder",
     "kind": "runtime",
     "file": "src/project_manager/l4/overseer_server/overseer_server.py",
     "line": 16
    },
    {
     "src": "l4.overseer_server",
     "dst": "l0.record_store",
     "kind": "runtime",
     "file": "src/project_manager/l4/overseer_server/overseer_server.py",
     "line": 17
    },
    {
     "src": "l4.overseer_server",
     "dst": "l1.map_watcher",
     "kind": "runtime",
     "file": "src/project_manager/l4/overseer_server/overseer_server.py",
     "line": 18
    },
    {
     "src": "l4.overseer_server",
     "dst": "l2.agent_tab",
     "kind": "runtime",
     "file": "src/project_manager/l4/overseer_server/overseer_server.py",
     "line": 19
    },
    {
     "src": "l4.overseer_server",
     "dst": "l3.tab_manager",
     "kind": "runtime",
     "file": "src/project_manager/l4/overseer_server/overseer_server.py",
     "line": 20
    }
   ],
   "violations": [],
   "orphans": []
  },
  {
   "package": "webapp",
   "package_root": "src/webapp",
   "language": null,
   "modules": [],
   "edges": [],
   "violations": [],
   "orphans": []
  }
 ]
};
