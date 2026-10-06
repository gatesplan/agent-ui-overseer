# Overseer 훅을 Claude Code 전역 설정(~/.claude/settings.json)에 등록한다. 여러 번 실행해도 한 벌만 남는다
# 훅은 패널이 띄운 세션(OVERSEER_TAB)에서만 동작하고 다른 세션에서는 바로 끝난다
# 사용: uv run python scripts/install_hooks.py [--remove]
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SETTINGS = Path.home() / '.claude' / 'settings.json'
SCRIPT = ROOT / 'scripts' / 'capture_hook.py'
PYTHON = ROOT / '.venv' / 'Scripts' / 'python.exe'
EVENTS = ('SessionStart', 'UserPromptSubmit', 'Stop')


def ours(group: dict) -> bool:
    return any('capture_hook.py' in h.get('command', '') for h in group.get('hooks', []))


def main() -> int:
    remove = '--remove' in sys.argv
    if not remove and not PYTHON.exists():
        print(f'가상환경이 없다: {PYTHON}. 먼저 uv sync')
        return 1
    settings = json.loads(SETTINGS.read_text(encoding='utf-8')) if SETTINGS.exists() else {}
    if SETTINGS.exists():
        shutil.copy2(SETTINGS, SETTINGS.with_name('settings.json.bak-overseer'))

    hooks = settings.setdefault('hooks', {})
    command = f'"{PYTHON}" "{SCRIPT}"'
    for event in EVENTS:
        groups = [g for g in hooks.get(event, []) if not ours(g)]
        if not remove:
            groups.append({'hooks': [{'type': 'command', 'command': command, 'timeout': 10}]})
        if groups:
            hooks[event] = groups
        else:
            hooks.pop(event, None)
    if not hooks:
        settings.pop('hooks')

    SETTINGS.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS.write_text(json.dumps(settings, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f"{'제거' if remove else '등록'}: {SETTINGS} ({', '.join(EVENTS)})")
    return 0


if __name__ == '__main__':
    sys.exit(main())
