from __future__ import annotations

import ast
import json
import math
import re
import time
from html import escape
from pathlib import Path
from typing import Any

from ..core.errors import error_response
from .svg_linechart import (
    _COLORS, _DARK_BG, _DARK_TEXT, _LIGHT_BG, _LIGHT_TEXT,
    _SVG_MARGIN, _SVG_W, _SVG_H,
    safe_log_db, complex_components, scalar_series,
    svg_linechart, svg_mini_trend,
)
from .svg_heatmap import svg_heatmap
from .svg_page import svg_page, metric_cards_html
from .canvas_3d import render_3d_farfield

_TIMELINE_TOOLS = {
    "change-parameter",
    "define-parameters",
    "define-brick", "define-cylinder", "define-cone", "define-sphere",
    "define-extrude-curve", "define-loft", "define-rectangle", "define-polygon-3d",
    "boolean-subtract", "boolean-add", "boolean-insert", "boolean-intersect",
    "delete-entity", "rename-entity",
    "start-simulation", "start-simulation-async",
    "get-1d-result",
    "stage-evidence",
    "inspect-project",
    "prepare-experiment",
    "run-experiment",
    "generate-report",
    "record-stage",
    "update-status",
    "export-farfield-grid",
    "export-farfield-cut",
    "export-run-results",
    "cst-session-open",
    "cst-session-close",
    "list-parameters",
    "list-entities",
    "list-run-ids",
    "get-parameter-combination",
}

_SECTION_LABELS = {
    "s11": "S11 曲线",
    "farfield": "3D 辐射方向图",
    "2d": "2D 场分布",
    "timeline": "操作审计追踪",
    "params": "参数变更记录",
    "efield": "电场分布",
    "surface_current": "表面电流",
    "voltage": "电压",
    "optimization": "优化总览",
    "audit": "完整审计追踪",
    "cuts": "远场切面分析",
}


# ── File loading and parsing utilities ──


def _load_exported_payload(file_path: str) -> dict[str, Any]:
    source = Path(file_path).expanduser().resolve()
    text = source.read_text(encoding="utf-8-sig", errors="replace")
    if source.suffix.lower() == ".json":
        return json.loads(text)
    parsed = _try_parse_cst_farfield_ascii(text, filename=source.name)
    if parsed is None:
        raise ValueError(f"unsupported exported file format: {source}")
    return parsed


def _try_parse_cst_farfield_ascii(text: str, filename: str = "") -> dict[str, Any] | None:
    lines = text.splitlines()
    if not lines:
        return None

    header = next((line.strip() for line in lines if "Theta" in line and "Phi" in line), "")
    if not header:
        return None

    quantity = "Value"
    unit = ""
    compact_header = re.sub(r"\s+", "", header)
    quantity_candidates = {
        "Abs(RealizedGain)": "Abs(Realized Gain)",
        "Abs(Gain)": "Abs(Gain)",
        "Abs(Directivity)": "Abs(Directivity)",
        "Abs(E)": "Abs(E)",
        "Abs(Theta)": "Abs(Theta)",
        "Abs(Phi)": "Abs(Phi)",
    }
    for compact_candidate, display_name in quantity_candidates.items():
        if compact_candidate in compact_header:
            quantity = display_name
            suffix = compact_header.split(compact_candidate, 1)[1]
            unit_match = re.search(r"\[([^\]]*)\]", suffix)
            unit = (unit_match.group(1).strip() if unit_match else "")
            break

    samples: dict[tuple[float, float], float] = {}
    theta_values: set[float] = set()
    phi_values: set[float] = set()
    for line in lines:
        parts = line.split()
        if len(parts) < 3:
            continue
        try:
            theta = float(parts[0])
            phi = float(parts[1])
            value = float(parts[2])
        except Exception:
            continue
        theta_values.add(theta)
        phi_values.add(phi)
        samples[(theta, phi)] = value

    if not samples:
        return None

    theta_sorted = sorted(theta_values)
    phi_sorted = sorted(phi_values)
    closure_added = False
    if len(phi_sorted) > 1 and abs(phi_sorted[0]) <= 1e-9 and 350.0 <= phi_sorted[-1] < 360.0:
        phi_sorted = [*phi_sorted, 360.0]
        closure_added = True

    grid: list[list[float | None]] = []
    for theta in theta_sorted:
        row: list[float | None] = []
        for phi in phi_sorted:
            source_phi = 0.0 if closure_added and abs(phi - 360.0) <= 1e-9 else phi
            row.append(samples.get((theta, source_phi)))
        grid.append(row)

    dataunit = unit or ("dBi" if quantity in {"Abs(Realized Gain)", "Abs(Gain)", "Abs(Directivity)"} else "")
    return {
        "kind": "2d",
        "title": filename or "CST Farfield",
        "xlabel": "Phi (deg)",
        "ylabel": "Theta (deg)",
        "zlabel": f"{quantity} ({dataunit})" if dataunit else quantity,
        "xpositions": phi_sorted,
        "ypositions": theta_sorted,
        "data": grid,
        "metadata": {
            "source_format": "cst_farfield_ascii",
            "source_quantity": quantity,
            "dataunit": dataunit,
            "point_count": len(samples),
            "theta_count": len(theta_sorted),
            "phi_count": len(phi_sorted),
            "closure_phi_360_added": closure_added,
        },
    }


