# Overseer 훅 등록, 점검, 제거. 저장소에서 쓰는 입구. 설치한 패키지에서는 overseer-setup 명령이 같은 일을 한다
# 사용: uv run python scripts/setup.py              훅 등록 후 점검
#       uv run python scripts/setup.py --check      점검만
#       uv run python scripts/setup.py --uninstall  훅 제거
# 훅은 Claude Code 전역 설정(~/.claude/settings.json)에 등록한다. 패널이 띄운 세션(OVERSEER_TAB)에서만 동작한다
# 훅을 바꾼 뒤(이벤트 추가 등)에도 다시 실행한다. 이미 떠 있는 claude 세션은 다시 띄워야 새 훅을 쓴다
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'src'))

from project_manager.l1.hook_installer import HookInstaller  # noqa: E402

if __name__ == '__main__':
    sys.exit(HookInstaller.main())
