# 표준 ln-structure
import 체인에 기반하여 깊이 체인을 만드는 파일, 폴더 규칙

## 목적
AI 생성 코드의 의존성 관리를 선형화하고, 계층의 목적 없이 구조만 남는 확장을 무한하게 할 수 있는 체계를 제공.

## 기본 규칙
1. 항상 폴더 구조 사용
   - 모든 단순 모듈은 `ln/modulename/` 폴더로 구성
   - 모든 중첩 모듈은 `ln/modulename/lm/submoudle_name` 폴더로 구성
   - __init__는 모듈이 공개하는 것만을 re-export 한다.

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
   - `if TYPE_CHECKING:` 안의 임포트도 의존이다. 층 판정에 포함한다.
   - 모듈 간 순환은 금지. 모듈 내부 파일 간 순환은 규칙 밖 (허용).

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
      for-agent-moduleinfo.md
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
      for-agent-moduleinfo.md
      __init__.py

tests/
  ln/
    modulename/
      test_modulename.py
      test_integration.py
```

## __init__.py 패턴

**규칙: 항상 상대 임포트 사용**

### 모듈 __init__.py

```python
# src/fishfactory/l1/order/__init__.py

from .order import Order  # 상대 임포트

__all__ = ['Order']
```

**이유:**
- 모듈 이동 시 경로 불변 (l1 -> l2 이동 시 수정 불필요)
- 레벨 변경 자동 반영 (디렉토리 위치 = 계층 상태)
- 다른 프로젝트 복사 시 패키지명 변경 불필요

**효과:**
```python
# 사용자 코드
from fishfactory.l1.order import Order  # 짧은 import
```

### 레이어 __init__.py

각 레이어 폴더(ln/)의 `__init__.py`는 해당 레이어의 모든 모듈을 re-export한다.
단, 즉시 import하지 않고 PEP 562 모듈 `__getattr__`로 지연 로드한다.
층에 모듈이 많아도 요청한 모듈만 로드된다.

```python
# src/fishfactory/l1/__init__.py
import importlib

# 공개 이름 -> 모듈 폴더명. lnt doc이 생성한다
_EXPORTS = {
    'Order': 'order',
    'Pair': 'pair',
}
__all__ = list(_EXPORTS)

def __getattr__(name: str):
    if name in _EXPORTS:
        mod = importlib.import_module(f'.{_EXPORTS[name]}', __name__)
        return getattr(mod, name)
    raise AttributeError(name)
```

**효과:**
```python
from fishfactory.l1 import Order, Pair  # 레이어 단위 import. order, pair만 로드
```

### 패키지 최상단 __init__.py

패키지 루트의 `__init__.py`는 최상위 레이어의 메인 비즈니스 모듈만 노출한다.

```python
# src/fishfactory/__init__.py

from .l3.portfolio import Portfolio  # 최상위 파사드만

__all__ = ['Portfolio']
```

**효과:**
```python
from fishfactory import Portfolio  # 최단 경로 import
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
from shop.l0.order_placer import OrderPlacer

class Strategy(Protocol):
    def on_tick(self, placer: OrderPlacer, price: float) -> None: ...

# l2/momentum/momentum.py
from typing_extensions import override
from shop.l0.order_placer import OrderPlacer
from shop.l1.strategy import Strategy

class Momentum(Strategy):
    @override
    def on_tick(self, placer: OrderPlacer, price: float) -> None:
        placer.place_order('buy', 1)

# l2/engine/engine.py
from typing_extensions import override
from shop.l0.order_placer import OrderPlacer
from shop.l1.strategy import Strategy

class Engine(OrderPlacer):
    def __init__(self, strategy: Strategy):
        self.strategy = strategy

    @override
    def place_order(self, side: str, qty: float) -> None:
        pass

    def run(self) -> None:
        self.strategy.on_tick(self, 100.0)

# l3/app/app.py  (진입점. 연결은 여기서만)
from shop.l2.engine import Engine
from shop.l2.momentum import Momentum

