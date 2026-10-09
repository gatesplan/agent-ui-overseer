# 표준 ln-structure
import 체인에 기반하여 깊이 체인을 만드는 파일, 폴더 규칙

## 목적
AI 생성 코드의 의존성 관리를 선형화하고, 계층의 목적 없이 구조만 남는 확장을 무한하게 할 수 있는 체계를 제공.

## 기본 규칙
1. 항상 폴더 구조 사용
   - 모든 단순 모듈은 `ln/modulename/` 폴더로 구성
   - 모든 중첩 모듈은 `ln/modulename/lm/submoudle_name` 폴더로 구성
   - 객체 기반이다. 모듈이 공개하는 이름은 클래스와 타입 별칭(`Answer = Union[A, B]`)뿐이다.
     함수는 메서드로, 상수는 클래스 속성으로, 진입 함수 `main`은 진입 클래스의 메서드로 둔다.
     이름이나 파일 이름이 `_`로 시작하면 비공개다.
   - `__init__.py`는 패키지 루트까지 모두 `lnt doc`이 만든다. 손으로 고치지 않는다.
   - 파일 하나에 클래스 하나. 파일 이름이 그 세부 책임의 이름이 되어, 모듈 폴더만 봐도 무엇으로 이뤄졌는지 보인다.
   - 모듈 하나에 책임 하나. 여러 책임을 한 모듈에 몰면 그 모듈이 허브가 되어 영향 범위(blast)가 무뎌진다.
   - 모듈 안 파일 사이의 관계는 검사하지 않는다(순환 허용). 그 관계까지 검사가 필요해지면 중첩 모듈로 바꾼다. 중첩 안에서는 C1~C5가 걸린다.

2. l0, l1, ... ln 층 규칙
   - 외부 라이브러리 의존이 없는 모듈 (표준 라이브러리만 허용)의 위치
   - 층(ln)에는 어떠한 의미도, 역할도 부여하지 않는다.
   - 층은 오직 의존성 관계만을 따라 결정한다.

3. 미러 테스트 구조
   - `tests/` 구조는 `src/` 구조와 동일
   - `src/l1/order/` → `tests/l1/order/`

4. 임포트 규칙
   - 항상 낮은 레벨의 모듈만 임포트할 수 있다
   - 낮은 레벨의 표면만 임포트할 수 있고, 중첩 구조 심부로 들어가 임포트해선 안 된다.
     표면에 없는 이름(함수, 상수, 비공개 클래스)을 가져오는 것도, 같은 층에서 공개 이름이 겹치는 것도 표면 위반(C2)이다.
   - `if TYPE_CHECKING:` 안의 임포트도 의존이다. 층 판정에 포함한다.
   - 모듈 간 순환은 금지. 모듈 내부 파일 간 순환은 규칙 밖 (허용).
   - 패키지 안 임포트는 상대 경로로 쓴다(C5). 절대 경로는 패키지가 다른 프로젝트에 중첩 모듈로 들어가면 깨진다.

5. 진입점 규칙
   - 외부 진입점은 마지막 층에 위치하며, 외부에서는 마지막 층의 진입점만 re-export 한다.
   - 진입점(연결 모듈)은 1파일 1클래스, 단일 책임 규칙의 예외. 모든 구현체를 알고 조립하는 것이 역할이다.

6. 층 결정 규칙
   - 모듈의 층 = 의존하는 모듈의 최고 층 + 1. 의존이 없으면 l0.
   - 선언 층(디렉토리)과 계산 층이 다르면 위반. `lnt check`가 판정한다.


## 디렉토리 구조

### 단순 모듈

```
src/fishfactory/
  ln/
    modulename/
      modulename.py
      __init__.py

tests/
  ln/
    modulename/
      test_modulename.py
```

### 중첩 모듈

```
src/fishfactory/
  ln/
    modulename/
      l0/
      l1/
      l2/
      __init__.py

tests/
  ln/
    modulename/
      test_modulename.py
      test_integration.py
```

## __init__.py 패턴

모든 `__init__.py`는 패키지 루트까지 `lnt doc`이 만든다. 손으로 고치지 않는다.
지울 수 없는 정의가 있으면(표면에서 빠질 이름이 아직 코드에 있거나 `__init__` 안에 코드가 있으면) 그 파일은 쓰지 않고 알린다.
쓰는 곳을 고친 뒤에도 알림이 남으면(다른 모듈의 이름을 다시 내보내던 경우) 그 파일을 지우고 다시 `lnt doc`을 돌린다.
모듈을 새로 만들거나 공개 이름을 바꾸면 `lnt doc`을 돌린다. 안 돌리면 훅과 `lnt doc --check`가 알린다.
패키지 안 import는 모두 상대 경로다. 패키지가 다른 프로젝트에 중첩 모듈로 들어가도 그대로 동작하고, `lnt move`도 상대 경로로 고친다.