def _plot_output_path(output_html: str, source_file: Path, prefix: str) -> Path:
    if output_html:
        target = Path(output_html).expanduser().resolve()
    else:
        target = source_file.expanduser().resolve().parent / f"{prefix}_{source_file.stem}.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    return target


def _parse_cli_filename(filename: str) -> dict[str, Any] | None:
    m = re.match(r"cli_(\d{8})_(\d{6})_(\d+)_(.+)\.json", filename)
    if not m:
        return None
    date_str, time_str, micro, tool = m.groups()
    ts = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}T{time_str[:2]}:{time_str[2:4]}:{time_str[4:6]}.{micro}"
    return {"timestamp": ts, "tool": tool.replace("_", "-"), "filename": filename, "sort_key": f"{date_str}{time_str}{micro}"}


def _build_timeline(run_dir: str) -> list[dict[str, Any]]:
    stages_dir = Path(run_dir) / "stages"
    if not stages_dir.is_dir():
        return []

    records: list[dict[str, Any]] = []
    for fpath in sorted(stages_dir.iterdir()):
        info = _parse_cli_filename(fpath.name)
        if not info:
            continue
        if info["tool"] not in _TIMELINE_TOOLS:
            continue
        try:
            data = json.loads(fpath.read_text(encoding="utf-8-sig"))
        except Exception:
            continue
        info["status"] = data.get("status", "unknown")
        info["args"] = data.get("args", {})
        info["result"] = data.get("result", {})
        records.append(info)

    records.sort(key=lambda r: r["sort_key"])
    return records


def _categorize_step(record: dict[str, Any]) -> str:
    tool = record["tool"]
    if tool in {"change-parameter"}:
        return "param_change"
    if tool in {"define-parameters"}:
        return "param_define"
    if tool in {"define-brick", "define-cylinder", "define-cone", "define-sphere",
                 "define-extrude-curve", "define-loft", "define-rectangle", "define-polygon-3d"}:
        return "geometry"
    if tool.startswith("boolean-"):
        return "boolean"
    if tool in {"delete-entity", "rename-entity"}:
        return "entity"
    if tool in {"start-simulation", "start-simulation-async", "run-experiment"}:
        return "simulation"
    if tool in {"prepare-experiment", "change-parameter", "define-parameters"}:
        return "param_change"
    if tool in {"inspect-project", "list-parameters", "list-entities", "list-run-ids",
                 "get-parameter-combination", "stage-evidence"}:
        return "read"
    if tool in {"cst-session-open", "cst-session-close"}:
        return "session"
    if tool in {"generate-report", "export-run-results", "export-farfield-grid", "export-farfield-cut"}:
        return "export"
    if tool in {"record-stage", "update-status"}:
        return "audit"
    if tool in {"cleanup-cst-processes"}:
        return "cleanup"
    return "other"
    if tool in {"get-1d-result"}:
        return "result"
    if tool in {"stage-evidence"}:
        return "evidence"
    return "other"


def _step_summary(record: dict[str, Any]) -> str:
    tool = record["tool"]
    args = record.get("args", {})
    if tool == "change-parameter":
        return f'{args.get("name", "?")} = {args.get("value", "?")}'
    if tool == "define-parameters":
        names = args.get("names", [])
        if isinstance(names, str):
            try:
                names = ast.literal_eval(names)
            except Exception:
                names = [names]
        return f'define {len(names)} params'
    if tool in {"define-brick", "define-cylinder", "define-cone", "define-sphere"}:
        return f'{args.get("name", "?")} ({args.get("material", "PEC")})'
    if tool.startswith("boolean-"):
        op = tool.replace("boolean-", "")
        return f'{op}: {args.get("target", "?")} / {args.get("tool", "?")}'
    if tool in {"delete-entity"}:
        return f'del {args.get("name", "?")}'
    if tool in {"start-simulation", "start-simulation-async"}:
        return "simulate"
    if tool in {"get-1d-result"}:
        return f'read S11 run={args.get("run_id", "?")}'
    if tool in {"stage-evidence"}:
        return f'capture: {args.get("stage_name", "?")}'
    if tool == "prepare-experiment":
        return f'{args.get("param_name", "?")} = {args.get("param_value", "?")}'
    if tool == "run-experiment":
        return f'simulate + export'
    if tool in {"inspect-project", "list-parameters", "list-entities", "list-run-ids", "get-parameter-combination"}:
        return f'read project info'
    if tool in {"generate-report", "export-run-results", "export-farfield-grid", "export-farfield-cut"}:
        return f'export data'
    if tool in {"record-stage", "update-status"}:
        return f'audit log'
    if tool in {"cst-session-open", "cst-session-close"}:
        return tool
    return tool


