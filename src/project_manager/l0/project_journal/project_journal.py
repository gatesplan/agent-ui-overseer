import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

# 프로젝트 안 패널 폴더. git 에서 스스로 빠진다(폴더 안 .gitignore 의 `*`)
FOLDER = '.overseer'
GITIGNORE = '*\n'
# 사안 ID 와 종합 의견 키(`sum-<턴 ID>`)에서 세션 번호를 읽는다
SESSION_OF = re.compile(r'^(?:sum-)?(\d+)S-')
# 턴 기록에 남기는 턴 항목. 토큰 사용량, claude 세션 ID 같은 실행 정보는 패널 캡처에만 둔다
TURN_KEYS = ('id', 'session', 'turn', 'at', 'after', 'prompt', 'preamble', 'items', 'files')


# 한 프로젝트의 세션 이력. 세션마다 `.overseer/sessions/<번호>.jsonl` 한 파일에 턴(사안), 사용자 결정, 책임 변경을 쌓는다
# 세션 번호는 프로젝트 안에서 하나씩 오른다. 새 탭과 /clear 가 새 세션이고, resume 과 compact 는 같은 세션을 이어 간다
# 줄은 덧붙이기만 한다. 같은 턴이 다시 쓰이면(이어 붙은 응답) 마지막 줄이 그 턴이다
class ProjectJournal:
    def __init__(self, project: str | Path):
        self.project = Path(project)
        self.root = self.project / FOLDER
        self.dir = self.root / 'sessions'
        # 세션별로 이미 쓴 턴의 내용 해시. 같은 내용을 다시 쓰지 않는다
        self._written: dict[int, dict[str, str]] = {}

    # 폴더를 만들고 git 에서 빠지게 한다
    def ensure(self) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        ignore = self.root / '.gitignore'
        if not ignore.exists():
            ignore.write_text(GITIGNORE, encoding='utf-8')

    # 있는 세션 번호. 작은 것부터
    def sessions(self) -> list[int]:
        if not self.dir.is_dir():
            return []
        return sorted(int(p.stem) for p in self.dir.glob('*.jsonl') if p.stem.isdigit())

    # 새 세션 번호를 받는다. 파일을 배타적으로 만들어 두 쪽이 같은 번호를 받지 않게 한다
    def open_session(self, session_id: str | None, tab_id: str | None, source: str | None = None) -> int:
        self.ensure()
        n = max(self.sessions(), default=0) + 1
        while True:
            try:
                with (self.dir / f'{n}.jsonl').open('x', encoding='utf-8') as f:
                    f.write(self._line({'type': 'session', 'session': n, 'session_id': session_id, 'tab': tab_id,
                                        'source': source, 'at': self._now()}))
                return n
            except FileExistsError:
                n += 1

    # claude 세션 ID 로 세션 번호를 찾는다. 시작 줄과 이어 붙인 줄(attach)을 본다
    def session_of(self, session_id: str | None) -> int | None:
        if not session_id:
            return None
        for n in reversed(self.sessions()):
            for row in self._rows(n):
                if row.get('type') in ('session', 'attach') and row.get('session_id') == session_id:
                    return n
        return None

    # 세션을 연 탭. 시작 줄이 없으면 None
    def owner(self, n: int) -> str | None:
        path = self.dir / f'{n}.jsonl'
        if not path.exists():
            return None
        with path.open(encoding='utf-8') as f:
            try:
                row = json.loads(f.readline() or '{}')
            except json.JSONDecodeError:
                return None
        return row.get('tab') if row.get('type') == 'session' else None

    # 이미 있는 세션에 다른 claude 세션 ID 를 잇는다(resume 이 새 ID 로 뜬 경우)
    def attach(self, n: int, session_id: str, source: str | None = None) -> None:
        self._append(n, {'type': 'attach', 'session_id': session_id, 'source': source, 'at': self._now()})

    # 턴 하나를 쓴다. 지난번에 쓴 내용과 같으면 쓰지 않는다. 썼으면 True
    def write_turn(self, turn: dict) -> bool:
        n = turn['session']
        row = {'type': 'turn', **{k: turn.get(k) for k in TURN_KEYS}}
        digest = hashlib.sha1(json.dumps(row, ensure_ascii=False, sort_keys=True).encode('utf-8')).hexdigest()
        written = self._written_for(n)
        if written.get(turn['id']) == digest:
            return False
        self._append(n, row)
        written[turn['id']] = digest
        return True

    # 사용자 결정. decisions: [(사안 ID, 처리, 사유)]. 사안이 난 세션의 파일에 쓴다. message: 실어 보낸 메시지 ID(패널에서만 내린 결정이면 None)
    def add_decisions(self, decisions: list[tuple[str, str, str]], message: int | None = None) -> None:
        at = self._now()
        for item_id, action, note in decisions:
            n = self.session_number(item_id)
            if n is None:
                continue
            self._append(n, {'type': 'decision', 'item': item_id, 'action': action, 'note': note, 'message': message, 'at': at})

    # 모듈 책임이 바뀐 사건. event: {module, before, after, request, turn}. 그때의 세션 파일에 쓴다
    def add_module_change(self, n: int, event: dict) -> None:
        self._append(n, {'type': 'module', **event, 'at': event.get('at') or self._now()})

    # 결정 이력. sessions 를 주면 그 세션들만. 오래된 것부터
    def decisions(self, sessions: list[int] | set[int] | None = None) -> list[dict]:
        return [r for n in self._pick(sessions) for r in self._rows(n) if r.get('type') == 'decision']

    # 사안마다 마지막 결정 {action, note, at}
    def sent(self, sessions: list[int] | set[int] | None = None) -> dict[str, dict]:
        return {r['item']: {'action': r['action'], 'note': r.get('note') or '', 'at': r.get('at')} for r in self.decisions(sessions)}

    # 사안 하나에 내린 결정 이력
    def history(self, item_id: str) -> list[dict]:
        n = self.session_number(item_id)
        return [r for r in self.decisions([n]) if r['item'] == item_id] if n is not None else []

    # 세션의 턴들. 같은 턴이 여러 번 쓰였으면 마지막 것
    def turns(self, n: int) -> list[dict]:
        out: dict[str, dict] = {}
        for r in self._rows(n):
            if r.get('type') == 'turn' and r.get('id'):
                out[r['id']] = r
        return sorted(out.values(), key=lambda t: t.get('turn') or 0)

    # 프로젝트의 모든 사안 {사안 ID: 사안}. 사안에 at(그 턴의 시각)을 붙인다
    def items(self) -> dict[str, dict]:
        out = {}
        for n in self.sessions():
            for t in self.turns(n):
                for i in t.get('items') or []:
                    out[i['id']] = {**i, 'at': t.get('at')}
        return out

    # 모듈 책임 변경 이력 {모듈: [사건]}. 오래된 것부터
    def module_history(self) -> dict[str, list[dict]]:
        out: dict[str, list[dict]] = {}
        for n in self.sessions():
            for r in self._rows(n):
                if r.get('type') == 'module' and r.get('module'):
                    out.setdefault(r['module'], []).append({**r, 'session': n})
        return out

    @staticmethod
    def session_number(item_id: str) -> int | None:
        m = SESSION_OF.match(item_id or '')
        return int(m.group(1)) if m else None

    def _pick(self, sessions) -> list[int]:
        have = self.sessions()
        return have if sessions is None else [n for n in have if n in set(sessions)]

    def _written_for(self, n: int) -> dict[str, str]:
        if n not in self._written:
            # 서버를 다시 띄운 뒤에도 같은 턴을 또 쓰지 않게 파일에서 읽어 둔다
            self._written[n] = {}
            for r in self._rows(n):
                if r.get('type') == 'turn' and r.get('id'):
                    row = {'type': 'turn', **{k: r.get(k) for k in TURN_KEYS}}
                    self._written[n][r['id']] = hashlib.sha1(json.dumps(row, ensure_ascii=False, sort_keys=True).encode('utf-8')).hexdigest()
        return self._written[n]

    def _rows(self, n: int) -> list[dict]:
        path = self.dir / f'{n}.jsonl'
        if not path.exists():
            return []
        rows = []
        with path.open(encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return rows

    def _append(self, n: int, row: dict) -> None:
        self.ensure()
        with (self.dir / f'{n}.jsonl').open('a', encoding='utf-8') as f:
            f.write(self._line(row))

    def _line(self, row: dict) -> str:
        return json.dumps(row, ensure_ascii=False) + '\n'

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()