### 모듈 __init__.py (모듈 표면)

모듈 폴더 바로 아래 파일의 공개 클래스와 타입 별칭을 모두 내보낸다. 이름이나 파일 이름이 `_`로 시작하면 빠진다.

```python
# src/fishfactory/l1/order/__init__.py  (lnt doc 이 씀)
from .order import Order

__all__ = ["Order"]
```

```python
# src/fishfactory/l2/report/report.py
from ...l1.order import Order  # 모듈 표면 import
```

### 중첩 모듈 __init__.py

안쪽 맨 위 층 모듈들의 표면을 그대로 공개한다. 맨 위 층 클래스의 공개 메서드가 곧 진입점이고, 아래 층은 내부다.
지연 로드라 안쪽 모듈을 import해도 맨 위 층까지 끌려오지 않는다.
맨 위 층의 공개 시그니처가 아래 층 타입을 쓰면 바깥에서는 그 타입을 만들 수 없다.
`lnt review`가 '숨은 타입 노출'로 알리니, 그 타입을 맨 위 층으로 올리거나 중첩 모듈 밖으로 뺀다.

```python
# src/fishfactory/l3/portfolio/__init__.py  (lnt doc 이 씀. 안쪽 맨 위 층이 l1 이고 거기에 store 가 있다)
import importlib

# 모듈 표면: 안쪽 맨 위 층. 이름 -> 모듈 경로. 지연 로드. lnt doc 이 생성한다
_EXPORTS = {
    "Store": "l1.store",
}
__all__ = list(_EXPORTS)


def __getattr__(name: str):
    if name in _EXPORTS:
        mod = importlib.import_module(f".{_EXPORTS[name]}", __name__)
        return getattr(mod, name)
    raise AttributeError(name)
```

### 레이어 __init__.py (층 표면)

그 층 모듈들의 표면을 합친 목록이다. PEP 562 모듈 `__getattr__`로 지연 로드하므로 요청한 모듈만 로드된다.
같은 층의 두 모듈이 같은 이름을 내놓으면 목록에서 빠지고 C2 위반이 된다(객체 기반에서는 같은 책임 이름을 두 모듈이 주장하는 설계 오류다).

```python
# src/fishfactory/l1/__init__.py  (lnt doc 이 씀. 위와 같은 지연 로드 형식)
_EXPORTS = {
    "Order": "order",
    "Pair": "pair",
}
```

```python
# src/fishfactory/l2/report/report.py
from ...l1 import Order, Pair  # 레이어 단위 import. order, pair만 로드
```

### 패키지 최상단 __init__.py

중첩 모듈과 같은 규칙이다. 맨 위 층 모듈들의 표면을 지연 로드로 공개한다.
패키지는 다른 프로젝트에 그대로 중첩 모듈로 들어갈 수 있으므로 공개 규칙이 같아야 한다.
지연 로드라 패키지 안 어느 모듈을 import해도 맨 위 층까지 끌려오지 않는다.
`__main__.py`는 `__init__`이 아니라 실행 진입 스크립트라 `lnt doc`이 만들지 않는다. 진입 클래스의 메서드를 부른다.

```python
# src/fishfactory/__init__.py  (lnt doc 이 씀. 맨 위 층이 l3 이고 거기에 portfolio 가 있다. 위와 같은 지연 로드 형식)
_EXPORTS = {
    "Portfolio": "l3.portfolio",
}
```

```python
from fishfactory import Portfolio  # 패키지 밖에서 쓰는 최단 경로 import. 패키지 안은 상대 경로
```

```python
# src/fishfactory/__main__.py  (진입 스크립트. 코드로 둔다)
import sys

from .l3.portfolio import Portfolio

sys.exit(Portfolio.main())
```

## 상위 층 호출이 필요할 때

하위 모듈이 상위 모듈을 호출해야 하는 상황은 세 갈래로 처리한다. 순서대로 검토한다.

### 1. 층을 올린다

A가 B에 의존하면 A를 B보다 위로 옮긴다. 대부분 이걸로 끝난다.
`lnt move A lK`로 이동하고 `lnt check`로 연쇄 이동을 확인한다.

### 2. 1:1 상호 호출이면 한 모듈로 합친다

