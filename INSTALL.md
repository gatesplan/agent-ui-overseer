# 설치 안내 (에이전트용)

이 문서를 읽은 에이전트가 사용자의 Windows 컴퓨터에 Overseer 를 설치하고 실행할 수 있게 쓴다. 순서대로 따른다.

## 0. 요구 사항

- Windows 10/11. macOS, Linux 는 지원하지 않는다(PTY 가 pywinpty/ConPTY 기반)
- Claude Code CLI: `claude` 명령이 PATH 에 있고 로그인되어 있어야 한다
- [uv](https://docs.astral.sh/uv/), git
- 인터넷: 화면이 xterm.js 와 글꼴을 CDN 에서 받는다
- 모듈 패널은 ln 구조 프로젝트의 모듈 지도를 `lnt map --json` 으로 받는다. `lnt`(ff-lntools)는 의존성이라 `uv sync` 로 같은 환경에 설치되고, 패널은 그것을 먼저 쓴다. 없으면 `OVERSEER_LNT`, 그다음 PATH 의 `lnt`

## 1. 설치

쓰기만 할 때는 도구로 설치한다.

```bash
uv tool install git+https://github.com/gatesplan/agent-ui-overseer
overseer-setup
```

고치면서 쓸 때는 저장소를 받는다. 명령은 `uv run` 을 붙여 같다(`uv run overseer-setup`, 또는 `uv run python scripts/setup.py`).

```bash
git clone https://github.com/gatesplan/agent-ui-overseer
cd agent-ui-overseer
uv sync
uv run overseer-setup
```

`overseer-setup` 은 Claude Code 전역 설정(`~/.claude/settings.json`)에 훅 5개(SessionStart, UserPromptSubmit, Stop, Notification, PermissionRequest)를 등록하고 점검한다.
설치를 갱신(`uv tool upgrade project-overseer` 나 git pull)한 뒤에도 다시 실행한다. 훅이 늘었을 수 있다.
마지막 줄이 `준비 완료` 면 끝이다. `실패` 가 있으면 아래 문제 해결을 본다. 점검만: `overseer-setup --check`

사용자에게 알린다.
- 전역 설정에 훅을 등록했다. 훅은 Overseer 가 띄운 세션에서만 동작하고 다른 Claude Code 세션에서는 바로 끝난다(수십 ms)
- 원래 설정은 `~/.claude/settings.json.bak-overseer` 에 남겼다
- 훅은 설치한 환경의 python 과 훅 스크립트를 절대 경로로 가리킨다. 저장소 폴더를 옮기거나 다른 방식으로 다시 설치하면 `overseer-setup` 을 다시 실행한다

## 2. 실행

```bash
overseer          # 저장소에서는 uv run overseer
```

서버다. 끝나지 않으니 별도 터미널이나 백그라운드로 띄우고 브라우저에서 http://127.0.0.1:47310/ 을 연다.

| 옵션 | 뜻 |
|---|---|
| `--port N` | 포트 (기본 47310) |
| `--projects DIR` | 새 세션 창에 보일 프로젝트 루트. 여러 번 줄 수 있다. 환경변수 `OVERSEER_PROJECTS`(`;` 구분)로도 된다. 없으면 드라이브마다 루트의 `Projects` 폴더(`C:\Projects` 등) |
| `--claude-args "..."` | 모든 탭의 claude 에 붙일 인자 |
| `--data DIR` | 이 컴퓨터의 패널 기록 폴더. 기본은 환경변수 `OVERSEER_DATA`, 없으면 `~/.overseer` |

- Overseer 가 띄우는 claude 세션은 서버를 띄운 셸의 환경(PATH, conda 등)을 물려받는다. 사용자가 평소 claude 를 쓰는 셸에서 띄운다
- 서버를 끄면 그 서버가 띄운 claude 세션도 끝난다. 다시 켜면 탭이 "세션 꺼짐" 으로 돌아오고 `이어서 띄우기` 로 `--resume` 한다
- 다시 띄우기: `pwsh scripts/restart_server.ps1`. 모든 탭이 15초 동안 이어서 쉴 때까지 기다렸다가(`-Quiet <초>`) 서버를 다시 띄우고 떠 있던 탭을 `이어서 띄우기` 한다. 서버와 무관한 프로세스에서 돌아 패널 탭 안의 에이전트가 불러도 된다. 작업 스케줄러에 `Overseer` 작업이 있으면 그것으로 띄우고, 없으면 `uv run overseer` 를 창 없이 띄운다. 진행은 `~/.overseer/logs/restart.log`, 멈추지 않고 점검만 할 때는 `-DryRun`
- 프로젝트 기록(사안, 결정, 보존 기록, 책임 이력)은 각 프로젝트의 `.overseer/` 에 쌓인다. 폴더 안 `.gitignore` 로 git 에서 스스로 빠진다
- 이 컴퓨터의 패널 상태는 `~/.overseer/` 에 쌓인다(훅 기록 JSONL, `overseer.db`, 로그). 예전 판처럼 저장소의 `data/` 에 있으면 `pwsh scripts/restart_server.ps1 -WhileStopped scripts/move_data_home.py` 로 옮긴다

## 3. 사용 요령 (사용자에게 전할 것)

- `+` 로 폴더를 고른다. 검색, 목록에 없는 이름은 새 폴더 만들기, 드라이브 문자로 시작하는 전체 경로는 그 경로 열기
- `--dangerously-skip-permissions` 는 새 세션 창에서 고른다(기본 켬). 켜도 위험한 명령은 확인을 받는다
- 권한 확인이 필요하면 흐름 위에 띠가 뜨고 탭 점이 깜빡인다. 띠에서 허용·거부(사유를 적으면 에이전트에게 전해진다)하거나 `터미널에서` 로 원래 확인 창을 띄운다
- 그 밖에 터미널에서 응답해야 하는 확인은 `터미널 확인 필요` 띠가 뜬다. 터미널 창에서 응답하면 사라진다
- 시작 확인 창(폴더 신뢰 등)은 터미널 창에서 한다. 새 탭은 터미널 창을 펼친 채 뜨고, 정상으로 시작하면 접힌다. 첫 입력은 패널의 지시 칸에서 해도 된다
- 응답이 사안 카드로 나오면 카드마다 처리(숫자키)와 의견을 고르고 Ctrl+Shift+Enter 로 보낸다. 카드 입력칸에서 Ctrl+Enter 는 다음 카드로
- Overseer 자신을 Overseer 안에서 고칠 때는 서버 코드를 고친 뒤 `scripts/restart_server.ps1` 로 다시 띄운다. 그 세션도 잠깐 끊겼다가 이어서 뜬다

## 4. 문제 해결

| 증상 | 조치 |
|---|---|
| `claude 명령` 실패 | Claude Code 를 설치하고 새 셸에서 다시 `overseer-setup --check` |
| `uv sync` 가 `overseer.exe` 접근 거부 | Overseer 서버가 떠 있다. 서버를 끄고 다시 |
| `포트 47310` 실패 | 다른 프로그램이 쓰는 중. `uv run overseer --port 47320` |
| 터미널 창이 비어 있다 | CDN(cdn.jsdelivr.net) 접속 확인 |
| 권한 확인이 띠로 안 뜨고 터미널에만 뜬다 | 그 세션이 훅 등록 전에 떴거나 예전 서버가 띄운 것이다. `overseer-setup` 을 다시 실행하고 서버를 다시 켠 뒤 `이어서 띄우기` |
| 턴이 끝나도 카드가 안 생긴다 | `overseer-setup --check` 로 훅 확인. 로그 `~/.overseer/logs/capture_hook.log`. 응답이 규약(`### [질문] 제목`) 을 안 지키면 종합 의견 카드만 생긴다 |
| 세션 안에서 python 등이 엉뚱하게 잡힌다 | 서버를 띄운 셸의 환경을 물려받는다. 원하는 환경이 켜진 셸에서 서버를 다시 띄운다 |
| 새 세션 창에 폴더가 없다 | 드라이브 루트에 `Projects` 폴더가 없다. `--projects <폴더>` 로 정하거나, 이름을 입력해 만든다 |

로그: `~/.overseer/logs/overseer.log`(서버), `~/.overseer/logs/capture_hook.log`(훅)

## 5. 제거

```bash
overseer-setup --uninstall
uv tool uninstall project-overseer   # 도구로 설치했을 때
```

전역 설정에서 Overseer 훅만 지운다. 다른 훅과 설정은 그대로 둔다. 패널 기록은 `~/.overseer/`, 프로젝트 기록은 각 프로젝트의 `.overseer/` 에 남는다. 필요 없으면 지운다.

## 6. 개발할 때

- 코드 구조와 규칙은 `CLAUDE.md`, 방향은 `개발계획.md`
- `.claude/settings.json` 의 훅은 Ln 구조 검사 도구(`lntools`, ff-lntools)를 부른다. 없으면 이 저장소를 고칠 때 훅 오류가 보인다. 도구를 설치하거나 그 훅을 지운다
- 테스트: `uv run pytest`
- 화면만 볼 때: `python scripts/serve_mock.py` → http://127.0.0.1:47311/ (목업 데이터)
