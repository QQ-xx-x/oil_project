# -*- coding: utf-8 -*-
"""精简完井与井控 CSV 的独立前端解析器。"""

import csv
import io
import math
import os
import re


COMPLETION_CONTROL_COLUMNS = (
    "well_name",
    "well_type",
    "event",
    "comp_id",
    "date",
    "md_top_m",
    "md_bottom_m",
    "rw_m",
    "control_type",
    "bhp_bar",
    "target",
    "target_id",
)
COMPLETION_CONTROL_ENCODINGS = ("utf-8-sig", "gb18030", "utf-16")
WELL_EVENTS = {"PERF", "OPEN", "SHUT", "CONTROL"}
TARGET_ALIASES = {
    "": "none",
    "none": "none",
    "未连接": "none",
    "matrix": "matrix",
    "基质": "matrix",
    "fracture": "fracture",
    "裂缝": "fracture",
    "matrix_and_fracture": "matrix_and_fracture",
    "matrix+fracture": "matrix_and_fracture",
    "both": "matrix_and_fracture",
    "基质与裂缝": "matrix_and_fracture",
}


def parse_completion_control_file(
        path, generated_fractures=None, trajectory_payload=None):
    """解析独立完井 CSV，并用已生成裂缝补齐内部兼容数据。"""

    resolved_path = os.path.abspath(str(path or "").strip())
    if not resolved_path or not os.path.isfile(resolved_path):
        raise ValueError("完井与井控文件不存在。")

    text, encoding = _read_text(resolved_path)
    payload = parse_completion_control_text(
        text,
        source_path=resolved_path,
        generated_fractures=generated_fractures,
        trajectory_payload=trajectory_payload,
    )
    payload["encoding"] = encoding
    return payload


def parse_completion_control_text(
        text, source_path="", generated_fractures=None,
        trajectory_payload=None):
    """解析精简 CSV；裂缝几何和物性来自上游人工裂缝记录。"""

    source_path = os.path.abspath(source_path) if source_path else ""
    reader = csv.DictReader(io.StringIO(str(text or "")))
    if not reader.fieldnames:
        raise ValueError("完井与井控文件没有表头。")
    headers = [_clean_header(value) for value in reader.fieldnames]
    if len(headers) != len(set(headers)):
        raise ValueError("完井与井控文件存在重复表头。")
    missing = [
        column for column in COMPLETION_CONTROL_COLUMNS
        if column not in headers
    ]
    if missing:
        raise ValueError(
            "完井与井控文件表头缺少字段："
            f"{', '.join(missing)}。")
    reader.fieldnames = headers

    fracture_index = _generated_fracture_index(generated_fractures)
    trajectory_ranges = _trajectory_ranges(trajectory_payload)
    warnings = []
    rows = []
    definitions = {}
    active = set()
    counts = {event: 0 for event in WELL_EVENTS}

    for line_number, source_row in enumerate(reader, 2):
        raw = {
            str(key or "").strip(): str(value or "").strip()
            for key, value in source_row.items()
            if key is not None
        }
        if not any(raw.values()):
            continue
        row = _parse_row(raw, line_number)
        event = row["event"]
        key = (row["well_name"], row["comp_id"])

        if event == "PERF":
            if key in definitions:
                raise ValueError(
                    f"第 {line_number} 行重复定义完井段："
                    f"{row['well_name']} / {row['comp_id']}。")
            _validate_trajectory_range(
                row, trajectory_ranges, line_number)
            _link_generated_fracture(
                row, fracture_index, warnings, line_number)
            definitions[key] = row
        elif event in {"OPEN", "SHUT"}:
            if key not in definitions:
                raise ValueError(
                    f"第 {line_number} 行 {event} 找不到对应 PERF："
                    f"{row['well_name']} / {row['comp_id']}。")
            row = _inherit_definition(row, definitions[key])
            if event == "OPEN":
                if key in active:
                    raise ValueError(
                        f"第 {line_number} 行重复开启已开启的完井段："
                        f"{row['well_name']} / {row['comp_id']}。")
                active.add(key)
            else:
                if key not in active:
                    raise ValueError(
                        f"第 {line_number} 行关闭了尚未开启的完井段："
                        f"{row['well_name']} / {row['comp_id']}。")
                active.remove(key)

        counts[event] += 1
        rows.append(row)

    if not rows:
        raise ValueError("完井与井控文件中没有有效记录。")
    if not definitions:
        raise ValueError("完井与井控文件至少需要一条 PERF 定义。")

    well_names = {
        row["well_name"] for row in rows if row.get("well_name")
    }
    linked_count = sum(
        1 for row in definitions.values()
        if row.get("generated_fracture_id")
    )
    return {
        "schema_version": "completion_control_compact_v1",
        "source_path": source_path,
        "file_name": os.path.basename(source_path) if source_path else "",
        "columns": list(COMPLETION_CONTROL_COLUMNS),
        "rows": rows,
        "summary": {
            "record_count": len(rows),
            "well_count": len(well_names),
            "definition_count": counts["PERF"],
            "open_count": counts["OPEN"],
            "shut_count": counts["SHUT"],
            "control_count": counts["CONTROL"],
            "linked_fracture_count": linked_count,
            "warning_count": len(warnings),
        },
        "warnings": warnings,
    }


