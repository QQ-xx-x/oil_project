# -*- coding: utf-8 -*-
"""射孔文件的前端解析器。"""

import math
import os
import re


PERFORATION_COLUMNS = ("WELLNAME", "MD1", "MD2")
PERFORATION_ENCODINGS = ("utf-8-sig", "gb18030", "utf-16")


def parse_perforation_file(path):
    """解析 WELLNAME/MD1/MD2 射孔文件并保留记录顺序和显示精度。"""

    resolved_path = os.path.abspath(str(path or "").strip())
    if not resolved_path or not os.path.isfile(resolved_path):
        raise ValueError("射孔文件不存在。")

    text, encoding = _read_text(resolved_path)
    payload = parse_perforation_text(text, source_path=resolved_path)
    payload["encoding"] = encoding
    return payload


def parse_perforation_text(text, source_path=""):
    """解析以空格、制表符或逗号分隔的射孔文本。"""

    source_path = os.path.abspath(source_path) if source_path else ""
    meaningful = [
        (line_number, line.strip())
        for line_number, line in enumerate(str(text or "").splitlines(), 1)
        if line.strip() and not line.lstrip().startswith(("#", "//"))
    ]
    if not meaningful:
        raise ValueError("射孔文件为空。")

    header_line_number, header_line = meaningful[0]
    headers = [token.upper() for token in _split_fields(header_line)]
    missing = [
        column for column in PERFORATION_COLUMNS if column not in headers
    ]
    if missing:
        raise ValueError(
            f"射孔文件表头缺少字段：{', '.join(missing)}。"
            f"需要包含：{', '.join(PERFORATION_COLUMNS)}。")
    if len(headers) != len(set(headers)):
        raise ValueError(f"射孔文件第 {header_line_number} 行存在重复表头。")

    indexes = {
        column: headers.index(column) for column in PERFORATION_COLUMNS
    }
    rows = []
    well_names = set()
    for line_number, line in meaningful[1:]:
        fields = _split_fields(line)
        if len(fields) != len(headers):
            raise ValueError(
                f"射孔文件第 {line_number} 行包含 {len(fields)} 个字段，"
                f"应为 {len(headers)} 个。")

        well_name = fields[indexes["WELLNAME"]].strip()
        if not well_name:
            raise ValueError(f"射孔文件第 {line_number} 行井名为空。")

        numeric = {}
        display = {}
        for column in ("MD1", "MD2"):
            raw_value = fields[indexes[column]].strip()
            try:
                number = float(raw_value)
            except ValueError as exc:
                raise ValueError(
                    f"射孔文件第 {line_number} 行 {column} 不是有效数值："
                    f"{raw_value}。") from exc
            if not math.isfinite(number):
                raise ValueError(
                    f"射孔文件第 {line_number} 行 {column} 不是有限数值。")
            numeric[column.lower()] = number
            display[f"{column.lower()}_text"] = raw_value

        well_names.add(well_name)
        rows.append({
            "well_name": well_name,
            "source_line": line_number,
            **numeric,
            **display,
        })

    if not rows:
        raise ValueError("射孔文件中没有有效射孔数据。")

    return {
        "source_path": source_path,
        "file_name": os.path.basename(source_path) if source_path else "",
        "columns": list(PERFORATION_COLUMNS),
        "rows": rows,
        "summary": {
            "perforation_count": len(rows),
            "well_count": len(well_names),
        },
    }


def _read_text(path):
    with open(path, "rb") as stream:
        raw = stream.read()
    for encoding in PERFORATION_ENCODINGS:
        try:
            return raw.decode(encoding), encoding
        except UnicodeError:
            continue
    raise UnicodeError("射孔文件编码无法识别，请使用 UTF-8 或 GB18030 编码。")


def _split_fields(line):
    return [
        token for token in re.split(r"[\s,]+", str(line or "").strip())
        if token
    ]


__all__ = [
    "PERFORATION_COLUMNS",
    "parse_perforation_file",
    "parse_perforation_text",
]
