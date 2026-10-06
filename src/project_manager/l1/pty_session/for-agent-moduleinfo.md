---
sources:
  pty_session.py: 7c453f72fdd2
---
# pty_session

pywinpty(ConPTY)로 띄운 프로세스 하나. 읽기 스레드가 출력을 받아 듣는 쪽에 넘기고, 다시 그리기용으로 일부를 남긴다.

## PtySession

### Properties
listeners: list[Callable[[str], None]]   # 출력 콜백. 읽기 스레드에서 불린다
on_exit: Callable[[], None] | None       # 프로세스가 끝나면 읽기 스레드에서 한 번
alive: bool                              # 프로세스가 살아 있는지

### __init__
__init__(argv: list[str], cwd: str, env: dict[str, str], rows: int = 40, cols: int = 120)

### Methods

start() -> None
history() -> str
    남겨 둔 출력(최근 약 1MB). 터미널 창이 새로 붙을 때 먼저 보낸다.
write(data: str) -> None
    키 입력 그대로. 꺼졌으면 무시.
paste(text: str) -> None
    bracketed paste(ESC[200~ … ESC[201~)로 감싸 쓴다. 줄바꿈이 제출로 읽히지 않는다. 제출은 따로 CR.
resize(rows: int, cols: int) -> None
terminate() -> None

## 설계 이유

- 콜백은 읽기 스레드에서 불린다. asyncio 쪽은 call_soon_threadsafe 로 넘겨 받아야 한다.
