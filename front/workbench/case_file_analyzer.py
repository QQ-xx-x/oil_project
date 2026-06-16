# -*- coding: utf-8 -*-
"""分析 CaseData 输入文件中引用的外部数据文件。

具体格式解析交给算法侧提供的标准模块 ``front.uniform_parser``，
本模块只负责整理前端展示需要的摘要、校验和预览文本。
"""

import csv
import os
from dataclasses import dataclass, field

from front.uniform_parser import (
    filter_active_values,
    parse_dfn,
    parse_grid,
    parse_property,
)


@dataclass
class FileAnalysis:
    path: str
    file_type: str = "text"
    exists: bool = False
    size: int = 0
    summary: dict = field(default_factory=dict)
    validation: list = field(default_factory=list)
    errors: list = field(default_factory=list)

    def summary_text(self):
        lines = [
            f"文件类型: {self.file_type}",
            f"文件存在: {'是' if self.exists else '否'}",
            f"文件大小: {self.size} bytes",
        ]
        if self.errors:
            lines.append("")
            lines.append("错误:")
            lines.extend(f"- {item}" for item in self.errors)
        if self.summary:
            lines.append("")
            lines.append("解析摘要:")
            lines.extend(_format_mapping(self.summary))
        return "\n".join(lines)

    def validation_text(self):
        if not self.validation:
            return "暂无校验信息。"
        return "\n".join(self.validation)


def analyze_case_file(path, keyword_key="", null_value=99999):
    analysis = FileAnalysis(path=path)
    if not path:
        analysis.errors.append("文件路径为空")
        return analysis
    if not os.path.exists(path):
        analysis.errors.append("文件不存在")
        return analysis

    analysis.exists = True
    analysis.size = os.path.getsize(path)
    analysis.file_type = detect_file_type(path, keyword_key)

    try:
        if analysis.file_type == "grid":
            _analyze_grid_file(path, analysis)
        elif analysis.file_type == "dfn_geometry":
            _analyze_dfn_file(path, analysis)
        elif analysis.file_type == "property_array":
            _analyze_property_array(path, analysis, null_value)
        elif analysis.file_type == "csv":
            _analyze_csv_file(path, analysis)
        else:
            analysis.summary["说明"] = "普通文本文件，仅提供原始预览。"
    except Exception as exc:
        analysis.errors.append(f"解析失败: {exc}")
    return analysis


def detect_file_type(path, keyword_key=""):
    name = os.path.basename(path).lower()
    key = (keyword_key or "").lower()
    if name == "grid.inc" or key == "grid_file":
        return "grid"
    if name == "dfn.txt" or key == "fracture_file":
        return "dfn_geometry"
    if name.endswith(".csv"):
        return "csv"
    if name.endswith(".txt") and (
        key.endswith("_file")
        or name.startswith(("matrix_", "dfn_"))
        or name in {"sigma.txt", "actnum.txt"}
    ):
        return "property_array"
    return "text"


def read_text_preview(path, max_lines=200):
    if not path:
        return "文件路径为空。"
    if not os.path.exists(path):
        return f"文件不存在:\n{path}"
    lines = []
    try:
        with open(path, "r", encoding="utf-8-sig", errors="replace") as file:
            for index, line in enumerate(file, start=1):
                if index > max_lines:
                    lines.append(f"\n... 已截断，仅显示前 {max_lines} 行 ...")
                    break
                lines.append(line.rstrip("\n"))
    except OSError as exc:
        return f"文件读取失败:\n{exc}"
    if not lines:
        return "文件为空。"
    return "\n".join(lines)


def read_expanded_array_preview(path, grid_path=None, null_value=99999):
    """返回预览页使用的展开属性数组文本。

    如果提供了 grid_path，则只显示 ACTNUM == 1 且 value != null_value 的值，
    与前端有效值展示规则保持一致。
    """
    try:
        values = parse_property(path)
        actnum = None
        if grid_path and os.path.exists(grid_path):
            actnum = parse_grid(grid_path).get("actnum") or None
    except Exception as exc:
        return f"属性数组解析失败:\n{exc}"

    if not values:
        return "未解析到属性数组数值。"

    if actnum:
        valid_count = len(filter_active_values(values, actnum, float(null_value)))
        lines = [
            "展开属性数组（已按 ACTNUM==1 且 value!=99999 过滤）",
            f"原始数量: {len(values)}",
            f"ACTNUM 数量: {len(actnum)}",
            f"显示有效数量: {valid_count}",
            "",
        ]
        limit = min(len(values), len(actnum))
        for index in range(limit):
            if actnum[index] == 1 and not _is_null(values[index], null_value):
                lines.append(f"{index:>10}: {_format_number(values[index])}")
        return "\n".join(lines)

    lines = ["展开属性数组", f"总数量: {len(values)}", ""]
    lines.extend(
        f"{index:>10}: {_format_number(value)}"
        for index, value in enumerate(values)
    )
    return "\n".join(lines)


def analyze_property_against_grid(property_path, grid_path, null_value=99999):
    """将属性数组与网格维度和 ACTNUM 做联合校验。"""
    values = parse_property(property_path)
    grid = parse_grid(grid_path)
    actnum = grid.get("actnum") or []
    filtered = filter_active_values(values, actnum, float(null_value))
    limit = min(len(values), len(actnum))
    inactive_skipped = 0
    active_null = 0
    active_valid = 0
    for index in range(limit):
        if actnum[index] != 1:
            inactive_skipped += 1
        elif _is_null(values[index], null_value):
            active_null += 1
        else:
            active_valid += 1

    return {
        "property_count": len(values),
        "grid_total_cell_count": grid.get("total_cell_count"),
        "actnum_count": len(actnum),
        "active_cell_count": grid.get("active_cell_count"),
        "inactive_cell_count": grid.get("inactive_cell_count"),
        "inactive_skipped_count": inactive_skipped,
        "active_null_count": active_null,
        "active_valid_count": active_valid,
        "display_value_count": len(filtered),
        "display_min": min(filtered) if filtered else None,
        "display_max": max(filtered) if filtered else None,
        "length_mismatch": len(values) != len(actnum),
    }


