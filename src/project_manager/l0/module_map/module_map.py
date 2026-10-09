import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

LAYER_DIR = ('l0', 'l1', 'l2', 'l3', 'l4', 'l5', 'l6', 'l7', 'l8', 'l9')


# 프로젝트의 ln 모듈 지도를 lnt 에게서 받아 온다. 소스가 바뀌었는지는 파일 서명으로 알아본다
# 지도 계산은 lnt 가 맡는다. overseer 는 ln 규칙을 따로 해석하지 않는다
class ModuleMap:
    # command: lnt 실행 명령. 없으면 overseer 와 같은 환경의 lnt(의존성으로 함께 설치된다),
    # 그것도 없으면 환경변수 OVERSEER_LNT, 그다음 PATH 의 lnt. 같은 환경을 먼저 보는 것은 설치한 판끼리 맞물리게 하려는 것
    def __init__(self, command: list[str] | None = None, timeout: float = 30):
        self.command = command or self._own_lnt() or shlex.split(os.environ.get('OVERSEER_LNT', 'lnt'), posix=False)
        self.timeout = timeout

    # 이 파이썬과 같은 가상환경의 lnt 실행 파일. 없으면 None
    @staticmethod
    def _own_lnt() -> list[str] | None:
        scripts = Path(sys.executable).parent
        for name in ('lnt.exe', 'lnt'):
            if (scripts / name).is_file():
                return [str(scripts / name)]
        return None

    # 지도 하나. status 는 ok(map 에 지도), none(ln 프로젝트 아님), missing(lnt 없음),
    # unsupported(lnt 가 --json 을 모름), error(그 밖의 실패, message 에 이유)
    def scan(self, cwd: str | Path) -> dict:
        cwd = Path(cwd)
        if not self._has_layers(cwd):
            return {'status': 'none'}
        exe = shutil.which(self.command[0]) or (self.command[0] if Path(self.command[0]).is_file() else None)
        if not exe:
            return {'status': 'missing', 'message': f'{self.command[0]} 명령이 없다'}
        env = {**os.environ, 'PYTHONIOENCODING': 'utf-8'}
        try:
            run = subprocess.run([exe, *self.command[1:], 'map', '--json'], cwd=cwd, env=env, capture_output=True,
                                 encoding='utf-8', errors='replace', timeout=self.timeout)
        except subprocess.TimeoutExpired:
            return {'status': 'error', 'message': f'lnt 가 {self.timeout:.0f}초 안에 끝나지 않았다'}
        except OSError as e:
            return {'status': 'error', 'message': str(e)}
        if run.returncode == 2 and 'unrecognized arguments' in run.stderr:
            return {'status': 'unsupported', 'message': 'lnt 가 map --json 을 모른다. ff-lntools 를 새 판으로 올린다'}
        if run.returncode != 0:
            return {'status': 'error', 'message': (run.stderr or run.stdout).strip()[-500:]}
        try:
            return {'status': 'ok', 'map': json.loads(run.stdout)}
        except json.JSONDecodeError:
            return {'status': 'error', 'message': 'lnt 출력이 JSON 이 아니다'}

    # 소스 서명: src 아래 .py 와 layerinfo 문서의 (개수, 가장 늦은 수정 시각, 크기 합). 하나라도 바뀌면 다시 받는다
    def signature(self, cwd: str | Path) -> tuple:
        src = Path(cwd) / 'src'
        if not src.is_dir():
            return (0, 0, 0)
        count, latest, size = 0, 0, 0
        for root, dirs, files in os.walk(src):
            dirs[:] = [d for d in dirs if not d.startswith(('.', '__pycache__'))]
            for name in files:
                if not (name.endswith('.py') or name == 'for-agent-layerinfo.md'):
                    continue
                try:
                    st = os.stat(os.path.join(root, name))
                except OSError:
                    continue
                count += 1
                latest = max(latest, st.st_mtime_ns)
                size += st.st_size
        return (count, latest, size)

    # src/<패키지>/l0 같은 층 폴더가 있는지. 없으면 lnt 를 띄우지 않는다
    @staticmethod
    def _has_layers(cwd: Path) -> bool:
        src = cwd / 'src'
        if not src.is_dir():
            return False
        return any((pkg / layer).is_dir() for pkg in src.iterdir() if pkg.is_dir() for layer in LAYER_DIR)
