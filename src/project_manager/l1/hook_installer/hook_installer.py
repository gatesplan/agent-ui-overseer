import json
import os
import shutil
import socket
import subprocess
import sys
import urllib.request
import uuid
from pathlib import Path

from ...l0.install_layout import InstallLayout

SETTINGS = Path.home() / '.claude' / 'settings.json'
EVENTS = ('SessionStart', 'UserPromptSubmit', 'Stop', 'Notification', 'PermissionRequest')
# 권한 요청 훅은 화면의 결정을 기다린다. PermissionGate 의 기다림(1500초)보다 길게 둔다
TIMEOUTS = {'PermissionRequest': 1800}
PORT = 47310


# Claude Code 전역 설정(~/.claude/settings.json)에 패널 훅을 걸고 풀며, 설치가 제대로 됐는지 점검한다
# 훅은 패널이 띄운 세션(OVERSEER_TAB)에서만 동작한다. 훅 명령은 이 패키지가 설치된 환경의 python 을 직접 가리킨다
# 사용: overseer-setup [--check | --uninstall]  (저장소에서는 uv run python scripts/setup.py 도 같다)
class HookInstaller:
    def __init__(self, layout: InstallLayout | None = None, settings: Path = SETTINGS):
        self.layout = layout or InstallLayout()
        self.settings = settings
        self.hook = self.layout.hook_script
        # 화면 없는 pythonw 로 돌고 있어도 훅은 python 으로 건다. 훅의 출력을 claude 가 읽는다
        exe = Path(sys.executable)
        self.python = exe.with_name('python.exe') if exe.name.lower() == 'pythonw.exe' else exe
        self.results: list[tuple[bool, str, str]] = []

    @classmethod
    def main(cls) -> int:
        return cls().run(sys.argv[1:])

    def run(self, argv: list[str]) -> int:
        if '--uninstall' in argv:
            self.write_hooks(remove=True)
            print(f'훅 제거: {self.settings}')
            return 0
        if '--check' not in argv:
            self.write_hooks(remove=False)
            print(f'훅 등록: {self.settings} ({", ".join(EVENTS)}). 이전 설정: settings.json.bak-overseer')
        self.check()
        failed = [name for ok, name, _ in self.results if not ok]
        if failed:
            print(f'\n실패 {len(failed)}건: {", ".join(failed)}. INSTALL.md 의 문제 해결을 본다')
            return 1
        run = 'overseer' if self.layout.installed else 'uv run overseer'
        print(f'\n준비 완료. 실행: {run}  →  http://127.0.0.1:{PORT}/')
        return 0

    @staticmethod
    def ours(group: dict) -> bool:
        return any('capture_hook.py' in h.get('command', '') for h in group.get('hooks', []))

    def load_settings(self) -> dict:
        return json.loads(self.settings.read_text(encoding='utf-8')) if self.settings.exists() else {}

    # 전역 설정에 훅을 한 벌만 남긴다. remove 면 우리 것만 지운다. 고치기 전 설정은 settings.json.bak-overseer 로 남긴다
    def write_hooks(self, remove: bool) -> None:
        settings = self.load_settings()
        if self.settings.exists():
            shutil.copy2(self.settings, self.settings.with_name('settings.json.bak-overseer'))
        hooks = settings.setdefault('hooks', {})
        command = f'"{self.python}" "{self.hook}"'
        for event in EVENTS:
            groups = [g for g in hooks.get(event, []) if not self.ours(g)]
            if not remove:
                groups.append({'hooks': [{'type': 'command', 'command': command, 'timeout': TIMEOUTS.get(event, 10)}]})
            if groups:
                hooks[event] = groups
            else:
                hooks.pop(event, None)
        if not hooks:
            settings.pop('hooks')
        self.settings.parent.mkdir(parents=True, exist_ok=True)
        self.settings.write_text(json.dumps(settings, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

    def check(self) -> None:
        self.report(sys.platform == 'win32', 'Windows', sys.platform)
        self.report(self.python.exists() and self.hook.exists(), '훅 실행 파일', f'{self.python} {self.hook}')

        claude = shutil.which('claude')
        if self.report(bool(claude), 'claude 명령', claude or 'Claude Code CLI 설치 필요: https://docs.claude.com/claude-code'):
            try:
                out = subprocess.run('claude --version', shell=True, capture_output=True, text=True, timeout=60)
                self.report(out.returncode == 0, 'claude 실행', out.stdout.strip() or out.stderr.strip())
            except subprocess.TimeoutExpired:
                self.report(False, 'claude 실행', '응답 없음')

        registered = self.load_settings().get('hooks', {})
        missing = [e for e in EVENTS if not any(self.ours(g) for g in registered.get(e, []))]
        self.report(not missing, '전역 훅 등록', f'빠짐: {", ".join(missing)}' if missing else str(self.settings))

        if self.python.exists() and self.hook.exists():
            # 패널 세션이 아니면 아무것도 하지 않고 끝나야 한다
            idle = self.run_hook({'hook_event_name': 'Stop'}, None)
            self.report(idle.returncode == 0 and not idle.stdout, '훅: 패널 밖 세션은 무시')
            # 패널 세션이면 규약을 주입하고 기록을 남긴다
            tab = f'setup-{uuid.uuid4().hex[:6]}'
            start = self.run_hook({'hook_event_name': 'SessionStart', 'session_id': 'setup', 'source': 'startup'}, tab)
            self.report('사안' in start.stdout.decode('utf-8', 'replace'), '훅: 사안 규약 주입')
            self.run_hook({'hook_event_name': 'Stop', 'session_id': 'setup', 'last_assistant_message': '### [보고] 점검'}, tab)
            record = InstallLayout.data() / 'captures' / f'{tab}.jsonl'
            rows = record.read_text(encoding='utf-8').splitlines() if record.exists() else []
            self.report(len(rows) == 2 and '"점검"' in rows[-1], '훅: 기록', str(record))
            record.unlink(missing_ok=True)

        try:
            with urllib.request.urlopen(f'http://127.0.0.1:{PORT}/api/tabs', timeout=2):
                self.report(True, f'포트 {PORT}', 'Overseer 가 이미 떠 있다')
        except Exception:
            with socket.socket() as s:
                free = s.connect_ex(('127.0.0.1', PORT)) != 0
            self.report(free, f'포트 {PORT}', '비어 있음' if free else '다른 프로그램이 쓰는 중. overseer --port <다른 번호>')

    def run_hook(self, payload: dict, tab: str | None) -> subprocess.CompletedProcess:
        env = {k: v for k, v in os.environ.items() if k != 'OVERSEER_TAB'}
        if tab:
            env['OVERSEER_TAB'] = tab
        return subprocess.run([str(self.python), str(self.hook)], input=json.dumps(payload).encode('utf-8'),
                              capture_output=True, env=env, timeout=30)

    def report(self, ok: bool, name: str, detail: str = '') -> bool:
        self.results.append((ok, name, detail))
        print(f"[{'OK' if ok else '실패'}] {name}{f' - {detail}' if detail else ''}", flush=True)
        return ok
