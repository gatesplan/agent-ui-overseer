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

    # 이 프로젝트 자체의 기록
    def records(self, project: str, active_only: bool = False) -> list[dict]:
        sql = 'select * from records where project = ?' + (" and status = 'active'" if active_only else '') + ' order by kind, num'
        return [self._dict(r) for r in self.db.execute(sql, (project,)).fetchall()]

    # 이 프로젝트에 적용되는 기록: 자기 기록과 상위 폴더의 기록. 상위 폴더 기록은 ref 앞에 폴더 이름을 붙인다(gatesplan/D-1)
    # 묶음 폴더에서 정한 결정이 그 안의 프로젝트에도 적용되게 하려는 것
    def records_in_scope(self, project: str, active_only: bool = False) -> list[dict]:
        scopes = self.scopes(project)
        marks = ','.join('?' * len(scopes))
        sql = f'select * from records where project in ({marks})' + (" and status = 'active'" if active_only else '')
        rows = [self._scoped(r, project) for r in self.db.execute(sql, scopes).fetchall()]
        depth = {key: i for i, key in enumerate(scopes)}
        return sorted(rows, key=lambda r: (depth[r['project']], r['kind'], r['num']))

    # 프로젝트 자신과 상위 폴더들의 키. 가까운 것부터
    def scopes(self, project: str) -> list[str]:
        keys = [project]
        parent = os.path.dirname(project)
        while parent and parent != keys[-1]:
            keys.append(parent)
            parent = os.path.dirname(parent)
        return keys

    # ref 로 기록을 찾는다. 'D-3' 은 이 프로젝트, 'gatesplan/D-3' 은 그 이름의 상위 폴더
    def find(self, project: str, ref: str) -> dict | None:
        scope, _, local = (ref or '').strip().rpartition('/')
        match = REF.match(local)
        if not match:
            return None
        target = project
        if scope:
            target = next((s for s in self.scopes(project)[1:] if os.path.basename(s).lower() == scope.lower()), None)
            if not target:
                return None
        row = self.db.execute('select * from records where project = ? and kind = ? and num = ?',
                              (target, match.group(1), int(match.group(2)))).fetchone()
        return self._dict(row) if row else None

    # 세션 시작 때 넣을 목록. 유효한 기록만, 한 줄씩. 상위 폴더 기록은 따로 묶는다. 기록이 없으면 빈 문자열
    def briefing(self, project: str) -> str:
        rows = self.records_in_scope(project, active_only=True)
        if not rows:
            return ''
        lines = [
            '## 이 프로젝트의 결정 기록과 용어 (Overseer)',
            '',
            '사용자가 승인한 결정과 용어다. 작업은 이에 맞춘다. 바꿔야 하면 `대체: <ID>` 를 붙인 [D], [W] 사안으로 제안한다.',
            '',
        ]
        own = [r for r in rows if not r['inherited']]
        inherited = [r for r in rows if r['inherited']]
        lines += [self._line(r) for r in own]
        if inherited:
            if own:
                lines.append('')
            lines.append('상위 폴더에서 정한 기록. 이 프로젝트에도 적용된다. 바꾸려면 그 폴더에서 연 세션에서 제안한다.')
            lines += [self._line(r) for r in inherited]
        return '\n'.join(lines) + '\n'

    # 지금까지 생긴 가장 큰 기록 번호(내부 id). 상위 폴더 기록까지. 세션이 목록을 어디까지 받았는지 표시하는 데 쓴다
    def last_id(self, project: str) -> int:
        scopes = self.scopes(project)
        marks = ','.join('?' * len(scopes))
        return self.db.execute(f'select coalesce(max(id), 0) from records where project in ({marks})', scopes).fetchone()[0]

    # 세션이 마지막으로 받은 뒤 다른 탭에서 생긴 기록(상위 폴더 기록 포함)을 알리는 글. 없으면 빈 문자열
    # exclude_tab: 그 세션의 탭. 자기 탭에서 승인한 것은 이미 대화에 있다
    def notice(self, project: str, after_id: int, exclude_tab: str | None = None) -> str:
        rows = [r for r in self.records_in_scope(project) if r['id'] > after_id and r['tab_id'] != exclude_tab]
        if not rows:
            return ''
        lines = ['## 결정 기록 변경 (Overseer)', '', '다른 세션에서 사용자가 승인한 기록이다. 이후 작업은 이에 맞춘다.', '']
        for r in sorted(rows, key=lambda r: r['id']):
            old = self.db.execute('select * from records where id = ?', (r['replaces'],)).fetchone() if r['replaces'] else None
            if old:
                lines.append(f"- 변경: {self._scoped(old, project)['ref']} {old['text']} → {r['ref']} {r['text']}")
            else:
                lines.append(f"- 추가: {r['ref']} {r['text']}")
        return '\n'.join(lines) + '\n'

    def _line(self, r: dict) -> str:
        note = f" (메모: {r['note']})" if r['note'] else ''
        return f"- {r['ref']} {r['text']}{note}"

    # 보는 프로젝트 기준의 기록. 상위 폴더 기록이면 inherited, ref 에 폴더 이름을 붙인다
    def _scoped(self, row: sqlite3.Row, project: str) -> dict:
        d = self._dict(row)
        d['inherited'] = d['project'] != project
        d['scope'] = os.path.basename(d['project'])
        if d['inherited']:
            d['ref'] = f"{d['scope']}/{d['ref']}"
        return d

    def _dict(self, row: sqlite3.Row) -> dict:
        d = dict(row)
        d['ref'] = f"{d['kind']}-{d['num']}"
        return d

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()
