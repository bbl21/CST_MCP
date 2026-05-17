from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from .errors import error_response


_COMMON_CST_PATHS = [
    r"C:\Program Files\CST Studio Suite 2026\AMD64\python_cst_libraries",
    r"C:\Program Files\CST Studio Suite 2025\AMD64\python_cst_libraries",
    r"C:\Program Files (x86)\CST Studio Suite 2026\AMD64\python_cst_libraries",
]


def _probe_path(path_str: str) -> dict[str, Any]:
    p = Path(path_str).expanduser().resolve()
    result: dict[str, Any] = {
        "path": str(p),
        "exists": p.is_dir(),
        "has_interface": False,
        "has_results": False,
        "files_accessible": False,
    }
    if p.is_dir():
        cst_pkg = p / "cst"
        result["has_interface"] = (cst_pkg / "interface").is_dir() if cst_pkg.is_dir() else False
        result["has_results"] = (cst_pkg / "results.py").is_file() if cst_pkg.is_dir() else False
        try:
            next(p.iterdir())
            result["files_accessible"] = True
        except PermissionError:
            pass
    return result


def _scan_registry() -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\CST AG\CST Studio Suite")
        i = 0
        while True:
            try:
                version = winreg.EnumKey(key, i)
                vk = winreg.OpenKey(key, version)
                try:
                    install_dir, _ = winreg.QueryValueEx(vk, "Installation Directory")
                    py_lib = Path(install_dir) / "AMD64" / "python_cst_libraries"
                    if py_lib.is_dir():
                        info = _probe_path(str(py_lib))
                        info["source"] = f"registry:CST Studio Suite {version}"
                        found.append(info)
                except FileNotFoundError:
                    pass
                winreg.CloseKey(vk)
                i += 1
            except OSError:
                break
        winreg.CloseKey(key)
    except (FileNotFoundError, ImportError):
        pass
    return found


def scan_cst_installations() -> dict[str, Any]:
    found: list[dict[str, Any]] = []

    for raw_path in _COMMON_CST_PATHS:
        info = _probe_path(raw_path)
        info["source"] = "common_path"
        if info["exists"]:
            found.append(info)

    found.extend(_scan_registry())

    active_path = _read_active_cst_path()
    return {
        "status": "success",
        "found_count": len(found),
        "installations": found,
        "active_path": active_path,
        "active_valid": bool(active_path and Path(active_path).is_dir()),
    }


def _read_active_cst_path() -> str | None:
    try:
        pyproject = Path.cwd().resolve() / "pyproject.toml"
        if not pyproject.exists():
            pyproject = Path(__file__).resolve().parents[3] / "pyproject.toml"
        if not pyproject.exists():
            return None
        import tomllib
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        source = data.get("tool", {}).get("uv", {}).get("sources", {}).get("cst-studio-suite-link", {})
        if isinstance(source, dict):
            return source.get("path")
    except Exception:
        pass
    return None


def _write_pyproject_cst_path(cst_path: str) -> dict[str, Any]:
    pyproject = Path.cwd().resolve() / "pyproject.toml"
    if not pyproject.exists():
        pyproject = Path(__file__).resolve().parents[3] / "pyproject.toml"
    if not pyproject.exists():
        return error_response("pyproject_not_found", "No pyproject.toml found in workspace or repo root")

    original = pyproject.read_text(encoding="utf-8")

    toml_path = cst_path.replace("\\", "\\\\")
    entry = f'cst-studio-suite-link = {{ path = "{toml_path}", editable = true }}'

    # 1. 更新 [tool.uv.sources] 中的路径
    entry_start = "cst-studio-suite-link = {"
    idx = original.find(entry_start)
    if idx >= 0:
        line_end = original.find("\n", idx)
        if line_end == -1:
            line_end = len(original)
        new_content = original[:idx] + entry + original[line_end:]
    else:
        heading = "[tool.uv.sources]"
        hidx = original.find(heading)
        if hidx >= 0:
            insert_at = original.find("\n", hidx) + 1
            new_content = original[:insert_at] + entry + "\n" + original[insert_at:]
        else:
            uv_heading = "[tool.uv]"
            uvidx = original.find(uv_heading)
            if uvidx >= 0:
                insert_at = original.find("\n", uvidx) + 1
                new_content = original[:insert_at] + f"\n{heading}\n" + entry + "\n" + original[insert_at:]
            else:
                new_content = original.rstrip() + f"\n\n{uv_heading}\n\n{heading}\n" + entry + "\n"

    if new_content == original:
        return error_response("pyproject_update_failed", "Failed to modify pyproject.toml; check file format")

    # 2. 确保 cst-studio-suite-link 在 [project.dependencies] 中
    dep_name = "cst-studio-suite-link"
    deps_start = "dependencies = ["
    ds = new_content.find(deps_start)
    if ds >= 0:
        # 找到与 deps_start 的 [ 配对的 ]
        de = new_content.find("]", ds)
        if de >= 0 and dep_name not in new_content[ds:de]:
            new_content = new_content[:de] + f', "{dep_name}"' + new_content[de:]

    pyproject.write_text(new_content, encoding="utf-8")
    return {"status": "success", "cst_path": cst_path, "updated_file": str(pyproject)}


