---
sources:
  item.py: c0b30acd4f60
---
# item

에이전트 응답에서 분리한 사안 하나를 담는 데이터 객체.

## Item

### Properties
kind: str                 # 질문, 제안, 보고. 규약 밖 종류도 그대로 담는다
title: str                # 사안 제목. 출처 표기는 떼어낸 상태
body: str                 # 제목 아래 본문
known_kind: bool          # kind 가 규약 종류인지
parent: str | None        # 파생 출처 사안 ID (예: "1-4")

### Methods

to_dict() -> dict
    JSONL 저장용 dict.
