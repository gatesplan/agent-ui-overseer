# 결정 아카이브 조회 MCP 서버(stdio, 읽기 전용). 패널이 띄운 claude 세션에 --mcp-config 로 붙는다
# 환경변수: OVERSEER_DATA(기록 폴더), OVERSEER_PROJECT(프로젝트 폴더). 패널이 탭마다 설정 파일에 넣는다
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'src'))

from project_manager.l0.decision_store import DecisionStore
from project_manager.l0.record_store import RecordStore
from project_manager.l1.archive_query import ArchiveQuery
from project_manager.l2.overseer_mcp import OverseerMcp


def main() -> int:
    data = Path(os.environ.get('OVERSEER_DATA') or ROOT / 'data')
    project = os.environ.get('OVERSEER_PROJECT') or os.getcwd()
    db = data / 'overseer.db'
    query = ArchiveQuery(DecisionStore(db), RecordStore(db), data / 'captures', project)
    OverseerMcp(query).run()
    return 0


if __name__ == '__main__':
    sys.exit(main())