def install_cst_libraries(cst_path: str = "", dry_run: bool = False) -> dict[str, Any]:
    scan_result = scan_cst_installations()

    if cst_path:
        target_path = cst_path
        probe = _probe_path(target_path)
        if not probe["exists"]:
            return {
                **error_response("path_not_found", f"CST Python library path does not exist: {target_path}"),
                "scan": scan_result,
            }
    else:
        valid = [inst for inst in scan_result["installations"] if inst["has_interface"] and inst["has_results"]]
        if not valid:
            return {
                **error_response(
                    "cst_not_found",
                    "No CST Studio Suite 2026 Python libraries found. Install CST or provide --cst-path.",
                ),
                "scan": scan_result,
            }
        target_path = valid[0]["path"]

    if dry_run:
        return {
            "status": "success",
            "dry_run": True,
            "target_path": target_path,
            "active_path_matches": target_path == scan_result.get("active_path"),
            "scan": scan_result,
        }

    if target_path == scan_result.get("active_path"):
        verify = _verify_cst_imports(target_path)
        return {
            "status": "success",
            "cst_path": target_path,
            "already_configured": True,
            "pyproject_updated": False,
            "import_verification": verify,
            "scan": scan_result,
        }

    write_result = _write_pyproject_cst_path(target_path)
    if write_result.get("status") == "error":
        return {**write_result, "scan": scan_result}

    verify = _verify_cst_imports(target_path)
    return {
        "status": "success",
        "cst_path": target_path,
        "already_configured": False,
        "pyproject_updated": True,
        "import_verification": verify,
        "scan": scan_result,
    }


def _verify_cst_imports(cst_path: str) -> dict[str, Any]:
    results: dict[str, Any] = {}
    sp = str(Path(cst_path).resolve())
    if sp not in sys.path:
        sys.path.insert(0, sp)
    for mod in ("cst", "cst.interface", "cst.results"):
        try:
            __import__(mod)
            results[mod] = "success"
        except Exception as exc:
            results[mod] = f"error: {exc}"
    return results


