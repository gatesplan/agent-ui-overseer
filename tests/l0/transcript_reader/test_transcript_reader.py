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
