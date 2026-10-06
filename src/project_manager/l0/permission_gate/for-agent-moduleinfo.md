---
sources:
  permission_gate.py: 4f854a289a17
---
# permission_gate

권한 요청 훅(PermissionRequest)과 패널 화면 사이의 결정 전달. claude 가 권한 확인 창을 띄우기 직전에 훅이 불리면,
훅은 요청을 기록하고 화면의 결정을 결정 파일(`data/permissions/<요청 ID>.json`)로 기다린다. 서버는 화면의 결정을 그 파일로 쓴다.

## PermissionGate

### __init__
__init__(decisions_dir: str | Path, port: int | None, timeout: float = 1500, interval: float = 0.3)
    port: 패널 서버 포트(자식 세션 환경변수 OVERSEER_PORT). 서버 쪽에서 decide 만 쓸 때는 None.
    timeout: 훅이 기다리는 시간. 훅 등록 timeout(scripts/setup.py, 1800초)보다 짧아야 한다.

### Methods

new_id() -> str
ready() -> bool
    서버의 /api/health 가 permissions 를 알리면 True. 서버가 없거나 예전 버전이면 False 이고 훅은 기다리지 않는다.
wait(request_id: str) -> dict | None
    결정 파일이 생기면 읽고 지운 뒤 {behavior, message}. 시간이 지나면 None.
decide(request_id: str, behavior: str, message: str = '') -> None
    raise ValueError    # 요청 ID 형식(32자리 16진수)이 아니거나 behavior 가 allow | deny | terminal 이 아닐 때
    임시 파일에 쓰고 이름을 바꿔, 훅이 반쯤 쓰인 파일을 읽지 않게 한다.
hook_output(decision: dict | None) -> str
    allow, deny 면 훅 stdout JSON(hookSpecificOutput.decision). terminal 이나 None 이면 빈 문자열 → claude 가 원래 확인 창을 띄운다.

## 설계 이유

- 결정 전달을 파일로 한다. 훅은 짧게 사는 별도 프로세스라 서버와 연결을 유지하지 않고, 서버가 다시 켜져도 결정 파일은 남는다.
- 서버가 결정을 받을 수 없으면 기다리지 않는다. 패널 없이 띄운 세션이나 예전 서버에서 세션이 멈추지 않게 하려는 것.
