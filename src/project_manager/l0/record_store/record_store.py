import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

# 프로젝트 안 패널 폴더. git 에서 스스로 빠진다. ProjectJournal 과 같은 폴더, 같은 규칙
FOLDER = '.overseer'
GITIGNORE = '*\n'
REF = re.compile(r'^\s*([DW])-(\d+)\s*$')
FILE = re.compile(r'^([DW])-(\d+)\.md$')
# 파일 머리에 쓰는 항목과 순서. 값은 한 줄. 줄바꿈이 있거나 따옴표로 시작하면 JSON 문자열로 쓴다
HEAD = (('text', 'text'), ('status', 'status'), ('replaces', 'replaces'), ('replaced_by', 'replaced_by'),
        ('item', 'item_id'), ('tab', 'tab_id'), ('note', 'note'), ('created', 'created_at'),
        ('retired', 'retired_at'), ('reason', 'retired_reason'))


# 프로젝트 결정 아카이브. 사용자가 승인한 보존 사안([D] 결정 기록, [W] 용어)을 프로젝트별로 D-n, W-n 번호를 붙여 둔다
# 기록 하나가 `<프로젝트>/.overseer/records/D-3.md` 파일 하나다
# 기록은 지우지 않는다. 새 기록이 옛 기록을 대체하면 옛 기록은 replaced, 사용자가 폐기하면 retired 로 남긴다
class RecordStore:
    # 기록 하나를 더한다. 같은 사안(item_id)으로 이미 있으면 그것을 돌려준다
    # replaces: 대체할 기록 ID('D-3'). 같은 종류의 유효한 기록일 때만 대체한다
    def add(self, project: str, kind: str, text: str, body: str = '', note: str = '',
            tab_id: str | None = None, item_id: str | None = None, replaces: str | None = None) -> dict:
        if kind not in ('D', 'W'):
            raise ValueError(f'기록 종류가 아니다: {kind}')
        rows = self.records(project)
        if item_id:
            same = next((r for r in rows if r['item_id'] == item_id), None)
            if same:
                return same
        old = self.find(project, replaces) if replaces else None
        if old and (old['kind'] != kind or old['status'] != 'active'):
            old = None
        num = max((r['num'] for r in rows if r['kind'] == kind), default=0) + 1
        rec = {'project': project, 'kind': kind, 'num': num, 'ref': f'{kind}-{num}', 'text': text, 'body': body, 'note': note,
               'tab_id': tab_id, 'item_id': item_id, 'status': 'active', 'replaces': old['ref'] if old else None,
               'replaced_by': None, 'created_at': self._now()}
        self._write(rec)
        if old:
            self._write({**old, 'status': 'replaced', 'replaced_by': rec['ref']})
        return rec

    # 유효한 기록을 폐기한다. 대체할 결정 없이 더는 맞지 않는 기록을 세션 목록에서 빼려는 것
    # ref 는 이 프로젝트의 기록('D-3')만. 상위 폴더 기록은 그 폴더에서 폐기한다. 폐기했으면 그 기록, 아니면 None
    def retire(self, project: str, ref: str, reason: str = '') -> dict | None:
        rec = self.find(project, ref) if '/' not in (ref or '') else None
        if not rec or rec['status'] != 'active':
            return None
        rec = {**rec, 'status': 'retired', 'retired_at': self._now(), 'retired_reason': reason.strip() or None}
        self._write(rec)
        return rec

    # 이 프로젝트 자체의 기록. 종류, 번호 순
    def records(self, project: str, active_only: bool = False) -> list[dict]:
        folder = self._folder(project)
        if not folder.is_dir():
            return []
        rows = []
        for path in folder.iterdir():
            m = FILE.match(path.name)
            if m:
                rows.append(self._read(project, m.group(1), int(m.group(2)), path))
        rows = [r for r in rows if not active_only or r['status'] == 'active']
        return sorted(rows, key=lambda r: (r['kind'], r['num']))

    # 이 프로젝트에 적용되는 기록: 자기 기록과 상위 폴더의 기록. 상위 폴더 기록은 ref 앞에 폴더 이름을 붙인다(gatesplan/D-1)
    # 묶음 폴더에서 정한 결정이 그 안의 프로젝트에도 적용되게 하려는 것
    def records_in_scope(self, project: str, active_only: bool = False) -> list[dict]:
        return [self._scoped(r, project) for scope in self.scopes(project) for r in self.records(scope, active_only)]

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
        path = self._folder(target) / f'{match.group(1)}-{int(match.group(2))}.md'
        return self._read(target, match.group(1), int(match.group(2)), path) if path.exists() else None

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

    # 기록이 생기거나 폐기된 가장 늦은 시각. 상위 폴더 기록까지. 세션이 목록을 어디까지 받았는지 표시하는 데 쓴다. 없으면 빈 문자열
    def last_mark(self, project: str) -> str:
        return max((t or '' for r in self.records_in_scope(project) for t in (r['created_at'], r['retired_at'])), default='')

    # 세션이 마지막으로 받은 뒤 생긴 기록 변경(상위 폴더 기록 포함)을 알리는 글. 없으면 빈 문자열
    # 추가와 대체는 다른 탭에서 승인한 것만 알린다. 폐기는 패널에서 한 것이라 대화에 없으니 모두 알린다
    # exclude_tab: 그 세션의 탭. 자기 탭에서 승인한 것은 이미 대화에 있다
    def notice(self, project: str, after: str, exclude_tab: str | None = None) -> str:
        events = []
        for r in self.records_in_scope(project):
            if (r['created_at'] or '') > after and r['tab_id'] != exclude_tab:
                old = self.find(r['project'], r['replaces']) if r['replaces'] else None
                line = (f"- 변경: {self._scoped(old, project)['ref']} {old['text']} → {r['ref']} {r['text']}" if old
                        else f"- 추가: {r['ref']} {r['text']}")
                events.append((r['created_at'], line))
            if (r['retired_at'] or '') > after:
                reason = f" (사유: {r['retired_reason']})" if r['retired_reason'] else ''
                events.append((r['retired_at'], f"- 폐기: {r['ref']} {r['text']}{reason}"))
        if not events:
            return ''
        lines = ['## 결정 기록 변경 (Overseer)', '',
                 '다른 세션이나 패널에서 사용자가 바꾼 기록이다. 이후 작업은 이에 맞추고, 폐기된 기록은 더 따르지 않는다.', '']
        lines += [line for _, line in sorted(events)]
        return '\n'.join(lines) + '\n'

    def _line(self, r: dict) -> str:
        note = f" (메모: {r['note']})" if r['note'] else ''
        return f"- {r['ref']} {r['text']}{note}"

    # 보는 프로젝트 기준의 기록. 상위 폴더 기록이면 inherited, ref 에 폴더 이름을 붙인다
    def _scoped(self, rec: dict, project: str) -> dict:
        d = dict(rec)
        d['inherited'] = d['project'] != project
        d['scope'] = os.path.basename(d['project'])
        if d['inherited']:
            d['ref'] = f"{d['scope']}/{d['ref']}"
        return d

    def _folder(self, project: str) -> Path:
        return Path(project) / FOLDER / 'records'

    def _read(self, project: str, kind: str, num: int, path: Path) -> dict:
        text = path.read_text(encoding='utf-8')
        head, body = {}, text
        if text.startswith('---\n'):
            end = text.find('\n---\n', 4)
            if end >= 0:
                for line in text[4:end].splitlines():
                    key, sep, value = line.partition(':')
                    if sep:
                        head[key.strip()] = self._value(value.strip())
                body = text[end + 5:]
        rec = {'project': project, 'kind': kind, 'num': num, 'ref': f'{kind}-{num}', 'body': body.strip('\n')}
        for name, field in HEAD:
            rec[field] = head.get(name) or None
        rec['text'] = rec['text'] or ''
        rec['note'] = rec['note'] or ''
        rec['status'] = rec['status'] or 'active'
        return rec

    def _write(self, rec: dict) -> None:
        folder = self._folder(rec['project'])
        folder.mkdir(parents=True, exist_ok=True)
        ignore = folder.parent / '.gitignore'
        if not ignore.exists():
            ignore.write_text(GITIGNORE, encoding='utf-8')
        head = [f'{name}: {self._dump(rec.get(field))}' for name, field in HEAD if rec.get(field)]
        text = '---\n' + '\n'.join(head) + '\n---\n' + (rec.get('body') or '').strip('\n') + '\n'
        (folder / f"{rec['ref']}.md").write_text(text, encoding='utf-8')

    def _dump(self, value) -> str:
        value = str(value)
        return json.dumps(value, ensure_ascii=False) if '\n' in value or value.startswith('"') else value

    def _value(self, raw: str) -> str:
        if raw.startswith('"'):
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return raw
        return raw

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()
