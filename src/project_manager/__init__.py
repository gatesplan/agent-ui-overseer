import importlib

# 최상위 진입점. 훅 스크립트가 패키지를 불러도 서버 의존성까지 읽지 않게 지연 로드한다
_EXPORTS = {
    'OverseerServer': 'l4.overseer_server',
}
__all__ = list(_EXPORTS)


def __getattr__(name: str):
    if name in _EXPORTS:
        mod = importlib.import_module(f'.{_EXPORTS[name]}', __name__)
        return getattr(mod, name)
    raise AttributeError(name)
