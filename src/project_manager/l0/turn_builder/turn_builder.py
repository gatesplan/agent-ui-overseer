import re

# 사용자 응답이 아니라 상태만 알리는 알림. 화면에 띄우지 않는다
QUIET_NOTICES = ('idle_prompt', 'auth_success')
# 턴에 더하는 토큰 사용량 항목
USAGE_KEYS = ('calls', 'tools', 'input_tokens', 'cache_creation_input_tokens', 'cache_read_input_tokens', 'output_tokens')
# 시스템이 넣은 입력(백그라운드 작업 알림)의 시작. 입력 훅도 불리지만 사용자 입력이 아니다
SYSTEM_PROMPT_PREFIXES = ('<task-notification>',)
# 자동 압축 뒤 기록에 사용자 입력 대신 남는 요약문의 시작
COMPACT_SUMMARY_PREFIX = 'This session is being continued from a previous conversation'
# 터미널에서 친 명령(/login 등). 입력 훅은 불려도 응답 턴이 없을 수 있다
TERMINAL_COMMAND_PREFIX = '/'
# Claude Code 가 긴 붙여넣기를 감싸는 표시. 패널이 보낸 메시지가 이렇게 온다: <pasted_content id="71e1">…</pasted_content id="71e1">
PASTED = re.compile(r'<pasted_content(?: id="[^"]*")?>\n?(.*?)\n?</pasted_content(?: id="[^"]*")?>', re.S)
# 대화 기록에 사용자 입력처럼 남는 터미널 명령 줄(/clear, /model 등)과 그 출력
COMMAND = re.compile(r'<command-name>(.*?)</command-name>', re.S)
COMMAND_ARGS = re.compile(r'<command-args>(.*?)</command-args>', re.S)
COMMAND_OUTPUT_PREFIXES = ('<local-command-stdout>', '<local-command-stderr>')


# 예전 사안 ID(`#턴-순번`, 턴 번호가 탭 안에서 이어짐). 지난 기록의 본문과 출처를 새 ID 로 바꿀 때 쓴다
LEGACY_REF = re.compile(r'#(\d+)-(\d+)\b')
LEGACY_ID = re.compile(r'^(\d+)-(\d+)$')


