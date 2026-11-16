import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .capture_log import CaptureLog as CaptureLog
    from .conda_envs import CondaEnvs as CondaEnvs
    from .install_layout import InstallLayout as InstallLayout
    from .item import Item as Item
    from .launch_env import LaunchEnv as LaunchEnv
    from .module_map import ModuleMap as ModuleMap
    from .panel_store import PanelStore as PanelStore
    from .permission_gate import PermissionGate as PermissionGate
    from .plan_usage import PlanUsage as PlanUsage
    from .project_finder import ProjectFinder as ProjectFinder
    from .project_journal import ProjectJournal as ProjectJournal
    from .project_key import ProjectKey as ProjectKey
    from .record_store import RecordStore as RecordStore
    from .transcript_reader import TranscriptReader as TranscriptReader
    from .turn_builder import TurnBuilder as TurnBuilder

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
    "PlanUsage": "plan_usage",
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
