import re

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

from ...l0.project_spec import ProjectSpec
from ...l1.archive_query import ArchiveQuery

INSTRUCTIONS = (
    '이 프로젝트에서 사용자가 내린 결정을 읽고, 프로젝트 스펙(spec.json)을 다루는 도구다. 결정 기록은 읽기만 한다. '
    '제안하기 전에 decisions(action="reject")로 비슷한 제안이 기각된 적이 있는지 본다. '
    '결정 기록과 용어의 목록과 검색은 records, 기록 하나의 이력과 근거는 record 로 본다. '
    '모듈의 책임이 언제 누구의 요청으로 바뀌었는지는 module 로 본다. '
    '스펙은 spec.json 을 직접 열지 않고 spec_view 로 보고 spec_add, spec_edit, spec_remove, spec_move 로 고친다. 고친 것은 스펙 패널에 곧바로 보인다.'
)
READ_ONLY = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False)
WRITE = ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=False, open_world_hint=False)
REMOVE = ToolAnnotations(read_only_hint=False, destructive_hint=True, idempotent_hint=False, open_world_hint=False)

# 스펙 개체 번호. 프로젝트 아래 c(구성요소)와 w(용어), 구성요소 아래 c(하위 구성요소), d(설명), f(기능), n(하지 않는 것), m(목업),
# 기능 아래 f(이어서 일어나는 기능). 점으로 잇는다: c1.c2.f1.f3. 순번은 1부터
SEGMENT = re.compile(r'^([cwdfnm])([1-9]\d*)$')
STEP = {('root', 'c'): 'components', ('root', 'w'): 'terms',
        ('comp', 'c'): 'children', ('comp', 'd'): 'descs', ('comp', 'f'): 'does', ('comp', 'n'): 'donts', ('comp', 'm'): 'mocks',
        ('do', 'f'): 'then'}
LETTER = {key: letter for (_, letter), key in STEP.items()}
# 개체 번호 대신 쓰는 프로젝트의 글 칸
TOP_FIELDS = ('title', 'summary')
SPEC_HELP = ('개체 번호: 프로젝트 아래 c 구성요소, w 용어. 구성요소 아래 c 하위 구성요소, d 설명(그 구성요소가 무엇인지), f 기능(하는 것), n 하지 않는 것, m 목업. '
             '기능 아래 f 이어서 일어나는 기능. 점으로 잇고 순번은 1부터다(c1.c2.f1). 용어 글은 `낱말: 뜻`, 목업 글은 `이름 | 경로나 URL`.')


