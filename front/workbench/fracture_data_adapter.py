# -*- coding: utf-8 -*-
"""从井完井业务数据派生人工裂缝展示与计算参数。"""

import copy
import math


def derive_hydraulic_fractures(well_values):
    """从 PERF 定义中提取人工裂缝，并关联其 OPEN/SHUT 历史。

    ``well_values`` 既可以是模块完整值（包含 ``wells``），也可以直接是
    ``wells`` 业务字典。人工裂缝以 ``well_name + comp_id`` 唯一标识，
    调度事件仅用于计算状态，不会生成重复裂缝。
    """

    wells = _wells_payload(well_values)
    completions = _completion_rows(wells)
    event_rows = {}
    for row in completions:
        key = _completion_key(row)
        if not all(key):
            continue
        event_rows.setdefault(key, []).append(row)

    records = []
    seen = set()
    for row in completions:
        if str(row.get("event") or "").strip().upper() != "PERF":
            continue
        if not _is_true(row.get("is_fractured")) or not _is_true(
                row.get("connect_fracture")):
            continue
        key = _completion_key(row)
        if not all(key) or key in seen:
            continue
        fracture = row.get("fracture") or {}
        corners = _normalized_corners(fracture.get("corners") or [])
        if not corners:
            continue
        seen.add(key)

        center = {
            axis: sum(corner[axis] for corner in corners) / len(corners)
            for axis in ("x_m", "y_m", "z_m")
        }
        length, height = _fracture_dimensions(corners)
        history = _event_history(event_rows.get(key) or [])
        frac_id = _integer_or_value(row.get("frac_id"))
        records.append({
            "fracture_id": str(row.get("comp_id") or "").strip(),
            "comp_id": str(row.get("comp_id") or "").strip(),
            "frac_id": frac_id,
            "well_name": str(row.get("well_name") or "").strip(),
            "stage": frac_id + 1 if isinstance(frac_id, int) and frac_id >= 0 else frac_id,
            "md_top_m": _finite_number(row.get("md_top_m")),
            "md_bottom_m": _finite_number(row.get("md_bottom_m")),
            "center_x": center["x_m"],
            "center_y": center["y_m"],
            "center_z": center["z_m"],
            "length": length,
            "height": height,
            "aperture": _finite_number(fracture.get("aperture_m")),
            "perm": _finite_number(fracture.get("perm_mD")),
            "conductivity": _finite_number(
                fracture.get("conductivity_mD_m")),
            "corners": copy.deepcopy(corners),
            "events": history,
            "status": _current_status(history),
            "definition_date": _finite_number(
                row.get("date_day", row.get("date"))),
            "source_row": row.get("source_row"),
        })

    records.sort(key=lambda item: (
        item.get("well_name", ""),
        _sort_number(item.get("frac_id")),
        item.get("fracture_id", ""),
    ))
    return records


def hydraulic_fracture_summary(records):
    """汇总人工裂缝数量、关联井和当前启闭状态。"""

    rows = list(records or [])
    wells = {
        str(row.get("well_name") or "").strip()
        for row in rows if isinstance(row, dict)
    } - {""}
    return {
        "fracture_count": len(rows),
        "well_count": len(wells),
        "open_count": sum(
            1 for row in rows if row.get("status") == "开启"),
        "shut_count": sum(
            1 for row in rows if row.get("status") == "关闭"),
    }


def _wells_payload(values):
    payload = values if isinstance(values, dict) else {}
    nested = payload.get("wells")
    return nested if isinstance(nested, dict) else payload


def _completion_rows(wells):
    """兼容界面业务结构和 ``parse_wells`` 的原始嵌套结构。"""

    rows = [
        row for row in wells.get("completions") or []
        if isinstance(row, dict)
    ]
    if rows:
        return rows

    flattened = []
    for well in wells.get("wells") or []:
        if not isinstance(well, dict):
            continue
        definitions = {
            str(item.get("comp_id") or ""): item
            for item in well.get("completion_definitions") or []
            if isinstance(item, dict)
        }
        for definition in definitions.values():
            row = copy.deepcopy(definition)
            row.update({
                "event": "PERF",
                "date": row.get("date_day"),
            })
            flattened.append(row)
        for event in well.get("events") or []:
            if not isinstance(event, dict):
                continue
            definition = definitions.get(
                str(event.get("comp_id") or ""), {})
            row = copy.deepcopy(definition)
            row.update(copy.deepcopy(event))
            row["date"] = event.get("date_day")
            flattened.append(row)
    flattened.sort(key=lambda row: (
        _sort_number(row.get("date_day", row.get("date"))),
        _sort_number(row.get("source_row")),
    ))
    return flattened


def _completion_key(row):
    return (
        str(row.get("well_name") or "").strip(),
        str(row.get("comp_id") or "").strip(),
    )


def _normalized_corners(corners):
    normalized = []
    for index, corner in enumerate(corners):
        if not isinstance(corner, dict):
            continue
        coordinates = {
            axis: _finite_number(corner.get(axis))
            for axis in ("x_m", "y_m", "z_m")
        }
        if any(value is None for value in coordinates.values()):
            continue
        normalized.append({
            "corner_id": corner.get("corner_id", index + 1),
            **coordinates,
        })
    return normalized


def _fracture_dimensions(corners):
    if not corners:
        return None, None
    z_values = [corner["z_m"] for corner in corners]
    height = max(z_values) - min(z_values)
    horizontal_distances = []
    for index, first in enumerate(corners):
        for second in corners[index + 1:]:
            horizontal_distances.append(math.hypot(
                second["x_m"] - first["x_m"],
                second["y_m"] - first["y_m"],
            ))
    length = max(horizontal_distances) if horizontal_distances else 0.0
    return length, height


def _event_history(rows):
    ordered = sorted(rows, key=lambda row: (
        _sort_number(row.get("date_day", row.get("date"))),
        _sort_number(row.get("source_row")),
    ))
    labels = {
        "PERF": "定义",
        "OPEN": "开启",
        "SHUT": "关闭",
        "CONTROL": "控制调整",
    }
    return [{
        "date": _finite_number(row.get("date_day", row.get("date"))),
        "event": str(row.get("event") or "").strip().upper(),
        "event_label": labels.get(
            str(row.get("event") or "").strip().upper(),
            str(row.get("event") or "").strip()),
        "source_row": row.get("source_row"),
    } for row in ordered]


def _current_status(history):
    status = "已定义"
    for event in history:
        if event.get("event") == "OPEN":
            status = "开启"
        elif event.get("event") == "SHUT":
            status = "关闭"
    return status


def _finite_number(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _is_true(value):
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "open"}
    return bool(value)


def _integer_or_value(value):
    number = _finite_number(value)
    if number is None:
        return value
    if number.is_integer():
        return int(number)
    return number


def _sort_number(value):
    number = _finite_number(value)
    return number if number is not None else float("inf")
