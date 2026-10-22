import json

from project_manager.l0.capture_log import CaptureLog


def test_poll_reads_only_new_complete_lines(tmp_path):
    path = tmp_path / 't.jsonl'
    log = CaptureLog(path)
    assert log.poll() is False

    path.write_text(json.dumps({'event': 'prompt', 'prompt': '가'}, ensure_ascii=False) + '\n{"event": "tu', encoding='utf-8')
    assert log.poll() is True
    assert [e['event'] for e in log.events] == ['prompt']

    # 쓰다 만 줄이 마저 쓰이면 그때 읽는다
    with path.open('a', encoding='utf-8') as f:
        f.write('rn"}\n')
    assert log.poll() is True
    assert [e['event'] for e in log.events] == ['prompt', 'turn']
    assert log.poll() is False


def test_poll_reads_line_after_crash_padding(tmp_path):
    # 비정상 종료로 쓰다 만 자리가 NUL 로 남고, 다시 띄운 뒤의 시작 기록이 그 뒤에 붙는다
    path = tmp_path / 't.jsonl'
    path.write_bytes(b'{"event": "turn"}\n' + b'\x00' * 600 + b'{"event": "session_start"}\n')
    log = CaptureLog(path)
    assert log.poll() is True
    assert [e['event'] for e in log.events] == ['turn', 'session_start']
