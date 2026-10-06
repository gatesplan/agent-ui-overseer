---
sources:
  agent_tab.py: c4562ce0364b
---
# agent_tab

패널 탭 하나. claude 프로세스(PtySession), 훅 기록(CaptureLog), 결정 저장(DecisionStore)을 묶고 화면에 줄 상태를 만든다.

## AgentTab

### Properties
id: str                      # 탭 ID. 자식 프로세스 환경변수 OVERSEER_TAB 으로 넘겨 훅 기록과 잇는다
cwd: str
claude_args: str             # claude 실행 인자. 탭을 만들 때 정해져 DB 에 남는다
pty: PtySession | None       # 띄우기 전이나 복원 직후는 None
listeners: list              # 터미널 창 출력 콜백. PTY 를 다시 띄워도 이 목록을 그대로 넘긴다
alive: bool

### __init__
__init__(tab_id: str, cwd: str, claude_args: str, store: DecisionStore, captures_dir: Path)
    훅 기록을 한 번 읽어 둔다. 프로세스는 start 로 띄운다.

### Methods

start(resume: bool = False, rows: int = 40, cols: int = 120) -> None
    `cmd.exe /c claude <claude_args>` 를 띄운다. resume 이면 기록된 마지막 세션으로 `--resume <session_id>`.
    환경은 child_env 로 만든다.

child_env(environ: dict[str, str], tab_id: str) -> dict[str, str]    # staticmethod
    자식 claude 에 줄 환경. environ 은 고치지 않는다.
    - 부모 Claude Code 세션의 표식(SESSION_MARKERS)을 지운다. 남으면 자식이 하위 세션으로 떠서 대화 기록 저장이 꺼진다
    - 서버를 uv run 으로 띄우며 붙은 가상환경(UV_RUN_VARS, PATH 의 VIRTUAL_ENV\Scripts)을 지운다. 남으면 자식 세션의 python 이 패널 .venv 로 잡힌다
    - OVERSEER_TAB 을 넣는다

poll() -> bool
    새 훅 기록이 붙었거나 프로세스가 끝났으면 True.

async send(message: str, decisions: list[tuple[str, str, str]]) -> None
    raise RuntimeError    # 프로세스가 꺼져 있을 때
    결정을 저장하고 메시지를 붙여넣은 뒤 SUBMIT_DELAY 뒤에 Enter 를 친다.

close() -> None

state() -> dict
    화면용 상태. {id, project, cwd, agent, args, status, alive, running, turns, session_id, sent, summarySent, draft}
    status: exited(꺼짐) | working(입력 처리 중) | waiting(사안 처리 대기) | idle(아직 턴 없음)
    running: 처리 중인 입력문. 보낸 직후 훅 기록이 오기 전에는 마지막으로 보낸 메시지.
