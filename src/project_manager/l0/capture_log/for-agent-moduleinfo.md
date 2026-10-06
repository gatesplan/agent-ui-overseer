---
sources:
  capture_log.py: dbf538390355
---
# capture_log

탭 하나의 훅 기록 `data/captures/<탭 ID>.jsonl` 을 이어서 읽는다. 서버가 주기적으로 poll 한다.

## CaptureLog

### Properties
path: Path                 # 기록 파일
events: list[dict]         # 지금까지 읽은 기록. 형식은 capture_hook 참조

### __init__
__init__(path: str | Path)
    파일이 아직 없어도 된다. 생기면 poll 이 읽는다.

### Methods

poll() -> bool
    마지막으로 읽은 위치 뒤의 새 줄을 events 에 더한다. 더한 게 있으면 True.
    줄바꿈으로 끝나지 않은 마지막 줄은 훅이 쓰는 중일 수 있어 다음 poll 로 미룬다.
    JSON 이 깨진 줄은 건너뛴다.
