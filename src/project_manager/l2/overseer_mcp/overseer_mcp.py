from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

from project_manager.l1.archive_query import ArchiveQuery

INSTRUCTIONS = (
    '이 프로젝트에서 사용자가 내린 결정의 아카이브를 읽는다. 쓰기 도구는 없다. '
    '결정 기록이나 용어의 이력과 근거가 필요하면 record, 목록이나 검색은 records, '
    '어떤 제안을 내기 전에 같은 제안이 기각된 적이 있는지는 decisions(action="reject")로 본다.'
)
READ_ONLY = ToolAnnotations(read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False)


# 결정 아카이브 조회를 MCP 도구로 내놓는 읽기 전용 서버. 패널이 띄운 claude 세션에 --mcp-config 로 붙는다
class OverseerMcp:
    def __init__(self, query: ArchiveQuery):
        self.query = query
        self.server = MCPServer(name='overseer', instructions=INSTRUCTIONS)
        self.server.add_tool(self.records, name='records', annotations=READ_ONLY,
                             description='이 프로젝트의 결정 기록(D)과 용어(W) 목록. query 로 내용과 메모를 찾고, kind 로 D 나 W 만, '
                                         'include_replaced 로 대체된 옛 기록까지 본다.')
        self.server.add_tool(self.record, name='record', annotations=READ_ONLY,
                             description='기록 하나(예: D-3)를 자세히 본다. 대체 이력 전체, 원래 사안 본문, 근거 사안과 그에 대한 사용자 결정.')
        self.server.add_tool(self.decisions, name='decisions', annotations=READ_ONLY,
                             description='이 프로젝트의 지난 사안과 사용자 결정(답변, 승인, 보류, 기각, 확인)을 최근 순으로 찾는다. '
                                         'action="reject" 면 기각된 것과 그 사유만. 같은 제안을 다시 내기 전에 확인한다.')

    def records(self, query: str = '', kind: str = '', include_replaced: bool = False) -> str:
        return self.query.list_records(query, kind, include_replaced)

    def record(self, ref: str) -> str:
        return self.query.record(ref)

    def decisions(self, query: str = '', action: str = '', limit: int = 20) -> str:
        return self.query.decisions(query, action, limit)

    def run(self) -> None:
        self.server.run('stdio')
