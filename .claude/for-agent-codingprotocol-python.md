# Python Coding Protocol

Python 코딩 스타일 및 품질 규칙.

## 기본 규칙

1. **1파일 1클래스**
   - 하나의 파일은 하나의 클래스만 포함
   - 파일명과 클래스명은 CamelCase

2. **단일 책임 원칙**
   - 각 클래스는 하나의 책임만

3. **문서화**
   - 코드 내: 한줄 주석(`#`)만 사용
   - Docstring, 멀티라인 주석 사용 금지
   - 상세 설명: `for-agent-moduleinfo.md`에 작성

## 코드 예시

```python
# 주문 처리 서비스
class OrderService:
    def __init__(self, db_url: str):
        self.db_url = db_url

    def create_order(self, user_id: int):
        # 검증
        if not user_id:
            raise ValueError("Invalid user_id")

        # 주문 생성
        return {"order_id": 123}
```

## import 순서

표준 라이브러리, 서드파티, 자기 패키지(절대 경로), 모듈 내부(상대) 순. 그룹 사이 빈 줄.
함수 안에서 하는 지연 import 는 순환을 피하는 목적 외에는 쓰지 않는다.

```python
import json
from pathlib import Path

import requests

from shop.l0.candle import Candle
from shop.l1.order import Order

from .helper import Helper
```

## 인터페이스 구현

인터페이스(Protocol/ABC)를 구현하는 클래스는 명시 상속하고 구현 메서드에 `@override`를 붙인다.
Python 3.12+는 `typing.override`, 3.10/3.11은 `typing_extensions.override`.

```python
from typing_extensions import override
from pkg.l0.notifier import Notifier

class EmailNotifier(Notifier):
    @override
    def send(self, to: str, message: str) -> None:
        pass
```

순환 import가 타입 표기 때문에만 생기면 `TYPE_CHECKING` 블록으로 끊는다.

```python
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .engine import Engine
```

## 로깅

`loguru` 사용.

```python
from loguru import logger

class OrderService:
    def __init__(self, db_url: str):
        logger.info(f"OrderService 초기화: db_url={db_url}")
        self.db_url = db_url

    def create_order(self, user_id: int):
        logger.info(f"create_order 시작: user_id={user_id}")
        # 중요 단계는 DEBUG
        logger.debug(f"DB 연결 확인")
        return {"order_id": 123}
```
