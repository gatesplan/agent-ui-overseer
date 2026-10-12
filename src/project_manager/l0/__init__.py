import importlib

# 층 표면. 이름 -> 모듈 경로. 지연 로드. lnt doc 이 생성한다
_EXPORTS = {
    "CaptureLog": "capture_log",
    "CondaEnvs": "conda_envs",
    "InstallLayout": "install_layout",
    "Item": "item",
    "LaunchEnv": "launch_env",
    "ModuleMap": "module_map",
    "PanelStore": "panel_store",
    "PermissionGate": "permission_gate",
    "ProjectFinder": "project_finder",
    "ProjectJournal": "project_journal",
    "ProjectKey": "project_key",
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
