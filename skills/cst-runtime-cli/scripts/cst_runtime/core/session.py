from __future__ import annotations

from pathlib import Path
from typing import Any

from . import process as process_cleanup
from . import identity as project_identity
from .errors import error_response
from .utils import abs_project_path as _abs_project_path

_OPENED_PROJECTS: dict[str, Any] = {}


def get_attached_project(project_path: str) -> dict[str, Any] | None:
    normalized = _abs_project_path(project_path)
    return _OPENED_PROJECTS.get(normalized)


def _connect_new_design_environment():
    import cst.interface
    return cst.interface.DesignEnvironment()


def inspect(project_path: str = "") -> dict[str, Any]:
    return process_cleanup.inspect_cst_environment(project_path=project_path)


def create_blank_project(project_path: str) -> dict[str, Any]:
    normalized_project = _abs_project_path(project_path)
    if Path(normalized_project).is_file():
        return error_response(
            "project_already_exists",
            "project_path already exists; choose a different path or delete it first",
            project_path=normalized_project,
            runtime_module="cst_runtime.core.session",
        )
    project_dir = Path(normalized_project).parent
    project_dir.mkdir(parents=True, exist_ok=True)
    try:
        import cst.interface
        de = cst.interface.DesignEnvironment.new()
        project = de.new_mws()
        project.save(normalized_project)
        return {
            "status": "success",
            "project_path": normalized_project,
            "session_action": "create",
            "runtime_module": "cst_runtime.core.session",
        }
    except Exception as exc:
        return error_response(
            "create_blank_project_failed",
            str(exc),
            project_path=normalized_project,
            runtime_module="cst_runtime.core.session",
        )


def open_project(project_path: str) -> dict[str, Any]:
    normalized_project = _abs_project_path(project_path)
    if not Path(normalized_project).is_file():
        return error_response(
            "project_file_missing",
            "project_path does not exist",
            project_path=normalized_project,
            runtime_module="cst_runtime.core.session",
        )

    project, _ = project_identity.attach_expected_project(normalized_project)
    if project is not None:
        _OPENED_PROJECTS[normalized_project] = project
        result = {
            "status": "success",
            "project_path": normalized_project,
            "already_open": True,
            "session_action": "open",
            "post_inspect": inspect(project_path),
            "runtime_module": "cst_runtime.core.session",
        }
        return result

    try:
        de = _connect_new_design_environment()
        project = de.open_project(normalized_project)
        _OPENED_PROJECTS[normalized_project] = project
        return {
            "status": "success",
            "project_path": normalized_project,
            "already_open": False,
            "session_action": "open",
            "post_inspect": inspect(project_path),
            "runtime_module": "cst_runtime.core.session",
        }
    except Exception as exc:
        return error_response(
            "open_project_failed",
            str(exc),
            project_path=normalized_project,
            runtime_module="cst_runtime.core.session",
        )


def reattach_project(project_path: str) -> dict[str, Any]:
    status = project_identity.verify_project_identity(project_path)
    if status.get("status") == "error":
        return {
            **status,
            "session_action": "reattach",
            "post_inspect": inspect(project_path),
            "runtime_module": "cst_runtime.core.session",
        }
    return {
        **status,
        "session_action": "reattach",
        "post_inspect": inspect(project_path),
        "runtime_module": "cst_runtime.core.session",
    }


def close_project(
    project_path: str,
    save: bool = False,
    wait_unlock: bool = True,
    timeout_seconds: float = 30.0,
    poll_interval_seconds: float = 0.5,
    kill_processes: bool = True,
) -> dict[str, Any]:
    normalized_project = _abs_project_path(project_path)
    project, a_status = project_identity.attach_expected_project(normalized_project)
    de_pid: int | None = a_status.get("design_environment_pid")
    _OPENED_PROJECTS.pop(normalized_project, None)
    close_result: dict[str, Any] = a_status if project is None else {"status": "success"}
    if project is not None:
        try:
            if save:
                project.save()
            project.close()
            close_result = {
                "status": "success",
                "project_path": normalized_project,
                "saved": save,
            }
        except Exception as exc:
            close_result = error_response(
                "close_project_failed",
                str(exc),
                project_path=normalized_project,
                runtime_module="cst_runtime.core.session",
            )

    unlock_result: dict[str, Any] | None = None
    if close_result.get("status") != "error" and wait_unlock:
        unlock_result = project_identity.wait_project_unlocked(
            project_path=project_path,
            timeout_seconds=timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
        )

    kill_result: dict[str, Any] | None = None
    if close_result.get("status") != "error" and kill_processes and de_pid:
        kill_result = process_cleanup.stop_process(de_pid, "CST DESIGN ENVIRONMENT_AMD64")
    else:
        kill_result = None

    orphan_result: dict[str, Any] | None = None
    if kill_processes:
        orphan_result = process_cleanup.cleanup_orphan_processes(settle_seconds=0.5)

    status = "success"
    if close_result.get("status") == "error" or (unlock_result or {}).get("status") == "error":
        status = "error"
    payload: dict[str, Any] = {
        "status": status,
        "session_action": "close",
        "project_path": project_path,
        "save": save,
        "close_result": close_result,
        "unlock_result": unlock_result,
        "kill_result": kill_result,
        "orphan_result": orphan_result,
        "post_inspect": inspect(project_path),
        "runtime_module": "cst_runtime.core.session",
    }
    if status == "error":
        payload["error_type"] = "session_close_failed"
        payload["message"] = "close_project or lock-release verification failed"
    return payload


def quit_cst(
    project_path: str = "",
    dry_run: bool = False,
    settle_seconds: float = 0.5,
) -> dict[str, Any]:
    before = inspect(project_path)
    cleanup = process_cleanup.cleanup_cst_processes(
        project_path=project_path,
        dry_run=dry_run,
        settle_seconds=settle_seconds,
    )
    after = inspect(project_path)
    status = "success" if cleanup.get("status") != "error" else "error"
    payload: dict[str, Any] = {
        "status": status,
        "session_action": "quit",
        "project_path": project_path,
        "dry_run": dry_run,
        "pre_inspect": before,
        "cleanup_result": cleanup,
        "post_inspect": after,
        "runtime_module": "cst_runtime.core.session",
    }
    if status == "error":
        payload["error_type"] = "session_quit_failed"
        payload["message"] = "cleanup_cst_processes did not finish cleanly"
    return payload
