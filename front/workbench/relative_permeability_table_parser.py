# -*- coding: utf-8 -*-
"""Sw/Krw/Krg 相渗表格的前端解析器。"""

import math
import os
import re


RELATIVE_PERMEABILITY_COLUMNS = ("SW", "KRW", "KRG")
RELATIVE_PERMEABILITY_ENCODINGS = ("utf-8-sig", "gb18030", "utf-16")


def parse_relative_permeability_file(path):
    """解析相渗表格文件，并保留原始行顺序与显示精度。"""

    resolved_path = os.path.abspath(str(path or "").strip())
    if not resolved_path or not os.path.isfile(resolved_path):
        raise ValueError("相渗表格文件不存在。")

    text, encoding = _read_text(resolved_path)
    payload = parse_relative_permeability_text(
        text, source_path=resolved_path)
    payload["encoding"] = encoding
    return payload


def parse_relative_permeability_text(text, source_path=""):
    """解析以空格、制表符或逗号分隔的 Sw/Krw/Krg 表格。"""

    source_path = os.path.abspath(source_path) if source_path else ""
    meaningful = [
        (line_number, line.strip())
        for line_number, line in enumerate(str(text or "").splitlines(), 1)
        if line.strip() and not line.lstrip().startswith(("#", "//", "--"))
    ]
    if not meaningful:
        raise ValueError("相渗表格文件为空。")

    header_line_number, header_line = meaningful[0]
    headers = [token.upper() for token in _split_fields(header_line)]
    missing = [
        column for column in RELATIVE_PERMEABILITY_COLUMNS
        if column not in headers
    ]
    if missing:
        raise ValueError(
            f"相渗表格表头缺少字段：{', '.join(missing)}。"
            f"需要包含：{', '.join(RELATIVE_PERMEABILITY_COLUMNS)}。")
    if len(headers) != len(set(headers)):
        raise ValueError(f"相渗表格第 {header_line_number} 行存在重复表头。")

    indexes = {
        column: headers.index(column)
        for column in RELATIVE_PERMEABILITY_COLUMNS
    }
    rows = []
    for line_number, line in meaningful[1:]:
        fields = _split_fields(line)
        if len(fields) != len(headers):
            raise ValueError(
                f"相渗表格第 {line_number} 行包含 {len(fields)} 个字段，"
                f"应为 {len(headers)} 个。")

        numeric = {}
        display = {}
        for column in RELATIVE_PERMEABILITY_COLUMNS:
            raw_value = fields[indexes[column]].strip()
            try:
                number = float(raw_value)
            except ValueError as exc:
                raise ValueError(
                    f"相渗表格第 {line_number} 行 {column} 不是有效数值："
                    f"{raw_value}。") from exc
            if not math.isfinite(number):
                raise ValueError(
                    f"相渗表格第 {line_number} 行 {column} 不是有限数值。")
            key = column.lower()
            numeric[key] = number
            display[f"{key}_text"] = raw_value

        if not 0.0 <= numeric["sw"] <= 1.0:
            raise ValueError(
                f"相渗表格第 {line_number} 行 SW 必须位于 0 到 1 之间。")
        for key, title in (("krw", "KRW"), ("krg", "KRG")):
            if not 0.0 <= numeric[key] <= 1.0:
                raise ValueError(
                    f"相渗表格第 {line_number} 行 {title} "
                    "必须位于 0 到 1 之间。")
        if rows and numeric["sw"] <= rows[-1]["sw"]:
            raise ValueError(
                f"相渗表格第 {line_number} 行 SW 必须严格大于上一行。")

        rows.append({
            **numeric,
            **display,
        })

    if len(rows) < 2:
        raise ValueError("相渗表格至少需要两行数据。")

    return {
        "source_path": source_path,
        "file_name": os.path.basename(source_path) if source_path else "",
        "columns": list(RELATIVE_PERMEABILITY_COLUMNS),
        "rows": rows,
        "summary": {
            "point_count": len(rows),
            "sw_min": rows[0]["sw"],
            "sw_max": rows[-1]["sw"],
        },
    }


def _read_text(path):
    with open(path, "rb") as stream:
        raw = stream.read()
    for encoding in RELATIVE_PERMEABILITY_ENCODINGS:
        try:
            return raw.decode(encoding), encoding
        except UnicodeError:
            continue
    raise UnicodeError(
        "相渗表格编码无法识别，请使用 UTF-8 或 GB18030 编码。")


def _split_fields(line):
    return [
        token for token in re.split(r"[\s,]+", str(line or "").strip())
        if token
    ]


__all__ = [
    "RELATIVE_PERMEABILITY_COLUMNS",
    "parse_relative_permeability_file",
    "parse_relative_permeability_text",
]
