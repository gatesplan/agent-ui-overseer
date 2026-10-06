# l2

<!-- lnt:generated:start -->
## agent_tab
AgentTab.__init__(tab_id: str, cwd: str, claude_args: str, store: DecisionStore, captures_dir: Path, records: RecordStore | None=None, mcp: dict | None=None)  # agent_tab.py
AgentTab.start(resume: bool=False, rows: int=40, cols: int=120) -> None  # agent_tab.py
AgentTab.child_env(environ: dict[str, str], tab_id: str) -> dict[str, str]  # agent_tab.py
AgentTab.alive() -> bool  # agent_tab.py
AgentTab.poll() -> bool  # agent_tab.py
AgentTab.send(message: str, decisions: list[tuple[str, str, str]]) -> None  # agent_tab.py
AgentTab.clear(decisions: list[tuple[str, str, str]]) -> list[str]  # agent_tab.py
AgentTab.takeovers(decisions: list[tuple[str, str, str]]) -> list[tuple[str, str, str]]  # agent_tab.py
AgentTab.held() -> set[str]  # agent_tab.py
AgentTab.close_held(ids: list[str]) -> list[str]  # agent_tab.py
AgentTab.close() -> None  # agent_tab.py
AgentTab.sync_records() -> list[dict]  # agent_tab.py
AgentTab.decide_permission(request_id: str, behavior: str, message: str='') -> None  # agent_tab.py
AgentTab.acknowledge() -> bool  # agent_tab.py
AgentTab.state() -> dict  # agent_tab.py

## capture_hook
CaptureHook.__init__(store_dir: str | Path, protocol_path: str | Path | None=None, gate: PermissionGate | None=None, records: RecordStore | None=None)  # capture_hook.py
CaptureHook.run(hook_input: dict, tab_id: str) -> str  # capture_hook.py

## overseer_mcp
OverseerMcp.__init__(query: ArchiveQuery)  # overseer_mcp.py
OverseerMcp.records(query: str='', kind: str='', include_replaced: bool=False) -> str  # overseer_mcp.py
OverseerMcp.record(ref: str) -> str  # overseer_mcp.py
OverseerMcp.decisions(query: str='', action: str='', limit: int=20) -> str  # overseer_mcp.py
OverseerMcp.run() -> None  # overseer_mcp.py
<!-- lnt:generated:end -->

## Notes

