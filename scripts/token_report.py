# Overseer 세션과 일반 Claude Code 세션의 토큰 사용량을 턴 단위로 비교한다
# Overseer 세션은 data/captures 의 훅 기록에 남은 세션 ID 로 가린다. 사용량은 ~/.claude/projects 의 대화 기록에서 읽는다
# 대화 기록은 Claude Code 가 기본 30일 뒤 지운다(cleanupPeriodDays). 그보다 오래된 세션은 비교할 수 없다
# 사용: python scripts/token_report.py [--days 7] [--turns 5] [--model opus] [--min-turns 3]
#   --turns N: 세션마다 처음 N턴만 센다. 대화가 길수록 맥락이 커져 턴당 입력이 늘어나므로 길이를 맞춰 비교할 때 쓴다
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TRANSCRIPTS = Path.home() / '.claude' / 'projects'
COLUMNS = [
    ('turns', '턴'), ('calls', '호출/턴'), ('tools', '도구/턴'), ('out', '출력/턴'),
    ('write', '캐시쓰기/턴'), ('input', '입력합/턴'), ('ctx', '평균맥락'), ('prompt', '입력문자'), ('reply', '응답문자'),
]


def overseer_sessions() -> set[str]:
    ids = set()
    for f in (ROOT / 'data' / 'captures').glob('*.jsonl'):
        for line in f.open(encoding='utf-8'):
            try:
                sid = json.loads(line).get('session_id')
            except json.JSONDecodeError:
                continue
            if sid:
                ids.add(sid)
    return ids


def is_prompt(row: dict) -> bool:
    if row.get('type') != 'user' or row.get('isSidechain') or row.get('isMeta'):
        return False
    content = (row.get('message') or {}).get('content')
    if isinstance(content, list):
        if any(isinstance(b, dict) and b.get('type') == 'tool_result' for b in content):
            return False
        content = ''.join(b.get('text', '') for b in content if isinstance(b, dict))
    return isinstance(content, str) and bool(content) and not content.startswith(('<', '[Request interrupted'))


def prompt_text(row: dict) -> str:
    content = (row.get('message') or {}).get('content')
    if isinstance(content, str):
        return content
    return ''.join(b.get('text', '') for b in content if isinstance(b, dict) and b.get('type') == 'text')


# 한 세션의 턴당 지표. 턴 끝은 대화 기록의 turn_duration. 한 응답이 여러 줄로 나뉘어 기록되므로 호출은 메시지 ID 로 센다
def analyze(path: Path, limit: int | None) -> dict | None:
    calls: dict[str, dict] = {}
    model = None
    turns = prompts = tools = prompt_chars = reply_chars = 0
    last_text = ''
    for line in path.open(encoding='utf-8'):
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get('isSidechain'):
            continue
        if limit and turns >= limit:
            break
        if row.get('type') == 'system' and row.get('subtype') == 'turn_duration':
            turns += 1
            reply_chars += len(last_text)
            last_text = ''
        elif is_prompt(row):
            prompts += 1
            prompt_chars += len(prompt_text(row))
        elif row.get('type') == 'assistant':
            message = row.get('message') or {}
            model = model or message.get('model')
            if message.get('id') and message.get('usage'):
                calls[message['id']] = message['usage']
            for block in message.get('content') or []:
                if block.get('type') == 'tool_use':
                    tools += 1
                elif block.get('type') == 'text' and block.get('text'):
                    last_text = block['text']
    if not turns or not calls:
        return None
    usage = list(calls.values())
    context = [u.get('input_tokens', 0) + u.get('cache_read_input_tokens', 0) + u.get('cache_creation_input_tokens', 0) for u in usage]
    return {
        'project': path.parent.name, 'session': path.stem[:8], 'model': model or '',
        'turns': turns, 'calls': len(usage) / turns, 'tools': tools / turns,
        'out': sum(u.get('output_tokens', 0) for u in usage) / turns,
        'write': sum(u.get('cache_creation_input_tokens', 0) for u in usage) / turns,
        'input': sum(context) / turns, 'ctx': sum(context) / len(context),
        'prompt': prompt_chars / max(prompts, 1), 'reply': reply_chars / turns,
    }


def median(values: list[float]) -> float:
    values = sorted(values)
    mid = len(values) // 2
    return values[mid] if len(values) % 2 else (values[mid - 1] + values[mid]) / 2


def main() -> int:
    parser = argparse.ArgumentParser(description='Overseer 세션과 일반 세션의 턴당 토큰 사용량 비교')
    parser.add_argument('--days', type=float, default=30, help='최근 며칠 안에 고친 대화 기록만 (기본 30)')
    parser.add_argument('--turns', type=int, help='세션마다 처음 N턴만 센다')
    parser.add_argument('--model', default='', help='모델 이름에 이 글자가 든 세션만 (예: opus)')
    parser.add_argument('--min-turns', type=int, default=3, help='이보다 턴이 적은 세션은 뺀다')
    args = parser.parse_args()

    ours = overseer_sessions()
    since = time.time() - args.days * 86400
    rows = []
    for path in TRANSCRIPTS.glob('*/*.jsonl'):
        if path.stat().st_mtime < since:
            continue
        a = analyze(path, args.turns)
        if not a or args.model not in a['model']:
            continue
        if a['turns'] < (args.turns or args.min_turns):
            continue
        a['overseer'] = path.stem in ours
        rows.append(a)
    if not rows:
        print('비교할 세션이 없다')
        return 1

    print('  ' + ' | '.join(['프로젝트'.ljust(28), '세션    '] + [label for _, label in COLUMNS]))
    for a in sorted(rows, key=lambda a: (not a['overseer'], a['project'])):
        cells = [a['project'][-28:].ljust(28), a['session']] + [f'{a[key]:,.0f}' for key, _ in COLUMNS]
        print(('* ' if a['overseer'] else '  ') + ' | '.join(cells))

    print(f"\n* Overseer 세션. 기간 {args.days:g}일{f', 처음 {args.turns}턴' if args.turns else ''}{f', 모델 {args.model}' if args.model else ''}")
    for name, group in (('Overseer', [a for a in rows if a['overseer']]), ('일반', [a for a in rows if not a['overseer']])):
        if group:
            print(f'{name} {len(group)}개 중앙값: ' + ', '.join(f'{label} {median([a[key] for a in group]):,.0f}' for key, label in COLUMNS))
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.exit(main())
