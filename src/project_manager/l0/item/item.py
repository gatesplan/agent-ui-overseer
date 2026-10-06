from dataclasses import asdict, dataclass


# 에이전트 응답에서 분리한 사안 하나
@dataclass
class Item:
    kind: str
    title: str
    body: str
    known_kind: bool = True
    # 파생 출처 사안 ID. 제목 끝 `(← #1-4)` 표기에서 읽는다
    parent: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)