# 결정 아카이브 조회와 프로젝트 스펙 다루기를 MCP 도구로 내놓는 서버. 패널이 띄운 claude 세션에 --mcp-config 로 붙는다
# 결정 아카이브는 읽기만 한다. 스펙은 개체 번호로 필요한 부분만 보고 고쳐, spec.json 을 통째로 읽고 쓰지 않게 한다
class OverseerMcp:
    # spec: 그 탭 프로젝트의 스펙. 없으면 스펙 도구를 내놓지 않는다
    def __init__(self, query: ArchiveQuery, spec: ProjectSpec | None = None):
        self.query = query
        self.spec = spec
        self.server = MCPServer(name='overseer', instructions=INSTRUCTIONS)
        self.server.add_tool(self.records, name='records', annotations=READ_ONLY,
                             description='이 프로젝트의 결정 기록(D)과 용어(W) 목록. query 로 내용과 메모를 찾고, kind 로 D 나 W 만, '
                                         'include_replaced 로 대체되거나 폐기된 옛 기록까지 본다.')
        self.server.add_tool(self.record, name='record', annotations=READ_ONLY,
                             description='기록 하나(예: D-3)를 자세히 본다. 대체 이력 전체, 원래 사안 본문, 근거 사안과 그에 대한 사용자 결정.')
        self.server.add_tool(self.decisions, name='decisions', annotations=READ_ONLY,
                             description='이 프로젝트의 지난 사안과 사용자 결정(답변, 승인, 수정, 보류, 기각, 확인)을 최근 순으로 찾는다. '
                                         'action="reject" 면 기각된 것과 그 사유만. 같은 제안을 다시 내기 전에 확인한다.')
        self.server.add_tool(self.module, name='module', annotations=READ_ONLY,
                             description='모듈 하나(예: l1.item_splitter 나 item_splitter. fmp_harness/l1.cli_io 처럼 패키지를 붙여도 된다)의 책임 변경 이력과 그 모듈을 언급한 결정 기록. '
                                         '변경마다 이전 책임, 새 책임, 사용자가 요청한 것인지를 보인다. 책임을 바꾸기 전에 확인한다.')
        if spec is None:
            return
        self.server.add_tool(self.spec_view, name='spec_view', annotations=READ_ONLY,
                             description='프로젝트 스펙을 개체 번호가 붙은 들여쓰기 글로 본다. at 에 구성요소나 기능 번호를 주면 그 아래만 본다. ' + SPEC_HELP)
        self.server.add_tool(self.spec_add, name='spec_add', annotations=WRITE,
                             description='parent 개체 아래에 자식을 더한다(parent 가 빈 글이면 프로젝트). kind: component | desc | do | dont | term | mock. '
                                         '프로젝트에는 component, term. 구성요소에는 component, desc, do, dont, mock. 기능에는 do(이어서 일어나는 기능). ' + SPEC_HELP)
        self.server.add_tool(self.spec_edit, name='spec_edit', annotations=WRITE,
                             description='개체 하나의 글을 바꾼다. id 는 개체 번호나 title, summary. 구성요소는 이름, 나머지는 그 한 줄을 바꾼다. ' + SPEC_HELP)
        self.server.add_tool(self.spec_remove, name='spec_remove', annotations=REMOVE,
                             description='자식이 없는 개체 하나를 지운다. 지운 자리 뒤 형제의 번호는 하나씩 당겨진다. ' + SPEC_HELP)
        self.server.add_tool(self.spec_move, name='spec_move', annotations=WRITE,
                             description='개체 하나(id)를 자식째 parent 개체 아래로 옮긴다(parent 가 빈 글이면 프로젝트). 새 부모 목록 끝에 붙는다. '
                                         '갈 수 있는 자리는 spec_add 와 같다. 빠진 자리 뒤 형제의 번호는 하나씩 당겨진다. ' + SPEC_HELP)

    def records(self, query: str = '', kind: str = '', include_replaced: bool = False) -> str:
        return self.query.list_records(query, kind, include_replaced)

    def record(self, ref: str) -> str:
        return self.query.record(ref)

    def decisions(self, query: str = '', action: str = '', limit: int = 20) -> str:
        return self.query.decisions(query, action, limit)

    def module(self, name: str) -> str:
        return self.query.module(name)

    # 스펙 도구 ------------------------------------------------------------------

    def spec_view(self, at: str = '') -> str:
        try:
            spec = self._spec()
            if not at.strip():
                lines = [f'title: {spec.get("title", "")}']
                if spec.get('summary'):
                    lines.append(f'summary: {spec["summary"]}')
                lines += [f'{self._id(["terms", i])} {self._line("term", w)}' for i, w in enumerate(spec.get('terms') or [])]
                for i, comp in enumerate(spec.get('components') or []):
                    lines += self._tree(comp, ['components', i], 0)
                return '\n'.join(lines)
            path = self._path(at)
            role = ProjectSpec.role(path)
            if role not in ('comp', 'do'):
                raise ValueError(f'{at}: at 에는 구성요소나 기능 번호를 준다')
            # 그 개체까지 이어진 자리를 머리에 한 줄로 보인다
            crumb = [self._label(spec, path[:k]) for k in range(2, len(path), 2) if ProjectSpec.role(path[:k]) in ('comp', 'do')]
            head = [' > '.join(crumb)] if crumb else []
            return '\n'.join(head + self._tree(ProjectSpec.at(spec, path), path, 0))
        except ValueError as e:
            return f'실패: {e}'

    def spec_add(self, parent: str, kind: str, text: str) -> str:
        try:
            path = self._path(parent) if parent.strip() else []
            role = ProjectSpec.role(path)
            node = ProjectSpec.at(self._spec(), path)
            item = self._fields(kind, text)
            got = self._done(self.spec.add(path, ProjectSpec.seen(role, node), kind, item))
            return f'더함: {self._id(got["path"])} {self._line(ProjectSpec.role(got["path"]), ProjectSpec.at(got["spec"], got["path"]))}'
        except ValueError as e:
            return f'실패: {e}'

    def spec_edit(self, id: str, text: str) -> str:
        try:
            spec = self._spec()
            text = text.strip()
            if id in TOP_FIELDS:
                old = spec.get(id, '')
                self._done(self.spec.edit([{'path': [id], 'old': old, 'new': text}]))
                return f'{id}: "{old}" → "{text}"'
            path = self._path(id)
            role = ProjectSpec.role(path)
            node = ProjectSpec.at(spec, path)
            if role in ('term', 'mock'):
                new = self._fields(role, text)
                changes = [{'path': path + [f], 'old': node.get(f), 'new': v} for f, v in new.items() if node.get(f) != v]
            else:
                field = path + ['name'] if role == 'comp' else path + ['text'] if isinstance(node, dict) else path
                changes = [{'path': field, 'old': ProjectSpec.at(spec, field), 'new': text}]
            old = self._line(role, node)
            if changes:
                self._done(self.spec.edit(changes))
            return f'{id}: "{old}" → "{text}"'
        except ValueError as e:
            return f'실패: {e}'

    def spec_remove(self, id: str) -> str:
        try:
            path = self._path(id)
            role = ProjectSpec.role(path)
            node = ProjectSpec.at(self._spec(), path)
            self._done(self.spec.remove(path, ProjectSpec.seen(role, node)))
            return f'지움: {id} "{self._line(role, node)}". 뒤 형제의 번호는 하나씩 당겨졌다'
        except ValueError as e:
            return f'실패: {e}'

    def spec_move(self, id: str, parent: str) -> str:
        try:
            spec = self._spec()
            path = self._path(id)
            dest = self._path(parent) if parent.strip() else []
            role = ProjectSpec.role(path)
            node, target = ProjectSpec.at(spec, path), ProjectSpec.at(spec, dest)
            got = self._done(self.spec.move(path, ProjectSpec.seen(role, node), dest, ProjectSpec.seen(ProjectSpec.role(dest), target)))
            return f'옮김: {id} → {self._id(got["path"])} {self._line(role, node)}. 옛 자리 뒤 형제의 번호는 하나씩 당겨졌다'
        except ValueError as e:
            return f'실패: {e}'

    def run(self) -> None:
        self.server.run('stdio')

    def _spec(self) -> dict:
        got = self.spec.read()
        if got['status'] == 'none':
            raise ValueError('이 프로젝트에 spec.json 이 없다')
        if got['status'] != 'ok':
            raise ValueError(got['message'])
        return got['spec']

    @staticmethod
    def _done(got: dict) -> dict:
        if got['status'] != 'ok':
            raise ValueError(got['message'])
        return got

    # 개체 번호 → 스펙 JSON 안의 자리
    @staticmethod
    def _path(id: str) -> list:
        path, role = [], 'root'
        for seg in id.strip().split('.'):
            m = SEGMENT.match(seg)
            key = m and STEP.get((role, m.group(1)))
            if not key:
                raise ValueError(f'개체 번호가 아니다: {id}')
            path += [key, int(m.group(2)) - 1]
            role = ProjectSpec.role(path)
        return path

    # 스펙 JSON 안의 자리 → 개체 번호
    @staticmethod
    def _id(path: list) -> str:
        return '.'.join(f'{LETTER[path[k]]}{path[k + 1] + 1}' for k in range(0, len(path), 2))

    # 구성요소나 기능 하나와 그 아래를 들여쓴 줄로. 구성요소 아래는 스펙 패널에 놓인 차례대로 설명, 하위 구성요소, 목업, 기능, 하지 않는 것
    def _tree(self, node, path: list, depth: int) -> list[str]:
        role = ProjectSpec.role(path)
        pad = '  ' * depth
        lines = [f'{pad}{self._id(path)} {self._line(role, node)}']
        if not isinstance(node, dict):
            return lines
        keys = ('descs', 'children', 'mocks', 'does', 'donts') if role == 'comp' else ('then',)
        for key in keys:
            for i, kid in enumerate(node.get(key) or []):
                kid_path = path + [key, i]
                if ProjectSpec.role(kid_path) in ('comp', 'do'):
                    lines += self._tree(kid, kid_path, depth + 1)
                else:
                    lines.append(f'{pad}  {self._id(kid_path)} {self._line(ProjectSpec.role(kid_path), kid)}')
        return lines

    # 개체 한 줄 글. 용어는 `낱말: 뜻`, 목업은 `이름 | 경로`
    @staticmethod
    def _line(role: str, node) -> str:
        if isinstance(node, str):
            return node
        if role == 'term':
            return f'{node.get("word", "")}: {node.get("meaning", "")}'
        if role == 'mock':
            return f'{node.get("name", "")} | {node.get("href", "")}'
        return node.get('name') if role == 'comp' else node.get('text', '')

    def _label(self, spec: dict, path: list) -> str:
        return f'{self._id(path)} {self._line(ProjectSpec.role(path), ProjectSpec.at(spec, path))}'

    # 도구가 받은 한 줄 글을 스펙에 넣을 값으로. 용어는 `낱말: 뜻`, 목업은 `이름 | 경로나 URL`
    @staticmethod
    def _fields(kind: str, text: str) -> str | dict:
        if kind == 'term':
            word, sep, meaning = text.partition(':')
            if not sep:
                raise ValueError('용어는 `낱말: 뜻` 으로 쓴다')
            return {'word': word.strip(), 'meaning': meaning.strip()}
        if kind == 'mock':
            name, sep, href = text.partition('|')
            if not sep:
                raise ValueError('목업은 `이름 | 경로나 URL` 로 쓴다')
            return {'name': name.strip(), 'href': href.strip()}
        return text