def _run_uv_cmd(args: list[str], workspace_root: str, timeout: int = 120, label: str = "uv") -> dict[str, Any]:
    try:
        result = subprocess.run(args, cwd=workspace_root, capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0:
            return {"status": "error", "message": f"{label} failed (exit {result.returncode}):\n{result.stderr.strip()[:500]}"}
        return {"status": "success"}
    except FileNotFoundError:
        return {"status": "error", "message": f"uv not on PATH, cannot run {label}"}
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": f"{label} timed out after {timeout}s"}
    except Exception as exc:
        return {"status": "error", "message": f"{label} error: {exc}"}


def _record_check(checks: list[dict[str, Any]], remaining: list[dict[str, Any]], name: str, status: str, message: str = "", *, auto_fixed: bool = False, user_action: str = "") -> None:
    item = {"name": name, "status": status, "message": message, "auto_fixed": auto_fixed, "user_action": user_action}
    checks.append(item)
    if status != "pass":
        remaining.append(item)


def health_check(workspace: str = "", auto_fix: bool = True) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    fixes_applied: list[str] = []
    remaining_issues: list[dict[str, Any]] = []

    # 1. Python version
    py_ok = sys.version_info >= (3, 12)
    _record_check(checks, remaining_issues, "python_version",
        "pass" if py_ok else "error",
        f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}" if py_ok else f"Python {sys.version_info.major}.{sys.version_info.minor} < 3.12",
        user_action="Install Python 3.12 or later from https://python.org" if not py_ok else "")

    # 2. uv
    uv_path = shutil.which("uv")
    _record_check(checks, remaining_issues, "uv",
        "pass" if uv_path else "warning",
        f"uv found at {uv_path}" if uv_path else "uv not on PATH",
        user_action='Install uv: powershell -c "irm https://astral.sh/uv/install.ps1 | iex"' if not uv_path else "")

    # 3. Workspace
    from . import workspace as ws_mod
    ws_info = ws_mod.workspace_status(workspace)
    ws_ok = ws_info["workspace_initialized"]
    ws_fixed = False
    if not ws_ok and auto_fix:
        try:
            fix = ws_mod.init_workspace(workspace)
            if fix.get("status") == "success":
                ws_fixed = True
                fixes_applied.append("workspace: initialized workspace")
                ws_info = ws_mod.workspace_status(workspace)
                ws_ok = True
        except Exception:
            pass
    _record_check(checks, remaining_issues, "workspace",
        "pass" if ws_ok else "error",
        f"Workspace at {ws_info['workspace_root']}" if ws_ok else "Workspace not initialized",
        auto_fixed=ws_fixed,
        user_action="Run: python <skill-root>/scripts/cst_runtime_cli.py init-workspace --workspace <path>" if not ws_ok and not auto_fix else "")

    # 4. CST library scan + auto-configure
    scan = scan_cst_installations()
    cst_found = scan["found_count"] > 0
    cst_valid = any(inst["has_interface"] and inst["has_results"] for inst in scan["installations"])
    cst_configured = scan["active_valid"]

    cst_fixed = False
    if not cst_configured and cst_valid and auto_fix:
        try:
            install_result = install_cst_libraries()
            if install_result.get("status") == "success":
                cst_fixed = True
                fixes_applied.append(f"cst_libraries: configured {install_result.get('cst_path', '')}")
                scan = scan_cst_installations()
                cst_configured = True
        except Exception:
            pass

    if not cst_found:
        cst_status, cst_msg, cst_action = "error", "No CST Studio Suite installation detected", "Install CST Studio Suite 2026 or higher, then re-run health-check"
    elif not cst_valid:
        cst_status, cst_msg, cst_action = "error", f"CST found at {scan['installations'][0]['path']} but Python libraries incomplete", "Reinstall CST Studio Suite with Python libraries option"
    elif not cst_configured:
        cst_status, cst_msg, cst_action = "warning", "CST libraries found but not configured in pyproject.toml", f"Run: python <skill-root>/scripts/cst_runtime_cli.py install-cst-libraries --cst-path \"{scan['installations'][0]['path']}\""
    else:
        cst_status, cst_msg, cst_action = "pass", f"CST libraries at {scan['active_path']}", ""
    _record_check(checks, remaining_issues, "cst_libraries", cst_status, cst_msg, auto_fixed=cst_fixed, user_action=cst_action)

    # 5. uv sync (auto-fix only, skip if blocking issues exist)
    if auto_fix and not any(c["status"] == "error" for c in checks):
        ws_root = ws_info.get("workspace_root")
        if ws_root:
            first_setup = not (Path(str(ws_root)) / ".venv").is_dir()
            sync_result = _run_uv_cmd(["uv", "sync"], str(ws_root), label="uv sync")
            _record_check(checks, remaining_issues, "uv_sync",
                "pass" if sync_result["status"] == "success" else "error",
                sync_result.get("message", "uv sync completed"))
            if sync_result["status"] == "success" and first_setup:
                fixes_applied.append("uv_sync: dependencies installed to .venv")
                doctor_result = _run_uv_cmd(["uv", "run", "python", "-m", "cst_runtime", "doctor"], str(ws_root), timeout=60, label="doctor")
                _record_check(checks, remaining_issues, "final_verification",
                    "pass" if doctor_result["status"] == "success" else "warning",
                    doctor_result.get("message", "Post-sync doctor check passed"))
                if doctor_result["status"] == "success":
                    fixes_applied.append("final_verification: doctor check passed")

    overall = "pass"
    for c in checks:
        if c["status"] == "error":
            overall = "blocked"
            break
        if c["status"] == "warning" and overall == "pass":
            overall = "degraded"

    return {
        "status": "success",
        "overall": overall,
        "checks": checks,
        "fixes_applied": fixes_applied,
        "remaining_issues": [{k: v for k, v in issue.items() if v} for issue in remaining_issues],
        "readiness_summary": "All systems ready." if overall == "pass" else f"Auto-fixed {len(fixes_applied)} issue(s); {len(remaining_issues)} remaining.",
        "user_instructions": "\n".join(f"- [{issue['name']}] {issue['user_action']}" for issue in remaining_issues if issue.get("user_action")) if remaining_issues else "No manual action needed.",
    }
