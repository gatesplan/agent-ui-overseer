# Claude Code 훅 실행 스크립트(SessionStart, UserPromptSubmit, Stop). 설치 없이 src 를 경로에 올려 쓴다
# 전역 설정에 등록되므로 모든 세션에서 불린다. 패널이 띄운 세션(OVERSEER_TAB)이 아니면 무거운 import 전에 바로 끝낸다
import os
import sys

TAB = os.environ.get('OVERSEER_TAB')
if not TAB:
    sys.exit(0)

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'src'))

from loguru import logger

from project_manager.l0.permission_gate import PermissionGate
from project_manager.l0.record_store import RecordStore
from project_manager.l2.capture_hook import CaptureHook

# 패널 서버가 자식 세션에 넘기는 값. 서버 포트(권한 결정을 받을 곳)와 기록 폴더
PORT = os.environ.get('OVERSEER_PORT')
DATA = Path(os.environ.get('OVERSEER_DATA') or ROOT / 'data')


def main() -> int:
    logger.remove()
    logger.add(DATA / 'logs' / 'capture_hook.log', rotation='1 MB', encoding='utf-8')
    try:
        hook_input = json.loads(sys.stdin.buffer.read().decode('utf-8') or '{}')
        gate = PermissionGate(DATA / 'permissions', int(PORT) if PORT and PORT.isdigit() else None)
        # 기록 목록은 세션 시작 때만 읽는다. 다른 이벤트에서 DB 를 열지 않게 한다
        records = RecordStore(DATA / 'overseer.db') if hook_input.get('hook_event_name') == 'SessionStart' else None
        out = CaptureHook(DATA / 'captures', ROOT / 'docs' / 'item-protocol.md', gate, records).run(hook_input, TAB)
        if out:
            sys.stdout.buffer.write(out.encode('utf-8'))
    except Exception:
        # 훅 실패가 에이전트 세션을 막으면 안 된다
        logger.exception("hook 실패")
    return 0


if __name__ == '__main__':
    sys.exit(main())
