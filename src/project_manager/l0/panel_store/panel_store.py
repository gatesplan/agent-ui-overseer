import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

# decisions 표는 사안 결정이 프로젝트 `.overseer/` 로 옮겨 가기 전의 것이다. 이전 스크립트가 읽도록 남겨 둔다
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
create table if not exists drafts (
  tab_id text primary key,
  data text not null,
  updated_at text not null
);
'''


# 이 컴퓨터의 패널 상태. 열린 탭, 보낸 메시지, 작성 중 초안을 SQLite 에 둔다
# 사안과 결정은 프로젝트의 것이라 여기 두지 않는다(ProjectJournal)
class PanelStore:
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

    # 닫은 탭까지 전부
    def tabs(self) -> list[dict]:
        return [dict(r) for r in self.db.execute('select * from tabs order by created_at').fetchall()]

    def open_tabs(self) -> list[dict]:
        rows = self.db.execute('select * from tabs where closed_at is null order by created_at').fetchall()
        return [dict(r) for r in rows]

    # 보낸 메시지를 남기고 메시지 ID 를 돌려준다. 거기 담긴 결정은 프로젝트 기록에 따로 쓴다
    def add_message(self, tab_id: str, text: str) -> int:
        with self.db:
            cur = self.db.execute('insert into messages (tab_id, text, created_at) values (?, ?, ?)', (tab_id, text, self._now()))
        return cur.lastrowid

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
