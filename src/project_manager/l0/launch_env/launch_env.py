import json
from pathlib import Path

# 프로젝트 안 패널 폴더. git 에서 스스로 빠진다(폴더 안 .gitignore 의 `*`)
FOLDER = '.overseer'
GITIGNORE = '*\n'
FILE = 'launch.json'


# 프로젝트의 탭 실행 환경. 탭을 열 때 claude 보다 먼저 실행할 한 줄(예: `conda activate py314`)을
# `<프로젝트>/.overseer/launch.json` 에 둔다. 경로가 컴퓨터마다 달라 git 에서 빠지는 폴더에 둔다
class LaunchEnv:
    def __init__(self, project: str | Path):
        self.root = Path(project) / FOLDER
        self.path = self.root / FILE

    # 적어 둔 한 줄. 없으면 빈 문자열
    def command(self) -> str:
        try:
            return str(json.loads(self.path.read_text(encoding='utf-8')).get('command') or '').strip()
        except (OSError, ValueError, AttributeError):
            return ''

    # 한 줄을 저장한다. 비우면 파일을 지워 서버 환경 그대로 띄우게 한다
    def save(self, command: str) -> None:
        command = ' '.join(command.split())
        if not command:
            self.path.unlink(missing_ok=True)
            return
        self.root.mkdir(parents=True, exist_ok=True)
        ignore = self.root / '.gitignore'
        if not ignore.exists():
            ignore.write_text(GITIGNORE, encoding='utf-8')
        self.path.write_text(json.dumps({'command': command}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
