# for-agent-layerinfo-ln.md 템플릿

레벨별 중해상도 API 문서. 해당 레벨의 모든 모듈 공개 메서드 시그니처 나열.

## 위치

```
src/fishfactory/
  ln/
    for-agent-layerinfo-ln.md
```

예시:
- `l0/for-agent-layerinfo-l0.md`
- `l1/for-agent-layerinfo-l1.md`
- `l2/for-agent-layerinfo-l2.md`

## 형식

```markdown
# ln

<!-- lnt:generated:start -->
## modulename
ClassName.__init__(args) -> None  # modulename.py
ClassName.method_name(args) -> return_type  # modulename.py
ClassName.another_method(args) -> return_type  # modulename.py

## another_module
ClassName.__init__(args) -> None  # another_module.py
ClassName.method_name(args) -> return_type  # another_module.py
<!-- lnt:generated:end -->

## Notes

(자유 기술. 보존됨)
```

**규칙:**
- 마커 사이는 `lnt doc`이 각 모듈 `__all__`의 클래스에서 ast로 생성. 손으로 고치지 않는다
- 시그니처만 작성 (설명 없음)
- 한 줄에 하나씩
- `ClassName.method_name()` 형식
- 줄 끝 `# 파일` 은 정의가 있는 파일 (모듈 디렉토리 기준). 중첩 모듈은 `l1/store/store.py` 처럼 경로
- 함수명이 자기설명적이어야 함
- `lnt doc --check`가 생성 결과와 파일을 비교해 다르면 exit 1

## 예시: for-agent-layerinfo-l1.md

```markdown
# l1

## order
Order.__init__(symbol: str, side: str, price: float, quantity: float)  # order.py
Order.fill(quantity: float) -> Trade  # order.py
Order.cancel() -> None  # order.py
Order.get_unfilled() -> float  # order.py
Order.is_filled() -> bool  # order.py

## pair
Pair.__init__(token: Token, value: float)  # pair.py
Pair.merge(other: Pair) -> Pair  # pair.py
Pair.split(ratio: float) -> tuple[Pair, Pair]  # pair.py
Pair.get_average_price() -> float  # pair.py

## market
Market.__init__(candles: list[Candle])  # market.py
Market.get_at(timestamp: int) -> Candle  # market.py
Market.get_range(start: int, end: int) -> list[Candle]  # market.py
Market.to_dataframe() -> DataFrame  # market.py

## order_book
OrderBook.__init__(symbol: str)  # order_book.py
OrderBook.add_bid(price: float, quantity: float) -> None  # order_book.py
OrderBook.add_ask(price: float, quantity: float) -> None  # order_book.py
OrderBook.get_best_bid() -> float | None  # order_book.py
OrderBook.get_best_ask() -> float | None  # order_book.py
OrderBook.match_order(side: str, quantity: float) -> list[tuple[float, float]]  # order_book.py
```

## 3단계 해상도 구조

```
1. for-agent-layerinfo.md (저해상도)
   위치: src/fishfactory/
   내용: l1: order, pair, market, order_book

2. for-agent-layerinfo-l1.md (중해상도)
   위치: src/fishfactory/l1/
   내용: Order.fill(quantity: float) -> Trade

3. for-agent-moduleinfo.md (고해상도)
   위치: src/fishfactory/l1/order/
   내용: fill() 상세 설명, 예외, 설계 이유, 동작 방식
```

## 에이전트 활용

```
사용자: "주문 취소 함수 어디있어?"

에이전트:
1. for-agent-layerinfo.md 읽기
   → l1에 order 모듈 있음
2. l1/for-agent-layerinfo-l1.md 읽기
   → Order.cancel() -> None 발견
3. 필요시 l1/order/for-agent-moduleinfo.md 읽기
   → 상세 정보
```