def _rationale_from_step(record: dict[str, Any]) -> str:
    tool = record["tool"]
    args = record.get("args", {})
    if tool == "change-parameter":
        name = args.get("name", "")
        value = args.get("value", "")
        return f"修改参数 {name} = {value}"
    if tool == "define-parameters":
        return "定义优化参数"
    if tool == "prepare-experiment":
        return f"改参 {args.get('param_name', '?')} = {args.get('param_value', '?')}"
    if tool == "run-experiment":
        result = record.get("result", {})
        s11 = result.get("s11_metric", {})
        if s11:
            return f"仿真完成，S11 最优 {s11.get('min_db', '?')} dB @ {s11.get('best_freq', '?')} GHz"
        return "仿真 + 导出结果"
    if tool == "inspect-project":
        params = args.get("parameters", {})
        return f"读取工程参数和实体列表"
    if tool in {"generate-report"}:
        return f"生成综合报告"
    if tool in {"record-stage"}:
        return f"记录操作阶段"
    if tool in {"export-run-results", "export-farfield-grid", "export-farfield-cut"}:
        return f"导出结果数据"
    if tool in {"cst-session-open"}:
        return f"打开 CST 工程"
    if tool in {"cst-session-close"}:
        return f"关闭 CST 工程"
    if tool in {"define-brick", "define-cylinder", "define-cone"}:
        name = args.get("name", "")
        return f"创建几何体 {name}"
    if tool.startswith("boolean-"):
        return "布尔运算，细化几何结构"
    if tool in {"delete-entity"}:
        return "删除冗余几何体"
    if tool in {"start-simulation", "start-simulation-async"}:
        return "启动仿真"
    if tool in {"get-1d-result"}:
        return "导出 S11 结果"
    if tool in {"stage-evidence"}:
        stage = args.get("stage_name", "")
        return f"快照：{stage}"
    return ""


def _load_s11_exports(export_dir: str) -> dict[int, dict[str, Any]]:
    exports: dict[int, dict[str, Any]] = {}
    d = Path(export_dir)
    if not d.is_dir():
        return exports
    for fpath in sorted(list(d.glob("s11_run*.json")) + list(d.glob("result_1d_run*.json"))):
        try:
            payload = json.loads(fpath.read_text(encoding="utf-8-sig"))
            if "xdata" not in payload or "ydata" not in payload:
                continue
            run_id = payload.get("run_id", 0)
            db_values: list[float] = []
            for item in payload.get("ydata", []):
                real = item.get("real", 0) if isinstance(item, dict) else float(item) if isinstance(item, (int, float)) else 0
                imag = item.get("imag", 0) if isinstance(item, dict) else 0
                db_values.append(safe_log_db(math.hypot(real, imag)))
            min_db = min(db_values)
            min_idx = db_values.index(min_db)
            exports[run_id] = {
                "run_id": run_id,
                "file": fpath.name,
                "file_path": str(fpath),
                "xdata": payload.get("xdata", []),
                "ydata": db_values,
                "min_db": min_db,
                "best_freq": payload.get("xdata", [])[min_idx] if min_idx < len(payload.get("xdata", [])) else None,
                "parameter_combination": payload.get("parameter_combination", {}),
            }
        except Exception:
            pass
    return exports


# ── HTML component builders ──


