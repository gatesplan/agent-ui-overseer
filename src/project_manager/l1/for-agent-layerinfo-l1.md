# l1

<!-- lnt:generated:start -->
## archive_query
ArchiveQuery.__init__(store: DecisionStore, records: RecordStore, captures_dir: Path, project_cwd: str)  # archive_query.py
ArchiveQuery.list_records(query: str='', kind: str='', include_replaced: bool=False) -> str  # archive_query.py
ArchiveQuery.record(ref: str) -> str  # archive_query.py
ArchiveQuery.decisions(query: str='', action: str='', limit: int=20) -> str  # archive_query.py

## item_splitter
ItemSplitter.split(text: str) -> tuple[str, list[Item]]  # item_splitter.py

## pty_session
PtySession.__init__(argv: list[str], cwd: str, env: dict[str, str], rows: int=40, cols: int=120)  # pty_session.py
PtySession.start() -> None  # pty_session.py
PtySession.alive() -> bool  # pty_session.py
PtySession.history() -> str  # pty_session.py
PtySession.write(data: str) -> None  # pty_session.py
PtySession.paste(text: str) -> None  # pty_session.py
PtySession.resize(rows: int, cols: int) -> None  # pty_session.py
PtySession.terminate() -> None  # pty_session.py
<!-- lnt:generated:end -->

## Notes

