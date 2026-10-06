# Overseer 설치, 점검, 제거. 에이전트가 이것만 실행하면 되게 한다
# 사용: uv run python scripts/setup.py              훅 등록 후 점검
#       uv run python scripts/setup.py --check      점검만
#       uv run python scripts/setup.py --uninstall  훅 제거
# 훅은 Claude Code 전역 설정(~/.claude/settings.json)에 등록한다. 패널이 띄운 세션(OVERSEER_TAB)에서만 동작한다
# 훅을 바꾼 뒤(이벤트 추가 등)에도 다시 실행한다. 이미 떠 있는 claude 세션은 다시 띄워야 새 훅을 쓴다
import json
import os
import shutil
import subprocess
import sys
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SETTINGS = Path.home() / '.claude' / 'settings.json'
HOOK = ROOT / 'scripts' / 'capture_hook.py'
PYTHON = ROOT / '.venv' / 'Scripts' / 'python.exe'
CAPTURES = ROOT / 'data' / 'captures'
EVENTS = ('SessionStart', 'UserPromptSubmit', 'Stop', 'Notification', 'PermissionRequest')
# 권한 요청 훅은 화면의 결정을 기다린다. PermissionGate 의 기다림(1500초)보다 길게 둔다
TIMEOUTS = {'PermissionRequest': 1800}
PORT = 47310

results: list[tuple[bool, str, str]] = []


def report(ok: bool, name: str, detail: str = '') -> bool:
    results.append((ok, name, detail))
    print(f"[{'OK' if ok else '실패'}] {name}{f' - {detail}' if detail else ''}", flush=True)
    return ok


def ours(group: dict) -> bool:
    return any('capture_hook.py' in h.get('command', '') for h in group.get('hooks', []))


def load_settings() -> dict:
    return json.loads(SETTINGS.read_text(encoding='utf-8')) if SETTINGS.exists() else {}


# 전역 설정에 훅을 한 벌만 남긴다. remove 면 우리 것만 지운다. 고치기 전 설정은 settings.json.bak-overseer 로 남긴다
def write_hooks(remove: bool) -> None:
    settings = load_settings()
    if SETTINGS.exists():
        shutil.copy2(SETTINGS, SETTINGS.with_name('settings.json.bak-overseer'))
    hooks = settings.setdefault('hooks', {})
    command = f'"{PYTHON}" "{HOOK}"'
    for event in EVENTS:
        groups = [g for g in hooks.get(event, []) if not ours(g)]
        if not remove:
            groups.append({'hooks': [{'type': 'command', 'command': command, 'timeout': TIMEOUTS.get(event, 10)}]})
        if groups:
            hooks[event] = groups
        else:
            hooks.pop(event, None)
    if not hooks:
        settings.pop('hooks')
    SETTINGS.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS.write_text(json.dumps(settings, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def run_hook(payload: dict, tab: str | None) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k != 'OVERSEER_TAB'}
    if tab:
        env['OVERSEER_TAB'] = tab
    return subprocess.run([str(PYTHON), str(HOOK)], input=json.dumps(payload).encode('utf-8'),
                          capture_output=True, env=env, timeout=30)


def check() -> None:
    report(sys.platform == 'win32', 'Windows', sys.platform)
    report(PYTHON.exists(), '프로젝트 가상환경', str(PYTHON) if PYTHON.exists() else 'uv sync 를 먼저 실행')

    claude = shutil.which('claude')
    if report(bool(claude), 'claude 명령', claude or 'Claude Code CLI 설치 필요: https://docs.claude.com/claude-code'):
        try:
            out = subprocess.run('claude --version', shell=True, capture_output=True, text=True, timeout=60)
            report(out.returncode == 0, 'claude 실행', out.stdout.strip() or out.stderr.strip())
        except subprocess.TimeoutExpired:
            report(False, 'claude 실행', '응답 없음')

    registered = load_settings().get('hooks', {})
    missing = [e for e in EVENTS if not any(ours(g) for g in registered.get(e, []))]
    report(not missing, '전역 훅 등록', f'빠짐: {", ".join(missing)}' if missing else str(SETTINGS))

    if PYTHON.exists():
        # 패널 세션이 아니면 아무것도 하지 않고 끝나야 한다
        idle = run_hook({'hook_event_name': 'Stop'}, None)
        report(idle.returncode == 0 and not idle.stdout, '훅: 패널 밖 세션은 무시')
        # 패널 세션이면 규약을 주입하고 기록을 남긴다
        tab = f'setup-{uuid.uuid4().hex[:6]}'
        start = run_hook({'hook_event_name': 'SessionStart', 'session_id': 'setup', 'source': 'startup'}, tab)
        report('사안' in start.stdout.decode('utf-8', 'replace'), '훅: 사안 규약 주입')
        run_hook({'hook_event_name': 'Stop', 'session_id': 'setup', 'last_assistant_message': '### [보고] 점검'}, tab)
        record = CAPTURES / f'{tab}.jsonl'
        rows = record.read_text(encoding='utf-8').splitlines() if record.exists() else []
        report(len(rows) == 2 and '"점검"' in rows[-1], '훅: 기록', str(record))
        record.unlink(missing_ok=True)

    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{PORT}/api/tabs', timeout=2):
            report(True, f'포트 {PORT}', 'Overseer 가 이미 떠 있다')
    except Exception:
        import socket
        with socket.socket() as s:
            free = s.connect_ex(('127.0.0.1', PORT)) != 0
        report(free, f'포트 {PORT}', '비어 있음' if free else '다른 프로그램이 쓰는 중. uv run overseer --port <다른 번호>')


def main() -> int:
    if '--uninstall' in sys.argv:
        write_hooks(remove=True)
        print(f'훅 제거: {SETTINGS}')
        return 0
    if '--check' not in sys.argv:
        if not PYTHON.exists():
            print(f'가상환경이 없다: {PYTHON}. 먼저 uv sync')
            return 1
        write_hooks(remove=False)
        print(f'훅 등록: {SETTINGS} ({", ".join(EVENTS)}). 이전 설정: settings.json.bak-overseer')
    check()
    failed = [name for ok, name, _ in results if not ok]
    if failed:
        print(f'\n실패 {len(failed)}건: {", ".join(failed)}. INSTALL.md 의 문제 해결을 본다')
        return 1
    print('\n준비 완료. 실행: uv run overseer  →  http://127.0.0.1:47310/')
    return 0


if __name__ == '__main__':
    sys.exit(main())