def _step_card_html(step_idx: int, record: dict[str, Any], s11_exports: dict[int, dict[str, Any]]) -> str:
    tool = record["tool"]
    category = _categorize_step(record)
    summary = _step_summary(record)
    rationale = _rationale_from_step(record)
    ts = record.get("timestamp", "")
    status = record.get("status", "unknown")
    args = record.get("args", {})
    result = record.get("result", {})

    status_badge = f'<span class="badge badge-{"success" if status == "success" else "warn"}">{"成功" if status == "success" else "失败"}</span>'

    detail_json = json.dumps({"tool": tool, "args": args, "result": result}, indent=2, ensure_ascii=False)

    s11_snippet = ""
    if category == "result":
        export_path = args.get("export_path", "")
        if export_path:
            try:
                payload = json.loads((Path(export_path) if Path(export_path).is_file() else Path(export_path).expanduser()).read_text(encoding="utf-8-sig"))
                if "xdata" in payload and "ydata" in payload:
                    xs = payload.get("xdata", [])
                    ys_raw = payload.get("ydata", [])
                    db_vals = []
                    for item in ys_raw:
                        real = item.get("real", 0) if isinstance(item, dict) else float(item) if isinstance(item, (int, float)) else 0
                        imag = item.get("imag", 0) if isinstance(item, dict) else 0
                        db_vals.append(safe_log_db(math.hypot(real, imag)))
                    if db_vals:
                        min_db = min(db_vals)
                        min_idx = db_vals.index(min_db)
                        best_freq = xs[min_idx] if min_idx < len(xs) else 0
                        s11_snippet = f'<div class="s11-snippet"><span class="s11-min">S11={min_db:.2f} dB</span> <span class="s11-freq">@ {best_freq:.3f} GHz</span></div>'
            except Exception:
                pass

    card_class = "step-card"
    if category == "param_change":
        card_class += " step-param"
    elif category == "simulation":
        card_class += " step-sim"
    elif category == "result":
        card_class += " step-result"

    html = f'''<div class="{card_class}">
  <div class="step-header">
    <span class="step-idx">#{step_idx}</span>
    <span class="step-tool {category}">{category}</span>
    {status_badge}
    <span class="step-ts">{ts}</span>
  </div>
  <div class="step-body">
    <div class="step-summary"><strong>{escape(summary)}</strong></div>
    {f'<div class="step-rationale">{escape(rationale)}</div>' if rationale else ''}
    {s11_snippet}
  </div>
  <details class="step-detail">
    <summary>原始 JSON</summary>
    <pre>{escape(detail_json)}</pre>
  </details>
</div>'''
    return html


def _optimization_s11_chart(s11_exports: dict[int, dict[str, Any]], dark: bool = False) -> str:
    if not s11_exports:
        return '<div class="chart-panel"><p>无 S11 导出数据</p></div>'
    traces = []
    for rid in sorted(s11_exports.keys()):
        e = s11_exports[rid]
        traces.append({"x": e["xdata"], "y": e["ydata"], "name": f"Run {rid}"})
    svg = svg_linechart(traces, dark=dark)
    return f'<div class="chart-panel">{svg}</div>'


def _s11_table_html(s11_exports: dict[int, dict[str, Any]]) -> str:
    if not s11_exports:
        return ""
    best = min(s11_exports.values(), key=lambda e: e["min_db"])
    rows = []
    for rid in sorted(s11_exports.keys()):
        e = s11_exports[rid]
        is_best = rid == best["run_id"]
        row_class = ' class="best"' if is_best else ""
        badge = '<span class="badge badge-best">最优</span>' if is_best else ""
        rows.append(
            f'<tr{row_class}><td>{rid}{badge}</td><td>{escape(e["file"])}</td><td>{e["best_freq"]:.3f} GHz</td><td>{e["min_db"]:.3f} dB</td></tr>'
        )
    return (
        f'<div class="data-section">'
        f'<div class="section-title">S11 结果</div>'
            f'<table><thead><tr><th>运行</th><th>文件</th><th>最优频率</th><th>最低 S11</th></tr></thead><tbody>'
        + "".join(rows)
        + "</tbody></table></div>"
    )


def _optimization_metrics_html(s11_exports: dict[int, dict[str, Any]], timeline: list[dict[str, Any]]) -> str:
    metrics: list[dict[str, str]] = []
    if s11_exports:
        best = min(s11_exports.values(), key=lambda e: e["min_db"])
        metrics.append({"label": "最优 S11", "value": f"{best['min_db']:.2f}", "unit": "dB", "css_class": "success"})
        metrics.append({"label": "最优频率", "value": f"{best['best_freq']:.3f}" if best['best_freq'] else "-", "unit": "GHz", "css_class": "accent"})
        metrics.append({"label": "S11 运行", "value": str(len(s11_exports)), "css_class": ""})
    param_changes = [r for r in timeline if _categorize_step(r) == "param_change"]
    simulations = [r for r in timeline if _categorize_step(r) == "simulation"]
    if param_changes:
        metrics.append({"label": "参数变更", "value": str(len(param_changes)), "css_class": ""})
    if simulations:
        metrics.append({"label": "仿真次数", "value": str(len(simulations)), "css_class": ""})
    if timeline:
        freq_range = ""
        if s11_exports and len(s11_exports) > 0:
            any_e = next(iter(s11_exports.values()))
            if any_e["xdata"]:
                freq_range = f"{any_e['xdata'][0]:.2f} - {any_e['xdata'][-1]:.2f}"
        if freq_range:
            metrics.append({"label": "频率范围", "value": freq_range, "unit": "GHz", "css_class": ""})
    return metric_cards_html(metrics) if metrics else ""


