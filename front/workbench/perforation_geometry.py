# -*- coding: utf-8 -*-
"""根据井轨迹计算射孔空间位置并生成前端人工裂缝几何。"""

import bisect
import copy
import math
import re


def calculate_perforation_geometry(perforation_payload, trajectory_payload):
    """把 WELLNAME/MD1/MD2 射孔区间映射到 DEV 井轨迹的 XYZ 坐标。"""

    perforations = [
        row for row in (perforation_payload or {}).get("rows") or []
        if isinstance(row, dict)
    ]
    tracks = _trajectory_index(trajectory_payload)
    counters = {}
    results = []
    success_count = 0

    for source_index, row in enumerate(perforations):
        well_name = str(row.get("well_name") or "").strip()
        counters[well_name] = counters.get(well_name, 0) + 1
        perforation_id = (
            f"{well_name or 'UNKNOWN'}-PERF-{counters[well_name]:03d}")
        result = {
            "perforation_id": perforation_id,
            "well_name": well_name,
            "source_index": source_index,
            "source_line": row.get("source_line"),
            "md1": row.get("md1"),
            "md2": row.get("md2"),
            "md1_text": row.get("md1_text"),
            "md2_text": row.get("md2_text"),
            "eligible_for_fracture": False,
        }

        try:
            md1 = _finite_number(row.get("md1"), "MD1")
            md2 = _finite_number(row.get("md2"), "MD2")
            if not well_name:
                raise ValueError("井名为空")
            if md1 >= md2:
                raise ValueError("MD1 必须小于 MD2")
            track = tracks.get(well_name)
            if track is None:
                raise ValueError("没有找到同名DEV井轨迹")
            start = interpolate_track_at_md(track, md1)
            end = interpolate_track_at_md(track, md2)
            center_md = 0.5 * (md1 + md2)
            center = interpolate_track_at_md(track, center_md)
        except (TypeError, ValueError) as exc:
            result.update({
                "status": "error",
                "status_text": str(exc) or "射孔位置无法计算",
            })
            results.append(result)
            continue

        chord_length = math.sqrt(sum(
            (end[key] - start[key]) ** 2
            for key in ("x_m", "y_m", "z_m")
        ))
        result.update({
            "md1": md1,
            "md2": md2,
            "center_md": center_md,
            "start_x": start["x_m"],
            "start_y": start["y_m"],
            "start_z": start["z_m"],
            "end_x": end["x_m"],
            "end_y": end["y_m"],
            "end_z": end["z_m"],
            "center_x": center["x_m"],
            "center_y": center["y_m"],
            "center_z": center["z_m"],
            "center_tvd": center.get("tvd_m"),
            "measured_length": md2 - md1,
            "spatial_chord_length": chord_length,
            "status": "success",
            "status_text": "计算成功",
            "eligible_for_fracture": True,
        })
        success_count += 1
        results.append(result)

    return {
        "method": "piecewise_linear_md_interpolation",
        "rows": results,
        "summary": {
            "source_count": len(perforations),
            "success_count": success_count,
            "error_count": len(perforations) - success_count,
            "well_count": len({
                row.get("well_name") for row in results
                if row.get("status") == "success"
            }),
        },
    }


