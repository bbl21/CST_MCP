"""audit.py — audit 工具定义"""
from . import _register_tool_defs


TOOL_DEFS = {
"record-stage": {
    "category": "audit",
    "risk": "filesystem-write",
    "description": "Write a stage record and production-chain log entry.",
    "handler": "tool_record_stage",
    "direct_flags": False,
    "args_template": {"task_path": "C:\\path\\to\\tasks\\task_xxx", "run_id": "run_001", "stage": "cli_runtime_iteration", "status": "completed", "message": "", "details_json": "{}"},
},

"stage-evidence": {
    "category": "audit",
    "risk": "read",
    "description": "Capture CST project state snapshots and generate before/after comparison reports. Use --capture to snapshot, --compare to diff two snapshots into HTML.",
    "handler": "tool_stage_evidence",
    "direct_flags": True,
    "args_template": {"project_path": "C:\\path\\to\\tasks\\task_xxx\\runs\\run_001\\projects\\working.cst", "capture": ["parameters", "entities", "file_info"], "stage_name": "snapshot_before_modeling", "output_dir": "C:\\path\\to\\tasks\\task_xxx\\runs\\run_001\\analysis", "compare": ["C:\\path\\to\\tasks\\task_xxx\\runs\\run_001\\analysis\\snapshot_before.json", "C:\\path\\to\\tasks\\task_xxx\\runs\\run_001\\analysis\\snapshot_after.json"], "output_html": "C:\\path\\to\\tasks\\task_xxx\\runs\\run_001\\analysis\\evidence_report.html"},
},

"update-status": {
    "category": "audit",
    "risk": "filesystem-write",
    "description": "Update the formal run status.json file.",
    "handler": "tool_update_status",
    "direct_flags": False,
    "args_template": {"task_path": "C:\\path\\to\\tasks\\task_xxx", "run_id": "run_001", "status": "validated", "stage": "cli_runtime_iteration", "best_result_json": "{}", "output_files_json": "{}", "error_json": "", "extra_json": "{}"},
},
}


# --- Handlers ---

from ..core import audit as _audit
from ..core import evidence as _evidence
from ..core.utils import parse_list_arg


def tool_record_stage(args: dict) -> dict:
    return _audit.record_run_stage(**args)


def tool_update_status(args: dict) -> dict:
    return _audit.update_run_status(**args)


def tool_stage_evidence(args: dict) -> dict:
    capture = parse_list_arg(args.get("capture"))
    compare = parse_list_arg(args.get("compare"))
    if capture:
        return _evidence.capture_snapshot(
            project_path=str(args.get("project_path", "")),
            capture_types=capture if isinstance(capture, list) else [],
            output_dir=str(args.get("output_dir", "")),
            stage_name=str(args.get("stage_name", "")),
        )
    elif compare:
        if not isinstance(compare, list) or len(compare) < 2:
            return {"status": "error", "error_type": "invalid_compare_args", "message": "compare requires [before_file, after_file]"}
        return _evidence.compare_snapshots(
            before_file=str(compare[0]),
            after_file=str(compare[1]),
            output_html=str(args.get("output_html", "")),
        )
    else:
        return {"status": "error", "error_type": "missing_action", "message": "Provide --capture or --compare"}


_register_tool_defs(TOOL_DEFS)
