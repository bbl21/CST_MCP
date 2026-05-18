"""session.py — session_manager + process_cleanup 工具定义"""
from . import _register_tool_defs


TOOL_DEFS = {
"cleanup-cst-processes": {
    "category": "process_cleanup",
    "risk": "process-control",
    "description": "Force-kill only allowlisted CST processes and report Access is denied residuals with lock-file evidence.",
    "handler": "tool_cleanup_cst_processes",
    "direct_flags": True,
    "args_template": {"project_path": "C:\\path\\to\\tasks\\task_xxx\\runs\\run_001\\projects\\working.cst", "dry_run": False, "settle_seconds": 0.5},
},

"create-blank-project": {
    "category": "session_manager",
    "risk": "write",
    "description": "Create a new blank CST project at the specified path.",
    "handler": "tool_create_blank_project",
    "direct_flags": True,
    "args_template": {"project_path": "C:\\path\\to\\tasks\\task_xxx\\runs\\run_001\\projects\\working.cst"},
},

"cst-session-close": {
    "category": "session_manager",
    "risk": "session",
    "description": "Close the expected CST project, optionally wait for locks to clear, then inspect the environment.",
    "handler": "tool_cst_session_close",
    "direct_flags": True,
    "args_template": {"project_path": "C:\\path\\to\\tasks\\task_xxx\\runs\\run_001\\projects\\working.cst", "save": False, "wait_unlock": True, "timeout_seconds": 30, "poll_interval_seconds": 0.5},
},

"cst-session-inspect": {
    "category": "session_manager",
    "risk": "read",
    "description": "Central session/process gate: inspect processes, locks, open projects, and reattach readiness.",
    "handler": "tool_cst_session_inspect",
    "direct_flags": True,
    "args_template": {"project_path": "C:\\path\\to\\tasks\\task_xxx\\runs\\run_001\\projects\\working.cst"},
},

"cst-session-open": {
    "category": "session_manager",
    "risk": "session",
    "description": "Open a CST project through the central session manager and inspect the environment afterward.",
    "handler": "tool_cst_session_open",
    "direct_flags": True,
    "args_template": {"project_path": "C:\\path\\to\\tasks\\task_xxx\\runs\\run_001\\projects\\working.cst"},
},

"cst-session-quit": {
    "category": "session_manager",
    "risk": "process-control",
    "description": "Quit CST through the central session manager using only the process allowlist and lock evidence.",
    "handler": "tool_cst_session_quit",
    "direct_flags": True,
    "args_template": {"project_path": "C:\\path\\to\\tasks\\task_xxx\\runs\\run_001\\projects\\working.cst", "dry_run": False, "settle_seconds": 0.5},
},

"cst-session-reattach": {
    "category": "session_manager",
    "risk": "read",
    "description": "Reattach to the expected CST project only if it is the sole open project.",
    "handler": "tool_cst_session_reattach",
    "direct_flags": True,
    "args_template": {"project_path": "C:\\path\\to\\tasks\\task_xxx\\runs\\run_001\\projects\\working.cst"},
},

"inspect-cst-environment": {
    "category": "process_cleanup",
    "risk": "read",
    "description": "Inspect allowlisted CST processes, project locks, open projects, and attach readiness.",
    "handler": "tool_inspect_cst_environment",
    "direct_flags": True,
    "args_template": {"project_path": "C:\\path\\to\\tasks\\task_xxx\\runs\\run_001\\projects\\working.cst"},
},

"save-project": {
    "category": "session_manager",
    "risk": "filesystem-write",
    "description": "Save the verified CST working project.",
    "handler": "tool_save_project",
    "direct_flags": True,
    "args_template": {"project_path": "C:\\path\\to\\tasks\\task_xxx\\runs\\run_001\\projects\\working.cst"},
},
}


# --- Handlers ---

from ..core import session as _sm
from ..core import process as _pc
from ..core import project as _po
from ..core.utils import project_path_from_args


def tool_cleanup_cst_processes(args: dict) -> dict:
    return _pc.cleanup_cst_processes(
        project_path=str(args.get("project_path") or ""),
        dry_run=bool(args.get("dry_run", False)),
        settle_seconds=float(args.get("settle_seconds", 0.5)),
    )


def tool_create_blank_project(args: dict) -> dict:
    return _sm.create_blank_project(project_path_from_args(args))


def tool_cst_session_close(args: dict) -> dict:
    return _sm.close_project(
        project_path=project_path_from_args(args),
        save=bool(args.get("save", False)),
        wait_unlock=bool(args.get("wait_unlock", True)),
        timeout_seconds=float(args.get("timeout_seconds", 30.0)),
        poll_interval_seconds=float(args.get("poll_interval_seconds", 0.5)),
    )


def tool_cst_session_inspect(args: dict) -> dict:
    return _sm.inspect(project_path=str(args.get("project_path") or ""))


def tool_cst_session_open(args: dict) -> dict:
    return _sm.open_project(project_path_from_args(args))


def tool_cst_session_quit(args: dict) -> dict:
    return _sm.quit_cst(
        project_path=str(args.get("project_path") or ""),
        dry_run=bool(args.get("dry_run", False)),
        settle_seconds=float(args.get("settle_seconds", 0.5)),
    )


def tool_cst_session_reattach(args: dict) -> dict:
    return _sm.reattach_project(project_path_from_args(args))


def tool_inspect_cst_environment(args: dict) -> dict:
    return _pc.inspect_cst_environment(
        project_path=str(args.get("project_path") or ""),
    )


def tool_save_project(args: dict) -> dict:
    return _po.save_project(project_path_from_args(args))


_register_tool_defs(TOOL_DEFS)
