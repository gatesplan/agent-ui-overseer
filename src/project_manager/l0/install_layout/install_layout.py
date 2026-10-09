import os
from pathlib import Path

# 설치한 패키지 안에서 화면, 규약, 실행 스크립트가 놓이는 폴더. wheel 을 만들 때 저장소의 것을 여기로 옮겨 담는다(pyproject)
ASSETS = '_assets'
# 이 컴퓨터의 패널 기록 폴더. 환경변수 OVERSEER_DATA 가 있으면 그것
DATA = Path.home() / '.overseer'


# overseer 가 놓인 자리. 저장소에서 바로 돌 때와 설치한 패키지로 돌 때 화면, 규약, 실행 스크립트, 기록 폴더의 위치가 다르다
# 설치한 패키지면 패키지 안 _assets, 아니면 저장소의 web/, docs/, scripts/
class InstallLayout:
    def __init__(self, package: str | Path | None = None):
        self.package = Path(package) if package else Path(__file__).resolve().parents[2]
        self.installed = (self.package / ASSETS).is_dir()
        self.root = self.package / ASSETS if self.installed else self.package.parents[1]

    @property
    def web(self) -> Path:
        return self.root / 'web'

    # 패널 세션에 넣는 사안 출력 규약
    @property
    def protocol(self) -> Path:
        return self.root / ('item-protocol.md' if self.installed else 'docs/item-protocol.md')

    # Claude Code 훅으로 등록하는 실행 스크립트
    @property
    def hook_script(self) -> Path:
        return self.root / 'scripts' / 'capture_hook.py'

    # 패널 세션에 붙이는 결정 아카이브 조회 MCP 서버
    @property
    def mcp_script(self) -> Path:
        return self.root / 'scripts' / 'overseer_mcp.py'

    # 이 컴퓨터의 패널 기록 폴더(탭, 캡처, 로그). 환경변수 OVERSEER_DATA, 없으면 ~/.overseer
    @staticmethod
    def data() -> Path:
        return Path(os.environ.get('OVERSEER_DATA') or DATA)
