# 훅 기록을 턴 목록으로 조립한다. 턴 번호는 응답이 있는 turn 기록의 순서, 사안 ID 는 `턴-순번`
class TurnBuilder:
    def build(self, events: list[dict]) -> dict:
        turns: list[dict] = []
        prompts: list[str] = []
        after: str | None = None
        session_id: str | None = None
        for e in events:
            kind = e.get('event')
            session_id = e.get('session_id') or session_id
            if kind == 'session_start':
                # /clear, compact 뒤 첫 턴에 표시한다. 에이전트 맥락이 바뀐 지점
                if e.get('source') in ('clear', 'compact'):
                    after = e['source']
            elif kind == 'prompt':
                prompts.append(e.get('prompt') or '')
            elif kind == 'turn':
                if not (e.get('text') or '').strip():
                    continue
                n = len(turns) + 1
                items = [{**item, 'id': f'{n}-{k}'} for k, item in enumerate(e.get('items') or [], 1)]
                turns.append({
                    'turn': n, 'prompt': '\n\n'.join(prompts), 'text': e.get('text') or '',
                    'preamble': e.get('preamble') or '', 'items': items,
                    'session_id': e.get('session_id'), 'at': e.get('at'), 'after': after,
                })
                prompts = []
                after = None
        # 마지막 턴 뒤에 들어온 입력이 있으면 에이전트가 그것을 처리하는 중이다
        return {'turns': turns, 'pending': '\n\n'.join(prompts) if prompts else None, 'session_id': session_id}
