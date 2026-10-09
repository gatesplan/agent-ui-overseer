import re

from ...l0.item import Item


# 응답 텍스트를 `### [종류] 제목` 단위 사안으로 나눈다
class ItemSplitter:
    KINDS = ('질문', '제안', '보고')
    HEADING = re.compile(r'^#{2,4}\s*\[([^\]]+)\]\s*(.+?)\s*$')
    FENCE = re.compile(r'^\s*(```|~~~)')
    # 출처가 여럿이면 `(← #1S-4-7, #1S-5-6)`. parent 는 첫 출처
    PARENT = re.compile(r'\s*\(\s*(?:←|<-)\s*#([\w-]+)(?:\s*,\s*#[\w-]+)*\s*\)\s*$')
    TAG = re.compile(r'^\[([WD])\]\s*')

    def split(self, text: str) -> tuple[str, list[Item]]:
        preamble: list[str] = []
        items: list[Item] = []
        body: list[str] = []
        in_fence = False

        for line in text.splitlines():
            if self.FENCE.match(line):
                in_fence = not in_fence
            match = None if in_fence else self.HEADING.match(line)
            if match:
                self._close(items, body)
                kind = match.group(1).strip()
                tag, rest = self._tag(match.group(2))
                # 종류 없이 `### [D] 제목` 으로 쓴 보존 사안은 제안으로 본다
                if kind in ('D', 'W') and not tag:
                    kind, tag = '제안', kind
                title, parent = self._title(rest)
                items.append(Item(kind=kind, title=title, body='', known_kind=kind in self.KINDS, parent=parent, tag=tag))
                body = []
            elif items:
                body.append(line)
            else:
                preamble.append(line)

        self._close(items, body)
        return '\n'.join(preamble).strip(), items

    # 종류 라벨 바로 뒤의 보존 표시 `[D]`, `[W]`
    def _tag(self, raw: str) -> tuple[str | None, str]:
        match = self.TAG.match(raw)
        if not match:
            return None, raw
        return match.group(1), raw[match.end():]

    def _title(self, raw: str) -> tuple[str, str | None]:
        match = self.PARENT.search(raw)
        if not match:
            return raw, None
        return raw[:match.start()].strip(), match.group(1)

    def _close(self, items: list[Item], body: list[str]) -> None:
        if items:
            items[-1].body = '\n'.join(body).strip()