class App:
    def __init__(self):
        self.engine = Engine(strategy=Momentum())
```

import는 전부 아래로 흐르고, 런타임 호출은 Engine <-> Momentum 양방향이다.
Engine과 Momentum은 같은 l2에 있으면서 서로를 모른다.

## 3단계 해상도 문서 구조

```
1. for-agent-layerinfo.md (저해상도)
   위치: src/fishfactory/
   내용: 전체 시스템 모듈 목록

2. for-agent-layerinfo-ln.md (중해상도)
   위치: src/fishfactory/ln/
   내용: 레벨별 모든 모듈 공개 메서드 시그니처

3. for-agent-moduleinfo.md (고해상도)
   위치: src/fishfactory/ln/modulename/
   내용: 모듈 상세 설명, 예외, 설계 이유
```

1, 2는 `lnt doc`이 생성한다. 마커 사이는 생성 영역이며 손으로 고치지 않는다.
마커 밖은 Notes 영역으로 보존된다. 3은 사람이 쓰고 `sources` 헤더의 hash로 stale 여부만 도구가 판정한다.

## 도구 `lnt`

`ff-lntools` 패키지. 프로젝트 env에 설치되어 있어야 한다.

```
lnt check [--file PATH]     # 층 방향, 표면 import, 층 일치, 모듈 간 순환 검사. 위반 시 exit 1
lnt blast MODULE            # MODULE에 의존하는 상위 모듈 목록 (상속 경유 포함)
lnt doc [--check]           # layerinfo, layerinfo-ln 생성 / 불일치 검사
lnt doc --stamp MODULE      # moduleinfo의 sources hash 갱신
lnt move MODULE lK          # 층 이동 + import 경로 재작성
```

Claude Code 훅(`.claude/settings.json`)이 편집마다 `check`, `blast`, `doc --check`를 실행해
위반은 오류로, 영향 범위와 stale 문서는 정보로 세션에 주입한다.

## 전체 예시

```
project/
  src/fishfactory/
    for-agent-layerinfo.md                # 저해상도 (전체)

    l0/
      for-agent-layerinfo-l0.md           # 중해상도 (l0)
      candle/
        candle.py
        for-agent-moduleinfo.md           # 고해상도 (candle)
        __init__.py
      token/
        token.py
        for-agent-moduleinfo.md           # 고해상도 (token)
        __init__.py

    l1/
      for-agent-layerinfo-l1.md           # 중해상도 (l1)
      order/
        order.py
        for-agent-moduleinfo.md           # 고해상도 (order)
        __init__.py
      pair/
        pair.py
        for-agent-moduleinfo.md           # 고해상도 (pair)
        __init__.py

    l3/
      for-agent-layerinfo-l3.md           # 중해상도 (l3)
      portfolio/
        l0/
          tick_snapshot.py
          __init__.py
        l1/
          file_backend.py
          __init__.py
        l2/
          storage_l1.py
          __init__.py
        l3/
          portfolio.py
          __init__.py
        for-agent-moduleinfo.md           # 고해상도 (portfolio)
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

## 파일 배치 규칙

### 소스 코드
- 위치: `src/fishfactory/ln/modulename/`
- 메인 파일: `modulename.py` (또는 중첩 Ln)
- 문서: `for-agent-moduleinfo.md`
- Export: `__init__.py`

### 테스트
- 위치: `tests/ln/modulename/`
- 명명: `test_*.py`
- 구조: 소스 미러

### 문서

#### 저해상도 (전체 시스템)
- 위치: `src/fishfactory/for-agent-layerinfo.md`
- 템플릿: `for-agent-layerinfo-template.md` 참조

#### 중해상도 (레벨별 API)
- 위치: `src/fishfactory/ln/for-agent-layerinfo-ln.md`
- 템플릿: `for-agent-layerinfo-ln-template.md` 참조

#### 고해상도 (모듈별 상세)
- 위치: `src/fishfactory/ln/modulename/for-agent-moduleinfo.md`
- 템플릿: `for-agent-moduleinfo-template.md` 참조