def _param_changes_table_html(timeline: list[dict[str, Any]]) -> str:
    changes = [r for r in timeline if _categorize_step(r) == "param_change"]
    if not changes:
        return ""
    rows = []
    for r in changes:
        args = r.get("args", {})
        name = args.get("name", "?")
        value = args.get("value", "?")
        rows.append(f'<tr><td>{escape(str(name))}</td><td>{escape(str(value))}</td><td>{r.get("timestamp", "")}</td></tr>')
    return (
        f'<div class="data-section">'
        f'<div class="section-title">参数变更记录</div>'
        f'<table><thead><tr><th>参数</th><th>新值</th><th>时间</th></tr></thead><tbody>'
        + "".join(rows)
        + "</tbody></table></div>"
    )


# ── S11/Farfield data loaders ──


def load_s11_series(file_paths: list[str]) -> list[dict[str, Any]]:
    series: list[dict[str, Any]] = []
    for index, file_path in enumerate(file_paths):
        path = Path(file_path).expanduser().resolve()
        if path.suffix.lower() != ".json":
            raise ValueError(f"S11 input must be .json: {path}")
        payload = _load_exported_payload(str(path))
        xdata = payload.get("xdata") or []
        ydata = payload.get("ydata") or []
        if not xdata or not ydata:
            raise ValueError(f"S11 input is missing xdata/ydata: {path}")
        db_values: list[float] = []
        for item in ydata:
            real, imag = complex_components(item)
            db_values.append(safe_log_db(math.hypot(real, imag)))
        run_id = payload.get("run_id")
        if run_id is None:
            match = re.search(r"run[_-]?(\d+)", path.stem, re.IGNORECASE)
            run_id = int(match.group(1)) if match else index + 1
        min_db = min(db_values)
        min_index = db_values.index(min_db)
        series.append(
            {
                "label": f"Run {run_id}",
                "run_id": run_id,
                "file": path.name,
                "file_path": str(path),
                "xdata": xdata,
                "ydata": db_values,
                "min_db": min_db,
                "best_freq": xdata[min_index] if min_index < len(xdata) else None,
            }
        )
    return series


# ── Public API: plot exported file ──


def plot_exported_file(file_path: str, output_html: str = "", page_title: str = "") -> dict[str, Any]:
    try:
        source = Path(file_path).expanduser().resolve()
        payload = _load_exported_payload(str(source))
        title = page_title or payload.get("title") or f"Export Preview - {source.name}"
        target = _plot_output_path(output_html, source, "export_preview")

        if "xdata" in payload and "ydata" in payload:
            xdata = payload.get("xdata") or []
            ydata, y_kind = scalar_series(payload.get("ydata") or [])
            yaxis_title = "Magnitude (dB)" if y_kind == "magnitude_db" else str(payload.get("ylabel") or "Value")
            svg = svg_linechart(
                [{"x": xdata, "y": ydata, "name": "value"}],
                xlabel=str(payload.get("xlabel") or "X"),
                ylabel=yaxis_title,
            )
            rendered_kind = "1d"
        elif "data" in payload:
            svg = svg_heatmap(
                x=payload.get("xpositions") or [],
                y=payload.get("ypositions") or [],
                z=payload.get("data") or [],
                title=title,
                xlabel=str(payload.get("xlabel") or "X"),
                ylabel=str(payload.get("ylabel") or "Y"),
                zlabel=str(payload.get("zlabel") or "Value"),
            )
            rendered_kind = "2d"
        else:
            return error_response(
                "unsupported_export_payload",
                "JSON file does not contain xdata/ydata or 2D data",
                file_path=str(source),
                runtime_module="cst_runtime.render.dashboard",
            )

        target.write_text(svg_page(title, f'<div class="chart-panel">{svg}</div>'), encoding="utf-8")
        return {
            "status": "success",
            "source": "exported_file",
            "file_path": str(source),
            "rendered_kind": rendered_kind,
            "output_html": str(target),
            "runtime_module": "cst_runtime.render.dashboard",
        }
    except Exception as exc:
        return error_response(
            "plot_exported_file_failed",
            str(exc),
            file_path=str(file_path),
            runtime_module="cst_runtime.render.dashboard",
        )


# ── Report module system ──

_AUTO_MODULES: dict[str, callable] = {}


