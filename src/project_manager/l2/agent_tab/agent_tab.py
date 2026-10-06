import asyncio
import os
import re
import shlex
from pathlib import Path

from loguru import logger

from project_manager.l0.capture_log import CaptureLog
from project_manager.l0.decision_store import DecisionStore
from project_manager.l0.permission_gate import PermissionGate
from project_manager.l0.record_store import RecordStore
from project_manager.l0.turn_builder import TurnBuilder
from project_manager.l1.pty_session import PtySession

# 부모가 Claude Code 세션이면 물려받는 표식들. 남아 있으면 자식 세션이 하위 세션으로 떠서 대화 기록 저장이 꺼진다
SESSION_MARKERS = (
    'CLAUDECODE', 'CLAUDE_CODE_CHILD_SESSION', 'CLAUDE_CODE_SESSION_ID', 'CLAUDE_PID', 'CLAUDE_EFFORT',
    'CLAUDE_CODE_MESSAGING_SOCKET', 'CLAUDE_CODE_MESSAGING_TOKEN', 'CLAUDE_CODE_SESSION_ATTENDED',
    'CLAUDE_CODE_ENTRYPOINT', 'CLAUDE_CODE_EXECPATH', 'AI_AGENT',
)
# 붙여넣은 뒤 Enter 까지 기다리는 시간. 바로 치면 붙여넣기 처리 전에 제출될 수 있다
SUBMIT_DELAY = 0.3
# uv run 이 붙이는 변수. PATH 맨 앞의 가상환경 경로는 child_env 가 따로 뺀다
UV_RUN_VARS = ('VIRTUAL_ENV', 'UV', 'UV_RUN_RECURSION_DEPTH', '_')
# 보존 사안 본문의 대체 대상: `대체: D-3`
REPLACES = re.compile(r'^대체:\s*([DW]-\d+)', re.M)
# 보존 사안을 아카이브에 넣는 처리
KEEP_ACTIONS = ('approve', 'answer')


