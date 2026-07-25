"""
统一几何渲染器。

负责模拟前预览和模拟后结果共用的几何渲染：
1. 角点网格预览；
2. 真实井轨迹预览；
3. 天然裂缝预览；
4. 人工裂缝几何预览。
"""

from __future__ import annotations

import copy
import importlib
import numpy as np
import pyvista as pv

from .pyvista_static_property_preview import StaticPropertyPreviewRenderer


PREVIEW_ENABLE_ANTI_ALIASING = True
PREVIEW_ENABLE_DEPTH_PEELING = True
PREVIEW_DEPTH_PEEL_COUNT = 100
PREVIEW_DEPTH_PEEL_OCCLUSION_RATIO = 0.0
PREVIEW_MAIN_LIGHT_INTENSITY = 1.6

PREVIEW_USE_GEOMETRY_OVERLAY = False

GRID_SHOW_SURFACE = True
GRID_SHOW_EDGES = True
GRID_SURFACE_COLOR = (1.0, 1.0, 1.0)
GRID_SURFACE_OPACITY = 0.6
GRID_EDGE_COLOR = (0.5, 0.5, 0.5)

GRID_EDGE_LINE_WIDTH = 1.0
GRID_RENDER_LINES_AS_TUBES = False

GRID_INTERNAL_EDGES_VISIBLE_DEFAULT = True

GRID_PROPERTY_FOCUS_MODE = True
GRID_PROPERTY_SURFACE_OPACITY = 0.0
GRID_PROPERTY_EDGE_OPACITY = 0.3
GRID_PROPERTY_RENDER_LINES_AS_TUBES = False

GRID_POINT_MERGE_TOLERANCE_RATIO = 1e-9
GRID_POINT_MERGE_ABSOLUTE_TOLERANCE = 1e-8

GRID_LINE_OFFSET_FACTOR = -2.0
GRID_LINE_OFFSET_UNITS = -2.0
GRID_SURFACE_OFFSET_FACTOR = 1.0
GRID_SURFACE_OFFSET_UNITS = 1.0

WELL_COLOR = (0.08, 0.24, 0.62)
WELL_RADIUS = 2.0
WELL_OPACITY = 1.0
WELL_TUBE_SIDES = 32
WELL_FALLBACK_LINE_WIDTH = 4.0
                        
PERFORATION_COLOR = (1.0, 0.82, 0.0)
PERFORATION_OPACITY = 1.0

# 兼容旧的“射孔整体显隐”开关。
PERFORATION_VISIBLE = True

# 射孔点与射孔段分别控制。射孔点位于每条计算成功 PERF 记录
# 的 MD 中心位置；射孔段沿 DEV 轨迹的 MD1～MD2 区间绘制。
PERFORATION_POINT_VISIBLE = True
PERFORATION_SEGMENT_VISIBLE = True

# 射孔点使用模型坐标中的真实三维球体显示。
# 默认球半径等于井筒半径，因此球直径与井筒直径一致；
# 修改井半径时，射孔球会按相同比例自动变化。
PERFORATION_POINT_RADIUS_MULTIPLIER = 0.4
PERFORATION_POINT_THETA_RESOLUTION = 16
PERFORATION_POINT_PHI_RESOLUTION = 16

# 旧常量名称保留用于兼容外部导入。实际渲染半径由
# WELL_RADIUS * PERFORATION_POINT_RADIUS_MULTIPLIER 动态计算。
PERFORATION_POINT_RADIUS = (
    WELL_RADIUS * PERFORATION_POINT_RADIUS_MULTIPLIER
)
PERFORATION_POINT_SIZE = PERFORATION_POINT_RADIUS

WELL_LABEL_FONT_SIZE = 10
WELL_LABEL_MIN_FONT_SIZE = 6
WELL_LABEL_MAX_FONT_SIZE = 26
WELL_LABEL_ZOOM_EXPONENT = 0.75
WELL_LABEL_TEXT_COLOR = (0.05, 0.05, 0.05)

WELL_LABEL_BACKGROUND_OPACITY = 0.0
WELL_LABEL_SHAPE_OPACITY = 0.0
WELL_LABEL_MARGIN = 0

WELL_LABEL_PIXEL_OFFSET_X = 0
WELL_LABEL_PIXEL_OFFSET_Y = 0
WELL_LABEL_OFFSET_SCENE_RATIO = 0.008
WELL_LABEL_OFFSET_RADIUS_MULTIPLIER = 4.0
                                   
WELL_THIN_RADIUS_SCENE_RATIO = 1.0e-3
WELL_THIN_LINE_MIN_WIDTH = 2.5
WELL_THIN_LINE_MAX_WIDTH = 10.0

WELL_LABEL_COLLISION_SCENE_RATIO = 0.015
WELL_LABEL_SPREAD_SCENE_RATIO = 0.018
WELL_LABEL_SPREAD_Z_SCENE_RATIO = 0.004
                                                
GEOMETRY_CLIPPING_MARGIN_RATIO = 0.01
GEOMETRY_CLIPPING_MIN_NEAR = 1.0e-3
GEOMETRY_CLIPPING_NEAR_FAR_RATIO = 1.0e-5
GEOMETRY_CLIPPING_WELL_RADIUS_MARGIN = 8.0

NATURAL_FRACTURE_COLOR = (0.0, 0.25, 0.4)
NATURAL_FRACTURE_EDGE_COLOR = (0.0, 0.15, 0.25)
HYDRAULIC_FRACTURE_COLOR = (0.72, 0.38, 0.38)
HYDRAULIC_FRACTURE_EDGE_COLOR = (0.54, 0.29, 0.29)
FRACTURE_OPACITY = 1.0
FRACTURE_SHOW_EDGES = False
FRACTURE_EDGE_LINE_WIDTH = 0

FRACTURE_LIGHTING = False
FRACTURE_SMOOTH_SHADING = False
FRACTURE_AMBIENT = 1.0
FRACTURE_DIFFUSE = 0.0
FRACTURE_SPECULAR = 0.0

GEOMETRY_Z_TOL_RATIO = 0.02
GEOMETRY_Z_LOCAL_DEPTH_TOL_RATIO = 0.10
GEOMETRY_Z_ABS_TOL = 1e-6


