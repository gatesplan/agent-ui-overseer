import json

from project_manager.l0.transcript_reader import TranscriptReader


def _write(path, rows):
    path.write_text('\n'.join(json.dumps(r, ensure_ascii=False) for r in rows) + '\n', encoding='utf-8')


def test_last_turn_text_skips_tool_results_and_old_turns(tmp_path):
    path = tmp_path / 't.jsonl'
    _write(path, [
        {'type': 'user', 'message': {'content': '첫 질문'}},
        {'type': 'assistant', 'message': {'content': [{'type': 'text', 'text': '이전 턴'}]}},
        {'type': 'user', 'message': {'content': '두 번째 질문'}},
        {'type': 'assistant', 'message': {'content': [{'type': 'thinking', 'thinking': '...'}]}},
        {'type': 'assistant', 'message': {'content': [{'type': 'text', 'text': '확인합니다.'}]}},
        {'type': 'assistant', 'message': {'content': [{'type': 'tool_use', 'name': 'Read'}]}},
        {'type': 'user', 'message': {'content': [{'type': 'tool_result', 'content': 'x'}]}},
        {'type': 'user', 'isMeta': True, 'message': {'content': '주입된 메타'}},
        {'type': 'assistant', 'isSidechain': True, 'message': {'content': [{'type': 'text', 'text': '서브에이전트'}]}},
        {'type': 'assistant', 'message': {'content': [{'type': 'text', 'text': '### [보고] 끝'}]}},
    ])
    assert TranscriptReader(path).last_turn_text() == '확인합니다.\n\n### [보고] 끝'


def test_truncated_last_line_is_ignored(tmp_path):
    path = tmp_path / 't.jsonl'
    _write(path, [
        {'type': 'user', 'message': {'content': '질문'}},
        {'type': 'assistant', 'message': {'content': [{'type': 'text', 'text': '답'}]}},
    ])
    with path.open('a', encoding='utf-8') as f:
        f.write('{"type": "assist')
    assert TranscriptReader(path).last_turn_text() == '답'


def test_turn_prompts_after_last_turn_end_with_interrupt_merged(tmp_path):
    path = tmp_path / 't.jsonl'
    _write(path, [
        {'type': 'user', 'message': {'content': '이전 턴 입력'}},
        {'type': 'assistant', 'message': {'content': [{'type': 'text', 'text': '이전 응답'}]}},
        {'type': 'system', 'subtype': 'turn_duration'},
        {'type': 'user', 'message': {'content': '상태 확인'}},
        {'type': 'user', 'message': {'content': [{'type': 'text', 'text': '[Request interrupted by user]'}]}},
        {'type': 'user', 'message': {'content': '계속해봐'}},
        {'type': 'user', 'message': {'content': [{'type': 'tool_result', 'content': 'x'}]}},
        {'type': 'user', 'isMeta': True, 'message': {'content': '주입된 메타'}},
        {'type': 'assistant', 'message': {'content': [{'type': 'text', 'text': '응답'}]}},
    ])
    assert TranscriptReader(path).turn_prompts() == ['상태 확인', '계속해봐']


def test_prompt_absorbed_mid_turn_counts_as_turn_prompt(tmp_path):
    # 작업 중에 넣은 입력은 queued_command 첨부로 남는다. 턴 입력에 넣고, 응답 텍스트는 흡수 앞뒤를 모두 잇는다
    path = tmp_path / 't.jsonl'
    _write(path, [
        {'type': 'user', 'message': {'content': '변경사항 확인'}},
        {'type': 'assistant', 'message': {'content': [{'type': 'text', 'text': '확인합니다.'}]}},
        {'type': 'queue-operation', 'operation': 'enqueue', 'content': '유료 API 부르나?'},
        {'type': 'attachment', 'attachment': {'type': 'queued_command', 'prompt': '유료 API 부르나?', 'commandMode': 'prompt'}},
        {'type': 'attachment', 'attachment': {'type': 'queued_command', 'prompt': '/effort', 'commandMode': 'bash'}},
        {'type': 'assistant', 'message': {'content': [{'type': 'text', 'text': '부르지 않았습니다.'}]}},
    ])
    reader = TranscriptReader(path)
    assert reader.turn_prompts() == ['변경사항 확인', '유료 API 부르나?']
    assert reader.last_turn_text() == '확인합니다.\n\n부르지 않았습니다.'


def test_turn_prompts_without_turn_end_marker(tmp_path):
    # 턴 끝 표시가 없는 버전: 첫 턴이면 처음부터, 이전 응답이 있으면 경계를 몰라 None
    path = tmp_path / 't.jsonl'
    _write(path, [{'type': 'user', 'message': {'content': '첫 입력'}}])
    assert TranscriptReader(path).turn_prompts() == ['첫 입력']
    _write(path, [
        {'type': 'user', 'message': {'content': '첫 입력'}},
        {'type': 'assistant', 'message': {'content': [{'type': 'text', 'text': '응답'}]}},
        {'type': 'user', 'message': {'content': '둘째 입력'}},
    ])
    assert TranscriptReader(path).turn_prompts() is None


def test_turn_usage_counts_each_call_once_after_last_turn_end(tmp_path):
    path = tmp_path / 't.jsonl'
    usage = lambda i, o: {'input_tokens': i, 'cache_read_input_tokens': 100, 'cache_creation_input_tokens': 10, 'output_tokens': o}
    _write(path, [
        {'type': 'user', 'message': {'content': '이전'}},
        {'type': 'assistant', 'message': {'id': 'm0', 'model': 'x', 'usage': usage(9, 9), 'content': [{'type': 'text', 'text': '이전 응답'}]}},
        {'type': 'system', 'subtype': 'turn_duration'},
        {'type': 'user', 'message': {'content': '이번'}},
        # 한 응답이 두 줄로 기록된다. 같은 메시지 ID 는 한 번만
        {'type': 'assistant', 'message': {'id': 'm1', 'model': 'claude-opus', 'usage': usage(1, 5), 'content': [{'type': 'thinking', 'thinking': ''}]}},
        {'type': 'assistant', 'message': {'id': 'm1', 'model': 'claude-opus', 'usage': usage(1, 5), 'content': [{'type': 'tool_use', 'name': 'Bash'}]}},
        {'type': 'user', 'message': {'content': [{'type': 'tool_result', 'content': 'x'}]}},
        {'type': 'assistant', 'isSidechain': True, 'message': {'id': 's1', 'usage': usage(50, 50), 'content': []}},
        {'type': 'assistant', 'message': {'id': 'm2', 'model': 'claude-opus', 'usage': usage(2, 7), 'content': [{'type': 'text', 'text': '끝'}]}},
    ])
    assert TranscriptReader(path).turn_usage() == {
        'model': 'claude-opus', 'calls': 2, 'tools': 1,
        'input_tokens': 3, 'cache_creation_input_tokens': 20, 'cache_read_input_tokens': 200, 'output_tokens': 12,
    }