def _parse_row(raw, line_number):
    well_name = raw.get("well_name", "").strip()
    if not well_name:
        raise ValueError(f"第 {line_number} 行井名为空。")
    event = raw.get("event", "").strip().upper()
    if event not in WELL_EVENTS:
        raise ValueError(
            f"第 {line_number} 行 event 必须是 "
            "PERF、OPEN、SHUT 或 CONTROL。")
    comp_id = raw.get("comp_id", "").strip()
    if event != "CONTROL" and not comp_id:
        raise ValueError(f"第 {line_number} 行 comp_id 不能为空。")

    date = _number(raw.get("date"), "date", line_number, required=True)
    md_top = _number(raw.get("md_top_m"), "md_top_m", line_number)
    md_bottom = _number(raw.get("md_bottom_m"), "md_bottom_m", line_number)
    rw_m = _number(raw.get("rw_m"), "rw_m", line_number)
    bhp_bar = _number(raw.get("bhp_bar"), "bhp_bar", line_number)
    target_text = raw.get("target", "").strip().lower()
    if target_text not in TARGET_ALIASES:
        raise ValueError(
            f"第 {line_number} 行 target 必须是 "
            "matrix、fracture、matrix_and_fracture 或 none。")
    target = TARGET_ALIASES[target_text]
    target_id = raw.get("target_id", "").strip()

    if event == "PERF":
        if md_top is None or md_bottom is None or md_top >= md_bottom:
            raise ValueError(
                f"第 {line_number} 行 PERF 必须满足 "
                "md_top_m < md_bottom_m。")
        if rw_m is None or rw_m <= 0.0:
            raise ValueError(
                f"第 {line_number} 行 PERF 的 rw_m 必须大于零。")
        if bhp_bar is None or bhp_bar <= 0.0:
            raise ValueError(
                f"第 {line_number} 行 PERF 的 bhp_bar 必须大于零。")
        if target in {"fracture", "matrix_and_fracture"} and not target_id:
            raise ValueError(
                f"第 {line_number} 行裂缝连接必须填写 target_id。")

    return {
        "source_row": line_number,
        "well_name": well_name,
        "well_type": raw.get("well_type", "").strip().upper() or "PRODUCER",
        "event": event,
        "comp_id": comp_id,
        "date": date,
        "date_day": date,
        "md_top_m": md_top,
        "md_bottom_m": md_bottom,
        "depth_type": "MD",
        "rw_m": rw_m,
        "control_type": (
            raw.get("control_type", "").strip().upper() or "BHP"),
        "bhp_bar": bhp_bar,
        "target": target,
        "target_id": target_id,
        "connection_target": target,
        "is_fractured": target in {"fracture", "matrix_and_fracture"},
        "connect_matrix": target in {"matrix", "matrix_and_fracture"},
        "connect_fracture": target in {
            "fracture", "matrix_and_fracture"},
        "frac_id": None,
    }


