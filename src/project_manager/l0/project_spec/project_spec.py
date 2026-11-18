import json
import os
import re
from pathlib import Path

# 프로젝트 루트의 스펙 파일. 코드, 테스트와 같은 브랜치를 따라가게 git 으로 추적한다
FILE = 'spec.json'
# 칸마다 받는 키. 화면에 보이지 않는 칸은 숨은 설명이 되므로 받지 않는다
TOP_KEYS = {'title', 'summary', 'terms', 'components'}
TERM_KEYS = {'word', 'meaning'}
COMP_KEYS = {'name', 'mocks', 'does', 'donts', 'open', 'children'}
MOCK_KEYS = {'name', 'href'}
# 이어서 일어나는 일(then)이 있는 하는 것. 없으면 한 줄 글로 쓴다
DO_KEYS = {'text', 'then'}
# 목록 키가 담는 개체의 종류
ROLES = {'components': 'comp', 'children': 'comp', 'does': 'do', 'then': 'do', 'donts': 'dont', 'open': 'open',
         'terms': 'term', 'mocks': 'mock'}
# 고른 개체(종류) 아래에 더할 수 있는 자식(kind) 과 그것을 담는 목록 키
ADDS = {('root', 'component'): 'components', ('root', 'term'): 'terms',
        ('comp', 'component'): 'children', ('comp', 'do'): 'does', ('comp', 'dont'): 'donts', ('comp', 'open'): 'open',
        ('comp', 'mock'): 'mocks', ('do', 'do'): 'then'}
# 자식으로 치는 목록. 자식이 있는 개체는 지우지 않는다
KIDS = {'comp': ('children', 'mocks', 'does', 'donts', 'open'), 'do': ('then',)}


