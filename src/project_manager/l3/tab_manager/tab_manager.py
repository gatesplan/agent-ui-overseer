import uuid
from pathlib import Path

from loguru import logger

from ...l0.decision_store import DecisionStore
from ...l0.record_store import RecordStore
from ...l2.agent_tab import AgentTab

SKIP_PERMISSIONS = '--dangerously-skip-permissions'


# 열린 탭 목록. 새 탭을 띄우고, 패널을 다시 켜면 닫지 않은 탭을 꺼진 상태로 되살린다
class TabManager:
    # mcp: 결정 아카이브 조회 MCP 서버 실행 명령 {command, args}. 탭마다 claude 에 붙인다
    def __init__(self, store: DecisionStore, captures_dir: Path, claude_args: str = '', records: RecordStore | None = None,
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
    def open(self, cwd: str, rows: int = 40, cols: int = 120, skip_permissions: bool = False) -> AgentTab:
        path = Path(cwd).expanduser()
        if not path.is_dir():
            raise ValueError(f'폴더가 없다: {cwd}')
        tab_id = uuid.uuid4().hex[:8]
        args = ' '.join(a for a in (self.claude_args, SKIP_PERMISSIONS if skip_permissions else '') if a)
        self.store.add_tab(tab_id, str(path), args)
        tab = AgentTab(tab_id, str(path), args, self.store, self.captures_dir, self.records, self.mcp)
        tab.start(rows=rows, cols=cols)
        self.tabs[tab_id] = tab
        return tab

    # 꺼진 탭을 마지막 세션으로 이어서 띄운다. 기록된 세션이 없으면 새로 띄운다
    def resume(self, tab_id: str, rows: int = 40, cols: int = 120) -> AgentTab:
        tab = self.get(tab_id)
        if not tab.alive:
            tab.start(resume=True, rows=rows, cols=cols)
        return tab

    def close(self, tab_id: str) -> None:
        tab = self.tabs.pop(tab_id, None)
        if tab:
            tab.close()
            self.store.close_tab(tab_id)

    def get(self, tab_id: str) -> AgentTab:
        if tab_id not in self.tabs:
            raise KeyError(tab_id)
        return self.tabs[tab_id]

    def poll(self) -> list[AgentTab]:
        return [tab for tab in self.tabs.values() if tab.poll()]

    def shutdown(self) -> None:
        for tab in self.tabs.values():
            tab.close()