def _number(value, field, line_number, required=False):
    text = str(value or "").strip()
    if not text:
        if required:
            raise ValueError(f"第 {line_number} 行 {field} 不能为空。")
        return None
    try:
        number = float(text)
    except ValueError as exc:
        raise ValueError(
            f"第 {line_number} 行 {field} 不是有效数字：{text}。") from exc
    if not math.isfinite(number):
        raise ValueError(f"第 {line_number} 行 {field} 必须是有限数字。")
    return number


def _generated_fracture_index(records):
    result = {}
    for row in records or []:
        if not isinstance(row, dict):
            continue
        for key in ("fracture_id", "comp_id", "source_perforation_id"):
            value = str(row.get(key) or "").strip()
            if value:
                result[value] = row
    return result


def _link_generated_fracture(row, fracture_index, warnings, line_number):
    if not row.get("connect_fracture"):
        row["frac_id"] = -1
        return
    target_id = str(row.get("target_id") or row.get("comp_id") or "").strip()
    fracture = fracture_index.get(target_id)
    if fracture is None:
        warnings.append(
            f"第 {line_number} 行 target_id={target_id} "
            "未匹配当前已生成的人工裂缝。")
        return
    row["frac_id"] = fracture.get("frac_id")
    row["generated_fracture_id"] = str(
        fracture.get("fracture_id") or target_id)


def _inherit_definition(event, definition):
    inherited = dict(event)
    for key in (
            "well_type", "md_top_m", "md_bottom_m", "depth_type", "rw_m",
            "target", "target_id", "connection_target", "is_fractured",
            "connect_matrix", "connect_fracture", "frac_id",
            "generated_fracture_id", "fracture"):
        if inherited.get(key) in (None, "", "none", False):
            inherited[key] = definition.get(key)
    if inherited.get("bhp_bar") is None:
        inherited["bhp_bar"] = definition.get("bhp_bar")
    return inherited


def _trajectory_ranges(payload):
    result = {}
    for well in (payload or {}).get("wells") or []:
        if not isinstance(well, dict):
            continue
        name = str(well.get("well_name") or "").strip()
        md_values = [
            float(row["md_m"])
            for row in well.get("rows") or []
            if isinstance(row, dict) and row.get("md_m") is not None
        ]
        if name and md_values:
            result[name] = (min(md_values), max(md_values))
    return result


def _validate_trajectory_range(row, ranges, line_number):
    if not ranges:
        return
    well_name = row["well_name"]
    if well_name not in ranges:
        raise ValueError(
            f"第 {line_number} 行井名 {well_name} "
            "在当前 DEV 井轨迹中不存在。")
    minimum, maximum = ranges[well_name]
    if (row["md_top_m"] < minimum - 1e-9
            or row["md_bottom_m"] > maximum + 1e-9):
        raise ValueError(
            f"第 {line_number} 行 MD 范围超出当前井轨迹 "
            f"[{minimum:g}, {maximum:g}]。")


def _clean_header(value):
    text = str(value or "").strip().replace("\ufeff", "").lower()
    aliases = {
        "well": "well_name",
        "wellname": "well_name",
        "type": "well_type",
        "day": "date",
        "connection_target": "target",
        "fracture_id": "target_id",
    }
    normalized = re.sub(r"[\s-]+", "_", text)
    return aliases.get(normalized, normalized)


def _read_text(path):
    with open(path, "rb") as stream:
        raw = stream.read()
    for encoding in COMPLETION_CONTROL_ENCODINGS:
        try:
            return raw.decode(encoding), encoding
        except UnicodeError:
            continue
    raise UnicodeError(
        "完井与井控文件编码无法识别，请使用 UTF-8 或 GB18030 编码。")


__all__ = [
    "COMPLETION_CONTROL_COLUMNS",
    "parse_completion_control_file",
    "parse_completion_control_text",
]
