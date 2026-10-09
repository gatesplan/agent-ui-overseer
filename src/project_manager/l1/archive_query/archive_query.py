import os
import re
from pathlib import Path

from ...l0.project_journal import ProjectJournal
from ...l0.record_store import RecordStore

LABEL = {'answer': '답변', 'approve': '승인', 'revise': '수정', 'hold': '보류', 'reject': '기각', 'confirm': '확인', 'feedback': '피드백', 'close': '닫음'}
BASIS = re.compile(r'^근거:(.*)$', re.M)
ITEM_REF = re.compile(r'(?:([\w.-]+)/)?#?(\d+S-\d+-\d+)')
# 결과 본문을 이 길이로 자른다. 에이전트 컨텍스트를 아끼려는 것
BODY_LIMIT = 600


# 한 프로젝트의 결정 아카이브 조회. 결정 기록과 용어, 지난 사안과 사용자 결정, 모듈 책임 이력을 에이전트가 읽기 좋은 글로 돌려준다
# 프로젝트와 상위 폴더의 `.overseer/` 를 읽기만 한다. MCP 도구(OverseerMcp)가 이것을 감싼다
class ArchiveQuery:
    def __init__(self, records: RecordStore, project_cwd: str):
        self.records = records
        self.project = RecordStore.project_key(project_cwd)
        # 프로젝트 자신과 상위 폴더의 세션 이력. 가까운 것부터
        self.journals = [(scope, ProjectJournal(scope)) for scope in records.scopes(self.project)]

    # 결정 기록과 용어 목록. query 는 내용, 메모에서 찾는 글자(대소문자 무시). kind: D | W | 빈 값(둘 다)
    def list_records(self, query: str = '', kind: str = '', include_replaced: bool = False) -> str:
        # 상위 폴더 기록도 함께. ref 에 폴더 이름이 붙어 있다(gatesplan/D-1)
        rows = self.records.records_in_scope(self.project, active_only=not include_replaced)
        key = query.strip().lower()
        rows = [r for r in rows if (not kind or r['kind'] == kind.upper())
                and (not key or key in f"{r['text']} {r['note']} {r['body']}".lower())]
        if not rows:
            return '맞는 기록이 없다.'
        lines = []
        for r in rows:
            status = '' if r['status'] == 'active' else ' [대체됨]'
            note = f" (메모: {r['note']})" if r['note'] else ''
            lines.append(f"- {r['ref']}{status} {r['text']}{note}")
        return '\n'.join(lines)

    # 기록 하나: 대체 이력 전체, 원래 사안 본문, 근거 사안과 그에 대한 사용자 결정
    def record(self, ref: str) -> str:
        rec = self.records.find(self.project, ref)
        if not rec:
            return f'{ref} 기록이 없다.'
        lines = [f"# {self._ref(rec)} ({'유효' if rec['status'] == 'active' else '대체됨'})", rec['text']]
        if rec['project'] != self.project:
            lines.append(f"상위 폴더 {rec['project']} 에서 정한 기록. 이 프로젝트에도 적용된다")
        if rec['note']:
            lines.append(f"승인 메모: {rec['note']}")
        chain = self._chain(rec)
        if len(chain) > 1:
            lines += ['', '## 대체 이력 (오래된 것부터)']
            lines += [f"- {self._ref(r)} {r['text']}{' ← 지금' if r['ref'] == rec['ref'] else ''}{' [유효]' if r['status'] == 'active' else ''}"
                      for r in chain]
        journal = self._journal(rec['project'])
        item = journal.items().get(rec['item_id']) if rec['item_id'] else None
        body = item['body'] if item else rec['body']
        if rec['item_id'] or body:
            lines += ['', f"## 원래 사안 #{rec['item_id'] or '?'} ({self._date(rec['created_at'])})", self._clip(body)]
        basis = ITEM_REF.findall((BASIS.search(body or '') or [None, ''])[1])
        if basis:
            lines += ['', '## 근거 사안과 사용자 결정']
            lines += [self._item_line(scope, item_id, rec['project']) for scope, item_id in basis]
        return '\n'.join(lines)

    # 지난 사안과 사용자 결정. query 는 제목, 본문, 결정 의견에서 찾는다. action 으로 처리 종류를 거른다(reject 면 기각된 것만)
    def decisions(self, query: str = '', action: str = '', limit: int = 20) -> str:
        key = query.strip().lower()
        hits = []
        for scope, journal in self.journals:
            items = journal.items()
            for item_id, d in journal.sent().items():
                item = items.get(item_id)
                if not item or (action and d['action'] != action):
                    continue
                text = f"{item['title']} {item.get('body') or ''} {d['note']}".lower()
                if key and key not in text:
                    continue
                hits.append((d.get('at') or '', self._label(scope, item_id), item, d))
        if not hits:
            return '맞는 사안이 없다.'
        hits.sort(key=lambda h: h[0], reverse=True)
        lines = []
        for when, label, item, d in hits[:max(1, limit)]:
            tag = f"[{item['tag']}]" if item.get('tag') else ''
            note = f": {d['note']}" if d['note'] else ''
            lines.append(f"- {self._date(when)} #{label} [{item['kind']}]{tag} {item['title']} → {LABEL.get(d['action'], d['action'])}{note}")
        if len(hits) > limit:
            lines.append(f'(그 밖에 {len(hits) - limit}건. 검색어를 좁힌다)')
        return '\n'.join(lines)

    # 모듈 하나의 책임 변경 이력과 그 모듈을 언급한 결정 기록. name 은 `l1.item_splitter` 나 끝 이름 `item_splitter`
    def module(self, name: str) -> str:
        name = name.strip()
        history = self.journals[0][1].module_history() if self.journals else {}
        hits = [m for m in history if m == name or m.rsplit('.', 1)[-1] == name]
        lines = []
        for m in hits:
            lines.append(f'# {m} 책임 이력 (오래된 것부터)')
            for e in history[m]:
                who = f"사용자 요청: {e['request']}" if e.get('request') else '에이전트나 직접 편집'
                before = '(새 모듈)' if e.get('before') is None else (e['before'] or '(없음)')
                where = f" {e['turn']} 뒤" if e.get('turn') else ''
                lines.append(f"- {self._date(e.get('at'))}{where}: {before} → {e.get('after') or '(없음)'} [{who}]")
        short = name.rsplit('.', 1)[-1]
        recs = [r for r in self.records.records_in_scope(self.project, active_only=True) if short in f"{r['text']} {r['note']} {r['body']}"]
        if recs:
            lines += ['', f'# {short} 를 언급한 결정 기록']
            lines += [f"- {r['ref']} {r['text']}" for r in recs]
        return '\n'.join(lines) if lines else f'{name} 에 대한 책임 이력과 기록이 없다.'

    # 대체 관계를 따라 가장 오래된 기록부터 지금 유효한 기록까지
    def _chain(self, rec: dict) -> list[dict]:
        by_ref = {r['ref']: r for r in self.records.records(rec['project'])}
        first, seen = rec, {rec['ref']}
        while first.get('replaces') in by_ref and first['replaces'] not in seen:
            first = by_ref[first['replaces']]
            seen.add(first['ref'])
        chain = [first]
        while chain[-1].get('replaced_by') in by_ref and len(chain) < 50:
            chain.append(by_ref[chain[-1]['replaced_by']])
        return chain

    # 근거 사안 한 줄. scope 는 `gatesplan/5S-2-1` 의 폴더 이름. 없으면 그 기록의 프로젝트에서 찾는다
    def _item_line(self, scope: str, item_id: str, project: str) -> str:
        journal = self._journal(next((s for s, _ in self.journals if os.path.basename(s).lower() == scope.lower()), project) if scope else project)
        label = f'{scope}/{item_id}' if scope else item_id
        item = journal.items().get(item_id)
        if not item:
            return f'- #{label} 찾을 수 없는 사안'
        d = journal.sent([ProjectJournal.session_number(item_id)]).get(item_id)
        decision = f"{LABEL.get(d['action'], d['action'])}{': ' + d['note'] if d['note'] else ''}" if d else '사용자 결정 없음'
        return f"- #{label} [{item['kind']}] {item['title']} → {decision}"

    def _journal(self, project: str) -> ProjectJournal:
        return next((j for s, j in self.journals if s == project), None) or ProjectJournal(project)

    # 보는 프로젝트 기준의 사안 ID. 상위 폴더 사안이면 폴더 이름을 붙인다
    def _label(self, scope: str, item_id: str) -> str:
        return item_id if scope == self.project else f'{Path(scope).name}/{item_id}'

    # 보는 프로젝트 기준의 기록 ID. 상위 폴더 기록이면 폴더 이름을 붙인다
    def _ref(self, rec: dict) -> str:
        return rec['ref'] if rec['project'] == self.project else f"{Path(rec['project']).name}/{rec['ref']}"

    def _clip(self, text: str) -> str:
        text = (text or '').strip()
        return text if len(text) <= BODY_LIMIT else text[:BODY_LIMIT] + '…'

    def _date(self, iso: str | None) -> str:
        return (iso or '')[:10]
