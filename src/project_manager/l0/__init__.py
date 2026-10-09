import importlib

# 층 표면. 이름 -> 모듈 경로. 지연 로드. lnt doc 이 생성한다
_EXPORTS = {
    "CaptureLog": "capture_log",
    "InstallLayout": "install_layout",
    "Item": "item",
    "ModuleMap": "module_map",
    "PanelStore": "panel_store",
    "PermissionGate": "permission_gate",
    "ProjectFinder": "project_finder",
    "ProjectJournal": "project_journal",
    "RecordStore": "record_store",
    "TranscriptReader": "transcript_reader",
    "TurnBuilder": "turn_builder",
}
__all__ = list(_EXPORTS)


def __getattr__(name: str):
    if name in _EXPORTS:
        mod = importlib.import_module(f".{_EXPORTS[name]}", __name__)
        return getattr(mod, name)
    raise AttributeError(name)