def _auto_detect_modules(exports_d: Path) -> list[str]:
    """Detect available data modules from exports directory."""
    modules: list[str] = []
    if list(exports_d.glob("s11_run*.json")):
        modules.append("s11")
    if list(exports_d.glob("farfield/*.json")):
        modules.append("farfield3d")
    if list(exports_d.glob("result_2d_*.json")):
        modules.append("2d")
    if list(exports_d.glob("efield_*.txt")):
        modules.append("efield")
    if list(exports_d.glob("surface_current_*.txt")):
        modules.append("surface_current")
    if list(exports_d.glob("voltage_*.txt")):
        modules.append("voltage")
    if list(exports_d.glob("farfield/cuts/*.json")):
        modules.append("cuts")
    if list(exports_d.glob("s11_run*.json")) or list(exports_d.parent.glob("stages/*.json")):
        s11_exports = _load_s11_exports(str(exports_d))
        if s11_exports:
            modules.append("optimization")
    if (exports_d.parent / "stages").is_dir() or (exports_d.parent / "stage_records").is_dir():
        modules.append("timeline")
        modules.append("audit")
    return modules


def _report_module_s11(exports_d: Path) -> tuple[str, list[dict], dict[str, Any]]:
    s11_files = sorted(list(exports_d.glob("s11_run*.json")) + list(exports_d.glob("result_1d_run*.json")))
    s11_data = _load_s11_exports(str(exports_d)) if s11_files else {}
    if not s11_data:
        return "", [], {}
    traces = [{"x": e["xdata"], "y": e["ydata"], "name": f"Run {e['run_id']}"} for e in s11_data.values()]
    svg = svg_linechart(traces)
    html = f'<h2 class="section-h2">{_SECTION_LABELS["s11"]}</h2><div class="chart-panel">{svg}</div>'
    best = min(s11_data.values(), key=lambda e: e["min_db"])
    metrics = [
        {"label": "最优 S11", "value": f"{best['min_db']:.2f}", "unit": "dB", "css_class": "success"},
        {"label": "最优频率", "value": f"{best['best_freq']:.3f}" if best['best_freq'] else "-", "unit": "GHz", "css_class": "accent"},
        {"label": "S11 文件数", "value": str(len(s11_data)), "css_class": ""},
    ]
    return html, metrics, {"s11_data": s11_data}


def _report_module_farfield3d(exports_d: Path) -> tuple[str, list[dict], dict[str, Any]]:
    ff_files = sorted(exports_d.glob("farfield/*.json"))
    if not ff_files:
        return "", [], {}
    panels: list[str] = []
    for i, ff_file in enumerate(ff_files):
        try:
            ff_data = _load_exported_payload(str(ff_file))
            display = "block" if i == 0 else "none"
            panels.append(
                f'<div class="ff-panel" id="ffPanel{i}" style="display:{display}">'
                f'{render_3d_farfield(ff_data, f"ff3d_{i}")}'
                f'</div>'
            )
        except Exception:
            pass
    if not panels:
        return "", [], {}
    selector = ""
    if len(ff_files) > 1:
        opts = "".join(f'<option value="{i}">{ff.name}</option>' for i, ff in enumerate(ff_files))
        selector = f'<select id="ffSelect" onchange="switchFF(this.value)" style="margin-bottom:12px;padding:6px 12px;border:1px solid var(--border);border-radius:6px;background:var(--bg-raised);color:var(--text);font-size:13px">{opts}</select>'
        panels.append('<script>function switchFF(v){var ps=document.querySelectorAll(".ff-panel");for(var i=0;i<ps.length;i++)ps[i].style.display=i==v?"block":"none";}</script>')
    html = f'<h2 class="section-h2">{_SECTION_LABELS["farfield"]}</h2>{selector}\n{"".join(panels)}'
    metrics = [{"label": "远场文件数", "value": str(len(ff_files)), "css_class": ""}]
    return html, metrics, {"ff_files": ff_files}


def _report_module_2d(exports_d: Path) -> tuple[str, list[dict], dict[str, Any]]:
    two_d_files = sorted(exports_d.glob("result_2d_*.json"))
    if not two_d_files:
        return "", [], {}
    panels: list[str] = []
    for td in two_d_files:
        try:
            payload = _load_exported_payload(str(td))
            svg = svg_heatmap(
                x=payload.get("xpositions", []), y=payload.get("ypositions", []),
                z=payload.get("data", []), title=payload.get("title", td.stem),
                xlabel=payload.get("xlabel", "X"), ylabel=payload.get("ylabel", "Y"),
                zlabel=payload.get("zlabel", "Value"),
            )
            panels.append(f'<div class="chart-panel">{svg}</div>')
        except Exception:
            pass
    if not panels:
        return "", [], {}
    html = f'<h2 class="section-h2">{_SECTION_LABELS["2d"]}</h2>\n{"".join(panels)}'
    return html, [], {}


