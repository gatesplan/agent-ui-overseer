import json
import sys
import time

from project_manager.l0.module_map import ModuleMap


# 가짜 lnt: 인자를 보고 정해 둔 대로 답한다
def fake_lnt(tmp_path, body: str) -> ModuleMap:
    script = tmp_path / 'fake_lnt.py'
    script.write_text('import sys\n' + body, encoding='utf-8')
    return ModuleMap(command=[sys.executable, str(script)])


def ln_project(tmp_path):
    (tmp_path / 'proj' / 'src' / 'shop' / 'l0' / 'money').mkdir(parents=True)
    (tmp_path / 'proj' / 'src' / 'shop' / 'l0' / 'money' / 'money.py').write_text('class Money: pass\n', encoding='utf-8')
    return tmp_path / 'proj'


def test_scan_returns_map_from_lnt_json(tmp_path):
    data = {'format': 1, 'package': 'shop', 'modules': [{'name': 'l0.money', 'responsibility': '금액을 맡는다'}], 'edges': []}
    maps = fake_lnt(tmp_path, f"assert sys.argv[1:] == ['map', '--json']\nsys.stdout.reconfigure(encoding='utf-8')\nprint({json.dumps(json.dumps(data, ensure_ascii=False))})")
    assert maps.scan(ln_project(tmp_path)) == {'status': 'ok', 'map': data}


def test_scan_without_layers_does_not_run_lnt(tmp_path):
    maps = fake_lnt(tmp_path, "raise SystemExit('불리면 안 된다')")
    (tmp_path / 'plain' / 'src' / 'pkg').mkdir(parents=True)
    assert maps.scan(tmp_path / 'plain') == {'status': 'none'}
    assert maps.scan(tmp_path / 'nothing') == {'status': 'none'}


def test_scan_reports_old_lnt_and_failures(tmp_path):
    proj = ln_project(tmp_path)
    old = fake_lnt(tmp_path, "sys.stderr.write('lnt: error: unrecognized arguments: --json\\n'); sys.exit(2)")
    assert old.scan(proj)['status'] == 'unsupported'
    broken = fake_lnt(tmp_path, "sys.stderr.write('터졌다\\n'); sys.exit(1)")
    assert broken.scan(proj) == {'status': 'error', 'message': '터졌다'}
    garbage = fake_lnt(tmp_path, "print('not json')")
    assert garbage.scan(proj)['status'] == 'error'
    assert ModuleMap(command=['no-such-lnt-command']).scan(proj)['status'] == 'missing'


def test_signature_changes_when_source_or_layerinfo_changes(tmp_path):
    proj = ln_project(tmp_path)
    maps = ModuleMap(command=['lnt'])
    first = maps.signature(proj)
    assert first[0] == 1
    # 소스 밖의 파일과 캐시는 서명에 들지 않는다
    (proj / 'README.md').write_text('x', encoding='utf-8')
    (proj / 'src' / 'shop' / '__pycache__').mkdir()
    (proj / 'src' / 'shop' / '__pycache__' / 'x.py').write_text('x', encoding='utf-8')
    assert maps.signature(proj) == first
    time.sleep(0.01)
    (proj / 'src' / 'shop' / 'for-agent-layerinfo.md').write_text('## l0\n- money: 금액\n', encoding='utf-8')
    second = maps.signature(proj)
    assert second != first
    (proj / 'src' / 'shop' / 'l0' / 'money' / 'money.py').write_text('class Money:\n    pass\n', encoding='utf-8')
    assert maps.signature(proj) != second
    assert maps.signature(tmp_path / 'nothing') == (0, 0, 0)


def test_default_command_prefers_lnt_in_same_environment(tmp_path, monkeypatch):
    scripts = tmp_path / 'venv' / 'Scripts'
    scripts.mkdir(parents=True)
    monkeypatch.setattr(sys, 'executable', str(scripts / 'python.exe'))
    monkeypatch.setenv('OVERSEER_LNT', 'other-lnt')
    # 같은 환경에 lnt 가 없으면 환경변수
    assert ModuleMap().command == ['other-lnt']
    (scripts / 'lnt.exe').write_bytes(b'')
    assert ModuleMap().command == [str(scripts / 'lnt.exe')]
    # 직접 준 명령이 가장 앞선다
    assert ModuleMap(command=['x']).command == ['x']
