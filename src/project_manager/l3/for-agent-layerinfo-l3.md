# l3

<!-- lnt:generated:start -->
## tab_manager
TabManager.__init__(store: DecisionStore, captures_dir: Path, claude_args: str='', records: RecordStore | None=None, mcp: dict | None=None)  # tab_manager.py
TabManager.restore() -> None  # tab_manager.py
TabManager.open(cwd: str, rows: int=40, cols: int=120, skip_permissions: bool=False) -> AgentTab  # tab_manager.py
TabManager.resume(tab_id: str, rows: int=40, cols: int=120) -> AgentTab  # tab_manager.py
TabManager.close(tab_id: str) -> None  # tab_manager.py
TabManager.get(tab_id: str) -> AgentTab  # tab_manager.py
TabManager.poll() -> list[AgentTab]  # tab_manager.py
TabManager.shutdown() -> None  # tab_manager.py
<!-- lnt:generated:end -->

## Notes

