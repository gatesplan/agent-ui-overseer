# l0

<!-- lnt:generated:start -->
## capture_log
CaptureLog.__init__(path: str | Path)  # capture_log.py
CaptureLog.poll() -> bool  # capture_log.py

## decision_store
DecisionStore.__init__(path: str | Path)  # decision_store.py
DecisionStore.add_tab(tab_id: str, cwd: str, claude_args: str='') -> None  # decision_store.py
DecisionStore.close_tab(tab_id: str) -> None  # decision_store.py
DecisionStore.open_tabs() -> list[dict]  # decision_store.py
DecisionStore.add_message(tab_id: str, text: str, decisions: list[tuple[str, str, str]]) -> int  # decision_store.py
DecisionStore.sent(tab_id: str) -> dict[str, dict]  # decision_store.py
DecisionStore.last_message(tab_id: str) -> dict | None  # decision_store.py
DecisionStore.save_draft(tab_id: str, data: dict) -> None  # decision_store.py
DecisionStore.draft(tab_id: str) -> dict  # decision_store.py

## item
Item.to_dict() -> dict  # item.py

## permission_gate
PermissionGate.__init__(decisions_dir: str | Path, port: int | None, timeout: float=1500, interval: float=0.3)  # permission_gate.py
PermissionGate.new_id() -> str  # permission_gate.py
PermissionGate.ready() -> bool  # permission_gate.py
PermissionGate.wait(request_id: str) -> dict | None  # permission_gate.py
PermissionGate.decide(request_id: str, behavior: str, message: str='') -> None  # permission_gate.py
PermissionGate.hook_output(decision: dict | None) -> str  # permission_gate.py

## project_finder
ProjectFinder.__init__(folder: str='Projects', drives: list[str] | None=None, roots: list[str] | None=None)  # project_finder.py
ProjectFinder.roots() -> list[Path]  # project_finder.py
ProjectFinder.default_root() -> Path  # project_finder.py
ProjectFinder.scan() -> list[dict]  # project_finder.py
ProjectFinder.create(root: str, name: str) -> Path  # project_finder.py

## record_store
RecordStore.__init__(path: str | Path)  # record_store.py
RecordStore.project_key(path: str) -> str  # record_store.py
RecordStore.add(project: str, kind: str, text: str, body: str='', note: str='', tab_id: str | None=None, item_id: str | None=None, replaces: str | None=None) -> dict  # record_store.py
RecordStore.records(project: str, active_only: bool=False) -> list[dict]  # record_store.py
RecordStore.find(project: str, ref: str) -> dict | None  # record_store.py
RecordStore.briefing(project: str) -> str  # record_store.py
RecordStore.last_id(project: str) -> int  # record_store.py
RecordStore.notice(project: str, after_id: int, exclude_tab: str | None=None) -> str  # record_store.py

## transcript_reader
TranscriptReader.__init__(path: str | Path)  # transcript_reader.py
TranscriptReader.last_turn_text() -> str  # transcript_reader.py
TranscriptReader.turn_prompts(since: int | None=None) -> list[str] | None  # transcript_reader.py
TranscriptReader.turn_usage(since: int | None=None) -> dict | None  # transcript_reader.py
TranscriptReader.row_count() -> int  # transcript_reader.py

## turn_builder
TurnBuilder.build(events: list[dict]) -> dict  # turn_builder.py
<!-- lnt:generated:end -->

## Notes