def _report_module_timeline(exports_d: Path, data_dir: Path) -> tuple[str, list[dict], dict[str, Any]]:
    timeline = _build_timeline(str(data_dir))
    if not timeline:
        return "", [], {}
    s11_data = _load_s11_exports(str(exports_d))
    parts: list[str] = []
    parts.append(f'<h2 class="section-h2">{_SECTION_LABELS["timeline"]}（{len(timeline)} 步）</h2>')
    for idx, rec in enumerate(timeline, 1):
        parts.append(_step_card_html(idx, rec, s11_data))
    param_changes = [r for r in timeline if _categorize_step(r) == "param_change"]
    if param_changes:
        parts.append(f'<h2 class="section-h2">{_SECTION_LABELS["params"]}</h2>')
        parts.append(_param_changes_table_html(timeline))
    html = "\n".join(parts)
    metrics = [{"label": "操作步数", "value": str(len(timeline)), "css_class": ""}]
    if param_changes:
        metrics.append({"label": "参数变更", "value": str(len(param_changes)), "css_class": ""})
    return html, metrics, {"timeline": timeline, "s11_data": s11_data}


def _report_module_efield(exports_d: Path, label_key: str, glob_pattern: str, section_label_key: str) -> tuple[str, list[dict], dict[str, Any]]:
    files = sorted(exports_d.glob(glob_pattern))
    if not files:
        return "", [], {}
    html = f'<h2 class="section-h2">{_SECTION_LABELS[section_label_key]}（{len(files)} 文件）</h2>'
    html += f'<table><thead><tr><th>文件</th></tr></thead><tbody>{"".join(f"<tr><td>{escape(f.name)}</td></tr>" for f in files)}</tbody></table>'
    return html, [], {}


def _report_module_optimization(exports_d: Path, data_dir: Path) -> tuple[str, list[dict], dict[str, Any]]:
    s11_exports = _load_s11_exports(str(exports_d))
    timeline = _build_timeline(str(data_dir))
    if not s11_exports and not timeline:
        return "", [], {}
    parts: list[str] = []
    metrics = _optimization_metrics_html(s11_exports, timeline)
    parts.append(f'<h2 class="section-h2">{_SECTION_LABELS["optimization"]}</h2>')
    s11_chart = _optimization_s11_chart(s11_exports)
    if s11_chart:
        parts.append(s11_chart)
    if len(s11_exports) > 1:
        min_dbs = [s11_exports[rid]["min_db"] for rid in sorted(s11_exports.keys())]
        parts.append(f'<div class="chart-panel">{svg_mini_trend(min_dbs, label="最优 S11 per run")}</div>')
    param_table = _param_changes_table_html(timeline)
    if param_table:
        parts.append(param_table)
    s11_table = _s11_table_html(s11_exports)
    if s11_table:
        parts.append(s11_table)
    significant = [r for r in timeline if _categorize_step(r) in {"param_change", "simulation", "result"}]
    if significant:
        step_previews: list[str] = []
        for idx, r in enumerate(significant[-12:]):
            step_previews.append(_step_card_html(len(significant) - len(significant[-12:]) + idx + 1, r, s11_exports))
        parts.append(f'<div class="section-title">近期操作</div><div class="step-list">{"".join(step_previews)}</div>')
    html = "\n".join(parts)
    meta = {"s11_count": len(s11_exports), "timeline_count": len(timeline)}
    return html, [], meta


def _report_module_audit(exports_d: Path, data_dir: Path) -> tuple[str, list[dict], dict[str, Any]]:
    s11_exports = _load_s11_exports(str(exports_d))
    timeline = _build_timeline(str(data_dir))
    if not timeline and not s11_exports:
        return "", [], {}
    parts: list[str] = []
    s11_chart = _optimization_s11_chart(s11_exports)
    if s11_chart:
        parts.append(s11_chart)
    param_table = _param_changes_table_html(timeline)
    if param_table:
        parts.append(param_table)
    s11_table = _s11_table_html(s11_exports)
    if s11_table:
        parts.append(s11_table)
    if timeline:
        step_cards: list[str] = []
        for idx, r in enumerate(timeline, 1):
            step_cards.append(_step_card_html(idx, r, s11_exports))
        parts.append(f'<h2 class="section-h2">{_SECTION_LABELS["audit"]}（{len(timeline)} 条操作）</h2><div class="step-list">{"".join(step_cards)}</div>')
    html = "\n".join(parts)
    return html, [], {"timeline_count": len(timeline), "s11_count": len(s11_exports)}