def _analyze_property_array(path, analysis, null_value):
    values = parse_property(path)
    null_count = 0
    zero_count = 0
    nonzero_count = 0
    valid_values = []

    for value in values:
        if _is_null(value, null_value):
            null_count += 1
            continue
        valid_values.append(value)
        if value == 0:
            zero_count += 1
        else:
            nonzero_count += 1

    first_values = ", ".join(_format_number(item) for item in values[:20])
    analysis.summary.update({
        "总值数量": len(values),
        "Null 数量": null_count,
        "0 值数量": zero_count,
        "非零有效值数量": nonzero_count,
        "有效最小值": min(valid_values) if valid_values else None,
        "有效最大值": max(valid_values) if valid_values else None,
        "前 20 个展开值": first_values,
    })
    if not values:
        analysis.validation.append("未解析到属性数组数值。")
    else:
        analysis.validation.append("属性数组解析完成。")


def _analyze_grid_file(path, analysis):
    grid = parse_grid(path)
    nx = grid.get("nx")
    ny = grid.get("ny")
    nz = grid.get("nz")
    total = grid.get("total_cell_count")
    coord_count = len(grid.get("coord") or [])
    zcorn_count = len(grid.get("zcorn") or [])
    actnum_count = len(grid.get("actnum") or [])
    active_count = grid.get("active_cell_count")
    inactive_count = grid.get("inactive_cell_count")

    stats = {
        "nx": nx,
        "ny": ny,
        "nz": nz,
        "total_cell_count": total,
        "coord_value_count": coord_count,
        "zcorn_value_count": zcorn_count,
        "actnum_value_count": actnum_count,
        "active_cell_count": active_count,
        "inactive_cell_count": inactive_count,
    }
    analysis.summary.update(stats)
    _add_grid_validation(analysis, stats)


def _add_grid_validation(analysis, stats):
    nx, ny, nz = stats.get("nx"), stats.get("ny"), stats.get("nz")
    if not all(isinstance(item, int) and item > 0 for item in (nx, ny, nz)):
        analysis.validation.append("未解析到有效 SPECGRID。")
        return
    total = nx * ny * nz
    expected_coord = 6 * (nx + 1) * (ny + 1)
    expected_zcorn = 8 * total
    checks = [
        ("COORD", stats["coord_value_count"], expected_coord),
        ("ZCORN", stats["zcorn_value_count"], expected_zcorn),
        ("ACTNUM", stats["actnum_value_count"], total),
    ]
    for name, actual, expected in checks:
        state = "通过" if actual == expected else "不匹配"
        analysis.validation.append(f"{name}: {actual} / {expected} ({state})")
    activity_total = (stats.get("active_cell_count") or 0) + (stats.get("inactive_cell_count") or 0)
    state = "通过" if activity_total == total else "不匹配"
    analysis.validation.append(f"active + inactive: {activity_total} / {total} ({state})")


def _analyze_dfn_file(path, analysis):
    dfn = parse_dfn(path)
    fractures = dfn.get("fractures") or []
    vertex_distribution = {}
    for fracture in fractures:
        count = fracture.get("vertex_count")
        vertex_distribution[count] = vertex_distribution.get(count, 0) + 1

    analysis.summary.update({
        "fracture_count": dfn.get("fracture_count"),
        "parsed_fracture_count": len(fractures),
        "node_count": dfn.get("node_count"),
        "property_count": dfn.get("property_count"),
        "properties": _join_named_items(dfn.get("properties") or [], "name"),
        "sets": _join_named_items(dfn.get("sets") or [], "set_name"),
        "顶点数分布": ", ".join(
            f"{key}: {value}" for key, value in sorted(vertex_distribution.items())
        ),
        "bbox_min": dfn.get("bbox_min"),
        "bbox_max": dfn.get("bbox_max"),
    })
    expected = dfn.get("fracture_count")
    actual = len(fractures)
    state = "通过" if expected == actual else "不匹配"
    analysis.validation.append(f"fracture_count: {actual} / {expected} ({state})")


def _analyze_csv_file(path, analysis):
    row_count = 0
    preview_rows = []
    with open(path, "r", encoding="utf-8-sig", newline="", errors="replace") as file:
        reader = csv.DictReader(file)
        fieldnames = reader.fieldnames or []
        for row in reader:
            row_count += 1
            if len(preview_rows) < 5:
                preview_rows.append(row)
    analysis.summary.update({
        "列数": len(fieldnames),
        "列名": ", ".join(fieldnames),
        "数据行数": row_count,
        "前 5 行": str(preview_rows),
    })
    analysis.validation.append("CSV 表格读取完成。")


def _join_named_items(items, key):
    return "; ".join(str(item.get(key, "")) for item in items if item.get(key))


def _is_null(value, null_value):
    return abs(float(value) - float(null_value)) < 1e-12


def _format_number(value):
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return f"{value:.12g}"


def _format_mapping(mapping):
    return [f"{key}: {value}" for key, value in mapping.items()]