def interpolate_track_at_md(track, measured_depth):
    """在按MD递增的轨迹点之间进行分段线性插值。"""

    rows = track.get("rows") if isinstance(track, dict) else track
    points = [
        row for row in rows or []
        if isinstance(row, dict)
        and all(_optional_finite(row.get(key)) is not None for key in (
            "md_m", "x_m", "y_m", "z_m"))
    ]
    if len(points) < 2:
        raise ValueError("井轨迹少于两个有效点")

    md_values = [float(point["md_m"]) for point in points]
    if not all(
            current < following
            for current, following in zip(md_values, md_values[1:])):
        raise ValueError("井轨迹MD必须严格递增")

    md = _finite_number(measured_depth, "MD")
    tolerance = 1e-9
    if md < md_values[0] - tolerance or md > md_values[-1] + tolerance:
        raise ValueError(
            f"MD {md:g} 超出轨迹范围 "
            f"[{md_values[0]:g}, {md_values[-1]:g}]")

    index = bisect.bisect_left(md_values, md)
    if index < len(points) and abs(md_values[index] - md) <= tolerance:
        return _point_coordinates(points[index])
    if index == 0 or index >= len(points):
        raise ValueError(f"MD {md:g} 无法在井轨迹中插值")

    first = points[index - 1]
    second = points[index]
    first_md = md_values[index - 1]
    second_md = md_values[index]
    fraction = (md - first_md) / (second_md - first_md)
    result = {
        key: float(first[key]) + fraction * (
            float(second[key]) - float(first[key]))
        for key in ("x_m", "y_m", "z_m")
    }
    first_tvd = _optional_finite(first.get("tvd_m"))
    second_tvd = _optional_finite(second.get("tvd_m"))
    if first_tvd is not None and second_tvd is not None:
        result["tvd_m"] = first_tvd + fraction * (
            second_tvd - first_tvd)
    return result


def build_hydraulic_fractures(calculated_rows, parameters):
    """以射孔中心为中心生成矩形人工裂缝四角点。"""

    selected = [
        row for row in calculated_rows or []
        if isinstance(row, dict)
        and row.get("status") == "success"
        and row.get("eligible_for_fracture")
    ]
    if not selected:
        raise ValueError("请选择至少一条计算成功的射孔记录。")

    normalized = _normalized_fracture_parameters(parameters)
    records = []
    for index, row in enumerate(selected):
        center = (
            _finite_number(row.get("center_x"), "中心X"),
            _finite_number(row.get("center_y"), "中心Y"),
            _finite_number(row.get("center_z"), "中心Z"),
        )
        corners = rectangle_fracture_corners(
            center=center,
            length=normalized["length"],
            height=normalized["height"],
            azimuth_deg=normalized["azimuth_deg"],
            dip_deg=normalized["dip_deg"],
        )
        source_id = str(row.get("perforation_id") or "").strip()
        fracture_id = f"{normalized['prefix']}-{source_id}"
        stage_match = re.search(r"(\d+)$", source_id)
        stage_number = (
            int(stage_match.group(1)) if stage_match else index + 1)
        records.append({
            "fracture_id": fracture_id,
            "comp_id": source_id,
            "frac_id": stage_number - 1,
            "well_name": str(row.get("well_name") or "").strip(),
            "stage": stage_number,
            "md_top_m": float(row["md1"]),
            "md_bottom_m": float(row["md2"]),
            "center_x": center[0],
            "center_y": center[1],
            "center_z": center[2],
            "length": normalized["length"],
            "height": normalized["height"],
            "azimuth_deg": normalized["azimuth_deg"],
            "dip_deg": normalized["dip_deg"],
            "aperture": normalized["aperture"],
            "perm": normalized["perm"],
            "conductivity": normalized["conductivity"],
            "corners": corners,
            "events": [],
            "status": "已定义",
            "definition_date": None,
            "source_type": "perforation_generated",
            "source_perforation_id": source_id,
            "source_row": row.get("source_line"),
        })
    return records


