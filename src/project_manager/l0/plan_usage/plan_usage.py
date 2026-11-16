import json
import shutil
import subprocess
from datetime import datetime, timezone

# CLI 의 SDK 제어 요청. 사용량 미터처럼 요금제 한도만 필요한 쪽은 지난 7일 대화 기록 훑기를 건너뛴다
REQUEST = {'type': 'control_request', 'request_id': 'overseer-usage',
           'request': {'subtype': 'get_usage', 'skip_behaviors': True}}
# 대화를 시작하지 않는 헤드리스 실행. 세션 파일을 남기지 않고 MCP 서버를 띄우지 않는다
ARGS = ['-p', '--input-format', 'stream-json', '--output-format', 'stream-json', '--verbose',
        '--no-session-persistence', '--strict-mcp-config']
# limits[] 가 없는 응답에서 창 이름을 /usage 의 행 종류로 옮긴다
WINDOWS = (('five_hour', 'session'), ('seven_day', 'weekly_all'), ('seven_day_opus', 'weekly_opus'),
           ('seven_day_sonnet', 'weekly_sonnet'))
LABELS = {'session': '5시간', 'weekly_all': '주간 전체', 'weekly_opus': '주간 Opus', 'weekly_sonnet': '주간 Sonnet'}


# Claude Code 요금제의 사용 한도 현황을 CLI 에게서 받아 온다. /usage 화면의 막대와 같은 행이다
# 공식 CLI 를 헤드리스로 띄워 묻는다. 구독 토큰을 꺼내 사용량 API 를 직접 부르지 않는다
# get_usage 는 CLI 가 실험 기능으로 밝힌 요청이라 응답 모양이 바뀔 수 있다. 모르는 모양이면 error 로 돌려준다
class PlanUsage:
    # command: claude 실행 명령. env: 자식 환경(부모 Claude Code 세션 표식을 걷어 낸 것)
    def __init__(self, command: list[str] | None = None, env: dict[str, str] | None = None, timeout: float = 30):
        self.command = command or ['claude']
        self.env = env
        self.timeout = timeout

    # {status, limits, at, message}. status 는 ok(limits 에 행), unavailable(요금제 한도가 없는 로그인),
    # missing(claude 없음), error(그 밖, message 에 이유). limits 는 [{kind, label, percent, resets_at, severity}]
    def fetch(self) -> dict:
        at = datetime.now(timezone.utc).isoformat()
        exe = shutil.which(self.command[0])
        if not exe:
            return {'status': 'missing', 'limits': [], 'at': at, 'message': f'{self.command[0]} 명령이 없다'}
        try:
            # 패널은 콘솔 없는 pythonw 로 돈다. 창을 만들지 않게 한다
            run = subprocess.run([exe, *self.command[1:], *ARGS], input=json.dumps(REQUEST) + '\n', env=self.env,
                                 capture_output=True, encoding='utf-8', errors='replace', timeout=self.timeout,
                                 creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        except subprocess.TimeoutExpired:
            return {'status': 'error', 'limits': [], 'at': at, 'message': f'claude 가 {self.timeout:.0f}초 안에 답하지 않았다'}
        except OSError as e:
            return {'status': 'error', 'limits': [], 'at': at, 'message': str(e)}
        response = self._response(run.stdout)
        if response is None:
            return {'status': 'error', 'limits': [], 'at': at,
                    'message': (run.stderr.strip() or 'get_usage 응답이 없다')[-300:]}
        if response.get('subtype') != 'success':
            return {'status': 'error', 'limits': [], 'at': at, 'message': str(response.get('error') or response)[:300]}
        body = response.get('response') or {}
        if not body.get('rate_limits_available') or not isinstance(body.get('rate_limits'), dict):
            return {'status': 'unavailable', 'limits': [], 'at': at, 'message': '요금제 사용 한도가 없는 로그인이다'}
        limits = self.limits(body['rate_limits'])
        if not limits:
            return {'status': 'error', 'limits': [], 'at': at, 'message': '응답에 한도 행이 없다'}
        return {'status': 'ok', 'limits': limits, 'at': at, 'message': ''}

    # stdin 을 닫으면 CLI 가 남은 요청에 답하고 끝난다. 받은 줄 중 우리 요청의 답
    @staticmethod
    def _response(stdout: str) -> dict | None:
        for line in stdout.splitlines():
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            response = row.get('response') if isinstance(row, dict) and row.get('type') == 'control_response' else None
            if isinstance(response, dict) and response.get('request_id') == REQUEST['request_id']:
                return response
        return None

    # 한도 행. 서버가 /usage 에 주는 limits[] 를 그 순서대로 쓴다. 없으면 창별 값과 모델별 주간 창으로 만든다
    @classmethod
    def limits(cls, rate: dict) -> list[dict]:
        rows = rate.get('limits')
        if isinstance(rows, list) and rows:
            return [r for r in (cls._row(row) for row in rows if isinstance(row, dict)) if r]
        out = []
        for key, kind in WINDOWS:
            window = rate.get(key)
            if isinstance(window, dict):
                out.append(cls._row({'kind': kind, 'percent': window.get('utilization'), 'resets_at': window.get('resets_at')}))
        for window in rate.get('model_scoped') or []:
            if isinstance(window, dict):
                out.append(cls._row({'kind': 'weekly_scoped', 'percent': window.get('utilization'),
                                     'resets_at': window.get('resets_at'), 'model': window.get('display_name')}))
        return [r for r in out if r]

    @staticmethod
    def _row(row: dict) -> dict | None:
        percent = row.get('percent')
        if not isinstance(percent, (int, float)):
            return None
        kind = str(row.get('kind') or '')
        scope = row.get('scope') if isinstance(row.get('scope'), dict) else {}
        model = row.get('model') or ((scope.get('model') or {}).get('display_name') if isinstance(scope.get('model'), dict) else None)
        label = f'주간 {model}' if kind == 'weekly_scoped' and model else LABELS.get(kind, kind or '한도')
        severity = row.get('severity')
        if severity not in ('normal', 'warning', 'critical'):
            severity = 'critical' if percent >= 90 else 'warning' if percent >= 75 else 'normal'
        return {'kind': kind, 'label': label, 'percent': max(0.0, min(100.0, float(percent))),
                'resets_at': row.get('resets_at'), 'severity': severity}
