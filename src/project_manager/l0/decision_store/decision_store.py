import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = '''
create table if not exists tabs (
  id text primary key,
  cwd text not null,
  claude_args text not null default '',
  created_at text not null,
  closed_at text
);
create table if not exists messages (
  id integer primary key autoincrement,
  tab_id text not null,
  text text not null,
  created_at text not null
);
create table if not exists decisions (
  id integer primary key autoincrement,
  tab_id text not null,
  item_id text not null,
  action text not null,
  note text not null default '',
  message_id integer not null,
  created_at text not null
);
create index if not exists decisions_tab on decisions (tab_id, item_id);
create table if not exists drafts (
  tab_id text primary key,
  data text not null,
  updated_at text not null
);
'''


# 탭, 보낸 메시지, 사안 결정, 작성 중 초안을 SQLite 에 둔다. 결정은 덮어쓰지 않고 이벤트로 쌓는다
class DecisionStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute('pragma journal_mode=wal')
        self.db.executescript(SCHEMA)

    def add_tab(self, tab_id: str, cwd: str, claude_args: str = '') -> None:
        with self.db:
            self.db.execute('insert into tabs (id, cwd, claude_args, created_at) values (?, ?, ?, ?)',
                            (tab_id, cwd, claude_args, self._now()))

    def close_tab(self, tab_id: str) -> None:
        with self.db:
            self.db.execute('update tabs set closed_at = ? where id = ?', (self._now(), tab_id))

    def open_tabs(self) -> list[dict]:
        rows = self.db.execute('select * from tabs where closed_at is null order by created_at').fetchall()
        return [dict(r) for r in rows]

    # 메시지 한 번과 거기 담긴 결정들을 함께 남긴다. decisions: [(사안 ID, 처리, 사유)]
    def add_message(self, tab_id: str, text: str, decisions: list[tuple[str, str, str]]) -> int:
        now = self._now()
        with self.db:
            cur = self.db.execute('insert into messages (tab_id, text, created_at) values (?, ?, ?)', (tab_id, text, now))
            message_id = cur.lastrowid
            self.db.executemany(
                'insert into decisions (tab_id, item_id, action, note, message_id, created_at) values (?, ?, ?, ?, ?, ?)',
                [(tab_id, item_id, action, note, message_id, now) for item_id, action, note in decisions])
        return message_id

    # 사안마다 마지막으로 보낸 결정
    def sent(self, tab_id: str) -> dict[str, dict]:
        rows = self.db.execute(
            'select item_id, action, note from decisions where tab_id = ? order by id', (tab_id,)).fetchall()
        return {r['item_id']: {'action': r['action'], 'note': r['note']} for r in rows}

    def last_message(self, tab_id: str) -> dict | None:
        row = self.db.execute(
            'select * from messages where tab_id = ? order by id desc limit 1', (tab_id,)).fetchone()
        return dict(row) if row else None

    def save_draft(self, tab_id: str, data: dict) -> None:
        with self.db:
            self.db.execute(
                'insert into drafts (tab_id, data, updated_at) values (?, ?, ?) '
                'on conflict(tab_id) do update set data = excluded.data, updated_at = excluded.updated_at',
                (tab_id, json.dumps(data, ensure_ascii=False), self._now()))

    def draft(self, tab_id: str) -> dict:
        row = self.db.execute('select data from drafts where tab_id = ?', (tab_id,)).fetchone()
        return json.loads(row['data']) if row else {}

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()
