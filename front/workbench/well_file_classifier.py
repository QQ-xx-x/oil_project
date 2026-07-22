# -*- coding: utf-8 -*-
"""根据 CSV 文件自身的表头字段识别配对的井数据文件。"""

import csv
import os


TRACK_HEADER_FIELDS = frozenset((
    "well_name", "md_m", "x_m", "y_m", "z_m",
))
COMPLETION_HEADER_FIELDS = frozenset((
    "well_name", "well_type", "event", "comp_id", "date",
    "is_fractured", "md_top_m", "md_bottom_m", "depth_type", "rw_m",
    "control_type", "bhp_bar", "connect_matrix", "connect_fracture",
    "frac_id",
))


def identify_well_file_roles(first_path, second_path):
    """Return ``(track_path, completion_path)`` regardless of selection order."""

    paths = [os.path.abspath(first_path), os.path.abspath(second_path)]
    if paths[0] == paths[1]:
        raise ValueError("请选择两个不同的井数据文件。")

    identified = {}
    for path in paths:
        fields = _csv_header_fields(path)
        matches = []
        if TRACK_HEADER_FIELDS.issubset(fields):
            matches.append("track")
        if COMPLETION_HEADER_FIELDS.issubset(fields):
            matches.append("completion")
        if not matches:
            raise ValueError(
                f"无法根据表头识别文件：{os.path.basename(path)}。"
                "井轨迹文件需包含 md_m、x_m、y_m、z_m；"
                "完井文件需包含 event、comp_id、md_top_m、md_bottom_m 等字段。"
            )
        if len(matches) > 1:
            raise ValueError(
                f"文件表头同时符合两种井数据类型，无法确定用途："
                f"{os.path.basename(path)}。"
            )
        role = matches[0]
        if role in identified:
            label = "井轨迹" if role == "track" else "完井与井控"
            raise ValueError(f"两个文件都被识别为{label}文件，请重新选择。")
        identified[role] = path

    if set(identified) != {"track", "completion"}:
        raise ValueError("必须同时选择一个井轨迹文件和一个完井与井控文件。")
    return identified["track"], identified["completion"]


def _csv_header_fields(path):
    if not os.path.isfile(path):
        raise ValueError(f"文件不存在：{path}")
    with open(path, "r", encoding="utf-8-sig", newline="") as source:
        reader = csv.reader(source)
        try:
            header = next(reader)
        except StopIteration as exc:
            raise ValueError(
                f"CSV文件没有表头：{os.path.basename(path)}。") from exc
    fields = {
        str(value or "").strip().replace("\ufeff", "")
        for value in header
        if str(value or "").strip()
    }
    if not fields:
        raise ValueError(f"CSV文件没有有效表头：{os.path.basename(path)}。")
    return fields


__all__ = [
    "COMPLETION_HEADER_FIELDS",
    "TRACK_HEADER_FIELDS",
    "identify_well_file_roles",
]
