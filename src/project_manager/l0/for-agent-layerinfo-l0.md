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

## project_finder
ProjectFinder.__init__(folder: str='Projects', drives: list[str] | None=None)  # project_finder.py
ProjectFinder.roots() -> list[Path]  # project_finder.py
ProjectFinder.default_root() -> Path  # project_finder.py
ProjectFinder.scan() -> list[dict]  # project_finder.py
ProjectFinder.create(root: str, name: str) -> Path  # project_finder.py

## transcript_reader
TranscriptReader.__init__(path: str | Path)  # transcript_reader.py
TranscriptReader.last_turn_text() -> str  # transcript_reader.py

## turn_builder
TurnBuilder.build(events: list[dict]) -> dict  # turn_builder.py
<!-- lnt:generated:end -->

## Notes