A와 B가 서로 호출하고, 항상 함께 바뀌고, 각각 하나뿐이면 둘은 동작 단위가 하나다.
같은 모듈 폴더에 두 파일로 둔다. 모듈 내부 순환은 규칙 밖이다.

```
ln/trading_engine/
  engine.py       # class Engine
  strategy.py     # class Momentum
  __init__.py     # Engine만 공개
```

Python 순환 import는 상대 객체를 파라미터로 받는 경우 타입 표기용이므로 `TYPE_CHECKING`으로 끊는다.

```python
# ln/trading_engine/strategy.py
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .engine import Engine

class Momentum:
    def on_tick(self, engine: Engine, price: float) -> None:
        engine.place_order('buy', 1)
```

### 3. 1:N 또는 패키지 외부 코드면 의존성 역전

한쪽이 여러 구현(전략 N개, 플러그인)이거나 패키지 밖 사용자 코드를 호출해야 하면
1, 2로 풀리지 않는다. 이때만 역전을 쓴다.

- 인터페이스(Protocol 또는 ABC)는 소비자와 구현체 양쪽보다 낮은 층에 둔다. 소비자 모듈 안도 된다.
- 구현체는 인터페이스를 **명시 상속**하고 메서드에 `@override`를 붙인다.
  구조적 타이핑만 쓰면 import 간선이 없어 `lnt blast`가 영향 범위를 추적하지 못한다.
- 연결(생성과 주입)은 진입점에서만 한다.
- 모듈 로드 시 스스로 등록하는 방식(import 부수효과)은 금지. 등록 목록이 코드 한 곳에 보여야 한다.

```python
# l0/order_placer/order_placer.py
from typing import Protocol

class OrderPlacer(Protocol):
    def place_order(self, side: str, qty: float) -> None: ...

# l1/strategy/strategy.py
from typing import Protocol
from ...l0.order_placer import OrderPlacer

class Strategy(Protocol):
    def on_tick(self, placer: OrderPlacer, price: float) -> None: ...

# l2/momentum/momentum.py
from typing_extensions import override
from ...l0.order_placer import OrderPlacer
from ...l1.strategy import Strategy

class Momentum(Strategy):
    @override
    def on_tick(self, placer: OrderPlacer, price: float) -> None:
        placer.place_order('buy', 1)

# l2/engine/engine.py
from typing_extensions import override
from ...l0.order_placer import OrderPlacer
from ...l1.strategy import Strategy

class Engine(OrderPlacer):
    def __init__(self, strategy: Strategy):
        self.strategy = strategy

    @override
    def place_order(self, side: str, qty: float) -> None:
        pass

    def run(self) -> None:
        self.strategy.on_tick(self, 100.0)

# l3/app/app.py  (진입점. 연결은 여기서만)
from ...l2.engine import Engine
from ...l2.momentum import Momentum

class App:
    def __init__(self):
        self.engine = Engine(strategy=Momentum())
```

import는 전부 아래로 흐르고, 런타임 호출은 Engine <-> Momentum 양방향이다.
Engine과 Momentum은 같은 l2에 있으면서 서로를 모른다.

## 문서

저장하는 문서는 `for-agent-layerinfo.md` 하나다. 나머지는 그 자리에서 조회하거나 코드를 읽는다.

```
1. for-agent-layerinfo.md
   위치: src/fishfactory/ (중첩 모듈은 그 모듈 폴더에 따로)
   내용: 층별 모듈 목록과 모듈마다 책임 한 줄
   세션 시작 훅이 넣어 준다

2. 시그니처: 문서로 두지 않는다
   lnt sig l1            # 층
   lnt sig l1.order      # 모듈
   lnt sig order         # 모듈 이름

3. 상세: 문서로 두지 않는다. 코드를 읽는다
```

모듈 목록은 `lnt doc`이 마커 사이에 생성한다. 책임 한 줄은 마커 안의 각 줄에 쓰고, 다음 생성 때 보존된다.
새 모듈은 `[설명 필요]`로 들어가고 `lnt doc`과 훅이 알린다. 책임은 사람이 정하는 스펙이고, 처음 채우는 쪽이 에이전트여도 같은 기준으로 쓴다.

- 책임 한 줄에는 그 모듈이 무엇을 맡는지(무엇에 답하는지) 쓴다
- 어떻게 하는지(기능 나열, 알고리즘, 처리 단계, 함수 이름)는 쓰지 않는다. 세부 기능은 코드와 `lnt sig`가 보여 준다
- 책임으로 써 보면 같은 일을 맡은 모듈이 여럿인지 드러난다. 기능 나열로는 보이지 않는다

