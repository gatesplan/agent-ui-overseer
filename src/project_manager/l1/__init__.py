import importlib

# 공개 이름 -> 모듈 폴더명. lnt doc이 생성한다
_EXPORTS = {
    'ArchiveQuery': 'archive_query',
    'ItemSplitter': 'item_splitter',
    'PtySession': 'pty_session',
}
__all__ = list(_EXPORTS)

def __getattr__(name: str):
    if name in _EXPORTS:
        mod = importlib.import_module(f'.{_EXPORTS[name]}', __name__)
        return getattr(mod, name)
    raise AttributeError(name)
