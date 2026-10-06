import asyncio
import os
import shlex
from pathlib import Path

from loguru import logger

from project_manager.l0.capture_log import CaptureLog
from project_manager.l0.decision_store import DecisionStore
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


# 패널 탭 하나. claude 프로세스, 훅 기록, 결정 저장을 묶고 화면에 줄 상태를 만든다
class AgentTab:
    def __init__(self, tab_id: str, cwd: str, claude_args: str, store: DecisionStore, captures_dir: Path):
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
        self.log.poll()

    def start(self, resume: bool = False, rows: int = 40, cols: int = 120) -> None:
        argv = ['cmd.exe', '/c', 'claude', *shlex.split(self.claude_args)]
        session_id = self.builder.build(self.log.events)['session_id']
        if resume and session_id:
            argv += ['--resume', session_id]
        env = {k: v for k, v in os.environ.items() if k not in SESSION_MARKERS}
        env['OVERSEER_TAB'] = self.id
        self.pty = PtySession(argv, self.cwd, env, rows, cols)
        self.pty.listeners = self.listeners
        self.pty.start()
        self._was_alive = True

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
        logger.info(f"전송: tab={self.id}, decisions={len(decisions)}, len={len(message)}")
        self._sending = True
        self.pty.paste(message)
        await asyncio.sleep(SUBMIT_DELAY)
        self.pty.write('\r')

    def close(self) -> None:
        if self.pty:
            self.pty.terminate()

    def state(self) -> dict:
        built = self.builder.build(self.log.events)
        sent = self.store.sent(self.id)
        running = built['pending']
        if running is None and self._sending:
            running = (self.store.last_message(self.id) or {}).get('text')
        return {
            'id': self.id, 'project': Path(self.cwd).name, 'cwd': self.cwd, 'agent': 'claude', 'args': self.claude_args,
            'status': self._status(built, running), 'alive': self.alive, 'running': running,
            'turns': built['turns'], 'session_id': built['session_id'],
            # 종합 의견 피드백은 `sum-<턴>` 으로 저장한다
            'sent': {k: v for k, v in sent.items() if not k.startswith('sum-')},
            'summarySent': {k[4:]: v['note'] for k, v in sent.items() if k.startswith('sum-')},
            'draft': self.store.draft(self.id),
        }

    def _status(self, built: dict, running: str | None) -> str:
        if not self.alive:
            return 'exited'
        if running is not None:
            return 'working'
        return 'waiting' if built['turns'] else 'idle'
