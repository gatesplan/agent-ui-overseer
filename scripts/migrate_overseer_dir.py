# 패널 DB 와 캡처 기록에 있던 프로젝트 기록을 각 프로젝트의 `.overseer/` 로 옮긴다
# - 세션 번호를 탭 단위에서 프로젝트 단위로 다시 매긴다. 같은 프로젝트의 지난 세션들을 시작 시각 순으로 1S 부터
# - 사안 ID 를 새 번호로 바꾼다: 결정(decisions), 보존 기록(records), 초안, 캡처 기록(시작 기록의 번호, 본문의 `#3S-2-1`, 출처)
# - `.overseer/sessions/<번호>.jsonl` 에 세션 시작 줄, 턴(사안), 결정을, `.overseer/records/D-3.md` 에 보존 기록을 쓴다
# - 폴더 안 .gitignore(`*`)로 git 에서 빠진다. 커밋하지 않는다
# 건너뛰는 것: 임시 폴더에서 연 탭, 없는 폴더, 이미 .overseer 가 있는 프로젝트, 이미 옮긴 탭(data/migrated-overseer.json)
# 서버를 멈춘 동안 돌린다. 돌기 전 DB 와 캡처를 data/backups 에 떠 둔다. DB 의 decisions, records 표는 지우지 않는다(더는 읽지 않는다)
# 사용: uv run python scripts/migrate_overseer_dir.py [--dry-run] [--data data]
import argparse
import json
import os
import re
import shutil
import sqlite3
import sys
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'src'))

from project_manager.l0.project_journal import ProjectJournal  # noqa: E402
from project_manager.l0.record_store import RecordStore  # noqa: E402
from project_manager.l0.turn_builder import TurnBuilder  # noqa: E402

# 사안 ID 와 턴 ID: `3S-2-1`, `3S-2`, 종합 의견 키 `sum-3S-2`
ID = re.compile(r'^(sum-)?(\d+)S-(\d+(?:-\d+)?)$')
TEXT_REF = re.compile(r'#(\d+)S-(\d+)\b')
STAGE = '.overseer-migrating'
MARKER = 'migrated-overseer.json'


