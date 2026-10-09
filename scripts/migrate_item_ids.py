# 저장된 사안 ID 를 예전 형식(`턴-순번`, 턴 번호가 탭 안에서 이어짐)에서 `<세션>S-<턴>-<순번>` 으로 옮긴다
# 탭마다 캡처 기록을 다시 조립해 예전 턴 번호(탭 전체에서 n 번째 턴)와 새 턴 ID 의 대응을 만든다
# 옮기는 것: 결정(decisions.item_id, 종합 의견 `sum-<턴>`), 보존 기록(records.item_id, 본문의 `#턴-순번`), 초안(처리, 종합 의견 키)
# 새 형식 ID 는 건드리지 않으니 여러 번 돌려도 된다. 서버를 멈춘 동안 돌린다(돌기 전 DB 를 data/backups 에 떠 둔다)
# 사용: uv run python scripts/migrate_item_ids.py [--dry-run] [--data data]
import argparse
import json
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'src'))

from project_manager.l0.capture_log import CaptureLog  # noqa: E402
from project_manager.l0.turn_builder import TurnBuilder  # noqa: E402

ITEM = re.compile(r'^(\d+)-(\d+)$')
SUMMARY = re.compile(r'^sum-(\d+)$')
REF = re.compile(r'#(\d+)-(\d+)\b')


# 탭 하나의 예전 턴 번호 → 새 턴 ID
def turn_ids(captures: Path, tab_id: str) -> list[str]:
    log = CaptureLog(captures / f'{tab_id}.jsonl')
    log.poll()
    return [t['id'] for t in TurnBuilder().build(log.events)['turns']]


class Mapper:
    def __init__(self, turns: list[str]):
        self.turns = turns
        self.missed: list[str] = []

    def turn(self, n: str) -> str | None:
        return self.turns[int(n) - 1] if 0 < int(n) <= len(self.turns) else None

    # 사안 ID 나 `sum-<턴>`. 새 형식이거나 모르는 것은 그대로
    def key(self, key: str) -> str:
        if m := ITEM.match(key):
            tid = self.turn(m.group(1))
            if tid:
                return f'{tid}-{m.group(2)}'
            self.missed.append(key)
        elif m := SUMMARY.match(key):
            tid = self.turn(m.group(1))
            if tid:
                return f'sum-{tid}'
            self.missed.append(key)
        return key

    # 초안의 종합 의견은 턴 번호가 키다
    def summary_key(self, key: str) -> str:
        if key.isdigit():
            tid = self.turn(key)
            if tid:
                return tid
            self.missed.append(f'summary {key}')
        return key

    def text(self, text: str) -> str:
        def ref(m: re.Match) -> str:
            tid = self.turn(m.group(1))
            return f'#{tid}-{m.group(2)}' if tid else m.group(0)
        return REF.sub(ref, text or '')


def migrate(db: sqlite3.Connection, captures: Path, dry: bool) -> None:
    tab_ids = sorted({r[0] for q in ('select id from tabs', 'select distinct tab_id from decisions',
                                     'select distinct tab_id from records where tab_id is not null',
                                     'select tab_id from drafts') for r in db.execute(q)})
    total = 0
    for tab_id in tab_ids:
        m = Mapper(turn_ids(captures, tab_id))
        changes = []
        for rid, item_id in db.execute('select id, item_id from decisions where tab_id = ?', (tab_id,)).fetchall():
            new = m.key(item_id)
            if new != item_id:
                changes.append(('update decisions set item_id = ? where id = ?', (new, rid)))
        for rid, item_id, body in db.execute('select id, item_id, body from records where tab_id = ?', (tab_id,)).fetchall():
            new, new_body = m.key(item_id) if item_id else item_id, m.text(body)
            if (new, new_body) != (item_id, body):
                changes.append(('update records set item_id = ?, body = ? where id = ?', (new, new_body, rid)))
        row = db.execute('select data from drafts where tab_id = ?', (tab_id,)).fetchone()
        if row:
            data = json.loads(row[0])
            new = {**data,
                   'decisions': {m.key(k): v for k, v in (data.get('decisions') or {}).items()},
                   'summary': {m.summary_key(k): v for k, v in (data.get('summary') or {}).items()}}
            if new != data:
                changes.append(('update drafts set data = ? where tab_id = ?', (json.dumps(new, ensure_ascii=False), tab_id)))
        missed = sorted(set(m.missed))
        if changes or missed:
            print(f'{tab_id}: 턴 {len(m.turns)}, 바꿀 행 {len(changes)}' + (f', 대응 없음 {missed}' if missed else ''))
        total += len(changes)
        if not dry:
            with db:
                for sql, args in changes:
                    db.execute(sql, args)
    print(f"{'점검' if dry else '완료'}: 탭 {len(tab_ids)}, 바꾼 행 {total}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--data', type=Path, default=ROOT / 'data')
    args = parser.parse_args()
    db = sqlite3.connect(args.data / 'overseer.db', timeout=10)
    if not args.dry_run:
        backups = args.data / 'backups'
        backups.mkdir(exist_ok=True)
        target = backups / f"overseer-{datetime.now():%Y%m%d-%H%M%S}.db"
        with sqlite3.connect(target) as out:
            db.backup(out)
        print(f'백업: {target}')
    migrate(db, args.data / 'captures', args.dry_run)


if __name__ == '__main__':
    main()
