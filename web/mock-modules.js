// 목업용 모듈 지도. honetnest 를 lnt map --json 형식으로 스캔한 결과
window.MOCK_MODULES = {
 "format": 1,
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
 "orphans": []
};
