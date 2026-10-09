import importlib

# 층 표면. 이름 -> 모듈 경로. 지연 로드. lnt doc 이 생성한다
_EXPORTS = {
    "AgentTab": "agent_tab",
    "CaptureHook": "capture_hook",
    "OverseerMcp": "overseer_mcp",
}
__all__ = list(_EXPORTS)


def __getattr__(name: str):
    if name in _EXPORTS:
        mod = importlib.import_module(f".{_EXPORTS[name]}", __name__)
        return getattr(mod, name)
    raise AttributeError(name)