코드만 보고 알 수 없는 설계 이유와 코드 밖 계약은 마커 밖 Notes에 짧게 쓴다.

```markdown
# for-agent-layerinfo.md

<!-- lnt:generated:start -->
## l0
- candle: 한 구간의 가격 흐름을 값으로 나타낸다
## l1
- order: 주문이 체결되거나 취소되기까지의 상태를 맡는다
<!-- lnt:generated:end -->

## Notes

(자유 기술. 보존됨)
```

## 도구 `lnt`

`ff-lntools` 패키지. 프로젝트 env에 설치되어 있어야 한다.

```
lnt check [--file PATH]     # 층 방향, 표면 import, 층 일치, 모듈 간 순환 검사. 문법 오류 파일도 알린다. 위반 시 exit 1
lnt blast MODULE            # MODULE에 의존하는 상위 모듈 목록 (상속 경유 포함)
lnt sig [TARGET ...]        # 층이나 모듈의 공개 시그니처. 없으면 전체
lnt review                  # 점검 대상: 우회 의존, 아무도 쓰지 않는 모듈, 클래스가 여럿인 파일, 숨은 타입 노출. exit 0
lnt doc [--check]           # layerinfo 와 __init__.py 생성 / 불일치 검사
lnt move MODULE lK          # 층 이동 + import 경로 재작성
```

Claude Code 훅(`.claude/settings.json`)이 편집마다 `check`, `blast`, layerinfo 와 `__init__.py` 검사를 실행해
위반은 해결 방법과 함께 오류로, 영향 범위와 문서·`__init__` 불일치, 문법 오류로 읽지 못한 파일은 정보로 세션에 주입한다.

점검 대상(`lnt review`)은 판정이 아니라 질문이다. 정상인 경우가 많아 훅에는 넣지 않고 필요할 때 목록으로 본다.
- 우회: M이 A를 쓰면서 A 아래의 B도 직접 쓴다. 그 일이 A의 책임이면 A로 옮기고, 다른 용도면 그대로 둔다
  (B가 l0이거나, M이 맨 위 층이거나, A의 공개 시그니처에 B의 이름이 나오면 조립이나 어휘로 보고 빼고 보인다)
- 고아: 아무도 import하지 않는 모듈. 남길지 확인한다. 맨 위 층, 패키지 루트나 중첩 모듈 표면이 내보내는 모듈,
  패키지 밖 코드(app/, scripts/, pyproject의 scripts)가 쓰는 모듈은 빼고 보인다
- 클래스가 여럿인 파일: 1파일 1클래스 점검. 파일을 나눠 세부 책임을 드러낼지 확인한다. 진입점(맨 위 층)은 예외라 빼고 보인다
- 숨은 타입 노출: 중첩 모듈 맨 위 층의 공개 시그니처가 표면에 없는 안쪽 타입을 쓴다. 맨 위 층으로 올리거나 중첩 모듈 밖으로 뺀다

## 전체 예시

```
project/
  src/fishfactory/
    for-agent-layerinfo.md                # 모듈 목록과 책임

    l0/
      candle/
        candle.py
        __init__.py
      token/
        token.py
        __init__.py

    l1/
      order/
        order.py
        __init__.py
      pair/
        pair.py
        __init__.py

    l3/
      portfolio/                          # 중첩 모듈. 안쪽 층에도 모듈 폴더를 둔다
        l0/
          tick_snapshot/
            tick_snapshot.py
            __init__.py
          __init__.py
        l1/
          store/
            store.py
            __init__.py
          __init__.py
        for-agent-layerinfo.md            # portfolio 안의 모듈 목록과 책임
        __init__.py

  tests/
    l0/
      candle/
        test_candle.py
      token/
        test_token.py

    l1/
      order/
        test_order.py
      pair/
        test_pair.py

    l3/
      portfolio/
        test_portfolio.py
        test_integration.py
```

## 파일 배치 규칙

### 소스 코드
- 위치: `src/fishfactory/ln/modulename/`
- 메인 파일: `modulename.py` (또는 중첩 Ln)
- Export: `__init__.py`

### 테스트
- 위치: `tests/ln/modulename/`
- 명명: `test_*.py`
- 구조: 소스 미러

### 문서
- 위치: `src/fishfactory/for-agent-layerinfo.md`. 중첩 모듈은 그 모듈 폴더에 따로 둔다
- 형식: 위 '문서' 절