# 프로젝트의 스펙. 스펙 패널이 그리는 모양 그대로다(용어, 구성요소, 목업, 하는 것, 하지 않는 것, 열린 것)
# 하는 것에는 그것이 실행되면 이어서 일어나는 일을 달고, 그 일도 다시 이어 간다
# 목업은 아무 URL 이나 프로젝트 안 파일 경로를 가리킨다. 프로젝트 안 파일은 패널 서버가 읽기 전용으로 내준다
# 사용자가 스펙 패널에서, 에이전트가 overseer MCP 로 고치고 더하고 지운 것도 여기서 파일에 쓴다
class ProjectSpec:
    def __init__(self, project: str | Path):
        self.root = Path(project)
        self.path = self.root / FILE

    # 파일이 바뀌었는지 알아볼 서명. 파일이 없으면 None
    def signature(self) -> tuple[int, int] | None:
        try:
            st = self.path.stat()
        except OSError:
            return None
        return (st.st_mtime_ns, st.st_size)

    # {'status': 'ok', 'spec'} | {'status': 'none'} | {'status': 'error', 'message'}
    def read(self) -> dict:
        try:
            text = self.path.read_text(encoding='utf-8')
        except FileNotFoundError:
            return {'status': 'none'}
        except OSError as e:
            return {'status': 'error', 'message': f'{FILE} 를 읽지 못했다: {e}'}
        try:
            spec = json.loads(text)
            self._check_top(spec)
        except ValueError as e:
            return {'status': 'error', 'message': f'{FILE} 를 읽지 못했다: {e}'}
        return {'status': 'ok', 'spec': spec}

    # 사용자가 스펙 패널에서 고친 글. path 는 스펙 JSON 안의 자리(['components', 0, 'does', 1, 'text'] 처럼 키와 순번)
    # changes: [{'path', 'old', 'new'}]. 화면이 본 글(old)이 그대로인 칸만 고치고, 하나라도 안 되면 하나도 쓰지 않는다
    # {'status': 'ok', 'spec'} | {'status': 'error', 'message'}
    def edit(self, changes: list[dict]) -> dict:
        def apply(spec):
            for ch in changes:
                path, new = list(ch.get('path') or []), str(ch.get('new') or '').strip()
                if not path or not new:
                    raise ValueError('빈 글로는 고치지 않는다')
                parent, key = self.at(spec, path[:-1]), path[-1]
                if self._get(parent, key) != ch.get('old'):
                    raise ValueError(f'{self._where(path)}: 화면이 본 뒤 바뀌었다. 다시 보고 고친다')
                parent[key] = new
            return {}
        return self._write(apply)

    # 고른 개체(path) 아래에 자식을 더한다. kind: component | do | dont | open | term | mock
    # 프로젝트([]) 에는 구성요소와 용어, 구성요소에는 구성요소, 기능, 하지 않는 것, 열린 것, 목업, 기능에는 이어서 일어나는 기능(then)
    # text 는 한 줄 글. 용어는 {word, meaning}, 목업은 {name, href} 다
    # expect 는 화면이 본 그 개체의 글(seen). 바뀌었으면 더하지 않는다
    # at 이 없으면 목록 끝에 붙이고, 있으면 그 순번에 끼운다(지운 개체를 제자리에 되살릴 때)
    # {'status': 'ok', 'spec', 'path': 더한 자식의 자리} | {'status': 'error', 'message'}
    def add(self, path: list, expect: str, kind: str, text: str | dict, at: int | None = None) -> dict:
        def apply(spec):
            where = list(path)
            node = self.at(spec, where)
            role = self.role(where)
            if self.seen(role, node) != expect:
                raise ValueError(f'{self._where(where) or "스펙"}: 화면이 본 뒤 바뀌었다. 다시 보고 더한다')
            key = ADDS.get((role, kind))
            if not key:
                raise ValueError(f'{self._where(where) or "스펙"} 아래에는 {kind} 를 더할 수 없다')
            item = self._item(kind, text)
            size = len(node.get(key, [])) if isinstance(node, dict) else 0
            if at is not None and not (type(at) is int and 0 <= at <= size):
                raise ValueError(f'{self._where(where + [key]) or key}: 끼울 순번 {at} 이 목록 밖이다 (0~{size})')
            if role == 'do' and isinstance(node, str):
                node = {'text': node}
                self.at(spec, where[:-1])[where[-1]] = node
            items = node.setdefault(key, [])
            pos = size if at is None else at
            items.insert(pos, item)
            return {'path': where + [key, pos]}
        return self._write(apply)

    # 자식이 없는 개체(path)를 지운다. 프로젝트는 지우지 않는다. expect 는 화면이 본 그 개체의 글(seen)
    # 목록이 비면 키를 지우고, 이어지는 일이 다 없어진 기능은 다시 한 줄 글이 된다
    # {'status': 'ok', 'spec', 'path': 지운 자리} | {'status': 'error', 'message'}
    def remove(self, path: list, expect: str) -> dict:
        def apply(spec):
            where = list(path)
            role = self.role(where)
            if role in ('root', 'other'):
                raise ValueError(f'{self._where(where) or "스펙"} 는 지울 수 없다')
            node = self.at(spec, where)
            if self.seen(role, node) != expect:
                raise ValueError(f'{self._where(where)}: 화면이 본 뒤 바뀌었다. 다시 보고 지운다')
            if isinstance(node, dict) and any(node.get(k) for k in KIDS.get(role, ())):
                raise ValueError(f'{self._where(where)}: 자식이 있는 개체는 지우지 않는다')
            holder_path, key = where[:-2], where[-2]
            holder = self.at(spec, holder_path)
            holder[key].pop(where[-1])
            if not holder[key]:
                del holder[key]
                if key == 'then' and set(holder) == {'text'}:
                    self.at(spec, holder_path[:-1])[holder_path[-1]] = holder['text']
            return {'path': where}
        return self._write(apply)

    # 개체를 알아보는 글. 프로젝트는 제목, 구성요소와 목업은 이름, 용어는 낱말, 나머지는 그 한 줄
    @staticmethod
    def seen(role: str, node) -> str | None:
        if isinstance(node, str):
            return node if role in ('do', 'dont', 'open') else None
        if not isinstance(node, dict):
            return None
        return {'root': node.get('title', ''), 'comp': node.get('name'), 'mock': node.get('name'),
                'term': node.get('word'), 'do': node.get('text')}.get(role)

    # 더할 자식. 글은 앞뒤 빈칸을 걷고, 빈 글은 받지 않는다
    @staticmethod
    def _item(kind: str, text) -> str | dict:
        fields = {'term': ('word', 'meaning'), 'mock': ('name', 'href')}.get(kind)
        if fields:
            got = {f: str((text or {}).get(f) or '').strip() if isinstance(text, dict) else '' for f in fields}
            if not all(got.values()):
                raise ValueError(f'{kind} 는 {", ".join(fields)} 가 모두 있어야 한다')
            return got
        item = str(text or '').strip() if not isinstance(text, dict) else ''
        if not item:
            raise ValueError('빈 글은 더하지 않는다')
        return {'name': item} if kind == 'component' else item

    # 자리가 가리키는 개체의 종류: root | comp | do | dont | open | term | mock | other
    @staticmethod
    def role(path: list) -> str:
        if not path:
            return 'root'
        if len(path) >= 2 and type(path[-1]) is int:
            return ROLES.get(path[-2], 'other')
        return 'other'

    # 목업 경로가 가리키는 프로젝트 안 파일. 프로젝트 밖, 점으로 시작하는 폴더나 파일, 폴더, 없는 파일이면 None
    def mock_file(self, rel: str) -> Path | None:
        parts = [p for p in re.split(r'[\\/]', rel) if p not in ('', '.')]
        if not parts or rel.startswith(('/', '\\')) or any(p.startswith('.') or ':' in p for p in parts):
            return None
        root = self.root.resolve()
        path = root.joinpath(*parts).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            return None
        return path

    # 지금 파일을 읽어 apply 로 고치고, 검사를 통과하면 통째로 다시 쓴다. apply 가 돌려준 칸을 결과에 더한다
    # 패널이 반쯤 쓴 파일을 읽지 않게 옆 파일에 쓰고 바꿔 끼운다
    def _write(self, apply) -> dict:
        got = self.read()
        if got['status'] != 'ok':
            return {'status': 'error', 'message': got.get('message', f'{FILE} 가 없다')}
        spec = got['spec']
        try:
            extra = apply(spec)
            self._check_top(spec)
        except ValueError as e:
            return {'status': 'error', 'message': str(e)}
        tmp = self.path.with_name(f'.{FILE}.tmp')
        try:
            tmp.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            os.replace(tmp, self.path)
        except OSError as e:
            return {'status': 'error', 'message': f'{FILE} 를 쓰지 못했다: {e}'}
        return {'status': 'ok', 'spec': spec, **extra}

    # 스펙 JSON 안의 자리(path)에 있는 값. 없는 자리면 ValueError
    @classmethod
    def at(cls, spec, path: list):
        node = spec
        for step in path:
            node = cls._get(node, step)
        return node

    @staticmethod
    def _get(node, step):
        if isinstance(node, dict) and isinstance(step, str) and step in node:
            return node[step]
        if isinstance(node, list) and type(step) is int and 0 <= step < len(node):
            return node[step]
        raise ValueError(f'스펙에 없는 자리: {step}')

    # 오류 글에 쓰는 자리: components[0].does[1]
    @staticmethod
    def _where(path: list) -> str:
        out = ''
        for step in path:
            out += f'[{step}]' if type(step) is int else (f'.{step}' if out else str(step))
        return out

    def _check_top(self, spec) -> None:
        self._check_keys(spec, TOP_KEYS, '스펙')
        for key in ('title', 'summary'):
            if key in spec and not isinstance(spec[key], str):
                raise ValueError(f'{key}: 글이어야 한다')
        for i, term in enumerate(self._list(spec, 'terms', '')):
            where = f'terms[{i}]'
            self._check_keys(term, TERM_KEYS, where)
            for key in TERM_KEYS:
                if not isinstance(term.get(key), str):
                    raise ValueError(f'{where}.{key}: 글이어야 한다')
        for i, comp in enumerate(self._list(spec, 'components', '')):
            self._check_comp(comp, f'components[{i}]')

    def _check_comp(self, comp, where: str) -> None:
        self._check_keys(comp, COMP_KEYS, where)
        if not isinstance(comp.get('name'), str):
            raise ValueError(f'{where}.name: 글이어야 한다')
        for i, mock in enumerate(self._list(comp, 'mocks', where)):
            self._check_keys(mock, MOCK_KEYS, f'{where}.mocks[{i}]')
            for key in MOCK_KEYS:
                if not isinstance(mock.get(key), str):
                    raise ValueError(f'{where}.mocks[{i}].{key}: 글이어야 한다')
        for i, line in enumerate(self._list(comp, 'does', where)):
            self._check_do(line, f'{where}.does[{i}]')
        for key in ('donts', 'open'):
            for i, line in enumerate(self._list(comp, key, where)):
                if not isinstance(line, str):
                    raise ValueError(f'{where}.{key}[{i}]: 한 줄 글이어야 한다')
        for i, child in enumerate(self._list(comp, 'children', where)):
            self._check_comp(child, f'{where}.children[{i}]')

    def _check_do(self, line, where: str) -> None:
        if isinstance(line, str):
            return
        if not isinstance(line, dict):
            raise ValueError(f'{where}: 한 줄 글이거나 {{text, then}} 이어야 한다')
        self._check_keys(line, DO_KEYS, where)
        if not isinstance(line.get('text'), str):
            raise ValueError(f'{where}.text: 글이어야 한다')
        for i, nxt in enumerate(self._list(line, 'then', where)):
            self._check_do(nxt, f'{where}.then[{i}]')

    @staticmethod
    def _check_keys(obj, allowed: set[str], where: str) -> None:
        if not isinstance(obj, dict):
            raise ValueError(f'{where}: 객체여야 한다')
        extra = sorted(set(obj) - allowed)
        if extra:
            raise ValueError(f'{where}: 받지 않는 칸 {", ".join(extra)} (받는 칸: {", ".join(sorted(allowed))})')

    @staticmethod
    def _list(obj: dict, key: str, where: str) -> list:
        value = obj.get(key, [])
        if not isinstance(value, list):
            raise ValueError(f'{where + "." if where else ""}{key}: 목록이어야 한다')
        return value
