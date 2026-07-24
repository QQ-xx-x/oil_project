# -*- coding: utf-8 -*-
"""Petrel DEV 井轨迹文件的前端解析器。"""

import math
import os
import re


DEV_ENCODINGS = ("utf-8-sig", "gb18030", "utf-16")
DEV_REQUIRED_COLUMNS = ("MD", "X", "Y", "Z", "TVD")
DEV_COLUMN_ALIASES = {
    "AZIMUTH": "AZIM",
    "INCLINATION": "INCL",
}
DEV_COLUMN_KEYS = {
    "MD": "md_m",
    "X": "x_m",
    "Y": "y_m",
    "Z": "z_m",
    "TVD": "tvd_m",
    "DX": "dx_m",
    "DY": "dy_m",
    "AZIM": "azim_deg",
    "INCL": "incl_deg",
    "DLS": "dls",
}


def parse_dev_file(path):
    """解析一口井的 Petrel ``.dev`` 轨迹文件。"""

    resolved_path = os.path.abspath(str(path or "").strip())
    if not resolved_path or not os.path.isfile(resolved_path):
        raise ValueError("井轨迹 DEV 文件不存在。")

    text, encoding = _read_text(resolved_path)
    payload = parse_dev_text(text, source_path=resolved_path)
    payload["encoding"] = encoding
    return payload


def parse_dev_files(paths):
    """解析多个 DEV 文件，并保证每个文件对应唯一井名。"""

    resolved_paths = [
        os.path.abspath(str(path or "").strip())
        for path in paths or []
        if str(path or "").strip()
    ]
    if not resolved_paths:
        raise ValueError("请选择至少一个井轨迹 DEV 文件。")

    wells = []
    names = set()
    for path in resolved_paths:
        well = parse_dev_file(path)
        well_name = str(well.get("well_name") or "").strip()
        if well_name in names:
            raise ValueError(f"选择的 DEV 文件中存在重复井名：{well_name}。")
        names.add(well_name)
        wells.append(well)

    return build_trajectory_payload(wells)


def build_trajectory_payload(wells, vertical_mode="elevation_z"):
    """把单井 DEV 解析结果整理为井轨迹页面使用的批量载荷。"""

    normalized = [
        dict(well) for well in wells or []
        if isinstance(well, dict) and (well.get("rows") or [])
    ]
    warning_count = sum(
        len(well.get("warnings") or []) for well in normalized)
    return {
        "format": "petrel_dev",
        "vertical_mode": (
            vertical_mode
            if vertical_mode in {"elevation_z", "tvd", "subsea_depth"}
            else "elevation_z"
        ),
        "source_paths": [
            str(well.get("source_path") or "") for well in normalized
        ],
        "wells": normalized,
        "summary": {
            "well_count": len(normalized),
            "track_point_count": sum(
                len(well.get("rows") or []) for well in normalized),
            "warning_count": warning_count,
        },
    }


def parse_dev_text(text, source_path=""):
    """解析 Petrel DEV 文本，保留原始列、精度和元数据。"""

    source_path = os.path.abspath(source_path) if source_path else ""
    lines = str(text or "").splitlines()
    if not any(line.strip() for line in lines):
        raise ValueError("井轨迹 DEV 文件为空。")

    metadata = _parse_metadata(lines)
    well_name = str(metadata.get("well_name") or "").strip()
    if not well_name:
        raise ValueError("井轨迹 DEV 文件头缺少 WELL NAME。")

    header_index = None
    headers = []
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        candidates = [
            DEV_COLUMN_ALIASES.get(token.upper(), token.upper())
            for token in re.split(r"\s+", stripped)
            if token
        ]
        if "MD" in candidates:
            header_index = index
            headers = candidates
            break
    if header_index is None:
        raise ValueError("井轨迹 DEV 文件中没有找到数据表头。")
    if len(headers) != len(set(headers)):
        raise ValueError("井轨迹 DEV 数据表头存在重复字段。")

    missing = [
        column for column in DEV_REQUIRED_COLUMNS if column not in headers
    ]
    if missing:
        raise ValueError(
            f"井轨迹 DEV 表头缺少字段：{', '.join(missing)}。"
            f"至少需要：{', '.join(DEV_REQUIRED_COLUMNS)}。")

    indexes = {
        column: headers.index(column)
        for column in DEV_COLUMN_KEYS if column in headers
    }
    rows = []
    previous_md = None
    for line_number, line in enumerate(lines[header_index + 1:],
                                       header_index + 2):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        fields = re.split(r"\s+", stripped)
        if len(fields) != len(headers):
            raise ValueError(
                f"井轨迹 DEV 第 {line_number} 行包含 {len(fields)} 个字段，"
                f"应为 {len(headers)} 个。")

        row = {
            "well_name": well_name,
            "source_line": line_number,
        }
        for column, column_index in indexes.items():
            raw_value = fields[column_index].strip()
            try:
                number = float(raw_value)
            except ValueError as exc:
                raise ValueError(
                    f"井轨迹 DEV 第 {line_number} 行 {column} "
                    f"不是有效数值：{raw_value}。") from exc
            if not math.isfinite(number):
                raise ValueError(
                    f"井轨迹 DEV 第 {line_number} 行 {column} "
                    "不是有限数值。")
            key = DEV_COLUMN_KEYS[column]
            row[key] = number
            row[f"{key}_text"] = raw_value

        md = row["md_m"]
        if previous_md is not None and md <= previous_md:
            raise ValueError(
                f"井轨迹 DEV 第 {line_number} 行 MD 必须严格大于上一行。")
        previous_md = md
        inclination = row.get("incl_deg")
        if inclination is not None and not 0.0 <= inclination <= 180.0:
            raise ValueError(
                f"井轨迹 DEV 第 {line_number} 行 INCL 必须位于 0 到 180 度。")
        azimuth = row.get("azim_deg")
        if azimuth is not None and not 0.0 <= azimuth <= 360.0:
            raise ValueError(
                f"井轨迹 DEV 第 {line_number} 行 AZIM 必须位于 0 到 360 度。")
        dls = row.get("dls")
        if dls is not None and dls < 0.0:
            raise ValueError(
                f"井轨迹 DEV 第 {line_number} 行 DLS 不能为负数。")
        rows.append(row)

    if len(rows) < 2:
        raise ValueError("井轨迹 DEV 至少需要两个有效轨迹点。")

    warnings = _quality_warnings(metadata, rows)
    tvd_z_errors = []
    kb = metadata.get("wellhead_kb")
    if kb is not None:
        tvd_z_errors = [
            abs(float(row["tvd_m"]) - (float(kb) - float(row["z_m"])))
            for row in rows
        ]
    summary = {
        "track_point_count": len(rows),
        "md_min": rows[0]["md_m"],
        "md_max": rows[-1]["md_m"],
        "z_min": min(row["z_m"] for row in rows),
        "z_max": max(row["z_m"] for row in rows),
        "incl_max": max(
            (row.get("incl_deg") for row in rows
             if row.get("incl_deg") is not None),
            default=None,
        ),
        "dls_max": max(
            (row.get("dls") for row in rows
             if row.get("dls") is not None),
            default=None,
        ),
        "tvd_z_max_error": max(tvd_z_errors) if tvd_z_errors else None,
        "tvd_z_consistent": (
            max(tvd_z_errors) <= 1e-3 if tvd_z_errors else None
        ),
    }
    return {
        "well_name": well_name,
        "source_path": source_path,
        "file_name": os.path.basename(source_path) if source_path else "",
        "columns": headers,
        "metadata": metadata,
        "rows": rows,
        "summary": summary,
        "warnings": warnings,
    }