# 패널 탭 하나. claude 프로세스, 훅 기록, 결정 저장을 묶고 화면에 줄 상태를 만든다
class AgentTab:
    # records: 프로젝트 결정 아카이브. 승인된 보존 사안을 옮긴다. 없으면 옮기지 않는다
    def __init__(self, tab_id: str, cwd: str, claude_args: str, store: DecisionStore, captures_dir: Path,
                 records: RecordStore | None = None):
        self.id = tab_id
        self.cwd = cwd
        self.claude_args = claude_args
        self.store = store
        self.log = CaptureLog(captures_dir / f'{tab_id}.jsonl')
        self.builder = TurnBuilder()
        self.pty: PtySession | None = None
        # 터미널 창이 붙어 듣는 출력. 다시 띄워 PTY 가 바뀌어도 그대로 이어 붙인다
        self.listeners: list = []
        self._sending = False
        self._was_alive = False
        # 사용자가 터미널에서 응답한 시점의 기록 위치. 그보다 앞선 확인 알림은 처리된 것으로 본다
        self._ack_seq = -1
        self.gate = PermissionGate(captures_dir.parent / 'permissions', None)
        self.records = records
        self.project = RecordStore.project_key(cwd)
        self.log.poll()
        self.sync_records()

    def start(self, resume: bool = False, rows: int = 40, cols: int = 120) -> None:
        argv = ['cmd.exe', '/c', 'claude', *shlex.split(self.claude_args)]
        session_id = self.builder.build(self.log.events)['session_id']
        if resume and session_id:
            argv += ['--resume', session_id]
        env = self.child_env(dict(os.environ), self.id)
        self.pty = PtySession(argv, self.cwd, env, rows, cols)
        self.pty.listeners = self.listeners
        self.pty.start()
        self._was_alive = True

    # 자식 claude 에 줄 환경. 서버가 물려받은 것 중 자식 세션을 바꿔 놓는 것을 걷어 낸다
    # - 부모 Claude Code 세션 표식
    # - 서버를 uv run 으로 띄우며 생긴 패널 가상환경. 남으면 자식 세션의 python 이 패널 .venv 로 잡힌다
    @staticmethod
    def child_env(environ: dict[str, str], tab_id: str) -> dict[str, str]:
        env = {k: v for k, v in environ.items() if k.upper() not in SESSION_MARKERS + UV_RUN_VARS}
        venv = environ.get('VIRTUAL_ENV')
        if venv:
            scripts = {os.path.normcase(os.path.join(venv, d)) for d in ('Scripts', 'bin')}
            for key in [k for k in env if k.upper() == 'PATH']:
                env[key] = os.pathsep.join(p for p in env[key].split(os.pathsep) if os.path.normcase(p.rstrip('\\/')) not in scripts)
        env['OVERSEER_TAB'] = tab_id
        return env

    @property
    def alive(self) -> bool:
        return bool(self.pty and self.pty.alive)

    # 새 훅 기록이 붙었거나 프로세스가 끝났으면 True
    def poll(self) -> bool:
        changed = self.log.poll()
        if changed:
            self._sending = False
        if self._was_alive and not self.alive:
            self._was_alive = False
            changed = True
        return changed

    async def send(self, message: str, decisions: list[tuple[str, str, str]]) -> None:
        if not self.alive:
            raise RuntimeError('세션이 떠 있지 않다')
        self.store.add_message(self.id, message, decisions)
        self.sync_records()
        logger.info(f"전송: tab={self.id}, decisions={len(decisions)}, len={len(message)}")
        self._sending = True
        self.pty.paste(message)
        await asyncio.sleep(SUBMIT_DELAY)
        self.pty.write('\r')

    def close(self) -> None:
        # 결정을 기다리던 권한 훅을 풀어 준다. 안 풀면 훅이 시간이 다 될 때까지 남는다
        permission = self.builder.build(self.log.events)['permission']
        if permission:
            self.gate.decide(permission['request_id'], 'terminal')
        if self.pty:
            self.pty.terminate()

    # 보낸 결정 중 승인(또는 답변)한 보존 사안을 아카이브로 옮긴다. 이미 옮긴 것은 그대로 둔다
    def sync_records(self) -> list[dict]:
        if not self.records:
            return []
        sent = self.store.sent(self.id)
        added = []
        for turn in self.builder.build(self.log.events)['turns']:
            for item in turn['items']:
                decision = sent.get(item['id'])
                if item.get('tag') not in ('D', 'W') or not decision or decision['action'] not in KEEP_ACTIONS:
                    continue
                replaces = REPLACES.search(item.get('body') or '')
                added.append(self.records.add(self.project, item['tag'], item['title'], item.get('body') or '', decision['note'],
                                              self.id, item['id'], replaces.group(1) if replaces else None))
        return added

    # 화면의 권한 결정. behavior: allow | deny | terminal
    def decide_permission(self, request_id: str, behavior: str, message: str = '') -> None:
        logger.info(f"권한 결정 전달: tab={self.id}, request={request_id}, behavior={behavior}")
        self.gate.decide(request_id, behavior, message)

    # 터미널 창에 입력이 들어오면 떠 있던 확인 알림은 사용자가 본 것으로 친다. 알림을 내렸으면 True
    def acknowledge(self) -> bool:
        attention = self.builder.build(self.log.events)['attention']
        if not attention or attention['seq'] <= self._ack_seq:
            return False
        self._ack_seq = len(self.log.events) - 1
        return True

    def state(self) -> dict:
        built = self.builder.build(self.log.events)
        sent = self.store.sent(self.id)
        running = built['pending']
        if running is None and self._sending:
            running = (self.store.last_message(self.id) or {}).get('text')
        attention = built['attention'] if built['attention'] and built['attention']['seq'] > self._ack_seq else None
        permission = built['permission'] if self.alive else None
        return {
            'id': self.id, 'project': Path(self.cwd).name, 'cwd': self.cwd, 'agent': 'claude', 'args': self.claude_args,
            'status': self._status(built, running, permission or attention), 'alive': self.alive, 'running': running,
            'permission': permission, 'attention': attention,
            # 이 프로젝트의 결정 기록과 용어. 대체된 것도 넣는다(카드의 대체 대상 표시)
            'records': self.records.records(self.project) if self.records else [],
            'turns': built['turns'], 'session_id': built['session_id'],
            # 종합 의견 피드백은 `sum-<턴>` 으로 저장한다
            'sent': {k: v for k, v in sent.items() if not k.startswith('sum-')},
            'summarySent': {k[4:]: v['note'] for k, v in sent.items() if k.startswith('sum-')},
            'draft': self.store.draft(self.id),
        }

    def _status(self, built: dict, running: str | None, waiting_user: dict | None) -> str:
        if not self.alive:
            return 'exited'
        # 터미널 확인 창이나 권한 결정을 기다리느라 멈춘 상태
        if waiting_user:
            return 'attention'
        if running is not None:
            return 'working'
        return 'waiting' if built['turns'] else 'idle'
