---
sources:
  agent_tab.py: 7732c48fe8fb
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
__init__(tab_id: str, cwd: str, claude_args: str, store: DecisionStore, captures_dir: Path, records: RecordStore | None = None, mcp: dict | None = None)
    mcp: 결정 아카이브 조회 MCP 서버 실행 명령 {command, args}. 있으면 start 가 탭별 설정 파일(data/mcp/<탭>.json)을 쓰고
    `--mcp-config <파일> --allowedTools mcp__overseer` 를 붙인다(읽기 전용이라 권한 확인 없이).
    훅 기록을 한 번 읽고 sync_records 를 한 번 한다. 프로세스는 start 로 띄운다.

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
    결정(과 takeovers)을 저장하고 메시지를 붙여넣은 뒤 SUBMIT_DELAY 뒤에 Enter 를 친다.

close() -> None
    결정을 기다리던 권한 훅이 있으면 terminal 로 풀어 준다.

sync_records() -> list[dict]
    보낸 결정 중 승인(approve) 또는 답변(answer)한 보존 사안([D], [W])을 결정 아카이브로 옮긴다. 결정 의견은 note 로.
    본문의 `대체: D-3` 이 있으면 대체한다. 이미 옮긴 사안은 그대로(같은 기록). send 뒤와 생성 때 부른다.

held() -> set[str]
    지금 보류 중인 사안 ID(마지막 결정이 hold).

close_held(ids: list[str]) -> list[str]
    보류함의 닫기. 보류 중인 것만 close 로 끝낸다(add_local, 에이전트에게 보내지 않음). 닫은 ID 반환.

takeovers(decisions: list[tuple[str, str, str]]) -> list[tuple[str, str, str]]
    처리하는 사안의 출처가 보류 사안이면 그 보류 사안을 close 하는 결정(의견 `#새ID 로 이어짐`). send 가 결정에 붙여 저장한다.
    보류 사안 자체를 같은 메시지에서 처리하면 붙이지 않는다.

decide_permission(request_id: str, behavior: str, message: str = '') -> None
    raise ValueError
    화면의 권한 결정을 결정 파일로 쓴다(PermissionGate.decide).

acknowledge() -> bool
    터미널 창 입력이 들어오면 서버가 부른다. 떠 있던 확인 알림을 사용자가 본 것으로 치고 내린다. 내렸으면 True.

state() -> dict
    화면용 상태. {id, project, cwd, agent, args, status, alive, running, permission, attention, records, turns, session_id, sent, summarySent, draft}
    status: exited(꺼짐) | attention(권한 결정이나 터미널 확인을 기다림) | working(입력 처리 중) | waiting(사안 처리 대기) | idle(아직 턴 없음)
    running: 처리 중인 입력문. 보낸 직후 훅 기록이 오기 전에는 마지막으로 보낸 메시지.