def read_events(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


# 탭 하나의 예전 세션 구간. 예전 TurnBuilder 처럼 1 에서 시작해 /clear 시작 기록마다 하나씩 올린다
def old_sessions(events: list[dict], created_at: str) -> tuple[list[dict], list[int]]:
    sessions: list[dict] = []
    per_event: list[int] = []
    k = 1
    cur = None
    for e in events:
        if e.get('event') == 'session_start' and e.get('source') == 'clear':
            k += 1
        if cur is None or cur['old'] != k:
            cur = {'old': k, 'start': None, 'sids': [], 'source': e.get('source') if e.get('event') == 'session_start' else 'migrated'}
            sessions.append(cur)
        sid = e.get('session_id')
        if sid and sid != 'unknown' and sid not in cur['sids']:
            cur['sids'].append(sid)
        if not cur['start'] and e.get('at'):
            cur['start'] = e['at']
        per_event.append(k)
    for s in sessions:
        s['start'] = s['start'] or created_at
    return sessions, per_event


class TabMap:
    def __init__(self, tab_id: str, mapping: dict[int, int]):
        self.tab_id = tab_id
        self.mapping = mapping
        self.missed: list[str] = []

    def id(self, value: str | None) -> str | None:
        if not value:
            return value
        m = ID.match(value)
        if not m:
            self.missed.append(value)
            return value
        new = self.mapping.get(int(m.group(2)))
        if new is None:
            self.missed.append(value)
            return value
        return f"{m.group(1) or ''}{new}S-{m.group(3)}"

    def text(self, text: str | None) -> str | None:
        if not text or '#' not in text:
            return text
        return TEXT_REF.sub(lambda m: f"#{self.mapping[int(m.group(1))]}S-{m.group(2)}" if int(m.group(1)) in self.mapping else m.group(0), text)

    # 캡처 기록 한 줄. 시작 기록에는 새 세션 번호를, 입력, 응답, 사안에는 새 ID 를
    def event(self, e: dict, new_session: int) -> dict:
        e = dict(e)
        if e.get('event') == 'session_start':
            e['session'] = new_session
        for key in ('prompt', 'text', 'preamble'):
            if isinstance(e.get(key), str):
                e[key] = self.text(e[key])
        if isinstance(e.get('prompts'), list):
            e['prompts'] = [self.text(p) if isinstance(p, str) else p for p in e['prompts']]
        if isinstance(e.get('items'), list):
            items = []
            for i in e['items']:
                i = dict(i)
                i['title'], i['body'] = self.text(i.get('title')), self.text(i.get('body'))
                if i.get('parent') and ID.match(i['parent']):
                    i['parent'] = self.id(i['parent'])
                items.append(i)
            e['items'] = items
        return e


def project_exists(key: str) -> bool:
    return os.path.isdir(key)


def temp_folder(cwd: str) -> bool:
    return f'{os.sep}appdata{os.sep}local{os.sep}temp{os.sep}' in os.path.normcase(cwd)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true', help='프로젝트, DB, 캡처를 건드리지 않고 임시 폴더에 써 보고 대조만 한다')
    parser.add_argument('--data', type=Path, default=ROOT / 'data')
    args = parser.parse_args()
    data, dry = args.data, args.dry_run
    captures = data / 'captures'
    db = sqlite3.connect(data / 'overseer.db', timeout=10)
    db.row_factory = sqlite3.Row
    tables = {r[0] for r in db.execute("select name from sqlite_master where type='table'")}
    marker_path = data / MARKER
    done_tabs = set(json.loads(marker_path.read_text(encoding='utf-8'))) if marker_path.exists() else set()

    stamp = f'{datetime.now():%Y%m%d-%H%M%S}'
    if not dry:
        backups = data / 'backups'
        backups.mkdir(exist_ok=True)
        with sqlite3.connect(backups / f'overseer-{stamp}.db') as out:
            db.backup(out)
        shutil.copytree(captures, backups / f'captures-{stamp}')
        print(f'백업: {backups / f"overseer-{stamp}.db"}, {backups / f"captures-{stamp}"}')

    sandbox = Path(tempfile.mkdtemp(prefix='overseer-migrate-')) if dry else None

    # 탭을 프로젝트별로
    skipped: list[str] = []
    projects: dict[str, list[dict]] = {}
    for tab in db.execute('select * from tabs order by created_at').fetchall():
        tab = dict(tab)
        if tab['id'] in done_tabs:
            continue
        if temp_folder(tab['cwd']):
            skipped.append(f"탭 {tab['id']}: 임시 폴더 {tab['cwd']}")
            continue
        key = RecordStore.project_key(tab['cwd'])
        if not project_exists(key):
            skipped.append(f"탭 {tab['id']}: 없는 폴더 {tab['cwd']}")
            continue
        projects.setdefault(key, []).append(tab)
    record_projects = {r['project'] for r in db.execute('select distinct project from records')} if 'records' in tables else set()
    for key in sorted(record_projects - set(projects)):
        if project_exists(key):
            projects.setdefault(key, [])
        else:
            skipped.append(f'기록: 없는 폴더 {key}')

    report = []
    new_captures: dict[str, list[dict]] = {}
    new_drafts: dict[str, dict] = {}
    for key in sorted(projects):
        tabs = projects[key]
        target = Path(key) / '.overseer'
        if target.exists():
            skipped.append(f'프로젝트 {key}: 이미 .overseer 가 있다')
            continue

        # 세션을 시작 시각 순으로 다시 매긴다
        per_tab = {}
        all_sessions = []
        for tab in tabs:
            events = read_events(captures / f"{tab['id']}.jsonl")
            if any(e.get('event') == 'session_start' and isinstance(e.get('session'), int) for e in events):
                skipped.append(f"탭 {tab['id']}: 캡처에 이미 새 세션 번호가 있다")
                continue
            sessions, per_event = old_sessions(events, tab['created_at'])
            per_tab[tab['id']] = (tab, events, sessions, per_event)
            all_sessions += [(s['start'], tab['id'], s) for s in sessions]
        all_sessions.sort(key=lambda x: (x[0] or '', x[1], x[2]['old']))
        maps: dict[str, TabMap] = {tid: TabMap(tid, {}) for tid in per_tab}
        for n, (_, tid, s) in enumerate(all_sessions, 1):
            s['new'] = n
            maps[tid].mapping[s['old']] = n

        stage_root = (sandbox / re.sub(r'[^\w.-]+', '_', key)) if dry else Path(key) / STAGE
        if stage_root.exists():
            shutil.rmtree(stage_root)
        journal = ProjectJournal(stage_root)
        journal.ensure()
        # 세션 시작 줄. 그 세션의 claude 세션 ID 들(resume 으로 바뀐 것까지)을 잇는다
        for _, tid, s in all_sessions:
            sids = s['sids'] or [None]
            head = {'type': 'session', 'session': s['new'], 'session_id': sids[0], 'tab': tid, 'source': s['source'], 'at': s['start']}
            lines = [head] + [{'type': 'attach', 'session_id': sid, 'source': 'migrated', 'at': s['start']} for sid in sids[1:]]
            (journal.dir / f"{s['new']}.jsonl").write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in lines), encoding='utf-8')

        turns = items = 0
        item_ids: set[str] = set()
        for tid, (tab, events, sessions, per_event) in per_tab.items():
            m = maps[tid]
            rewritten = [m.event(e, m.mapping[k]) for e, k in zip(events, per_event)]
            # 첫 기록이 시작 기록이 아니면 번호를 지닌 시작 기록을 앞에 둔다
            if rewritten and rewritten[0].get('event') != 'session_start':
                first = rewritten[0]
                rewritten.insert(0, {'at': first.get('at') or tab['created_at'], 'session_id': first.get('session_id'), 'event': 'session_start',
                                     'source': 'migrated', 'session': m.mapping[per_event[0]]})
            new_captures[tid] = rewritten
            for t in TurnBuilder().build(rewritten)['turns']:
                journal.write_turn(t)
                turns += 1
                items += len(t['items'])
                item_ids.update(i['id'] for i in t['items'])

        # 결정. 사안이 난 세션의 파일에, 원래 시각과 메시지 ID 그대로
        decisions = written = 0
        unknown: list[str] = []
        if 'decisions' in tables:
            for tid in per_tab:
                m = maps[tid]
                for r in db.execute('select * from decisions where tab_id = ? order by id', (tid,)).fetchall():
                    decisions += 1
                    item = m.id(r['item_id'])
                    n = ProjectJournal.session_number(item)
                    if n is None or n not in m.mapping.values():
                        unknown.append(f"{tid}:{r['item_id']}")
                        continue
                    if not item.startswith('sum-') and item not in item_ids:
                        unknown.append(f"{tid}:{r['item_id']}(사안 없음)")
                    row = {'type': 'decision', 'item': item, 'action': r['action'], 'note': r['note'],
                           'message': r['message_id'] or None, 'at': r['created_at']}
                    with (journal.dir / f'{n}.jsonl').open('a', encoding='utf-8') as f:
                        f.write(json.dumps(row, ensure_ascii=False) + '\n')
                    written += 1

        # 보존 기록. 번호와 대체 관계를 그대로 두고 근거 사안 ID 를 새 번호로
        records = 0
        if 'records' in tables:
            rows = [dict(r) for r in db.execute('select * from records where project = ? order by id', (key,)).fetchall()]
            ref_of = {r['id']: f"{r['kind']}-{r['num']}" for r in rows}
            store = RecordStore()
            for r in rows:
                m = maps.get(r['tab_id']) if r['tab_id'] else None
                rec = {'project': RecordStore.project_key(str(stage_root)), 'kind': r['kind'], 'num': r['num'], 'ref': ref_of[r['id']],
                       'text': r['text'], 'body': m.text(r['body']) if m else r['body'], 'note': r['note'], 'tab_id': r['tab_id'],
                       'item_id': m.id(r['item_id']) if m else r['item_id'], 'status': r['status'],
                       'replaces': ref_of.get(r['replaces']), 'replaced_by': ref_of.get(r['replaced_by']), 'created_at': r['created_at']}
                if r['tab_id'] and not m:
                    unknown.append(f"기록 {rec['ref']}: 탭 {r['tab_id']} 을 옮기지 않아 사안 ID 를 그대로 둔다")
                store._write(rec)
                records += 1

        # 초안: 처리와 종합 의견의 키
        for tid in per_tab:
            row = db.execute('select data from drafts where tab_id = ?', (tid,)).fetchone()
            if not row:
                continue
            draft = json.loads(row['data'])
            m = maps[tid]
            new_drafts[tid] = {**draft,
                               'decisions': {m.id(k): v for k, v in (draft.get('decisions') or {}).items()},
                               'summary': {m.id(k): v for k, v in (draft.get('summary') or {}).items()}}

        # 대조: 다시 읽은 것이 쓴 것과 같은지
        check = ProjectJournal(stage_root)
        read_items = len(check.items())
        read_decisions = len(check.decisions())
        read_records = len(store.records(RecordStore.project_key(str(stage_root)))) if 'records' in tables else 0
        ok = read_items == len(item_ids) and read_decisions == written and read_records == records and len(check.sessions()) == len(all_sessions)
        missed = sorted({x for m in maps.values() for x in m.missed})
        report.append((key, len(per_tab), len(all_sessions), turns, items, decisions, written, records, ok, unknown, missed))

        # 프로젝트 하나를 끝까지 마치고 다음으로: 폴더, 캡처, 초안, 옮긴 탭 표시
        # 중간에 멈춰도 폴더만 옮기고 캡처는 예전 번호인 프로젝트가 생기지 않게 한다. 대조가 다르면 옮기지 않는다
        if not dry and not ok:
            skipped.append(f'프로젝트 {key}: 대조가 달라 옮기지 않았다. 써 본 것은 {stage_root}')
            continue
        if not dry:
            (stage_root / '.overseer').rename(target)
            shutil.rmtree(stage_root)
        # 점검이면 고친 캡처 기록을 써 본 곳에 둔다(캡처는 그대로)
        out_captures = captures if not dry else sandbox / 'captures'
        out_captures.mkdir(exist_ok=True)
        for tid in per_tab:
            rows = new_captures.get(tid) or []
            path = out_captures / f'{tid}.jsonl'
            if path.exists() or rows:
                path.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows), encoding='utf-8')
        if not dry:
            with db:
                for tid in per_tab:
                    if tid in new_drafts:
                        db.execute('update drafts set data = ? where tab_id = ?', (json.dumps(new_drafts[tid], ensure_ascii=False), tid))
            done_tabs |= set(per_tab)
            marker_path.write_text(json.dumps(sorted(done_tabs), ensure_ascii=False, indent=1), encoding='utf-8')

    print(f"{'점검' if dry else '완료'}: 프로젝트 {len(report)}")
    print('프로젝트 | 탭 | 세션 | 턴 | 사안 | 결정(DB→씀) | 기록 | 대조')
    for key, ntabs, nsess, nturns, nitems, ndec, nwritten, nrec, ok, unknown, missed in report:
        print(f"{key} | {ntabs} | {nsess} | {nturns} | {nitems} | {ndec}→{nwritten} | {nrec} | {'맞음' if ok else '다름'}")
        for u in unknown[:10]:
            print(f'    대응 없음: {u}')
        if len(unknown) > 10:
            print(f'    대응 없음 그 밖에 {len(unknown) - 10}건')
        if missed:
            print(f"    새 번호로 못 바꾼 ID: {', '.join(missed[:10])}{' …' if len(missed) > 10 else ''}")
    for s in skipped:
        print(f'건너뜀: {s}')
    if sandbox:
        print(f'써 본 곳: {sandbox}')
    return 0 if all(r[8] for r in report) else 1


if __name__ == '__main__':
    sys.exit(main())
