# agent-ui-overseer

CLI 코딩 에이전트(Claude Code) 세션을 탭으로 다루고, 에이전트 응답을 사안 단위 카드로 쪼개 답변·보류·기각으로 처리하는 개인용 UI.

공식 CLI 바이너리를 그대로 띄우고 훅과 대화 기록만 읽는다. 구독 토큰을 꺼내거나 바이너리를 고치지 않는다.

## 실행

Windows, [uv](https://docs.astral.sh/uv/), Claude Code CLI(`claude`)가 있어야 한다.

```bash
uv sync
uv run python scripts/install_hooks.py   # 처음 한 번. ~/.claude/settings.json 에 훅 등록
uv run overseer                          # http://127.0.0.1:47310/
```

- 위의 `+` 로 작업 폴더를 고르면 그 폴더에서 `claude` 가 뜬다. 목록은 드라이브 루트의 `Projects` 폴더(`C:\Projects` 등) 안의 폴더이고, 없는 이름을 입력하면 거기에 새로 만든다. 전체 경로를 입력하면 다른 위치도 연다. 시작 확인 창과 첫 입력은 오른쪽 터미널 창에서 한다
- 턴이 끝나면 응답이 사안 카드로 나온다. 카드마다 처리를 고르고 `승인 및 작업`(Ctrl+Shift+Enter)을 누르면 전송 시안이 claude 입력으로 들어간다
- 작업 중 권한 확인은 터미널 창에서 직접 응답한다
- 새 세션 창에서 `--dangerously-skip-permissions` 를 고른다(기본 켬). 탭마다 남아 이어서 띄울 때도 같은 인자로 뜬다
- 모든 탭에 붙일 claude 인자: `uv run overseer --claude-args "..."`
- 패널을 다시 켜면 닫지 않은 탭이 꺼진 상태로 돌아온다. `이어서 띄우기` 로 마지막 세션을 `--resume` 한다
- 훅 제거: `uv run python scripts/install_hooks.py --remove`

훅은 전역 설정에 등록되지만 패널이 띄운 세션(환경변수 `OVERSEER_TAB`)에서만 동작한다. 다른 세션에서는 바로 끝난다.

## 구성

- `docs/item-protocol.md`: 에이전트에게 주는 사안 출력 규약. 패널 세션에는 SessionStart 훅이 넣는다
- `scripts/capture_hook.py`: 훅. 세션 시작, 입력, 턴 끝을 `data/captures/<탭 ID>.jsonl` 에 쌓는다
- `data/overseer.db`: 탭, 보낸 메시지, 사안 결정, 작성 중 초안 (SQLite)
- `src/project_manager/`: 캡처, 저장, PTY, 서버 (Ln 구조)
- `web/`: 화면. 턴을 기둥으로, 사안을 카드로 보인다

## 목업

```bash
python scripts/serve_mock.py   # http://127.0.0.1:47311/
```

서버 API 가 없으면 `web/mock-data.js` 로 동작한다.

## 상태

기본 제어 패널 첫 구현. 결정 아카이브(`[D]`, `[W]` 보존, 조회)는 아직 없다. 방향은 `개발계획.md`.
