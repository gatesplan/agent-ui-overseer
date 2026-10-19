# ln-structure: Python

공통 규칙은 `for-agent-codingprotocol-ln-structure.md` 에 있다. 이 문서는 Python 에서 그 규칙을 어떻게 쓰는지 정한다.

## 공개 이름

- 모듈이 공개하는 이름은 클래스와 타입 별칭(`Answer = Union[A, B]`, `Maybe = A | None`, `type X = ...`)뿐이다
- 함수는 메서드로(`@staticmethod`, `@classmethod`), 상수는 클래스 속성으로 둔다
- 공개 이름을 타입으로 한정하는 까닭: 표면이 한 가지 꼴이 되어 생성과 검사가 단순해지고, 함수가 어느 타입의 일인지 이름에 드러난다.
  모듈 안에서만 쓰는 함수는 자유 함수로 두어도 된다
- 이름이나 파일 이름이 `_`로 시작하면 비공개다
- 꺼내 주기(맨 위 층 모듈이 아래 층 클래스를 다시 내보내기)는 새로 쓰지 않는다. 숨은 타입은 공통 문서 '표면' 절의 방법으로 푼다.
  이미 쓴 `Env: TypeAlias = _Env` 꼴은 lnt 가 계속 공개 이름으로 센다. 이 줄을 `type` 문으로 바꾸면 생성, 정적 메서드, isinstance 가 깨지므로 바꾸지 않는다

## 디렉토리 구조

`tests/` 는 이 문서가 쓰는 예시다. 테스트 위치는 ln 규칙이 아니다.

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

## 표면 파일 = `__init__.py`

모든 `__init__.py`는 패키지 루트까지 `lnt doc`이 만든다. 손으로 고치지 않는다.
패키지 안 import는 모두 상대 경로다. 패키지가 다른 프로젝트에 중첩 모듈로 들어가도 그대로 동작하고, `lnt move`도 상대 경로로 고친다.

### 모듈 __init__.py (모듈 표면)

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

안쪽 맨 위 층 모듈들의 표면을 지연 로드로 공개한다. 안쪽 모듈을 import해도 맨 위 층까지 끌려오지 않는다.
`if TYPE_CHECKING:` 안의 재노출은 타입 검사기용이다. `__getattr__` 로만 내보낸 이름은 mypy 와 pyright 가 Any 로 본다.
실행 중에는 이 블록을 읽지 않으므로 지연 로드는 그대로다.

```python
# src/fishfactory/l3/portfolio/__init__.py  (lnt doc 이 씀. 안쪽 맨 위 층이 l1 이고 거기에 store 가 있다)
import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .l1.store import Store as Store

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

PEP 562 모듈 `__getattr__`로 지연 로드하므로 요청한 모듈만 로드된다.

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

중첩 모듈과 같은 지연 로드 형식으로 맨 위 층 모듈들의 표면을 공개한다.
`__main__.py`는 `__init__`이 아니라 실행 진입 스크립트라 `lnt doc`이 만들지 않는다. 진입 클래스의 메서드를 부른다.

```python
# src/fishfactory/__init__.py  (lnt doc 이 씀. 맨 위 층이 l3 이고 거기에 portfolio 가 있다)
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

## import

- 패키지 안은 상대 경로: `src/pkg/l2/report/report.py` 에서 `from ...l1.order import Order`
- `if TYPE_CHECKING:` 안의 import 도 의존이다. 층 판정에 포함한다
- 표준 라이브러리 밖 패키지를 import 하면 그 모듈은 l1 이상이다

## 상위 층 호출 예시

### 1:1 상호 호출을 한 모듈로 합칠 때

순환 import는 상대 객체를 파라미터로 받는 경우 타입 표기용이므로 `TYPE_CHECKING`으로 끊는다.

```
ln/trading_engine/
  engine.py       # class Engine
  strategy.py     # class Momentum
  __init__.py     # Engine만 공개
```

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

### 의존성 역전

인터페이스는 Protocol 또는 ABC. 구현체는 인터페이스를 **명시 상속**하고 메서드에 `@override`를 붙인다.

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
- 표면: `__init__.py`
- 모듈 폴더 밖에 둘 수 있는 소스: 표면 파일(`__init__.py`)과, 패키지 루트나 중첩 모듈 폴더 바로 아래의 `__main__.py`. 그 밖은 C7

### 테스트
테스트 위치는 ln 규칙이 아니다. 이 문서의 예시는 `tests/` 아래 소스 미러(`tests/ln/modulename/test_*.py`)다.

### 고아 판정에서 패키지 밖 쓰임으로 보는 것
- 패키지 밖 파이썬 파일(app/, scripts/ 등. tests 제외)의 import
- pyproject 의 `[project.scripts]`
