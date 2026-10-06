# Claude Code Stop 훅 실행 스크립트. 설치 없이 src 를 경로에 올려 쓴다
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'src'))

from loguru import logger

from project_manager import CaptureHook


def main() -> int:
    logger.remove()
    logger.add(ROOT / 'data' / 'logs' / 'capture_hook.log', rotation='1 MB', encoding='utf-8')
    try:
        hook_input = json.loads(sys.stdin.buffer.read().decode('utf-8') or '{}')
        CaptureHook(ROOT / 'data' / 'captures').run(hook_input)
    except Exception:
        # 훅 실패가 에이전트 세션을 막으면 안 된다
        logger.exception("capture 실패")
    return 0


if __name__ == '__main__':
    sys.exit(main())
