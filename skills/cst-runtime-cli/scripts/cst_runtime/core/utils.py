from __future__ import annotations

import math
import os
from typing import Any


def abs_project_path(project_path: str) -> str:
    normalized = os.path.abspath(os.path.expanduser(project_path))
    if not normalized.lower().endswith(".cst"):
        normalized += ".cst"
    return normalized


def safe_log_db(value: float) -> float:
    return 20.0 * math.log10(max(abs(value), 1e-15))


def serialize_value(value: Any) -> Any:
    if isinstance(value, complex):
        return {"real": value.real, "imag": value.imag, "complex_str": str(value)}
    if isinstance(value, dict):
        return {str(key): serialize_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [serialize_value(item) for item in value]
    if hasattr(value, "tolist"):
        return serialize_value(value.tolist())
    return value


def parse_list_arg(value: Any) -> list[str]:
    """Parse a CLI arg that may be a list, a JSON string, or a comma-separated string."""
    if isinstance(value, list):
        return [str(v) for v in value]
    if not isinstance(value, str) or not value.strip():
        return []
    s = value.strip()
    if s.startswith("[") and s.endswith("]"):
        try:
            import json as _json
            parsed = _json.loads(s)
            if isinstance(parsed, list):
                return [str(v) for v in parsed]
        except Exception:
            pass
    return [v.strip().strip('"').strip("'") for v in s.strip("[]").split(",") if v.strip()]


def project_path_from_args(args: dict) -> str:
    """Validate and extract .cst project path from args dict."""
    from . import identity as _pi
    from pathlib import Path
    project_path = _pi.project_path_from_args(args)
    if Path(project_path).suffix.lower() != ".cst":
        raise ValueError("project_path must point to a concrete .cst file, not a directory")
    return project_path


def run_id_from_args(args: dict, default: int = 0) -> int:
    """Extract run_id from args, with fallback to max(run_ids)."""
    if args.get("run_id") is not None:
        return int(args.get("run_id", default))
    run_ids = args.get("run_ids")
    if isinstance(run_ids, list) and run_ids:
        return int(max(run_ids))
    return default