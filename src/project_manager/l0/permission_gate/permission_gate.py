import json
import re
import time
import urllib.request
import uuid
from pathlib import Path

# 화면이 보내는 결정: allow(허용), deny(거부), terminal(터미널 확인 창에 맡김)
BEHAVIORS = ('allow', 'deny', 'terminal')
REQUEST_ID = re.compile(r'^[0-9a-f]{32}$')


# 권한 요청 훅과 패널 화면 사이의 결정 전달. 훅은 요청 ID 로 결정 파일을 기다리고, 서버는 화면의 결정을 그 파일로 쓴다
# 서버가 없거나 결정을 받을 수 없는 버전이면 기다리지 않는다. 그때는 claude 가 원래 확인 창을 띄운다
class PermissionGate:
    def __init__(self, decisions_dir: str | Path, port: int | None, timeout: float = 1500, interval: float = 0.3):
        self.decisions_dir = Path(decisions_dir)
        self.port = port
        self.timeout = timeout
        self.interval = interval

    def new_id(self) -> str:
        return uuid.uuid4().hex

    # 패널 서버가 떠 있고 권한 결정을 받을 수 있는지
    def ready(self) -> bool:
        if not self.port:
            return False
        try:
            with urllib.request.urlopen(f'http://127.0.0.1:{self.port}/api/health', timeout=2) as res:
                return bool(json.loads(res.read().decode('utf-8')).get('permissions'))
        except Exception:
            return False

    # 결정 파일이 생길 때까지 기다려 {behavior, message} 를 돌려준다. 시간이 지나면 None
    def wait(self, request_id: str) -> dict | None:
        path = self.decisions_dir / f'{request_id}.json'
        end = time.monotonic() + self.timeout
        while time.monotonic() < end:
            if path.exists():
                try:
                    decision = json.loads(path.read_text(encoding='utf-8'))
                except (OSError, json.JSONDecodeError):
                    time.sleep(self.interval)
                    continue
                path.unlink(missing_ok=True)
                return decision
            time.sleep(self.interval)
        return None

    # 서버 쪽: 화면의 결정을 결정 파일로 쓴다
    def decide(self, request_id: str, behavior: str, message: str = '') -> None:
        if not REQUEST_ID.match(request_id):
            raise ValueError(f'요청 ID 형식이 아니다: {request_id}')
        if behavior not in BEHAVIORS:
            raise ValueError(f'알 수 없는 결정: {behavior}')
        self.decisions_dir.mkdir(parents=True, exist_ok=True)
        tmp = self.decisions_dir / f'{request_id}.tmp'
        tmp.write_text(json.dumps({'behavior': behavior, 'message': message}, ensure_ascii=False), encoding='utf-8')
        tmp.replace(self.decisions_dir / f'{request_id}.json')

    # 훅 출력. terminal 이나 결정 없음이면 빈 문자열(확인 창을 그대로 띄운다)
    def hook_output(self, decision: dict | None) -> str:
        if not decision or decision.get('behavior') not in ('allow', 'deny'):
            return ''
        body = {'behavior': decision['behavior']}
        if decision['behavior'] == 'deny':
            body['message'] = decision.get('message') or '사용자가 패널에서 거부했다'
        return json.dumps({'hookSpecificOutput': {'hookEventName': 'PermissionRequest', 'decision': body}}, ensure_ascii=False)
