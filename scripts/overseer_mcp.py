# 결정 아카이브 조회(읽기 전용)와 프로젝트 스펙 도구 MCP 서버(stdio). 패널이 띄운 claude 세션에 --mcp-config 로 붙는다
# 환경변수: OVERSEER_PROJECT(프로젝트 폴더). 패널이 탭마다 설정 파일에 넣는다. 읽는 곳은 그 프로젝트와 상위 폴더의 .overseer/, 스펙은 그 폴더의 spec.json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if (ROOT / 'src' / 'project_manager').is_dir():
    sys.path.insert(0, str(ROOT / 'src'))

from project_manager.l0.project_spec import ProjectSpec
from project_manager.l0.record_store import RecordStore
from project_manager.l1.archive_query import ArchiveQuery
from project_manager.l2.overseer_mcp import OverseerMcp


def main() -> int:
    project = os.environ.get('OVERSEER_PROJECT') or os.getcwd()
    query = ArchiveQuery(RecordStore(), project)
    OverseerMcp(query, ProjectSpec(project)).run()
    return 0


if __name__ == '__main__':
    sys.exit(main())
