# agent-ui-overseer

CLI 코딩 에이전트(Claude Code) 세션을 탭으로 다루고, 에이전트 응답을 사안 단위 카드로 쪼개 답변·보류·기각으로 처리하는 개인용 UI.

공식 CLI 바이너리를 그대로 띄우고 훅과 대화 기록만 읽는다. 구독 토큰을 꺼내거나 바이너리를 고치지 않는다.

## 설치와 실행

Windows 전용. Claude Code CLI, [uv](https://docs.astral.sh/uv/) 가 있어야 한다. 자세한 절차, 옵션, 문제 해결, 제거는 [INSTALL.md](INSTALL.md).
에이전트에게 설치를 맡길 때는 이 저장소 주소와 함께 `INSTALL.md 를 따라 설치해 줘` 라고 하면 된다.

```bash
uv sync
uv run python scripts/setup.py   # 전역 훅 등록과 점검. 처음 한 번
uv run overseer                  # http://127.0.0.1:47310/
```

- `+` 로 작업 폴더를 고르면 그 폴더에서 `claude` 가 뜬다. 목록은 드라이브 루트의 `Projects` 폴더(`--projects` 로 바꿀 수 있다)
- 턴이 끝나면 응답이 사안 카드로 나온다. 카드마다 처리를 고르고 `승인 및 작업`(Ctrl+Shift+Enter)을 누르면 전송 시안이 claude 입력으로 들어간다
- 시작 확인 창과 첫 입력은 오른쪽 터미널 창에서 한다
- 작업 중 권한 확인이 필요하면 흐름 위에 띠가 뜬다. 거기서 허용·거부하거나 터미널 확인 창으로 넘긴다
- 응답의 `[D]`(결정 기록), `[W]`(용어) 사안을 승인하면 프로젝트별로 보존되고, 다음 세션 시작 때 에이전트에게 들어간다. 흐름 막대의 `기록` 에서 본다
- 패널 세션에는 읽기 전용 MCP 서버 `overseer` 가 붙는다. 에이전트가 기록 이력, 근거, 지난 결정과 기각 사유를 찾아본다
- 턴마다 토큰 사용량을 훅 기록에 남긴다. 비교: `python scripts/token_report.py --days 7 --turns 5`
- 패널을 다시 켜면 닫지 않은 탭이 꺼진 상태로 돌아온다. `이어서 띄우기` 로 마지막 세션을 `--resume` 한다

## 구성

- `docs/item-protocol.md`: 에이전트에게 주는 사안 출력 규약. 패널 세션에는 SessionStart 훅이 넣는다
- `scripts/capture_hook.py`: 훅. 세션 시작, 입력, 턴 끝을 `data/captures/<탭 ID>.jsonl` 에 쌓는다
- `scripts/setup.py`: 훅 등록, 점검, 제거
- `<프로젝트>/.overseer/`: 그 프로젝트의 세션 이력(`sessions/<번호>.jsonl`: 사안, 결정, 책임 변경)과 보존 기록(`records/D-3.md`). 폴더 안 `.gitignore` 로 git 에서 빠진다
- `data/overseer.db`: 이 컴퓨터의 탭, 보낸 메시지, 작성 중 초안 (SQLite)
- `src/project_manager/`: 캡처, 저장, PTY, 서버 (Ln 구조)
- `web/`: 화면. 턴을 기둥으로, 사안을 카드로 보인다. 서버 API 가 없으면 목업 모드(`python scripts/serve_mock.py`, 47311)

## 상태

기본 제어 패널. 결정 아카이브(`[D]`, `[W]` 보존, 조회)는 아직 없다. 방향은 `개발계획.md`.
macOS, Linux 지원은 없다. PTY(`l1/pty_session`)와 실행 명령(`l2/agent_tab`), 훅 경로(`scripts/setup.py`)를 운영체제별로 나누면 된다.
