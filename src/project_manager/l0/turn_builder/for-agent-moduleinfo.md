---
sources:
  turn_builder.py: 6e5df5383565
---
# turn_builder

훅 기록(session_start, prompt, turn)을 화면이 쓰는 턴 목록으로 조립한다.

## TurnBuilder

### Methods

build(events: list[dict]) -> dict
    반환: {turns, pending, session_id}
    turns: 응답 텍스트가 있는 turn 기록마다 하나. {turn, prompt, text, preamble, items, session_id, at, after}
      턴 번호는 1부터, 사안 ID 는 `턴-순번`(사안 순서는 응답에 나온 순서)
      prompt: 앞 턴 뒤로 들어온 입력. 여럿이면 빈 줄로 잇는다
      after: 이 턴 앞에 /clear 나 compact 가 있었으면 'clear' | 'compact'
    pending: 마지막 턴 뒤에 들어온 입력. 에이전트가 처리 중이라는 뜻. 없으면 None
    session_id: 가장 최근 기록의 claude 세션 ID. --resume 에 쓴다

## 설계 이유

- 응답이 빈 turn(중단 등)은 턴으로 세지 않는다. 사안 ID 가 비지 않게 하려는 것.
- 사안 ID 는 탭 안에서 이어진다. /clear 로 claude 세션이 바뀌어도 번호는 이어 간다.
