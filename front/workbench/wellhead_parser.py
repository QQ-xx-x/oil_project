# -*- coding: utf-8 -*-
"""井位文件的前端解析器。"""

import math
import os
import re


WELLHEAD_COLUMNS = ("WELLNAME", "X", "Y", "KB")
WELLHEAD_ENCODINGS = ("utf-8-sig", "gb18030", "utf-16")


def parse_wellhead_file(path):
    """解析 WELLNAME/X/Y/KB 井位文件并保留原始显示精度。"""

    resolved_path = os.path.abspath(str(path or "").strip())
    if not resolved_path or not os.path.isfile(resolved_path):
        raise ValueError("井位文件不存在。")

    text, encoding = _read_text(resolved_path)
    payload = parse_wellhead_text(text, source_path=resolved_path)
    payload["encoding"] = encoding
    return payload


def parse_wellhead_text(text, source_path=""):
    """解析以空格、制表符或逗号分隔的井位文本。"""

    source_path = os.path.abspath(source_path) if source_path else ""
    meaningful = [
        (line_number, line.strip())
        for line_number, line in enumerate(str(text or "").splitlines(), 1)
        if line.strip() and not line.lstrip().startswith(("#", "//"))
    ]
    if not meaningful:
        raise ValueError("井位文件为空。")

    header_line_number, header_line = meaningful[0]
    headers = [token.upper() for token in _split_fields(header_line)]
    missing = [column for column in WELLHEAD_COLUMNS if column not in headers]
    if missing:
        raise ValueError(
            f"井位文件表头缺少字段：{', '.join(missing)}。"
            f"需要包含：{', '.join(WELLHEAD_COLUMNS)}。")
    if len(headers) != len(set(headers)):
        raise ValueError(f"井位文件第 {header_line_number} 行存在重复表头。")

    indexes = {column: headers.index(column) for column in WELLHEAD_COLUMNS}
    rows = []
    names = set()
    for line_number, line in meaningful[1:]:
        fields = _split_fields(line)
        if len(fields) != len(headers):
            raise ValueError(
                f"井位文件第 {line_number} 行包含 {len(fields)} 个字段，"
                f"应为 {len(headers)} 个。")

        well_name = fields[indexes["WELLNAME"]].strip()
        if not well_name:
            raise ValueError(f"井位文件第 {line_number} 行井名为空。")
        if well_name in names:
            raise ValueError(f"井位文件存在重复井名：{well_name}。")

        numeric = {}
        display = {}
        for column in ("X", "Y", "KB"):
            raw_value = fields[indexes[column]].strip()
            try:
                number = float(raw_value)
            except ValueError as exc:
                raise ValueError(
                    f"井位文件第 {line_number} 行 {column} 不是有效数值："
                    f"{raw_value}。") from exc
            if not math.isfinite(number):
                raise ValueError(
                    f"井位文件第 {line_number} 行 {column} 不是有限数值。")
            numeric[column.lower()] = number
            display[f"{column.lower()}_text"] = raw_value

        names.add(well_name)
        rows.append({
            "well_name": well_name,
            **numeric,
            **display,
        })

    if not rows:
        raise ValueError("井位文件中没有有效井位数据。")

    return {
        "source_path": source_path,
        "file_name": os.path.basename(source_path) if source_path else "",
        "columns": list(WELLHEAD_COLUMNS),
        "rows": rows,
        "summary": {
            "wellhead_count": len(rows),
        },
    }


def _read_text(path):
    with open(path, "rb") as stream:
        raw = stream.read()
    for encoding in WELLHEAD_ENCODINGS:
        try:
            return raw.decode(encoding), encoding
        except UnicodeError:
            continue
    raise UnicodeError("井位文件编码无法识别，请使用 UTF-8 或 GB18030 编码。")


def _split_fields(line):
    return [token for token in re.split(r"[\s,]+", str(line or "").strip()) if token]


__all__ = [
    "WELLHEAD_COLUMNS",
    "parse_wellhead_file",
    "parse_wellhead_text",
]
