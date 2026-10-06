---
sources:
  item_splitter.py: c2a2773617ff
---
# item_splitter

응답 텍스트를 `### [종류] 제목` 단위 사안으로 나눈다. 규약은 `docs/item-protocol.md`.

## ItemSplitter

### Properties
KINDS: tuple[str, ...]    # 규약 종류: 질문, 제안, 보고

### Methods

split(text: str) -> tuple[str, list[Item]]
    (서문, 사안 목록)을 반환한다.
    제목 줄: `##`~`####` 다음 `[종류] 제목`. 코드 펜스 안의 제목은 본문으로 취급한다.
    제목 끝 `(← #1-4)` 또는 `(<- #1-4)`는 parent 로 떼어낸다.
    첫 제목 앞 텍스트는 서문. 제목이 없으면 전체가 서문이고 사안은 빈 목록.
    마지막 사안 뒤 맺음말은 구분하지 못하고 마지막 사안 본문에 붙는다. 규약으로 막는다.