def _parse_metadata(lines):
    metadata = {}
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("#"):
            continue
        content = stripped.lstrip("#").strip()
        upper = content.upper()
        if upper.startswith("WELL NAME:"):
            metadata["well_name"] = content.split(":", 1)[1].strip()
        elif upper.startswith("DEFINITIVE SURVEY:"):
            metadata["survey_name"] = content.split(":", 1)[1].strip()
        elif upper.startswith("WELL HEAD X-COORDINATE:"):
            metadata["wellhead_x"] = _leading_float(
                content.split(":", 1)[1])
        elif upper.startswith("WELL HEAD Y-COORDINATE:"):
            metadata["wellhead_y"] = _leading_float(
                content.split(":", 1)[1])
        elif upper.startswith("WELL DATUM"):
            metadata["wellhead_kb"] = _leading_float(
                content.split(":", 1)[1] if ":" in content else "")
        elif upper.startswith("WELL TYPE:"):
            metadata["well_type"] = content.split(":", 1)[1].strip()
        elif upper.startswith("XYZ TRACE IS GIVEN IN COORDINATE SYSTEM"):
            match = re.search(r"<([^>]*)>", content)
            metadata["coordinate_system"] = (
                match.group(1).strip() if match else content)
        elif upper.startswith("AZIMUTH REFERENCE"):
            metadata["azimuth_reference"] = content[
                len("AZIMUTH REFERENCE"):].strip(" :")
        elif upper.startswith("MD AND TVD ARE REFERENCED"):
            metadata["depth_reference"] = content
    return metadata


def _quality_warnings(metadata, rows):
    warnings = []
    coordinate_system = str(
        metadata.get("coordinate_system") or "").strip()
    if not coordinate_system or coordinate_system.upper() == "UNDEFINED":
        warnings.append("DEV 文件未定义 XYZ 坐标系。")
    azimuth_reference = str(
        metadata.get("azimuth_reference") or "").strip()
    if not azimuth_reference or azimuth_reference.upper() == "UNDEFINED":
        warnings.append("DEV 文件未定义方位角参考方向。")
    if rows[0]["md_m"] != 0.0:
        warnings.append("首个轨迹点 MD 不为 0。")

    x = metadata.get("wellhead_x")
    y = metadata.get("wellhead_y")
    kb = metadata.get("wellhead_kb")
    if None in (x, y, kb):
        warnings.append("DEV 文件头缺少完整的井口 X、Y 或 KB 信息。")
    else:
        first = rows[0]
        if (
                abs(first["x_m"] - float(x)) > 1e-3
                or abs(first["y_m"] - float(y)) > 1e-3
                or abs(first["z_m"] - float(kb)) > 1e-3):
            warnings.append("首个轨迹点与 DEV 文件头井口坐标不一致。")
        tvd_z_error = max(
            abs(float(row["tvd_m"]) - (float(kb) - float(row["z_m"])))
            for row in rows
        )
        if tvd_z_error > 1e-3:
            warnings.append("TVD 与 KB-Z 的关系存在超过 0.001 m 的偏差。")
    return warnings


def _leading_float(text):
    match = re.search(
        r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][-+]?\d+)?",
        str(text or ""),
    )
    return float(match.group(0)) if match else None


def _read_text(path):
    with open(path, "rb") as stream:
        raw = stream.read()
    for encoding in DEV_ENCODINGS:
        try:
            return raw.decode(encoding), encoding
        except UnicodeError:
            continue
    raise UnicodeError(
        "井轨迹 DEV 文件编码无法识别，请使用 UTF-8 或 GB18030 编码。")


__all__ = [
    "DEV_COLUMN_KEYS",
    "DEV_REQUIRED_COLUMNS",
    "build_trajectory_payload",
    "parse_dev_file",
    "parse_dev_files",
    "parse_dev_text",
]
