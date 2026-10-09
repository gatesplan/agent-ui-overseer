---
sources:
  turn_builder.py: 348c7f3e0999
---
# turn_builder

훅 기록(session_start, prompt, turn)을 화면이 쓰는 턴 목록으로 조립한다.

## TurnBuilder

### Methods

build(events: list[dict]) -> dict
    반환: {turns, pending, session_id, session, permission, attention}
    turns: {id, session, turn, prompt, text, preamble, items, parts, session_id, at, after}
      session 은 /clear 구간 번호(1부터), turn 은 세션 안의 턴 번호(1부터), id 는 `<세션>S-<턴>`
      사안 ID 는 `<세션>S-<턴>-<순번>`(순번은 응답에 나온 순서). 예: 2S-3-1
      예전 ID(`#턴-순번`, 턴 번호가 탭 안에서 이어짐)로 쓴 입력, 응답, 사안 본문의 참조와 출처는 새 ID 로 바꿔 낸다
      예전 분리기가 종류 D, W 로 읽은 사안은 종류 제안, tag D, W 로 고쳐 낸다
      prompt: 이 턴이 받은 입력. turn 기록의 prompts(기록 파일에서 읽음)를 쓰고, 없으면 그때까지 온 입력 훅 기록 전부
      parts: 이 턴에 묶인 응답 수
      usage: 이 턴의 토큰 사용량 합(이어 붙인 응답 포함). 기록이 없으면 None
      after: 이 턴 앞에 /clear 나 compact 가 있었으면 'clear' | 'compact'
    pending: 아직 어느 턴에도 들어가지 않은 입력. 에이전트가 처리 중이라는 뜻. 없으면 None
    session_id: 가장 최근 기록의 claude 세션 ID. --resume 에 쓴다
    session: 지금 세션 번호. source=clear 인 session_start 마다 오른다. compact, resume 은 맥락을 이어 가므로 그대로. 화면이 앞 세션의 턴을 접는다
    permission: 화면의 결정을 기다리는 권한 요청 {request_id, tool_name, tool_input, at, seq}. 없으면 None
    attention: 터미널 확인을 기다리는 알림 {message, kind, at, seq}. 대기 알림(QUIET_NOTICES)은 넣지 않고,
      뒤에 입력, 턴, 세션 시작, 권한 결정이 오면 끝난 것으로 본다. seq 는 기록 위치(AgentTab 이 터미널 입력으로 내릴 때 쓴다)

## 턴 경계

- 패널의 턴은 사용자가 한 번에 처리할 묶음이다. 에이전트가 사용자에게 돌려주지 않고 이어 간 응답은 같은 턴이다.
- 입력 훅(prompt 기록)은 대기열에 넣는 순간 불린다. 작업 중에 넣은 입력은 앞 응답의 turn 기록보다 먼저 온다.
  그래서 턴 입력은 turn 기록의 prompts 로 정하고, 입력 훅 기록은 맞춰 지운다(남은 것이 pending).
- 응답이 끝났을 때 남은 입력이 있으면 에이전트는 쉬지 않고 그것을 처리한다. 다음 응답을 같은 턴에 붙이고
  사안 ID 를 이어 매긴다(1S-1-6, 1S-1-7 …). 입력문, 응답, 종합 의견도 이어 붙인다.
- 작업 중 입력이 진행 중인 턴에 흡수되면 그 턴의 prompts 에 들어온다(TranscriptReader 가 queued_command 첨부로 읽음).
  그래도 입력이 남아 있는데 입력 대기 알림(idle_prompt)이 오면, 흡수를 못 읽은 것으로 보고 앞 턴 입력으로 옮긴다.
  남겨 두면 pending 이 풀리지 않아 탭이 계속 작업 중으로 보이고 전송이 막힌다.
- 시스템이 넣은 입력(`<task-notification>` 으로 시작하는 백그라운드 작업 알림)은 사용자 입력이 아니다.
  입력 훅이 불려도 대기로 두지 않고, turn 기록의 prompts 에 있어도(예전 훅) 뺀다. pending 에도 넣지 않는다.
  prompts 가 기록 파일에서 읽혔는데 사용자 입력이 하나도 없는 응답(작업 알림에 대한 응답)은 앞 턴에 붙인다.
  /clear, compact 바로 뒤 응답은 맥락이 바뀌었으니 새 턴으로 연다. prompts 를 못 읽은 응답은 붙이지 않는다.
- 응답이 빈 turn(중단 등)은 턴으로 세지 않는다. 중단된 입력은 다음 응답의 prompts 에 함께 들어온다.
- 사안 ID 는 탭 안에서 겹치지 않는다. /clear 로 세션 번호가 오르고 턴 번호는 1부터 다시 매긴다.
  결정, 보류, 기록 근거는 이 ID 를 그대로 키로 쓴다.