class GeometryPreviewRenderer:
    def __init__(self, host):
        self.host = host
        self.plotter = host.plotter

        self._configure_preview_scene()

        self._grid_helper = StaticPropertyPreviewRenderer(host)

        self.grid_actor = None

        
        
        self.grid_edge_actor = None
        self.grid_internal_edge_actor = None
        self.show_internal_grid_edges = bool(
            GRID_INTERNAL_EDGES_VISIBLE_DEFAULT
        )

        self.well_actors = []

        # 射孔段和射孔点分别保存，perforation_actors 作为兼容聚合列表。
        self.perforation_segment_actors = []
        self.perforation_point_actors = []
        self.perforation_actors = []

        self.well_label_actors = []

        # 每口井分别保存井筒、射孔段和射孔点 actor。
        # UI 可通过 set_well_visible(well_name, visible) 单独控制一口井。
        self._well_actor_groups = {}
        self._hidden_well_names = set()
        self._well_label_anchor_by_name = {}

        self.natural_fracture_actors = []
        self.hydraulic_fracture_actors = []

        self._last_sim_data = None

        
        self._scene_geometry_data = {
            "well_data": None,
            "perforation_data": None,
            "natural_fractures": [],
            "hydraulic_fractures": [],
        }
        self._scene_geometry_signature = None
        self._scene_geometry_revision = 0
        self._wells_render_revision = -1
        self._natural_fractures_render_revision = -1
        self._hydraulic_fractures_render_revision = -1

        self.well_color = tuple(WELL_COLOR)
        self.well_radius = float(WELL_RADIUS)
        self.perforation_color = tuple(PERFORATION_COLOR)

        # 射孔球默认与井筒等粗：球半径 = 井筒半径 × 比例。
        # 保留实际半径字段，兼容旧 UI 和外部代码读取。
        self.perforation_point_radius_multiplier = float(
            PERFORATION_POINT_RADIUS_MULTIPLIER
        )
        self.perforation_point_radius = float(
            self.well_radius
            * self.perforation_point_radius_multiplier
        )
        self.perforation_point_size = self.perforation_point_radius

        self.show_perforation_points = bool(
            PERFORATION_VISIBLE and PERFORATION_POINT_VISIBLE
        )
        self.show_perforation_segments = bool(
            PERFORATION_VISIBLE and PERFORATION_SEGMENT_VISIBLE
        )

        # 旧接口兼容值：只要射孔点或射孔段有一个被请求显示，就视为
        # 射孔整体处于开启状态。
        self.show_perforations = bool(
            self.show_perforation_points
            or self.show_perforation_segments
        )

        self.natural_fracture_color = tuple(NATURAL_FRACTURE_COLOR)
        self.natural_fracture_edge_color = tuple(NATURAL_FRACTURE_EDGE_COLOR)
        self.hydraulic_fracture_color = tuple(HYDRAULIC_FRACTURE_COLOR)
        self.hydraulic_fracture_edge_color = tuple(HYDRAULIC_FRACTURE_EDGE_COLOR)

        self.fracture_show_edges = bool(FRACTURE_SHOW_EDGES)
        self.fracture_edge_line_width = float(FRACTURE_EDGE_LINE_WIDTH)

        self._geometry_clipping_guard = False
        self._geometry_render_observer_ids = []
        self._scene_reference_length_cache = {}
        self._corner_grid_bounds_cache = {}
        self._well_label_reference_view_scale = None
        self._well_label_current_font_size = None
        self._well_label_points = []
        self._well_label_texts = []
        self._well_label_use_billboard = False
        self._well_labels_forced_hidden = False
        self._install_geometry_render_observers()

    @staticmethod
    def _normalize_color(color):
        if color is None:
            raise ValueError("颜色不能为空")

        if hasattr(color, "getRgbF"):
            values = color.getRgbF()
            color = values[:3]

        elif hasattr(color, "redF") and hasattr(color, "greenF") and hasattr(color, "blueF"):
            color = (
                color.redF(),
                color.greenF(),
                color.blueF(),
            )

        elif isinstance(color, str):
            value = color.strip()

            if value.startswith("#"):
                value = value[1:]

                if len(value) == 3:
                    value = "".join(ch * 2 for ch in value)

                if len(value) != 6:
                    raise ValueError("十六进制颜色必须是 #RGB 或 #RRGGBB")

                try:
                    color = tuple(
                        int(value[index:index + 2], 16) / 255.0
                        for index in (0, 2, 4)
                    )
                except ValueError as exc:
                    raise ValueError("无效的十六进制颜色") from exc
            else:
                try:
                    color = tuple(pv.Color(value).float_rgb)
                except Exception as exc:
                    raise ValueError(f"无法识别颜色: {color}") from exc

        try:
            values = np.asarray(color, dtype=np.float64).reshape(-1)
        except Exception as exc:
            raise ValueError("颜色必须是 QColor、颜色名称、十六进制字符串或 RGB 三元组") from exc

        if values.size < 3 or not np.isfinite(values[:3]).all():
            raise ValueError("颜色必须包含三个有限 RGB 分量")

        values = values[:3]

        if np.max(values) > 1.0:
            values = values / 255.0

        values = np.clip(values, 0.0, 1.0)

        return tuple(float(value) for value in values)

    def set_well_labels_forced_hidden(
        self,
        hidden,
        render_now=False,
    ):
        """剖面期间移除井名 actor；退出剖面后按保存的锚点重新创建。"""
        hidden = bool(hidden)
        was_hidden = bool(self._well_labels_forced_hidden)
        self._well_labels_forced_hidden = hidden

        if hidden:
            self._remove_actor_list(self.well_label_actors)
            self.well_label_actors = []
            self._well_label_use_billboard = False
            self._well_label_current_font_size = None
        elif (
            was_hidden
            and self.is_wells_visible()
            and self._well_label_points
            and self._well_label_texts
            and not self.well_label_actors
        ):
            self._rebuild_well_name_labels(
                font_size=self._current_well_label_font_size(),
            )

        if render_now:
            self._render()

        return True

    def are_well_labels_forced_hidden(self):
        """返回井名是否被剖面模式强制隐藏。"""
        return bool(self._well_labels_forced_hidden)

    @staticmethod
    def _geometry_signature_value(value):
        """把几何输入转换成可比较的轻量签名。"""
        if isinstance(value, np.ndarray):
            array = np.ascontiguousarray(value)
            return (
                "ndarray",
                tuple(int(v) for v in array.shape),
                str(array.dtype),
                hash(array.tobytes()),
            )

        if isinstance(value, np.generic):
            return GeometryPreviewRenderer._geometry_signature_value(
                value.item()
            )

        if isinstance(value, dict):
            return (
                "dict",
                tuple(
                    (
                        str(key),
                        GeometryPreviewRenderer._geometry_signature_value(
                            item
                        ),
                    )
                    for key, item in sorted(
                        value.items(),
                        key=lambda pair: str(pair[0]),
                    )
                ),
            )

        if isinstance(value, (list, tuple)):
            return (
                type(value).__name__,
                tuple(
                    GeometryPreviewRenderer._geometry_signature_value(item)
                    for item in value
                ),
            )

        if isinstance(value, (set, frozenset)):
            frozen = [
                GeometryPreviewRenderer._geometry_signature_value(item)
                for item in value
            ]
            return (
                type(value).__name__,
                tuple(sorted(frozen, key=repr)),
            )

        if isinstance(value, float):
            if np.isnan(value):
                return ("float", "nan")
            if np.isposinf(value):
                return ("float", "+inf")
            if np.isneginf(value):
                return ("float", "-inf")
            return ("float", float(value))

        if value is None or isinstance(
            value,
            (str, bytes, bool, int),
        ):
            return value

        return (
            type(value).__name__,
            repr(value),
        )

    @classmethod
    def _make_scene_geometry_signature(cls, scene_data):
        return cls._geometry_signature_value(
            {
                "well_data": scene_data.get("well_data"),
                "perforation_data": scene_data.get("perforation_data"),
                "natural_fractures": scene_data.get(
                    "natural_fractures",
                    [],
                ),
                "hydraulic_fractures": scene_data.get(
                    "hydraulic_fractures",
                    [],
                ),
            }
        )

    def get_scene_geometry_revision(self) -> int:
        return int(self._scene_geometry_revision)

    def wells_need_scene_refresh(self) -> bool:
        return (
            self.is_wells_visible()
            and self._wells_render_revision
            != self._scene_geometry_revision
        )

    def fractures_need_scene_refresh(self) -> bool:
        return (
            (
                self.is_natural_fractures_visible()
                and self._natural_fractures_render_revision
                != self._scene_geometry_revision
            )
            or (
                self.is_hydraulic_fractures_visible()
                and self._hydraulic_fractures_render_revision
                != self._scene_geometry_revision
            )
        )

    def _remember_sim_data(self, sim_data):
        if sim_data is None:
            return False

        self._last_sim_data = sim_data
        scene_data = {
            "well_data": self._resolved_well_data(
                sim_data
            ),
            "perforation_data": self._resolved_perforation_data(
                sim_data
            ),
            "natural_fractures": self._resolved_natural_fractures(
                sim_data
            ),
            "hydraulic_fractures": self._resolved_hydraulic_fractures(
                sim_data
            ),
        }

        signature = self._make_scene_geometry_signature(
            scene_data
        )
        changed = (
            signature
            != self._scene_geometry_signature
        )

        self._scene_geometry_data = scene_data
        self._scene_geometry_signature = signature

        if changed:
            self._scene_geometry_revision += 1

        return changed


    def _legacy_well_data(self, sim_data):
        """Return the legacy CaseDataset well payload, when available."""
        if sim_data is None:
            sim_data = self._last_sim_data

        well_data = getattr(
            sim_data,
            "parsed_well_data",
            None,
        )
        if isinstance(well_data, dict):
            return well_data

        well_data = getattr(
            self.host,
            "_parsed_well_data",
            None,
        )
        return (
            well_data
            if isinstance(well_data, dict)
            else None
        )

    @staticmethod
    def _wellhead_kb_by_name(sim_data):
        wellhead_data = getattr(
            sim_data,
            "wellhead",
            None,
        )
        if not isinstance(wellhead_data, dict):
            return {}

        result = {}
        for row in wellhead_data.get("rows", []) or []:
            if not isinstance(row, dict):
                continue
            name = str(
                row.get("well_name")
                or row.get("name")
                or ""
            ).strip()
            try:
                kb = float(
                    row.get(
                        "kb",
                        row.get("wellhead_kb"),
                    )
                )
            except (TypeError, ValueError):
                continue
            if name and np.isfinite(kb):
                result[name.casefold()] = kb
        return result

    @staticmethod
    def _completion_identity(completion):
        if not isinstance(completion, dict):
            return None
        value = completion.get(
            "comp_id",
            completion.get("id"),
        )
        text = str(value or "").strip()
        return text.casefold() if text else None

    @classmethod
    def _merge_completion_definitions(
        cls,
        primary,
        secondary,
    ):
        result = [
            copy.deepcopy(item)
            for item in primary or []
            if isinstance(item, dict)
        ]
        seen = {
            identity
            for identity in (
                cls._completion_identity(item)
                for item in result
            )
            if identity
        }
        for item in secondary or []:
            if not isinstance(item, dict):
                continue
            identity = cls._completion_identity(item)
            if identity and identity in seen:
                continue
            result.append(copy.deepcopy(item))
            if identity:
                seen.add(identity)
        return result

    @staticmethod
    def _well_for_preview(
        well,
        wellhead_kb_by_name,
    ):
        if not isinstance(well, dict):
            return None

        result = copy.deepcopy(well)
        well_name = str(
            result.get("well_name")
            or result.get("name")
            or ""
        ).strip()
        result["well_name"] = well_name

        rows = result.get("rows")
        if not isinstance(rows, list) or not rows:
            rows = result.get("track", [])
        rows = [
            copy.deepcopy(row)
            for row in rows or []
            if isinstance(row, dict)
        ]

        metadata = result.get("metadata")
        metadata = (
            copy.deepcopy(metadata)
            if isinstance(metadata, dict)
            else {}
        )
        reference = metadata.get("wellhead_kb")
        try:
            reference = float(reference)
        except (TypeError, ValueError):
            reference = None
        if reference is None or not np.isfinite(reference):
            reference = wellhead_kb_by_name.get(
                well_name.casefold()
            )

        if reference is None or not np.isfinite(reference):
            reference_candidates = []
            for row in rows:
                try:
                    candidate = (
                        float(row["tvd_m"])
                        + float(row["z_m"])
                    )
                except (KeyError, TypeError, ValueError):
                    continue
                if np.isfinite(candidate):
                    reference_candidates.append(candidate)
            if reference_candidates:
                reference = float(
                    np.median(reference_candidates)
                )

        if reference is None or not np.isfinite(reference):
            z_values = []
            for row in rows:
                try:
                    value = float(row["z_m"])
                except (KeyError, TypeError, ValueError):
                    continue
                if np.isfinite(value):
                    z_values.append(value)
            if z_values:
                reference = float(max(z_values))

        if reference is not None and np.isfinite(reference):
            metadata["wellhead_kb"] = float(reference)
            for row in rows:
                try:
                    tvd = float(row.get("tvd_m"))
                except (TypeError, ValueError):
                    tvd = None
                if tvd is not None and np.isfinite(tvd):
                    continue
                try:
                    z = float(row["z_m"])
                except (KeyError, TypeError, ValueError):
                    continue
                if np.isfinite(z):
                    row["tvd_m"] = float(reference) - z

        result["metadata"] = metadata
        result["rows"] = rows
        return result

    def _resolved_well_data(self, sim_data):
        """
        Merge the current UI trajectory payload with legacy Dataset wells.

        The UI trajectory wins for duplicate well names.  Legacy-only wells
        are appended, while legacy completion definitions are retained so
        their artificial-fracture geometry can still be rendered.
        """
        if sim_data is None:
            sim_data = self._last_sim_data

        current = getattr(
            sim_data,
            "well_trajectory",
            None,
        )
        if not isinstance(current, dict):
            current = None
        legacy = self._legacy_well_data(
            sim_data
        )
        if current is None and legacy is None:
            return None

        payload = copy.deepcopy(
            current
            if current is not None
            else legacy
        )
        if not isinstance(payload, dict):
            payload = {}
        payload["vertical_mode"] = str(
            (
                current.get("vertical_mode")
                if current is not None
                else legacy.get("vertical_mode")
            )
            or "elevation_z"
        )

        wellhead_kb_by_name = (
            self._wellhead_kb_by_name(sim_data)
        )
        merged_wells = []
        well_index = {}

        for source in (current, legacy):
            if not isinstance(source, dict):
                continue
            for source_well in source.get("wells", []) or []:
                well = self._well_for_preview(
                    source_well,
                    wellhead_kb_by_name,
                )
                if well is None:
                    continue
                name = str(
                    well.get("well_name") or ""
                ).strip()
                key = name.casefold() if name else None

                if key is None or key not in well_index:
                    if key is not None:
                        well_index[key] = len(merged_wells)
                    merged_wells.append(well)
                    continue

                target = merged_wells[
                    well_index[key]
                ]
                if not target.get("rows") and well.get("rows"):
                    target["rows"] = copy.deepcopy(
                        well["rows"]
                    )
                    target["metadata"] = copy.deepcopy(
                        well.get("metadata") or {}
                    )
                target["completion_definitions"] = (
                    self._merge_completion_definitions(
                        target.get(
                            "completion_definitions",
                            [],
                        ),
                        well.get(
                            "completion_definitions",
                            [],
                        ),
                    )
                )

        payload["wells"] = merged_wells
        return payload if merged_wells else None

    def _resolved_perforation_data(self, sim_data):
        """只读取最新射孔页面载荷 sim_data.perforation。"""
        if sim_data is None:
            sim_data = self._last_sim_data

        data = getattr(
            sim_data,
            "perforation",
            None,
        )
        return data if isinstance(data, dict) else None


    @staticmethod
    def _fracture_record_points(fracture):
        if not isinstance(fracture, dict):
            return None

        raw = fracture.get(
            "vertices",
            fracture.get(
                "points",
                fracture.get(
                    "corners",
                    [],
                ),
            ),
        )

        if not isinstance(raw, (list, tuple)):
            return None

        points = []

        for item in raw:
            if isinstance(item, dict):
                try:
                    point = (
                        float(
                            item.get(
                                "x_m",
                                item.get("x"),
                            )
                        ),
                        float(
                            item.get(
                                "y_m",
                                item.get("y"),
                            )
                        ),
                        float(
                            item.get(
                                "z_m",
                                item.get("z"),
                            )
                        ),
                    )
                except (
                    TypeError,
                    ValueError,
                ):
                    continue
            else:
                try:
                    values = np.asarray(
                        item,
                        dtype=np.float64,
                    ).reshape(-1)
                except Exception:
                    continue

                if values.size < 3:
                    continue

                point = (
                    float(values[0]),
                    float(values[1]),
                    float(values[2]),
                )

            if np.isfinite(point).all():
                points.append(point)

        if len(points) < 3:
            return None

        return points


    @staticmethod
    def _fracture_record_is_hydraulic(fracture):
        if not isinstance(fracture, dict):
            return False

        try:
            flag = int(
                fracture.get(
                    "is_hydraulic",
                    0,
                )
            ) == 1
        except Exception:
            flag = False

        kind = str(
            fracture.get(
                "type",
                fracture.get(
                    "fracture_type",
                    "",
                ),
            )
        ).strip().lower()

        return bool(
            flag
            or kind in (
                "hydraulic",
                "artificial",
                "人工",
                "人工裂缝",
            )
        )


    @staticmethod
    def _fracture_record_signature(points):
        try:
            array = np.asarray(
                points,
                dtype=np.float64,
            ).reshape(-1, 3)
        except Exception:
            return None

        if array.shape[0] < 3:
            return None

        rounded = np.round(
            array,
            decimals=6,
        )
        order = np.lexsort(
            (
                rounded[:, 2],
                rounded[:, 1],
                rounded[:, 0],
            )
        )

        return tuple(
            tuple(float(value) for value in row)
            for row in rounded[order]
        )


    def _normalized_fracture_records(
        self,
        records,
        *,
        hydraulic,
    ):
        result = []
        seen = set()
        for fracture in records or []:
            if not isinstance(fracture, dict):
                continue
            if (
                self._fracture_record_is_hydraulic(
                    fracture
                )
                != bool(hydraulic)
            ):
                continue
            points = self._fracture_record_points(
                fracture
            )
            if points is None:
                continue
            signature = self._fracture_record_signature(
                points
            )
            if signature is None or signature in seen:
                continue
            seen.add(signature)
            result.append(
                {
                    **fracture,
                    "vertices": points,
                    "points": points,
                    "is_hydraulic": (
                        1 if hydraulic else 0
                    ),
                    "type": (
                        "hydraulic"
                        if hydraulic
                        else "natural"
                    ),
                }
            )
        return result


    def _resolved_natural_fractures(self, sim_data):

        if sim_data is None:
            sim_data = self._last_sim_data

        dfn_data = getattr(
            sim_data,
            "static_dfn_data",
            None,
        )
        candidates = []
        if isinstance(dfn_data, dict):
            static_fractures = dfn_data.get(
                "fractures",
                [],
            )

            if isinstance(static_fractures, list):
                candidates.extend(
                    static_fractures
                )
        return self._normalized_fracture_records(
            candidates,
            hydraulic=False,
        )

    def _completion_hydraulic_fractures(
        self,
        sim_data,
    ):
        well_data = self._resolved_well_data(
            sim_data
        )
        if not isinstance(well_data, dict):
            return []

        records = []
        for well in well_data.get("wells", []) or []:
            if not isinstance(well, dict):
                continue
            well_name = str(
                well.get("well_name")
                or well.get("name")
                or ""
            ).strip()
            for completion in (
                well.get(
                    "completion_definitions",
                    [],
                )
                or []
            ):
                if not isinstance(completion, dict):
                    continue
                if not completion.get(
                    "is_fractured",
                    False,
                ):
                    continue
                fracture_data = completion.get(
                    "fracture",
                )
                if not isinstance(fracture_data, dict):
                    continue
                if (
                    fracture_data.get(
                        "geometry_available"
                    )
                    is False
                ):
                    continue
                points = self._fracture_record_points(
                    {
                        "corners": fracture_data.get(
                            "corners",
                            [],
                        )
                    }
                )
                if points is None:
                    continue
                completion_id = completion.get(
                    "comp_id",
                    completion.get("id"),
                )
                records.append(
                    {
                        **copy.deepcopy(fracture_data),
                        "vertices": points,
                        "points": points,
                        "is_hydraulic": 1,
                        "type": "hydraulic",
                        "fracture_type": "artificial",
                        "source": "well_completion",
                        "well_name": well_name,
                        "completion_id": completion_id,
                        "fracture_id": completion_id,
                    }
                )
        return records

    def _resolved_hydraulic_fractures(
        self,
        sim_data,
    ):
        if sim_data is None:
            sim_data = self._last_sim_data
        records = getattr(
            sim_data,
            "generated_hydraulic_fractures",
            None,
        )
        candidates = []
        for fracture in (
            records
            if isinstance(records, list)
            else []
        ):
            if not isinstance(fracture, dict):
                continue
            candidates.append(
                {
                    **fracture,
                    "is_hydraulic": 1,
                    "type": "hydraulic",
                    "fracture_type": "artificial",
                }
            )
        candidates.extend(
            self._completion_hydraulic_fractures(
                sim_data
            )
        )
        return self._normalized_fracture_records(
            candidates,
            hydraulic=True,
        )


    def set_scene_data(
        self,
        sim_data,
        *,
        render_now=False,
    ):
        """
        设置预览/模拟共用的几何数据源。

        如果井、射孔或裂缝数据发生变化，当前已经显示的几何会立即
        使用新数据重建；没有显示的几何仍保持隐藏，不会被自动打开。
        """
        changed = self._remember_sim_data(
            sim_data
        )

        if changed:
            # _remember_sim_data 已经完成签名更新，这里直接使用缓存，
            # 避免对大型井/裂缝数组重复计算一次数据签名。
            self.refresh_changed_geometry(
                sim_data=None,
                render_now=False,
            )
        else:
            self.refresh_preview_stack(
                render_now=False,
            )

        if render_now:
            self._render()

        return dict(
            self._scene_geometry_data
        )

    def refresh_changed_geometry(
        self,
        sim_data=None,
        *,
        force=False,
        render_now=True,
    ):
        """立即刷新当前已经显示、且数据已经变化的井和裂缝。"""
        if sim_data is not None:
            self._remember_sim_data(sim_data)

        wells_refreshed = False
        fractures_refreshed = False

        if force or self.wells_need_scene_refresh():
            wells_refreshed = self._rebuild_visible_wells(
                sim_data
            )

        if force or self.fractures_need_scene_refresh():
            fractures_refreshed = self._rebuild_visible_fractures(
                sim_data
            )

        self.refresh_preview_stack(
            render_now=False,
        )
        self._apply_stable_geometry_clipping_range()

        if render_now:
            self._render()

        return {
            "wells_refreshed": bool(wells_refreshed),
            "fractures_refreshed": bool(fractures_refreshed),
        }


    def get_scene_geometry_data(self):
        return dict(
            self._scene_geometry_data
        )


    @staticmethod
    def uses_preview_geometry_only() -> bool:
        """井和裂缝是否严格只使用预览解析数据。"""
        return True


    def get_geometry_style(self):
        return {
            "well_color": self.well_color,
            "well_radius": self.well_radius,
            "perforation_color": self.perforation_color,
            "perforation_point_radius": self.perforation_point_radius,
            "perforation_point_radius_multiplier": (
                self.perforation_point_radius_multiplier
            ),
            # 兼容旧 UI 字段，数值语义为当前模型坐标半径。
            "perforation_point_size": self.perforation_point_radius,
            "show_perforations": self.show_perforations,
            "show_perforation_points": self.show_perforation_points,
            "show_perforation_segments": self.show_perforation_segments,
            "natural_fracture_color": self.natural_fracture_color,
            "natural_fracture_edge_color": self.natural_fracture_edge_color,
            "hydraulic_fracture_color": self.hydraulic_fracture_color,
            "hydraulic_fracture_edge_color": self.hydraulic_fracture_edge_color,
            "fracture_show_edges": self.fracture_show_edges,
            "fracture_edge_line_width": self.fracture_edge_line_width,
        }

    @staticmethod
    def _set_actor_color(actor, color):
        if actor is None:
            return

        try:
            prop = actor.GetProperty()

            if prop is not None:
                prop.SetColor(*color)
        except Exception:
            pass

    def _update_well_actor_colors(self):
        for actor in self.well_actors or []:
            self._set_actor_color(actor, self.well_color)

    def _update_perforation_actor_colors(self):
        for actor in self.perforation_actors or []:
            self._set_actor_color(
                actor,
                self.perforation_color,
            )

    @staticmethod
    def _set_actor_visibility(actor, visible):
        if actor is None:
            return False

        visible = bool(visible)

        try:
            actor.SetVisibility(visible)
            return True
        except Exception:
            pass

        try:
            actor.visibility = visible
            return True
        except Exception:
            return False

    def get_well_names(self):
        """返回当前井轨迹数据中的井名，顺序与导入顺序一致。"""
        well_data = self._scene_geometry_data.get("well_data")

        if not isinstance(well_data, dict):
            well_data = self._resolved_well_data(self._last_sim_data)

        names = []
        seen = set()

        if isinstance(well_data, dict):
            for well in well_data.get("wells", []) or []:
                if not isinstance(well, dict):
                    continue

                name = str(well.get("well_name") or "").strip()

                if name and name not in seen:
                    seen.add(name)
                    names.append(name)

        return names

    def is_well_visible(self, well_name):
        name = str(well_name or "").strip()
        if not name:
            return False
        return name not in self._hidden_well_names

    def get_well_visibility_map(self):
        return {
            name: self.is_well_visible(name)
            for name in self.get_well_names()
        }

    def _rebuild_visible_well_name_labels(self, font_size=None):
        self._remove_actor_list(self.well_label_actors)
        self.well_label_actors = []
        self._well_label_points = []
        self._well_label_texts = []
        self._well_label_use_billboard = False
        self._well_label_current_font_size = None
        if self._well_labels_forced_hidden:
            return False
        names = [
            name
            for name in self.get_well_names()
            if name not in self._hidden_well_names
            and name in self._well_label_anchor_by_name
        ]
        if not names:
            return False
        points = [
            np.asarray(
                self._well_label_anchor_by_name[name],
                dtype=np.float64,
            ).reshape(3).copy()
            for name in names
        ]
        points = self._spread_overlapping_well_label_points(
            self._last_sim_data,
            points,
        )
        self._well_label_points = [
            np.asarray(point, dtype=np.float64).reshape(3).copy()
            for point in points
        ]
        self._well_label_texts = list(names)
        label_actors = self._add_well_name_labels(
            well_head_points=self._well_label_points,
            well_names=self._well_label_texts,
            font_size=(
                font_size
                if font_size is not None
                else self._current_well_label_font_size()
            ),
        )
        if not label_actors:
            return False
        self.well_label_actors.extend(label_actors)
        self._well_label_use_billboard = any(
            getattr(actor, "GetTextProperty", None) is not None
            for actor in label_actors
        )
        self._well_label_current_font_size = int(
            font_size
            if font_size is not None
            else self._current_well_label_font_size()
        )
        self._ensure_well_name_labels_attached()
        return True

    def _sync_perforation_visibility_to_actors(self):
        """同步全局射孔开关，同时尊重每口井自己的显隐状态。"""
        grouped_actor_ids = set()

        for well_name, group in self._well_actor_groups.items():
            well_visible = well_name not in self._hidden_well_names

            for actor in group.get(
                "perforation_point_actors",
                [],
            ) or []:
                grouped_actor_ids.add(id(actor))
                self._set_actor_visibility(
                    actor,
                    well_visible and self.show_perforation_points,
                )

            for actor in group.get(
                "perforation_segment_actors",
                [],
            ) or []:
                grouped_actor_ids.add(id(actor))
                self._set_actor_visibility(
                    actor,
                    well_visible and self.show_perforation_segments,
                )

        # 兼容未归入单井分组的旧 actor。
        for actor in self.perforation_point_actors or []:
            if id(actor) not in grouped_actor_ids:
                self._set_actor_visibility(
                    actor,
                    self.show_perforation_points,
                )

        for actor in self.perforation_segment_actors or []:
            if id(actor) not in grouped_actor_ids:
                self._set_actor_visibility(
                    actor,
                    self.show_perforation_segments,
                )

        return True

    def is_perforation_points_visible(self):
        """返回 UI 请求的射孔点全局显隐状态。"""
        return bool(self.show_perforation_points)

    def are_perforation_points_visible(self):
        """兼容复数命名。"""
        return self.is_perforation_points_visible()

    def is_perforation_segments_visible(self):
        """返回 UI 请求的射孔段全局显隐状态。"""
        return bool(self.show_perforation_segments)

    def are_perforation_segments_visible(self):
        """兼容复数命名。"""
        return self.is_perforation_segments_visible()

    def get_perforation_visibility_state(self):
        """返回 UI 初始化按钮时使用的射孔显隐状态。"""
        return {
            "points": self.is_perforation_points_visible(),
            "segments": self.is_perforation_segments_visible(),
        }

    def set_perforation_points_visible(
        self,
        visible,
        render_now=True,
    ):
        visible = bool(visible)
        changed = (
            visible
            != self.show_perforation_points
        )
        self.show_perforation_points = visible
        self.show_perforations = bool(
            self.show_perforation_points
            or self.show_perforation_segments
        )
        self._sync_perforation_visibility_to_actors()
        self._sync_geometry_overlay_attachment()
        self._apply_stable_geometry_clipping_range()
        if render_now and changed:
            self._render()
        return changed

    def set_perforation_point_visible(
        self,
        visible,
        render_now=True,
    ):
        return self.set_perforation_points_visible(
            visible,
            render_now=render_now,
        )

    def toggle_perforation_points_visible(
        self,
        render_now=True,
    ):
        target = not self.show_perforation_points
        self.set_perforation_points_visible(
            target,
            render_now=render_now,
        )
        return target

    def set_perforation_segments_visible(
        self,
        visible,
        sim_data=None,
        render_now=True,
    ):
        visible = bool(visible)
        changed = (
            visible
            != self.show_perforation_segments
        )
        self.show_perforation_segments = visible
        self.show_perforations = bool(
            self.show_perforation_points
            or self.show_perforation_segments
        )

        rebuilt = False
        if changed:
            rebuilt = self._rebuild_visible_wells(
                sim_data
            )

        if not rebuilt:
            self._sync_perforation_visibility_to_actors()
            self._sync_geometry_overlay_attachment()
            self._apply_stable_geometry_clipping_range()

        if render_now and changed:
            self._render()

        return changed

    def set_perforation_segment_visible(
        self,
        visible,
        sim_data=None,
        render_now=True,
    ):
        return self.set_perforation_segments_visible(
            visible,
            sim_data=sim_data,
            render_now=render_now,
        )

    def toggle_perforation_segments_visible(
        self,
        sim_data=None,
        render_now=True,
    ):
        target = not self.show_perforation_segments
        self.set_perforation_segments_visible(
            target,
            sim_data=sim_data,
            render_now=render_now,
        )
        return target

    def set_well_visible(
        self,
        well_name,
        visible,
        render_now=True,
    ):
        name = str(well_name or "").strip()
        if not name:
            return False
        available_names = self.get_well_names()
        exact_name = next(
            (
                item
                for item in available_names
                if item == name
            ),
            None,
        )
        if exact_name is None:
            lowered = name.casefold()
            exact_name = next(
                (
                    item
                    for item in available_names
                    if item.casefold() == lowered
                ),
                None,
            )
        if exact_name is None:
            return False
        name = exact_name
        visible = bool(visible)
        if visible:
            self._hidden_well_names.discard(name)
        else:
            self._hidden_well_names.add(name)

        group = self._well_actor_groups.get(name) or {}
        for actor in group.get(
            "well_actors",
            [],
        ) or []:
            self._set_actor_visibility(
                actor,
                visible,
            )

        for actor in group.get(
            "perforation_segment_actors",
            [],
        ) or []:
            self._set_actor_visibility(
                actor,
                visible and self.show_perforation_segments,
            )

        for actor in group.get(
            "perforation_point_actors",
            [],
        ) or []:
            self._set_actor_visibility(
                actor,
                visible and self.show_perforation_points,
            )

        self._rebuild_visible_well_name_labels()
        self._sync_geometry_overlay_attachment()
        self._apply_stable_geometry_clipping_range()

        if render_now:
            self._render()

        return True

    def set_single_well_visible(
        self,
        well_name,
        visible,
        render_now=True,
    ):
        return self.set_well_visible(
            well_name,
            visible,
            render_now=render_now,
        )

    def toggle_well_visible(
        self,
        well_name,
        render_now=True,
    ):
        target_visible = not self.is_well_visible(well_name)

        if not self.set_well_visible(
            well_name,
            target_visible,
            render_now=render_now,
        ):
            return None

        return target_visible

    def set_well_visibility_map(
        self,
        visibility_by_name,
        render_now=True,
    ):
        if not isinstance(visibility_by_name, dict):
            return False

        changed = False

        for name, visible in visibility_by_name.items():
            changed = self.set_well_visible(
                name,
                visible,
                render_now=False,
            ) or changed

        if render_now and changed:
            self._render()

        return changed

    def _rebuild_visible_wells(self, sim_data=None):
        if not self.is_wells_visible():
            return False

        data = sim_data if sim_data is not None else self._last_sim_data

        if data is None:
            return False

        self.clear_wells(render_now=False)
        self.render_wells(
            data,
            render_now=False,
        )
        return True

    def _rebuild_visible_fractures(self, sim_data=None):
        natural_visible = self.is_natural_fractures_visible()
        hydraulic_visible = self.is_hydraulic_fractures_visible()

        if not natural_visible and not hydraulic_visible:
            return False

        data = sim_data if sim_data is not None else self._last_sim_data

        if data is None:
            return False

        self.clear_fractures(render_now=False)

        natural_count = 0
        hydraulic_count = 0

        if natural_visible:
            natural_count = self._render_natural_fractures(data)

        if hydraulic_visible:
            hydraulic_count = self._render_hydraulic_fractures(data)

        self._natural_fractures_render_revision = (
            self._scene_geometry_revision
            if natural_visible and natural_count > 0
            else -1
        )
        self._hydraulic_fractures_render_revision = (
            self._scene_geometry_revision
            if hydraulic_visible and hydraulic_count > 0
            else -1
        )

        self.refresh_preview_stack(render_now=False)
        return True

    def set_geometry_style(
        self,
        *,
        well_color=None,
        well_radius=None,
        perforation_color=None,
        perforation_point_radius=None,
        perforation_point_size=None,
        perforation_point_radius_multiplier=None,
        show_perforations=None,
        show_perforation_points=None,
        show_perforation_segments=None,
        fracture_color=None,
        natural_fracture_color=None,
        hydraulic_fracture_color=None,
        fracture_edge_color=None,
        natural_fracture_edge_color=None,
        hydraulic_fracture_edge_color=None,
        fracture_show_edges=None,
        fracture_edge_line_width=None,
        sim_data=None,
        render_now=True,
    ):
        self._remember_sim_data(sim_data)

        well_color_changed = False
        perforation_color_changed = False
        perforation_point_visibility_changed = False
        perforation_segment_visibility_changed = False
        perforation_point_geometry_changed = False
        well_geometry_changed = False
        fracture_style_changed = False

        if well_color is not None:
            value = self._normalize_color(well_color)
            well_color_changed = value != self.well_color
            self.well_color = value

        if well_radius is not None:
            value = float(well_radius)

            if not np.isfinite(value) or value <= 0.0:
                raise ValueError("井半径必须是大于 0 的有限数值")

            well_geometry_changed = not np.isclose(
                value,
                self.well_radius,
            )
            self.well_radius = value

            # 射孔球跟随井筒半径变化。只要井半径变化，
            # 同步更新球半径并重建射孔点 actor。
            followed_radius = float(
                self.well_radius
                * self.perforation_point_radius_multiplier
            )
            if not np.isclose(
                followed_radius,
                self.perforation_point_radius,
            ):
                perforation_point_geometry_changed = True
            self.perforation_point_radius = followed_radius
            self.perforation_point_size = followed_radius

        if perforation_color is not None:
            value = self._normalize_color(
                perforation_color
            )
            perforation_color_changed = (
                value != self.perforation_color
            )
            self.perforation_color = value
        if perforation_point_radius_multiplier is not None:
            multiplier = float(
                perforation_point_radius_multiplier
            )
            if not np.isfinite(multiplier) or multiplier <= 0.0:
                raise ValueError(
                    "射孔点半径比例必须是大于 0 的有限数值"
                )

            new_radius = float(
                self.well_radius * multiplier
            )
            perforation_point_geometry_changed = (
                perforation_point_geometry_changed
                or not np.isclose(
                    multiplier,
                    self.perforation_point_radius_multiplier,
                )
                or not np.isclose(
                    new_radius,
                    self.perforation_point_radius,
                )
            )
            self.perforation_point_radius_multiplier = multiplier
            self.perforation_point_radius = new_radius
            self.perforation_point_size = new_radius

        point_radius_value = (
            perforation_point_radius
            if perforation_point_radius is not None
            else perforation_point_size
        )

        if point_radius_value is not None:
            value = float(point_radius_value)

            if not np.isfinite(value) or value <= 0.0:
                raise ValueError(
                    "射孔点半径必须是大于 0 的有限数值"
                )

            # 兼容旧接口：外部仍可传绝对球半径。内部将其换算为
            # 相对井半径的比例，之后井半径变化时仍会同比例跟随。
            multiplier = float(
                value / max(self.well_radius, 1.0e-12)
            )
            perforation_point_geometry_changed = (
                perforation_point_geometry_changed
                or not np.isclose(
                    value,
                    self.perforation_point_radius,
                )
                or not np.isclose(
                    multiplier,
                    self.perforation_point_radius_multiplier,
                )
            )
            self.perforation_point_radius_multiplier = multiplier
            self.perforation_point_radius = value
            self.perforation_point_size = value

        if show_perforations is not None:
            value = bool(show_perforations)
            perforation_point_visibility_changed = (
                perforation_point_visibility_changed
                or value
                != self.show_perforation_points
            )
            perforation_segment_visibility_changed = (
                perforation_segment_visibility_changed
                or value
                != self.show_perforation_segments
            )
            self.show_perforation_points = value
            self.show_perforation_segments = value

        if show_perforation_points is not None:
            value = bool(show_perforation_points)
            perforation_point_visibility_changed = (
                perforation_point_visibility_changed
                or value
                != self.show_perforation_points
            )
            self.show_perforation_points = value

        if show_perforation_segments is not None:
            value = bool(show_perforation_segments)
            perforation_segment_visibility_changed = (
                perforation_segment_visibility_changed
                or value
                != self.show_perforation_segments
            )
            self.show_perforation_segments = value

        self.show_perforations = bool(
            self.show_perforation_points
            or self.show_perforation_segments
        )

        if fracture_color is not None:
            value = self._normalize_color(fracture_color)

            if (
                value != self.natural_fracture_color
                or value != self.hydraulic_fracture_color
            ):
                fracture_style_changed = True

            self.natural_fracture_color = value
            self.hydraulic_fracture_color = value

        if natural_fracture_color is not None:
            value = self._normalize_color(
                natural_fracture_color
            )
            fracture_style_changed = (
                fracture_style_changed
                or value
                != self.natural_fracture_color
            )
            self.natural_fracture_color = value

        if hydraulic_fracture_color is not None:
            value = self._normalize_color(
                hydraulic_fracture_color
            )
            fracture_style_changed = (
                fracture_style_changed
                or value
                != self.hydraulic_fracture_color
            )
            self.hydraulic_fracture_color = value

        if fracture_edge_color is not None:
            value = self._normalize_color(
                fracture_edge_color
            )

            if (
                value != self.natural_fracture_edge_color
                or value
                != self.hydraulic_fracture_edge_color
            ):
                fracture_style_changed = True

            self.natural_fracture_edge_color = value
            self.hydraulic_fracture_edge_color = value

        if natural_fracture_edge_color is not None:
            value = self._normalize_color(
                natural_fracture_edge_color
            )
            fracture_style_changed = (
                fracture_style_changed
                or value
                != self.natural_fracture_edge_color
            )
            self.natural_fracture_edge_color = value

        if hydraulic_fracture_edge_color is not None:
            value = self._normalize_color(
                hydraulic_fracture_edge_color
            )
            fracture_style_changed = (
                fracture_style_changed
                or value
                != self.hydraulic_fracture_edge_color
            )
            self.hydraulic_fracture_edge_color = value

        if fracture_show_edges is not None:
            value = bool(fracture_show_edges)
            fracture_style_changed = (
                fracture_style_changed
                or value
                != self.fracture_show_edges
            )
            self.fracture_show_edges = value

            if (
                value
                and fracture_edge_line_width is None
                and self.fracture_edge_line_width <= 0.0
            ):
                self.fracture_edge_line_width = 1.0
                fracture_style_changed = True

        if fracture_edge_line_width is not None:
            value = float(fracture_edge_line_width)

            if not np.isfinite(value) or value < 0.0:
                raise ValueError(
                    "裂缝边框宽度必须是大于等于 0 的有限数值"
                )

            fracture_style_changed = (
                fracture_style_changed
                or not np.isclose(
                    value,
                    self.fracture_edge_line_width,
                )
            )
            self.fracture_edge_line_width = value

        rebuilt = False

        # 射孔段显隐会改变井轨迹的颜色分段。关闭射孔段时必须
        # 重建为完整普通井筒，避免原射孔位置留下空白。
        if (
            well_geometry_changed
            or perforation_segment_visibility_changed
            or perforation_point_geometry_changed
        ):
            rebuilt = self._rebuild_visible_wells(
                sim_data
            ) or rebuilt
        elif well_color_changed:
            self._update_well_actor_colors()

        if perforation_color_changed:
            self._update_perforation_actor_colors()

        if (
            perforation_point_visibility_changed
            and not rebuilt
        ):
            self._sync_perforation_visibility_to_actors()
            self._sync_geometry_overlay_attachment()
            self._apply_stable_geometry_clipping_range()

        if fracture_style_changed:
            rebuilt = self._rebuild_visible_fractures(
                sim_data
            ) or rebuilt

        if render_now and (
            rebuilt
            or well_color_changed
            or perforation_color_changed
            or perforation_point_visibility_changed
            or perforation_segment_visibility_changed
            or perforation_point_geometry_changed
            or fracture_style_changed
        ):
            self._render()

        return self.get_geometry_style()

    def set_well_color(self, color, render_now=True):
        return self.set_geometry_style(
            well_color=color,
            render_now=render_now,
        )

    def set_well_radius(self, radius, sim_data=None, render_now=True):
        return self.set_geometry_style(
            well_radius=radius,
            sim_data=sim_data,
            render_now=render_now,
        )

    def set_perforation_color(
        self,
        color,
        render_now=True,
    ):
        return self.set_geometry_style(
            perforation_color=color,
            render_now=render_now,
        )

    def set_perforation_visible(
        self,
        visible,
        sim_data=None,
        render_now=True,
    ):
        return self.set_geometry_style(
            show_perforations=visible,
            sim_data=sim_data,
            render_now=render_now,
        )

    def set_perforation_point_radius(
        self,
        radius,
        sim_data=None,
        render_now=True,
    ):
        return self.set_geometry_style(
            perforation_point_radius=radius,
            sim_data=sim_data,
            render_now=render_now,
        )

    def set_perforation_point_radius_multiplier(
        self,
        multiplier,
        sim_data=None,
        render_now=True,
    ):
        """设置射孔球半径相对井筒半径的比例。

        multiplier=1.0 时，射孔球直径与井筒直径一致。
        """
        return self.set_geometry_style(
            perforation_point_radius_multiplier=multiplier,
            sim_data=sim_data,
            render_now=render_now,
        )

    def set_perforation_point_size(
        self,
        size,
        sim_data=None,
        render_now=True,
    ):
        return self.set_perforation_point_radius(
            size,
            sim_data=sim_data,
            render_now=render_now,
        )

    def set_fracture_style(
        self,
        *,
        color=None,
        edge_color=None,
        show_edges=None,
        edge_line_width=None,
        sim_data=None,
        render_now=True,
    ):
        return self.set_geometry_style(
            fracture_color=color,
            fracture_edge_color=edge_color,
            fracture_show_edges=show_edges,
            fracture_edge_line_width=edge_line_width,
            sim_data=sim_data,
            render_now=render_now,
        )

    def set_natural_fracture_style(
        self,
        *,
        color=None,
        edge_color=None,
        show_edges=None,
        edge_line_width=None,
        sim_data=None,
        render_now=True,
    ):
        return self.set_geometry_style(
            natural_fracture_color=color,
            natural_fracture_edge_color=edge_color,
            fracture_show_edges=show_edges,
            fracture_edge_line_width=edge_line_width,
            sim_data=sim_data,
            render_now=render_now,
        )

    def set_hydraulic_fracture_style(
        self,
        *,
        color=None,
        edge_color=None,
        show_edges=None,
        edge_line_width=None,
        sim_data=None,
        render_now=True,
    ):
        return self.set_geometry_style(
            hydraulic_fracture_color=color,
            hydraulic_fracture_edge_color=edge_color,
            fracture_show_edges=show_edges,
            fracture_edge_line_width=edge_line_width,
            sim_data=sim_data,
            render_now=render_now,
        )

    def _configure_preview_scene(self):
        try:
            render_window = getattr(self.plotter, "ren_win", None)

            if render_window is not None:
                render_window.SetAlphaBitPlanes(1)
                render_window.SetMultiSamples(0)
        except Exception:
            pass

        try:
            renderer = getattr(self.plotter, "renderer", None)

            if renderer is not None:
                renderer.SetUseDepthPeeling(True)
                renderer.SetMaximumNumberOfPeels(PREVIEW_DEPTH_PEEL_COUNT)
                renderer.SetOcclusionRatio(PREVIEW_DEPTH_PEEL_OCCLUSION_RATIO)
        except Exception:
            pass

        if PREVIEW_ENABLE_DEPTH_PEELING:
            try:
                self.plotter.enable_depth_peeling(
                    number_of_peels=PREVIEW_DEPTH_PEEL_COUNT,
                    occlusion_ratio=PREVIEW_DEPTH_PEEL_OCCLUSION_RATIO,
                )
            except TypeError:
                try:
                    self.plotter.enable_depth_peeling()
                except Exception:
                    pass
            except Exception:
                pass

        if PREVIEW_ENABLE_ANTI_ALIASING:
            try:
                self.plotter.enable_anti_aliasing("fxaa")
            except TypeError:
                try:
                    self.plotter.enable_anti_aliasing()
                except Exception:
                    pass
            except Exception:
                pass

        if PREVIEW_ENABLE_ANTI_ALIASING:
            try:
                renderer = getattr(self.plotter, "renderer", None)

                if renderer is not None and hasattr(renderer, "SetUseFXAA"):
                    renderer.SetUseFXAA(True)
            except Exception:
                pass

        try:
            renderer = getattr(
                self.host,
                "renderer",
                None,
            )

            if renderer is None:
                renderer = getattr(
                    self.plotter,
                    "renderer",
                    None,
                )

            if renderer is not None:
                lights = renderer.GetLights()

                if lights is not None:
                    light = lights.GetItemAsObject(0)

                    if light:
                        light.SetIntensity(
                            PREVIEW_MAIN_LIGHT_INTENSITY
                        )

        except Exception:
            pass

    def _install_geometry_render_observers(self):
        camera = getattr(
            self.plotter,
            "camera",
            None,
        )

        if (
            camera is not None
            and hasattr(camera, "AddObserver")
            and not getattr(
                self.host,
                "_geometry_preview_well_label_camera_observer_installed",
                False,
            )
        ):
            try:
                observer_id = camera.AddObserver(
                    "ModifiedEvent",
                    self._on_geometry_camera_modified,
                )
                self._geometry_render_observer_ids.append(
                    (
                        camera,
                        observer_id,
                    )
                )
                setattr(
                    self.host,
                    "_geometry_preview_well_label_camera_observer_installed",
                    True,
                )
            except Exception:
                pass

    def _on_geometry_camera_modified(self, *_args):
        if not self.well_label_actors:
            return

        if self._well_labels_forced_hidden:
            self.set_well_labels_forced_hidden(
                True,
                render_now=False,
            )
            return

        self._sync_well_name_labels_with_camera()

    def _on_geometry_render_start(self, *_args):
        if self._geometry_clipping_guard:
            return

        if not (
            self._geometry_top_actors()
            or self.well_label_actors
            or self._has_visible_preview_background()
        ):
            return

        self._ensure_well_name_labels_attached()

        if self._well_labels_forced_hidden:
            self.set_well_labels_forced_hidden(
                True,
                render_now=False,
            )
            return

        self._sync_well_name_labels_with_camera()

    def _camera_view_scale(self):
        camera = getattr(
            self.plotter,
            "camera",
            None,
        )

        if camera is None:
            return None

        try:
            if bool(camera.GetParallelProjection()):
                value = float(camera.GetParallelScale())
            else:
                position = np.asarray(
                    camera.GetPosition(),
                    dtype=np.float64,
                )
                focal_point = np.asarray(
                    camera.GetFocalPoint(),
                    dtype=np.float64,
                )
                distance = float(
                    np.linalg.norm(
                        position - focal_point
                    )
                )
                view_angle = float(
                    camera.GetViewAngle()
                )
                view_angle = float(
                    np.clip(
                        view_angle,
                        1.0e-3,
                        179.0,
                    )
                )
                value = distance * np.tan(
                    np.deg2rad(view_angle) * 0.5
                )
        except Exception:
            return None

        if not np.isfinite(value) or value <= 1.0e-12:
            return None

        return value

    @staticmethod
    def _well_label_text_property(actor):
        if actor is None:
            return None


        getter = getattr(
            actor,
            "GetTextProperty",
            None,
        )

        if getter is not None:
            try:
                text_property = getter()
            except Exception:
                text_property = None

            if text_property is not None:
                return text_property


        try:
            mapper = actor.GetMapper()
        except Exception:
            mapper = None

        if mapper is not None:
            for getter_name in (
                "GetLabelTextProperty",
                "GetTextProperty",
            ):
                getter = getattr(
                    mapper,
                    getter_name,
                    None,
                )

                if getter is None:
                    continue

                try:
                    text_property = getter()
                except Exception:
                    text_property = None

                if text_property is not None:
                    return text_property

        return None

    def _set_well_label_font_size(self, font_size):
        try:
            font_size = int(round(float(font_size)))
        except Exception:
            return False

        font_size = int(
            np.clip(
                font_size,
                WELL_LABEL_MIN_FONT_SIZE,
                WELL_LABEL_MAX_FONT_SIZE,
            )
        )

        if self._well_label_current_font_size == font_size:
            return False

        changed = False

        for actor in self.well_label_actors or []:
            text_property = self._well_label_text_property(
                actor
            )

            if text_property is None:
                continue

            try:
                text_property.SetFontSize(
                    font_size
                )

                
                
                modified = getattr(
                    text_property,
                    "Modified",
                    None,
                )
                if callable(modified):
                    modified()

                try:
                    mapper = actor.GetMapper()
                except Exception:
                    mapper = None

                if mapper is not None:
                    modified = getattr(
                        mapper,
                        "Modified",
                        None,
                    )
                    if callable(modified):
                        modified()

                modified = getattr(
                    actor,
                    "Modified",
                    None,
                )
                if callable(modified):
                    modified()

                changed = True
            except Exception:
                pass

        if changed:
            self._well_label_current_font_size = font_size

        return changed

    def _reset_well_label_zoom_reference(self):
        self._well_label_reference_view_scale = (
            self._camera_view_scale()
        )
        self._well_label_current_font_size = None
        self._set_well_label_font_size(
            WELL_LABEL_FONT_SIZE
        )

    def _update_well_label_font_size(self):
        if not self.well_label_actors:
            return False

        return self._set_well_label_font_size(
            self._current_well_label_font_size()
        )

    def _current_well_label_font_size(self):
        current_scale = self._camera_view_scale()

        if current_scale is None:
            return int(WELL_LABEL_FONT_SIZE)

        reference_scale = self._well_label_reference_view_scale

        if (
            reference_scale is None
            or not np.isfinite(reference_scale)
            or reference_scale <= 1.0e-12
        ):
            self._well_label_reference_view_scale = current_scale
            reference_scale = current_scale

        zoom_ratio = reference_scale / current_scale
        zoom_ratio = float(
            np.clip(
                zoom_ratio,
                1.0e-3,
                1.0e3,
            )
        )

        font_size = WELL_LABEL_FONT_SIZE * (
            zoom_ratio ** WELL_LABEL_ZOOM_EXPONENT
        )

        return int(
            np.clip(
                np.round(font_size),
                WELL_LABEL_MIN_FONT_SIZE,
                WELL_LABEL_MAX_FONT_SIZE,
            )
        )

    def _sync_well_name_labels_with_camera(self):
        if not self.well_label_actors:
            return False

        if self._well_labels_forced_hidden:
            self._remove_actor_list(self.well_label_actors)
            self.well_label_actors = []
            return False

        font_size = self._current_well_label_font_size()

        
        
        if self._well_label_use_billboard:
            return self._set_well_label_font_size(font_size)

        if self._well_label_current_font_size == font_size:
            return False

        return self._rebuild_well_name_labels(
            font_size=font_size,
        )

    def _well_name_label_point(
        self,
        sim_data,
        ordered_points,
    ):
        try:
            points = np.asarray(
                ordered_points,
                dtype=np.float64,
            ).reshape(-1, 3)
        except Exception:
            return None

        if points.shape[0] < 1:
            return None

        head = points[0].copy()

        if not np.isfinite(head).all():
            return None

        if points.shape[0] >= 2:
            first_segment = points[1] - head
            segment_length = float(
                np.linalg.norm(first_segment)
            )
        else:
            first_segment = None
            segment_length = 0.0

        if (
            first_segment is None
            or not np.isfinite(segment_length)
            or segment_length <= 1.0e-12
        ):
            direction = np.asarray(
                [0.0, 0.0, 1.0],
                dtype=np.float64,
            )
        else:
            
            
            direction = -first_segment / segment_length

        reference_length = self._scene_reference_length(
            sim_data,
            fallback_points=points,
        )
        offset_distance = max(
            reference_length * WELL_LABEL_OFFSET_SCENE_RATIO,
            float(self.well_radius)
            * WELL_LABEL_OFFSET_RADIUS_MULTIPLIER,
        )

        label_point = head + direction * offset_distance

        if not np.isfinite(label_point).all():
            return head.copy()

        return label_point

    def _spread_overlapping_well_label_points(
        self,
        sim_data,
        label_points,
    ):
        try:
            points = np.asarray(
                label_points,
                dtype=np.float64,
            ).reshape(-1, 3)
        except Exception:
            return label_points

        if points.shape[0] <= 1 or not np.isfinite(points).all():
            return [point.copy() for point in points]

        reference_length = self._scene_reference_length(
            sim_data,
            fallback_points=points,
        )
        collision_distance = max(
            reference_length * WELL_LABEL_COLLISION_SCENE_RATIO,
            float(self.well_radius) * 10.0,
        )
        spread_radius = max(
            reference_length * WELL_LABEL_SPREAD_SCENE_RATIO,
            float(self.well_radius) * 14.0,
        )
        z_step = max(
            reference_length * WELL_LABEL_SPREAD_Z_SCENE_RATIO,
            float(self.well_radius) * 4.0,
        )

        remaining = set(range(points.shape[0]))
        groups = []

        while remaining:
            seed = remaining.pop()
            group = [seed]
            queue = [seed]

            while queue:
                current = queue.pop()
                nearby = [
                    index
                    for index in remaining
                    if np.linalg.norm(points[index] - points[current])
                    <= collision_distance
                ]
                for index in nearby:
                    remaining.remove(index)
                    queue.append(index)
                    group.append(index)

            groups.append(group)

        adjusted = points.copy()

        for group in groups:
            count = len(group)
            if count <= 1:
                continue

            center = np.mean(points[group], axis=0)
            for local_index, source_index in enumerate(group):
                angle = (2.0 * np.pi * local_index) / count
                vertical_index = local_index - (count - 1) * 0.5
                adjusted[source_index] = center + np.asarray(
                    [
                        np.cos(angle) * spread_radius,
                        np.sin(angle) * spread_radius,
                        vertical_index * z_step,
                    ],
                    dtype=np.float64,
                )

        return [point.copy() for point in adjusted]

    def _has_visible_preview_background(self) -> bool:
        if self._actor_is_visible(self.grid_actor):
            return True

        if self._actor_is_visible(self.grid_edge_actor):
            return True

        if self._actor_is_visible(
            self.grid_internal_edge_actor
        ):
            return True

        static_preview = getattr(
            self.host,
            "static_property_preview",
            None,
        )

        if static_preview is None:
            return False

        for name in (
            "actor",
            "surface_actor",
            "property_actor",
            "layer_actor",
        ):
            actor = getattr(
                static_preview,
                name,
                None,
            )

            if self._actor_is_visible(actor):
                return True

        return False

    @staticmethod
    def _bounds_corners(bounds):
        if bounds is None or len(bounds) != 6:
            return None

        try:
            min_x, max_x, min_y, max_y, min_z, max_z = [
                float(value)
                for value in bounds
            ]
        except Exception:
            return None

        corners = np.asarray(
            [
                [x, y, z]
                for x in (min_x, max_x)
                for y in (min_y, max_y)
                for z in (min_z, max_z)
            ],
            dtype=np.float64,
        )

        if not np.isfinite(corners).all():
            return None

        return corners

    @staticmethod
    def _merge_bounds(*bounds_values):
        valid = []

        for bounds in bounds_values:
            if bounds is None or len(bounds) != 6:
                continue

            try:
                values = np.asarray(
                    bounds,
                    dtype=np.float64,
                ).reshape(6)
            except Exception:
                continue

            if not np.isfinite(values).all():
                continue

            if (
                values[1] < values[0]
                or values[3] < values[2]
                or values[5] < values[4]
            ):
                continue

            valid.append(values)

        if not valid:
            return None

        return (
            float(min(item[0] for item in valid)),
            float(max(item[1] for item in valid)),
            float(min(item[2] for item in valid)),
            float(max(item[3] for item in valid)),
            float(min(item[4] for item in valid)),
            float(max(item[5] for item in valid)),
        )

    def _visible_background_bounds(self):
        bounds_values = []

        for actor in (
            self.grid_actor,
            self.grid_edge_actor,
            self.grid_internal_edge_actor,
        ):
            if self._actor_is_visible(actor):
                bounds = self._actor_bounds(actor)

                if bounds is not None:
                    bounds_values.append(bounds)

        static_preview = getattr(
            self.host,
            "static_property_preview",
            None,
        )

        if static_preview is not None:
            for name in (
                "actor",
                "surface_actor",
                "property_actor",
                "layer_actor",
            ):
                actor = getattr(
                    static_preview,
                    name,
                    None,
                )

                if not self._actor_is_visible(actor):
                    continue

                bounds = self._actor_bounds(actor)

                if bounds is not None:
                    bounds_values.append(bounds)

        return self._merge_bounds(
            *bounds_values
        )

    def _visible_scene_bounds(self):
        geometry_bounds = (
            self.get_visible_geometry_bounds()
        )
        background_bounds = (
            self._visible_background_bounds()
        )

        return self._merge_bounds(
            geometry_bounds,
            background_bounds,
        )

    def _expanded_clipping_bounds(self, bounds):
        if bounds is None or len(bounds) != 6:
            return None

        try:
            values = np.asarray(
                bounds,
                dtype=np.float64,
            ).reshape(6)
        except Exception:
            return None

        if not np.isfinite(values).all():
            return None

        spans = np.asarray(
            [
                max(values[1] - values[0], 0.0),
                max(values[3] - values[2], 0.0),
                max(values[5] - values[4], 0.0),
            ],
            dtype=np.float64,
        )

        diagonal = float(
            np.linalg.norm(spans)
        )

        margin = max(
            diagonal * 1.0e-5,
            float(self.well_radius)
            * GEOMETRY_CLIPPING_WELL_RADIUS_MARGIN,
            GEOMETRY_CLIPPING_MIN_NEAR,
        )

        return (
            float(values[0] - margin),
            float(values[1] + margin),
            float(values[2] - margin),
            float(values[3] + margin),
            float(values[4] - margin),
            float(values[5] + margin),
        )

    def _apply_stable_scene_clipping_range(
        self,
        bounds=None,
    ) -> bool:
        if self._geometry_clipping_guard:
            return False

        if bounds is None:
            bounds = self._visible_scene_bounds()

        bounds = self._expanded_clipping_bounds(
            bounds
        )

        if bounds is None or len(bounds) != 6:
            return False

        try:
            bounds_array = np.asarray(
                bounds,
                dtype=np.float64,
            ).reshape(6)
        except Exception:
            return False

        if not np.isfinite(bounds_array).all():
            return False

        renderer = self._main_renderer()

        if renderer is None:
            return False

        try:
            camera = renderer.GetActiveCamera()
        except Exception:
            camera = getattr(
                self.plotter,
                "camera",
                None,
            )

        if camera is None:
            return False

        try:
            self._geometry_clipping_guard = True

            reset_ok = False

            try:
                renderer.ResetCameraClippingRange(
                    float(bounds_array[0]),
                    float(bounds_array[1]),
                    float(bounds_array[2]),
                    float(bounds_array[3]),
                    float(bounds_array[4]),
                    float(bounds_array[5]),
                )
                reset_ok = True
            except Exception:
                pass

            if not reset_ok:
                try:
                    renderer.ResetCameraClippingRange(
                        tuple(
                            float(value)
                            for value in bounds_array
                        )
                    )
                    reset_ok = True
                except Exception:
                    pass

            if not reset_ok:
                try:
                    self.plotter.reset_camera_clipping_range()
                    reset_ok = True
                except Exception:
                    return False

            try:
                near_value, far_value = (
                    camera.GetClippingRange()
                )
                near_value = float(near_value)
                far_value = float(far_value)
            except Exception:
                return False

            if (
                not np.isfinite(near_value)
                or not np.isfinite(far_value)
                or far_value <= 0.0
            ):
                return False

            spans = np.asarray(
                [
                    bounds_array[1] - bounds_array[0],
                    bounds_array[3] - bounds_array[2],
                    bounds_array[5] - bounds_array[4],
                ],
                dtype=np.float64,
            )

            scene_diagonal = max(
                float(np.linalg.norm(spans)),
                float(self.well_radius) * 2.0,
                GEOMETRY_CLIPPING_MIN_NEAR,
            )

            minimum_near = max(
                GEOMETRY_CLIPPING_MIN_NEAR,
                scene_diagonal * 1.0e-7,
                far_value
                * GEOMETRY_CLIPPING_NEAR_FAR_RATIO,
            )

            near_value = max(
                near_value,
                minimum_near,
            )
            far_value = max(
                far_value,
                near_value * 1.01,
            )

            camera.SetClippingRange(
                float(near_value),
                float(far_value),
            )

            main_renderer = self._main_renderer()
            overlay_renderer = getattr(
                self.host,
                "_geometry_preview_overlay_renderer",
                None,
            )

            if (
                overlay_renderer is not None
                and main_renderer is not None
            ):
                try:
                    overlay_renderer.SetActiveCamera(
                        main_renderer.GetActiveCamera()
                    )
                except Exception:
                    pass

            return True

        except Exception:
            return False

        finally:
            self._geometry_clipping_guard = False

    def _apply_stable_geometry_clipping_range(self) -> bool:
        return self._apply_stable_scene_clipping_range()

    def _reset_clipping_range_for_bounds(
        self,
        bounds,
    ) -> bool:
        return self._apply_stable_scene_clipping_range(
            bounds=bounds,
        )

    def _scene_reference_length(self, sim_data, fallback_points=None):
        cache_key = id(sim_data) if sim_data is not None else None

        if cache_key is not None:
            cached = self._scene_reference_length_cache.get(
                cache_key,
                None,
            )

            if cached is not None:
                return cached

        spans = None
        grid_data = getattr(
            sim_data,
            "static_grid_data",
            None,
        ) if sim_data is not None else None

        if isinstance(grid_data, dict):
            coord = grid_data.get(
                "coord",
                None,
            )

            try:
                coord_array = np.asarray(
                    coord,
                    dtype=np.float64,
                ).reshape(-1, 6)
                x_values = np.concatenate(
                    [
                        coord_array[:, 0],
                        coord_array[:, 3],
                    ]
                )
                y_values = np.concatenate(
                    [
                        coord_array[:, 1],
                        coord_array[:, 4],
                    ]
                )
                x_values = x_values[np.isfinite(x_values)]
                y_values = y_values[np.isfinite(y_values)]
                z_bounds = self._static_grid_z_bounds(
                    sim_data
                )

                if (
                    x_values.size > 0
                    and y_values.size > 0
                    and z_bounds is not None
                ):
                    spans = np.asarray(
                        [
                            float(np.max(x_values) - np.min(x_values)),
                            float(np.max(y_values) - np.min(y_values)),
                            float(z_bounds[1] - z_bounds[0]),
                        ],
                        dtype=np.float64,
                    )
            except Exception:
                spans = None

        if spans is None and fallback_points is not None:
            try:
                points = np.asarray(
                    fallback_points,
                    dtype=np.float64,
                ).reshape(-1, 3)
                finite_mask = np.isfinite(points).all(axis=1)
                points = points[finite_mask]

                if points.shape[0] > 0:
                    spans = np.ptp(
                        points,
                        axis=0,
                    )
            except Exception:
                spans = None

        if spans is None:
            reference_length = 1.0
        else:
            reference_length = float(
                np.linalg.norm(spans)
            )

            if not np.isfinite(reference_length) or reference_length <= 0.0:
                reference_length = 1.0

        if cache_key is not None:
            self._scene_reference_length_cache[
                cache_key
            ] = reference_length

        return reference_length

    def _should_render_well_as_screen_line(
        self,
        sim_data,
        ordered_points,
    ) -> bool:
        reference_length = self._scene_reference_length(
            sim_data,
            fallback_points=ordered_points,
        )

        return (
            float(self.well_radius)
            / max(reference_length, 1.0e-12)
            < WELL_THIN_RADIUS_SCENE_RATIO
        )

    def _thin_well_line_width(self) -> float:
        scale = float(self.well_radius) / max(
            float(WELL_RADIUS),
            1.0e-12,
        )
        width = float(WELL_FALLBACK_LINE_WIDTH) * scale

        return float(
            np.clip(
                width,
                WELL_THIN_LINE_MIN_WIDTH,
                WELL_THIN_LINE_MAX_WIDTH,
            )
        )

    def _add_stable_well_line(
        self,
        polyline,
        color=None,
        opacity=WELL_OPACITY,
    ):
        if color is None:
            color = self.well_color

        kwargs = dict(
            color=color,
            line_width=self._thin_well_line_width(),
            opacity=float(opacity),
            lighting=False,
            render=False,
        )

        try:
            actor = self.plotter.add_mesh(
                polyline,
                render_lines_as_tubes=True,
                **kwargs,
            )
        except TypeError:
            actor = self.plotter.add_mesh(
                polyline,
                **kwargs,
            )

        try:
            prop = actor.GetProperty()

            if prop is not None:
                try:
                    prop.LightingOff()
                except Exception:
                    pass

                try:
                    prop.RenderLinesAsTubesOn()
                except Exception:
                    try:
                        prop.SetRenderLinesAsTubes(True)
                    except Exception:
                        pass

                try:
                    prop.SetLineStipplePattern(0xFFFF)
                    prop.SetLineStippleRepeatFactor(1)
                except Exception:
                    pass
        except Exception:
            pass

        try:
            mapper = actor.GetMapper()

            if mapper is not None:
                try:
                    mapper.ScalarVisibilityOff()
                except Exception:
                    pass
        except Exception:
            pass

        self._configure_depth_sorted_geometry_actor(
            actor
        )
        return actor


    @staticmethod
    def _trajectory_point_z(point, vertical_mode):
        mode = str(vertical_mode or "elevation_z").strip().lower()

        if mode == "tvd":
            return float(point["tvd_m"])
        if mode == "subsea_depth":
            return -float(point["z_m"])
        return float(point["z_m"])

    @classmethod
    def _well_trajectory_z_values(cls, well_data):
        if not isinstance(well_data, dict):
            return []

        mode = well_data.get("vertical_mode", "elevation_z")
        values = []
        for well in well_data.get("wells", []) or []:
            if not isinstance(well, dict):
                continue
            for point in well.get("rows", []) or []:
                if not isinstance(point, dict):
                    continue
                try:
                    z = cls._trajectory_point_z(point, mode)
                except (KeyError, TypeError, ValueError):
                    continue
                if np.isfinite(z):
                    values.append(float(z))
        return values

    @classmethod
    def _raw_geometry_z_transform_for_wells(cls, well_data):
        """
        将射孔和人工裂缝保存的原始 DEV z_m 转换到井轨迹当前垂向模式。

        返回函数接收原始 Z 和井名。TVD 模式优先使用各井的 KB；
        如果 DEV 未直接提供 KB，则用轨迹上的 median(TVD + Z) 推导。
        """
        if not isinstance(well_data, dict):
            return lambda z, _well_name="": float(z)

        mode = str(
            well_data.get("vertical_mode")
            or "elevation_z"
        ).strip().lower()

        if mode == "subsea_depth":
            return lambda z, _well_name="": -float(z)
        if mode != "tvd":
            return lambda z, _well_name="": float(z)

        references = {}
        all_references = []
        for well in well_data.get("wells", []) or []:
            if not isinstance(well, dict):
                continue

            well_name = str(
                well.get("well_name") or ""
            ).strip()
            metadata = well.get("metadata") or {}
            reference = metadata.get("wellhead_kb")
            try:
                reference = float(reference)
            except (TypeError, ValueError):
                reference = None

            if reference is None or not np.isfinite(reference):
                candidates = []
                for row in well.get("rows", []) or []:
                    if not isinstance(row, dict):
                        continue
                    try:
                        candidate = (
                            float(row["tvd_m"])
                            + float(row["z_m"])
                        )
                    except (KeyError, TypeError, ValueError):
                        continue
                    if np.isfinite(candidate):
                        candidates.append(candidate)
                reference = (
                    float(np.median(candidates))
                    if candidates
                    else None
                )

            if reference is not None and np.isfinite(reference):
                if well_name:
                    references[well_name] = float(reference)
                all_references.append(float(reference))

        fallback_reference = (
            float(np.median(all_references))
            if all_references
            else None
        )

        def transform(z, well_name=""):
            z = float(z)
            reference = references.get(
                str(well_name or "").strip(),
                fallback_reference,
            )
            if reference is None:
                return z
            return float(reference) - z

        return transform

    @staticmethod
    def _xyz_from_value(value):
        """从前端保存的点记录中读取原始 XYZ，不做坐标推算。"""
        if isinstance(value, dict):
            x = value.get("x_m", value.get("x"))
            y = value.get("y_m", value.get("y"))
            z = value.get("z_m", value.get("z"))
            try:
                point = np.asarray(
                    [float(x), float(y), float(z)],
                    dtype=np.float64,
                )
            except (TypeError, ValueError):
                return None
        else:
            try:
                point = np.asarray(
                    value,
                    dtype=np.float64,
                ).reshape(-1)
            except Exception:
                return None

            if point.size < 3:
                return None
            point = point[:3]

        if not np.isfinite(point).all():
            return None

        return point.astype(
            np.float64,
            copy=True,
        )

    @classmethod
    def _perforation_row_xyz(
        cls,
        row,
        role,
    ):
        """读取射孔计算结果中保存的起点、终点或中心点 XYZ。"""
        if not isinstance(row, dict):
            return None

        role = str(role or "").strip().lower()
        nested_keys = {
            "start": (
                "start",
                "start_point",
                "start_xyz",
                "start_xyz_m",
                "start_coordinates",
                "point1",
                "p1",
            ),
            "end": (
                "end",
                "end_point",
                "end_xyz",
                "end_xyz_m",
                "end_coordinates",
                "point2",
                "p2",
            ),
            "center": (
                "center",
                "centre",
                "center_point",
                "centre_point",
                "center_xyz",
                "centre_xyz",
                "center_xyz_m",
                "midpoint",
                "middle_point",
            ),
        }.get(role, ())

        for key in nested_keys:
            if key not in row:
                continue
            point = cls._xyz_from_value(row.get(key))
            if point is not None:
                return point

        flat_key_groups = {
            "start": (
                ("start_x", "start_y", "start_z"),
                ("start_x_m", "start_y_m", "start_z_m"),
                ("x_start", "y_start", "z_start"),
                ("x1", "y1", "z1"),
                ("p1_x", "p1_y", "p1_z"),
            ),
            "end": (
                ("end_x", "end_y", "end_z"),
                ("end_x_m", "end_y_m", "end_z_m"),
                ("x_end", "y_end", "z_end"),
                ("x2", "y2", "z2"),
                ("p2_x", "p2_y", "p2_z"),
            ),
            "center": (
                ("center_x", "center_y", "center_z"),
                ("center_x_m", "center_y_m", "center_z_m"),
                ("centre_x", "centre_y", "centre_z"),
                ("mid_x", "mid_y", "mid_z"),
                ("midpoint_x", "midpoint_y", "midpoint_z"),
                ("xc", "yc", "zc"),
            ),
        }.get(role, ())

        for keys in flat_key_groups:
            if not all(key in row for key in keys):
                continue
            point = cls._xyz_from_value(
                [row[key] for key in keys]
            )
            if point is not None:
                return point

        return None

    @classmethod
    def _calculated_perforation_geometry_by_well(
        cls,
        perforation_data,
        z_transform=None,
        source_z_transform=None,
    ):
        """
        按井名整理前端已经计算并保存的射孔几何。

        XYZ 只读取计算结果，不再根据 MD 对 DEV 轨迹重新插值。
        MD 仅用于把保存的几何点插入井轨迹的正确顺序。
        """
        if not isinstance(perforation_data, dict):
            return {}

        calculation = perforation_data.get("calculation") or {}
        rows = calculation.get("rows") or []
        grouped = {}

        for row in rows:
            if not isinstance(row, dict):
                continue

            if str(row.get("status") or "").strip().lower() != "success":
                continue

            well_name = str(row.get("well_name") or "").strip()
            if not well_name:
                continue

            try:
                md1 = float(row["md1"])
                md2 = float(row["md2"])
            except (KeyError, TypeError, ValueError):
                continue

            if not np.isfinite([md1, md2]).all():
                continue

            start_xyz = cls._perforation_row_xyz(
                row,
                "start",
            )
            end_xyz = cls._perforation_row_xyz(
                row,
                "end",
            )
            center_xyz = cls._perforation_row_xyz(
                row,
                "center",
            )

            # 成功记录必须至少具有前端保存的起点和终点坐标。
            if start_xyz is None or end_xyz is None:
                continue

            if md2 < md1:
                md1, md2 = md2, md1
                start_xyz, end_xyz = end_xyz, start_xyz

            if md2 - md1 <= 1.0e-10:
                continue

            def transform_point(point):
                if point is None:
                    return None
                result = np.asarray(
                    point,
                    dtype=np.float64,
                ).reshape(3).copy()
                if callable(source_z_transform):
                    result[2] = float(
                        source_z_transform(
                            result[2],
                            well_name,
                        )
                    )
                if callable(z_transform):
                    result[2] = float(
                        z_transform(result[2])
                    )
                return result if np.isfinite(result).all() else None

            start_xyz = transform_point(start_xyz)
            end_xyz = transform_point(end_xyz)
            center_xyz = transform_point(center_xyz)

            if start_xyz is None or end_xyz is None:
                continue

            center_md = row.get(
                "center_md",
                row.get(
                    "mid_md",
                    (md1 + md2) * 0.5,
                ),
            )
            try:
                center_md = float(center_md)
            except (TypeError, ValueError):
                center_md = (md1 + md2) * 0.5

            if not np.isfinite(center_md):
                center_md = (md1 + md2) * 0.5

            center_md = min(
                max(center_md, md1),
                md2,
            )

            grouped.setdefault(
                well_name,
                [],
            ).append(
                {
                    "md1": float(md1),
                    "md2": float(md2),
                    "center_md": float(center_md),
                    "start_xyz": start_xyz,
                    "center_xyz": center_xyz,
                    "end_xyz": end_xyz,
                    "source_row": row,
                }
            )

        for records in grouped.values():
            records.sort(
                key=lambda item: (
                    item["md1"],
                    item["md2"],
                )
            )

        return grouped

    def _split_track_by_perforation_geometry(
        self,
        valid_points,
        perforation_records,
    ):
        """
        使用前端保存的射孔 XYZ 分割井轨迹。

        原始 DEV 点保持原样；射孔边界和中心使用计算结果中的 XYZ，
        不调用 MD 插值函数重新生成坐标。
        """
        if not valid_points:
            return []

        samples = []

        for md, xyz in valid_points:
            try:
                md = float(md)
                xyz = np.asarray(
                    xyz,
                    dtype=np.float64,
                ).reshape(3)
            except Exception:
                continue

            if not np.isfinite([md, *xyz]).all():
                continue

            samples.append(
                {
                    "md": md,
                    "point": xyz.copy(),
                    "priority": 0,
                }
            )

        if len(samples) < 2:
            return []

        track_min = min(item["md"] for item in samples)
        track_max = max(item["md"] for item in samples)
        intervals = []

        for record in perforation_records or []:
            if not isinstance(record, dict):
                continue

            start = max(float(record["md1"]), track_min)
            end = min(float(record["md2"]), track_max)
            if end - start <= 1.0e-10:
                continue

            intervals.append((start, end))

            exact_points = (
                (record["md1"], record.get("start_xyz"), 2),
                (record.get("center_md"), record.get("center_xyz"), 3),
                (record["md2"], record.get("end_xyz"), 2),
            )

            for md, point, priority in exact_points:
                if point is None or md is None:
                    continue
                try:
                    md = float(md)
                    point = np.asarray(
                        point,
                        dtype=np.float64,
                    ).reshape(3)
                except Exception:
                    continue
                if not np.isfinite([md, *point]).all():
                    continue
                if md < track_min - 1.0e-9 or md > track_max + 1.0e-9:
                    continue
                samples.append(
                    {
                        "md": md,
                        "point": point.copy(),
                        "priority": int(priority),
                    }
                )

        samples.sort(
            key=lambda item: (
                item["md"],
                item["priority"],
            )
        )

        deduplicated = []
        for item in samples:
            if (
                deduplicated
                and abs(item["md"] - deduplicated[-1]["md"])
                <= 1.0e-10
            ):
                if item["priority"] >= deduplicated[-1]["priority"]:
                    deduplicated[-1] = item
                continue
            deduplicated.append(item)

        if len(deduplicated) < 2:
            return []

        def is_perforation_md(md):
            return any(
                start - 1.0e-9 <= md <= end + 1.0e-9
                for start, end in intervals
            )

        result = []

        for index in range(len(deduplicated) - 1):
            current = deduplicated[index]
            following = deduplicated[index + 1]
            md0 = current["md"]
            md1 = following["md"]

            if md1 - md0 <= 1.0e-12:
                continue

            is_perforation = is_perforation_md(
                (md0 + md1) * 0.5
            )
            point0 = current["point"]
            point1 = following["point"]

            if (
                result
                and result[-1]["is_perforation"] == is_perforation
            ):
                if np.linalg.norm(
                    point0 - result[-1]["points"][-1]
                ) > 1.0e-8:
                    result[-1]["points"].append(point0)
                result[-1]["points"].append(point1)
            else:
                result.append(
                    {
                        "is_perforation": is_perforation,
                        "points": [point0, point1],
                    }
                )

        normalized = []
        for item in result:
            points = []
            for point in item["points"]:
                point = np.asarray(
                    point,
                    dtype=np.float64,
                ).reshape(3)
                if (
                    not points
                    or np.linalg.norm(point - points[-1]) > 1.0e-8
                ):
                    points.append(point)

            if len(points) >= 2:
                normalized.append(
                    {
                        "is_perforation": item["is_perforation"],
                        "points": np.asarray(
                            points,
                            dtype=np.float64,
                        ),
                    }
                )

        return normalized

    def _add_well_track_segment_actor(
        self,
        sim_data,
        points,
        color,
        opacity=WELL_OPACITY,
    ):
        polyline = self._polyline_from_points(
            points
        )

        if polyline is None:
            return None

        use_screen_line = (
            self._should_render_well_as_screen_line(
                sim_data,
                points,
            )
        )

        if use_screen_line:
            try:
                return self._add_stable_well_line(
                    polyline,
                    color=color,
                    opacity=opacity,
                )
            except Exception:
                return None

        try:
            tube = polyline.tube(
                radius=self.well_radius,
                n_sides=WELL_TUBE_SIDES,
                capping=True,
            )

            actor = self.plotter.add_mesh(
                tube,
                color=color,
                opacity=float(opacity),
                lighting=True,
                smooth_shading=True,
                ambient=0.86,
                diffuse=0.44,
                specular=0.05,
                specular_power=12.0,
                render=False,
            )
        except Exception:
            actor = self._add_stable_well_line(
                polyline,
                color=color,
                opacity=opacity,
            )

        self._configure_depth_sorted_geometry_actor(
            actor
        )

        return actor

    def _add_perforation_points_actor(
        self,
        points,
    ):
        try:
            array = np.asarray(
                points,
                dtype=np.float64,
            ).reshape(-1, 3)
        except Exception:
            return None

        valid = np.isfinite(
            array
        ).all(axis=1)
        array = array[valid]

        if array.shape[0] == 0:
            return None

        # 每次创建 actor 时都按当前井筒半径计算，确保射孔球
        # 始终跟随井半径。默认 multiplier=1.0，球直径与井直径一致。
        radius = float(
            self.well_radius
            * self.perforation_point_radius_multiplier
        )
        self.perforation_point_radius = radius
        self.perforation_point_size = radius

        if not np.isfinite(radius) or radius <= 0.0:
            return None

        try:
            point_cloud = pv.PolyData(array)
            sphere = pv.Sphere(
                radius=radius,
                theta_resolution=int(
                    PERFORATION_POINT_THETA_RESOLUTION
                ),
                phi_resolution=int(
                    PERFORATION_POINT_PHI_RESOLUTION
                ),
            )
            glyphs = point_cloud.glyph(
                geom=sphere,
                orient=False,
                scale=False,
            )

            if glyphs is None or glyphs.n_points == 0:
                return None

            actor = self.plotter.add_mesh(
                glyphs,
                color=self.perforation_color,
                opacity=float(
                    PERFORATION_OPACITY
                ),
                lighting=True,
                smooth_shading=True,
                ambient=0.85,
                diffuse=0.45,
                specular=0.08,
                specular_power=12.0,
                pickable=False,
                render=False,
            )
        except Exception:
            return None

        self._configure_depth_sorted_geometry_actor(
            actor
        )

        try:
            mapper = actor.GetMapper()
            if mapper is not None:
                mapper.ScalarVisibilityOff()
        except Exception:
            pass

        return actor

    def _corner_grid_bounds(self, sim_data):
        if sim_data is None:
            return None

        cache_key = id(sim_data)
        cached = self._corner_grid_bounds_cache.get(
            cache_key,
            None,
        )

        if cached is not None:
            return cached

        grid_data = getattr(
            sim_data,
            "static_grid_data",
            None,
        )

        if not isinstance(grid_data, dict):
            return None

        coord = grid_data.get(
            "coord",
            None,
        )

        if coord is None:
            return None

        try:
            coord_array = np.asarray(
                coord,
                dtype=np.float64,
            ).reshape(-1, 6)
        except Exception:
            return None

        x_values = np.concatenate(
            [
                coord_array[:, 0],
                coord_array[:, 3],
            ]
        )
        y_values = np.concatenate(
            [
                coord_array[:, 1],
                coord_array[:, 4],
            ]
        )

        x_values = x_values[
            np.isfinite(x_values)
        ]
        y_values = y_values[
            np.isfinite(y_values)
        ]

        if x_values.size == 0 or y_values.size == 0:
            return None

        z_bounds = self._static_grid_z_bounds(
            sim_data
        )

        if z_bounds is None:
            z_values = np.concatenate(
                [
                    coord_array[:, 2],
                    coord_array[:, 5],
                ]
            )
            z_values = z_values[
                np.isfinite(z_values)
            ]

            if z_values.size == 0:
                return None

            min_z = float(np.min(z_values))
            max_z = float(np.max(z_values))
        else:
            min_z, max_z = [
                float(value)
                for value in z_bounds
            ]

        bounds = (
            float(np.min(x_values)),
            float(np.max(x_values)),
            float(np.min(y_values)),
            float(np.max(y_values)),
            min(min_z, max_z),
            max(min_z, max_z),
        )

        values = np.asarray(
            bounds,
            dtype=np.float64,
        )

        if (
            values.size != 6
            or not np.isfinite(values).all()
            or values[1] <= values[0]
            or values[3] <= values[2]
            or values[5] <= values[4]
        ):
            return None

        self._corner_grid_bounds_cache[
            cache_key
        ] = bounds

        return bounds

    def _setup_camera_for_corner_grid_bounds(self, bounds):
        if bounds is None or len(bounds) != 6:
            return

        try:
            min_x, max_x, min_y, max_y, min_z, max_z = [
                float(value)
                for value in bounds
            ]

            cx = (min_x + max_x) / 2.0
            cy = (min_y + max_y) / 2.0
            cz = (min_z + max_z) / 2.0

            dx = max_x - min_x
            dy = max_y - min_y
            dz = max_z - min_z

            max_xy = max(dx, dy)
            z_ratio = dz / max_xy if max_xy > 0 else 1.0

            if z_ratio < 0.1:
                dist = max(max_xy * 1.8, 1.0)
                camera_position = (
                    cx + dx * 0.3,
                    cy - dist,
                    cz + dz * 8,
                )
            else:
                dist = max(
                    dx,
                    dy,
                    dz,
                    1.0,
                ) * 2.5
                camera_position = (
                    cx + dist * 0.8,
                    cy + dist * 0.6,
                    cz + dist * 0.4,
                )

            camera = self.plotter.camera
            camera.SetPosition(
                *camera_position
            )
            camera.SetFocalPoint(
                cx,
                cy,
                cz,
            )
            camera.SetViewUp(
                0.0,
                0.0,
                1.0,
            )

            camera.OrthogonalizeViewUp()

            try:
                self.plotter.reset_camera(
                    bounds=bounds,
                    render=False,
                )
            except TypeError:
                renderer = self._main_renderer()

                if renderer is not None:
                    renderer.ResetCamera(
                        *bounds
                    )

            camera.SetFocalPoint(
                cx,
                cy,
                cz,
            )
            camera.SetViewUp(
                0.0,
                0.0,
                1.0,
            )
            camera.OrthogonalizeViewUp()

        except Exception:
            pass

    def clear_grid(self, render_now=True):
        self._remove_actor(self.grid_actor)
        self._remove_actor(self.grid_edge_actor)
        self._remove_actor(
            self.grid_internal_edge_actor
        )

        self.grid_actor = None
        self.grid_edge_actor = None
        self.grid_internal_edge_actor = None

        if self._geometry_top_actors():
            self.refresh_preview_stack(
                render_now=False,
            )

        if render_now:
            self._render()

    def clear_wells(self, render_now=True):
        self._remove_actor_list(self.well_actors)
        self._remove_actor_list(
            self.perforation_actors
        )
        self._remove_actor_list(self.well_label_actors)

        self.well_actors = []
        self.perforation_segment_actors = []
        self.perforation_point_actors = []
        self.perforation_actors = []
        self.well_label_actors = []
        self._well_actor_groups = {}
        self._well_label_anchor_by_name = {}
        self._well_label_reference_view_scale = None
        self._well_label_current_font_size = None
        self._well_label_points = []
        self._well_label_texts = []
        self._well_label_use_billboard = False
        self._wells_render_revision = -1

        self._sync_geometry_overlay_attachment()

        if render_now:
            self._render()

    def clear_natural_fractures(self, render_now=True):
        self._remove_actor_list(self.natural_fracture_actors)
        self.natural_fracture_actors = []
        self._natural_fractures_render_revision = -1

        self._sync_geometry_overlay_attachment()

        if render_now:
            self._render()

    def clear_hydraulic_fractures(self, render_now=True):
        self._remove_actor_list(self.hydraulic_fracture_actors)
        self.hydraulic_fracture_actors = []
        self._hydraulic_fractures_render_revision = -1

        self._sync_geometry_overlay_attachment()

        if render_now:
            self._render()

    def clear_fractures(self, render_now=True):
        self.clear_natural_fractures(render_now=False)
        self.clear_hydraulic_fractures(render_now=False)

        if render_now:
            self._render()

    def clear_all(self, render_now=True):
        self.clear_grid(render_now=False)
        self.clear_wells(render_now=False)
        self.clear_fractures(render_now=False)

        setattr(
            self.host,
            "_preview_camera_session_key",
            None,
        )
        setattr(
            self.host,
            "_preview_camera_initialized",
            False,
        )

        if render_now:
            self._render()

    def is_grid_visible(self) -> bool:
        return bool(
            self.grid_actor is not None
            or self.grid_edge_actor is not None
            or self.grid_internal_edge_actor is not None
        )

    def is_wells_visible(self) -> bool:
        """仅返回井筒本体是否已显示，不再把射孔点/射孔段算入井显示状态。"""
        return bool(self.well_actors)

    def is_natural_fractures_visible(self) -> bool:
        return bool(self.natural_fracture_actors)

    def is_hydraulic_fractures_visible(self) -> bool:
        return bool(self.hydraulic_fracture_actors)

    def is_fractures_visible(self) -> bool:
        return self.is_natural_fractures_visible() or self.is_hydraulic_fractures_visible()

    def _initialize_preview_camera_once(
        self,
        sim_data,
        bounds=None,
    ) -> bool:

        corner_grid_bounds = self._corner_grid_bounds(
            sim_data
        )

        target_bounds = (
            corner_grid_bounds
            if corner_grid_bounds is not None
            else bounds
        )

        if target_bounds is None or len(target_bounds) != 6:
            return False

        session_key = id(sim_data)

        old_session_key = getattr(
            self.host,
            "_preview_camera_session_key",
            None,
        )

        if old_session_key != session_key:
            setattr(
                self.host,
                "_preview_camera_session_key",
                session_key,
            )
            setattr(
                self.host,
                "_preview_camera_initialized",
                False,
            )

        if bool(
            getattr(
                self.host,
                "_preview_camera_initialized",
                False,
            )
        ):
            return False

        self._setup_camera_for_corner_grid_bounds(
            target_bounds,
        )

        setattr(
            self.host,
            "_preview_camera_initialized",
            True,
        )

        return True

    @staticmethod
    def _actor_bounds(actor):
        if actor is None:
            return None

        try:
            bounds = actor.GetBounds()
        except Exception:
            try:
                bounds = actor.bounds
            except Exception:
                return None

        if bounds is None or len(bounds) != 6:
            return None

        values = np.asarray(
            bounds,
            dtype=np.float64,
        )

        if values.size != 6 or not np.isfinite(values).all():
            return None

        if (
            values[1] < values[0]
            or values[3] < values[2]
            or values[5] < values[4]
        ):
            return None

        return tuple(
            float(value)
            for value in values
        )

    def _actors_bounds(self, actors):
        valid_bounds = []

        for actor in actors or []:
            bounds = self._actor_bounds(actor)

            if bounds is not None:
                valid_bounds.append(bounds)

        if not valid_bounds:
            return None

        return (
            min(bounds[0] for bounds in valid_bounds),
            max(bounds[1] for bounds in valid_bounds),
            min(bounds[2] for bounds in valid_bounds),
            max(bounds[3] for bounds in valid_bounds),
            min(bounds[4] for bounds in valid_bounds),
            max(bounds[5] for bounds in valid_bounds),
        )

    def _main_renderer(self):
        renderer = getattr(
            self.plotter,
            "renderer",
            None,
        )

        if renderer is None:
            renderer = getattr(
                self.host,
                "renderer",
                None,
            )

        return renderer

    def _geometry_mesh_actors(self):
        return [
            actor
            for actor in [
                *(self.natural_fracture_actors or []),
                *(self.hydraulic_fracture_actors or []),
                *(self.well_actors or []),
                *(self.perforation_actors or []),
            ]
            if actor is not None
        ]

    def _geometry_top_actors(self):
        return self._geometry_mesh_actors()

    @staticmethod
    def _actor_is_visible(actor) -> bool:
        if actor is None:
            return False

        try:
            return bool(actor.GetVisibility())
        except Exception:
            try:
                return bool(actor.visibility)
            except Exception:
                return True

    def get_visible_geometry_bounds(self):
        actors = [
            actor
            for actor in self._geometry_mesh_actors()
            if self._actor_is_visible(actor)
        ]

        return self._actors_bounds(actors)

    @staticmethod
    def _renderer_is_attached(render_window, renderer) -> bool:
        if render_window is None or renderer is None:
            return False

        try:
            renderers = render_window.GetRenderers()

            if renderers is not None and hasattr(renderers, "IsItemPresent"):
                return bool(renderers.IsItemPresent(renderer))
        except Exception:
            pass

        return False

    def _set_geometry_overlay_attached(self, attached: bool) -> None:

        render_window = getattr(
            self.plotter,
            "ren_win",
            None,
        )
        overlay_renderer = getattr(
            self.host,
            "_geometry_preview_overlay_renderer",
            None,
        )

        if render_window is None or overlay_renderer is None:
            return

        is_attached = self._renderer_is_attached(
            render_window,
            overlay_renderer,
        )

        if attached and not is_attached:
            try:
                render_window.AddRenderer(overlay_renderer)
                is_attached = True
            except Exception:
                pass

        elif not attached and is_attached:
            try:
                render_window.RemoveRenderer(overlay_renderer)
                is_attached = False
            except Exception:
                pass

        setattr(
            self.host,
            "_geometry_preview_overlay_attached",
            bool(is_attached),
        )

        if not attached:
            main_renderer = self._main_renderer()

            if main_renderer is not None:
                try:
                    main_renderer.ResetCameraClippingRange()
                except Exception:
                    try:
                        self.plotter.reset_camera_clipping_range()
                    except Exception:
                        pass

    def _sync_geometry_overlay_attachment(self) -> None:
        top_actors = self._geometry_top_actors()

        if not PREVIEW_USE_GEOMETRY_OVERLAY:
            for actor in top_actors:
                self._configure_depth_sorted_geometry_actor(actor)
                self._move_actor_to_renderer_end(actor)

            self._set_geometry_overlay_attached(False)
            return

        if top_actors:
            self._ensure_geometry_overlay_renderer(
                attach_to_window=True,
            )
        else:
            self._set_geometry_overlay_attached(False)

    def _ensure_geometry_overlay_renderer(
        self,
        attach_to_window: bool = True,
    ):

        main_renderer = self._main_renderer()
        render_window = getattr(
            self.plotter,
            "ren_win",
            None,
        )

        if main_renderer is None or render_window is None:
            return None

        overlay_renderer = getattr(
            self.host,
            "_geometry_preview_overlay_renderer",
            None,
        )

        if overlay_renderer is None:
            try:
                overlay_renderer = main_renderer.NewInstance()
            except Exception:
                return None

            try:
                main_layer = int(main_renderer.GetLayer())
            except Exception:
                main_layer = 0

            try:
                current_layer_count = int(
                    render_window.GetNumberOfLayers()
                )
            except Exception:
                current_layer_count = 1

            overlay_layer = max(
                main_layer + 1,
                current_layer_count,
            )

            try:
                render_window.SetNumberOfLayers(
                    overlay_layer + 1
                )
                overlay_renderer.SetLayer(
                    overlay_layer
                )
            except Exception:
                return None

            setattr(
                self.host,
                "_geometry_preview_overlay_renderer",
                overlay_renderer,
            )
            setattr(
                self.host,
                "_geometry_preview_overlay_layer",
                overlay_layer,
            )
            setattr(
                self.host,
                "_geometry_preview_overlay_attached",
                False,
            )

        if attach_to_window:
            self._set_geometry_overlay_attached(True)

        try:
            overlay_renderer.SetActiveCamera(
                main_renderer.GetActiveCamera()
            )
        except Exception:
            pass

        try:
            overlay_renderer.SetViewport(
                *main_renderer.GetViewport()
            )
        except Exception:
            pass

        try:
            overlay_renderer.SetInteractive(False)
        except Exception:
            try:
                overlay_renderer.InteractiveOff()
            except Exception:
                pass

        try:
            overlay_renderer.SetPreserveColorBuffer(True)
        except Exception:
            try:
                overlay_renderer.PreserveColorBufferOn()
            except Exception:
                pass

        try:
            overlay_renderer.SetPreserveDepthBuffer(False)
        except Exception:
            try:
                overlay_renderer.PreserveDepthBufferOff()
            except Exception:
                pass

        try:
            overlay_renderer.SetBackgroundAlpha(0.0)
        except Exception:
            pass

        try:
            overlay_renderer.SetUseDepthPeeling(False)
        except Exception:
            pass

        if PREVIEW_ENABLE_ANTI_ALIASING:
            try:
                if hasattr(overlay_renderer, "SetUseFXAA"):
                    overlay_renderer.SetUseFXAA(True)
            except Exception:
                pass

        try:
            if hasattr(overlay_renderer, "AutomaticLightCreationOn"):
                overlay_renderer.AutomaticLightCreationOn()
        except Exception:
            pass

        return overlay_renderer

    @staticmethod
    def _configure_depth_sorted_geometry_actor(actor) -> None:

        if actor is None:
            return

        try:
            actor.ForceTranslucentOff()
        except Exception:
            try:
                actor.SetForceTranslucent(False)
            except Exception:
                pass

        try:
            actor.ForceOpaqueOn()
        except Exception:
            try:
                actor.SetForceOpaque(True)
            except Exception:
                pass

        try:
            prop = actor.GetProperty()

            if prop is not None:
                try:
                    prop.FrontfaceCullingOff()
                except Exception:
                    pass

                try:
                    prop.BackfaceCullingOff()
                except Exception:
                    pass

                try:
                    prop.RenderPointsAsSpheresOff()
                except Exception:
                    pass

        except Exception:
            pass

    def _move_actor_to_renderer_end(self, actor) -> None:
        if actor is None:
            return

        main_renderer = self._main_renderer()

        if main_renderer is None:
            return

        overlay_renderer = getattr(
            self.host,
            "_geometry_preview_overlay_renderer",
            None,
        )

        if overlay_renderer is not None:
            try:
                overlay_renderer.RemoveActor2D(actor)
            except Exception:
                pass

            try:
                overlay_renderer.RemoveActor(actor)
            except Exception:
                try:
                    overlay_renderer.RemoveViewProp(actor)
                except Exception:
                    pass

        try:
            main_renderer.RemoveActor(actor)
        except Exception:
            try:
                main_renderer.RemoveViewProp(actor)
            except Exception:
                pass

        try:
            main_renderer.AddActor(actor)
        except Exception:
            try:
                main_renderer.AddViewProp(actor)
            except Exception:
                pass

    def _move_actor_to_geometry_overlay(self, actor) -> None:
        if actor is None:
            return

        overlay_renderer = self._ensure_geometry_overlay_renderer()

        if overlay_renderer is None:
            self._move_actor_to_renderer_end(actor)
            return

        main_renderer = self._main_renderer()

        if main_renderer is not None:
            try:
                main_renderer.RemoveActor2D(actor)
            except Exception:
                pass

            try:
                main_renderer.RemoveActor(actor)
            except Exception:
                try:
                    main_renderer.RemoveViewProp(actor)
                except Exception:
                    pass

        try:
            overlay_renderer.RemoveActor(actor)
        except Exception:
            try:
                overlay_renderer.RemoveViewProp(actor)
            except Exception:
                pass

        try:
            overlay_renderer.AddActor(actor)
        except Exception:
            try:
                overlay_renderer.AddViewProp(actor)
            except Exception:
                if main_renderer is not None:
                    try:
                        main_renderer.AddViewProp(actor)
                    except Exception:
                        pass

    def _is_static_property_visible(self) -> bool:
        static_preview = getattr(
            self.host,
            "static_property_preview",
            None,
        )

        if static_preview is None:
            return False

        actor = getattr(
            static_preview,
            "actor",
            None,
        )

        return self._actor_is_visible(actor)

    def _is_fence_section_display_active(self) -> bool:
        """返回当前是否正在显示已经生成的持久任意剖面。"""
        checker = getattr(
            self.host,
            "_vertical_fence_section_is_active",
            None,
        )

        if checker is not None:
            try:
                return bool(checker())
            except Exception:
                pass

        checker = getattr(
            self.host,
            "is_fence_property_display_mode",
            None,
        )

        if checker is not None:
            try:
                return bool(checker())
            except Exception:
                pass

        return False

    def _hide_grid_for_fence_section(self) -> None:
        """剖面显示期间隐藏预览整体网格面及全部网格线。"""
        for actor in (
            self.grid_actor,
            self.grid_edge_actor,
            self.grid_internal_edge_actor,
        ):
            self._set_actor_visibility(
                actor,
                False,
            )

    @staticmethod
    def _set_actor_opacity(actor, opacity) -> None:
        if actor is None:
            return

        try:
            prop = actor.GetProperty()
        except Exception:
            prop = None

        if prop is None:
            return

        try:
            prop.SetOpacity(float(opacity))
        except Exception:
            pass

    def _apply_property_focus_grid_style(self) -> None:
        if self._is_fence_section_display_active():
            self._hide_grid_for_fence_section()
            return

        property_visible = (
            GRID_PROPERTY_FOCUS_MODE
            and self._is_static_property_visible()
        )

        if self.grid_actor is not None:
            if property_visible:
                try:
                    self.grid_actor.ForceOpaqueOff()
                except Exception:
                    try:
                        self.grid_actor.SetForceOpaque(False)
                    except Exception:
                        pass

                try:
                    self.grid_actor.ForceTranslucentOn()
                except Exception:
                    try:
                        self.grid_actor.SetForceTranslucent(True)
                    except Exception:
                        pass

                self._set_actor_opacity(
                    self.grid_actor,
                    GRID_PROPERTY_SURFACE_OPACITY,
                )
            else:
                self._configure_stable_grid_surface_actor(
                    self.grid_actor
                )

        for edge_actor in (
            self.grid_edge_actor,
            self.grid_internal_edge_actor,
        ):
            if edge_actor is None:
                continue

            if property_visible:
                try:
                    edge_actor.ForceOpaqueOff()
                except Exception:
                    try:
                        edge_actor.SetForceOpaque(False)
                    except Exception:
                        pass

                try:
                    edge_actor.ForceTranslucentOn()
                except Exception:
                    try:
                        edge_actor.SetForceTranslucent(True)
                    except Exception:
                        pass

                self._set_actor_opacity(
                    edge_actor,
                    GRID_PROPERTY_EDGE_OPACITY,
                )

                try:
                    prop = edge_actor.GetProperty()

                    if prop is not None:
                        if GRID_PROPERTY_RENDER_LINES_AS_TUBES:
                            try:
                                prop.RenderLinesAsTubesOn()
                            except Exception:
                                prop.SetRenderLinesAsTubes(True)
                        else:
                            try:
                                prop.RenderLinesAsTubesOff()
                            except Exception:
                                prop.SetRenderLinesAsTubes(False)
                except Exception:
                    pass
            else:
                self._configure_stable_grid_edge_actor(
                    edge_actor
                )

        
        self._set_actor_visibility(
            self.grid_internal_edge_actor,
            self.show_internal_grid_edges,
        )

    def refresh_preview_stack(
        self,
        render_now=False,
    ) -> None:
        """
        同步预览样式，但不再移动、删除或重新添加井/裂缝 actor。

        井、射孔、井名和裂缝只在用户真正切换其显隐或修改几何样式时
        创建/删除；属性切换、模拟分层切换仅更新网格聚焦样式。
        """
        self._apply_property_focus_grid_style()

        for actor in self._geometry_top_actors():
            self._configure_depth_sorted_geometry_actor(actor)

        self._set_geometry_overlay_attached(False)

        if self.well_label_actors:
            self._ensure_well_name_labels_attached()

        if render_now:
            self._render()

    @staticmethod
    def _corner_grid_clean_tolerance(bounds):

        try:
            values = np.asarray(
                bounds,
                dtype=np.float64,
            ).reshape(6)

            spans = np.asarray(
                [
                    abs(values[1] - values[0]),
                    abs(values[3] - values[2]),
                    abs(values[5] - values[4]),
                ],
                dtype=np.float64,
            )

            finite_spans = spans[
                np.isfinite(spans)
            ]

            reference_span = (
                float(np.max(finite_spans))
                if finite_spans.size > 0
                else 0.0
            )

        except Exception:
            reference_span = 0.0

        return max(
            reference_span
            * GRID_POINT_MERGE_TOLERANCE_RATIO,
            GRID_POINT_MERGE_ABSOLUTE_TOLERANCE,
        )


    @staticmethod
    def _set_actor_visibility(
        actor,
        visible,
    ) -> None:
        if actor is None:
            return

        try:
            actor.SetVisibility(
                bool(visible)
            )
        except Exception:
            try:
                actor.visibility = bool(visible)
            except Exception:
                pass

    def get_internal_grid_edges_visible(self) -> bool:
        return bool(self.show_internal_grid_edges)

    def set_internal_grid_edges_visible(
        self,
        visible,
        render_now=True,
    ) -> bool:
        """
        控制角点网格体内部单元线的显示状态。

        该接口只控制 grid_internal_edge_actor，不影响：
        1. 网格面；
        2. 模型外轮廓线；
        3. 模型外表面上的单元网格线。
        """
        self.show_internal_grid_edges = bool(
            visible
        )

        self._set_actor_visibility(
            self.grid_internal_edge_actor,
            self.show_internal_grid_edges,
        )

        if render_now:
            self._render()

        return self.show_internal_grid_edges

    def toggle_internal_grid_edges(
        self,
        render_now=True,
    ) -> bool:
        return self.set_internal_grid_edges_visible(
            not self.show_internal_grid_edges,
            render_now=render_now,
        )

    @staticmethod
    def _quantized_grid_point_key(
        point,
        tolerance,
    ):
        point = np.asarray(
            point,
            dtype=np.float64,
        ).reshape(3)

        tolerance = max(
            float(tolerance),
            1.0e-12,
        )

        quantized = np.rint(
            point / tolerance
        ).astype(np.int64)

        return tuple(
            int(value)
            for value in quantized
        )

    @classmethod
    def _grid_edge_segment_key(
        cls,
        point0,
        point1,
        tolerance,
    ):
        key0 = cls._quantized_grid_point_key(
            point0,
            tolerance,
        )
        key1 = cls._quantized_grid_point_key(
            point1,
            tolerance,
        )

        return (
            (key0, key1)
            if key0 <= key1
            else (key1, key0)
        )

    @staticmethod
    def _iter_polydata_line_segments(polydata):
        if polydata is None:
            return

        try:
            lines = np.asarray(
                polydata.lines,
                dtype=np.int64,
            ).reshape(-1)
        except Exception:
            return

        cursor = 0
        line_count = int(lines.size)

        while cursor < line_count:
            point_count = int(lines[cursor])
            cursor += 1

            if point_count <= 0:
                continue

            end = cursor + point_count

            if end > line_count:
                break

            point_ids = lines[cursor:end]
            cursor = end

            if point_count < 2:
                continue

            for index in range(point_count - 1):
                yield (
                    int(point_ids[index]),
                    int(point_ids[index + 1]),
                )

    @classmethod
    def _extract_internal_grid_edges(
        cls,
        all_edges,
        surface_edges,
        tolerance,
    ):
        """
        从全部单元边中剔除外表面边，只保留模型体内部边。

        surface_edges 包含模型外轮廓和外表面单元线；
        all_edges - surface_edges 才是透过半透明网格面看到的内部线。
        """
        if all_edges is None:
            return None

        boundary_keys = set()

        if surface_edges is not None:
            surface_points = np.asarray(
                surface_edges.points,
                dtype=np.float64,
            )

            for point_id0, point_id1 in (
                cls._iter_polydata_line_segments(
                    surface_edges
                )
            ):
                boundary_keys.add(
                    cls._grid_edge_segment_key(
                        surface_points[point_id0],
                        surface_points[point_id1],
                        tolerance,
                    )
                )

        all_points = np.asarray(
            all_edges.points,
            dtype=np.float64,
        )

        internal_lines = []

        for point_id0, point_id1 in (
            cls._iter_polydata_line_segments(
                all_edges
            )
        ):
            edge_key = cls._grid_edge_segment_key(
                all_points[point_id0],
                all_points[point_id1],
                tolerance,
            )

            if edge_key in boundary_keys:
                continue

            internal_lines.extend(
                [
                    2,
                    int(point_id0),
                    int(point_id1),
                ]
            )

        if not internal_lines:
            return None

        
        
        internal_edges = pv.PolyData()
        internal_edges.points = all_points.copy()

        try:
            internal_edges.verts = np.empty(
                0,
                dtype=np.int64,
            )
        except Exception:
            pass

        internal_edges.lines = np.asarray(
            internal_lines,
            dtype=np.int64,
        )

        try:
            internal_edges = internal_edges.clean(
                tolerance=max(
                    float(tolerance),
                    1.0e-12,
                ),
                remove_unused_points=True,
            )
        except TypeError:
            try:
                internal_edges = internal_edges.clean(
                    tolerance=max(
                        float(tolerance),
                        1.0e-12,
                    )
                )
            except Exception:
                pass
        except Exception:
            pass

        return internal_edges

    def _build_stable_corner_grid_surface_and_edges(
        self,
        grid,
    ):
        if grid is None:
            return None, None, None

        tolerance = self._corner_grid_clean_tolerance(
            grid.bounds,
        )

        stable_grid = grid

        try:
            stable_grid = grid.clean(
                tolerance=tolerance,
                remove_unused_points=True,
            )
        except TypeError:
            try:
                stable_grid = grid.clean(
                    tolerance=tolerance,
                )
            except Exception:
                stable_grid = grid
        except Exception:
            stable_grid = grid

        if (
            stable_grid is None
            or stable_grid.n_cells == 0
        ):
            stable_grid = grid

        surface = None
        surface_edges = None
        internal_edges = None

        try:
            surface = stable_grid.extract_surface()
        except Exception:
            surface = None

        if GRID_SHOW_EDGES:
            all_edges = None

            try:
                all_edges = stable_grid.extract_all_edges()
            except Exception:
                all_edges = None

            if surface is not None:
                try:
                    surface_edges = (
                        surface.extract_all_edges()
                    )
                except Exception:
                    surface_edges = None

            internal_edges = (
                self._extract_internal_grid_edges(
                    all_edges=all_edges,
                    surface_edges=surface_edges,
                    tolerance=tolerance,
                )
            )

        return (
            surface,
            surface_edges,
            internal_edges,
        )


    @staticmethod
    def _configure_stable_grid_edge_actor(actor):

        if actor is None:
            return

        try:
            actor.ForceTranslucentOff()
        except Exception:
            try:
                actor.SetForceTranslucent(False)
            except Exception:
                pass

        try:
            actor.ForceOpaqueOn()
        except Exception:
            try:
                actor.SetForceOpaque(True)
            except Exception:
                pass

        try:
            prop = actor.GetProperty()

            if prop is not None:
                try:
                    prop.SetOpacity(1.0)
                except Exception:
                    pass

                try:
                    prop.LightingOff()
                except Exception:
                    try:
                        prop.SetLighting(False)
                    except Exception:
                        pass

                try:
                    prop.SetLineWidth(
                        max(
                            float(GRID_EDGE_LINE_WIDTH),
                            1.0,
                        )
                    )
                except Exception:
                    pass

                if GRID_RENDER_LINES_AS_TUBES:
                    try:
                        prop.RenderLinesAsTubesOn()
                    except Exception:
                        try:
                            prop.SetRenderLinesAsTubes(True)
                        except Exception:
                            pass
                else:
                    try:
                        prop.RenderLinesAsTubesOff()
                    except Exception:
                        try:
                            prop.SetRenderLinesAsTubes(False)
                        except Exception:
                            pass

                
                
                try:
                    prop.VertexVisibilityOff()
                except Exception:
                    try:
                        prop.SetVertexVisibility(False)
                    except Exception:
                        pass

                try:
                    prop.RenderPointsAsSpheresOff()
                except Exception:
                    try:
                        prop.SetRenderPointsAsSpheres(False)
                    except Exception:
                        pass

        except Exception:
            pass

        try:
            mapper = actor.GetMapper()

            if mapper is not None:
                try:
                    mapper.ScalarVisibilityOff()
                except Exception:
                    try:
                        mapper.SetScalarVisibility(False)
                    except Exception:
                        pass

                try:
                    mapper.SetResolveCoincidentTopologyToPolygonOffset()
                except Exception:
                    pass

                try:
                    mapper.SetRelativeCoincidentTopologyLineOffsetParameters(
                        GRID_LINE_OFFSET_FACTOR,
                        GRID_LINE_OFFSET_UNITS,
                    )
                except Exception:
                    try:
                        mapper.SetResolveCoincidentTopologyLineOffsetParameters(
                            GRID_LINE_OFFSET_FACTOR,
                            GRID_LINE_OFFSET_UNITS,
                        )
                    except Exception:
                        pass

        except Exception:
            pass


    @staticmethod
    def _configure_stable_grid_surface_actor(actor):
        if actor is None:
            return

        try:
            actor.ForceOpaqueOff()
        except Exception:
            try:
                actor.SetForceOpaque(False)
            except Exception:
                pass

        try:
            prop = actor.GetProperty()

            if prop is not None:
                try:
                    prop.SetOpacity(
                        float(GRID_SURFACE_OPACITY)
                    )
                except Exception:
                    pass

                try:
                    prop.LightingOff()
                except Exception:
                    try:
                        prop.SetLighting(False)
                    except Exception:
                        pass

                try:
                    prop.EdgeVisibilityOff()
                except Exception:
                    try:
                        prop.SetEdgeVisibility(False)
                    except Exception:
                        pass

        except Exception:
            pass

        try:
            mapper = actor.GetMapper()

            if mapper is not None:
                try:
                    mapper.SetResolveCoincidentTopologyToPolygonOffset()
                except Exception:
                    pass

                try:
                    mapper.SetRelativeCoincidentTopologyPolygonOffsetParameters(
                        GRID_SURFACE_OFFSET_FACTOR,
                        GRID_SURFACE_OFFSET_UNITS,
                    )
                except Exception:
                    try:
                        mapper.SetResolveCoincidentTopologyPolygonOffsetParameters(
                            GRID_SURFACE_OFFSET_FACTOR,
                            GRID_SURFACE_OFFSET_UNITS,
                        )
                    except Exception:
                        pass

        except Exception:
            pass


    def prepare_scene_for_render(self):
        """渲染前只同步材质，不重新挂载任何几何 actor。"""
        self._apply_property_focus_grid_style()

        for actor in self._geometry_top_actors():
            self._configure_depth_sorted_geometry_actor(actor)

        if self.well_label_actors:
            self._ensure_well_name_labels_attached()


    def ensure_grid_visible(
        self,
        sim_data=None,
        render_now=False,
    ):
        """确保预览网格存在且可见，不使用 render_grid() 的切换语义。"""
        data = (
            sim_data
            if sim_data is not None
            else self._last_sim_data
        )

        if data is None:
            return None

        self._remember_sim_data(data)
        self.show_internal_grid_edges = True

        if not self.is_grid_visible():
            actor = self.render_grid(
                data,
                render_now=False,
            )
        else:
            actor = self.grid_actor or self.grid_edge_actor

        self._set_actor_visibility(
            self.grid_actor,
            True,
        )
        self._set_actor_visibility(
            self.grid_edge_actor,
            True,
        )
        self._set_actor_visibility(
            self.grid_internal_edge_actor,
            True,
        )

        if self._is_fence_section_display_active():
            self._hide_grid_for_fence_section()
        else:
            self._apply_property_focus_grid_style()

        if render_now:
            self._render()

        return actor


    def render_grid(
        self,
        sim_data,
        render_now=True,
    ):
        self._remember_sim_data(sim_data)
        self._configure_preview_scene()

        if self.is_grid_visible():
            self.clear_grid(render_now=render_now)
            return None

        self.clear_grid(render_now=False)

        grid_data = getattr(
            sim_data,
            "static_grid_data",
            None,
        )

        if not isinstance(grid_data, dict):
            if render_now:
                self._render()
            return None

        try:
            nx = int(grid_data["nx"])
            ny = int(grid_data["ny"])
            nz = int(grid_data["nz"])
        except Exception:
            if render_now:
                self._render()
            return None

        total = nx * ny * nz

        values = np.ones(
            total,
            dtype=np.float64,
        )

        actnum = np.asarray(
            grid_data.get(
                "actnum",
                np.ones(total, dtype=np.int32),
            ),
            dtype=np.int32,
        )

        if actnum.size != total:
            actnum = np.ones(
                total,
                dtype=np.int32,
            )

        mask = actnum == 1

        grid = self._grid_helper._build_corner_point_property_grid(
            grid_data=grid_data,
            values=values,
            mask=mask,
            scalar_name="GridPreview",
        )

        if grid is None or grid.n_cells == 0:
            if render_now:
                self._render()
            return None

        (
            surface,
            surface_edges,
            internal_edges,
        ) = self._build_stable_corner_grid_surface_and_edges(
            grid
        )

        if (
            GRID_SHOW_EDGES
            and surface_edges is not None
            and surface_edges.n_points > 0
            and surface_edges.n_cells > 0
        ):
            self.grid_edge_actor = self.plotter.add_mesh(
                surface_edges,
                color=GRID_EDGE_COLOR,
                line_width=max(
                    float(GRID_EDGE_LINE_WIDTH),
                    1.0,
                ),
                opacity=1.0,
                lighting=False,
                render_lines_as_tubes=False,
                render=False,
            )

            self._configure_stable_grid_edge_actor(
                self.grid_edge_actor
            )

        if (
            GRID_SHOW_EDGES
            and internal_edges is not None
            and internal_edges.n_points > 0
            and internal_edges.n_cells > 0
        ):
            self.grid_internal_edge_actor = (
                self.plotter.add_mesh(
                    internal_edges,
                    color=GRID_EDGE_COLOR,
                    line_width=max(
                        float(GRID_EDGE_LINE_WIDTH),
                        1.0,
                    ),
                    opacity=1.0,
                    lighting=False,
                    render_lines_as_tubes=False,
                    render=False,
                )
            )

            self._configure_stable_grid_edge_actor(
                self.grid_internal_edge_actor
            )

            self._set_actor_visibility(
                self.grid_internal_edge_actor,
                self.show_internal_grid_edges,
            )

        if (
            GRID_SHOW_SURFACE
            and surface is not None
            and surface.n_points > 0
            and surface.n_cells > 0
        ):
            self.grid_actor = self.plotter.add_mesh(
                surface,
                color=GRID_SURFACE_COLOR,
                opacity=GRID_SURFACE_OPACITY,
                show_edges=False,
                lighting=False,
                smooth_shading=False,
                render=False,
            )

            self._configure_stable_grid_surface_actor(
                self.grid_actor
            )

        self._initialize_preview_camera_once(
            sim_data=sim_data,
            bounds=grid.bounds,
        )

        self.refresh_preview_stack(
            render_now=False,
        )

        if render_now:
            self._render()

        return self.grid_actor or self.grid_edge_actor

    @staticmethod
    def _pyvista_billboard_text_actor_class():
        """Return BillboardTextActor3D through PyVista's compatibility layer.

        This deliberately does not import ``vtk`` or ``vtkmodules``.  Different
        PyVista releases expose the compatibility namespace in different places,
        so all supported PyVista locations are checked.
        """
        namespaces = []

        namespace = getattr(pv, "_vtk", None)
        if namespace is not None:
            namespaces.append(namespace)

        for module_name in (
            "pyvista.plotting._vtk",
            "pyvista._vtk",
        ):
            try:
                namespace = importlib.import_module(module_name)
            except Exception:
                continue

            if namespace not in namespaces:
                namespaces.append(namespace)

        for namespace in namespaces:
            actor_class = getattr(
                namespace,
                "vtkBillboardTextActor3D",
                None,
            )

            if actor_class is not None:
                return actor_class

        return None

    @classmethod
    def _new_billboard_text_actor(cls):
        actor_class = cls._pyvista_billboard_text_actor_class()

        if actor_class is None:
            return None

        try:
            return actor_class()
        except Exception:
            return None

    @staticmethod
    def _set_text_property_flag(
        text_property,
        method_name,
        fallback_name,
        value,
    ):
        method = getattr(text_property, method_name, None)

        if callable(method):
            try:
                method()
                return
            except Exception:
                pass

        method = getattr(text_property, fallback_name, None)

        if callable(method):
            try:
                method(bool(value))
            except Exception:
                pass

    def _configure_well_name_billboard_actor(
        self,
        actor,
        label,
        point,
        font_size=None,
    ) -> bool:
        if actor is None:
            return False

        try:
            point = np.asarray(
                point,
                dtype=np.float64,
            ).reshape(3)
        except Exception:
            return False

        if not np.isfinite(point).all():
            return False

        try:
            actor.SetInput(str(label))
            actor.SetPosition(
                float(point[0]),
                float(point[1]),
                float(point[2]),
            )
        except Exception:
            return False

        try:
            actor.SetDisplayOffset(
                int(WELL_LABEL_PIXEL_OFFSET_X),
                int(WELL_LABEL_PIXEL_OFFSET_Y),
            )
        except Exception:
            pass

        try:
            text_property = actor.GetTextProperty()
        except Exception:
            text_property = None

        if text_property is not None:
            try:
                text_property.SetFontSize(
                    int(font_size if font_size is not None else WELL_LABEL_FONT_SIZE)
                )
            except Exception:
                pass

            try:
                text_property.SetColor(
                    *WELL_LABEL_TEXT_COLOR
                )
            except Exception:
                pass

            
            try:
                text_property.SetBackgroundOpacity(
                    0.0
                )
            except Exception:
                pass

            self._set_text_property_flag(
                text_property,
                "BoldOff",
                "SetBold",
                False,
            )
            self._set_text_property_flag(
                text_property,
                "ItalicOff",
                "SetItalic",
                False,
            )
            self._set_text_property_flag(
                text_property,
                "ShadowOff",
                "SetShadow",
                False,
            )

            try:
                text_property.SetJustificationToCentered()
            except Exception:
                pass

            try:
                text_property.SetVerticalJustificationToBottom()
            except Exception:
                try:
                    text_property.SetVerticalJustificationToCentered()
                except Exception:
                    pass

        try:
            actor.SetVisibility(True)
        except Exception:
            pass

        try:
            actor.PickableOff()
        except Exception:
            try:
                actor.SetPickable(False)
            except Exception:
                pass

        return True

    def _add_well_name_labels_with_point_labels(
        self,
        points,
        labels,
        font_size=None,
    ):
        """Fallback for PyVista builds without BillboardTextActor3D."""
        if self._well_labels_forced_hidden:
            return []

        label_points = np.asarray(
            points,
            dtype=np.float64,
        )
        label_values = list(labels)

        
        
        try:
            actor = self.plotter.add_point_labels(
                label_points,
                label_values,
                font_size=int(font_size if font_size is not None else WELL_LABEL_FONT_SIZE),
                text_color=WELL_LABEL_TEXT_COLOR,
                show_points=False,
                always_visible=True,
                shape=None,
                margin=0,
                reset_camera=False,
                render=False,
            )
        except (TypeError, ValueError):
            try:
                actor = self.plotter.add_point_labels(
                    label_points,
                    label_values,
                    font_size=int(font_size if font_size is not None else WELL_LABEL_FONT_SIZE),
                    text_color=WELL_LABEL_TEXT_COLOR,
                    show_points=False,
                    always_visible=True,
                    shape_opacity=0.0,
                    margin=0,
                    reset_camera=False,
                    render=False,
                )
            except TypeError:
                try:
                    actor = self.plotter.add_point_labels(
                        label_points,
                        label_values,
                        font_size=int(font_size if font_size is not None else WELL_LABEL_FONT_SIZE),
                        text_color=WELL_LABEL_TEXT_COLOR,
                        show_points=False,
                        always_visible=True,
                        reset_camera=False,
                        render=False,
                    )
                except Exception:
                    return []
            except Exception:
                return []
        except Exception:
            return []

        if actor is None:
            return []

        renderer = self._main_renderer()
        if renderer is not None:
            try:
                renderer.AddViewProp(actor)
            except Exception:
                pass

        try:
            actor.SetVisibility(True)
        except Exception:
            pass

        try:
            actor.PickableOff()
        except Exception:
            try:
                actor.SetPickable(False)
            except Exception:
                pass

        return [actor]

    def _add_well_name_labels(
        self,
        well_head_points,
        well_names,
        font_size=None,
    ):
        """Create one persistent label at each real well-head coordinate."""
        if self._well_labels_forced_hidden:
            return []

        if not well_head_points or not well_names:
            return []

        valid_points = []
        valid_labels = []

        for point, name in zip(
            well_head_points,
            well_names,
        ):
            try:
                point = np.asarray(
                    point,
                    dtype=np.float64,
                ).reshape(3)
            except Exception:
                continue

            label = str(name or "").strip()

            if not label or not np.isfinite(point).all():
                continue

            valid_points.append(point.copy())
            valid_labels.append(label)

        if not valid_points:
            return []

        renderer = self._main_renderer()
        actor_class = self._pyvista_billboard_text_actor_class()

        if renderer is not None and actor_class is not None:
            actors = []

            for point, label in zip(
                valid_points,
                valid_labels,
            ):
                actor = self._new_billboard_text_actor()

                if not self._configure_well_name_billboard_actor(
                    actor=actor,
                    label=label,
                    point=point,
                    font_size=font_size,
                ):
                    continue

                try:
                    renderer.AddViewProp(actor)
                except Exception:
                    try:
                        renderer.AddActor(actor)
                    except Exception:
                        continue

                actors.append(actor)

            if actors:
                return actors

        return self._add_well_name_labels_with_point_labels(
            points=valid_points,
            labels=valid_labels,
            font_size=font_size,
        )

    def _rebuild_well_name_labels(
        self,
        font_size=None,
    ):
        if self._well_labels_forced_hidden:
            self._remove_actor_list(self.well_label_actors)
            self.well_label_actors = []
            return False

        if not self._well_label_points or not self._well_label_texts:
            return False

        self._remove_actor_list(self.well_label_actors)
        self.well_label_actors = []

        label_actors = self._add_well_name_labels(
            well_head_points=self._well_label_points,
            well_names=self._well_label_texts,
            font_size=font_size,
        )

        if not label_actors:
            return False

        self.well_label_actors.extend(label_actors)
        self._well_label_use_billboard = any(
            getattr(actor, 'GetTextProperty', None) is not None
            for actor in label_actors
        )
        self._well_label_current_font_size = int(
            font_size if font_size is not None else self._current_well_label_font_size()
        )
        self._ensure_well_name_labels_attached()
        return True

    def _ensure_well_name_labels_attached(self):
        """Keep label props attached after renderer-order refresh operations."""
        if self._well_labels_forced_hidden:
            self._remove_actor_list(self.well_label_actors)
            self.well_label_actors = []
            return False

        if not self.well_label_actors:
            return False

        renderer = self._main_renderer()

        if renderer is None:
            return False

        attached = False

        for actor in self.well_label_actors:
            if actor is None:
                continue

            already_present = False

            try:
                already_present = bool(
                    renderer.HasViewProp(actor)
                )
            except Exception:
                pass

            if not already_present:
                try:
                    renderer.AddViewProp(actor)
                    attached = True
                except Exception:
                    try:
                        renderer.AddActor(actor)
                        attached = True
                    except Exception:
                        continue

            try:
                actor.SetVisibility(True)
            except Exception:
                pass

        return attached

    def render_wells(
        self,
        sim_data,
        render_now=True,
    ):
        self._remember_sim_data(sim_data)
        self._configure_preview_scene()

        if self.is_wells_visible():
            self.clear_wells(
                render_now=render_now
            )
            return False

        self.clear_wells(
            render_now=False
        )

        well_data = self._resolved_well_data(
            sim_data
        )
        if not isinstance(
            well_data,
            dict,
        ):
            if render_now:
                self._render()
            return False

        wells = well_data.get(
            "wells",
            [],
        )
        if not isinstance(
            wells,
            list,
        ) or not wells:
            if render_now:
                self._render()
            return False

        vertical_mode = str(
            well_data.get("vertical_mode")
            or "elevation_z"
        )
        z_transform = self._build_geometry_z_transform(
            z_values=self._well_trajectory_z_values(
                well_data
            ),
            grid_z_bounds=self._static_grid_z_bounds(
                sim_data
            ),
        )
        source_z_transform = (
            self._raw_geometry_z_transform_for_wells(
                well_data
            )
        )

        perforation_data = (
            self._resolved_perforation_data(
                sim_data
            )
        )
        perforation_geometry_by_well = (
            self._calculated_perforation_geometry_by_well(
                perforation_data,
                z_transform=z_transform,
                source_z_transform=source_z_transform,
            )
        )

        count = 0
        self._well_actor_groups = {}
        self._well_label_anchor_by_name = {}

        for well in wells:
            if not isinstance(
                well,
                dict,
            ):
                continue

            well_name = str(
                well.get("well_name")
                or ""
            ).strip()
            raw_track = well.get(
                "rows",
                [],
            )
            if not isinstance(
                raw_track,
                list,
            ):
                continue

            valid_points = []

            for point in raw_track:
                if not isinstance(
                    point,
                    dict,
                ):
                    continue

                try:
                    md = float(
                        point["md_m"]
                    )
                    x = float(
                        point["x_m"]
                    )
                    y = float(
                        point["y_m"]
                    )
                    raw_z = (
                        self._trajectory_point_z(
                            point,
                            vertical_mode,
                        )
                    )
                    z = float(
                        z_transform(raw_z)
                    )
                except (
                    KeyError,
                    TypeError,
                    ValueError,
                ):
                    continue

                if not np.isfinite(
                    [md, x, y, z]
                ).all():
                    continue

                valid_points.append(
                    (
                        md,
                        np.asarray(
                            [x, y, z],
                            dtype=np.float64,
                        ),
                    )
                )

            if len(valid_points) < 2:
                continue

            valid_points.sort(
                key=lambda item: item[0]
            )

            ordered_points = []
            clean_valid_points = []

            for md, xyz in valid_points:
                if (
                    clean_valid_points
                    and abs(
                        md
                        - clean_valid_points[-1][0]
                    )
                    <= 1.0e-10
                ):
                    clean_valid_points[-1] = (
                        md,
                        xyz,
                    )
                    if ordered_points:
                        ordered_points[-1] = xyz
                    continue

                clean_valid_points.append(
                    (
                        md,
                        xyz,
                    )
                )

                if (
                    not ordered_points
                    or np.linalg.norm(
                        xyz
                        - ordered_points[-1]
                    )
                    > 1.0e-8
                ):
                    ordered_points.append(
                        xyz
                    )

            valid_points = clean_valid_points

            if (
                len(valid_points) < 2
                or len(ordered_points) < 2
            ):
                continue

            # 射孔段直接使用前端计算结果中保存的起点、中心和终点 XYZ。
            # MD 只用于维持这些已保存点在 DEV 轨迹中的先后顺序。
            active_perforation_geometry = (
                perforation_geometry_by_well.get(
                    well_name,
                    [],
                )
                if self.show_perforation_segments
                else []
            )
            track_segments = (
                self._split_track_by_perforation_geometry(
                    valid_points,
                    active_perforation_geometry,
                )
            )

            if not track_segments:
                continue

            rendered_segment_count = 0
            well_group = {
                "well_actors": [],
                "perforation_segment_actors": [],
                "perforation_point_actors": [],
                # 兼容旧代码读取该键。
                "perforation_actors": [],
            }

            for segment in track_segments:
                is_perforation = bool(
                    segment["is_perforation"]
                )

                actor = (
                    self._add_well_track_segment_actor(
                        sim_data=sim_data,
                        points=segment["points"],
                        color=(
                            self.perforation_color
                            if is_perforation
                            else self.well_color
                        ),
                        opacity=(
                            PERFORATION_OPACITY
                            if is_perforation
                            else WELL_OPACITY
                        ),
                    )
                )

                if actor is None:
                    continue

                if is_perforation:
                    self.perforation_segment_actors.append(
                        actor
                    )
                    self.perforation_actors.append(
                        actor
                    )
                    well_group[
                        "perforation_segment_actors"
                    ].append(actor)
                    well_group[
                        "perforation_actors"
                    ].append(actor)
                else:
                    self.well_actors.append(
                        actor
                    )
                    well_group[
                        "well_actors"
                    ].append(actor)

                rendered_segment_count += 1

            if rendered_segment_count == 0:
                continue

            # 射孔点直接使用前端计算结果中保存的中心 XYZ。
            perforation_points = []

            for record in (
                perforation_geometry_by_well.get(
                    well_name,
                    [],
                )
                or []
            ):
                point = record.get("center_xyz")
                if point is None:
                    continue

                point = np.asarray(
                    point,
                    dtype=np.float64,
                ).reshape(3)

                if not np.isfinite(point).all():
                    continue

                if any(
                    np.linalg.norm(
                        point - existing
                    ) <= 1.0e-8
                    for existing in perforation_points
                ):
                    continue

                perforation_points.append(point)

            if perforation_points:
                point_actor = (
                    self._add_perforation_points_actor(
                        perforation_points
                    )
                )

                if point_actor is not None:
                    self.perforation_point_actors.append(
                        point_actor
                    )
                    self.perforation_actors.append(
                        point_actor
                    )
                    well_group[
                        "perforation_point_actors"
                    ].append(
                        point_actor
                    )
                    well_group[
                        "perforation_actors"
                    ].append(
                        point_actor
                    )

            if well_name:
                self._well_actor_groups[
                    well_name
                ] = well_group

                well_visible = (
                    well_name
                    not in self._hidden_well_names
                )

                for actor in well_group[
                    "well_actors"
                ]:
                    self._set_actor_visibility(
                        actor,
                        well_visible,
                    )

                for actor in well_group[
                    "perforation_segment_actors"
                ]:
                    self._set_actor_visibility(
                        actor,
                        well_visible
                        and self.show_perforation_segments,
                    )

                for actor in well_group[
                    "perforation_point_actors"
                ]:
                    self._set_actor_visibility(
                        actor,
                        well_visible
                        and self.show_perforation_points,
                    )

                label_point = (
                    self._well_name_label_point(
                        sim_data=sim_data,
                        ordered_points=ordered_points,
                    )
                )

                if label_point is not None:
                    self._well_label_anchor_by_name[
                        well_name
                    ] = (
                        np.asarray(
                            label_point,
                            dtype=np.float64,
                        ).reshape(3).copy()
                    )

            count += 1

        self._rebuild_visible_well_name_labels(
            font_size=(
                self._current_well_label_font_size()
            ),
        )

        if self._well_labels_forced_hidden:
            self.set_well_labels_forced_hidden(
                True,
                render_now=False,
            )

        if count > 0:
            self._wells_render_revision = (
                self._scene_geometry_revision
            )
            self._initialize_preview_camera_once(
                sim_data=sim_data,
                bounds=self._actors_bounds(
                    [
                        actor
                        for actor in [
                            *(
                                self.well_actors
                                or []
                            ),
                            *(
                                self.perforation_actors
                                or []
                            ),
                        ]
                        if self._actor_is_visible(
                            actor
                        )
                    ]
                ),
            )
            self.refresh_preview_stack(
                render_now=False
            )

            if self.well_label_actors:
                self._ensure_well_name_labels_attached()
                self._reset_well_label_zoom_reference()
        else:
            self._wells_render_revision = -1

        if render_now:
            self._render()

        return count > 0


    def render_natural_fractures(
        self,
        sim_data,
        render_now=True,
    ):
        self._remember_sim_data(sim_data)
        self._configure_preview_scene()

        if self.is_natural_fractures_visible():
            self.clear_natural_fractures(render_now=render_now)
            return False

        self.clear_natural_fractures(render_now=False)

        count = self._render_natural_fractures(
            sim_data,
        )

        if count > 0:
            self._natural_fractures_render_revision = (
                self._scene_geometry_revision
            )
            self._initialize_preview_camera_once(
                sim_data=sim_data,
                bounds=self._actors_bounds(
                    self.natural_fracture_actors,
                ),
            )
            self.refresh_preview_stack(
                render_now=False,
            )
        else:
            self._natural_fractures_render_revision = -1

        if render_now:
            self._render()

        return count > 0

    def _render_natural_fractures(
        self,
        sim_data,
    ):
        fractures = self._resolved_natural_fractures(
            sim_data
        )

        if not isinstance(fractures, list) or not fractures:
            return 0

        grid_z_bounds = self._static_grid_z_bounds(sim_data)

        z_transform = self._build_geometry_z_transform(
            z_values=self._natural_fracture_z_values(fractures),
            grid_z_bounds=grid_z_bounds,
        )

        count = 0

        for fracture in fractures:
            if not isinstance(fracture, dict):
                continue

            vertices = fracture.get(
                "vertices",
                [],
            )

            points = self._safe_points(vertices)

            if points is None or len(points) < 3:
                continue

            points = self._apply_z_transform_to_points(
                points,
                z_transform,
            )

            if points is None or len(points) < 3:
                continue

            actors = self._add_fracture_polygon(
                points=points,
                color=self.natural_fracture_color,
                edge_color=self.natural_fracture_edge_color,
            )

            if actors:
                self.natural_fracture_actors.extend(actors)
                count += 1

        return count

    def render_hydraulic_fractures(
        self,
        sim_data,
        render_now=True,
    ):
        self._remember_sim_data(sim_data)
        self._configure_preview_scene()

        if self.is_hydraulic_fractures_visible():
            self.clear_hydraulic_fractures(render_now=render_now)
            return False

        self.clear_hydraulic_fractures(render_now=False)

        count = self._render_hydraulic_fractures(
            sim_data,
        )

        if count > 0:
            self._hydraulic_fractures_render_revision = (
                self._scene_geometry_revision
            )
            self._initialize_preview_camera_once(
                sim_data=sim_data,
                bounds=self._actors_bounds(
                    self.hydraulic_fracture_actors,
                ),
            )
            self.refresh_preview_stack(
                render_now=False,
            )
        else:
            self._hydraulic_fractures_render_revision = -1

        if render_now:
            self._render()

        return count > 0

    def _render_hydraulic_fractures(
        self,
        sim_data,
    ):
        fractures = self._resolved_hydraulic_fractures(
            sim_data
        )

        if not isinstance(fractures, list) or not fractures:
            return 0

        grid_z_bounds = self._static_grid_z_bounds(
            sim_data
        )

        # 人工裂缝由射孔位置生成，本质上与 DEV 井轨迹使用同一套
        # 原始 Z 坐标。不能再根据“人工裂缝自身的窄 Z 范围”单独
        # 猜测翻转方向，否则井轨迹可能判定为 z -> -z，而位于深部的
        # 人工裂缝因其局部范围未与网格重叠而保持原值，最终井和裂缝
        # 会被渲染到场景两侧。优先使用整套 DEV 轨迹确定统一变换。
        well_data = self._resolved_well_data(sim_data)
        source_z_transform = (
            self._raw_geometry_z_transform_for_wells(
                well_data
            )
        )
        well_z_values = (
            self._well_trajectory_z_values(well_data)
            if isinstance(well_data, dict)
            else []
        )
        fracture_z_values = []
        for fracture in fractures:
            if not isinstance(fracture, dict):
                continue
            well_name = str(
                fracture.get("well_name") or ""
            ).strip()
            points = self._fracture_record_points(
                fracture
            )
            if points is None:
                continue
            for point in points:
                try:
                    value = source_z_transform(
                        point[2],
                        well_name,
                    )
                except (TypeError, ValueError, IndexError):
                    continue
                if np.isfinite(value):
                    fracture_z_values.append(float(value))
        z_transform = self._build_geometry_z_transform(
            z_values=(
                well_z_values
                if well_z_values
                else fracture_z_values
            ),
            grid_z_bounds=grid_z_bounds,
        )

        count = 0

        for fracture in fractures:
            well_name = str(
                fracture.get("well_name") or ""
            ).strip()
            points = self._safe_points(
                fracture.get(
                    "vertices",
                    fracture.get("points", []),
                )
            )

            if points is None or len(points) < 3:
                continue

            points = self._apply_z_transform_to_points(
                points,
                lambda z, current_well=well_name: z_transform(
                    source_z_transform(
                        z,
                        current_well,
                    )
                ),
            )

            if points is None or len(points) < 3:
                continue

            actors = self._add_fracture_polygon(
                points=points,
                color=self.hydraulic_fracture_color,
                edge_color=self.hydraulic_fracture_edge_color,
            )

            if actors:
                self.hydraulic_fracture_actors.extend(
                    actors
                )
                count += 1

        return count


    def render_fractures(
        self,
        sim_data,
        render_now=True,
    ):
        self._remember_sim_data(sim_data)
        self._configure_preview_scene()

        if self.is_fractures_visible():
            self.clear_fractures(render_now=render_now)
            return False

        self.clear_fractures(render_now=False)

        natural_count = self._render_natural_fractures(
            sim_data,
        )

        hydraulic_count = self._render_hydraulic_fractures(
            sim_data,
        )
        total_count = natural_count + hydraulic_count

        if total_count > 0:
            self._natural_fractures_render_revision = (
                self._scene_geometry_revision
                if natural_count > 0
                else -1
            )
            self._hydraulic_fractures_render_revision = (
                self._scene_geometry_revision
                if hydraulic_count > 0
                else -1
            )
            fracture_actors = [
                *(self.natural_fracture_actors or []),
                *(self.hydraulic_fracture_actors or []),
            ]

            self._initialize_preview_camera_once(
                sim_data=sim_data,
                bounds=self._actors_bounds(
                    fracture_actors,
                ),
            )
            self.refresh_preview_stack(
                render_now=False,
            )
        else:
            self._natural_fractures_render_revision = -1
            self._hydraulic_fractures_render_revision = -1

        if render_now:
            self._render()

        return total_count > 0

    def _static_grid_z_bounds(self, sim_data):
        grid_data = getattr(
            sim_data,
            "static_grid_data",
            None,
        )

        if not isinstance(grid_data, dict):
            return None

        z_values = []

        zcorn = grid_data.get(
            "zcorn",
            None,
        )

        if zcorn is not None:
            try:
                array = np.asarray(
                    zcorn,
                    dtype=np.float64,
                )

                finite = array[
                    np.isfinite(array)
                ]

                if finite.size > 0:
                    z_values.extend(
                        finite.tolist()
                    )

            except Exception:
                pass

        if not z_values:
            coord = grid_data.get(
                "coord",
                None,
            )

            if coord is not None:
                try:
                    coord_array = np.asarray(
                        coord,
                        dtype=np.float64,
                    ).reshape(
                        -1,
                        6,
                    )

                    z0 = coord_array[:, 2]
                    z1 = coord_array[:, 5]

                    z_array = np.concatenate(
                        [
                            z0,
                            z1,
                        ]
                    )

                    finite = z_array[
                        np.isfinite(z_array)
                    ]

                    if finite.size > 0:
                        z_values.extend(
                            finite.tolist()
                        )

                except Exception:
                    pass

        return self._finite_range(
            z_values,
        )

    @staticmethod
    def _natural_fracture_z_values(fractures):
        z_values = []

        if not isinstance(fractures, list):
            return z_values

        for fracture in fractures:
            if not isinstance(fracture, dict):
                continue

            vertices = fracture.get(
                "vertices",
                [],
            )

            points = GeometryPreviewRenderer._safe_points(
                vertices,
            )

            if points is None:
                continue

            z_values.extend(
                points[:, 2].tolist()
            )

        return z_values

    @staticmethod
    def _hydraulic_fracture_z_values(fractures):
        """读取新人工裂缝记录中的 vertices/points/corners 的 Z。"""
        z_values = []
        if not isinstance(fractures, list):
            return z_values

        for fracture in fractures:
            points = GeometryPreviewRenderer._fracture_record_points(
                fracture
            )
            if points is None:
                continue
            array = np.asarray(points, dtype=np.float64).reshape(-1, 3)
            z_values.extend(array[:, 2].tolist())
        return z_values


    @staticmethod
    def _finite_range(values):
        try:
            array = np.asarray(
                values,
                dtype=np.float64,
            )

        except (
            TypeError,
            ValueError,
        ):
            return None

        if array.size == 0:
            return None

        array = array[
            np.isfinite(array)
        ]

        if array.size == 0:
            return None

        return (
            float(np.min(array)),
            float(np.max(array)),
        )

    @staticmethod
    def _ranges_overlap(range_a, range_b, tolerance=0.0):
        if range_a is None or range_b is None:
            return False

        a_min, a_max = [
            float(value)
            for value in range_a
        ]

        b_min, b_max = [
            float(value)
            for value in range_b
        ]

        if a_max < a_min:
            a_min, a_max = a_max, a_min

        if b_max < b_min:
            b_min, b_max = b_max, b_min

        tolerance = max(
            float(tolerance),
            0.0,
        )

        return (
            a_min <= b_max + tolerance
            and b_min <= a_max + tolerance
        )

    def _build_geometry_z_transform(
        self,
        z_values,
        grid_z_bounds,
    ):
        input_range = self._finite_range(
            z_values,
        )

        if input_range is None:
            return lambda z: z

        if grid_z_bounds is None:
            return lambda z: z

        input_min, input_max = [
            float(value)
            for value in input_range
        ]

        grid_min, grid_max = [
            float(value)
            for value in grid_z_bounds
        ]

        if grid_max < grid_min:
            grid_min, grid_max = grid_max, grid_min

        if input_max < input_min:
            input_min, input_max = input_max, input_min

        grid_span = max(
            abs(grid_max - grid_min),
            GEOMETRY_Z_ABS_TOL,
        )

        input_span = max(
            abs(input_max - input_min),
            GEOMETRY_Z_ABS_TOL,
        )

        grid_tol = max(
            grid_span * GEOMETRY_Z_TOL_RATIO,
            GEOMETRY_Z_ABS_TOL,
        )

        local_depth_tol = max(
            grid_span * GEOMETRY_Z_LOCAL_DEPTH_TOL_RATIO,
            GEOMETRY_Z_ABS_TOL,
        )

        if self._ranges_overlap(
            (input_min, input_max),
            (grid_min, grid_max),
            grid_tol,
        ):
            return lambda z: z

        flipped_range = (
            -input_max,
            -input_min,
        )

        if self._ranges_overlap(
            flipped_range,
            (grid_min, grid_max),
            grid_tol,
        ):
            return lambda z: -z

        looks_like_local_depth = (
            input_min >= -local_depth_tol
            and input_span <= grid_span + local_depth_tol
        )

        shifted_range = (
            input_min + grid_min,
            input_max + grid_min,
        )

        if (
            looks_like_local_depth
            and self._ranges_overlap(
                shifted_range,
                (grid_min, grid_max),
                local_depth_tol,
            )
        ):
            return lambda z: z + grid_min

        return lambda z: z

    def _apply_z_transform_to_points(
        self,
        points,
        z_transform,
    ):
        points = self._safe_points(points)

        if points is None:
            return None

        transformed = points.copy()

        try:
            transformed[:, 2] = np.asarray(
                [
                    float(
                        z_transform(
                            float(z)
                        )
                    )
                    for z in transformed[:, 2]
                ],
                dtype=np.float64,
            )

        except Exception:
            return points

        mask = np.isfinite(
            transformed,
        ).all(
            axis=1,
        )

        transformed = transformed[
            mask
        ]

        if transformed.shape[0] == 0:
            return None

        return transformed

    @staticmethod
    def _polyline_from_points(points):
        if points is None or len(points) < 2:
            return None

        pts = np.asarray(
            points,
            dtype=np.float64,
        )

        if pts.ndim != 2 or pts.shape[1] != 3:
            return None

        if not np.isfinite(pts).all():
            return None

        lines = [len(pts)]

        for index in range(len(pts)):
            lines.append(index)

        polyline = pv.PolyData()
        polyline.points = pts
        polyline.lines = np.asarray(
            lines,
            dtype=np.int64,
        )

        return polyline

    @staticmethod
    def _safe_points(points):
        try:
            array = np.asarray(
                points,
                dtype=np.float64,
            )

        except (
            TypeError,
            ValueError,
        ):
            return None

        if array.size == 0:
            return None

        try:
            array = array.reshape(
                -1,
                3,
            )

        except ValueError:
            return None

        mask = np.isfinite(array).all(axis=1)
        array = array[mask]

        if array.shape[0] == 0:
            return None

        return array


    @staticmethod
    def _order_fracture_points(points):
        points = GeometryPreviewRenderer._safe_points(points)

        if points is None or len(points) < 3:
            return None

        unique_points = []

        for point in points:
            if not unique_points:
                unique_points.append(point)
                continue

            if all(
                np.linalg.norm(point - existing) > 1.0e-8
                for existing in unique_points
            ):
                unique_points.append(point)

        if len(unique_points) < 3:
            return None

        points = np.asarray(
            unique_points,
            dtype=np.float64,
        )

        center = np.mean(
            points,
            axis=0,
        )
        centered = points - center

        try:
            _, singular_values, vh = np.linalg.svd(
                centered,
                full_matrices=False,
            )
        except Exception:
            return points

        if vh.shape[0] < 2:
            return points

        axis_u = vh[0]
        axis_v = vh[1]

        projected_u = centered @ axis_u
        projected_v = centered @ axis_v

        angles = np.arctan2(
            projected_v,
            projected_u,
        )
        radii = (
            projected_u * projected_u
            + projected_v * projected_v
        )

        order = np.lexsort(
            (
                radii,
                angles,
            )
        )
        ordered = points[order]

        if len(ordered) >= 3:
            polygon_normal = np.zeros(
                3,
                dtype=np.float64,
            )

            for index in range(len(ordered)):
                current_point = ordered[index]
                next_point = ordered[
                    (index + 1) % len(ordered)
                ]
                polygon_normal += np.cross(
                    current_point - center,
                    next_point - center,
                )

            reference_normal = vh[-1]

            if np.dot(
                polygon_normal,
                reference_normal,
            ) < 0.0:
                ordered = ordered[::-1]

        return ordered

    def _add_fracture_polygon(
        self,
        points,
        color,
        edge_color,
    ):
        points = self._order_fracture_points(
            points
        )

        if points is None or len(points) < 3:
            return []

        cleaned_points = []

        for point in points:
            if not cleaned_points:
                cleaned_points.append(point)
                continue

            if np.linalg.norm(point - cleaned_points[-1]) > 1e-8:
                cleaned_points.append(point)

        if (
            len(cleaned_points) >= 2
            and np.linalg.norm(cleaned_points[0] - cleaned_points[-1]) <= 1e-8
        ):
            cleaned_points.pop()

        if len(cleaned_points) < 3:
            return []

        points = np.asarray(
            cleaned_points,
            dtype=np.float64,
        )

        actors = []

        try:
            polygon = pv.PolyData()
            polygon.points = points
            polygon.faces = np.asarray(
                [len(points), *range(len(points))],
                dtype=np.int64,
            )

            actor = self.plotter.add_mesh(
                polygon,
                style="surface",
                color=color,
                opacity=FRACTURE_OPACITY,
                show_edges=False,
                edge_color=edge_color,
                line_width=0.0,
                lighting=FRACTURE_LIGHTING,
                smooth_shading=FRACTURE_SMOOTH_SHADING,
                ambient=FRACTURE_AMBIENT,
                diffuse=FRACTURE_DIFFUSE,
                specular=FRACTURE_SPECULAR,

                render=False,
            )

            self._configure_depth_sorted_geometry_actor(actor)
            actors.append(actor)

            if (
                self.fracture_show_edges
                and self.fracture_edge_line_width > 0.0
            ):
                edge_lines = []

                for index in range(len(points)):
                    start_point = points[index]
                    end_point = points[(index + 1) % len(points)]

                    edge_lines.append(
                        pv.Line(
                            start_point,
                            end_point,
                        )
                    )

                if edge_lines:
                    edge_actor = self.plotter.add_mesh(
                        pv.MultiBlock(edge_lines),
                        color=edge_color,
                        opacity=FRACTURE_OPACITY,
                        line_width=self.fracture_edge_line_width,
                        lighting=False,
                        render=False,
                    )

                    self._configure_depth_sorted_geometry_actor(edge_actor)
                    actors.append(edge_actor)

            return actors

        except Exception:
            return []

    def _remove_actor(self, actor):
        if actor is None:
            return

        overlay_renderer = getattr(
            self.host,
            "_geometry_preview_overlay_renderer",
            None,
        )

        if overlay_renderer is not None:
            try:
                overlay_renderer.RemoveActor2D(actor)
            except Exception:
                pass

            try:
                overlay_renderer.RemoveActor(actor)
            except Exception:
                try:
                    overlay_renderer.RemoveViewProp(actor)
                except Exception:
                    pass

        main_renderer = self._main_renderer()

        if main_renderer is not None:
            try:
                main_renderer.RemoveActor2D(actor)
            except Exception:
                pass

            try:
                main_renderer.RemoveActor(actor)
            except Exception:
                try:
                    main_renderer.RemoveViewProp(actor)
                except Exception:
                    pass

        if hasattr(self.host, "_remove_actor"):
            try:
                self.host._remove_actor(actor)
                return
            except Exception:
                pass

        try:
            self.plotter.remove_actor(
                actor,
                render=False,
            )
        except Exception:
            pass

    def _remove_actor_list(self, actors):
        for actor in actors or []:
            self._remove_actor(actor)

    def _render(self):
        self.prepare_scene_for_render()

        static_preview = getattr(
            self.host,
            "static_property_preview",
            None,
        )

        layer_preview_active = False

        if static_preview is not None and hasattr(
            static_preview,
            "refresh_layer_clipping_range",
        ):
            try:
                layer_preview_active = bool(
                    static_preview.refresh_layer_clipping_range(
                        render_now=False,
                    )
                )
            except Exception:
                layer_preview_active = False

        if (
            not layer_preview_active
            and (
                self._geometry_top_actors()
                or self._has_visible_preview_background()
            )
        ):
            self._apply_stable_scene_clipping_range()

        if hasattr(self.host, "_render"):
            self.host._render()
        else:
            self.plotter.render()


GeometryLayerRenderer = GeometryPreviewRenderer
