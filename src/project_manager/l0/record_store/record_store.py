import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = '''
create table if not exists records (
  id integer primary key autoincrement,
  project text not null,
  kind text not null,
  num integer not null,
  text text not null,
  body text not null default '',
  note text not null default '',
  tab_id text,
  item_id text,
  status text not null default 'active',
  replaces integer,
  replaced_by integer,
  created_at text not null,
  unique (project, kind, num),
  unique (tab_id, item_id)
);
'''
REF = re.compile(r'^\s*([DW])-(\d+)\s*$')


# 프로젝트 결정 아카이브. 사용자가 승인한 보존 사안([D] 결정 기록, [W] 용어)을 프로젝트별로 D-n, W-n 번호를 붙여 둔다
# 기록은 지우지 않는다. 새 기록이 옛 기록을 대체하면 옛 기록은 replaced 로 남긴다
class RecordStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path, timeout=5, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute('pragma journal_mode=wal')
        self.db.executescript(SCHEMA)

    # 프로젝트 구분 키. 같은 폴더면 대소문자, 구분자가 달라도 같은 키
    @staticmethod
    def project_key(path: str) -> str:
        return os.path.normcase(os.path.abspath(path))

    # 기록 하나를 더한다. 같은 사안(tab_id, item_id)으로 이미 있으면 그것을 돌려준다
    # replaces: 대체할 기록 ID('D-3'). 같은 종류의 유효한 기록일 때만 대체한다
    def add(self, project: str, kind: str, text: str, body: str = '', note: str = '',
            tab_id: str | None = None, item_id: str | None = None, replaces: str | None = None) -> dict:
        if kind not in ('D', 'W'):
            raise ValueError(f'기록 종류가 아니다: {kind}')
        if tab_id and item_id:
            row = self.db.execute('select * from records where tab_id = ? and item_id = ?', (tab_id, item_id)).fetchone()
            if row:
                return self._dict(row)
        old = self.find(project, replaces) if replaces else None
        if old and (old['kind'] != kind or old['status'] != 'active'):
            old = None
        with self.db:
            num = self.db.execute('select coalesce(max(num), 0) + 1 from records where project = ? and kind = ?',
                                  (project, kind)).fetchone()[0]
            cur = self.db.execute(
                'insert into records (project, kind, num, text, body, note, tab_id, item_id, replaces, created_at) '
                'values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                (project, kind, num, text, body, note, tab_id, item_id, old['id'] if old else None, self._now()))
            if old:
                self.db.execute("update records set status = 'replaced', replaced_by = ? where id = ?", (cur.lastrowid, old['id']))
        return self._dict(self.db.execute('select * from records where id = ?', (cur.lastrowid,)).fetchone())

    def records(self, project: str, active_only: bool = False) -> list[dict]:
        sql = 'select * from records where project = ?' + (" and status = 'active'" if active_only else '') + ' order by kind, num'
        return [self._dict(r) for r in self.db.execute(sql, (project,)).fetchall()]

    def find(self, project: str, ref: str) -> dict | None:
        match = REF.match(ref or '')
        if not match:
            return None
        row = self.db.execute('select * from records where project = ? and kind = ? and num = ?',
                              (project, match.group(1), int(match.group(2)))).fetchone()
        return self._dict(row) if row else None

    # 세션 시작 때 넣을 목록. 유효한 기록만, 한 줄씩. 기록이 없으면 빈 문자열
    def briefing(self, project: str) -> str:
        rows = self.records(project, active_only=True)
        if not rows:
            return ''
        lines = [
            '## 이 프로젝트의 결정 기록과 용어 (Overseer)',
            '',
            '사용자가 승인한 것이다. 따른다. 어긋나는 결정을 제안하려면 `대체: <ID>` 를 붙인다. 이 목록을 문서에 옮겨 적지 않는다.',
            '',
        ]
        for r in rows:
            note = f" (메모: {r['note']})" if r['note'] else ''
            lines.append(f"- {r['ref']} {r['text']}{note}")
        return '\n'.join(lines) + '\n'

    def _dict(self, row: sqlite3.Row) -> dict:
        d = dict(row)
        d['ref'] = f"{d['kind']}-{d['num']}"
        return d

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()
