import re

from project_manager.l0.item import Item


# 응답 텍스트를 `### [종류] 제목` 단위 사안으로 나눈다
class ItemSplitter:
    KINDS = ('질문', '제안', '보고')
    HEADING = re.compile(r'^#{2,4}\s*\[([^\]]+)\]\s*(.+?)\s*$')
    FENCE = re.compile(r'^\s*(```|~~~)')
    PARENT = re.compile(r'\s*\(\s*(?:←|<-)\s*#([\w-]+)\s*\)\s*$')

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
                title, parent = self._title(match.group(2))
                items.append(Item(kind=kind, title=title, body='', known_kind=kind in self.KINDS, parent=parent))
                body = []
            elif items:
                body.append(line)
            else:
                preamble.append(line)

        self._close(items, body)
        return '\n'.join(preamble).strip(), items

    def _title(self, raw: str) -> tuple[str, str | None]:
        match = self.PARENT.search(raw)
        if not match:
            return raw, None
        return raw[:match.start()].strip(), match.group(1)

    def _close(self, items: list[Item], body: list[str]) -> None:
        if items:
            items[-1].body = '\n'.join(body).strip()