def _report_module_cuts(exports_d: Path) -> tuple[str, list[dict], dict[str, Any]]:
    cuts_dir = exports_d / "farfield" / "cuts"
    if not cuts_dir.is_dir():
        return "", [], {}
    cut_files = sorted(cuts_dir.glob("*.json"))
    if not cut_files:
        return "", [], {}
    rows: list[str] = []
    for cf in cut_files:
        try:
            payload = json.loads(cf.read_text(encoding="utf-8"))
            angle_deg = payload.get("angle_deg", [])
            primary_db = payload.get("primary_db", [])
            if not angle_deg or not primary_db:
                continue
            cut_type = payload.get("cut_type", "")
            cut_angle = payload.get("cut_angle", "")
            label_parts = [cf.stem]
            if cut_type:
                label_parts.append(f"({cut_type}={cut_angle}°)")
            label = " ".join(label_parts)
            min_v, max_v = min(primary_db), max(primary_db)
            rows.append(
                f"<tr><td>{escape(label)}</td>"
                f"<td>{len(angle_deg)}</td><td>{min_v:.2f}</td><td>{max_v:.2f}</td>"
                f"<td>{max_v - min_v:.2f}</td></tr>"
            )
        except Exception:
            pass
    if not rows:
        return "", [], {}
    html = (
        f'<h2 class="section-h2">{_SECTION_LABELS["cuts"]}（{len(rows)} 切面）</h2>'
        f'<table><thead><tr><th>切面</th><th>采样点</th><th>最小值(dB)</th><th>最大值(dB)</th><th>波动(dB)</th></tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table>'
    )
    return html, [], {"cut_count": len(rows)}


_REPORT_MODULES: dict[str, callable] = {
    "s11": lambda d, dd: _report_module_s11(d),
    "farfield3d": lambda d, dd: _report_module_farfield3d(d),
    "2d": lambda d, dd: _report_module_2d(d),
    "timeline": lambda d, dd: _report_module_timeline(d, dd),
    "efield": lambda d, dd: _report_module_efield(d, "efield", "efield_*.txt", "efield"),
    "surface_current": lambda d, dd: _report_module_efield(d, "surface_current", "surface_current_*.txt", "surface_current"),
    "voltage": lambda d, dd: _report_module_efield(d, "voltage", "voltage_*.txt", "voltage"),
    "optimization": _report_module_optimization,
    "audit": _report_module_audit,
    "cuts": lambda d, dd: _report_module_cuts(d),
}


# ── Public API: generate_report report ──


def generate_report(
    data_dir: str,
    output_html: str = "",
    page_title: str = "",
    modules: str = "",
    split: bool = False,
) -> dict[str, Any]:
    try:
        dd = Path(data_dir).expanduser().resolve()
        exports_d = dd / "exports"
        if not exports_d.is_dir():
            exports_d = dd
        target = Path(output_html).expanduser().resolve() if output_html else exports_d / "report.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        title = page_title or f"电磁仿真报告 — {dd.name}"

        module_names = [m.strip() for m in modules.split(",") if m.strip()] if modules else _auto_detect_modules(exports_d)

        body_parts: list[str] = []
        all_metrics: list[dict[str, str]] = []
        module_htmls: dict[str, str] = {}
        result_payload: dict[str, Any] = {"status": "success", "output_html": str(target), "runtime_module": "cst_runtime.render.dashboard"}

        for name in module_names:
            builder = _REPORT_MODULES.get(name)
            if builder is None:
                continue
            try:
                html, metrics, meta = builder(exports_d, dd)
            except Exception:
                continue
            if not html:
                continue
            body_parts.append(html)
            all_metrics.extend(metrics)
            module_htmls[name] = html
            for key, value in meta.items():
                if isinstance(value, (int, list)):
                    result_payload[f"{name}_{key}"] = value

        if split:
            for mod_name, mod_html in module_htmls.items():
                mod_label = _SECTION_LABELS.get(mod_name, mod_name)
                mod_target = target.with_stem(f"{target.stem}_{mod_name}")
                mod_target.write_text(svg_page(f"{title} — {mod_label}", mod_html), encoding="utf-8")

        body = "\n".join(body_parts)
        metrics_str = metric_cards_html(all_metrics) if all_metrics else ""
        target.write_text(
            svg_page(title, body, metrics_html=metrics_str, subtitle=f"数据目录：{str(exports_d)}"),
            encoding="utf-8")

        result_payload["module_count"] = len(module_htmls)
        return result_payload
    except Exception as exc:
        return error_response(
            "generate_report_failed",
            str(exc),
            data_dir=str(data_dir),
            runtime_module="cst_runtime.render.dashboard",
        )