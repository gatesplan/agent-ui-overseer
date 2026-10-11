from pathlib import Path

# conda 가 만든 환경을 모두 적어 두는 파일. conda 를 띄우지 않고 목록을 읽는다
ENVIRONMENTS_TXT = Path.home() / '.conda' / 'environments.txt'


# 이 컴퓨터의 conda 환경 목록. 새 세션 창의 conda 단추가 쓴다
# base(설치 폴더)는 빼고, envs 폴더 아래 환경만 이름으로 내놓는다. 이름이 겹치면 경로로 activate 한다
class CondaEnvs:
    def __init__(self, environments: Path | None = None):
        self.environments = environments or ENVIRONMENTS_TXT

    # [{name, prefix, activate}]. 이름 순. conda 가 없으면 빈 목록
    def list(self) -> list[dict]:
        try:
            lines = self.environments.read_text(encoding='utf-8', errors='replace').splitlines()
        except OSError:
            return []
        prefixes = []
        for line in lines:
            p = Path(line.strip())
            if line.strip() and p.parent.name.lower() == 'envs' and (p / 'conda-meta').is_dir() and p not in prefixes:
                prefixes.append(p)
        names = [p.name for p in prefixes]
        envs = [{'name': p.name, 'prefix': str(p),
                 'activate': f'conda activate {p.name if names.count(p.name) == 1 else str(p)}'} for p in prefixes]
        return sorted(envs, key=lambda e: (e['name'].lower(), e['prefix'].lower()))
