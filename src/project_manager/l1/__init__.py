import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .archive_query import ArchiveQuery as ArchiveQuery
    from .hook_installer import HookInstaller as HookInstaller
    from .item_splitter import ItemSplitter as ItemSplitter
    from .map_watcher import MapWatcher as MapWatcher
    from .pty_session import PtySession as PtySession

# 층 표면. 이름 -> 모듈 경로. 지연 로드. lnt doc 이 생성한다
_EXPORTS = {
    "ArchiveQuery": "archive_query",
    "HookInstaller": "hook_installer",
    "ItemSplitter": "item_splitter",
    "MapWatcher": "map_watcher",
    "PtySession": "pty_session",
}
__all__ = list(_EXPORTS)


def __getattr__(name: str):
    if name in _EXPORTS:
        mod = importlib.import_module(f".{_EXPORTS[name]}", __name__)
        return getattr(mod, name)
    raise AttributeError(name)
