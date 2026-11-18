import json
import shutil
import subprocess
from datetime import datetime, timezone

# CLI 의 SDK 시작 요청. 답에 /model 고르는 창과 같은 모델 목록(models)이 들어 있다
REQUEST = {'type': 'control_request', 'request_id': 'overseer-models', 'request': {'subtype': 'initialize'}}
# 대화를 시작하지 않는 헤드리스 실행. 세션 파일을 남기지 않고 MCP 서버를 띄우지 않는다
ARGS = ['-p', '--input-format', 'stream-json', '--output-format', 'stream-json', '--verbose',
        '--no-session-persistence', '--strict-mcp-config']
# 화면이 쓰는 칸. 나머지(effort 지원 등)는 버린다
KEYS = ('value', 'resolvedModel', 'displayName', 'description')


# Claude Code 에서 고를 수 있는 모델 목록을 CLI 에게서 받아 온다. /model 고르는 창과 같은 목록, 같은 순서다
# value 는 /model 에 넘기는 값(opus 같은 별칭이나 claude-opus-4-8 같은 모델 ID), resolvedModel 은 그 값이 지금 가리키는 모델 ID
# 목록과 버전은 CLI 가 정한다. 새 모델이 나와도 여기를 고치지 않는다
class ModelCatalog:
    # command: claude 실행 명령. env: 자식 환경(부모 Claude Code 세션 표식을 걷어 낸 것)
    def __init__(self, command: list[str] | None = None, env: dict[str, str] | None = None, timeout: float = 30):
        self.command = command or ['claude']
        self.env = env
        self.timeout = timeout

    # {status, models, at, message}. status 는 ok, missing(claude 없음), error(그 밖, message 에 이유)
    # models 는 [{value, resolvedModel, displayName, description}]
    def fetch(self) -> dict:
        at = datetime.now(timezone.utc).isoformat()
        exe = shutil.which(self.command[0])
        if not exe:
            return {'status': 'missing', 'models': [], 'at': at, 'message': f'{self.command[0]} 명령이 없다'}
        try:
            # 패널은 콘솔 없는 pythonw 로 돈다. 창을 만들지 않게 한다
            run = subprocess.run([exe, *self.command[1:], *ARGS], input=json.dumps(REQUEST) + '\n', env=self.env,
                                 capture_output=True, encoding='utf-8', errors='replace', timeout=self.timeout,
                                 creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        except subprocess.TimeoutExpired:
            return {'status': 'error', 'models': [], 'at': at, 'message': f'claude 가 {self.timeout:.0f}초 안에 답하지 않았다'}
        except OSError as e:
            return {'status': 'error', 'models': [], 'at': at, 'message': str(e)}
        response = self._response(run.stdout)
        if response is None:
            return {'status': 'error', 'models': [], 'at': at, 'message': (run.stderr.strip() or 'initialize 응답이 없다')[-300:]}
        if response.get('subtype') != 'success':
            return {'status': 'error', 'models': [], 'at': at, 'message': str(response.get('error') or response)[:300]}
        models = self.models((response.get('response') or {}).get('models'))
        if not models:
            return {'status': 'error', 'models': [], 'at': at, 'message': '응답에 모델 목록이 없다'}
        return {'status': 'ok', 'models': models, 'at': at, 'message': ''}

    # 받은 줄 중 우리 요청의 답. stdin 을 닫으면 CLI 가 남은 요청에 답하고 끝난다
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

    # 값과 이름이 있는 항목만 받은 순서대로. 가리키는 모델을 모르면 값 그대로 둔다
    @staticmethod
    def models(rows) -> list[dict]:
        out = []
        for row in rows if isinstance(rows, list) else []:
            if not isinstance(row, dict) or not isinstance(row.get('value'), str) or not row['value']:
                continue
            item = {k: row.get(k) if isinstance(row.get(k), str) else '' for k in KEYS}
            item['resolvedModel'] = item['resolvedModel'] or item['value']
            item['displayName'] = item['displayName'] or item['value']
            out.append(item)
        return out