# 훅 기록을 턴 목록으로 조립한다. 세션은 프로젝트 안에서 매긴 번호(새 탭, /clear 마다 오름), 턴 번호는 세션 안에서 응답이 있는 turn 기록의 순서
# 사안 ID 는 `<세션>S-<턴>-<순번>`. 프로젝트 안에서 겹치지 않는다
# 터미널에서 사용자 응답을 기다리는 것(권한 요청, 확인 알림)도 함께 가린다
class TurnBuilder:
    def build(self, events: list[dict]) -> dict:
        turns: list[dict] = []
        # 아직 어느 턴에도 들어가지 않은 입력 훅 기록. 입력 훅은 대기열에 넣는 순간 불려 앞 턴보다 먼저 올 수 있다
        waiting: list[str] = []
        after: str | None = None
        # 지금 세션 번호. /clear 마다 하나씩 올라간다. 화면은 앞 세션의 턴을 접는다
        session = 1
        # 지금 세션의 턴 수
        count = 0
        session_id: str | None = None
        # 패널의 결정을 기다리는 권한 요청(요청 ID 별), 마지막 확인 알림
        permissions: dict[str, dict] = {}
        attention: dict | None = None
        for seq, e in enumerate(events):
            kind = e.get('event')
            session_id = e.get('session_id') or session_id
            if kind in ('session_start', 'prompt', 'turn', 'permission_done'):
                # 에이전트가 다음으로 넘어갔으면 앞선 확인 알림은 끝난 것이다
                attention = None
            if kind == 'session_start':
                # /clear, compact 뒤 첫 턴에 표시한다. 에이전트 맥락이 바뀐 지점
                if e.get('source') in ('clear', 'compact'):
                    after = e['source']
                # 새로 뜬 세션은 앞 세션의 남은 입력을 처리하지 않는다. compact 는 진행 중인 턴이 이어진다
                if e.get('source') != 'compact':
                    waiting = []
                # 세션 번호는 훅이 프로젝트에서 받아 적는다. 적히지 않은 기록(번호를 받지 못한 훅)은 /clear 마다 하나씩 올린다
                number = e.get('session')
                if isinstance(number, int):
                    if number != session:
                        session, count = number, 0
                elif e.get('source') == 'clear':
                    session, count = session + 1, 0
                # 세션이 새로 뜨면 앞 세션에서 기다리던 권한 요청은 끝났다
                permissions.clear()
            elif kind == 'prompt':
                # 시스템 입력과 터미널 명령은 대기로 두지 않는다. 진행 중인 턴에 흡수되거나 응답이 없어 남으면 작업 중이 풀리지 않는다
                prompt = (e.get('prompt') or '').lstrip()
                if not self._system(prompt) and not prompt.startswith(TERMINAL_COMMAND_PREFIX):
                    waiting.append(self._unwrap(prompt))
            elif kind == 'permission':
                permissions[e.get('request_id')] = {
                    'request_id': e.get('request_id'), 'tool_name': e.get('tool_name'),
                    'tool_input': e.get('tool_input'), 'at': e.get('at'), 'seq': seq,
                }
            elif kind == 'permission_done':
                permissions.pop(e.get('request_id'), None)
            elif kind == 'notification':
                # 입력을 기다린다는 알림이면 진행 중인 것이 없다. 남은 입력은 응답이 기록되지 않은 것이라 대기에서 뺀다
                # 훅이 남기지 못한 턴은 이 알림 앞에 기록 파일에서 되살려 둔다. 앞 턴에 붙이면 엉뚱한 턴이 답한 것처럼 보인다
                if e.get('kind') == 'idle_prompt':
                    waiting = []
                    if turns:
                        turns[-1]['open'] = False
                if e.get('kind') not in QUIET_NOTICES:
                    attention = {'message': e.get('message') or '', 'kind': e.get('kind'), 'at': e.get('at'), 'seq': seq}
            elif kind == 'turn':
                if not (e.get('text') or '').strip():
                    continue
                prompts = e.get('prompts')
                # 압축된 턴의 기록에는 요약문만 있어 받은 입력을 읽지 못한다
                if prompts and any(p.lstrip().startswith(COMPACT_SUMMARY_PREFIX) for p in prompts):
                    prompts = None
                known = prompts is not None
                if not known:
                    # 기록 파일에서 읽지 못한 턴은 그때까지 온 입력 전부로 본다
                    prompts, waiting = waiting, []
                else:
                    # 예전 훅은 시스템 입력도 턴 입력으로 남겼다
                    prompts = self._typed([p for p in prompts if not self._system(p)])
                    waiting = self._consume(waiting, prompts)
                # 기록 파일에 사용자 입력이 없는 응답(작업 알림에 대한 응답)은 앞 턴에 붙인다. /clear, compact 뒤면 맥락이 바뀌어 새 턴
                joins = known and not prompts and after is None
                if turns and (turns[-1]['open'] or joins):
                    self._extend(turns[-1], e, prompts)
                else:
                    count += 1
                    turns.append(self._new(session, count, e, prompts, after))
                    after = None
                # 응답이 끝났을 때 대기열에 입력이 남아 있으면 에이전트는 쉬지 않고 이어 간다. 다음 응답을 같은 턴에 붙인다
                turns[-1]['open'] = bool(waiting)
        for t in turns:
            del t['open']
        self._relabel(turns)
        return {
            'turns': turns, 'session_id': session_id, 'session': session,
            # 남은 입력이 있으면 에이전트가 그것을 처리하는 중이다
            'pending': '\n\n'.join(waiting) if waiting else None,
            'permission': list(permissions.values())[-1] if permissions else None,
            'attention': attention,
        }

    def _new(self, session: int, n: int, e: dict, prompts: list[str], after: str | None) -> dict:
        tid = f'{session}S-{n}'
        items = [self._item(item, f'{tid}-{k}') for k, item in enumerate(e.get('items') or [], 1)]
        return {
            'id': tid, 'session': session, 'turn': n, 'prompt': '\n\n'.join(prompts), 'text': e.get('text') or '',
            'preamble': e.get('preamble') or '', 'items': items, 'parts': 1,
            'usage': self._usage(None, e.get('usage')), 'files': list(e.get('files') or []),
            'session_id': e.get('session_id'), 'at': e.get('at'), 'after': after, 'open': False,
        }

    # 이어진 응답을 턴에 붙인다. 사안 ID 는 그 턴 안에서 이어 매긴다
    def _extend(self, turn: dict, e: dict, prompts: list[str]) -> None:
        tid, start = turn['id'], len(turn['items'])
        turn['items'] += [self._item(item, f'{tid}-{start + k}') for k, item in enumerate(e.get('items') or [], 1)]
        turn['prompt'] = '\n\n'.join(p for p in [turn['prompt'], *prompts] if p)
        turn['text'] = f"{turn['text']}\n\n{e.get('text') or ''}"
        turn['preamble'] = '\n\n'.join(p for p in [turn['preamble'], e.get('preamble') or ''] if p)
        turn['usage'] = self._usage(turn['usage'], e.get('usage'))
        turn['files'] += [f for f in e.get('files') or [] if f not in turn['files']]
        turn['parts'] += 1
        turn['session_id'], turn['at'] = e.get('session_id'), e.get('at')

    # 사안에 ID 를 붙인다. 예전 분리기로 `### [D] 제목` 을 종류 D 로 읽은 기록은 보존 표시가 붙은 제안으로 고친다
    def _item(self, item: dict, item_id: str) -> dict:
        if item.get('kind') in ('D', 'W') and not item.get('tag'):
            item = {**item, 'kind': '제안', 'tag': item['kind'], 'known_kind': True}
        return {**item, 'id': item_id}

    # 예전 ID 로 쓴 참조를 새 ID 로 바꾼다. 예전에는 턴 번호가 탭 안에서 이어졌으니 n 은 탭 전체에서 n 번째 턴이다
    # 새 ID 를 본 에이전트는 새 ID 를 옮겨 쓰니, 세션 표시가 없는 참조는 예전 기록에만 나온다
    def _relabel(self, turns: list[dict]) -> None:
        def turn_id(n: str) -> str | None:
            return turns[int(n) - 1]['id'] if 0 < int(n) <= len(turns) else None

        def ref(m: re.Match) -> str:
            tid = turn_id(m.group(1))
            return f'#{tid}-{m.group(2)}' if tid else m.group(0)

        def sub(text: str) -> str:
            return LEGACY_REF.sub(ref, text) if text and '#' in text else text

        for t in turns:
            t['prompt'], t['text'], t['preamble'] = sub(t['prompt']), sub(t['text']), sub(t['preamble'])
            for i in t['items']:
                i['title'], i['body'] = sub(i.get('title') or ''), sub(i.get('body') or '')
                m = LEGACY_ID.match(i.get('parent') or '')
                if m and turn_id(m.group(1)):
                    i['parent'] = f'{turn_id(m.group(1))}-{m.group(2)}'

    # 토큰 사용량을 더한다. 기록이 없는 응답(이전 버전 훅)이 섞이면 아는 것만 더한다
    def _usage(self, total: dict | None, add: dict | None) -> dict | None:
        if not add:
            return total
        if not total:
            return {k: add.get(k, 0) for k in USAGE_KEYS}
        return {k: total.get(k, 0) + add.get(k, 0) for k in USAGE_KEYS}

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

    def _system(self, text: str) -> bool:
        return text.lstrip().startswith(SYSTEM_PROMPT_PREFIXES)

    # 기록 파일에서 읽은 턴 입력을 사용자가 친 글로 줄인다. 붙여넣기 감싸개는 벗기고 명령 출력은 뺀다
    # 명령 줄은 다른 입력이 없을 때만 `/이름 인자` 로 남긴다. 명령이 연 턴(스킬 등)이 앞 턴에 붙지 않게
    def _typed(self, prompts: list[str]) -> list[str]:
        typed, commands = [], []
        for p in prompts:
            text = p.lstrip()
            if text.startswith(COMMAND_OUTPUT_PREFIXES):
                continue
            # 예전 판은 <command-message> 를 먼저 적었다
            command = COMMAND.search(text) if text.startswith(('<command-name>', '<command-message>')) else None
            if command:
                args = COMMAND_ARGS.search(text)
                commands.append(f"{command.group(1).strip()} {args.group(1).strip() if args else ''}".strip())
                continue
            typed.append(self._unwrap(p))
        return typed or commands

    def _unwrap(self, text: str) -> str:
        return PASTED.sub(lambda m: m.group(1), text).strip() if '<pasted_content' in text else text.strip()

    def _key(self, text: str) -> str:
        return ' '.join(text.split())
