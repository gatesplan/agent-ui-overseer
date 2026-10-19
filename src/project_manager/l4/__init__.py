import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .overseer_server import OverseerServer as OverseerServer

# 층 표면. 이름 -> 모듈 경로. 지연 로드. lnt doc 이 생성한다
_EXPORTS = {
    "OverseerServer": "overseer_server",
}
__all__ = list(_EXPORTS)


def __getattr__(name: str):
    if name in _EXPORTS:
        mod = importlib.import_module(f".{_EXPORTS[name]}", __name__)
        return getattr(mod, name)
    raise AttributeError(name)
