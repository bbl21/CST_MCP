from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Any

from .errors import error_response
from .project_identity import find_lock_files

CST_FORCE_KILL_PROCESS_ALLOWLIST = [
    "cstd",
    "CST DESIGN ENVIRONMENT_AMD64",
    "CSTDCMainController_AMD64",
    "CSTDCSolverServer_AMD64",
]


def _run_powershell(command: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            command,
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )


def _loads_json_array(text: str) -> list[dict[str, Any]]:
    stripped = text.strip()
    if not stripped:
        return []
    value = json.loads(stripped)
    if isinstance(value, dict):
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    return []


def _discover_cst_processes() -> list[dict[str, Any]]:
    names = ",".join(json.dumps(name) for name in CST_FORCE_KILL_PROCESS_ALLOWLIST)
    command = f"""
$allow = @({names})
$items = @()
foreach ($name in $allow) {{
  $items += Get-Process -Name $name -ErrorAction SilentlyContinue |
    ForEach-Object {{
      [pscustomobject]@{{
        pid = $_.Id
        name = $_.ProcessName
        main_window_title = $_.MainWindowTitle
      }}
    }}
}}
$items | Sort-Object pid -Unique | ConvertTo-Json -Depth 4
"""
    result = _run_powershell(command)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "Get-Process failed")
    return _loads_json_array(result.stdout)


def _stop_process(pid: int, name: str) -> dict[str, Any]:
    command = f"""
try {{
  Stop-Process -Id {int(pid)} -Force -ErrorAction Stop
  [pscustomobject]@{{ status = "killed"; pid = {int(pid)}; name = {json.dumps(name)} }} | ConvertTo-Json -Depth 4
}} catch {{
  [pscustomobject]@{{
    status = "failed"
    pid = {int(pid)}
    name = {json.dumps(name)}
    error = $_.Exception.Message
  }} | ConvertTo-Json -Depth 4
}}
"""
    result = _run_powershell(command)
    if result.returncode != 0:
        return {
            "status": "failed",
            "pid": pid,
            "name": name,
            "error": result.stderr.strip() or result.stdout.strip() or "Stop-Process failed",
        }
    payload = json.loads(result.stdout.strip())
    if isinstance(payload, dict):
        return payload
    return {"status": "failed", "pid": pid, "name": name, "error": "unexpected Stop-Process output"}


def _is_access_denied(message: str) -> bool:
    lowered = message.lower()
    return "access is denied" in lowered or "拒绝访问" in lowered or "存取被拒" in lowered


def cleanup_cst_processes(
    project_path: str = "",
    dry_run: bool = False,
    settle_seconds: float = 0.5,
) -> dict[str, Any]:
    try:
        before = _discover_cst_processes()
        lock_files_before: list[Path] = find_lock_files(project_path) if project_path else []

        attempts: list[dict[str, Any]] = []
        if not dry_run:
            for proc in before:
                attempts.append(_stop_process(int(proc["pid"]), str(proc["name"])))
            time.sleep(max(0.0, float(settle_seconds)))

        after = _discover_cst_processes()
        lock_files_after: list[Path] = find_lock_files(project_path) if project_path else []
        access_denied = [
            item
            for item in attempts
            if item.get("status") == "failed" and _is_access_denied(str(item.get("error", "")))
        ]
        other_failures = [
            item
            for item in attempts
            if item.get("status") == "failed" and item not in access_denied
        ]

        cleanup_status = "dry_run" if dry_run else "completed"
        message = "CST process cleanup completed"
        if dry_run:
            message = "CST process cleanup dry run completed"
        elif after and access_denied and not other_failures and project_path and not lock_files_after:
            cleanup_status = "nonblocking_access_denied_residual"
            message = (
                "Allowlisted CST processes remain because Stop-Process returned Access is denied; "
                "project lock files are clear, so this is a recorded non-blocking residual."
            )
        elif after or other_failures or lock_files_after:
            return error_response(
                "cleanup_cst_processes_blocked",
                "CST process cleanup did not finish cleanly",
                cleanup_status="blocked",
                force_kill_allowlist=CST_FORCE_KILL_PROCESS_ALLOWLIST,
                project_path=str(project_path or ""),
                lock_files_before=[path.as_posix() for path in lock_files_before],
                lock_files_after=[path.as_posix() for path in lock_files_after],
                processes_before=before,
                attempts=attempts,
                processes_after=after,
                access_denied=access_denied,
                other_failures=other_failures,
                runtime_module="cst_runtime.process_cleanup",
            )

        return {
            "status": "success",
            "cleanup_status": cleanup_status,
            "message": message,
            "force_kill_allowlist": CST_FORCE_KILL_PROCESS_ALLOWLIST,
            "project_path": str(project_path or ""),
            "lock_files_before": [path.as_posix() for path in lock_files_before],
            "lock_files_after": [path.as_posix() for path in lock_files_after],
            "processes_before": before,
            "attempts": attempts,
            "processes_after": after,
            "access_denied": access_denied,
            "runtime_module": "cst_runtime.process_cleanup",
        }
    except Exception as exc:
        return error_response(
            "cleanup_cst_processes_failed",
            f"cleanup_cst_processes failed: {str(exc)}",
            force_kill_allowlist=CST_FORCE_KILL_PROCESS_ALLOWLIST,
            project_path=str(project_path or ""),
            runtime_module="cst_runtime.process_cleanup",
        )
