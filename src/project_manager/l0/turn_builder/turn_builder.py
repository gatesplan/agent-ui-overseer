# 훅 기록을 턴 목록으로 조립한다. 턴 번호는 응답이 있는 turn 기록의 순서, 사안 ID 는 `턴-순번`
class TurnBuilder:
    def build(self, events: list[dict]) -> dict:
        turns: list[dict] = []
        # 아직 어느 턴에도 들어가지 않은 입력 훅 기록. 입력 훅은 대기열에 넣는 순간 불려 앞 턴보다 먼저 올 수 있다
        waiting: list[str] = []
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
                waiting.append(e.get('prompt') or '')
            elif kind == 'turn':
                if not (e.get('text') or '').strip():
                    continue
                prompts = e.get('prompts')
                if prompts is None:
                    # 기록 파일에서 읽지 못한 턴은 그때까지 온 입력 전부로 본다
                    prompts, waiting = waiting, []
                else:
                    waiting = self._consume(waiting, prompts)
                if turns and turns[-1]['open']:
                    self._extend(turns[-1], e, prompts)
                else:
                    turns.append(self._new(len(turns) + 1, e, prompts, after))
                    after = None
                # 응답이 끝났을 때 대기열에 입력이 남아 있으면 에이전트는 쉬지 않고 이어 간다. 다음 응답을 같은 턴에 붙인다
                turns[-1]['open'] = bool(waiting)
        for t in turns:
            del t['open']
        # 남은 입력이 있으면 에이전트가 그것을 처리하는 중이다
        return {'turns': turns, 'pending': '\n\n'.join(waiting) if waiting else None, 'session_id': session_id}

    def _new(self, n: int, e: dict, prompts: list[str], after: str | None) -> dict:
        items = [{**item, 'id': f'{n}-{k}'} for k, item in enumerate(e.get('items') or [], 1)]
        return {
            'turn': n, 'prompt': '\n\n'.join(prompts), 'text': e.get('text') or '',
            'preamble': e.get('preamble') or '', 'items': items, 'parts': 1,
            'session_id': e.get('session_id'), 'at': e.get('at'), 'after': after, 'open': False,
        }

    # 이어진 응답을 턴에 붙인다. 사안 ID 는 그 턴 안에서 이어 매긴다
    def _extend(self, turn: dict, e: dict, prompts: list[str]) -> None:
        n, start = turn['turn'], len(turn['items'])
        turn['items'] += [{**item, 'id': f'{n}-{start + k}'} for k, item in enumerate(e.get('items') or [], 1)]
        turn['prompt'] = '\n\n'.join(p for p in [turn['prompt'], *prompts] if p)
        turn['text'] = f"{turn['text']}\n\n{e.get('text') or ''}"
        turn['preamble'] = '\n\n'.join(p for p in [turn['preamble'], e.get('preamble') or ''] if p)
        turn['parts'] += 1
        turn['session_id'], turn['at'] = e.get('session_id'), e.get('at')

    # 턴이 받은 입력을 대기 목록에서 지운다. 맞춘 것보다 앞에 남은 입력은 이미 지나간 것이라 함께 지운다
    def _consume(self, waiting: list[str], prompts: list[str]) -> list[str]:
        keys = [self._key(p) for p in waiting]
        last = -1
        for p in prompts:
            k = self._key(p)
            for i in range(last + 1, len(keys)):
                if keys[i] == k:
                    last = i
                    break
        return waiting[last + 1:]

    def _key(self, text: str) -> str:
        return ' '.join(text.split())
