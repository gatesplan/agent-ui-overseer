import time
import uuid
from pathlib import Path

from loguru import logger

from ...l0.panel_store import PanelStore
from ...l0.project_key import ProjectKey
from ...l0.record_store import RecordStore
from ...l2.agent_tab import AgentTab

SKIP_PERMISSIONS = '--dangerously-skip-permissions'
# 다시 띄울 때 앞 세션이 끝나기를 기다리는 최대 시간(초)
RESTART_WAIT = 5.0


# 열린 탭 목록. 새 탭을 띄우고, 패널을 다시 켜면 닫지 않은 탭을 꺼진 상태로 되살린다
# 한 프로젝트 폴더에는 탭을 하나만 연다. 두 에이전트가 같은 코드와 같은 세션 이력을 함께 고치지 않게 하려는 것
class TabManager:
    # mcp: 결정 아카이브 조회 MCP 서버 실행 명령 {command, args}. 탭마다 claude 에 붙인다
    def __init__(self, store: PanelStore, captures_dir: Path, claude_args: str = '', records: RecordStore | None = None,
                 mcp: dict | None = None):
        self.store = store
        self.records = records
        self.mcp = mcp
        self.captures_dir = captures_dir
        self.claude_args = claude_args
        self.tabs: dict[str, AgentTab] = {}

    def restore(self) -> None:
        for row in self.store.open_tabs():
            self.tabs[row['id']] = AgentTab(row['id'], row['cwd'], row['claude_args'], self.store, self.captures_dir, self.records, self.mcp)
        logger.info(f"탭 복원: {len(self.tabs)}개")

    # skip_permissions: 권한 확인 없이 띄운다(--dangerously-skip-permissions). 탭 인자로 남아 이어서 띄울 때도 쓴다
    # launch: 프로젝트의 실행 환경 한 줄. None 이면 저장된 것을 그대로 쓴다
    # 그 폴더에 이미 열린 탭이 있으면 새로 띄우지 않고 그 탭을 돌려준다
    def open(self, cwd: str, rows: int = 40, cols: int = 120, skip_permissions: bool = False,
             launch: str | None = None) -> AgentTab:
        path = Path(cwd).expanduser()
        if not path.is_dir():
            raise ValueError(f'폴더가 없다: {cwd}')
        opened = self.find(str(path))
        if opened:
            logger.info(f"이미 열린 프로젝트: {path} → 탭 {opened.id}")
            return opened
        tab_id = uuid.uuid4().hex[:8]
        args = ' '.join(a for a in (self.claude_args, SKIP_PERMISSIONS if skip_permissions else '') if a)
        tab = AgentTab(tab_id, str(path), args, self.store, self.captures_dir, self.records, self.mcp)
        if launch is not None:
            tab.set_launch(launch)
        self.store.add_tab(tab_id, str(path), args)
        tab.start(rows=rows, cols=cols)
        self.tabs[tab_id] = tab
        return tab

    # 꺼진 탭을 마지막 세션으로 이어서 띄운다. 기록된 세션이 없으면 새로 띄운다
    def resume(self, tab_id: str, rows: int = 40, cols: int = 120) -> AgentTab:
        tab = self.get(tab_id)
        if not tab.alive:
            tab.start(resume=True, rows=rows, cols=cols)
        return tab

    # 떠 있는 세션을 끝내고 마지막 세션으로 다시 띄운다. 바꾼 실행 환경을 바로 적용할 때 쓴다
    def restart(self, tab_id: str, rows: int = 40, cols: int = 120) -> AgentTab:
        tab = self.get(tab_id)
        tab.close()
        deadline = time.monotonic() + RESTART_WAIT
        while tab.alive and time.monotonic() < deadline:
            time.sleep(0.1)
        if tab.alive:
            raise RuntimeError('세션이 끝나지 않아 다시 띄우지 못했다')
        tab.start(resume=True, rows=rows, cols=cols)
        return tab

    def close(self, tab_id: str) -> None:
        tab = self.tabs.pop(tab_id, None)
        if tab:
            tab.close()
            self.store.close_tab(tab_id)

    # 그 프로젝트 폴더를 연 탭. 없으면 None
    def find(self, cwd: str) -> AgentTab | None:
        key = ProjectKey.of(cwd)
        return next((t for t in self.tabs.values() if t.project == key), None)

    def get(self, tab_id: str) -> AgentTab:
        if tab_id not in self.tabs:
            raise KeyError(tab_id)
        return self.tabs[tab_id]

    def poll(self) -> list[AgentTab]:
        return [tab for tab in self.tabs.values() if tab.poll()]

    def shutdown(self) -> None:
        for tab in self.tabs.values():
            tab.close()
