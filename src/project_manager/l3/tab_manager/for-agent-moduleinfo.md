---
sources:
  tab_manager.py: 506878a7c621
---
# tab_manager

열린 탭 목록. 새 탭 띄우기, 패널 재시작 때 닫지 않은 탭 복원, 이어서 띄우기, 닫기.

## TabManager

### Properties
tabs: dict[str, AgentTab]

### __init__
__init__(store: DecisionStore, captures_dir: Path, claude_args: str = '')
    claude_args 는 새로 여는 탭에 쓴다. 복원한 탭은 DB 에 남은 자기 인자를 쓴다.

### Methods

restore() -> None
    닫지 않은 탭을 꺼진 상태로 되살린다. 프로세스는 띄우지 않는다.
open(cwd: str, rows: int = 40, cols: int = 120, skip_permissions: bool = False) -> AgentTab
    raise ValueError    # 폴더가 없을 때
    skip_permissions 면 서버 기본 인자 뒤에 --dangerously-skip-permissions 를 붙인다. 탭 인자로 DB 에 남아 이어서 띄울 때도 쓴다.
resume(tab_id: str, rows: int = 40, cols: int = 120) -> AgentTab
    raise KeyError
    꺼진 탭을 마지막 claude 세션으로 이어서 띄운다. 기록된 세션이 없으면 새로 띄운다.
close(tab_id: str) -> None
    프로세스를 끝내고 DB 에 닫은 시각을 남긴다.
get(tab_id: str) -> AgentTab
    raise KeyError
poll() -> list[AgentTab]
    상태가 바뀐 탭.
shutdown() -> None
    서버가 끝날 때 모든 프로세스를 끝낸다. 탭은 닫지 않아 다음에 복원된다.
