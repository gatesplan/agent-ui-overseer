import re
from pathlib import Path

from ...l0.capture_log import CaptureLog
from ...l0.decision_store import DecisionStore
from ...l0.record_store import RecordStore
from ...l0.turn_builder import TurnBuilder

LABEL = {'answer': '답변', 'approve': '승인', 'revise': '수정', 'hold': '보류', 'reject': '기각', 'confirm': '확인', 'feedback': '피드백', 'close': '닫음'}
BASIS = re.compile(r'^근거:(.*)$', re.M)
# 결과 본문을 이 길이로 자른다. 에이전트 컨텍스트를 아끼려는 것
BODY_LIMIT = 600


# 한 프로젝트의 결정 아카이브 조회. 결정 기록과 용어, 지난 사안과 사용자 결정을 에이전트가 읽기 좋은 글로 돌려준다
# 쓰지 않는다. MCP 도구(OverseerMcp)가 이것을 감싼다
class ArchiveQuery:
    def __init__(self, store: DecisionStore, records: RecordStore, captures_dir: Path, project_cwd: str):
        self.store = store
        self.records = records
        self.captures_dir = Path(captures_dir)
        self.project = RecordStore.project_key(project_cwd)
        self._cache: dict[str, dict[str, dict]] = {}

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
            lines += [f"- {self._ref(r)} {r['text']}{' ← 지금' if r['id'] == rec['id'] else ''}{' [유효]' if r['status'] == 'active' else ''}"
                      for r in chain]
        item = self._item(rec['tab_id'], rec['item_id']) if rec['tab_id'] else None
        if item:
            lines += ['', f"## 원래 사안 #{rec['item_id']} ({self._date(rec['created_at'])})", self._clip(item['body'])]
            basis = re.findall(r'#(\d+S-\d+-\d+)', (BASIS.search(item['body'] or '') or [None, ''])[1])
            if basis:
                lines += ['', '## 근거 사안과 사용자 결정']
                lines += [self._item_line(rec['tab_id'], b) for b in basis]
        return '\n'.join(lines)

    # 지난 사안과 사용자 결정. query 는 제목, 본문, 결정 의견에서 찾는다. action 으로 처리 종류를 거른다(reject 면 기각된 것만)
    def decisions(self, query: str = '', action: str = '', limit: int = 20) -> str:
        key = query.strip().lower()
        hits = []
        for tab in self._tabs():
            sent = self.store.sent(tab['id'])
            for item_id, item in self._items(tab['id']).items():
                d = sent.get(item_id)
                if not d or (action and d['action'] != action):
                    continue
                text = f"{item['title']} {item.get('body') or ''} {d['note']}".lower()
                if key and key not in text:
                    continue
                when = (self.store.history(tab['id'], item_id) or [{}])[-1].get('created_at', '')
                hits.append((when, tab['id'], item_id, item, d))
        if not hits:
            return '맞는 사안이 없다.'
        hits.sort(key=lambda h: h[0], reverse=True)
        lines = []
        for when, tab_id, item_id, item, d in hits[:max(1, limit)]:
            tag = f"[{item['tag']}]" if item.get('tag') else ''
            note = f": {d['note']}" if d['note'] else ''
            lines.append(f"- {self._date(when)} 탭 {tab_id} #{item_id} [{item['kind']}]{tag} {item['title']} → {LABEL.get(d['action'], d['action'])}{note}")
        if len(hits) > limit:
            lines.append(f'(그 밖에 {len(hits) - limit}건. 검색어를 좁힌다)')
        return '\n'.join(lines)

    # 대체 관계를 따라 가장 오래된 기록부터 지금 유효한 기록까지
    def _chain(self, rec: dict) -> list[dict]:
        by_id = {r['id']: r for r in self.records.records(rec['project'])}
        first = rec
        while first.get('replaces') in by_id:
            first = by_id[first['replaces']]
        chain = [first]
        while chain[-1].get('replaced_by') in by_id and len(chain) < 50:
            chain.append(by_id[chain[-1]['replaced_by']])
        return chain

    def _item_line(self, tab_id: str, item_id: str) -> str:
        item = self._item(tab_id, item_id)
        if not item:
            return f'- #{item_id} 찾을 수 없는 사안'
        d = self.store.sent(tab_id).get(item_id)
        decision = f"{LABEL.get(d['action'], d['action'])}{': ' + d['note'] if d['note'] else ''}" if d else '사용자 결정 없음'
        return f"- #{item_id} [{item['kind']}] {item['title']} → {decision}"

    # 이 프로젝트와 상위 폴더에서 연 탭. 묶음 폴더 세션에서 내린 결정도 찾게 한다
    def _tabs(self) -> list[dict]:
        scopes = set(self.records.scopes(self.project))
        return [t for t in self.store.tabs() if RecordStore.project_key(t['cwd']) in scopes]

    # 보는 프로젝트 기준의 기록 ID. 상위 폴더 기록이면 폴더 이름을 붙인다
    def _ref(self, rec: dict) -> str:
        return rec['ref'] if rec['project'] == self.project else f"{Path(rec['project']).name}/{rec['ref']}"

    def _items(self, tab_id: str) -> dict[str, dict]:
        if tab_id not in self._cache:
            log = CaptureLog(self.captures_dir / f'{tab_id}.jsonl')
            log.poll()
            turns = TurnBuilder().build(log.events)['turns']
            self._cache[tab_id] = {i['id']: i for t in turns for i in t['items']}
        return self._cache[tab_id]

    def _item(self, tab_id: str, item_id: str) -> dict | None:
        return self._items(tab_id).get(item_id)

    def _clip(self, text: str) -> str:
        text = (text or '').strip()
        return text if len(text) <= BODY_LIMIT else text[:BODY_LIMIT] + '…'

    def _date(self, iso: str | None) -> str:
        return (iso or '')[:10]