def rectangle_fracture_corners(
        center, length, height, azimuth_deg, dip_deg):
    """生成以方位角为走向、以倾角向下倾斜的矩形裂缝。"""

    cx, cy, cz = (float(value) for value in center)
    half_length = 0.5 * float(length)
    half_height = 0.5 * float(height)
    azimuth = math.radians(float(azimuth_deg))
    dip = math.radians(float(dip_deg))

    strike = (math.sin(azimuth), math.cos(azimuth), 0.0)
    dip_direction = (
        math.cos(azimuth) * math.cos(dip),
        -math.sin(azimuth) * math.cos(dip),
        -math.sin(dip),
    )
    corners = []
    for corner_id, (length_sign, height_sign) in enumerate(
            ((-1, -1), (1, -1), (1, 1), (-1, 1)), 1):
        corners.append({
            "corner_id": corner_id,
            "x_m": (
                cx
                + length_sign * half_length * strike[0]
                + height_sign * half_height * dip_direction[0]
            ),
            "y_m": (
                cy
                + length_sign * half_length * strike[1]
                + height_sign * half_height * dip_direction[1]
            ),
            "z_m": (
                cz
                + length_sign * half_length * strike[2]
                + height_sign * half_height * dip_direction[2]
            ),
        })
    return corners


def merge_generated_fractures(existing, generated, replace_duplicates=True):
    """按裂缝ID合并生成记录，返回 ``(结果, 新增数, 更新/跳过数)``。"""

    result = [copy.deepcopy(row) for row in existing or []
              if isinstance(row, dict)]
    positions = {
        str(row.get("fracture_id") or ""): index
        for index, row in enumerate(result)
    }
    added = 0
    affected = 0
    for row in generated or []:
        fracture_id = str(row.get("fracture_id") or "")
        if fracture_id in positions:
            affected += 1
            if replace_duplicates:
                result[positions[fracture_id]] = copy.deepcopy(row)
        else:
            positions[fracture_id] = len(result)
            result.append(copy.deepcopy(row))
            added += 1
    return result, added, affected


def _trajectory_index(payload):
    return {
        str(well.get("well_name") or "").strip(): well
        for well in (payload or {}).get("wells") or []
        if isinstance(well, dict)
        and str(well.get("well_name") or "").strip()
    }


def _point_coordinates(point):
    result = {
        key: float(point[key]) for key in ("x_m", "y_m", "z_m")
    }
    tvd = _optional_finite(point.get("tvd_m"))
    if tvd is not None:
        result["tvd_m"] = tvd
    return result


def _normalized_fracture_parameters(parameters):
    values = dict(parameters or {})
    prefix = re.sub(
        r"[^A-Za-z0-9_-]+", "-",
        str(values.get("prefix") or "").strip(),
    ).strip("-")
    if not prefix:
        raise ValueError("人工裂缝编号前缀不能为空。")

    normalized = {
        "prefix": prefix,
        "length": _finite_number(values.get("length"), "裂缝长度"),
        "height": _finite_number(values.get("height"), "裂缝高度"),
        "azimuth_deg": _finite_number(
            values.get("azimuth_deg"), "裂缝方位角"),
        "dip_deg": _finite_number(values.get("dip_deg"), "裂缝倾角"),
        "aperture": _finite_number(values.get("aperture"), "裂缝开度"),
        "perm": _finite_number(values.get("perm"), "裂缝渗透率"),
        "conductivity": _finite_number(
            values.get("conductivity"), "裂缝导流能力"),
    }
    for key, title in (
            ("length", "裂缝长度"),
            ("height", "裂缝高度"),
            ("aperture", "裂缝开度"),
            ("perm", "裂缝渗透率"),
            ("conductivity", "裂缝导流能力")):
        if normalized[key] <= 0.0:
            raise ValueError(f"{title}必须大于 0。")
    if not 0.0 <= normalized["azimuth_deg"] <= 360.0:
        raise ValueError("裂缝方位角必须位于 0 到 360 度。")
    if not 0.0 <= normalized["dip_deg"] <= 90.0:
        raise ValueError("裂缝倾角必须位于 0 到 90 度。")
    return normalized


def _finite_number(value, title):
    number = _optional_finite(value)
    if number is None:
        raise ValueError(f"{title}必须是有限数字")
    return number


def _optional_finite(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


__all__ = [
    "build_hydraulic_fractures",
    "calculate_perforation_geometry",
    "interpolate_track_at_md",
    "merge_generated_fractures",
    "rectangle_fracture_corners",
]
