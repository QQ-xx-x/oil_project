"""
基于 PyVista 的可视化渲染器。
"""


from __future__ import annotations

import sys
import time
from pathlib import Path

def get_bright_jet_cmap():
    from matplotlib.colors import LinearSegmentedColormap
    bright_jet_colors = [
        (0.00, (0.00, 1.00, 1.00)),
        (0.04, (0.00, 1.00, 0.95)),
        (0.08, (0.00, 1.00, 0.88)),
        (0.12, (0.00, 1.00, 0.78)),
        (0.16, (0.00, 1.00, 0.65)),
        (0.20, (0.00, 1.00, 0.52)),
        (0.24, (0.00, 1.00, 0.40)),
        (0.26, (0.00, 1.00, 0.35)),
        (0.30, (0.08, 1.00, 0.22)),
        (0.34, (0.18, 1.00, 0.10)),
        (0.38, (0.32, 1.00, 0.02)),
        (0.42, (0.48, 1.00, 0.00)),
        (0.46, (0.62, 1.00, 0.00)),
        (0.50, (0.78, 1.00, 0.00)),
        (0.54, (0.92, 1.00, 0.00)),
        (0.58, (1.00, 1.00, 0.00)),
        (0.63, (1.00, 0.94, 0.00)),
        (0.68, (1.00, 0.86, 0.00)),
        (0.73, (1.00, 0.76, 0.00)),
        (0.78, (1.00, 0.64, 0.00)),
        (0.84, (1.00, 0.48, 0.00)),
        (0.90, (1.00, 0.34, 0.00)),
        (0.95, (1.00, 0.18, 0.00)),
        (1.00, (1.00, 0.00, 0.00)),
    ]
    return LinearSegmentedColormap.from_list("bright_jet", bright_jet_colors, N=4096)

def _ensure_local_pyvista_site() -> None:
    project_root = Path(__file__).resolve().parent.parent
    local_site = project_root / ".deps" / "pyvista_site"
    local_site_str = str(local_site)
    if local_site.exists() and local_site_str not in sys.path:
        sys.path.append(local_site_str)

_ensure_local_pyvista_site()

import numpy as np
import pyvista as pv

COORDINATE_APPROX_DIVISIONS = 6
COORDINATE_LABEL_FONT_SIZE = 12
COORDINATE_TICK_LENGTH_RATIO = 0.010
COORDINATE_TICK_LABEL_OFFSET_RATIO = 0.025
COORDINATE_AXIS_TITLE_GAP_RATIO = 0.028
COORDINATE_LABEL_DEPTH_OFFSET_RATIO = 0.003
COORDINATE_LABEL_SCREEN_EPSILON_PX = 2.0

COORDINATE_STANDARD_VIEW_COS_THRESHOLD = 0.999

RESULT_PROPERTY_OPACITY = 0.8

RESULT_PRESSURE_OPACITY = RESULT_PROPERTY_OPACITY
RESULT_PRESSURE_INTERPOLATE_BEFORE_MAP = False

RESULT_PROPERTY_BACKFACE_CULLING = True
RESULT_PROPERTY_MERGE_SHARED_POINTS = True
RESULT_PROPERTY_POINT_MERGE_TOLERANCE_RATIO = 1.0e-9
RESULT_PROPERTY_POINT_MERGE_ABSOLUTE_TOLERANCE = 1.0e-8

RESULT_BOUNDARY_POINT_TOLERANCE_RATIO = 1.0e-8
RESULT_BOUNDARY_POINT_TOLERANCE_ABSOLUTE = 1.0e-6
RESULT_BOUNDARY_CHECK_NONCONFORMING = True
RESULT_BOUNDARY_OUTSIDE_OFFSET_RATIO = 2.0e-5
RESULT_BOUNDARY_OUTSIDE_OFFSET_ABSOLUTE = 1.0e-5
RESULT_BOUNDARY_OUTSIDE_OFFSET_MULTIPLIERS = (1.0, 5.0, 25.0)
RESULT_BOUNDARY_FACE_BATCH_SIZE = 20000
RESULT_BOUNDARY_SAMPLE_UV = (
    (0.25, 0.25),
    (0.50, 0.25),
    (0.75, 0.25),
    (0.25, 0.50),
    (0.50, 0.50),
    (0.75, 0.50),
    (0.25, 0.75),
    (0.50, 0.75),
    (0.75, 0.75),
)


RESULT_GRID_SURFACE_OPACITY = 0.6
RESULT_GRID_EDGE_OPACITY = 1.0

RESULT_GRID_PROPERTY_FOCUS_MODE = True
RESULT_GRID_PROPERTY_SURFACE_OPACITY = 0.0
RESULT_GRID_PROPERTY_EDGE_OPACITY = 0.3
RESULT_GRID_RENDER_LINES_AS_TUBES = False

RESULT_GRID_LINE_OFFSET_FACTOR = -1.0
RESULT_GRID_LINE_OFFSET_UNITS = -1.0
RESULT_GRID_SURFACE_OFFSET_FACTOR = 1.0
RESULT_GRID_SURFACE_OFFSET_UNITS = 1.0

RESULT_RENDER_STYLE_VERSION = "unified-preview-result-picking-v3"

RESULT_WELL_LABEL_FONT_SIZE = 12
RESULT_WELL_LABEL_MIN_FONT_SIZE = 8
RESULT_WELL_LABEL_MAX_FONT_SIZE = 36
RESULT_WELL_LABEL_ZOOM_EXPONENT = 0.80
RESULT_WELL_LABEL_TEXT_COLOR = (0.05, 0.05, 0.05)
RESULT_WELL_LABEL_OFFSET_SCENE_RATIO = 0.012
RESULT_WELL_LABEL_OFFSET_RADIUS_MULTIPLIER = 4.0
RESULT_WELL_RADIUS = 2.0

RESULT_GEOMETRY_OPACITY = 1.0
RESULT_DEPTH_PEEL_COUNT = 100
RESULT_DEPTH_PEEL_OCCLUSION_RATIO = 0.0
RESULT_ENABLE_ANTI_ALIASING = True

RESULT_GEOMETRY_ACTOR_CACHE_KEYS = ()

RESULT_PROPERTY_ACTOR_CACHE_KEYS = (
    "pressure_actor",
    "pressure_field_actor",
    "layer_pressure_actor",
    "sw_field_actor",
    "layer_sw_actor",
    "phi_field_actor",
    "layer_phi_actor",
    "threshold_actor",
    "perm_field_actor",
    "layer_perm_actor",
    "time_playback_actor",
)

RESULT_GRID_SURFACE_ACTOR_CACHE_KEYS = (
    "corner_surface_actor",
)

RESULT_GRID_EDGE_ACTOR_CACHE_KEYS = (
    "grid_lines_actor",
    "corner_actor",
    "corner_lgr_parent_grid_actor",
    "corner_lgr_refined_grid_actor",
    "layer_coarse_grid_actor",
    "layer_sw_coarse_grid_actor",
    "threshold_grid_actor",
    "layer_phi_coarse_grid_actor",
    "layer_perm_coarse_grid_actor",
)

RESULT_WELL_LABEL_ACTOR_CACHE_KEYS = ()

RESULT_WELL_ACTOR_TO_LABEL_CACHE = ()

RESULT_MAIN_SCENE_ACTOR_CACHE_KEYS = (
    "corner_actor",
    "corner_surface_actor",
    "grid_lines_actor",
    "corner_lgr_parent_grid_actor",
    "corner_lgr_refined_grid_actor",
    "layer_coarse_grid_actor",
    "layer_sw_coarse_grid_actor",
    "threshold_grid_actor",
    "layer_phi_coarse_grid_actor",
    "layer_perm_coarse_grid_actor",
    *RESULT_PROPERTY_ACTOR_CACHE_KEYS,
)


class PyVistaRenderer:
    """基于 PyVista 的渲染器，并保留对旧 VTK 渲染器接口的兼容面。"""

    def __init__(self, qt_view):
        self.vtk_widget = qt_view
        self.plotter = qt_view.plotter
        self.renderer = qt_view.renderer
        self.cache = self._new_cache()
        self._parsed_well_data = None
        self.view = qt_view
        self.pv_renderer = qt_view.renderer

        self._result_geometry_overlay_renderer = None
        self._result_geometry_overlay_layer = None
        self._result_geometry_overlay_attached = False
        self._result_geometry_overlay_main_renderer = None

        self._result_clipping_observer_ids = []
        self._result_well_label_reference_view_scale = None
        self._result_well_label_current_font_size = None

        
        self._property_switch_camera_state = None
        self._preserve_camera_on_property_switch = False
 
        self._active_property_context = None
        self._property_display_mode = "full"

        self._result_translucent_scene_configured = False

        pv.global_theme.allow_empty_mesh = True

        self._configure_result_translucent_scene()
        self._add_petrel_arrow()

        ren = self.renderer
        light = ren.GetLights().GetItemAsObject(0)
        if light:
            light.SetIntensity(1.6)

        self._selection_overlay_state = {
            "world_bounds": None,
            "handle_radius": None,
            "outline_mesh": None,
            "fill_mesh": None,
        }

        self.camera_direction_locked = False

        self._six_view_projection_active = False
        self._six_view_left_button_down = False
        self._six_view_press_position = None
        self._six_view_rotation_interactor = None
        self._six_view_rotation_observer_ids = []

        from .pyvista_static_property_preview import StaticPropertyPreviewRenderer
        self.static_property_preview = StaticPropertyPreviewRenderer(self)
        
        from .pyvista_geometry_preview import GeometryPreviewRenderer
        self.geometry_preview = GeometryPreviewRenderer(self)

        self.property_preview = self.static_property_preview
        self.property_layers = self.static_property_preview
        self.geometry_layers = self.geometry_preview
        
        self._install_result_clipping_observer()
 
    # 统一属性场上下文

    def get_property_display_mode(self):
        """返回当前属性显示模式：full 或 fence。"""
        mode = getattr(self, "_property_display_mode", None)
        if mode not in ("full", "fence"):
            mode = self.cache.get("property_display_mode", "full")
        return mode if mode in ("full", "fence") else "full"

    def _set_property_display_mode(self, mode):
        """设置属性显示模式，并同步到缓存。"""
        normalized = str(mode or "full").strip().lower()
        if normalized not in ("full", "fence"):
            normalized = "full"
        self._property_display_mode = normalized
        if isinstance(getattr(self, "cache", None), dict):
            self.cache["property_display_mode"] = normalized
        return normalized

    def is_fence_property_display_mode(self):
        """当前属性选择按钮是否应保持剖面显示。"""
        return self.get_property_display_mode() == "fence"

    @staticmethod
    def _actor_visible_for_property_context(actor) -> bool:
        if actor is None:
            return False

        try:
            return bool(actor.GetVisibility())
        except Exception:
            pass

        try:
            return bool(actor.visibility)
        except Exception:
            return True


    @staticmethod
    def _dataset_has_cells(dataset) -> bool:
        if dataset is None:
            return False

        try:
            return int(dataset.n_cells) > 0
        except Exception:
            return False


    @staticmethod
    def _normalize_scene_property_name(property_name):
        raw = str(
            property_name
            if property_name is not None
            else ""
        ).strip()

        aliases = {
            "p": "Pressure",
            "pressure": "Pressure",
            "sw": "Sw",
            "water_saturation": "Sw",
            "water saturation": "Sw",
            "phi": "Phi",
            "porosity": "Phi",
            "kx": "Kx",
            "permeability_x": "Kx",
            "permeability x": "Kx",
            "ky": "Ky",
            "permeability_y": "Ky",
            "permeability y": "Ky",
            "kz": "Kz",
            "permeability_z": "Kz",
            "permeability z": "Kz",
        }

        return aliases.get(
            raw.lower(),
            raw,
        )


    def set_active_property_context(
        self,
        *,
        source_mode,
        sim_data,
        property_name,
        scalar_name,
        volume_grid,
        actor=None,
        axis=None,
        layer_index=None,
        title=None,
        unit="",
        metadata=None,
        refresh_picking=True,
    ):
        """
        注册当前显示的属性场。

        source_mode:
            "preview"  静态预览属性；
            "result"   模拟结果属性。

        volume_grid 必须是保留完整 cell 的体网格。可见 actor 可以使用
        extract_surface() 后的外壳，但拾取始终针对 volume_grid。
        """
        if not self._dataset_has_cells(volume_grid):
            return None

        incoming_metadata = dict(metadata or {})
    
        if incoming_metadata.get("operation") != "threshold":
            old_threshold_context = self.cache.get("threshold_source_context")
            if isinstance(old_threshold_context, dict):
                self._remove_actor(self.cache.get("threshold_actor"))
                self._remove_actor(self.cache.get("threshold_grid_actor"))
                old_title = self.cache.get("threshold_scalar_bar_title")
                if old_title:
                    try:
                        self.plotter.remove_scalar_bar(
                            title=old_title,
                            render=False,
                        )
                    except Exception:
                        pass
                self.cache["threshold_actor"] = None
                self.cache["threshold_grid_actor"] = None
                self.cache["threshold_scalar_bar"] = None
                self.cache["threshold_scalar_bar_title"] = None
                self.cache["threshold_source_context"] = None
                self.cache["threshold_source_actor_states"] = []

        context = {
            "source_mode": str(source_mode).strip().lower(),
            "sim_data": sim_data,
            "property_name": str(property_name).strip(),
            "scalar_name": str(scalar_name).strip(),
            "volume_grid": volume_grid,
            "actor": actor,
            "axis": (
                None
                if axis is None
                else str(axis).strip().lower()
            ),
            "layer_index": (
                None
                if layer_index is None
                else int(layer_index)
            ),
            "title": (
                str(title).strip()
                if title is not None
                else str(property_name).strip()
            ),
            "unit": str(unit or ""),
            "metadata": incoming_metadata,
        }

        self._active_property_context = context

        cache = getattr(self, "cache", None)
        if isinstance(cache, dict):
            cache["active_property_context"] = context
            cache["cell_pick_property"] = context["property_name"]
            cache["cell_pick_scalar_name"] = context["scalar_name"]
            cache["cell_pick_source_mode"] = context["source_mode"]

        if (
            refresh_picking
            and isinstance(cache, dict)
            and cache.get("cell_pick_enabled", False)
        ):
            self._refresh_cell_pick_target(
                render_now=False,
            )

        if self.is_fence_property_display_mode():
            self.cache["fence_section_pending_property_refresh"] = True
            self.cache["fence_section_property_context"] = context
            self.cache["fence_section_grid"] = context.get("volume_grid")
            self.cache["fence_section_context_token"] = (
                id(context.get("volume_grid")),
                id(context.get("actor")),
                str(context.get("source_mode", "")),
                str(context.get("property_name", "")),
                str(context.get("scalar_name", "")),
                context.get("axis"),
                context.get("layer_index"),
            )
            self._set_scene_actor_visibility(context.get("actor"), False)
            if self._vertical_fence_section_is_active():
                self._hide_fence_section_context()

        return context


    def clear_active_property_context(
        self,
        *,
        source_mode=None,
        actor=None,
        refresh_picking=True,
        force=False,
    ):
        context = self._active_property_context

        if not isinstance(context, dict):
            return False

        if not force and self.is_fence_property_display_mode():
            self.cache["fence_section_pending_property_refresh"] = True
            self.cache["fence_section_property_context"] = context
            return True

        if (
            source_mode is not None
            and context.get("source_mode")
            != str(source_mode).strip().lower()
        ):
            return False

        if (
            actor is not None
            and context.get("actor") is not actor
        ):
            return False

        self._active_property_context = None

        cache = getattr(self, "cache", None)
        if isinstance(cache, dict):
            cache["active_property_context"] = None
            cache["cell_pick_source_mode"] = None
            cache["cell_pick_scalar_name"] = None

        if (
            refresh_picking
            and isinstance(cache, dict)
            and cache.get("cell_pick_enabled", False)
        ):
            self._remove_actor(
                cache.get("cell_pick_actor")
            )
            self._remove_actor(
                cache.get(
                    "cell_pick_highlight_actor"
                )
            )
            cache["cell_pick_actor"] = None
            cache["cell_pick_grid"] = None
            cache["cell_pick_highlight_actor"] = None
            cache["cell_pick_last_info"] = None

        return True


    def get_active_property_context(self):
        """
        返回当前属性场上下文。

        为兼容旧 UI，即使静态预览文件没有显式注册，也会从
        static_property_preview.current_grid 自动补建上下文。
        """
        context = self._active_property_context

        if (
            isinstance(context, dict)
            and self._dataset_has_cells(
                context.get("volume_grid")
            )
        ):
            actor = context.get("actor")
            if (
                actor is None
                or self._actor_visible_for_property_context(actor)
                or self._vertical_fence_section_is_active()
            ):
                return context

        static_preview = getattr(
            self,
            "static_property_preview",
            None,
        )

        if static_preview is not None:
            grid = getattr(
                static_preview,
                "current_grid",
                None,
            )
            actor = getattr(
                static_preview,
                "actor",
                None,
            )
            property_key = getattr(
                static_preview,
                "current_property_key",
                None,
            )

            if (
                self._dataset_has_cells(grid)
                and actor is not None
                and property_key is not None
                and self._actor_visible_for_property_context(actor)
            ):
                scalar_name = None

                try:
                    scalar_names = list(
                        grid.cell_data.keys()
                    )
                except Exception:
                    scalar_names = []

                preferred = (
                    f"Static_{property_key}"
                )

                if preferred in scalar_names:
                    scalar_name = preferred
                elif scalar_names:
                    scalar_name = scalar_names[0]

                if scalar_name:
                    context = {
                        "source_mode": "preview",
                        "sim_data": getattr(
                            static_preview,
                            "current_sim_data",
                            None,
                        ),
                        "property_name": str(property_key),
                        "scalar_name": str(scalar_name),
                        "volume_grid": grid,
                        "actor": actor,
                        "axis": getattr(
                            static_preview,
                            "current_axis",
                            None,
                        ),
                        "layer_index": getattr(
                            static_preview,
                            "current_layer_index",
                            None,
                        ),
                        "title": getattr(
                            static_preview,
                            "scalar_bar_title",
                            str(property_key),
                        ),
                        "unit": "",
                        "metadata": {},
                    }

                    self._active_property_context = context
                    self.cache["active_property_context"] = context
                    return context

        return None


    @staticmethod
    def _set_scene_actor_visibility(actor, visible):
        """兼容 PyVista Actor 与 VTK Actor 的显隐设置。"""
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


    @staticmethod
    def _get_scene_actor_visibility(actor):
        if actor is None:
            return None

        try:
            return bool(actor.GetVisibility())
        except Exception:
            pass

        try:
            return bool(actor.visibility)
        except Exception:
            return None


    def _active_property_scalar_bar_actors(self, context=None):
        """返回当前属性场相关的颜色条 actor，不区分预览和模拟。"""
        if context is None:
            context = self.get_active_property_context()

        actors = []
        seen = set()

        def add(actor):
            if actor is None or id(actor) in seen:
                return
            seen.add(id(actor))
            actors.append(actor)

        static_preview = getattr(self, "static_property_preview", None)
        if static_preview is not None:
            add(getattr(static_preview, "scalar_bar_actor", None))

        for key in (
            "scalar_bar",
            "pressure_scalar_bar",
            "sw_scalar_bar",
            "phi_scalar_bar",
            "perm_scalar_bar",
            "layer_pressure_scalar_bar",
            "layer_sw_scalar_bar",
            "layer_phi_scalar_bar",
            "layer_perm_scalar_bar",
            "threshold_scalar_bar",
            "time_playback_scalar_bar",
        ):
            add(self.cache.get(key))

        return actors


    def _capture_actor_visibility_states(self, actors):
        states = []
        seen = set()

        for actor in actors or []:
            if actor is None or id(actor) in seen:
                continue
            seen.add(id(actor))
            states.append({
                "actor": actor,
                "visible": self._get_scene_actor_visibility(actor),
            })

        return states


    def _restore_actor_visibility_states(self, states):
        for state in states or []:
            actor = state.get("actor")
            visible = state.get("visible")
            if actor is None or visible is None:
                continue
            self._set_scene_actor_visibility(actor, visible)


    def _resolve_property_operation_context(
        self,
        sim_data=None,
        property_name=None,
    ):
        """
        为拾取、阈值、剖面、等值线等功能解析统一属性上下文。

        优先使用当前画面上的属性场；只有在没有当前属性场时，才兼容
        旧 UI 通过 sim_data + property_name 构建模拟结果网格。
        """
        context = self.get_active_property_context()

        if isinstance(context, dict) and self._dataset_has_cells(
            context.get("volume_grid")
        ):
            return context

        if sim_data is None:
            return None

        name = self._normalize_scene_property_name(
            property_name if property_name is not None else "Pressure"
        )
        config = self._get_pick_property_config(name, quiet=True)

        if config is None or config.get("column") is None:
            return None

        grid = self._build_cell_pick_grid(
            sim_data=sim_data,
            axis=None,
            layer_index=None,
            use_active_context=False,
        )

        if not self._dataset_has_cells(grid):
            return None

        scalar_name = str(config.get("scalar_name", name))
        if scalar_name not in grid.cell_data:
            return None

        return {
            "source_mode": "result",
            "sim_data": sim_data,
            "property_name": name,
            "scalar_name": scalar_name,
            "volume_grid": grid,
            "actor": None,
            "axis": None,
            "layer_index": None,
            "title": config.get("title", name),
            "unit": config.get("unit", ""),
            "metadata": {"compatibility_fallback": True},
        }


    def _context_cell_scalar_values(self, context, grid=None):
        """返回上下文体网格中的 cell 标量和实际标量名。"""
        if not isinstance(context, dict):
            return None, None, None

        if grid is None:
            grid = context.get("volume_grid")

        if not self._dataset_has_cells(grid):
            return None, None, None

        scalar_name = str(context.get("scalar_name", "")).strip()

        if scalar_name:
            try:
                if scalar_name in grid.cell_data:
                    values = np.asarray(
                        grid.cell_data[scalar_name],
                        dtype=np.float64,
                    ).reshape(-1)
                    if values.size == int(grid.n_cells):
                        return grid, scalar_name, values
            except Exception:
                pass

        config = self._get_pick_property_config(
            context.get("property_name"),
            quiet=True,
        ) or {}
        fallback_name = str(config.get("scalar_name", "")).strip()

        if fallback_name:
            try:
                if fallback_name in grid.cell_data:
                    values = np.asarray(
                        grid.cell_data[fallback_name],
                        dtype=np.float64,
                    ).reshape(-1)
                    if values.size == int(grid.n_cells):
                        return grid, fallback_name, values
            except Exception:
                pass

        metadata_names = {
            "PickCellId", "SourceCellId", "OriginalRowIndex",
            "I", "J", "K", "CellInfo0", "CellInfo1",
            "CellInfo2", "CellInfo3", "CenterX", "CenterY",
            "CenterZ", "Volume", "vtkOriginalCellIds",
        }

        try:
            candidate_names = [
                key for key in grid.cell_data.keys()
                if key not in metadata_names
            ]
        except Exception:
            candidate_names = []

        for name in candidate_names:
            try:
                values = np.asarray(
                    grid.cell_data[name],
                    dtype=np.float64,
                ).reshape(-1)
            except Exception:
                continue

            if values.size == int(grid.n_cells):
                return grid, str(name), values

        return grid, None, None


    def _active_property_bounds(self, context=None):
        if context is None:
            context = self.get_active_property_context()

        if not isinstance(context, dict):
            return None

        grid = context.get("volume_grid")
        if not self._dataset_has_cells(grid):
            return None

        try:
            bounds = tuple(float(v) for v in grid.bounds)
        except Exception:
            return None

        if len(bounds) != 6 or not np.isfinite(bounds).all():
            return None

        return bounds


    def _decorate_result_property_grid(
        self,
        *,
        grid,
        sim_data,
        source_indices=None,
    ):
        """给模拟结果体网格补齐与静态预览相同的拾取元数据。"""
        if not self._dataset_has_cells(grid):
            return grid

        cell_data = getattr(
            sim_data,
            "cell_geometry_with_pressure",
            None,
        )

        if (
            cell_data is None
            or getattr(cell_data, "ndim", 0) != 2
            or cell_data.shape[0] == 0
        ):
            return grid

        n_cells = int(grid.n_cells)

        if source_indices is None:
            if n_cells == cell_data.shape[0]:
                source_indices = np.arange(
                    n_cells,
                    dtype=np.int64,
                )
            else:
                source_indices = np.arange(
                    n_cells,
                    dtype=np.int64,
                )

        source_indices = np.asarray(
            source_indices,
            dtype=np.int64,
        ).reshape(-1)

        if source_indices.size != n_cells:
            source_indices = np.arange(
                n_cells,
                dtype=np.int64,
            )

        valid = (
            (source_indices >= 0)
            & (source_indices < cell_data.shape[0])
        )

        if not np.all(valid):
            source_indices = np.arange(
                n_cells,
                dtype=np.int64,
            )
            source_indices = np.clip(
                source_indices,
                0,
                cell_data.shape[0] - 1,
            )

        rows = cell_data[
            source_indices
        ]

        grid.cell_data["PickCellId"] = np.arange(
            n_cells,
            dtype=np.int32,
        )
        grid.cell_data["SourceCellId"] = (
            source_indices
        )
        grid.cell_data["OriginalRowIndex"] = (
            source_indices
        )

        for column, key in (
            (0, "CellInfo0"),
            (1, "CellInfo1"),
            (2, "CellInfo2"),
            (3, "CellInfo3"),
        ):
            if rows.shape[1] > column:
                grid.cell_data[key] = rows[
                    :,
                    column,
                ].astype(np.float64)

        try:
            nx = int(sim_data.grid_info["nx"])
            ny = int(sim_data.grid_info["ny"])
            parent_ids = np.rint(
                rows[:, 1]
            ).astype(np.int64)
            grid.cell_data["I"] = (
                parent_ids % nx
            )
            grid.cell_data["J"] = (
                (parent_ids // nx) % ny
            )
            grid.cell_data["K"] = (
                parent_ids // (nx * ny)
            )
        except Exception:
            pass

        for column, key in (
            (28, "Pressure"),
            (29, "Kx"),
            (30, "Ky"),
            (31, "Kz"),
            (32, "Phi"),
            (33, "Sw"),
        ):
            if rows.shape[1] > column:
                grid.cell_data[key] = rows[
                    :,
                    column,
                ].astype(np.float32)

        try:
            centers = np.asarray(
                grid.cell_centers().points,
                dtype=np.float64,
            )
            grid.cell_data["CenterX"] = (
                centers[:, 0]
            )
            grid.cell_data["CenterY"] = (
                centers[:, 1]
            )
            grid.cell_data["CenterZ"] = (
                centers[:, 2]
            )
        except Exception:
            pass

        if "Volume" not in grid.cell_data:
            try:
                sized = grid.compute_cell_sizes(
                    length=False,
                    area=False,
                    volume=True,
                )
                grid.cell_data["Volume"] = np.asarray(
                    sized.cell_data["Volume"],
                    dtype=np.float64,
                )
            except Exception:
                grid.cell_data["Volume"] = np.zeros(
                    n_cells,
                    dtype=np.float64,
                )

        return grid


    def _register_result_property_context(
        self,
        *,
        sim_data,
        property_name,
        volume_grid,
        actor,
        axis=None,
        layer_index=None,
        title=None,
        unit="",
        source_indices=None,
    ):
        property_name = self._normalize_scene_property_name(
            property_name
        )

        config = self._get_pick_property_config(
            property_name,
            quiet=True,
        ) or {}

        scalar_name = config.get(
            "scalar_name",
            property_name,
        )

        self._decorate_result_property_grid(
            grid=volume_grid,
            sim_data=sim_data,
            source_indices=source_indices,
        )

        
        
        static_preview = getattr(
            self,
            "static_property_preview",
            None,
        )
        if (
            static_preview is not None
            and getattr(
                static_preview,
                "actor",
                None,
            ) is not None
        ):
            try:
                static_preview.clear(
                    render_now=False,
                )
            except Exception:
                pass

        return self.set_active_property_context(
            source_mode="result",
            sim_data=sim_data,
            property_name=property_name,
            scalar_name=scalar_name,
            volume_grid=volume_grid,
            actor=actor,
            axis=axis,
            layer_index=layer_index,
            title=(
                title
                if title is not None
                else config.get("title", property_name)
            ),
            unit=(
                unit
                if unit
                else config.get("unit", "")
            ),
        )



    def _main_result_renderer(self):

        renderer = getattr(
            self.plotter,
            "renderer",
            None,
        )

        if renderer is None:
            renderer = getattr(
                self,
                "renderer",
                None,
            )

        return renderer


    @staticmethod
    def _result_actor_is_visible(actor) -> bool:

        if actor is None:
            return False

        try:
            return bool(actor.GetVisibility())
        except Exception:
            pass

        try:
            return bool(actor.visibility)
        except Exception:
            return False


    @staticmethod
    def _result_actor_bounds(actor):

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

        try:
            values = np.asarray(
                bounds,
                dtype=np.float64,
            ).reshape(6)
        except Exception:
            return None

        if not np.isfinite(values).all():
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


    def _visible_result_scene_bounds(self):
        """返回属性/网格与统一几何渲染器中所有可见对象的合并范围。"""
        cache = getattr(self, "cache", None)
        bounds_values = []
        seen = set()

        if isinstance(cache, dict):
            for cache_key in RESULT_MAIN_SCENE_ACTOR_CACHE_KEYS:
                cached_value = cache.get(cache_key)

                if isinstance(cached_value, (list, tuple, set)):
                    actors = cached_value
                else:
                    actors = (cached_value,)

                for actor in actors:
                    if actor is None:
                        continue

                    actor_id = id(actor)
                    if actor_id in seen:
                        continue
                    seen.add(actor_id)

                    if not self._result_actor_is_visible(actor):
                        continue

                    bounds = self._result_actor_bounds(actor)
                    if bounds is not None:
                        bounds_values.append(bounds)

        geometry_preview = getattr(self, "geometry_preview", None)
        if geometry_preview is not None:
            get_bounds = getattr(
                geometry_preview,
                "get_visible_geometry_bounds",
                None,
            )
            if get_bounds is not None:
                try:
                    geometry_bounds = get_bounds()
                except Exception:
                    geometry_bounds = None

                if geometry_bounds is not None and len(geometry_bounds) == 6:
                    try:
                        values = np.asarray(
                            geometry_bounds,
                            dtype=np.float64,
                        ).reshape(6)
                    except Exception:
                        values = None

                    if values is not None and np.isfinite(values).all():
                        bounds_values.append(tuple(float(v) for v in values))

        if not bounds_values:
            return None

        return (
            float(min(bounds[0] for bounds in bounds_values)),
            float(max(bounds[1] for bounds in bounds_values)),
            float(min(bounds[2] for bounds in bounds_values)),
            float(max(bounds[3] for bounds in bounds_values)),
            float(min(bounds[4] for bounds in bounds_values)),
            float(max(bounds[5] for bounds in bounds_values)),
        )


    def _apply_stable_result_clipping_range(self) -> bool:
        """
        使用几何预览中的稳定裁剪算法。

        正式结果的属性场、网格、井和裂缝全部位于主 renderer，
        因此只需要根据所有可见结果 actor 的合并 bounds 计算一次
        near/far 裁剪范围。
        """
        bounds = self._visible_result_scene_bounds()

        if bounds is None:
            return False

        geometry_preview = getattr(
            self,
            "geometry_layers",
            getattr(
                self,
                "geometry_preview",
                None,
            ),
        )

        if geometry_preview is None:
            return False

        apply_clipping = getattr(
            geometry_preview,
            "_apply_stable_scene_clipping_range",
            None,
        )

        if apply_clipping is None:
            return False

        try:
            return bool(
                apply_clipping(
                    bounds=bounds,
                )
            )
        except Exception:
            return False

    def _on_result_render_start(self, *_args):

        self._update_result_well_label_font_size()
        self._apply_stable_result_clipping_range()


    def _install_result_clipping_observer(self) -> None:

        render_window = getattr(
            self.plotter,
            "ren_win",
            None,
        )

        if (
            render_window is None
            or not hasattr(render_window, "AddObserver")
            or getattr(
                self,
                "_result_clipping_observer_installed",
                False,
            )
        ):
            return

        try:
            observer_id = render_window.AddObserver(
                "StartEvent",
                self._on_result_render_start,
            )

            self._result_clipping_observer_ids.append(
                (
                    render_window,
                    observer_id,
                )
            )
            self._result_clipping_observer_installed = True

        except Exception:
            pass



    def _result_camera_view_scale(self):
        """返回当前相机的视图尺度，用于让井名字号随缩放变化。"""
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
                    np.clip(
                        camera.GetViewAngle(),
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
    def _result_well_label_text_property(actor):
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


    def _iter_result_well_label_actors(self):
        cache = getattr(
            self,
            "cache",
            None,
        )

        if not isinstance(cache, dict):
            return []

        actors = []
        seen = set()

        for cache_key in RESULT_WELL_LABEL_ACTOR_CACHE_KEYS:
            for actor in cache.get(cache_key, []) or []:
                if actor is None:
                    continue

                actor_id = id(actor)

                if actor_id in seen:
                    continue

                seen.add(actor_id)
                actors.append(actor)

        return actors


    def _set_result_well_label_font_size(self, font_size):
        try:
            font_size = int(round(float(font_size)))
        except Exception:
            return False

        font_size = int(
            np.clip(
                font_size,
                RESULT_WELL_LABEL_MIN_FONT_SIZE,
                RESULT_WELL_LABEL_MAX_FONT_SIZE,
            )
        )

        if self._result_well_label_current_font_size == font_size:
            return False

        changed = False

        for actor in self._iter_result_well_label_actors():
            text_property = (
                self._result_well_label_text_property(
                    actor
                )
            )

            if text_property is None:
                continue

            try:
                text_property.SetFontSize(
                    font_size
                )
                changed = True
            except Exception:
                pass

        if changed:
            self._result_well_label_current_font_size = font_size

        return changed


    def _reset_result_well_label_zoom_reference(self):
        self._result_well_label_reference_view_scale = (
            self._result_camera_view_scale()
        )
        self._result_well_label_current_font_size = None
        self._set_result_well_label_font_size(
            RESULT_WELL_LABEL_FONT_SIZE
        )


    def _update_result_well_label_font_size(self):
        if not self._iter_result_well_label_actors():
            return False

        current_scale = self._result_camera_view_scale()

        if current_scale is None:
            return False

        reference_scale = (
            self._result_well_label_reference_view_scale
        )

        if (
            reference_scale is None
            or not np.isfinite(reference_scale)
            or reference_scale <= 1.0e-12
        ):
            self._result_well_label_reference_view_scale = (
                current_scale
            )
            reference_scale = current_scale

        zoom_ratio = max(
            float(reference_scale / current_scale),
            1.0e-6,
        )

        font_size = RESULT_WELL_LABEL_FONT_SIZE * (
            zoom_ratio
            ** RESULT_WELL_LABEL_ZOOM_EXPONENT
        )

        return self._set_result_well_label_font_size(
            font_size
        )


    def _result_scene_reference_length(
        self,
        sim_data,
        fallback_points=None,
    ) -> float:
        geometry_preview = getattr(
            self,
            "geometry_preview",
            None,
        )

        preview_method = getattr(
            geometry_preview,
            "_scene_reference_length",
            None,
        )

        if preview_method is not None:
            try:
                value = float(
                    preview_method(
                        sim_data,
                        fallback_points=fallback_points,
                    )
                )

                if np.isfinite(value) and value > 1.0e-12:
                    return value
            except Exception:
                pass

        bounds = None

        try:
            bounds = self.get_corner_model_bounds(
                sim_data
            )
        except Exception:
            bounds = None

        if bounds is not None and len(bounds) == 6:
            try:
                dx = float(bounds[1] - bounds[0])
                dy = float(bounds[3] - bounds[2])
                dz = float(bounds[5] - bounds[4])
                value = float(
                    np.linalg.norm(
                        [dx, dy, dz]
                    )
                )

                if np.isfinite(value) and value > 1.0e-12:
                    return value
            except Exception:
                pass

        try:
            points = np.asarray(
                fallback_points,
                dtype=np.float64,
            ).reshape(-1, 3)

            spans = np.ptp(
                points,
                axis=0,
            )
            value = float(
                np.linalg.norm(spans)
            )

            if np.isfinite(value) and value > 1.0e-12:
                return value
        except Exception:
            pass

        return 1.0


    def _result_well_name_label_point(
        self,
        sim_data,
        ordered_points,
        well_radius=RESULT_WELL_RADIUS,
    ):
        """按几何预览方法，把井名放在井口沿首段反方向偏移的位置。"""
        try:
            points = np.asarray(
                ordered_points,
                dtype=np.float64,
            ).reshape(-1, 3)
        except Exception:
            return None

        if points.shape[0] < 2:
            return None

        head = points[0]
        first_segment = points[1] - head
        segment_length = float(
            np.linalg.norm(first_segment)
        )

        if (
            not np.isfinite(segment_length)
            or segment_length <= 1.0e-12
        ):
            direction = np.asarray(
                [0.0, 0.0, 1.0],
                dtype=np.float64,
            )
        else:
            direction = (
                -first_segment / segment_length
            )

            if abs(float(direction[2])) < 0.25:
                direction = direction + np.asarray(
                    [0.0, 0.0, 0.35],
                    dtype=np.float64,
                )
                direction_length = float(
                    np.linalg.norm(direction)
                )

                if direction_length > 1.0e-12:
                    direction = (
                        direction / direction_length
                    )

        reference_length = (
            self._result_scene_reference_length(
                sim_data,
                fallback_points=points,
            )
        )

        offset_distance = max(
            reference_length
            * RESULT_WELL_LABEL_OFFSET_SCENE_RATIO,
            float(well_radius)
            * RESULT_WELL_LABEL_OFFSET_RADIUS_MULTIPLIER,
        )

        label_point = (
            head
            + direction * offset_distance
        )

        if not np.isfinite(label_point).all():
            return head.copy()

        return label_point


    @staticmethod
    def _new_result_billboard_text_actor():
        """仅通过 PyVista 内部 VTK 命名空间创建标签，不直接 import vtk。"""
        vtk_namespace = getattr(
            pv,
            "_vtk",
            None,
        )

        actor_class = (
            getattr(
                vtk_namespace,
                "vtkBillboardTextActor3D",
                None,
            )
            if vtk_namespace is not None
            else None
        )

        if actor_class is None:
            return None

        try:
            return actor_class()
        except Exception:
            return None


    def _add_result_well_name_labels(
        self,
        well_head_points,
        well_names,
        cache_key="well_label_actors",
    ):
        if not well_head_points or not well_names:
            return []

        try:
            points = np.asarray(
                well_head_points,
                dtype=np.float64,
            ).reshape(-1, 3)
        except Exception:
            return []

        labels = [
            str(name).strip()
            for name in well_names
        ]

        renderer = self._main_result_renderer()

        if renderer is None:
            return []

        actors = []

        for point, label in zip(points, labels):
            if not label or not np.isfinite(point).all():
                continue

            actor = (
                self._new_result_billboard_text_actor()
            )

            if actor is None:
                continue

            try:
                actor.SetInput(label)
                actor.SetPosition(
                    float(point[0]),
                    float(point[1]),
                    float(point[2]),
                )

                text_property = actor.GetTextProperty()
                text_property.SetFontSize(
                    int(
                        RESULT_WELL_LABEL_FONT_SIZE
                    )
                )
                text_property.SetColor(
                    *RESULT_WELL_LABEL_TEXT_COLOR
                )

                try:
                    text_property.SetBackgroundOpacity(
                        0.0
                    )
                except Exception:
                    pass

                try:
                    text_property.FrameOff()
                except Exception:
                    try:
                        text_property.SetFrame(False)
                    except Exception:
                        pass

                try:
                    text_property.BoldOff()
                except Exception:
                    pass

                try:
                    text_property.ShadowOff()
                except Exception:
                    pass

                try:
                    text_property.SetJustificationToCentered()
                    text_property.SetVerticalJustificationToCentered()
                except Exception:
                    pass

                renderer.AddActor(actor)
                actors.append(actor)

            except Exception:
                try:
                    renderer.RemoveActor(actor)
                except Exception:
                    pass

        
        
        if not actors:
            try:
                fallback_actor = self.plotter.add_point_labels(
                    points=points,
                    labels=labels,
                    font_size=RESULT_WELL_LABEL_FONT_SIZE,
                    text_color=RESULT_WELL_LABEL_TEXT_COLOR,
                    show_points=False,
                    fill_shape=False,
                    shape_opacity=0.0,
                    always_visible=True,
                    render=False,
                )

                if fallback_actor is not None:
                    actors.append(
                        fallback_actor
                    )
            except Exception:
                pass

        if actors:
            self.cache.setdefault(
                cache_key,
                [],
            ).extend(actors)
            self._reset_result_well_label_zoom_reference()

        return actors


    def _configure_result_translucent_scene(self):

        if getattr(
            self,
            "_result_translucent_scene_configured",
            False,
        ):
            return

        try:
            render_window = getattr(
                self.plotter,
                "ren_win",
                None,
            )

            if render_window is not None:
                render_window.SetAlphaBitPlanes(1)
                render_window.SetMultiSamples(0)
        except Exception:
            pass

        renderer = self._main_result_renderer()

        if renderer is not None:
            try:
                renderer.SetUseDepthPeeling(True)
                renderer.SetMaximumNumberOfPeels(
                    RESULT_DEPTH_PEEL_COUNT
                )
                renderer.SetOcclusionRatio(
                    RESULT_DEPTH_PEEL_OCCLUSION_RATIO
                )
            except Exception:
                pass

        try:
            self.plotter.enable_depth_peeling(
                number_of_peels=RESULT_DEPTH_PEEL_COUNT,
                occlusion_ratio=RESULT_DEPTH_PEEL_OCCLUSION_RATIO,
            )
        except TypeError:
            try:
                self.plotter.enable_depth_peeling()
            except Exception:
                pass
        except Exception:
            pass

        if RESULT_ENABLE_ANTI_ALIASING:
            try:
                self.plotter.enable_anti_aliasing("fxaa")
            except TypeError:
                try:
                    self.plotter.enable_anti_aliasing()
                except Exception:
                    pass
            except Exception:
                pass

            try:
                if (
                    renderer is not None
                    and hasattr(renderer, "SetUseFXAA")
                ):
                    renderer.SetUseFXAA(True)
            except Exception:
                pass

        self._result_translucent_scene_configured = True


    @staticmethod
    def _renderer_is_attached(render_window, renderer) -> bool:
        if render_window is None or renderer is None:
            return False

        try:
            renderers = render_window.GetRenderers()

            if renderers is not None and hasattr(
                renderers,
                "IsItemPresent",
            ):
                return bool(
                    renderers.IsItemPresent(renderer)
                )
        except Exception:
            pass

        return False


    def _set_result_geometry_overlay_attached(
        self,
        attached: bool,
    ) -> None:
        """
        正式结果已禁用独立 overlay renderer。

        该方法只负责移除旧版本可能残留的 overlay；即使传入
        attached=True，也不会重新附加覆盖层。
        """
        render_window = getattr(
            self.plotter,
            "ren_win",
            None,
        )
        overlay_renderer = getattr(
            self,
            "_result_geometry_overlay_renderer",
            None,
        )

        if render_window is not None and overlay_renderer is not None:
            try:
                if self._renderer_is_attached(
                    render_window,
                    overlay_renderer,
                ):
                    render_window.RemoveRenderer(
                        overlay_renderer
                    )
            except Exception:
                pass

        self._result_geometry_overlay_attached = False

    def _ensure_result_geometry_overlay_renderer(
        self,
        attach_to_window: bool = True,
    ):
        """
        正式结果不再使用独立 overlay renderer。

        保留该兼容方法只是为了清理旧状态；无论调用参数为何，
        都不会创建或附加新的 renderer。
        """
        self._clear_result_geometry_overlay(
            detach=True,
            remove_renderer=True,
        )
        return None

    @staticmethod
    def _set_result_actor_opacity(actor, opacity) -> None:

        if actor is None:
            return

        try:
            prop = actor.GetProperty()
        except Exception:
            prop = None

        if prop is None:
            return

        try:
            prop.SetOpacity(
                float(opacity)
            )
        except Exception:
            pass


    def _result_property_is_visible(self) -> bool:
        """判断正式结果中是否有可见属性场。"""
        cache = getattr(
            self,
            "cache",
            None,
        )

        if not isinstance(cache, dict):
            return False

        for cache_key in RESULT_PROPERTY_ACTOR_CACHE_KEYS:
            actor = cache.get(cache_key)

            if actor is None:
                continue

            if self._result_actor_is_visible(actor):
                return True

        return False


    @staticmethod
    def _configure_result_grid_surface_actor(
        actor,
        property_visible=False,
    ) -> None:
        """
        按预览模块设置网格面透明度。

        普通网格模式为 0.6；属性场显示时为 0.0。
        """
        if actor is None:
            return

        opacity = (
            RESULT_GRID_PROPERTY_SURFACE_OPACITY
            if (
                RESULT_GRID_PROPERTY_FOCUS_MODE
                and property_visible
            )
            else RESULT_GRID_SURFACE_OPACITY
        )

        try:
            actor.ForceOpaqueOff()
        except Exception:
            try:
                actor.SetForceOpaque(False)
            except Exception:
                pass

        try:
            actor.ForceTranslucentOn()
        except Exception:
            try:
                actor.SetForceTranslucent(True)
            except Exception:
                pass

        try:
            prop = actor.GetProperty()
        except Exception:
            prop = None

        if prop is not None:
            try:
                prop.SetOpacity(float(opacity))
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
                prop.SetAmbient(1.0)
                prop.SetDiffuse(0.0)
                prop.SetSpecular(0.0)
            except Exception:
                pass

            try:
                prop.EdgeVisibilityOff()
            except Exception:
                try:
                    prop.SetEdgeVisibility(False)
                except Exception:
                    pass

        try:
            mapper = actor.GetMapper()
        except Exception:
            mapper = None

        if mapper is not None:
            try:
                mapper.SetResolveCoincidentTopologyToPolygonOffset()
            except Exception:
                pass

            try:
                mapper.SetRelativeCoincidentTopologyPolygonOffsetParameters(
                    RESULT_GRID_SURFACE_OFFSET_FACTOR,
                    RESULT_GRID_SURFACE_OFFSET_UNITS,
                )
            except Exception:
                try:
                    mapper.SetResolveCoincidentTopologyPolygonOffsetParameters(
                        RESULT_GRID_SURFACE_OFFSET_FACTOR,
                        RESULT_GRID_SURFACE_OFFSET_UNITS,
                    )
                except Exception:
                    pass


    @staticmethod
    def _configure_result_grid_edge_actor(
        actor,
        property_visible=False,
    ) -> None:
        """
        按预览模块设置网格线透明度。

        普通网格模式为 1.0；属性场显示时为 0.3。
        """
        if actor is None:
            return

        opacity = (
            RESULT_GRID_PROPERTY_EDGE_OPACITY
            if (
                RESULT_GRID_PROPERTY_FOCUS_MODE
                and property_visible
            )
            else RESULT_GRID_EDGE_OPACITY
        )

        if opacity < 1.0 - 1.0e-12:
            try:
                actor.ForceOpaqueOff()
            except Exception:
                try:
                    actor.SetForceOpaque(False)
                except Exception:
                    pass

            try:
                actor.ForceTranslucentOn()
            except Exception:
                try:
                    actor.SetForceTranslucent(True)
                except Exception:
                    pass
        else:
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
        except Exception:
            prop = None

        if prop is not None:
            try:
                prop.SetOpacity(float(opacity))
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
                prop.SetAmbient(1.0)
                prop.SetDiffuse(0.0)
                prop.SetSpecular(0.0)
            except Exception:
                pass

            if RESULT_GRID_RENDER_LINES_AS_TUBES:
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
            mapper = actor.GetMapper()
        except Exception:
            mapper = None

        if mapper is not None:
            try:
                mapper.SetResolveCoincidentTopologyToPolygonOffset()
            except Exception:
                pass

            try:
                mapper.SetRelativeCoincidentTopologyLineOffsetParameters(
                    RESULT_GRID_LINE_OFFSET_FACTOR,
                    RESULT_GRID_LINE_OFFSET_UNITS,
                )
            except Exception:
                try:
                    mapper.SetResolveCoincidentTopologyLineOffsetParameters(
                        RESULT_GRID_LINE_OFFSET_FACTOR,
                        RESULT_GRID_LINE_OFFSET_UNITS,
                    )
                except Exception:
                    pass


    @staticmethod
    def _result_property_clean_tolerance(bounds) -> float:
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
            * RESULT_PROPERTY_POINT_MERGE_TOLERANCE_RATIO,
            RESULT_PROPERTY_POINT_MERGE_ABSOLUTE_TOLERANCE,
        )


    @staticmethod
    def _result_hexa_face_local_ids():
        """VTK_HEXAHEDRON 的六个四边形面。"""
        return np.asarray(
            [
                [0, 1, 2, 3],
                [4, 5, 6, 7],
                [0, 4, 5, 1],
                [1, 5, 6, 2],
                [2, 6, 7, 3],
                [3, 7, 4, 0],
            ],
            dtype=np.int64,
        )


    @staticmethod
    def _result_hexa_connectivity(grid):
        """
        返回形状为 (n_cells, 8) 的六面体连接关系。

        只有全部单元都是 VTK_HEXAHEDRON 时才使用拓扑外壳算法；
        其他网格类型回退到 PyVista/VTK 的 extract_surface()。
        """
        if grid is None:
            return None

        try:
            n_cells = int(grid.n_cells)
        except Exception:
            return None

        if n_cells <= 0:
            return None

        try:
            cell_types = np.asarray(
                grid.celltypes,
                dtype=np.uint8,
            ).reshape(-1)
        except Exception:
            return None

        if (
            cell_types.size != n_cells
            or not np.all(
                cell_types
                == int(pv.CellType.HEXAHEDRON)
            )
        ):
            return None

        try:
            cells = np.asarray(
                grid.cells,
                dtype=np.int64,
            ).reshape(-1)
        except Exception:
            return None

        if cells.size != n_cells * 9:
            return None

        try:
            records = cells.reshape(n_cells, 9)
        except ValueError:
            return None

        if not np.all(records[:, 0] == 8):
            return None

        connectivity = records[:, 1:9]

        try:
            n_points = int(grid.n_points)
        except Exception:
            return None

        if (
            connectivity.size == 0
            or np.min(connectivity) < 0
            or np.max(connectivity) >= n_points
        ):
            return None

        return connectivity


    def _result_boundary_point_tolerance(self, bounds):
        """计算边界面顶点归并容差。"""
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
            * RESULT_BOUNDARY_POINT_TOLERANCE_RATIO,
            RESULT_BOUNDARY_POINT_TOLERANCE_ABSOLUTE,
        )


    @staticmethod
    def _result_copy_boundary_data(
        source_grid,
        surface,
        owner_cell_ids,
        representative_point_ids,
    ):
        """把原网格的 cell_data/point_data 映射到边界面。"""
        if (
            source_grid is None
            or surface is None
        ):
            return

        owner_cell_ids = np.asarray(
            owner_cell_ids,
            dtype=np.int64,
        )

        representative_point_ids = np.asarray(
            representative_point_ids,
            dtype=np.int64,
        )

        try:
            cell_keys = list(
                source_grid.cell_data.keys()
            )
        except Exception:
            cell_keys = []

        for key in cell_keys:
            try:
                values = np.asarray(
                    source_grid.cell_data[key]
                )

                if values.shape[0] != int(
                    source_grid.n_cells
                ):
                    continue

                surface.cell_data[key] = values[
                    owner_cell_ids
                ]
            except Exception:
                pass

        try:
            point_keys = list(
                source_grid.point_data.keys()
            )
        except Exception:
            point_keys = []

        for key in point_keys:
            try:
                values = np.asarray(
                    source_grid.point_data[key]
                )

                if values.shape[0] != int(
                    source_grid.n_points
                ):
                    continue

                surface.point_data[key] = values[
                    representative_point_ids
                ]
            except Exception:
                pass

        try:
            field_keys = list(
                source_grid.field_data.keys()
            )
        except Exception:
            field_keys = []

        for key in field_keys:
            try:
                surface.field_data[key] = np.asarray(
                    source_grid.field_data[key]
                ).copy()
            except Exception:
                pass


    @staticmethod
    def _result_bilinear_face_samples(face_points):
        """
        在每个四边形内部生成 3×3 双线性采样点和对应法向。

        返回：
            sample_points: (n_faces, n_samples, 3)
            sample_normals: (n_faces, n_samples, 3)
        """
        faces = np.asarray(
            face_points,
            dtype=np.float64,
        )

        p0 = faces[:, 0, :]
        p1 = faces[:, 1, :]
        p2 = faces[:, 2, :]
        p3 = faces[:, 3, :]

        uv_values = np.asarray(
            RESULT_BOUNDARY_SAMPLE_UV,
            dtype=np.float64,
        )

        u = uv_values[:, 0][None, :, None]
        v = uv_values[:, 1][None, :, None]

        p0e = p0[:, None, :]
        p1e = p1[:, None, :]
        p2e = p2[:, None, :]
        p3e = p3[:, None, :]

        sample_points = (
            (1.0 - u) * (1.0 - v) * p0e
            + u * (1.0 - v) * p1e
            + u * v * p2e
            + (1.0 - u) * v * p3e
        )

        du = (
            -(1.0 - v) * p0e
            + (1.0 - v) * p1e
            + v * p2e
            - v * p3e
        )

        dv = (
            -(1.0 - u) * p0e
            - u * p1e
            + u * p2e
            + (1.0 - u) * p3e
        )

        sample_normals = np.cross(
            du,
            dv,
        )

        lengths = np.linalg.norm(
            sample_normals,
            axis=2,
            keepdims=True,
        )

        valid = lengths > 1.0e-20

        sample_normals = np.divide(
            sample_normals,
            lengths,
            out=np.zeros_like(sample_normals),
            where=valid,
        )

        return sample_points, sample_normals


    def _result_remove_nonconforming_internal_faces(
        self,
        grid,
        owner_cell_ids,
        face_points,
    ):
        """
        删除 LGR 粗细网格交界处无法靠“四点完全相同”配对的内部面。

        对每张候选四边形，在其外侧生成 3×3 个采样点；只有所有
        采样点都进入其他 leaf cell 时，才把该面判定为内部面。
        因而模型真正外边界以及 I/J/K 切层形成的新边界会被保留。
        """
        n_faces = int(len(face_points))

        if n_faces == 0:
            return np.zeros(
                0,
                dtype=bool,
            )

        if not RESULT_BOUNDARY_CHECK_NONCONFORMING:
            return np.zeros(
                n_faces,
                dtype=bool,
            )

        find_containing_cell = getattr(
            grid,
            "find_containing_cell",
            None,
        )

        if find_containing_cell is None:
            return np.zeros(
                n_faces,
                dtype=bool,
            )

        owner_cell_ids = np.asarray(
            owner_cell_ids,
            dtype=np.int64,
        )

        face_points = np.asarray(
            face_points,
            dtype=np.float64,
        )

        try:
            connectivity = self._result_hexa_connectivity(
                grid
            )

            if connectivity is None:
                return np.zeros(
                    n_faces,
                    dtype=bool,
                )

            grid_points = np.asarray(
                grid.points,
                dtype=np.float64,
            )

            cell_centers = np.mean(
                grid_points[connectivity],
                axis=1,
            )
        except Exception:
            return np.zeros(
                n_faces,
                dtype=bool,
            )

        internal_mask = np.zeros(
            n_faces,
            dtype=bool,
        )

        sample_count = len(
            RESULT_BOUNDARY_SAMPLE_UV
        )

        batch_size = max(
            int(RESULT_BOUNDARY_FACE_BATCH_SIZE),
            1,
        )

        for batch_start in range(
            0,
            n_faces,
            batch_size,
        ):
            batch_end = min(
                batch_start + batch_size,
                n_faces,
            )

            batch_faces = face_points[
                batch_start:batch_end
            ]

            batch_owners = owner_cell_ids[
                batch_start:batch_end
            ]

            sample_points, sample_normals = (
                self._result_bilinear_face_samples(
                    batch_faces
                )
            )

            owner_centers = cell_centers[
                batch_owners
            ][:, None, :]

            outward_vectors = (
                sample_points
                - owner_centers
            )

            orientation = np.sum(
                sample_normals
                * outward_vectors,
                axis=2,
            )

            flip_mask = orientation < 0.0
            sample_normals[flip_mask] *= -1.0

            edge_lengths = np.stack(
                [
                    np.linalg.norm(
                        batch_faces[:, 1] - batch_faces[:, 0],
                        axis=1,
                    ),
                    np.linalg.norm(
                        batch_faces[:, 2] - batch_faces[:, 1],
                        axis=1,
                    ),
                    np.linalg.norm(
                        batch_faces[:, 3] - batch_faces[:, 2],
                        axis=1,
                    ),
                    np.linalg.norm(
                        batch_faces[:, 0] - batch_faces[:, 3],
                        axis=1,
                    ),
                ],
                axis=1,
            )

            face_scale = np.max(
                edge_lengths,
                axis=1,
            )

            base_offset = np.maximum(
                face_scale
                * RESULT_BOUNDARY_OUTSIDE_OFFSET_RATIO,
                RESULT_BOUNDARY_OUTSIDE_OFFSET_ABSOLUTE,
            )

            sample_is_covered = np.zeros(
                (
                    batch_end - batch_start,
                    sample_count,
                ),
                dtype=bool,
            )

            unresolved = np.ones_like(
                sample_is_covered,
                dtype=bool,
            )

            owner_matrix = np.repeat(
                batch_owners[:, None],
                sample_count,
                axis=1,
            )

            for multiplier in (
                RESULT_BOUNDARY_OUTSIDE_OFFSET_MULTIPLIERS
            ):
                if not np.any(unresolved):
                    break

                query_points = (
                    sample_points
                    + sample_normals
                    * (
                        base_offset[:, None, None]
                        * float(multiplier)
                    )
                )

                unresolved_flat = unresolved.reshape(-1)
                query_flat = query_points.reshape(-1, 3)

                try:
                    located = np.asarray(
                        find_containing_cell(
                            query_flat[unresolved_flat]
                        ),
                        dtype=np.int64,
                    ).reshape(-1)
                except Exception:
                    
                    
                    return np.zeros(
                        n_faces,
                        dtype=bool,
                    )

                located_full = np.full(
                    unresolved_flat.shape,
                    -2,
                    dtype=np.int64,
                )
                located_full[unresolved_flat] = located
                located_full = located_full.reshape(
                    unresolved.shape
                )

                other_cell = (
                    unresolved
                    & (located_full >= 0)
                    & (located_full != owner_matrix)
                )

                outside_union = (
                    unresolved
                    & (located_full < 0)
                )

                sample_is_covered[other_cell] = True

                unresolved[
                    other_cell
                    | outside_union
                ] = False

                
                

            
            
            internal_mask[
                batch_start:batch_end
            ] = np.all(
                sample_is_covered,
                axis=1,
            )

        return internal_mask


    def _build_result_property_shell_surface_fallback(
        self,
        grid,
    ):
        """非纯六面体网格的兼容回退路径。"""
        stable_grid = grid

        if RESULT_PROPERTY_MERGE_SHARED_POINTS:
            tolerance = self._result_property_clean_tolerance(
                grid.bounds
            )

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
                or getattr(
                    stable_grid,
                    "n_cells",
                    0,
                ) == 0
            ):
                stable_grid = grid

        try:
            surface = stable_grid.extract_surface()
        except Exception:
            surface = grid.extract_surface()

        if surface is None:
            return None

        try:
            surface = surface.clean(
                remove_unused_points=True,
            )
        except TypeError:
            try:
                surface = surface.clean()
            except Exception:
                pass
        except Exception:
            pass

        return surface


    def _build_result_property_shell_surface(self, grid):
        """
        基于六面体面归属关系构建真正的 leaf-cell 外表面。
        """
        if grid is None:
            return None

        working_grid = grid

        if not isinstance(
            working_grid,
            pv.UnstructuredGrid,
        ):
            try:
                working_grid = (
                    working_grid.cast_to_unstructured_grid()
                )
            except Exception:
                return self._build_result_property_shell_surface_fallback(
                    grid
                )

        connectivity = self._result_hexa_connectivity(
            working_grid
        )

        if connectivity is None:
            return self._build_result_property_shell_surface_fallback(
                grid
            )

        points = np.asarray(
            working_grid.points,
            dtype=np.float64,
        )

        if (
            points.ndim != 2
            or points.shape[1] != 3
            or not np.isfinite(points).all()
        ):
            return self._build_result_property_shell_surface_fallback(
                grid
            )

        tolerance = self._result_boundary_point_tolerance(
            working_grid.bounds
        )

        try:
            quantized_points = np.rint(
                points / float(tolerance)
            ).astype(
                np.int64,
                copy=False,
            )

            (
                _unique_point_keys,
                representative_point_ids,
                merged_point_ids,
            ) = np.unique(
                quantized_points,
                axis=0,
                return_index=True,
                return_inverse=True,
            )
        except Exception:
            return self._build_result_property_shell_surface_fallback(
                grid
            )

        merged_points = points[
            representative_point_ids
        ]

        merged_connectivity = merged_point_ids[
            connectivity
        ]

        face_local_ids = self._result_hexa_face_local_ids()

        face_vertex_ids = merged_connectivity[
            :,
            face_local_ids,
        ]

        n_cells = int(
            merged_connectivity.shape[0]
        )

        flat_face_vertex_ids = face_vertex_ids.reshape(
            n_cells * 6,
            4,
        )

        face_keys = np.sort(
            flat_face_vertex_ids,
            axis=1,
        )

        try:
            (
                _unique_face_keys,
                face_key_inverse,
                face_key_counts,
            ) = np.unique(
                face_keys,
                axis=0,
                return_inverse=True,
                return_counts=True,
            )
        except Exception:
            return self._build_result_property_shell_surface_fallback(
                grid
            )

        
        candidate_flat_ids = np.flatnonzero(
            face_key_counts[
                face_key_inverse
            ] == 1
        )

        if candidate_flat_ids.size == 0:
            return pv.PolyData()

        owner_cell_ids = (
            candidate_flat_ids // 6
        ).astype(
            np.int64,
            copy=False,
        )

        local_face_ids = (
            candidate_flat_ids % 6
        ).astype(
            np.int64,
            copy=False,
        )

        candidate_face_ids = face_vertex_ids[
            owner_cell_ids,
            local_face_ids,
        ].copy()

        candidate_face_points = merged_points[
            candidate_face_ids
        ]

        
        tri_normal_1 = np.cross(
            candidate_face_points[:, 1]
            - candidate_face_points[:, 0],
            candidate_face_points[:, 2]
            - candidate_face_points[:, 0],
        )

        tri_normal_2 = np.cross(
            candidate_face_points[:, 2]
            - candidate_face_points[:, 0],
            candidate_face_points[:, 3]
            - candidate_face_points[:, 0],
        )

        area_measure = (
            np.linalg.norm(
                tri_normal_1,
                axis=1,
            )
            + np.linalg.norm(
                tri_normal_2,
                axis=1,
            )
        )

        valid_face_mask = (
            np.isfinite(area_measure)
            & (area_measure > tolerance * tolerance)
        )

        candidate_face_ids = candidate_face_ids[
            valid_face_mask
        ]
        candidate_face_points = candidate_face_points[
            valid_face_mask
        ]
        owner_cell_ids = owner_cell_ids[
            valid_face_mask
        ]

        if owner_cell_ids.size == 0:
            return pv.PolyData()

        
        cell_centers = np.mean(
            points[connectivity],
            axis=1,
        )

        face_centers = np.mean(
            candidate_face_points,
            axis=1,
        )

        face_normals = (
            tri_normal_1[valid_face_mask]
            + tri_normal_2[valid_face_mask]
        )

        outward_vectors = (
            face_centers
            - cell_centers[owner_cell_ids]
        )

        reverse_mask = np.sum(
            face_normals * outward_vectors,
            axis=1,
        ) < 0.0

        if np.any(reverse_mask):
            candidate_face_ids[reverse_mask] = (
                candidate_face_ids[
                    reverse_mask
                ][:, [0, 3, 2, 1]]
            )

            candidate_face_points[reverse_mask] = (
                candidate_face_points[
                    reverse_mask
                ][:, [0, 3, 2, 1]]
            )

        nonconforming_internal = (
            self._result_remove_nonconforming_internal_faces(
                grid=working_grid,
                owner_cell_ids=owner_cell_ids,
                face_points=candidate_face_points,
            )
        )

        keep_mask = ~nonconforming_internal

        boundary_face_ids = candidate_face_ids[
            keep_mask
        ]

        boundary_owner_ids = owner_cell_ids[
            keep_mask
        ]

        if boundary_owner_ids.size == 0:
            return pv.PolyData()

        used_merged_point_ids, compact_inverse = np.unique(
            boundary_face_ids.reshape(-1),
            return_inverse=True,
        )

        compact_points = merged_points[
            used_merged_point_ids
        ].astype(
            np.float64,
            copy=False,
        )

        compact_faces = compact_inverse.reshape(
            -1,
            4,
        )

        vtk_faces = np.empty(
            (
                compact_faces.shape[0],
                5,
            ),
            dtype=np.int64,
        )

        vtk_faces[:, 0] = 4
        vtk_faces[:, 1:5] = compact_faces

        surface = pv.PolyData(
            compact_points,
            vtk_faces.reshape(-1),
        )

        output_representative_point_ids = (
            representative_point_ids[
                used_merged_point_ids
            ]
        )

        self._result_copy_boundary_data(
            source_grid=working_grid,
            surface=surface,
            owner_cell_ids=boundary_owner_ids,
            representative_point_ids=(
                output_representative_point_ids
            ),
        )
      
        return surface


    @staticmethod
    def _configure_result_property_actor(actor):

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
            actor.ForceTranslucentOn()
        except Exception:
            try:
                actor.SetForceTranslucent(True)
            except Exception:
                pass

        try:
            prop = actor.GetProperty()
        except Exception:
            prop = None

        if prop is None:
            return

        try:
            prop.SetOpacity(
                RESULT_PROPERTY_OPACITY
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
            prop.SetAmbient(1.0)
            prop.SetDiffuse(0.0)
            prop.SetSpecular(0.0)
        except Exception:
            pass

        try:
            prop.EdgeVisibilityOff()
        except Exception:
            try:
                prop.SetEdgeVisibility(False)
            except Exception:
                pass

        try:
            prop.FrontfaceCullingOff()
        except Exception:
            pass

        try:
            if RESULT_PROPERTY_BACKFACE_CULLING:
                prop.BackfaceCullingOn()
            else:
                prop.BackfaceCullingOff()
        except Exception:
            try:
                prop.SetBackfaceCulling(
                    bool(RESULT_PROPERTY_BACKFACE_CULLING)
                )
            except Exception:
                pass


    @staticmethod
    def _configure_result_geometry_actor(actor):

        if actor is None:
            return

        try:
            prop = actor.GetProperty()

            if prop is not None:
                prop.SetOpacity(
                    RESULT_GEOMETRY_OPACITY
                )

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


    @staticmethod
    def _configure_result_fracture_actor(actor):

        if actor is None:
            return

        PyVistaRenderer._configure_result_geometry_actor(actor)

        try:
            prop = actor.GetProperty()

            if prop is not None:
                try:
                    prop.LightingOff()
                except Exception:
                    try:
                        prop.SetLighting(False)
                    except Exception:
                        pass

                try:
                    prop.SetAmbient(1.0)
                    prop.SetDiffuse(0.0)
                    prop.SetSpecular(0.0)
                except Exception:
                    pass

                try:
                    prop.SetInterpolationToFlat()
                except Exception:
                    pass

                try:
                    prop.EdgeVisibilityOff()
                except Exception:
                    try:
                        prop.SetEdgeVisibility(False)
                    except Exception:
                        pass

                try:
                    prop.SetLineWidth(0.0)
                except Exception:
                    pass

                try:
                    prop.SetRepresentationToSurface()
                except Exception:
                    pass

                try:
                    prop.RenderPointsAsSpheresOff()
                except Exception:
                    pass

                try:
                    prop.VertexVisibilityOff()
                except Exception:
                    try:
                        prop.SetVertexVisibility(False)
                    except Exception:
                        pass

        except Exception:
            pass


    @staticmethod
    def _build_result_fracture_polygon(points):

        try:
            array = np.asarray(
                points,
                dtype=np.float64,
            ).reshape(-1, 3)
        except Exception:
            return None

        finite_mask = np.isfinite(array).all(axis=1)
        array = array[finite_mask]

        if len(array) < 3:
            return None

        cleaned_points = []

        for point in array:
            if not cleaned_points:
                cleaned_points.append(point)
                continue

            if np.linalg.norm(
                point - cleaned_points[-1]
            ) > 1e-8:
                cleaned_points.append(point)

        if (
            len(cleaned_points) >= 2
            and np.linalg.norm(
                cleaned_points[0] - cleaned_points[-1]
            ) <= 1e-8
        ):
            cleaned_points.pop()

        if len(cleaned_points) < 3:
            return None

        cleaned_points = np.asarray(
            cleaned_points,
            dtype=np.float64,
        )

        polygon = pv.PolyData()
        polygon.points = cleaned_points

        try:
            polygon.verts = np.empty(0, dtype=np.int64)
        except Exception:
            pass

        try:
            polygon.lines = np.empty(0, dtype=np.int64)
        except Exception:
            pass

        try:
            polygon.strips = np.empty(0, dtype=np.int64)
        except Exception:
            pass

        polygon.faces = np.asarray(
            [
                len(cleaned_points),
                *range(len(cleaned_points)),
            ],
            dtype=np.int64,
        )

        return polygon


    def _add_result_fracture_actor(
        self,
        points,
        color,
        edge_color=None,
    ):

        polygon = self._build_result_fracture_polygon(
            points
        )

        if polygon is None:
            return None

        if edge_color is None:
            edge_color = color

        try:
            actor = self.plotter.add_mesh(
                polygon,
                style="surface",
                color=color,
                opacity=RESULT_GEOMETRY_OPACITY,
                show_edges=False,
                edge_color=edge_color,
                line_width=0.0,
                lighting=False,
                smooth_shading=False,
                ambient=1.0,
                diffuse=0.0,
                specular=0.0,
                render=False,
            )
        except Exception:
            return None

        self._configure_result_fracture_actor(
            actor
        )
        self._move_actor_to_result_main_renderer_end(
            actor
        )

        return actor


    def _add_result_well_actor(
        self,
        mesh,
        color=(0.08, 0.24, 0.62),
        lighting=True,
        ambient=0.9,
        diffuse=1.0,
    ):

        if mesh is None:
            return None

        try:
            actor = self.plotter.add_mesh(
                mesh,
                color=color,
                opacity=RESULT_GEOMETRY_OPACITY,
                lighting=lighting,
                ambient=ambient,
                diffuse=diffuse,
                render=False,
            )
        except Exception:
            return None

        self._configure_result_geometry_actor(
            actor
        )
        self._move_actor_to_result_main_renderer_end(
            actor
        )

        return actor


    def _move_actor_to_result_main_renderer_end(self, actor) -> None:
        """将结果 actor 放入主 renderer，并移动到当前渲染队列末尾。"""
        if actor is None:
            return

        main_renderer = self._main_result_renderer()

        if main_renderer is None:
            return

        
        overlay_renderer = getattr(
            self,
            "_result_geometry_overlay_renderer",
            None,
        )

        if overlay_renderer is not None:
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

    def _result_geometry_actors(self):

        cache = getattr(
            self,
            "cache",
            None,
        )

        if not isinstance(cache, dict):
            return []

        result = []
        seen = set()

        for cache_key in RESULT_GEOMETRY_ACTOR_CACHE_KEYS:
            actors = cache.get(
                cache_key,
                [],
            ) or []

            if not isinstance(
                actors,
                (list, tuple),
            ):
                actors = [actors]

            for actor in actors:
                if actor is None:
                    continue

                actor_id = id(actor)

                if actor_id in seen:
                    continue

                seen.add(actor_id)
                result.append(
                    (cache_key, actor)
                )

        return result


    def _move_actor_to_result_geometry_overlay(
        self,
        actor,
    ) -> None:
        """兼容旧调用：结果几何统一放入主 renderer。"""
        self._move_actor_to_result_main_renderer_end(
            actor
        )

    def _clear_result_geometry_overlay(
        self,
        detach: bool = True,
        remove_renderer: bool = False,
    ) -> None:

        overlay_renderer = getattr(
            self,
            "_result_geometry_overlay_renderer",
            None,
        )

        if overlay_renderer is not None:
            try:
                overlay_renderer.RemoveAllViewProps()
            except Exception:
                pass

        if detach:
            self._set_result_geometry_overlay_attached(
                False
            )

        if remove_renderer:
            self._result_geometry_overlay_renderer = None
            self._result_geometry_overlay_layer = None
            self._result_geometry_overlay_attached = False
            self._result_geometry_overlay_main_renderer = None


    def _prepare_result_depth_rendering(self):
        """
        在真正渲染前只同步材质和裁剪范围，不再移动或重新挂载 actor。
        """
        self._configure_result_translucent_scene()

        cache = getattr(self, "cache", None)
        if not isinstance(cache, dict):
            return

        property_visible = self._result_property_is_visible()

        for cache_key in RESULT_MAIN_SCENE_ACTOR_CACHE_KEYS:
            actor = cache.get(cache_key)
            if actor is None:
                continue

            if cache_key in RESULT_PROPERTY_ACTOR_CACHE_KEYS:
                self._configure_result_property_actor(actor)
            elif cache_key in RESULT_GRID_SURFACE_ACTOR_CACHE_KEYS:
                self._configure_result_grid_surface_actor(
                    actor,
                    property_visible=property_visible,
                )
            elif cache_key in RESULT_GRID_EDGE_ACTOR_CACHE_KEYS:
                self._configure_result_grid_edge_actor(
                    actor,
                    property_visible=property_visible,
                )

        geometry = getattr(self, "geometry_layers", None)
        if geometry is None:
            geometry = getattr(self, "geometry_preview", None)

        if geometry is not None:
            prepare = getattr(
                geometry,
                "prepare_scene_for_render",
                None,
            )
            if prepare is not None:
                try:
                    prepare()
                except Exception:
                    pass

        self._clear_result_geometry_overlay(
            detach=True,
            remove_renderer=True,
        )

        
        self._apply_stable_result_clipping_range()

    def _add_petrel_arrow(self):

        shaft = pv.Box(
            bounds=(
                0.0, 0.62,
                -0.14, 0.14,
                -0.05, 0.05
            )
        )
        pts = np.array([

            
            [0.62, -0.30, -0.05],
            [0.62,  0.30, -0.05],
            [1.08,  0.00, -0.05],

            
            [0.62, -0.30,  0.05],
            [0.62,  0.30,  0.05],
            [1.08,  0.00,  0.05],

        ])

        faces = np.hstack([
            [3, 0, 1, 2],
            [3, 3, 5, 4],
            [4, 0, 3, 4, 1],
            [4, 1, 4, 5, 2],
            [4, 2, 5, 3, 0],
        ])

        head = pv.PolyData(pts, faces)
        arrow = shaft.merge(head)
        arrow.scale(
            [1.0, 0.72, 0.42],
            inplace=True
        )

        arrow = arrow.compute_normals(
            auto_orient_normals=True
        )

        self.plotter.add_orientation_widget(
            arrow,
            viewport=(
                0.80,
                0.01,
                0.995,
                0.19
            ),
            color="#39d353"
        )

    
    # 动态三面三维坐标系
    
    def _clear_fixed_coordinate_axes(self):

        self._remove_actor_list(
            self.cache.get(
                "fixed_coordinate_axis_actors",
                [],
            )
        )

        self._clear_fixed_coordinate_label_actors()

        self.cache[
            "fixed_coordinate_axis_actors"
        ] = []

        self.cache[
            "fixed_coordinate_label_specs"
        ] = []

        self.cache[
            "fixed_coordinate_bounds"
        ] = None

        self.cache[
            "fixed_coordinate_visible"
        ] = False

        self.cache[
            "fixed_coordinate_hidden_axis"
        ] = None


    def _clear_fixed_coordinate_label_actors(self):
        """
        删除所有坐标系文字 actor。
        """
        label_actors = self.cache.get(
            "fixed_coordinate_label_actors",
            [],
        ) or []

        self._remove_actor_list(
            label_actors
        )

        old_label_actor = self.cache.get(
            "fixed_coordinate_label_actor"
        )

        if (
            old_label_actor is not None
            and old_label_actor not in label_actors
        ):
            self._remove_actor(
                old_label_actor
            )

        self.cache[
            "fixed_coordinate_label_actor"
        ] = None

        self.cache[
            "fixed_coordinate_label_actors"
        ] = []

        self.cache[
            "fixed_coordinate_label_layout_signature"
        ] = None


    @staticmethod
    def _nice_grid_step(value):

        value = float(value)

        if value <= 0.0:
            return 1.0

        exponent = np.floor(
            np.log10(value)
        )

        fraction = value / (
            10.0 ** exponent
        )

        if fraction < 1.5:
            nice_fraction = 1.0

        elif fraction < 3.0:
            nice_fraction = 2.0

        elif fraction < 7.0:
            nice_fraction = 5.0

        else:
            nice_fraction = 10.0

        return float(
            nice_fraction * (
                10.0 ** exponent
            )
        )


    def _get_fixed_grid_step(
        self,
        xmin,
        xmax,
        ymin,
        ymax,
        zmin,
        zmax,
        approx_divisions=COORDINATE_APPROX_DIVISIONS,
    ):
        """
        计算统一网格步长。
        X、Y、Z 三个方向共用相同刻度间隔。
        """
        x_span = abs(
            float(xmax) - float(xmin)
        )

        y_span = abs(
            float(ymax) - float(ymin)
        )

        z_span = abs(
            float(zmax) - float(zmin)
        )

        max_span = max(
            x_span,
            y_span,
            z_span,
        )

        if max_span <= 1e-12:
            return 1.0

        raw_step = max_span / max(
            int(approx_divisions),
            2,
        )

        return self._nice_grid_step(
            raw_step
        )


    @staticmethod
    def _make_fixed_axis_ticks(
        vmin,
        vmax,
        step,
    ):
        vmin = float(vmin)
        vmax = float(vmax)
        step = float(step)

        if vmax < vmin:
            vmin, vmax = vmax, vmin

        if step <= 1e-12:
            return np.array(
                [vmin, vmax],
                dtype=np.float64,
            )

        ticks = [vmin]
        current = vmin + step

        while current < vmax - 1e-8:
            ticks.append(current)
            current += step

        if abs(ticks[-1] - vmax) > 1e-8:
            ticks.append(vmax)

        return np.asarray(
            ticks,
            dtype=np.float64,
        )


    @staticmethod
    def _format_fixed_coordinate_value(value):
        value = float(value)
        if abs(value) < 1e-8:
            return "0"
        if abs(value - round(value)) < 1e-8:
            return f"{round(value):.0f}"
        return (
            f"{value:.3f}"
            .rstrip("0")
            .rstrip(".")
        )


    def _add_fixed_coordinate_line(
        self,
        start_point,
        end_point,
        color=(0.58, 0.58, 0.58),
        line_width=1.0,
        opacity=0.65,
    ):
        start = np.asarray(
            start_point,
            dtype=np.float64,
        )

        end = np.asarray(
            end_point,
            dtype=np.float64,
        )

        if np.linalg.norm(end - start) < 1e-12:
            return None

        line = pv.Line(
            start,
            end,
        )

        actor = self.plotter.add_mesh(
            line,
            color=color,
            line_width=float(line_width),
            opacity=float(opacity),
            lighting=False,
            render=False,
        )

        self.cache[
            "fixed_coordinate_axis_actors"
        ].append(actor)

        return actor


    def _append_fixed_coordinate_label_spec(
        self,
        label_specs,
        axis_point,
        label_point,
        text,
    ):
        label_specs.append(
            {
                "axis_point": tuple(
                    float(value)
                    for value in axis_point
                ),
                "label_point": tuple(
                    float(value)
                    for value in label_point
                ),
                "text": str(text),
            }
        )


    def _add_fixed_coordinate_tick_with_label(
        self,
        label_specs,
        axis_point,
        tick_end_point,
        label_point,
        text,
        color=(0.12, 0.12, 0.12),
        line_width=1.2,
    ):
        self._add_fixed_coordinate_line(
            axis_point,
            tick_end_point,
            color=color,
            line_width=line_width,
            opacity=1.0,
        )
        self._append_fixed_coordinate_label_spec(
            label_specs=label_specs,
            axis_point=axis_point,
            label_point=label_point,
            text=text,
        )


    def _world_to_display_for_coordinate_label(
        self,
        world_point,
    ):
        """
        将三维世界坐标转换为当前屏幕坐标。
        """
        if world_point is None:
            return None

        try:
            x, y, z = [
                float(value)
                for value in world_point
            ]

            renderer = self.plotter.renderer

            renderer.SetWorldPoint(
                x,
                y,
                z,
                1.0,
            )

            renderer.WorldToDisplay()

            display_point = renderer.GetDisplayPoint()

            if display_point is None:
                return None

            return (
                float(display_point[0]),
                float(display_point[1]),
            )

        except Exception:
            return None


    def _get_coordinate_label_justification(
        self,
        axis_point,
        label_point,
    ):
        """
        根据标签锚点相对坐标轴基准点的屏幕投影方向，
        自动决定文字展开方向。
        """
        axis_display = (
            self._world_to_display_for_coordinate_label(
                axis_point
            )
        )

        label_display = (
            self._world_to_display_for_coordinate_label(
                label_point
            )
        )

        if (
            axis_display is None
            or label_display is None
        ):
            return (
                "center",
                "center",
            )

        dx = (
            float(label_display[0])
            - float(axis_display[0])
        )

        dy = (
            float(label_display[1])
            - float(axis_display[1])
        )

        epsilon = float(
            COORDINATE_LABEL_SCREEN_EPSILON_PX
        )

        if dx > epsilon:
            horizontal = "left"

        elif dx < -epsilon:
            horizontal = "right"

        else:
            horizontal = "center"

        if dy > epsilon:
            vertical = "bottom"

        elif dy < -epsilon:
            vertical = "top"

        else:
            vertical = "center"

        return (
            horizontal,
            vertical,
        )


    def _build_fixed_coordinate_label_groups(
        self,
        label_specs,
    ):
        groups = {}
        for index, spec in enumerate(
            label_specs
        ):
            horizontal, vertical = (
                self._get_coordinate_label_justification(
                    axis_point=spec["axis_point"],
                    label_point=spec["label_point"],
                )
            )

            group_key = (
                horizontal,
                vertical,
            )

            if group_key not in groups:
                groups[group_key] = {
                    "points": [],
                    "texts": [],
                    "indices": [],
                }

            groups[group_key][
                "points"
            ].append(
                spec["label_point"]
            )

            groups[group_key][
                "texts"
            ].append(
                spec["text"]
            )

            groups[group_key][
                "indices"
            ].append(index)

        layout_signature = tuple(
            (
                group_key,
                tuple(
                    groups[group_key][
                        "indices"
                    ]
                ),
            )
            for group_key in sorted(
                groups.keys()
            )
        )

        return (
            groups,
            layout_signature,
        )


    def _create_fixed_coordinate_label_actors(
        self,
        groups,
        layout_signature,
    ):
        """
        删除旧文字 actor，并按当前投影方向重新创建。
        """
        self._clear_fixed_coordinate_label_actors()

        label_actors = []

        for (
            horizontal,
            vertical,
        ) in sorted(
            groups.keys()
        ):
            group = groups[
                (
                    horizontal,
                    vertical,
                )
            ]

            points = np.asarray(
                group["points"],
                dtype=np.float64,
            )

            texts = [
                str(text)
                for text in group["texts"]
            ]

            if len(points) == 0:
                continue

            try:
                actor = self.plotter.add_point_labels(
                    points=points,
                    labels=texts,
                    font_size=COORDINATE_LABEL_FONT_SIZE,
                    text_color=(0.0, 0.0, 0.0),
                    show_points=False,
                    fill_shape=False,
                    shape_opacity=0.0,
                    always_visible=True,
                    justification_horizontal=horizontal,
                    justification_vertical=vertical,
                    render=False,
                )

                if actor is not None:
                    label_actors.append(actor)

            except Exception as exc:
                print("=" * 60)
                print("创建坐标系标签失败：")
                print("horizontal =", horizontal)
                print("vertical =", vertical)
                print(type(exc).__name__, exc)
                print("=" * 60)

        self.cache[
            "fixed_coordinate_label_actors"
        ] = label_actors

        self.cache[
            "fixed_coordinate_label_actor"
        ] = (
            label_actors[0]
            if label_actors
            else None
        )

        self.cache[
            "fixed_coordinate_label_layout_signature"
        ] = layout_signature


    def _update_fixed_coordinate_label_alignments(
        self,
        force=False,
    ):
        """
        根据当前相机投影更新标签对齐方式。
        """
        label_specs = self.cache.get(
            "fixed_coordinate_label_specs",
            [],
        ) or []

        if not label_specs:
            return False

        groups, layout_signature = (
            self._build_fixed_coordinate_label_groups(
                label_specs
            )
        )

        old_signature = self.cache.get(
            "fixed_coordinate_label_layout_signature"
        )

        if (
            not force
            and layout_signature == old_signature
        ):
            return False

        self._create_fixed_coordinate_label_actors(
            groups=groups,
            layout_signature=layout_signature,
        )

        return True


    def get_corner_model_bounds(self, sim_data):

        point_groups = []

        def append_valid_points(points):

            if points is None:
                return

            try:
                points_array = np.asarray(
                    points,
                    dtype=np.float64,
                )

            except (
                TypeError,
                ValueError,
            ):
                return

            if points_array.size == 0:
                return

            try:
                points_array = points_array.reshape(
                    -1,
                    3,
                )

            except ValueError:
                return

            finite_mask = np.isfinite(
                points_array
            ).all(
                axis=1
            )

            points_array = points_array[
                finite_mask
            ]

            if len(points_array) == 0:
                return

            point_groups.append(
                points_array
            )

        cell_data = getattr(
            sim_data,
            "cell_geometry_with_pressure",
            None,
        )

        if cell_data is not None:
            try:
                cell_array = np.asarray(
                    cell_data,
                    dtype=np.float64,
                )

                if (
                    cell_array.ndim == 2
                    and cell_array.shape[0] > 0
                    and cell_array.shape[1] >= 28
                ):
                    grid_points = cell_array[
                        :,
                        4:28,
                    ].reshape(
                        -1,
                        3,
                    )

                    append_valid_points(
                        grid_points
                    )

            except (
                TypeError,
                ValueError,
            ):
                pass

        fractures = getattr(
            sim_data,
            "fractures",
            None,
        )

        if isinstance(
            fractures,
            (list, tuple),
        ):
            for fracture in fractures:
                if not isinstance(
                    fracture,
                    dict,
                ):
                    continue

                append_valid_points(
                    fracture.get(
                        "points",
                        None,
                    )
                )

        well_data = getattr(
            sim_data,
            "parsed_well_data",
            None,
        )

        if not isinstance(
            well_data,
            dict,
        ):
            well_data = getattr(
                self,
                "_parsed_well_data",
                None,
            )

        well_tube_radius = 2.0

        well_min_x = None
        well_max_x = None
        well_min_y = None
        well_max_y = None
        well_min_z = None
        well_max_z = None

        if isinstance(
            well_data,
            dict,
        ):
            wells = well_data.get(
                "wells",
                [],
            )

            if isinstance(
                wells,
                list,
            ):
                for well in wells:
                    if not isinstance(
                        well,
                        dict,
                    ):
                        continue

                    track = well.get(
                        "track",
                        [],
                    )

                    if not isinstance(
                        track,
                        list,
                    ):
                        continue

                    valid_track_points = []

                    for point in track:
                        if not isinstance(
                            point,
                            dict,
                        ):
                            continue

                        try:
                            x = float(
                                point["x_m"]
                            )

                            y = float(
                                point["y_m"]
                            )

                            z = float(
                                point["z_m"]
                            )

                        except (
                            KeyError,
                            TypeError,
                            ValueError,
                        ):
                            continue

                        if not np.isfinite(
                            [x, y, z]
                        ).all():
                            continue

                        valid_track_points.append(
                            (
                                x,
                                y,
                                z,
                            )
                        )

                    if not valid_track_points:
                        continue

                    track_array = np.asarray(
                        valid_track_points,
                        dtype=np.float64,
                    )

                    append_valid_points(
                        track_array
                    )

                    current_min_x = float(
                        np.min(
                            track_array[:, 0]
                        )
                    )

                    current_max_x = float(
                        np.max(
                            track_array[:, 0]
                        )
                    )

                    current_min_y = float(
                        np.min(
                            track_array[:, 1]
                        )
                    )

                    current_max_y = float(
                        np.max(
                            track_array[:, 1]
                        )
                    )

                    current_min_z = float(
                        np.min(
                            track_array[:, 2]
                        )
                    )

                    current_max_z = float(
                        np.max(
                            track_array[:, 2]
                        )
                    )

                    if well_min_x is None:
                        well_min_x = current_min_x
                        well_max_x = current_max_x
                        well_min_y = current_min_y
                        well_max_y = current_max_y
                        well_min_z = current_min_z
                        well_max_z = current_max_z

                    else:
                        well_min_x = min(
                            well_min_x,
                            current_min_x,
                        )

                        well_max_x = max(
                            well_max_x,
                            current_max_x,
                        )

                        well_min_y = min(
                            well_min_y,
                            current_min_y,
                        )

                        well_max_y = max(
                            well_max_y,
                            current_max_y,
                        )

                        well_min_z = min(
                            well_min_z,
                            current_min_z,
                        )

                        well_max_z = max(
                            well_max_z,
                            current_max_z,
                        )

        if not point_groups:
            return None

        all_points = np.vstack(
            point_groups
        )

        xmin = float(
            np.min(
                all_points[:, 0]
            )
        )

        xmax = float(
            np.max(
                all_points[:, 0]
            )
        )

        ymin = float(
            np.min(
                all_points[:, 1]
            )
        )

        ymax = float(
            np.max(
                all_points[:, 1]
            )
        )

        zmin = float(
            np.min(
                all_points[:, 2]
            )
        )

        zmax = float(
            np.max(
                all_points[:, 2]
            )
        )

        if well_min_x is not None:
            xmin = min(
                xmin,
                well_min_x
                - well_tube_radius,
            )

            xmax = max(
                xmax,
                well_max_x
                + well_tube_radius,
            )

            ymin = min(
                ymin,
                well_min_y
                - well_tube_radius,
            )

            ymax = max(
                ymax,
                well_max_y
                + well_tube_radius,
            )

            zmin = min(
                zmin,
                well_min_z
                - well_tube_radius,
            )

            zmax = max(
                zmax,
                well_max_z
                + well_tube_radius,
            )

        return (
            xmin,
            xmax,
            ymin,
            ymax,
            zmin,
            zmax,
        )


    def _get_camera_aware_coordinate_signature(
        self,
        bounds,
    ):
        """
        判断相机当前位于模型哪个方向。
        """
        if bounds is None or len(bounds) != 6:
            return None

        xmin, xmax, ymin, ymax, zmin, zmax = [
            float(value)
            for value in bounds
        ]

        center_x = (xmin + xmax) * 0.5
        center_y = (ymin + ymax) * 0.5
        center_z = (zmin + zmax) * 0.5

        try:
            camera_position = np.asarray(
                self.plotter.camera_position[0],
                dtype=np.float64,
            )

        except Exception:
            try:
                camera_position = np.asarray(
                    self.plotter.camera.position,
                    dtype=np.float64,
                )

            except Exception:
                return None

        x_side = (
            "xmin"
            if camera_position[0] >= center_x
            else "xmax"
        )

        y_side = (
            "ymin"
            if camera_position[1] >= center_y
            else "ymax"
        )

        z_side = (
            "zmin"
            if camera_position[2] >= center_z
            else "zmax"
        )

        return (
            x_side,
            y_side,
            z_side,
        )


    def _get_hidden_coordinate_axis_for_standard_view(self):
        """
        判断当前是否为标准六向视图。
        """
        try:
            camera_position, focal_point, _ = (
                self.plotter.camera_position
            )

            camera_position = np.asarray(
                camera_position,
                dtype=np.float64,
            )

            focal_point = np.asarray(
                focal_point,
                dtype=np.float64,
            )

        except Exception:
            return None

        view_vector = (
            camera_position
            - focal_point
        )

        vector_length = float(
            np.linalg.norm(view_vector)
        )

        if vector_length <= 1e-12:
            return None

        view_direction = (
            view_vector / vector_length
        )

        absolute_direction = np.abs(
            view_direction
        )

        dominant_index = int(
            np.argmax(
                absolute_direction
            )
        )

        dominant_value = float(
            absolute_direction[
                dominant_index
            ]
        )

        if (
            dominant_value
            < COORDINATE_STANDARD_VIEW_COS_THRESHOLD
        ):
            return None

        axis_names = (
            "x",
            "y",
            "z",
        )

        return axis_names[
            dominant_index
        ]


    def create_fixed_3d_coordinate_axes(
        self,
        bounds,
        approx_divisions=COORDINATE_APPROX_DIVISIONS,
        signature=None,
    ):
        """
        根据当前相机方向创建动态三面坐标系。
        """
        if bounds is None or len(bounds) != 6:
            print("动态坐标系创建失败：bounds 无效")
            return

        xmin, xmax, ymin, ymax, zmin, zmax = [
            float(value)
            for value in bounds
        ]

        x_span = xmax - xmin
        y_span = ymax - ymin
        z_span = zmax - zmin

        if (
            abs(x_span) < 1e-12
            or abs(y_span) < 1e-12
            or abs(z_span) < 1e-12
        ):
            print("动态坐标系创建失败：模型范围无效")
            return

        if signature is None:
            signature = (
                self._get_camera_aware_coordinate_signature(
                    bounds
                )
            )

        if signature is None:
            signature = (
                "xmin",
                "ymin",
                "zmin",
            )

        x_side, y_side, z_side = signature

        
        
        
        hidden_axis = (
            self._get_hidden_coordinate_axis_for_standard_view()
        )

        show_x_axis = (
            hidden_axis != "x"
        )

        show_y_axis = (
            hidden_axis != "y"
        )

        show_z_axis = (
            hidden_axis != "z"
        )

        
        
        
        is_side_x_view = (
            hidden_axis == "x"
        )

        
        x_plane = (
            xmin
            if x_side == "xmin"
            else xmax
        )

        y_plane = (
            ymin
            if y_side == "ymin"
            else ymax
        )

        z_plane = (
            zmin
            if z_side == "zmin"
            else zmax
        )

        
        x_outer = (
            xmax
            if x_side == "xmin"
            else xmin
        )

        y_outer = (
            ymax
            if y_side == "ymin"
            else ymin
        )

        z_outer = (
            zmax
            if z_side == "zmin"
            else zmin
        )

        
        sign_x_plane = (
            -1.0
            if x_side == "xmin"
            else 1.0
        )

        sign_y_plane = (
            -1.0
            if y_side == "ymin"
            else 1.0
        )

        sign_z_plane = (
            -1.0
            if z_side == "zmin"
            else 1.0
        )

        
        sign_x_outer = (
            1.0
            if x_outer == xmax
            else -1.0
        )

        sign_y_outer = (
            1.0
            if y_outer == ymax
            else -1.0
        )

        sign_z_outer = (
            1.0
            if z_outer == zmax
            else -1.0
        )

        self._clear_fixed_coordinate_axes()

        
        
        
        grid_step = self._get_fixed_grid_step(
            xmin=xmin,
            xmax=xmax,
            ymin=ymin,
            ymax=ymax,
            zmin=zmin,
            zmax=zmax,
            approx_divisions=approx_divisions,
        )

        x_ticks = self._make_fixed_axis_ticks(
            xmin,
            xmax,
            grid_step,
        )

        y_ticks = self._make_fixed_axis_ticks(
            ymin,
            ymax,
            grid_step,
        )

        z_ticks = self._make_fixed_axis_ticks(
            zmin,
            zmax,
            grid_step,
        )

        
        
        
        reference_span = max(
            abs(x_span),
            abs(y_span),
            abs(z_span),
        )

        reference_span = max(
            float(reference_span),
            1e-12,
        )

        tick_x = (
            reference_span
            * COORDINATE_TICK_LENGTH_RATIO
        )

        tick_y = (
            reference_span
            * COORDINATE_TICK_LENGTH_RATIO
        )

        tick_label_offset = (
            reference_span
            * COORDINATE_TICK_LABEL_OFFSET_RATIO
        )

        axis_title_offset = (
            tick_label_offset
            + reference_span
            * COORDINATE_AXIS_TITLE_GAP_RATIO
        )

        label_depth_offset = (
            reference_span
            * COORDINATE_LABEL_DEPTH_OFFSET_RATIO
        )

        
        axis_color = (0.12, 0.12, 0.12)
        axis_line_width = 1.8

        
        edge_color = (0.58, 0.58, 0.58)
        edge_line_width = 1.0

        
        grid_color = (0.62, 0.62, 0.62)
        grid_line_width = 0.7

        label_specs = []

        
        
        
        

        
        if show_x_axis:
            self._add_fixed_coordinate_line(
                (xmin, y_outer, z_plane),
                (xmax, y_outer, z_plane),
                color=axis_color,
                line_width=axis_line_width,
                opacity=1.0,
            )

        
        if show_y_axis:
            self._add_fixed_coordinate_line(
                (x_outer, ymin, z_plane),
                (x_outer, ymax, z_plane),
                color=axis_color,
                line_width=axis_line_width,
                opacity=1.0,
            )

        
        self._add_fixed_coordinate_line(
            (xmin, y_plane, z_plane),
            (xmax, y_plane, z_plane),
            color=edge_color,
            line_width=edge_line_width,
            opacity=0.75,
        )

        self._add_fixed_coordinate_line(
            (x_plane, ymin, z_plane),
            (x_plane, ymax, z_plane),
            color=edge_color,
            line_width=edge_line_width,
            opacity=0.75,
        )

        
        for x in x_ticks:
            self._add_fixed_coordinate_line(
                (x, ymin, z_plane),
                (x, ymax, z_plane),
                color=grid_color,
                line_width=grid_line_width,
                opacity=0.45,
            )

        
        for y in y_ticks:
            self._add_fixed_coordinate_line(
                (xmin, y, z_plane),
                (xmax, y, z_plane),
                color=grid_color,
                line_width=grid_line_width,
                opacity=0.45,
            )

        
        
        
        

        
        if show_z_axis:
            self._add_fixed_coordinate_line(
                (x_plane, y_outer, zmin),
                (x_plane, y_outer, zmax),
                color=axis_color,
                line_width=axis_line_width,
                opacity=1.0,
            )

        
        if show_y_axis:
            self._add_fixed_coordinate_line(
                (x_plane, ymin, z_outer),
                (x_plane, ymax, z_outer),
                color=axis_color,
                line_width=axis_line_width,
                opacity=1.0,
            )

        
        self._add_fixed_coordinate_line(
            (x_plane, y_plane, zmin),
            (x_plane, y_plane, zmax),
            color=edge_color,
            line_width=edge_line_width,
            opacity=0.75,
        )

        self._add_fixed_coordinate_line(
            (x_plane, ymin, z_plane),
            (x_plane, ymax, z_plane),
            color=edge_color,
            line_width=edge_line_width,
            opacity=0.75,
        )

        
        for y in y_ticks:
            self._add_fixed_coordinate_line(
                (x_plane, y, zmin),
                (x_plane, y, zmax),
                color=grid_color,
                line_width=grid_line_width,
                opacity=0.45,
            )

        
        for z in z_ticks:
            self._add_fixed_coordinate_line(
                (x_plane, ymin, z),
                (x_plane, ymax, z),
                color=grid_color,
                line_width=grid_line_width,
                opacity=0.45,
            )

        
        
        
        

        
        if show_z_axis:
            self._add_fixed_coordinate_line(
                (x_outer, y_plane, zmin),
                (x_outer, y_plane, zmax),
                color=axis_color,
                line_width=axis_line_width,
                opacity=1.0,
            )

        
        if show_x_axis:
            self._add_fixed_coordinate_line(
                (xmin, y_plane, z_outer),
                (xmax, y_plane, z_outer),
                color=axis_color,
                line_width=axis_line_width,
                opacity=1.0,
            )

        
        self._add_fixed_coordinate_line(
            (x_plane, y_plane, zmin),
            (x_plane, y_plane, zmax),
            color=edge_color,
            line_width=edge_line_width,
            opacity=0.75,
        )

        self._add_fixed_coordinate_line(
            (xmin, y_plane, z_plane),
            (xmax, y_plane, z_plane),
            color=edge_color,
            line_width=edge_line_width,
            opacity=0.75,
        )

        
        for x in x_ticks:
            self._add_fixed_coordinate_line(
                (x, y_plane, zmin),
                (x, y_plane, zmax),
                color=grid_color,
                line_width=grid_line_width,
                opacity=0.45,
            )

        
        for z in z_ticks:
            self._add_fixed_coordinate_line(
                (xmin, y_plane, z),
                (xmax, y_plane, z),
                color=grid_color,
                line_width=grid_line_width,
                opacity=0.45,
            )

        
        
        
        if show_x_axis:
            for x in x_ticks:
                axis_point = (
                    x,
                    y_plane,
                    z_outer,
                )

                tick_end_point = (
                    x,
                    y_plane
                    + sign_y_plane * tick_y,
                    z_outer,
                )

                label_point = (
                    x,
                    y_plane
                    + sign_y_plane
                    * tick_label_offset,
                    z_outer
                    + sign_z_outer
                    * label_depth_offset,
                )

                self._add_fixed_coordinate_tick_with_label(
                    label_specs=label_specs,
                    axis_point=axis_point,
                    tick_end_point=tick_end_point,
                    label_point=label_point,
                    text=self._format_fixed_coordinate_value(
                        x
                    ),
                )

        
        
        
        if show_y_axis:
            for y in y_ticks:
                axis_point = (
                    x_plane,
                    y,
                    z_outer,
                )

                tick_end_point = (
                    x_plane
                    + sign_x_plane * tick_x,
                    y,
                    z_outer,
                )

                label_point = (
                    x_plane
                    + sign_x_plane
                    * tick_label_offset,
                    y,
                    z_outer
                    + sign_z_outer
                    * label_depth_offset,
                )

                self._add_fixed_coordinate_tick_with_label(
                    label_specs=label_specs,
                    axis_point=axis_point,
                    tick_end_point=tick_end_point,
                    label_point=label_point,
                    text=self._format_fixed_coordinate_value(
                        y
                    ),
                )

        
        
        
        if show_x_axis:
            for x in x_ticks:
                axis_point = (
                    x,
                    y_outer,
                    z_plane,
                )

                tick_end_point = (
                    x,
                    y_outer
                    + sign_y_outer * tick_y,
                    z_plane,
                )

                label_point = (
                    x,
                    y_outer
                    + sign_y_outer
                    * tick_label_offset,
                    z_plane
                    + sign_z_plane
                    * label_depth_offset,
                )

                self._add_fixed_coordinate_tick_with_label(
                    label_specs=label_specs,
                    axis_point=axis_point,
                    tick_end_point=tick_end_point,
                    label_point=label_point,
                    text=self._format_fixed_coordinate_value(
                        x
                    ),
                )

        
        
        
        if show_y_axis:
            for y in y_ticks:
                axis_point = (
                    x_outer,
                    y,
                    z_plane,
                )

                tick_end_point = (
                    x_outer
                    + sign_x_outer * tick_x,
                    y,
                    z_plane,
                )

                label_point = (
                    x_outer
                    + sign_x_outer
                    * tick_label_offset,
                    y,
                    z_plane
                    + sign_z_plane
                    * label_depth_offset,
                )

                self._add_fixed_coordinate_tick_with_label(
                    label_specs=label_specs,
                    axis_point=axis_point,
                    tick_end_point=tick_end_point,
                    label_point=label_point,
                    text=self._format_fixed_coordinate_value(
                        y
                    ),
                )

        
        
        
        if show_z_axis:
            for z in z_ticks:

                
                
                
                
                axis_point = (
                    x_plane,
                    y_outer,
                    z,
                )

                if is_side_x_view:
                    tick_end_point = (
                        x_plane,
                        y_outer
                        + sign_y_outer * tick_y,
                        z,
                    )

                    label_point = (
                        x_plane,
                        y_outer
                        + sign_y_outer
                        * tick_label_offset,
                        z,
                    )

                else:
                    tick_end_point = (
                        x_plane
                        + sign_x_plane * tick_x,
                        y_outer,
                        z,
                    )

                    label_point = (
                        x_plane
                        + sign_x_plane
                        * tick_label_offset,
                        y_outer,
                        z,
                    )

                self._add_fixed_coordinate_tick_with_label(
                    label_specs=label_specs,
                    axis_point=axis_point,
                    tick_end_point=tick_end_point,
                    label_point=label_point,
                    text=self._format_fixed_coordinate_value(
                        z
                    ),
                )

                
                
                
                
                axis_point = (
                    x_outer,
                    y_plane,
                    z,
                )

                if is_side_x_view:
                    tick_end_point = (
                        x_outer,
                        y_plane
                        + sign_y_plane * tick_y,
                        z,
                    )

                    label_point = (
                        x_outer,
                        y_plane
                        + sign_y_plane
                        * tick_label_offset,
                        z,
                    )

                else:
                    tick_end_point = (
                        x_outer
                        + sign_x_outer * tick_x,
                        y_plane,
                        z,
                    )

                    label_point = (
                        x_outer
                        + sign_x_outer
                        * tick_label_offset,
                        y_plane,
                        z,
                    )

                self._add_fixed_coordinate_tick_with_label(
                    label_specs=label_specs,
                    axis_point=axis_point,
                    tick_end_point=tick_end_point,
                    label_point=label_point,
                    text=self._format_fixed_coordinate_value(
                        z
                    ),
                )

        
        
        

        
        if show_x_axis:
            axis_point = (
                (xmin + xmax) * 0.5,
                y_outer,
                z_plane,
            )

            label_point = (
                (xmin + xmax) * 0.5,
                y_outer
                + sign_y_outer
                * axis_title_offset,
                z_plane
                + sign_z_plane
                * label_depth_offset,
            )

            self._append_fixed_coordinate_label_spec(
                label_specs=label_specs,
                axis_point=axis_point,
                label_point=label_point,
                text="X-axis",
            )

        
        if show_y_axis:
            axis_point = (
                x_outer,
                (ymin + ymax) * 0.5,
                z_plane,
            )

            label_point = (
                x_outer
                + sign_x_outer
                * axis_title_offset,
                (ymin + ymax) * 0.5,
                z_plane
                + sign_z_plane
                * label_depth_offset,
            )

            self._append_fixed_coordinate_label_spec(
                label_specs=label_specs,
                axis_point=axis_point,
                label_point=label_point,
                text="Y-axis",
            )

        
        if show_z_axis:
            axis_point = (
                x_plane,
                y_outer,
                (zmin + zmax) * 0.5,
            )

            if is_side_x_view:
                label_point = (
                    x_plane,
                    y_outer
                    + sign_y_outer
                    * axis_title_offset,
                    (zmin + zmax) * 0.5,
                )

            else:
                label_point = (
                    x_plane
                    + sign_x_plane
                    * axis_title_offset,
                    y_outer,
                    (zmin + zmax) * 0.5,
                )

            self._append_fixed_coordinate_label_spec(
                label_specs=label_specs,
                axis_point=axis_point,
                label_point=label_point,
                text="Z-axis",
            )

        self.cache[
            "fixed_coordinate_label_specs"
        ] = label_specs

        self.cache[
            "fixed_coordinate_bounds"
        ] = (
            xmin,
            xmax,
            ymin,
            ymax,
            zmin,
            zmax,
        )

        self.cache[
            "fixed_coordinate_visible"
        ] = True

        self.cache[
            "camera_aware_coordinate_signature"
        ] = signature

        self.cache[
            "fixed_coordinate_hidden_axis"
        ] = hidden_axis

        self._update_fixed_coordinate_label_alignments(
            force=True
        )

    
    
    
    def _get_render_interactor_for_coordinate_axes(self):
        """
        获取 PyVistaQt / PyVista 的交互器。
        """
        candidates = [
            getattr(self.plotter, "iren", None),
            getattr(self.vtk_widget, "iren", None),
            getattr(self.plotter, "interactor", None),
            getattr(self.vtk_widget, "interactor", None),
        ]

        for candidate in candidates:
            if candidate is None:
                continue

            if (
                hasattr(candidate, "add_observer")
                or hasattr(candidate, "AddObserver")
            ):
                return candidate

            inner_interactor = getattr(
                candidate,
                "interactor",
                None,
            )

            if (
                inner_interactor is not None
                and (
                    hasattr(
                        inner_interactor,
                        "add_observer",
                    )
                    or hasattr(
                        inner_interactor,
                        "AddObserver",
                    )
                )
            ):
                return inner_interactor

        return None


    def _remove_camera_aware_coordinate_observers(self):
        """
        取消动态坐标系相机监听器。
        """
        observers = self.cache.get(
            "camera_aware_coordinate_observers",
            [],
        ) or []

        for interactor, observer_id in observers:
            if interactor is None or observer_id is None:
                continue

            try:
                if hasattr(
                    interactor,
                    "remove_observer",
                ):
                    interactor.remove_observer(
                        observer_id
                    )

                elif hasattr(
                    interactor,
                    "RemoveObserver",
                ):
                    interactor.RemoveObserver(
                        observer_id
                    )

            except Exception:
                pass

        self.cache[
            "camera_aware_coordinate_observers"
        ] = []


    def _add_camera_aware_coordinate_observer(
        self,
        event_name,
    ):
        """
        监听旋转、缩放、平移等相机变化。
        """
        interactor = (
            self._get_render_interactor_for_coordinate_axes()
        )

        if interactor is None:
            print("动态坐标系监听失败：未获取到 interactor")
            return None

        def _callback(*args):
            self._update_camera_aware_coordinate_axes()

        try:
            if hasattr(interactor, "add_observer"):
                observer_id = interactor.add_observer(
                    event_name,
                    _callback,
                )

            else:
                observer_id = interactor.AddObserver(
                    event_name,
                    _callback,
                )

            self.cache[
                "camera_aware_coordinate_observers"
            ].append(
                (
                    interactor,
                    observer_id,
                )
            )
            return observer_id
        except Exception as exc:
            print("=" * 60)
            print("动态坐标系监听器注册失败：")
            print(event_name)
            print(type(exc).__name__, exc)
            print("=" * 60)
            return None


    def _update_camera_aware_coordinate_axes(self):
        """
        相机旋转、缩放、平移过程中自动执行。
        """
        if not self.cache.get(
            "camera_aware_coordinate_enabled",
            False,
        ):
            return

        bounds = self.cache.get(
            "fixed_coordinate_bounds"
        )

        if bounds is None:
            return

        new_signature = (
            self._get_camera_aware_coordinate_signature(
                bounds
            )
        )

        if new_signature is None:
            return

        old_signature = self.cache.get(
            "camera_aware_coordinate_signature"
        )

        new_hidden_axis = (
            self._get_hidden_coordinate_axis_for_standard_view()
        )

        old_hidden_axis = self.cache.get(
            "fixed_coordinate_hidden_axis"
        )
        if (
            new_signature != old_signature
            or new_hidden_axis != old_hidden_axis
        ):
            self.create_fixed_3d_coordinate_axes(
                bounds=bounds,
                approx_divisions=COORDINATE_APPROX_DIVISIONS,
                signature=new_signature,
            )

            self._render()
            return
        labels_changed = (
            self._update_fixed_coordinate_label_alignments(
                force=False
            )
        )
        if labels_changed:
            self._render()


    
    
    
    def show_coordinate_axes_for_model(self, sim_data):
        """
        根据当前完整模型显示动态三面坐标系。
        """
        model_bounds = self.get_corner_model_bounds(
            sim_data
        )
        if model_bounds is None:
            print("=" * 60)
            print("显示坐标系失败：当前没有有效网格、裂缝或井坐标数据。")
            print("=" * 60)
            return False
        try:
            self.cache[
                "camera_aware_coordinate_enabled"
            ] = True
            signature = (
                self._get_camera_aware_coordinate_signature(
                    model_bounds
                )
            )
            self.create_fixed_3d_coordinate_axes(
                bounds=model_bounds,
                approx_divisions=COORDINATE_APPROX_DIVISIONS,
                signature=signature,
            )
            self._remove_camera_aware_coordinate_observers()
            self._add_camera_aware_coordinate_observer(
                "InteractionEvent"
            )
            self._render()
            return True
        except Exception as exc:
            print("=" * 60)
            print("显示动态坐标系失败：")
            print(type(exc).__name__, exc)
            print("=" * 60)
            return False


    def hide_coordinate_axes(self):
        """
        隐藏坐标系并停止监听相机。
        """
        self.cache[
            "camera_aware_coordinate_enabled"
        ] = False
        self._remove_camera_aware_coordinate_observers()
        for actor in self.cache.get(
            "fixed_coordinate_axis_actors",
            [],
        ) or []:
            if actor is None:
                continue
            try:
                actor.visibility = False
            except Exception:
                try:
                    actor.SetVisibility(False)
                except Exception:
                    pass
        for actor in self.cache.get(
            "fixed_coordinate_label_actors",
            [],
        ) or []:
            if actor is None:
                continue
            try:
                actor.visibility = False
            except Exception:
                try:
                    actor.SetVisibility(False)
                except Exception:
                    pass
        self.cache[
            "fixed_coordinate_visible"
        ] = False
        self._render()


    def disable_camera_aware_coordinate_axes(
        self,
        clear_axes=True,
    ):
        """
        完全关闭动态三面坐标系。
        """
        self.cache[
            "camera_aware_coordinate_enabled"
        ] = False
        self._remove_camera_aware_coordinate_observers()
        if clear_axes:
            self._clear_fixed_coordinate_axes()
        self._render()


    def _new_cache(self):
        return {
            "pressure_actor": None,
            "fracture_actors": [],
            "scalar_bar": None,
            "grid_lines_actor": None,
            "data_hash": None,
            "corner_actor": None,
            "corner_surface_actor": None,
            "corner_grid_hash": None,
            "corner_grid_camera_initialized": False,
            "well_actors": [],
            "well_label_actors": [],

            "original_grid_opacity": None,
            "original_pressure_opacity": None,
            "corner_lgr_parent_grid_actor": None,
            "corner_lgr_refined_grid_actor": None,
            "selection_outline_actor": None,
            "selection_fill_actor": None,
            "selection_handle_actors": [],
            
            "pressure_field_actor": None,
            "pressure_scalar_bar": None,
            "layer_pressure_actor": None,
            "layer_pressure_scalar_bar": None,
            "layer_coarse_grid_actor": None,
            "layer_frac_actors": [],
            "layer_well_actors": [],
            "layer_well_label_actors": [],
            
            "sw_field_actor": None,
            "sw_scalar_bar": None,
            "layer_sw_actor": None,
            "layer_sw_scalar_bar": None,
            "layer_sw_coarse_grid_actor": None,
            "layer_sw_frac_actors": [],
            "layer_sw_well_actors": [],
            "layer_sw_well_label_actors": [],

            "phi_field_actor": None,
            "phi_scalar_bar": None,
            "layer_phi_actor": None,
            "layer_phi_scalar_bar": None,
            "layer_phi_coarse_grid_actor": None,
            "layer_phi_frac_actors": [],
            "layer_phi_well_actors": [],
            "layer_phi_well_label_actors": [],

            "threshold_actor": None,
            "threshold_scalar_bar": None,
            "threshold_grid_actor": None,
            "threshold_grid_visible": True,
            "threshold_scalar_bar_title": None,
            "threshold_source_context": None,
            "threshold_source_actor_states": [],

            "perm_field_actor": None,
            "perm_scalar_bar": None,
            "layer_perm_actor": None,
            "layer_perm_scalar_bar": None,
            "layer_perm_coarse_grid_actor": None,
            "layer_perm_frac_actors": [],
            "layer_perm_well_actors": [],
            "layer_perm_well_label_actors": [],

            
            "cell_pick_grid": None,
            "cell_pick_actor": None,
            "cell_pick_highlight_actor": None,
            "cell_pick_observer_id": None,
            "cell_pick_enabled": False,
            "cell_pick_property": "Pressure",
            "cell_pick_last_info": None,
            "cell_pick_source_mode": None,
            "cell_pick_scalar_name": None,
            "active_property_context": None,

            
            "measure_enabled": False,
            "measure_start_point": None,
            "measure_end_point": None,
            "measure_line_mesh": None,
            "measure_line_actor": None,
            "measure_observer_ids": [],
            "measure_is_previewing": False,
            "measure_last_info": None,

            
            "time_playback_actor": None,
            "time_playback_scalar_bar": None,
            "time_playback_surface": None,
            "time_playback_source_cell_ids": None,
            "time_playback_steps": None,
            "time_playback_values": None,
            "time_playback_property": None,
            "time_playback_scalar_name": None,
            "time_playback_scalar_bar_title": None,
            "time_playback_mode": None,
            "time_playback_axis": None,
            "time_playback_layer_index": None,
            "time_playback_current_index": -1,
            "time_playback_clim": None,
            "time_playback_selected_cell_ids": None,

            
            "fixed_coordinate_axis_actors": [],
            "fixed_coordinate_label_actor": None,
            "fixed_coordinate_label_actors": [],
            "fixed_coordinate_label_specs": [],
            "fixed_coordinate_label_layout_signature": None,
            "fixed_coordinate_bounds": None,
            "fixed_coordinate_visible": False,
            "fixed_coordinate_hidden_axis": None,
            "camera_aware_coordinate_enabled": False,
            "camera_aware_coordinate_signature": None,
            "camera_aware_coordinate_observers": [],

            
            "magnify_2d_active": False,
            "magnify_2d_dragging": False,
            "magnify_2d_world_bounds": None,
            "magnify_2d_start_xy": None,

            
            "property_display_mode": "full",
            "fence_section_drawing": False,
            "fence_section_finished": False,
            "fence_section_sim_data": None,
            "fence_section_property": "Pressure",
            "fence_section_scalar_name": None,
            "fence_section_bounds": None,
            "fence_section_grid": None,
            "fence_section_points": [],
            "fence_section_observer_ids": [],
            "fence_section_path_mesh": None,
            "fence_section_path_actor": None,
            "fence_section_preview_mesh": None,
            "fence_section_preview_actor": None,
            "fence_section_point_actors": [],
            "fence_section_actor": None,
            "fence_section_data": None,
            "fence_section_scalar_bar": None,
            "fence_section_scalar_bar_title": None,
            "fence_section_last_info": None,
            "fence_section_last_click_time": None,
            "fence_section_last_click_display": None,
            "fence_section_previous_camera_locked": None,
            "fence_section_previous_camera_state": None,
            "fence_section_context_actor_states": [],
            "fence_section_context_captured": False,
            "fence_section_context_hidden_once": False,
            "fence_section_property_context": None,
            "fence_section_property_config": None,
            "fence_section_refreshing_property": False,
            "fence_section_persistent_active": False,
            "fence_section_pending_property_refresh": False,
            "fence_section_context_token": None,
            "fence_section_applied_context_token": None,
            "fence_section_render_guard": False,
        }

    def _render(self):
        """在最终绘制前同步材质，再让持久剖面状态最后生效。"""
        self._prepare_result_depth_rendering()

        if not self.cache.get("fence_section_render_guard", False):
            self._ensure_vertical_fence_section_before_render()

        self.plotter.render()

    def render_now(self):
        self._render()

    def capture_camera_state(self):
        cam = self.plotter.camera
        position, focal_point, view_up = self.plotter.camera_position
        return {
            "position": tuple(float(v) for v in position),
            "focal_point": tuple(float(v) for v in focal_point),
            "view_up": tuple(float(v) for v in view_up),
            "parallel_projection": bool(getattr(cam, "parallel_projection", False)),
            "parallel_scale": float(getattr(cam, "parallel_scale", 1.0)),
            "view_angle": float(getattr(cam, "view_angle", 30.0)),
            "clipping_range": tuple(float(v) for v in getattr(cam, "clipping_range", (0.01, 1000.0))),
        }

    def restore_camera_state(self, state) -> None:
        if not state:
            return
        try:
            self.plotter.camera_position = (
                state.get("position"),
                state.get("focal_point"),
                state.get("view_up"),
            )
            cam = self.plotter.camera
            cam.parallel_projection = bool(state.get("parallel_projection"))
            if "parallel_scale" in state and state["parallel_scale"] is not None:
                cam.parallel_scale = float(state["parallel_scale"])
            if "view_angle" in state and state["view_angle"] is not None:
                cam.view_angle = float(state["view_angle"])
            if "clipping_range" in state and state["clipping_range"] is not None:
                cam.clipping_range = tuple(state["clipping_range"])
            self._render()
        except Exception:
            pass

    def _capture_property_switch_camera(self):
        """保存属性切换前的完整摄像头状态，不触发渲染。"""
        try:
            self._property_switch_camera_state = self.capture_camera_state()
        except Exception:
            self._property_switch_camera_state = None

        self._preserve_camera_on_property_switch = True
        return self._property_switch_camera_state

    def _restore_property_switch_camera(self, consume=False):
        """恢复属性切换前视角；只写相机参数，不主动 render。"""
        state = getattr(
            self,
            "_property_switch_camera_state",
            None,
        )

        if not state:
            return False

        try:
            camera_position = (
                state.get("position"),
                state.get("focal_point"),
                state.get("view_up"),
            )

            if all(value is not None for value in camera_position):
                self.plotter.camera_position = camera_position

            cam = self.plotter.camera

            try:
                cam.parallel_projection = bool(
                    state.get("parallel_projection", False)
                )
            except Exception:
                pass

            try:
                parallel_scale = state.get("parallel_scale")
                if parallel_scale is not None:
                    cam.parallel_scale = float(parallel_scale)
            except Exception:
                pass

            try:
                view_angle = state.get("view_angle")
                if view_angle is not None:
                    cam.view_angle = float(view_angle)
            except Exception:
                pass

            try:
                clipping_range = state.get("clipping_range")
                if clipping_range is not None:
                    cam.clipping_range = tuple(
                        float(value)
                        for value in clipping_range
                    )
            except Exception:
                pass

            return True

        except Exception:
            return False

        finally:
            if consume:
                self._property_switch_camera_state = None

    def _finish_property_switch_render(self):
        """属性/网格替换完成后恢复视角，并只渲染一次。"""
        if self.is_fence_property_display_mode():
            self.cache["fence_section_pending_property_refresh"] = True
            self._set_fence_section_well_labels_hidden(True)
            if self._vertical_fence_section_is_active():
                self._hide_fence_section_context()

        self._restore_property_switch_camera(consume=True)
        self._preserve_camera_on_property_switch = False
        self._render()

    def configure_selection_camera(self, world_bounds) -> None:
        if not world_bounds or len(world_bounds) != 6:
            return
        xmin, xmax, ymin, ymax, zmin, zmax = (float(v) for v in world_bounds)
        cx = (xmin + xmax) * 0.5
        cy = (ymin + ymax) * 0.5
        cz = (zmin + zmax) * 0.5
        span = max(xmax - xmin, ymax - ymin, 1.0)

        cam = self.plotter.camera
        cam.parallel_projection = True
        cam.parallel_scale = span * 0.55
        self.plotter.camera_position = (
            (cx, cy, zmax + span * 2.0),
            (cx, cy, cz),
            (0.0, 1.0, 0.0),
        )
        self._render()

    def _selection_plane_z(self, world_bounds) -> float:
        if not world_bounds or len(world_bounds) != 6:
            return 0.0
        return float(world_bounds[5])

    def _display_world_ray(self, display_x: float, display_y: float):
        renderer = self.plotter.renderer
        renderer.SetDisplayPoint(float(display_x), float(display_y), 0.0)
        renderer.DisplayToWorld()
        w0 = renderer.GetWorldPoint()
        renderer.SetDisplayPoint(float(display_x), float(display_y), 1.0)
        renderer.DisplayToWorld()
        w1 = renderer.GetWorldPoint()
        if not w0 or not w1:
            return None

        x0, y0, z0, w0w = w0
        x1, y1, z1, w1w = w1
        if w0w != 0.0:
            x0, y0, z0 = x0 / w0w, y0 / w0w, z0 / w0w
        if w1w != 0.0:
            x1, y1, z1 = x1 / w1w, y1 / w1w, z1 / w1w
        return (float(x0), float(y0), float(z0)), (float(x1), float(y1), float(z1))

    def display_to_world_xy(self, display_x, display_y, world_bounds):
        z_plane = self._selection_plane_z(world_bounds)
        try:
            ray = self._display_world_ray(display_x, display_y)
            if ray is None:
                return None
            (x0, y0, z0), (x1, y1, z1) = ray
            denom = z1 - z0
            if abs(denom) < 1e-12:
                return (float(x0), float(y0), float(z_plane))
            t = (z_plane - z0) / denom
            x = x0 + (x1 - x0) * t
            y = y0 + (y1 - y0) * t
            return (float(x), float(y), float(z_plane))
        except Exception:
            return None

    def _handle_radius(self, world_bounds) -> float:
        if not world_bounds or len(world_bounds) != 6:
            return 1.0
        xmin, xmax, ymin, ymax, zmin, zmax = (float(v) for v in world_bounds)
        span = max(xmax - xmin, ymax - ymin, zmax - zmin, 1.0)
        return span * 0.005

    def _ensure_selection_overlay(self, world_bounds) -> None:
        if not world_bounds or len(world_bounds) != 6:
            return

        bounds_key = tuple(float(v) for v in world_bounds)
        handle_radius = self._handle_radius(bounds_key)
        prev_bounds = self._selection_overlay_state.get("world_bounds")
        prev_radius = self._selection_overlay_state.get("handle_radius")
        need_rebuild = prev_bounds != bounds_key or prev_radius != handle_radius

        if need_rebuild:
            self.clear_selection_overlay()
            self._selection_overlay_state["world_bounds"] = bounds_key
            self._selection_overlay_state["handle_radius"] = handle_radius

        if self.cache.get("selection_outline_actor") is None:
            z_plane = self._selection_plane_z(bounds_key)
            min_x, max_x, min_y, max_y, _, _ = bounds_key
            corners = [
                (min_x, min_y, z_plane),
                (max_x, min_y, z_plane),
                (max_x, max_y, z_plane),
                (min_x, max_y, z_plane),
            ]
            segments = [
                (corners[0], corners[1]),
                (corners[1], corners[2]),
                (corners[2], corners[3]),
                (corners[3], corners[0]),
            ]
            outline_mesh = self._polydata_from_line_segments(segments)
            if outline_mesh is not None:
                self._selection_overlay_state["outline_mesh"] = outline_mesh
                self.cache["selection_outline_actor"] = self.plotter.add_mesh(
                    outline_mesh,
                    color=(1.0, 1.0, 1.0),
                    line_width=2.0,
                    opacity=1.0,
                    render=False,
                )

        if self.cache.get("selection_fill_actor") is None:
            z_plane = self._selection_plane_z(bounds_key)
            min_x, max_x, min_y, max_y, _, _ = bounds_key
            fill_mesh = pv.PolyData(
                np.array(
                    [
                        (min_x, min_y, z_plane),
                        (max_x, min_y, z_plane),
                        (max_x, max_y, z_plane),
                        (min_x, max_y, z_plane),
                    ],
                    dtype=float,
                )
            )
            fill_mesh.faces = np.array([4, 0, 1, 2, 3], dtype=np.int32)
            self._selection_overlay_state["fill_mesh"] = fill_mesh
            self.cache["selection_fill_actor"] = self.plotter.add_mesh(
                fill_mesh,
                color=(1.0, 1.0, 1.0),
                opacity=0.08,
                show_edges=False,
                render=False,
            )

        if not self.cache.get("selection_handle_actors"):
            sphere_mesh = pv.Sphere(
                radius=handle_radius,
                center=(0.0, 0.0, 0.0),
                theta_resolution=12,
                phi_resolution=12,
            )
            self.cache["selection_handle_actors"] = []
            for _ in range(4):
                actor = self.plotter.add_mesh(
                    sphere_mesh,
                    color=(1.0, 1.0, 1.0),
                    opacity=0.9,
                    render=False,
                )
                self.cache["selection_handle_actors"].append(actor)

    def _apply_selection_overlay_style(self, finalized: bool) -> None:
        outline_color = (0.2, 1.0, 0.2) if not finalized else (1.0, 0.8, 0.2)
        fill_color = outline_color
        fill_opacity = 0.08 if not finalized else 0.12

        outline_actor = self.cache.get("selection_outline_actor")
        if outline_actor is not None:
            outline_actor.prop.color = outline_color
            outline_actor.prop.opacity = 1.0

        fill_actor = self.cache.get("selection_fill_actor")
        if fill_actor is not None:
            fill_actor.prop.color = fill_color
            fill_actor.prop.opacity = fill_opacity

        for actor in self.cache.get("selection_handle_actors", []) or []:
            actor.prop.color = outline_color
            actor.prop.opacity = 0.9

    def _update_selection_overlay_geometry(self, xmin, xmax, ymin, ymax, z_plane: float) -> None:
        corners = [
            (xmin, ymin, z_plane),
            (xmax, ymin, z_plane),
            (xmax, ymax, z_plane),
            (xmin, ymax, z_plane),
        ]

        outline_mesh = self._selection_overlay_state.get("outline_mesh")
        if outline_mesh is not None:
            segments = [
                (corners[0], corners[1]),
                (corners[1], corners[2]),
                (corners[2], corners[3]),
                (corners[3], corners[0]),
            ]
            points = []
            lines = []
            point_index = 0
            for start, end in segments:
                points.extend([start, end])
                lines.extend([2, point_index, point_index + 1])
                point_index += 2
            outline_mesh.points = np.array(points, dtype=float)
            outline_mesh.lines = np.array(lines, dtype=np.int64)

        fill_mesh = self._selection_overlay_state.get("fill_mesh")
        if fill_mesh is not None:
            fill_mesh.points = np.array(corners, dtype=float)

        handle_actors = self.cache.get("selection_handle_actors") or []
        for actor, pt in zip(handle_actors, corners):
            actor.position = (float(pt[0]), float(pt[1]), float(pt[2]))

    def show_selection_preview(self, start_xy, end_xy, world_bounds, finalized: bool = False) -> None:
        if not start_xy or not end_xy:
            return
        if not world_bounds or len(world_bounds) != 6:
            return

        min_x, max_x, min_y, max_y, _, _ = (float(v) for v in world_bounds)
        z_plane = self._selection_plane_z(world_bounds)

        x0, y0 = float(start_xy[0]), float(start_xy[1])
        x1, y1 = float(end_xy[0]), float(end_xy[1])
        xmin = max(min_x, min(max_x, min(x0, x1)))
        xmax = max(min_x, min(max_x, max(x0, x1)))
        ymin = max(min_y, min(max_y, min(y0, y1)))
        ymax = max(min_y, min(max_y, max(y0, y1)))
        self._ensure_selection_overlay(world_bounds)
        self._update_selection_overlay_geometry(xmin, xmax, ymin, ymax, float(z_plane))
        self._apply_selection_overlay_style(finalized)
        self._render()

    def clear_selection_overlay(self) -> None:
        self._remove_actor(self.cache.get("selection_outline_actor"))
        self._remove_actor(self.cache.get("selection_fill_actor"))
        self._remove_actor_list(self.cache.get("selection_handle_actors", []))
        self.cache["selection_outline_actor"] = None
        self.cache["selection_fill_actor"] = None
        self.cache["selection_handle_actors"] = []
        self._selection_overlay_state["outline_mesh"] = None
        self._selection_overlay_state["fill_mesh"] = None
        self._selection_overlay_state["world_bounds"] = None
        self._selection_overlay_state["handle_radius"] = None
        self._render()

    def _remove_cached_property_scalar_bar(self, cache_key):
        scalar_bar = self.cache.get(cache_key)

        if scalar_bar is None:
            return

        try:
            self.plotter.remove_scalar_bar(
                title=getattr(scalar_bar, "title", None),
                render=False,
            )
        except Exception:
            try:
                self.plotter.remove_scalar_bar(render=False)
            except Exception:
                pass

        self.cache[cache_key] = None


    def clear_result_property_view(self, render_now=False):
        """
        属性切换专用轻量清理：清属性、网格和颜色条，保留井、裂缝、
        坐标轴、摄像头及交互工具。预览和模拟共用该入口。
        """
        self._capture_property_switch_camera()

        if self.is_fence_property_display_mode():
            self.cache["fence_section_pending_property_refresh"] = True
        else:
            self.clear_active_property_context(refresh_picking=True)

        static_property_preview = getattr(
            self,
            "static_property_preview",
            None,
        )
        if static_property_preview is not None:
            try:
                static_property_preview.clear(render_now=False)
            except Exception:
                pass

        geometry = getattr(self, "geometry_layers", None)
        if geometry is None:
            geometry = getattr(self, "geometry_preview", None)
        if geometry is not None:
            clear_grid = getattr(geometry, "clear_grid", None)
            if clear_grid is not None:
                try:
                    clear_grid(render_now=False)
                except Exception:
                    pass

        for key in tuple(dict.fromkeys(RESULT_PROPERTY_ACTOR_CACHE_KEYS)):
            self._remove_actor(self.cache.get(key))
            self.cache[key] = None

        for key in tuple(dict.fromkeys(
            RESULT_GRID_SURFACE_ACTOR_CACHE_KEYS
            + RESULT_GRID_EDGE_ACTOR_CACHE_KEYS
        )):
            self._remove_actor(self.cache.get(key))
            self.cache[key] = None

        threshold_title = self.cache.get("threshold_scalar_bar_title")
        if threshold_title:
            try:
                self.plotter.remove_scalar_bar(
                    title=threshold_title,
                    render=False,
                )
            except Exception:
                pass

        for key in (
            "scalar_bar", "pressure_scalar_bar", "layer_pressure_scalar_bar",
            "sw_scalar_bar", "layer_sw_scalar_bar", "phi_scalar_bar",
            "layer_phi_scalar_bar", "threshold_scalar_bar", "perm_scalar_bar",
            "layer_perm_scalar_bar", "time_playback_scalar_bar",
        ):
            self._remove_cached_property_scalar_bar(key)

        self.cache["threshold_scalar_bar_title"] = None
        self.cache["threshold_source_context"] = None
        self.cache["threshold_source_actor_states"] = []
        self.cache["threshold_actor"] = None
        self.cache["threshold_grid_actor"] = None

        self.cache["corner_grid_hash"] = None
        self.cache["data_hash"] = None

        
        
        
        if render_now:
            self._restore_property_switch_camera(consume=False)

        return True

    def clear_scene(self, render_now=False):
        """兼容属性按钮原调用：只清属性场、网格和颜色条。"""
        return self.clear_result_property_view(render_now=render_now)

    def clear_all_scene(self, render_now=True):
        """真正清空整个工作台，仅用于换工程或用户主动清空。"""
        self.disable_cell_info_picking(
            clear_highlight=True,
            render_now=False,
        )
        self.clear_active_property_context(
            refresh_picking=False,
            force=True,
        )
        self._remove_actor(self.cache.get("pressure_actor"))
        self._remove_actor(self.cache.get("pressure_field_actor"))
        self._remove_actor(self.cache.get("corner_actor"))
        self._remove_actor(self.cache.get("corner_surface_actor"))
        self._remove_actor(self.cache.get("grid_lines_actor"))
        self._remove_actor(self.cache.get("corner_lgr_parent_grid_actor"))
        self._remove_actor(self.cache.get("corner_lgr_refined_grid_actor"))
        self._remove_actor(self.cache.get("selection_outline_actor"))
        self._remove_actor(self.cache.get("selection_fill_actor"))
        self._remove_actor_list(self.cache.get("fracture_actors", []))
        self._remove_actor_list(self.cache.get("well_actors", []))
        self._remove_actor(self.cache.get("layer_pressure_actor"))
        self._remove_actor(self.cache.get("layer_coarse_grid_actor"))
        self._remove_actor_list(self.cache.get("layer_frac_actors", []))
        self._remove_actor_list(self.cache.get("layer_well_actors", []))
        self._remove_actor_list(self.cache.get("selection_handle_actors", []))
        self._remove_actor(self.cache.get("sw_field_actor"))
        self._remove_actor(self.cache.get("layer_sw_actor"))
        self._remove_actor(self.cache.get("layer_sw_coarse_grid_actor"))
        self._remove_actor_list(self.cache.get("layer_sw_frac_actors", []))
        self._remove_actor_list(self.cache.get("layer_sw_well_actors", []))
        self._remove_actor(self.cache.get("threshold_actor"))
        self._remove_actor(self.cache.get("threshold_grid_actor"))
        self._remove_actor(self.cache.get("phi_field_actor"))
        self._remove_actor(self.cache.get("layer_phi_actor"))
        self._remove_actor(self.cache.get("layer_phi_coarse_grid_actor"))
        self._remove_actor_list(self.cache.get("layer_phi_frac_actors", []))
        self._remove_actor_list(self.cache.get("layer_phi_well_actors", []))
        self._remove_actor(self.cache.get("perm_field_actor"))
        self._remove_actor(self.cache.get("layer_perm_actor"))
        self._remove_actor(self.cache.get("layer_perm_coarse_grid_actor"))
        self._remove_actor_list(self.cache.get("layer_perm_frac_actors", []))
        self._remove_actor_list(self.cache.get("layer_perm_well_actors", []))
        self._remove_actor(self.cache.get("cell_pick_actor"))
        self._remove_actor(self.cache.get("cell_pick_highlight_actor"))
        self._remove_actor(self.cache.get("measure_line_actor"))
        self._remove_actor(self.cache.get("time_playback_actor"))

        if hasattr(self, "disable_vertical_fence_section"):
            self.disable_vertical_fence_section(
                clear_result=True,
                render=False,
                force_clear=True,
            )

        if getattr(self, "static_property_preview", None) is not None:
            self.static_property_preview.clear(render_now=False)

        if getattr(self, "geometry_preview", None) is not None:
            self.geometry_preview.clear_all(render_now=False)

        self.disable_camera_aware_coordinate_axes(clear_axes=True)
        self.deactivate_2d_magnify(render=False)

        try:
            self.plotter.remove_scalar_bar(render=False)
        except Exception:
            pass

        self._clear_result_geometry_overlay(
            detach=True,
            remove_renderer=False,
        )

        self.cache = self._new_cache()
        self._active_property_context = None
        self._property_display_mode = "full"
        self._property_switch_camera_state = None
        self._preserve_camera_on_property_switch = False
        self._six_view_projection_active = False
        self._six_view_left_button_down = False
        self._six_view_press_position = None

        if render_now:
            self._render()

        return True

    def clear_cache(self, full=False, render_now=False):
        """
        兼容外层旧代码。

        属性切换代码即使仍调用 clear_cache()，默认也只做轻量清理，
        不再执行 plotter.clear()。需要真正清空时传 full=True，
        或直接调用 clear_all_cache()。
        """
        if not full:
            return self.clear_result_property_view(
                render_now=render_now,
            )

        return self.clear_all_cache(render_now=render_now)

    def clear_all_cache(self, render_now=False):
        """彻底清空 Plotter 和缓存，仅用于换工程/重新载入数据。"""
        self.disable_cell_info_picking(
            clear_highlight=True,
            render_now=False,
        )
        self.clear_active_property_context(
            refresh_picking=False,
            force=True,
        )
        self._clear_result_geometry_overlay(
            detach=True,
            remove_renderer=False,
        )

        if getattr(self, "static_property_preview", None) is not None:
            self.static_property_preview.clear(render_now=False)

        if getattr(self, "geometry_preview", None) is not None:
            self.geometry_preview.clear_all(render_now=False)

        self.plotter.clear()
        self.cache = self._new_cache()
        self._active_property_context = None
        self._property_display_mode = "full"
        self._property_switch_camera_state = None
        self._preserve_camera_on_property_switch = False
        self._six_view_projection_active = False
        self._six_view_left_button_down = False
        self._six_view_press_position = None

        if render_now:
            self._render()

        return True


    def _remove_actor(self, actor):
        if actor is None:
            return

        
        result_overlay = getattr(
            self,
            "_result_geometry_overlay_renderer",
            None,
        )

        if result_overlay is not None:
            try:
                result_overlay.RemoveActor(actor)
            except Exception:
                pass

        
        
        preview_overlay = getattr(
            self,
            "_geometry_preview_overlay_renderer",
            None,
        )

        if preview_overlay is not None:
            try:
                preview_overlay.RemoveActor(actor)
            except Exception:
                pass

        main_renderer = self._main_result_renderer()

        if main_renderer is not None:
            try:
                main_renderer.RemoveActor(actor)
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
        # 删除任一井 actor 列表时，同步删除对应井名标签。
        cache = getattr(
            self,
            "cache",
            None,
        )

        if isinstance(cache, dict):
            for actor_key, label_key in (
                RESULT_WELL_ACTOR_TO_LABEL_CACHE
            ):
                if actors is cache.get(actor_key):
                    for label_actor in (
                        cache.get(label_key, [])
                        or []
                    ):
                        self._remove_actor(
                            label_actor
                        )

                    cache[label_key] = []

        for actor in actors or []:
            self._remove_actor(actor)

    def _replace_scalar_bar(self, cache_key, title, **kwargs):
        existing = self.cache.get(cache_key)
        if existing is not None:
            try:
                self.plotter.remove_scalar_bar(render=False)
            except Exception:
                try:
                    self.plotter.remove_scalar_bar(render=False)
                except Exception:
                    pass
        scalar_bar = self.plotter.add_scalar_bar(title=title, **kwargs)
        self.cache[cache_key] = scalar_bar
        return scalar_bar

    def _structured_grid_from_field(self, field_data, dimensions):
        points = np.array([[x, y, z] for x, y, z, _ in field_data], dtype=float)
        scalars = np.array([p for _, _, _, p in field_data], dtype=float)
        expected = int(np.prod(dimensions))
        if len(points) != expected:
            return None, None

        grid = pv.StructuredGrid()
        grid.points = points
        grid.dimensions = dimensions
        grid.point_data["Pressure"] = scalars
        return grid, scalars

    def _polydata_from_line_segments(self, segments):
        if not segments:
            return None

        points = []
        lines = []
        point_index = 0

        for start, end in segments:
            start_point = tuple(float(value) for value in start)
            end_point = tuple(float(value) for value in end)
            if start_point == end_point:
                continue

            points.extend([start_point, end_point])
            lines.extend([2, point_index, point_index + 1])
            point_index += 2

        if not points:
            return None

        poly_data = pv.PolyData()
        poly_data.points = np.array(points, dtype=float)
        poly_data.lines = np.array(lines, dtype=np.int64)
        return poly_data

    def render_mode3_smooth_pressure(self, sim_data):
        field_data = sim_data.interpolated_pressure or sim_data.pressure_field
        if not field_data:
            return

        data_hash = hash((len(field_data), tuple(field_data[0]), tuple(field_data[-1])))
        if self.cache["data_hash"] == data_hash and self.cache["pressure_actor"] is not None:
            self.cache["pressure_actor"].visibility = True
            if self.cache["scalar_bar"] is not None:
                self.cache["scalar_bar"].visibility = True
            self.setup_camera(sim_data)
            self._render()
            return

        self._remove_actor(self.cache["pressure_actor"])
        if self.cache["scalar_bar"] is not None:
            try:
                self.plotter.remove_scalar_bar(render=False)
            except Exception:
                pass
            self.cache["scalar_bar"] = None

        if sim_data.interpolated_pressure:
            dimensions = (50, 25, 10)
        else:
            info = sim_data.grid_info
            dimensions = (int(info["nx"]), int(info["ny"]), int(info["nz"]))

        grid, scalars = self._structured_grid_from_field(field_data, dimensions)
        if grid is None:
            self.render_pressure_field(sim_data)
            return

        surface = self._build_result_property_shell_surface(grid)
        min_p = float(np.min(scalars))
        max_p = float(np.max(scalars))

        actor = self.plotter.add_mesh(
            surface,
            scalars="Pressure",
            cmap=get_bright_jet_cmap(),
            clim=[min_p, max_p],
            show_scalar_bar=False,
            opacity=RESULT_PROPERTY_OPACITY,
            render=False,
        )

        scalar_bar = self._replace_scalar_bar(
            "scalar_bar",
            "Pressure (MPa)",
            label_font_size=14,
            title_font_size=16,
            color="#2f3640",
            position_x=0.02,
            position_y=0.55,
            width=0.08,
            height=0.4,
            vertical=True,
            render=False,
        )

        self.cache["data_hash"] = data_hash
        self.cache["pressure_actor"] = actor
        self.cache["scalar_bar"] = scalar_bar

        self.setup_camera(sim_data)
        self._render()
    

    
    @staticmethod
    def _normalize_shared_fracture_type(fracture_type):
        value = str(fracture_type or "").strip().lower()
        aliases = {
            "natural": "natural",
            "dfn": "natural",
            "hydraulic": "hydraulic",
            "artificial": "hydraulic",
            "all": None,
            "fractures": None,
            "": None,
        }
        if value not in aliases:
            raise ValueError(
                f"Unsupported fracture type: {fracture_type}"
            )
        return aliases[value]

    def refresh_geometry_data(
        self,
        sim_data,
        *,
        render_now=True,
    ):
        """刷新当前已显示的井和裂缝 actor，同时保持各图层显隐状态。"""
        if sim_data is None:
            return False

        self.geometry_layers.set_scene_data(
            sim_data,
            render_now=False,
        )

        if render_now:
            self._render()

        return True

    def set_shared_fractures_visible(
        self,
        visible,
        sim_data=None,
        render_now=True,
        fracture_type=None,
    ):
        """按 natural/hydraulic 独立控制模拟与预览共用的裂缝 actors。"""
        visible = bool(visible)
        fracture_type = self._normalize_shared_fracture_type(
            fracture_type
        )

        if sim_data is not None:
            self.geometry_layers.set_scene_data(
                sim_data,
                render_now=False,
            )
        else:
            sim_data = getattr(
                self.geometry_layers,
                "_last_sim_data",
                None,
            )

        if fracture_type is None:
            natural_visible = bool(
                self.geometry_layers
                .is_natural_fractures_visible()
            )
            hydraulic_visible = bool(
                self.geometry_layers
                .is_hydraulic_fractures_visible()
            )

            if visible and sim_data is not None:
                if not natural_visible:
                    self.geometry_layers.render_natural_fractures(
                        sim_data,
                        render_now=False,
                    )
                if not hydraulic_visible:
                    self.geometry_layers.render_hydraulic_fractures(
                        sim_data,
                        render_now=False,
                    )
            elif not visible and (
                natural_visible or hydraulic_visible
            ):
                self.geometry_layers.clear_fractures(
                    render_now=False,
                )

            if render_now:
                self._render()

            return bool(
                self.geometry_layers.is_fractures_visible()
            )

        if fracture_type == "natural":
            is_visible = (
                self.geometry_layers
                .is_natural_fractures_visible
            )
            render_fractures = (
                self.geometry_layers
                .render_natural_fractures
            )
            clear_fractures = (
                self.geometry_layers
                .clear_natural_fractures
            )
        elif fracture_type == "hydraulic":
            is_visible = (
                self.geometry_layers
                .is_hydraulic_fractures_visible
            )
            render_fractures = (
                self.geometry_layers
                .render_hydraulic_fractures
            )
            clear_fractures = (
                self.geometry_layers
                .clear_hydraulic_fractures
            )
        current = bool(is_visible())

        if visible and not current and sim_data is not None:
            render_fractures(
                sim_data,
                render_now=False,
            )
        elif not visible and current:
            clear_fractures(
                render_now=False,
            )

        if render_now:
            self._render()

        return bool(is_visible())


    def set_shared_wells_visible(
        self,
        visible,
        sim_data=None,
        render_now=True,
    ):
        visible = bool(visible)

        if sim_data is not None:
            self.geometry_layers.set_scene_data(
                sim_data,
                render_now=False,
            )
        else:
            sim_data = getattr(
                self.geometry_layers,
                "_last_sim_data",
                None,
            )

        current = self.geometry_layers.is_wells_visible()

        if visible and not current and sim_data is not None:
            self.geometry_layers.render_wells(
                sim_data,
                render_now=False,
            )
        elif not visible and current:
            self.geometry_layers.clear_wells(
                render_now=False,
            )

        if render_now:
            self._render()

        return self.geometry_layers.is_wells_visible()


    
    def render_fractures(self, sim_data):
        """统一裂缝按钮接口：只切换预览阶段创建的同一批裂缝 actor。"""
        visible = self.geometry_layers.is_fractures_visible()
        return self.set_shared_fractures_visible(
            visible=not visible,
            sim_data=sim_data,
            render_now=True,
        )
 
    def create_grid_lines(self, sim_data):
        self._remove_actor(self.cache["grid_lines_actor"])
        self.cache["grid_lines_actor"] = None

        segments = []
        if sim_data.grid_lines:
            for line_data in sim_data.grid_lines:
                segments.append((line_data[:3], line_data[3:6]))
        else:
            lx = sim_data.grid_info["Lx"]
            ly = sim_data.grid_info["Ly"]
            lz = sim_data.grid_info["Lz"]
            nx = sim_data.grid_info["nx"]
            ny = sim_data.grid_info["ny"]
            nz = sim_data.grid_info["nz"]

            for i in range(nx + 1):
                x = i * lx / nx
                for k in range(nz + 1):
                    z = k * lz / nz
                    segments.append(((x, 0, z), (x, ly, z)))

            for j in range(ny + 1):
                y = j * ly / ny
                for k in range(nz + 1):
                    z = k * lz / nz
                    segments.append(((0, y, z), (lx, y, z)))

            for i in range(nx + 1):
                x = i * lx / nx
                for j in range(ny + 1):
                    y = j * ly / ny
                    segments.append(((x, y, 0), (x, y, lz)))

        line_poly_data = self._polydata_from_line_segments(segments)
        if line_poly_data is None:
            return None

        actor = self.plotter.add_mesh(
            line_poly_data,
            color=(0.70, 0.74, 0.80),
            line_width=1.0,
            opacity=0.8,
            render=False,
        )
        self.cache["grid_lines_actor"] = actor
        self._render()
        return actor

    def has_grid_lines(self) -> bool:
        return self.cache.get("grid_lines_actor") is not None

    def ensure_grid_lines(self, sim_data):
        if self.has_grid_lines():
            return self.cache.get("grid_lines_actor")
        return self.create_grid_lines(sim_data)

    def toggle_grid_lines(self, show):
        if self.cache["grid_lines_actor"] is not None:
            self.cache["grid_lines_actor"].visibility = show
        self._render()

    def has_fractures(self, fracture_type=None) -> bool:
        fracture_type = self._normalize_shared_fracture_type(
            fracture_type
        )
        if fracture_type == "natural":
            return bool(
                self.geometry_layers
                .is_natural_fractures_visible()
            )
        if fracture_type == "hydraulic":
            return bool(
                self.geometry_layers
                .is_hydraulic_fractures_visible()
            )
        return bool(
            self.geometry_layers.is_fractures_visible()
        )

    def ensure_fractures(
        self,
        sim_data,
        fracture_type=None,
        render_now=True,
    ) -> bool:
        if self.has_fractures(fracture_type):
            return True

        return bool(
            self.set_shared_fractures_visible(
                visible=True,
                sim_data=sim_data,
                render_now=render_now,
                fracture_type=fracture_type,
            )
        )

    def toggle_fractures(
        self,
        show,
        fracture_type=None,
        sim_data=None,
        render_now=True,
    ):
        """旧接口：直接控制预览/模拟共用的裂缝 actor。"""
        return self.set_shared_fractures_visible(
            visible=show,
            sim_data=sim_data,
            render_now=render_now,
            fracture_type=fracture_type,
        )


    def setup_camera(self, sim_data):
        if getattr(self, "_preserve_camera_on_property_switch", False):
            self._restore_property_switch_camera(consume=False)
            return

        lx = sim_data.grid_info["Lx"]
        ly = sim_data.grid_info["Ly"]
        lz = sim_data.grid_info["Lz"]
        cx, cy, cz = lx / 2.0, ly / 2.0, lz / 2.0
        dist = max(lx, ly, lz) * 2.5

        self.plotter.camera_position = [
            (cx + dist, cy + dist, cz + dist),
            (cx, cy, cz),
            (0, 0, 1),
        ]
        self.plotter.reset_camera(render=False)
        self.plotter.camera.Zoom(1.1)

    def render_fracture_only(self, sim_data):
        self.clear_all_scene(render_now=False)
        self.geometry_layers.render_fractures(
            sim_data,
            render_now=False,
        )
        self.setup_camera(sim_data)
        self._render()

    def _get_active_parent_cells_from_leaf_data(self, sim_data):
        
        cell_data = getattr(
            sim_data,
            "cell_geometry_with_pressure",
            None,
        )

        cpg = getattr(
            sim_data,
            "corner_point_grid",
            None,
        )

        if cell_data is None or cell_data.shape[0] == 0:
            return []

        if cpg is None or not getattr(cpg, "cells", None):
            return []

        nx = int(sim_data.grid_info["nx"])
        ny = int(sim_data.grid_info["ny"])

        active_parent_ids = set(
            np.rint(
                cell_data[:, 1]
            ).astype(np.int64).tolist()
        )

        active_parent_cells = []

        for cell in cpg.cells:

            parent_id = (
                int(cell.ix)
                + int(cell.iy) * nx
                + int(cell.iz) * nx * ny
            )

            if parent_id in active_parent_ids:
                active_parent_cells.append(cell)

        print(
            f"[Parent Grid] total={len(cpg.cells)}, "
            f"active={len(active_parent_cells)}, "
            f"inactive={len(cpg.cells) - len(active_parent_cells)}"
        )

        return active_parent_cells

    def render_corner_point_grid(self, sim_data):
        
        #渲染父网格 / 粗网格。
        
        cpg = getattr(
            sim_data,
            "corner_point_grid",
            None,
        )

        if cpg is None or not getattr(cpg, "cells", None):
            return

        all_parent_cells = cpg.cells

        cell_data = getattr(
            sim_data,
            "cell_geometry_with_pressure",
            None,
        )

        has_leaf_data = (
            cell_data is not None
            and getattr(cell_data, "ndim", 0) == 2
            and cell_data.shape[0] > 0
            and cell_data.shape[1] > 1
        )

        if has_leaf_data:
            parent_cells_to_render = (
                self._get_active_parent_cells_from_leaf_data(
                    sim_data
                )
            )

            if not parent_cells_to_render:
                print(
                    "[Parent Grid] 检测到 leaf 数据，"
                    "但没有匹配到 active parent，取消父网格渲染。"
                )
                return

            render_mode = "active_only"

        else:

            parent_cells_to_render = all_parent_cells
            render_mode = "all_parents"

            print(
                "[Parent Grid] 当前没有 leaf 数据，"
                "暂时渲染全部 parent 网格。"
            )

        first_cell = parent_cells_to_render[0]

        first_corner = np.asarray(
            first_cell.corners[0],
            dtype=np.float64,
        )

        parent_id_sum = 0

        for cell in parent_cells_to_render:
            try:
                parent_id_sum += int(
                    getattr(cell, "id")
                )
            except Exception:

                parent_id_sum += (
                    int(getattr(cell, "ix", 0)) * 1_000_000
                    + int(getattr(cell, "iy", 0)) * 1_000
                    + int(getattr(cell, "iz", 0))
                )

        data_hash = hash(
            (
                render_mode,
                len(parent_cells_to_render),
                parent_id_sum,
                tuple(
                    np.round(
                        first_corner,
                        6,
                    )
                ),
            )
        )

        if (
            self.cache.get("corner_grid_hash") == data_hash
            and self.cache.get("corner_actor") is not None
        ):
            self.cache["corner_actor"].visibility = True

            surface_actor = self.cache.get(
                "corner_surface_actor"
            )

            if surface_actor is not None:
                surface_actor.visibility = True

            self.setup_camera_for_corner_grid(cpg)

            self._finish_property_switch_render()
            return

        self._remove_actor(
            self.cache.get("corner_actor")
        )

        self._remove_actor(
            self.cache.get("corner_surface_actor")
        )

        self.cache["corner_actor"] = None
        self.cache["corner_surface_actor"] = None

        all_points = []
        vtk_cells = []
        offset = 0
        valid_parent_count = 0

        for cell in parent_cells_to_render:

            try:
                pts = np.asarray(
                    cell.corners,
                    dtype=np.float64,
                )
            except Exception:
                continue

            if pts.shape != (8, 3):
                print(
                    "[Parent Grid] 跳过异常 parent，"
                    f"corners shape={pts.shape}"
                )
                continue

            if not np.all(np.isfinite(pts)):
                print(
                    "[Parent Grid] 跳过包含 NaN/Inf 的 parent。"
                )
                continue

            all_points.append(pts)

            vtk_cells.append([
                8,
                offset + 0,
                offset + 1,
                offset + 2,
                offset + 3,
                offset + 4,
                offset + 5,
                offset + 6,
                offset + 7,
            ])

            offset += 8
            valid_parent_count += 1

        if valid_parent_count == 0:
            print(
                "[Parent Grid] 没有可用于渲染的有效 parent 网格。"
            )
            return

        points = np.vstack(
            all_points
        ).astype(np.float32)

        cells = np.hstack(
            vtk_cells
        ).astype(np.int64)

        cell_types = np.full(
            valid_parent_count,
            pv.CellType.HEXAHEDRON,
            dtype=np.uint8,
        )

        grid = pv.UnstructuredGrid(
            cells,
            cell_types,
            points,
        )

        edges = grid.extract_all_edges()

        actor = self.plotter.add_mesh(
            edges,
            color=(0.5, 0.5, 0.5),
            line_width=0.6,
            reset_camera=False,
            render=False,
        )

        surface = self._build_result_property_shell_surface(grid)

        surface_actor = self.plotter.add_mesh(
            surface,
            color=(1.0, 1.0, 1.0),
            opacity=0.1,
            show_edges=False,
            reset_camera=False,
            render=False,
        )

        self.cache["corner_grid_hash"] = data_hash
        self.cache["corner_actor"] = actor
        self.cache["corner_surface_actor"] = surface_actor

        self.cache["corner_grid_render_mode"] = render_mode
        self.cache["corner_grid_parent_count"] = valid_parent_count

        inactive_count = (
            len(all_parent_cells)
            - valid_parent_count
        )

        print(
            "[Parent Grid] Render finished | "
            f"mode={render_mode} | "
            f"total_parent={len(all_parent_cells)} | "
            f"rendered_parent={valid_parent_count} | "
            f"hidden_parent={inactive_count}"
        )

        self.setup_camera_for_corner_grid(cpg)

        self._finish_property_switch_render()

    def setup_camera_for_corner_grid(self, cpg):
        if getattr(self, "_preserve_camera_on_property_switch", False):
            self._restore_property_switch_camera(consume=False)
            return

        min_x = min_y = min_z = float("inf")
        max_x = max_y = max_z = float("-inf")

        for cell in cpg.cells:
            for corner in cell.corners:
                min_x = min(min_x, corner[0])
                max_x = max(max_x, corner[0])
                min_y = min(min_y, corner[1])
                max_y = max(max_y, corner[1])
                min_z = min(min_z, corner[2])
                max_z = max(max_z, corner[2])

        cx = (min_x + max_x) / 2.0
        cy = (min_y + max_y) / 2.0
        cz = (min_z + max_z) / 2.0
        dx = max_x - min_x
        dy = max_y - min_y
        dz = max_z - min_z

        z_ratio = dz / max(dx, dy) if max(dx, dy) > 0 else 1.0
        if z_ratio < 0.1:
            dist = max(dx, dy) * 1.8
            self.plotter.camera_position = [
                (cx + dx * 0.3, cy - dist, cz + dz * 8),
                (cx, cy, cz),
                (0, 0, 1),
            ]
        else:
            dist = max(dx, dy, dz) * 2.5
            self.plotter.camera_position = [
                (cx + dist * 0.8, cy + dist * 0.6, cz + dist * 0.4),
                (cx, cy, cz),
                (0, 0, 1),
            ]

        self.plotter.reset_camera(render=False)
        self.plotter.camera.Zoom(1.0)

    
    def render_corner_fractures(self, sim_data):
        """兼容旧名称，实际调用统一几何渲染器的切换接口。"""
        return self.render_fractures(sim_data)

    def hide_fractures(self, fracture_type=None):
        return self.set_shared_fractures_visible(
            False,
            render_now=True,
            fracture_type=fracture_type,
        )

    
    def set_parsed_well_data(self, well_data):
        """保存 parse_wells() 结果，供模拟前后统一井渲染使用。"""
        if not isinstance(well_data, dict):
            print("[WellRender] 设置井数据失败：well_data 不是 dict。")
            self._parsed_well_data = None
            return False

        wells = well_data.get("wells", [])
        if not isinstance(wells, list):
            print("[WellRender] 设置井数据失败：well_data 中没有 wells 列表。")
            self._parsed_well_data = None
            return False

        self._parsed_well_data = well_data
        print(f"[WellRender] 已保存解析井数据：{len(wells)} 口井")
        return True

    def render_wells(self, sim_data):
        """统一井按钮接口：只切换预览阶段创建的同一批井 actor。"""
        visible = self.geometry_layers.is_wells_visible()
        return self.set_shared_wells_visible(
            visible=not visible,
            sim_data=sim_data,
            render_now=True,
        )

    def hide_wells(self):
        return self.set_shared_wells_visible(
            False,
            render_now=True,
        )

    def render_corner_wells(self, sim_data):
        """兼容旧名称，实际调用统一几何渲染器的切换接口。"""
        return self.render_wells(sim_data)

    @staticmethod
    def _prepare_exact_cell_scalar_surface(
        surface,
        scalar_name,
    ):
        """强制表面只使用原始 cell scalar，不生成或使用 point scalar。"""
        if surface is None:
            return None

        scalar_name = str(scalar_name)

        if scalar_name not in surface.cell_data:
            raise RuntimeError(
                f"surface.cell_data 中缺少 {scalar_name}"
            )

        try:
            if scalar_name in surface.point_data:
                del surface.point_data[scalar_name]
        except Exception:
            pass

        try:
            surface.set_active_scalars(
                scalar_name,
                preference="cell",
            )
        except TypeError:
            surface.set_active_scalars(
                scalar_name,
            )

        return surface


    @staticmethod
    def _configure_exact_cell_scalar_actor(actor):
        """只固定 cell 标量映射方式，不修改透明度、光照或材质。"""
        if actor is None:
            return

        try:
            mapper = actor.GetMapper()
        except Exception:
            mapper = None

        if mapper is None:
            return

        try:
            mapper.SetScalarModeToUseCellData()
        except Exception:
            pass

        try:
            mapper.InterpolateScalarsBeforeMappingOff()
        except Exception:
            try:
                mapper.SetInterpolateScalarsBeforeMapping(False)
            except Exception:
                pass

        try:
            mapper.ScalarVisibilityOn()
        except Exception:
            pass


    def render_pressure_field(self, sim_data):
        if not sim_data.pressure_field:
            print("No pressure field data")
            return

        self._remove_actor(self.cache["pressure_field_actor"])
        if self.cache["pressure_scalar_bar"] is not None:
            try:
                self.plotter.remove_scalar_bar(render=False)
            except Exception:
                pass
            self.cache["pressure_scalar_bar"] = None

        self._render_pressure_field_points(sim_data.pressure_field)

    #压力场渲染
    def render_corner_pressure_field(self, sim_data):

        if getattr(sim_data, "cell_geometry_with_pressure", None) is None:
            return

        self._remove_actor(self.cache.get("pressure_field_actor"))
        self.cache["pressure_field_actor"] = None

        if self.cache.get("pressure_scalar_bar") is not None:
            try:
                self.plotter.remove_scalar_bar(render=False)
            except Exception:
                pass
            self.cache["pressure_scalar_bar"] = None

        try:
            cell_data = sim_data.cell_geometry_with_pressure
            n_cells = cell_data.shape[0]

            if n_cells == 0:
                return

            pressures = np.asarray(
                cell_data[:, 28],
                dtype=np.float64,
            ).copy()
            pmin, pmax = float(np.min(pressures)), float(np.max(pressures))

            all_points = []
            cells = []
            offset = 0

            for i in range(n_cells):

                pts = np.asarray(
                    cell_data[i, 4:28],
                    dtype=np.float64,
                ).reshape(8, 3)
                all_points.append(pts)

                cells.append([
                    8,
                    offset, offset+1, offset+2, offset+3,
                    offset+4, offset+5, offset+6, offset+7
                ])
                offset += 8

            points = np.vstack(all_points)
            cells = np.hstack(cells)

            cell_types = np.full(
                n_cells,
                pv.CellType.HEXAHEDRON,
                dtype=np.uint8
            )

            grid = pv.UnstructuredGrid(cells, cell_types, points)

            grid.cell_data["Pressure"] = pressures

            surface = self._build_result_property_shell_surface(grid)
            surface = self._prepare_exact_cell_scalar_surface(
                surface,
                "Pressure",
            )

            if (
                surface is None
                or surface.n_cells == 0
                or "Pressure" not in surface.cell_data
                or len(surface.cell_data["Pressure"]) != surface.n_cells
            ):
                raise RuntimeError(
                    "Pressure 外壳面与原始单元值映射失败"
                )

            actor = self.plotter.add_mesh(
                surface,
                scalars="Pressure",
                preference="cell",
                cmap=get_bright_jet_cmap(),
                clim=[pmin, pmax],
                opacity=RESULT_PRESSURE_OPACITY,
                show_edges=False,
                show_scalar_bar=False,
                lighting=False,
                smooth_shading=False,
                ambient=1.0,
                diffuse=0.0,
                specular=0.0,
                interpolate_before_map=(
                    RESULT_PRESSURE_INTERPOLATE_BEFORE_MAP
                ),
                reset_camera=False,
                render=False,
            )
            self._configure_exact_cell_scalar_actor(
                actor
            )

            scalar_bar = self._replace_scalar_bar(
                "pressure_scalar_bar",
                "Pressure (bar)",
                position_x=0.02,
                position_y=0.55,
                width=0.08,
                height=0.40,
                label_font_size=14,
                title_font_size=16,
                color="#2f3640",
                vertical=True,
                render=False,
            )

            self.cache["pressure_field_actor"] = actor
            self.cache["pressure_scalar_bar"] = scalar_bar

            self._register_result_property_context(
                sim_data=sim_data,
                property_name="Pressure",
                volume_grid=grid,
                actor=actor,
                title="Pressure",
                unit="bar",
            )

            self._finish_property_switch_render()

        except Exception as exc:
            print("\n")
            print("=" * 60)
            print("ERROR IN render_corner_pressure_field")
            print(exc)
            print("=" * 60)
            print("\n")



    def _render_pressure_field_points(self, field_data):
        points = np.array([[x, y, z] for x, y, z, _ in field_data], dtype=float)
        pressures = np.array([p for _, _, _, p in field_data], dtype=float)
        pressure_min = float(np.min(pressures))
        pressure_max = float(np.max(pressures))

        cloud = pv.PolyData(points)
        cloud.point_data["Pressure"] = pressures
        actor = self.plotter.add_volume(
            cloud,
            scalars="Pressure",
            cmap=get_bright_jet_cmap(),
            clim=[pressure_min, pressure_max],
            opacity=RESULT_PROPERTY_OPACITY,
            opacity_unit_distance=50,
            blending="maximum",
            shade=False,
            mapper="gpu",
        )
        scalar_bar = self._replace_scalar_bar(
            "pressure_scalar_bar",
            "Pressure (bar)",
            position_x=0.02,
            position_y=0.55,
            width=0.08,
            height=0.4,
            label_font_size=14,
            title_font_size=16,
            color="#2f3640",
            vertical=True,
            render=False,
        )

        self.cache["pressure_field_actor"] = actor
        self.cache["pressure_scalar_bar"] = scalar_bar
        self._render()

    def hide_pressure_field(self):
        self._remove_actor(self.cache["pressure_field_actor"])
        self.cache["pressure_field_actor"] = None
        if self.cache["pressure_scalar_bar"] is not None:
            try:
                self.plotter.remove_scalar_bar(render=False)
            except Exception:
                pass
            self.cache["pressure_scalar_bar"] = None
        self._render()


    def toggle_grid_visibility(self, visible):
        """预览和模拟共用的网格显隐入口。"""
        visible = bool(visible)

        for key in (
            "corner_actor",
            "corner_surface_actor",
            "grid_lines_actor",
            "corner_lgr_parent_grid_actor",
            "corner_lgr_refined_grid_actor",
            "layer_coarse_grid_actor",
            "layer_sw_coarse_grid_actor",
            "layer_phi_coarse_grid_actor",
            "layer_perm_coarse_grid_actor",
            "threshold_grid_actor",
        ):
            self._set_scene_actor_visibility(
                self.cache.get(key),
                visible,
            )

        geometry = getattr(self, "geometry_layers", None)
        if geometry is None:
            geometry = getattr(self, "geometry_preview", None)

        if geometry is not None:
            for actor_name in (
                "grid_actor",
                "grid_edge_actor",
                "grid_internal_edge_actor",
            ):
                actor = getattr(geometry, actor_name, None)
                if actor_name == "grid_internal_edge_actor":
                    requested = bool(
                        getattr(geometry, "show_internal_grid_edges", True)
                    )
                    self._set_scene_actor_visibility(
                        actor,
                        visible and requested,
                    )
                else:
                    self._set_scene_actor_visibility(actor, visible)

        self._render()
        return True

    def toggle_fractures_visibility(
        self,
        visible,
        fracture_type=None,
        sim_data=None,
        render_now=True,
    ):
        """模拟和预览按钮共同控制同一批预览裂缝 actor。"""
        return self.set_shared_fractures_visible(
            visible=visible,
            sim_data=sim_data,
            render_now=render_now,
            fracture_type=fracture_type,
        )

    def toggle_wells_visibility(
        self,
        visible,
        sim_data=None,
        render_now=True,
    ):
        """模拟和预览按钮共同控制同一批预览井 actor。"""
        return self.set_shared_wells_visible(
            visible=visible,
            sim_data=sim_data,
            render_now=render_now,
        )


    def toggle_pressure_visibility(self, visible):
        """
        兼容旧 UI 名称：控制当前属性显示；剖面模式下只控制剖面。
        """
        visible = bool(visible)
        context = self.get_active_property_context()

        if self.is_fence_property_display_mode():
            self._set_scene_actor_visibility(
                self.cache.get("fence_section_actor"),
                visible,
            )
            self._set_scene_actor_visibility(
                self.cache.get("fence_section_scalar_bar"),
                visible,
            )
            if isinstance(context, dict):
                self._set_scene_actor_visibility(context.get("actor"), False)
            self._hide_fence_section_context()
        else:
            if isinstance(context, dict):
                self._set_scene_actor_visibility(
                    context.get("actor"),
                    visible,
                )

            for actor in self._active_property_scalar_bar_actors(context):
                self._set_scene_actor_visibility(actor, visible)

        self._render()
        return True


    def apply_layer_visibility(
        self,
        show_grid,
        show_fractures,
        show_wells,
        show_pressure,
    ):
        """
        统一分层显隐入口。

        show_pressure 兼容旧名称，实际控制当前预览/模拟属性 actor；
        井和裂缝始终控制 GeometryLayerRenderer 中唯一的一套 actor。
        """
        show_grid = bool(show_grid)
        show_property = bool(show_pressure)

        for key in (
            "layer_coarse_grid_actor",
            "layer_sw_coarse_grid_actor",
            "layer_phi_coarse_grid_actor",
            "layer_perm_coarse_grid_actor",
        ):
            self._set_scene_actor_visibility(
                self.cache.get(key),
                show_grid,
            )

        geometry = getattr(self, "geometry_layers", None)
        if geometry is None:
            geometry = getattr(self, "geometry_preview", None)

        if geometry is not None:
            for actor_name in (
                "grid_actor",
                "grid_edge_actor",
                "grid_internal_edge_actor",
            ):
                actor = getattr(geometry, actor_name, None)
                if actor_name == "grid_internal_edge_actor":
                    requested = bool(
                        getattr(geometry, "show_internal_grid_edges", True)
                    )
                    self._set_scene_actor_visibility(
                        actor,
                        show_grid and requested,
                    )
                else:
                    self._set_scene_actor_visibility(actor, show_grid)

        context = self.get_active_property_context()
        if self.is_fence_property_display_mode():
            self._set_scene_actor_visibility(
                self.cache.get("fence_section_actor"),
                show_property,
            )
            self._set_scene_actor_visibility(
                self.cache.get("fence_section_scalar_bar"),
                show_property,
            )
            if isinstance(context, dict):
                self._set_scene_actor_visibility(context.get("actor"), False)
            self._hide_fence_section_context()
        elif isinstance(context, dict):
            self._set_scene_actor_visibility(
                context.get("actor"),
                show_property,
            )
            for actor in self._active_property_scalar_bar_actors(context):
                self._set_scene_actor_visibility(actor, show_property)

        self.set_shared_fractures_visible(
            visible=show_fractures,
            render_now=False,
        )
        self.set_shared_wells_visible(
            visible=show_wells,
            render_now=False,
        )

        self._render()
        return True

    @staticmethod
    def _get_grid_line_tolerance(*grid_geometries):

        valid_points = []

        for geometry in grid_geometries:
            if geometry is None:
                continue

            try:
                array = np.asarray(
                    geometry,
                    dtype=np.float64,
                )
            except Exception:
                continue

            if array.size == 0:
                continue

            try:
                array = array.reshape(-1, 3)
            except ValueError:
                continue

            finite_mask = np.isfinite(array).all(axis=1)
            array = array[finite_mask]

            if len(array) > 0:
                valid_points.append(array)

        if not valid_points:
            return 1e-7

        points = np.vstack(valid_points)
        spans = np.ptp(points, axis=0)
        reference_span = float(np.max(spans))

        return max(reference_span * 1e-10, 1e-7)


    @staticmethod
    def _make_grid_point_key(point, tolerance):
        point = np.asarray(
            point,
            dtype=np.float64,
        )

        return tuple(
            np.rint(point / float(tolerance))
            .astype(np.int64)
            .tolist()
        )


    def _collect_unique_grid_line_segments(
        self,
        grid_geom,
        tolerance,
        excluded_edge_keys=None,
    ):

        if grid_geom is None:
            return [], set()

        try:
            geometry = np.asarray(
                grid_geom,
                dtype=np.float64,
            )
        except Exception:
            return [], set()

        if geometry.size == 0:
            return [], set()

        if geometry.ndim == 2:
            if geometry.shape[1] < 24:
                return [], set()

            geometry = geometry[:, :24].reshape(-1, 8, 3)

        elif geometry.ndim == 3:
            if geometry.shape[1:] != (8, 3):
                return [], set()

        else:
            return [], set()

        local_edges = (
            (0, 1), (1, 2), (2, 3), (3, 0),
            (4, 5), (5, 6), (6, 7), (7, 4),
            (0, 4), (1, 5), (2, 6), (3, 7),
        )

        excluded_edge_keys = set(
            excluded_edge_keys or ()
        )

        unique_edge_keys = set()
        unique_segments = []

        for corners in geometry:
            if not np.isfinite(corners).all():
                continue

            for start_index, end_index in local_edges:
                start_point = corners[start_index]
                end_point = corners[end_index]

                if np.linalg.norm(
                    end_point - start_point
                ) <= float(tolerance):
                    continue

                start_key = self._make_grid_point_key(
                    start_point,
                    tolerance,
                )
                end_key = self._make_grid_point_key(
                    end_point,
                    tolerance,
                )

                edge_key = (
                    (start_key, end_key)
                    if start_key <= end_key
                    else (end_key, start_key)
                )

                if edge_key in excluded_edge_keys:
                    continue

                if edge_key in unique_edge_keys:
                    continue

                unique_edge_keys.add(edge_key)
                unique_segments.append(
                    (
                        tuple(float(value) for value in start_point),
                        tuple(float(value) for value in end_point),
                    )
                )

        return unique_segments, unique_edge_keys


    def _create_grid_lines_actor(
        self,
        grid_geom,
        color,
        line_width,
        opacity,
        excluded_edge_keys=None,
        tolerance=None,
        return_edge_keys=False,
    ):
        """创建稳定的父网格/加密网格线 actor。"""
        if grid_geom is None:
            return (None, set()) if return_edge_keys else None

        try:
            if np.asarray(grid_geom).size == 0:
                return (None, set()) if return_edge_keys else None
        except Exception:
            return (None, set()) if return_edge_keys else None

        if tolerance is None:
            tolerance = self._get_grid_line_tolerance(
                grid_geom
            )

        segments, edge_keys = (
            self._collect_unique_grid_line_segments(
                grid_geom=grid_geom,
                tolerance=tolerance,
                excluded_edge_keys=excluded_edge_keys,
            )
        )

        line_poly_data = self._polydata_from_line_segments(
            segments
        )

        if line_poly_data is None:
            return (None, edge_keys) if return_edge_keys else None

        
        stable_line_width = max(
            float(line_width),
            1.0,
        )

        stable_opacity = float(
            np.clip(opacity, 0.0, 1.0)
        )

        mesh_kwargs = dict(
            reset_camera=False,
            color=color,
            line_width=stable_line_width,
            opacity=stable_opacity,
            lighting=False,
            render=False,
        )

        try:
            actor = self.plotter.add_mesh(
                line_poly_data,
                render_lines_as_tubes=(
                    RESULT_GRID_RENDER_LINES_AS_TUBES
                ),
                **mesh_kwargs,
            )
        except TypeError:
            
            actor = self.plotter.add_mesh(
                line_poly_data,
                **mesh_kwargs,
            )

        if actor is not None:
            try:
                prop = actor.GetProperty()

                if prop is not None:
                    prop.SetLineWidth(stable_line_width)
                    prop.SetOpacity(stable_opacity)

                    try:
                        prop.LightingOff()
                    except Exception:
                        pass

                    try:
                        if RESULT_GRID_RENDER_LINES_AS_TUBES:
                            prop.RenderLinesAsTubesOn()
                        else:
                            prop.RenderLinesAsTubesOff()
                    except Exception:
                        try:
                            prop.SetRenderLinesAsTubes(
                                bool(RESULT_GRID_RENDER_LINES_AS_TUBES)
                            )
                        except Exception:
                            pass
            except Exception:
                pass

            
            if stable_opacity >= 0.999:
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
                mapper = actor.GetMapper()

                if mapper is not None and hasattr(
                    mapper,
                    "SetResolveCoincidentTopologyToPolygonOffset",
                ):
                    mapper.SetResolveCoincidentTopologyToPolygonOffset()

                if mapper is not None and hasattr(
                    mapper,
                    "SetRelativeCoincidentTopologyLineOffsetParameters",
                ):
                    mapper.SetRelativeCoincidentTopologyLineOffsetParameters(
                        0.0,
                        -2.0,
                    )
            except Exception:
                pass

        if return_edge_keys:
            return actor, edge_keys

        return actor

    # NOTE: 此定义会被下方第二个 render_corner_lgr_grid 覆盖，保留仅用于参考旧实现。
    def render_corner_lgr_grid(self, sim_data):
        self._remove_actor(self.cache["corner_lgr_parent_grid_actor"])
        self._remove_actor(self.cache["corner_lgr_refined_grid_actor"])
        self.cache["corner_lgr_parent_grid_actor"] = None
        self.cache["corner_lgr_refined_grid_actor"] = None

        if getattr(sim_data, "corner_lgr_parent_grid_geometry", None) is not None:
            self.cache["corner_lgr_parent_grid_actor"] = self._create_grid_lines_actor(
                sim_data.corner_lgr_parent_grid_geometry,
                (1.0, 1.0, 1.0),
                0.5,
                0.3,
            )

        if getattr(sim_data, "corner_lgr_refined_grid_geometry", None) is not None:
            self.cache["corner_lgr_refined_grid_actor"] = self._create_grid_lines_actor(
                sim_data.corner_lgr_refined_grid_geometry,
                (1.0, 1.0, 1.0),
                1.0,
                0.8,
            )

        self._render()

    
    """def render_corner_lgr_grid(self, sim_data):

        self._remove_actor(self.cache["corner_lgr_parent_grid_actor"])
        self._remove_actor(self.cache["corner_lgr_refined_grid_actor"])

        self.cache["corner_lgr_parent_grid_actor"] = None
        self.cache["corner_lgr_refined_grid_actor"] = None

        if getattr(sim_data, "corner_lgr_parent_grid_geometry", None) is not None:

            self.cache["corner_lgr_parent_grid_actor"] = self._create_grid_lines_actor(
                sim_data.corner_lgr_parent_grid_geometry,
                (0.7, 0.7, 0.7),
                0.4,
                0.15,
            )
        refined_geom = getattr(sim_data, "corner_lgr_refined_grid_geometry", None)

        if refined_geom is None:
            self._render()
            return

        if not hasattr(sim_data, "cell_geometry_with_pressure"):
            self._render()
            return

        cell_data = sim_data.cell_geometry_with_pressure

        if cell_data is None or len(cell_data) == 0:
            self._render()
            return

        try:

            n_cells = refined_geom.shape[0]

            pressures = cell_data[:, 28].astype(np.float32)

            pressure_min = float(np.min(pressures))
            pressure_max = float(np.max(pressures))
            raw_points = refined_geom.reshape(-1, 3).astype(np.float32)

            points, inverse = np.unique(
                raw_points,
                axis=0,
                return_inverse=True
            )

            inverse = inverse.reshape(n_cells, 8)
            cell_array = np.empty(n_cells * 9, dtype=np.int64)

            cell_array[0::9] = 8

            for i in range(n_cells):

                start = i * 9 + 1

                cell_array[start:start + 8] = inverse[i]

            cell_types = np.full(
                n_cells,
                pv.CellType.HEXAHEDRON,
                dtype=np.uint8
            )

            grid = pv.UnstructuredGrid(
                cell_array,
                cell_types,
                points
            )

            grid.cell_data["Pressure"] = pressures

            grid = grid.cell_data_to_point_data()

            surface = self._build_result_property_shell_surface(grid)
            actor = self.plotter.add_mesh(
                surface,
                scalars="Pressure",
                cmap=get_bright_jet_cmap(),
                clim=[pressure_min, pressure_max],
                opacity=0.68,
                smooth_shading=True,
                lighting=True,
                ambient=0.35,
                diffuse=0.75,
                specular=0.08,
                show_edges=True,
                edge_color=(0.15, 0.15, 0.15),
                line_width=0.35,
                render=False,
            )

            self.cache["corner_lgr_refined_grid_actor"] = actor

        except Exception as exc:

            print("\n")
            print("=" * 60)
            print("ERROR IN render_corner_lgr_grid")
            print(exc)
            print("=" * 60)
            print("\n")

        self._render()"""

    def render_corner_lgr_grid(self, sim_data):

        self._remove_actor(
            self.cache["corner_lgr_parent_grid_actor"]
        )
        self._remove_actor(
            self.cache["corner_lgr_refined_grid_actor"]
        )

        self.cache["corner_lgr_parent_grid_actor"] = None
        self.cache["corner_lgr_refined_grid_actor"] = None

        parent_geom = getattr(
            sim_data,
            "corner_lgr_parent_grid_geometry",
            None,
        )

        refined_geom = getattr(
            sim_data,
            "corner_lgr_refined_grid_geometry",
            None,
        )

        common_tolerance = self._get_grid_line_tolerance(
            parent_geom,
            refined_geom,
        )

        parent_edge_keys = set()

        if parent_geom is not None:
            parent_actor, parent_edge_keys = (
                self._create_grid_lines_actor(
                    grid_geom=parent_geom,
                    color=(0.5, 0.5, 0.5),
                    line_width=1.0,
                    opacity=1.0,
                    tolerance=common_tolerance,
                    return_edge_keys=True,
                )
            )

            self.cache[
                "corner_lgr_parent_grid_actor"
            ] = parent_actor

        if refined_geom is not None:
            self.cache[
                "corner_lgr_refined_grid_actor"
            ] = self._create_grid_lines_actor(
                grid_geom=refined_geom,
                color=(0.5, 0.5, 0.5),
                line_width=1.0,
                opacity=1.0,
                excluded_edge_keys=parent_edge_keys,
                tolerance=common_tolerance,
            )

        self._finish_property_switch_render()

    def toggle_corner_lgr_grid_visibility(self, visible):
        if self.cache["corner_lgr_parent_grid_actor"] is not None:
            self.cache["corner_lgr_parent_grid_actor"].visibility = visible
        if self.cache["corner_lgr_refined_grid_actor"] is not None:
            self.cache["corner_lgr_refined_grid_actor"].visibility = visible
        self._render()


    def set_full_corner_result_visibility(self, visible):
        """
        兼容旧接口：控制当前整体属性和网格，预览/模拟均可使用。
        井和裂缝是全局几何层，不受该接口影响。
        """
        visible = bool(visible)

        for key in (
            "corner_actor",
            "corner_surface_actor",
            "grid_lines_actor",
            "corner_lgr_parent_grid_actor",
            "corner_lgr_refined_grid_actor",
        ):
            self._set_scene_actor_visibility(
                self.cache.get(key),
                visible,
            )

        context = self.get_active_property_context()
        if isinstance(context, dict) and context.get("axis") is None:
            self._set_scene_actor_visibility(
                context.get("actor"),
                visible,
            )
            for actor in self._active_property_scalar_bar_actors(context):
                self._set_scene_actor_visibility(actor, visible)

        geometry = getattr(self, "geometry_layers", None)
        if geometry is not None:
            for actor_name in (
                "grid_actor",
                "grid_edge_actor",
                "grid_internal_edge_actor",
            ):
                actor = getattr(geometry, actor_name, None)
                if actor_name == "grid_internal_edge_actor":
                    requested = bool(
                        getattr(geometry, "show_internal_grid_edges", True)
                    )
                    self._set_scene_actor_visibility(
                        actor,
                        visible and requested,
                    )
                else:
                    self._set_scene_actor_visibility(actor, visible)

        self._render()
        return True


    def _get_layer_row_indices_by_parent_id(
        self,
        sim_data,
        axis,
        layer_index,
        cell_data=None,
    ):

        if cell_data is None:
            cell_data = getattr(
                sim_data,
                "cell_geometry_with_pressure",
                None,
            )

        if cell_data is None or cell_data.shape[0] == 0:
            return np.empty(0, dtype=np.int64)

        axis = str(axis).lower().strip()
        layer_index = int(layer_index)

        if axis not in ("i", "j", "k"):
            raise ValueError(
                f"axis 必须是 i / j / k，当前为：{axis}"
            )

        nx = int(sim_data.grid_info["nx"])
        ny = int(sim_data.grid_info["ny"])
        nz = int(sim_data.grid_info["nz"])

        max_index = {
            "i": nx - 1,
            "j": ny - 1,
            "k": nz - 1,
        }[axis]

        if layer_index < 0 or layer_index > max_index:
            raise ValueError(
                f"{axis.upper()} 层索引无效：{layer_index}，"
                f"合法范围为 0 ~ {max_index}"
            )

        parent_ids = np.rint(
            cell_data[:, 1]
        ).astype(np.int64)

        parent_i = parent_ids % nx
        parent_j = (parent_ids // nx) % ny
        parent_k = parent_ids // (nx * ny)

        if axis == "i":
            mask = parent_i == layer_index

        elif axis == "j":
            mask = parent_j == layer_index

        else:
            mask = parent_k == layer_index

        return np.flatnonzero(mask).astype(np.int64)


    def _replace_layer_grid_with_refined_grid(
        self,
        selected_rows,
        cache_key,
        show_grid=True,
    ):
        """
        用当前分层命中的 leaf/refined cells 绘制网格线。

        cache_key 继续沿用原来的 *_coarse_grid_actor 名称，
        以兼容现有 UI 显隐逻辑；实际保存的 actor 已经是加密网格。
        """
        self._remove_actor(
            self.cache.get(cache_key)
        )
        self.cache[cache_key] = None

        if not show_grid:
            return None

        try:
            refined_geometry = np.asarray(
                selected_rows[:, 4:28],
                dtype=np.float64,
            ).reshape(-1, 8, 3)
        except (
            TypeError,
            ValueError,
            IndexError,
        ):
            return None

        if refined_geometry.size == 0:
            return None

        valid_cell_mask = np.isfinite(
            refined_geometry
        ).all(axis=(1, 2))

        refined_geometry = refined_geometry[
            valid_cell_mask
        ]

        if refined_geometry.shape[0] == 0:
            return None

        actor = self._create_grid_lines_actor(
            grid_geom=refined_geometry,
            color=(0.5, 0.5, 0.5),
            line_width=1.0,
            opacity=1.0,
        )

        self.cache[cache_key] = actor
        return actor


    def clear_layer_render(self):
        """Remove layer-render actors so full-field rendering can take over cleanly."""
        self._remove_actor(self.cache.get("layer_pressure_actor"))
        self._remove_actor(self.cache.get("layer_coarse_grid_actor"))
        self._remove_actor_list(self.cache.get("layer_frac_actors", []))
        self._remove_actor_list(self.cache.get("layer_well_actors", []))

        layer_scalar_bar = self.cache.get("layer_pressure_scalar_bar")
        if layer_scalar_bar is not None:
            try:
                layer_scalar_bar.visibility = False
                self.plotter.remove_scalar_bar()
            except Exception:
                pass

        self.cache["layer_pressure_actor"] = None
        self.cache["layer_pressure_scalar_bar"] = None
        self.cache["layer_coarse_grid_actor"] = None
        self.cache["layer_frac_actors"] = []
        self.cache["layer_well_actors"] = []
        self._render()


    def _add_layer_pressure_mesh(
        self,
        surface,
        pressures_all
    ):

        surface = self._prepare_exact_cell_scalar_surface(
            surface,
            "Pressure",
        )

        actor = self.plotter.add_mesh(
            surface,
            scalars="Pressure",
            preference="cell",
            cmap=get_bright_jet_cmap(),
            clim=[
                float(np.min(pressures_all)),
                float(np.max(pressures_all))
            ],
            opacity=RESULT_PRESSURE_OPACITY,
            show_scalar_bar=False,
            show_edges=False,
            lighting=False,
            smooth_shading=False,
            ambient=1.0,
            diffuse=0.0,
            specular=0.0,
            interpolate_before_map=(
                RESULT_PRESSURE_INTERPOLATE_BEFORE_MAP
            ),
            render=False,
        )
        self._configure_exact_cell_scalar_actor(
            actor
        )

        scalar_bar = self._replace_scalar_bar(
            "layer_pressure_scalar_bar",
            "Pressure (bar)",
            position_x=0.02,
            position_y=0.55,
            width=0.08,
            height=0.4,
            label_font_size=14,
            title_font_size=16,
            color="#2f3640",
            vertical=True,
            render=False,
        )

        self.cache["layer_pressure_actor"] = actor
        self.cache["layer_pressure_scalar_bar"] = scalar_bar

        return actor, scalar_bar


    # 新增：根据 Z 坐标渲染地质切片  
    def render_corner_grid_by_layer_k(self, sim_data, k_layer: int):

        self._remove_actor(self.cache.get("layer_pressure_actor"))
        self._remove_actor(self.cache.get("layer_coarse_grid_actor"))


        self.cache["layer_pressure_actor"] = None
        self.cache["layer_coarse_grid_actor"] = None

        
        try:
            self.plotter.remove_scalar_bar(render=False)
        except Exception:
            pass
        self.cache["layer_pressure_scalar_bar"] = None

        if not sim_data.corner_point_grid:
            return

        if not hasattr(sim_data, "cell_geometry_with_pressure"):
            return

        cpg = sim_data.corner_point_grid
        nx = int(sim_data.grid_info["nx"])
        ny = int(sim_data.grid_info["ny"])
        nz = int(sim_data.grid_info["nz"])

        if k_layer < 0 or k_layer >= nz:
            print(f"Invalid k_layer = {k_layer}")
            return

        start = k_layer * nx * ny
        end = (k_layer + 1) * nx * ny
        coarse_cells = cpg.cells[start:end]

        coarse_boxes = []
        coarse_points = []
        coarse_cell_array = []
        coarse_cell_types = []

        point_offset = 0

        for cell in coarse_cells:
            pts = np.array(cell.corners, dtype=np.float32)
            if pts.shape != (8, 3):
                continue

            xs = pts[:, 0]
            ys = pts[:, 1]
            zs = pts[:, 2]

            coarse_boxes.append({
                "xmin": xs.min(),
                "xmax": xs.max(),
                "ymin": ys.min(),
                "ymax": ys.max(),
                "zmin": zs.min(),
                "zmax": zs.max(),
            })

            coarse_points.extend(pts)

            coarse_cell_array.extend([
                8, point_offset + 0, point_offset + 1, point_offset + 2, point_offset + 3,
                point_offset + 4, point_offset + 5, point_offset + 6, point_offset + 7
            ])

            coarse_cell_types.append(pv.CellType.HEXAHEDRON)
            point_offset += 8

        
        

        all_data = sim_data.cell_geometry_with_pressure

        try:
            selected_indices = self._get_layer_row_indices_by_parent_id(
                sim_data=sim_data,
                axis="k",
                layer_index=k_layer,
                cell_data=all_data,
            )
        except ValueError as exc:
            print(exc)
            self._render()
            return

        if selected_indices.size == 0:
            print(f"No leaf cells found for k layer = {k_layer}")
            self._render()
            return

        selected_rows = all_data[selected_indices]

        all_points = []
        cell_corner_ids = []

        for row in selected_rows:
            pts = row[4:28].reshape(8, 3)
            start_idx = len(all_points)
            all_points.extend(pts)
            cell_corner_ids.append(list(range(start_idx, start_idx + 8)))

        all_points = np.array(all_points)
        points, inverse = np.unique(all_points, axis=0, return_inverse=True)

        n_cells = len(cell_corner_ids)
        cell_array = np.empty(n_cells * 9, dtype=np.int64)
        cell_types = np.full(n_cells, pv.CellType.HEXAHEDRON, dtype=np.uint8)

        for i in range(n_cells):
            cell_array[i * 9] = 8
            ids = inverse[i * 8:(i + 1) * 8]
            cell_array[i * 9 + 1:i * 9 + 9] = ids

        grid = pv.UnstructuredGrid(cell_array, cell_types, points)
        pressures = np.asarray(selected_rows[:, 28], dtype=np.float64).copy()
        pressures_all = np.asarray(
            sim_data.cell_geometry_with_pressure[:, 28],
            dtype=np.float64,
        ).copy()
        grid.cell_data["Pressure"] = pressures

        surface = self._build_result_property_shell_surface(grid)
        self._add_layer_pressure_mesh(
            surface,
            pressures_all
        )

        self._replace_layer_grid_with_refined_grid(
            selected_rows=selected_rows,
            cache_key="layer_coarse_grid_actor",
            show_grid=True,
        )

        self._register_result_property_context(
            sim_data=sim_data,
            property_name="Pressure",
            volume_grid=grid,
            actor=self.cache.get("layer_pressure_actor"),
            axis="k",
            layer_index=k_layer,
            title="Pressure",
            unit="bar",
            source_indices=selected_indices,
        )

        
        self._finish_property_switch_render()

    #i方向
    def render_corner_grid_by_layer_i(self, sim_data, i_layer: int):

        self._remove_actor(self.cache.get("layer_pressure_actor"))
        self._remove_actor(self.cache.get("layer_coarse_grid_actor"))


        self.cache["layer_pressure_actor"] = None
        self.cache["layer_coarse_grid_actor"] = None

        if not sim_data.corner_point_grid:
            return

        if not hasattr(sim_data, "cell_geometry_with_pressure"):
            return

        cpg = sim_data.corner_point_grid

        nx = int(sim_data.grid_info["nx"])
        ny = int(sim_data.grid_info["ny"])
        nz = int(sim_data.grid_info["nz"])

        if i_layer < 0 or i_layer >= nx:
            print(f"Invalid i_layer = {i_layer}")
            return

        
        
        
        coarse_cells = []

        for j in range(ny):
            for k in range(nz):

                idx = i_layer + j * nx + k * nx * ny

                if idx < len(cpg.cells):
                    coarse_cells.append(cpg.cells[idx])

        coarse_boxes = []

        coarse_points = []

        coarse_cell_array = []

        coarse_cell_types = []

        point_offset = 0

        for cell in coarse_cells:

            pts = np.array(cell.corners, dtype=np.float32)

            if pts.shape != (8, 3):
                continue

            xs = pts[:, 0]
            ys = pts[:, 1]
            zs = pts[:, 2]

            coarse_boxes.append({
                "xmin": xs.min(),
                "xmax": xs.max(),
                "ymin": ys.min(),
                "ymax": ys.max(),
                "zmin": zs.min(),
                "zmax": zs.max(),
            })

            coarse_points.extend(pts)

            coarse_cell_array.extend([
                8,
                point_offset + 0,
                point_offset + 1,
                point_offset + 2,
                point_offset + 3,
                point_offset + 4,
                point_offset + 5,
                point_offset + 6,
                point_offset + 7
            ])

            coarse_cell_types.append(pv.CellType.HEXAHEDRON)

            point_offset += 8

        
        

        all_data = sim_data.cell_geometry_with_pressure

        try:
            selected_indices = self._get_layer_row_indices_by_parent_id(
                sim_data=sim_data,
                axis="i",
                layer_index=i_layer,
                cell_data=all_data,
            )
        except ValueError as exc:
            print(exc)
            self._render()
            return

        if selected_indices.size == 0:
            print(f"No leaf cells found for i layer = {i_layer}")
            self._render()
            return

        selected_rows = all_data[selected_indices]

        all_points = []

        cell_corner_ids = []

        for row in selected_rows:

            pts = row[4:28].reshape(8, 3)

            start_idx = len(all_points)

            all_points.extend(pts)

            cell_corner_ids.append(
                list(range(start_idx, start_idx + 8))
            )

        all_points = np.array(all_points)

        points, inverse = np.unique(
            all_points,
            axis=0,
            return_inverse=True
        )

        n_cells = len(cell_corner_ids)

        cell_array = np.empty(n_cells * 9, dtype=np.int64)

        cell_types = np.full(
            n_cells,
            pv.CellType.HEXAHEDRON,
            dtype=np.uint8
        )

        for i in range(n_cells):

            cell_array[i * 9] = 8

            ids = inverse[i * 8:(i + 1) * 8]

            cell_array[
                i * 9 + 1:i * 9 + 9
            ] = ids

        grid = pv.UnstructuredGrid(
            cell_array,
            cell_types,
            points
        )

        pressures = np.asarray(selected_rows[:, 28], dtype=np.float64).copy()

        pressures_all = np.asarray(
            sim_data.cell_geometry_with_pressure[:, 28],
            dtype=np.float64,
        ).copy()

        grid.cell_data["Pressure"] = pressures


        surface = self._build_result_property_shell_surface(grid)
        self._add_layer_pressure_mesh(
            surface,
            pressures_all
        )

        self._replace_layer_grid_with_refined_grid(
            selected_rows=selected_rows,
            cache_key="layer_coarse_grid_actor",
            show_grid=True,
        )

        self._register_result_property_context(
            sim_data=sim_data,
            property_name="Pressure",
            volume_grid=grid,
            actor=self.cache.get("layer_pressure_actor"),
            axis="i",
            layer_index=i_layer,
            title="Pressure",
            unit="bar",
            source_indices=selected_indices,
        )

        
        self._finish_property_switch_render()

    # j方向
    def render_corner_grid_by_layer_j(self, sim_data, j_layer: int):

        self._remove_actor(self.cache.get("layer_pressure_actor"))
        self._remove_actor(self.cache.get("layer_coarse_grid_actor"))


        self.cache["layer_pressure_actor"] = None
        self.cache["layer_coarse_grid_actor"] = None

        if not sim_data.corner_point_grid:
            return

        if not hasattr(sim_data, "cell_geometry_with_pressure"):
            return

        cpg = sim_data.corner_point_grid

        nx = int(sim_data.grid_info["nx"])
        ny = int(sim_data.grid_info["ny"])
        nz = int(sim_data.grid_info["nz"])

        if j_layer < 0 or j_layer >= ny:
            print(f"Invalid j_layer = {j_layer}")
            return

        coarse_cells = []

        for i in range(nx):
            for k in range(nz):

                idx = i + j_layer * nx + k * nx * ny

                if idx < len(cpg.cells):
                    coarse_cells.append(cpg.cells[idx])

        coarse_boxes = []

        coarse_points = []

        coarse_cell_array = []

        coarse_cell_types = []

        point_offset = 0

        for cell in coarse_cells:

            pts = np.array(cell.corners, dtype=np.float32)

            if pts.shape != (8, 3):
                continue

            xs = pts[:, 0]
            ys = pts[:, 1]
            zs = pts[:, 2]

            coarse_boxes.append({
                "xmin": xs.min(),
                "xmax": xs.max(),
                "ymin": ys.min(),
                "ymax": ys.max(),
                "zmin": zs.min(),
                "zmax": zs.max(),
            })

            coarse_points.extend(pts)

            coarse_cell_array.extend([
                8,
                point_offset + 0,
                point_offset + 1,
                point_offset + 2,
                point_offset + 3,
                point_offset + 4,
                point_offset + 5,
                point_offset + 6,
                point_offset + 7
            ])

            coarse_cell_types.append(pv.CellType.HEXAHEDRON)

            point_offset += 8

        
        

        all_data = sim_data.cell_geometry_with_pressure

        try:
            selected_indices = self._get_layer_row_indices_by_parent_id(
                sim_data=sim_data,
                axis="j",
                layer_index=j_layer,
                cell_data=all_data,
            )
        except ValueError as exc:
            print(exc)
            self._render()
            return

        if selected_indices.size == 0:
            print(f"No leaf cells found for j layer = {j_layer}")
            self._render()
            return

        selected_rows = all_data[selected_indices]

        all_points = []

        cell_corner_ids = []

        for row in selected_rows:

            pts = row[4:28].reshape(8, 3)

            start_idx = len(all_points)

            all_points.extend(pts)

            cell_corner_ids.append(
                list(range(start_idx, start_idx + 8))
            )

        all_points = np.array(all_points)

        points, inverse = np.unique(
            all_points,
            axis=0,
            return_inverse=True
        )

        n_cells = len(cell_corner_ids)

        cell_array = np.empty(n_cells * 9, dtype=np.int64)

        cell_types = np.full(
            n_cells,
            pv.CellType.HEXAHEDRON,
            dtype=np.uint8
        )

        for i in range(n_cells):

            cell_array[i * 9] = 8

            ids = inverse[i * 8:(i + 1) * 8]

            cell_array[
                i * 9 + 1:i * 9 + 9
            ] = ids

        grid = pv.UnstructuredGrid(
            cell_array,
            cell_types,
            points
        )

        pressures = np.asarray(selected_rows[:, 28], dtype=np.float64).copy()

        pressures_all = np.asarray(
            sim_data.cell_geometry_with_pressure[:, 28],
            dtype=np.float64,
        ).copy()

        grid.cell_data["Pressure"] = pressures


        surface = self._build_result_property_shell_surface(grid)
        self._add_layer_pressure_mesh(
            surface,
            pressures_all
        )

        self._replace_layer_grid_with_refined_grid(
            selected_rows=selected_rows,
            cache_key="layer_coarse_grid_actor",
            show_grid=True,
        )

        self._register_result_property_context(
            sim_data=sim_data,
            property_name="Pressure",
            volume_grid=grid,
            actor=self.cache.get("layer_pressure_actor"),
            axis="j",
            layer_index=j_layer,
            title="Pressure",
            unit="bar",
            source_indices=selected_indices,
        )

        
        self._finish_property_switch_render()




    # 水饱和度渲染
    def render_corner_sw_field(self, sim_data):

        if getattr(sim_data, "cell_geometry_with_pressure", None) is None:
            return

        self._remove_actor(self.cache.get("sw_field_actor"))
        self.cache["sw_field_actor"] = None

        if self.cache.get("sw_scalar_bar") is not None:
            try:
                self.plotter.remove_scalar_bar(render=False)
            except Exception:
                pass

            self.cache["sw_scalar_bar"] = None

        try:
            cell_data = sim_data.cell_geometry_with_pressure
            n_cells = cell_data.shape[0]

            if n_cells == 0:
                return

            
            sw = cell_data[:, 33].astype(np.float32)

            valid_sw = sw[np.isfinite(sw)]

            if valid_sw.size == 0:
                print("No valid values for Sw")
                return

            smin = float(np.nanmin(valid_sw))
            smax = float(np.nanmax(valid_sw))

            if smin == smax:
                delta = abs(smin) * 0.01 if smin != 0 else 0.01
                smin -= delta
                smax += delta

            all_points = []
            cells = []
            offset = 0

            for i in range(n_cells):

                pts = cell_data[
                    i,
                    4:28
                ].reshape(
                    8,
                    3
                ).astype(np.float32)

                all_points.append(pts)

                cells.append([
                    8,
                    offset,
                    offset + 1,
                    offset + 2,
                    offset + 3,
                    offset + 4,
                    offset + 5,
                    offset + 6,
                    offset + 7,
                ])

                offset += 8

            points = np.vstack(all_points)
            cells = np.hstack(cells)

            cell_types = np.full(
                n_cells,
                pv.CellType.HEXAHEDRON,
                dtype=np.uint8
            )

            grid = pv.UnstructuredGrid(
                cells,
                cell_types,
                points
            )

            grid.cell_data["Sw"] = sw

            surface = self._build_result_property_shell_surface(grid)


            actor = self.plotter.add_mesh(
                surface,
                scalars="Sw",
                cmap=get_bright_jet_cmap(),
                clim=[smin, smax],
                opacity=RESULT_PROPERTY_OPACITY,
                show_edges=False,
                show_scalar_bar=False,
                lighting=False,
                smooth_shading=False,
                ambient=1.0,
                diffuse=0.0,
                specular=0.0,
                interpolate_before_map=False,
                reset_camera=False,
                render=False,
            )

            scalar_bar = self._replace_scalar_bar(
                "sw_scalar_bar",
                "Sw",
                position_x=0.02,
                position_y=0.55,
                width=0.08,
                height=0.40,
                label_font_size=14,
                title_font_size=16,
                color="#2f3640",
                vertical=True,
                render=False,
            )

            self.cache["sw_field_actor"] = actor
            self.cache["sw_scalar_bar"] = scalar_bar

            self._register_result_property_context(
                sim_data=sim_data,
                property_name="Sw",
                volume_grid=grid,
                actor=actor,
                title="Water Saturation",
            )

            print(
                f"[Sw Field] "
                f"cell_count={n_cells}, "
                f"sw_range=[{smin:.6f}, {smax:.6f}]"
            )

            self._finish_property_switch_render()

        except Exception as exc:
            print("\n")
            print("=" * 60)
            print("ERROR IN render_corner_sw_field")
            print(type(exc).__name__, exc)
            print("=" * 60)
            print("\n")



    
    # 水饱和度 Sw 分层渲染
    

    def render_corner_sw_by_layer(
        self,
        sim_data,
        axis="k",
        layer_index=0,
        opacity=RESULT_PROPERTY_OPACITY,
        show_edges=False,
        show_grid=True,
        show_fractures=True,
        show_wells=True,
    ):

        if not sim_data.corner_point_grid:
            return

        if getattr(sim_data, "cell_geometry_with_pressure", None) is None:
            return

        axis = str(axis).lower().strip()

        if axis not in ("i", "j", "k"):
            print(
                f"Invalid axis = {axis}, "
                "use 'i', 'j', or 'k'"
            )
            return

        cell_data = sim_data.cell_geometry_with_pressure

        if cell_data is None or cell_data.shape[0] == 0:
            return

        
        sw_col = 33

        if cell_data.shape[1] <= sw_col:
            print(
                f"Column index out of range for Sw: "
                f"column={sw_col}, "
                f"data columns={cell_data.shape[1]}"
            )
            return

        self._remove_actor(
            self.cache.get("layer_sw_actor")
        )

        self._remove_actor(
            self.cache.get("layer_sw_coarse_grid_actor")
        )


        self.cache["layer_sw_actor"] = None
        self.cache["layer_sw_coarse_grid_actor"] = None

        if self.cache.get("layer_sw_scalar_bar") is not None:
            try:
                self.plotter.remove_scalar_bar(
                    render=False
                )
            except Exception:
                pass

            self.cache["layer_sw_scalar_bar"] = None

        try:
            
            
            
            cpg = sim_data.corner_point_grid

            nx = int(sim_data.grid_info["nx"])
            ny = int(sim_data.grid_info["ny"])
            nz = int(sim_data.grid_info["nz"])

            if axis == "i":

                if layer_index < 0 or layer_index >= nx:
                    print(
                        f"Invalid i layer = {layer_index}"
                    )
                    return

                coarse_cells = []

                for k in range(nz):
                    for j in range(ny):

                        idx = (
                            layer_index
                            + j * nx
                            + k * nx * ny
                        )

                        if idx < len(cpg.cells):
                            coarse_cells.append(
                                cpg.cells[idx]
                            )

            elif axis == "j":

                if layer_index < 0 or layer_index >= ny:
                    print(
                        f"Invalid j layer = {layer_index}"
                    )
                    return

                coarse_cells = []

                for k in range(nz):
                    for i in range(nx):

                        idx = (
                            i
                            + layer_index * nx
                            + k * nx * ny
                        )

                        if idx < len(cpg.cells):
                            coarse_cells.append(
                                cpg.cells[idx]
                            )

            else:
                if layer_index < 0 or layer_index >= nz:
                    print(
                        f"Invalid k layer = {layer_index}"
                    )
                    return

                start = layer_index * nx * ny
                end = (layer_index + 1) * nx * ny

                coarse_cells = cpg.cells[start:end]

            if not coarse_cells:
                print(
                    f"No coarse cells found for "
                    f"axis={axis}, layer={layer_index}"
                )
                self._render()
                return

            
            
            
            coarse_boxes = []

            coarse_points = []
            coarse_cell_array = []
            coarse_cell_types = []

            point_offset = 0

            for cell in coarse_cells:

                pts = np.asarray(
                    cell.corners,
                    dtype=np.float32,
                )

                if pts.shape != (8, 3):
                    continue

                xs = pts[:, 0]
                ys = pts[:, 1]
                zs = pts[:, 2]

                coarse_boxes.append(
                    {
                        "xmin": float(xs.min()),
                        "xmax": float(xs.max()),
                        "ymin": float(ys.min()),
                        "ymax": float(ys.max()),
                        "zmin": float(zs.min()),
                        "zmax": float(zs.max()),
                    }
                )

                coarse_points.extend(pts)

                coarse_cell_array.extend(
                    [
                        8,
                        point_offset + 0,
                        point_offset + 1,
                        point_offset + 2,
                        point_offset + 3,
                        point_offset + 4,
                        point_offset + 5,
                        point_offset + 6,
                        point_offset + 7,
                    ]
                )

                coarse_cell_types.append(
                    pv.CellType.HEXAHEDRON
                )

                point_offset += 8

            if not coarse_boxes:
                print(
                    f"No valid coarse boxes for "
                    f"axis={axis}, layer={layer_index}"
                )
                self._render()
                return

            
            

            
            
            
            all_points = []

            for row in selected_rows:

                pts = row[4:28].reshape(
                    8,
                    3,
                ).astype(np.float32)

                all_points.extend(pts)

            all_points = np.asarray(
                all_points,
                dtype=np.float32,
            )

            points, inverse = np.unique(
                all_points,
                axis=0,
                return_inverse=True,
            )

            n_cells = len(selected_rows)

            cell_array = np.empty(
                n_cells * 9,
                dtype=np.int64,
            )

            cell_types = np.full(
                n_cells,
                pv.CellType.HEXAHEDRON,
                dtype=np.uint8,
            )

            for i in range(n_cells):

                cell_array[i * 9] = 8

                ids = inverse[
                    i * 8:
                    (i + 1) * 8
                ]

                cell_array[
                    i * 9 + 1:
                    i * 9 + 9
                ] = ids

            grid = pv.UnstructuredGrid(
                cell_array,
                cell_types,
                points,
            )

            selected_sw = selected_rows[
                :,
                sw_col,
            ].astype(np.float32)

            all_sw = cell_data[
                :,
                sw_col,
            ].astype(np.float32)

            grid.cell_data["Sw"] = selected_sw

            surface = self._build_result_property_shell_surface(grid)


            
            
            
            valid_sw = all_sw[
                np.isfinite(all_sw)
            ]

            if valid_sw.size == 0:
                print("No valid values for Sw")
                self._render()
                return

            sw_min = float(
                np.nanmin(valid_sw)
            )

            sw_max = float(
                np.nanmax(valid_sw)
            )

            if sw_min == sw_max:
                delta = (
                    abs(sw_min) * 0.01
                    if sw_min != 0
                    else 0.01
                )

                sw_min -= delta
                sw_max += delta

            
            
            
            sw_actor = self.plotter.add_mesh(
                surface,
                scalars="Sw",
                cmap=get_bright_jet_cmap(),
                clim=[sw_min, sw_max],
                opacity=opacity,
                show_scalar_bar=False,
                show_edges=show_edges,
                edge_color=(0.18, 0.18, 0.18),
                line_width=0.3,
                lighting=False,
                smooth_shading=False,
                ambient=1.0,
                diffuse=0.0,
                specular=0.0,
                interpolate_before_map=False,
                reset_camera=False,
                render=False,
            )

            scalar_bar = self._replace_scalar_bar(
                "layer_sw_scalar_bar",
                "Sw",
                position_x=0.02,
                position_y=0.55,
                width=0.08,
                height=0.40,
                label_font_size=14,
                title_font_size=16,
                color="#2f3640",
                vertical=True,
                render=False,
            )

            self.cache["layer_sw_actor"] = sw_actor
            self.cache["layer_sw_scalar_bar"] = scalar_bar

            self._replace_layer_grid_with_refined_grid(
                selected_rows=selected_rows,
                cache_key="layer_sw_coarse_grid_actor",
                show_grid=show_grid,
            )

            
            
            
            
            
            
            
            
            
            
            
            
            
            selected_parent_ids = np.rint(
                selected_rows[:, 1]
            ).astype(np.int64)

            print(
                "[Sw Layer] "
                f"axis={axis}, "
                f"layer={layer_index}, "
                f"leaf_count={n_cells}, "
                f"unique_parent_count="
                f"{len(np.unique(selected_parent_ids))}, "
                f"coarse_box_count={len(coarse_boxes)}, "
                f"sw_range=[{sw_min:.6f}, {sw_max:.6f}]"
            )

            self._register_result_property_context(
                sim_data=sim_data,
                property_name="Sw",
                volume_grid=grid,
                actor=sw_actor,
                axis=axis,
                layer_index=layer_index,
                title="Water Saturation",
                source_indices=selected_indices,
            )

            self._finish_property_switch_render()

        except Exception as exc:
            print("\n")
            print("=" * 60)
            print("ERROR IN render_corner_sw_by_layer")
            print(type(exc).__name__, exc)
            print("=" * 60)
            print("\n")


    
    
    

    def render_corner_sw_by_layer_i(
        self,
        sim_data,
        i_layer: int,
    ):
        """渲染 I 方向水饱和度 Sw 剖面。"""

        self.render_corner_sw_by_layer(
            sim_data=sim_data,
            axis="i",
            layer_index=i_layer,
        )


    
    
    

    def render_corner_sw_by_layer_j(
        self,
        sim_data,
        j_layer: int,
    ):
        """渲染 J 方向水饱和度 Sw 剖面。"""

        self.render_corner_sw_by_layer(
            sim_data=sim_data,
            axis="j",
            layer_index=j_layer,
        )


    
    
    

    def render_corner_sw_by_layer_k(
        self,
        sim_data,
        k_layer: int,
    ):
        """渲染 K 方向水饱和度 Sw 层面。"""

        self.render_corner_sw_by_layer(
            sim_data=sim_data,
            axis="k",
            layer_index=k_layer,
        )


    # 孔隙度渲染
    def render_corner_phi_field(self, sim_data):

        if getattr(sim_data, "cell_geometry_with_pressure", None) is None:
            return

        self._remove_actor(self.cache.get("phi_field_actor"))
        self.cache["phi_field_actor"] = None

        if self.cache.get("phi_scalar_bar") is not None:
            try:
                self.plotter.remove_scalar_bar(render=False)
            except Exception:
                pass
            self.cache["phi_scalar_bar"] = None

        try:
            cell_data = sim_data.cell_geometry_with_pressure
            n_cells = cell_data.shape[0]

            if n_cells == 0:
                return

            
            phi = cell_data[:, 32].astype(np.float32)

            pmin = float(np.nanmin(phi))
            pmax = float(np.nanmax(phi))

            all_points = []
            cells = []
            offset = 0

            for i in range(n_cells):

                pts = cell_data[i, 4:28].reshape(8, 3).astype(np.float32)
                all_points.append(pts)

                cells.append([
                    8,
                    offset, offset + 1, offset + 2, offset + 3,
                    offset + 4, offset + 5, offset + 6, offset + 7
                ])
                offset += 8

            points = np.vstack(all_points)
            cells = np.hstack(cells)

            cell_types = np.full(
                n_cells,
                pv.CellType.HEXAHEDRON,
                dtype=np.uint8
            )

            grid = pv.UnstructuredGrid(cells, cell_types, points)

            grid.cell_data["Phi"] = phi

            surface = self._build_result_property_shell_surface(grid)


            actor = self.plotter.add_mesh(
                surface,
                scalars="Phi",
                cmap=get_bright_jet_cmap(),
                clim=[pmin, pmax],
                opacity=RESULT_PROPERTY_OPACITY,
                show_edges=False,
                show_scalar_bar=False,
                lighting=False,
                smooth_shading=False,
                ambient=1.0,
                diffuse=0.0,
                specular=0.0,
                interpolate_before_map=False,
                reset_camera=False,
                render=False,
            )

            scalar_bar = self._replace_scalar_bar(
                "phi_scalar_bar",
                "Phi",
                position_x=0.02,
                position_y=0.55,
                width=0.08,
                height=0.40,
                label_font_size=14,
                title_font_size=16,
                color="#2f3640",
                vertical=True,
                render=False,
            )

            self.cache["phi_field_actor"] = actor
            self.cache["phi_scalar_bar"] = scalar_bar

            self._register_result_property_context(
                sim_data=sim_data,
                property_name="Phi",
                volume_grid=grid,
                actor=actor,
                title="Porosity",
            )

            self._finish_property_switch_render()

        except Exception as exc:
            print("\n")
            print("=" * 60)
            print("ERROR IN render_corner_phi_field")
            print(exc)
            print("=" * 60)
            print("\n")


    #孔隙度分层渲染
    def render_corner_phi_by_layer(
        self,
        sim_data,
        axis="k",
        layer_index=0,
        opacity=RESULT_PROPERTY_OPACITY,
        show_edges=False,
        show_grid=True,
        show_fractures=True,
        show_wells=True
    ):

        if not sim_data.corner_point_grid:
            return

        if getattr(sim_data, "cell_geometry_with_pressure", None) is None:
            return

        axis = str(axis).lower()

        if axis not in ("i", "j", "k"):
            print(f"Invalid axis = {axis}, use 'i', 'j', or 'k'")
            return

        cell_data = sim_data.cell_geometry_with_pressure

        if cell_data is None or cell_data.shape[0] == 0:
            return

        phi_col = 32

        if cell_data.shape[1] <= phi_col:
            print(
                f"Column index out of range for Phi: "
                f"column={phi_col}, data columns={cell_data.shape[1]}"
            )
            return

        
        
        
        self._remove_actor(self.cache.get("layer_phi_actor"))
        self._remove_actor(self.cache.get("layer_phi_coarse_grid_actor"))


        self.cache["layer_phi_actor"] = None
        self.cache["layer_phi_coarse_grid_actor"] = None

        if self.cache.get("layer_phi_scalar_bar") is not None:
            try:
                self.plotter.remove_scalar_bar(render=False)
            except Exception:
                pass
            self.cache["layer_phi_scalar_bar"] = None

        try:
            
            
            
            cpg = sim_data.corner_point_grid

            nx = int(sim_data.grid_info["nx"])
            ny = int(sim_data.grid_info["ny"])
            nz = int(sim_data.grid_info["nz"])

            if axis == "i":
                if layer_index < 0 or layer_index >= nx:
                    print(f"Invalid i layer = {layer_index}")
                    return

                coarse_cells = []

                for k in range(nz):
                    for j in range(ny):
                        idx = layer_index + j * nx + k * nx * ny

                        if idx < len(cpg.cells):
                            coarse_cells.append(cpg.cells[idx])

            elif axis == "j":
                if layer_index < 0 or layer_index >= ny:
                    print(f"Invalid j layer = {layer_index}")
                    return

                coarse_cells = []

                for k in range(nz):
                    for i in range(nx):
                        idx = i + layer_index * nx + k * nx * ny

                        if idx < len(cpg.cells):
                            coarse_cells.append(cpg.cells[idx])

            else:
                if layer_index < 0 or layer_index >= nz:
                    print(f"Invalid k layer = {layer_index}")
                    return

                start = layer_index * nx * ny
                end = (layer_index + 1) * nx * ny
                coarse_cells = cpg.cells[start:end]

            if not coarse_cells:
                print(f"No coarse cells found for axis={axis}, layer={layer_index}")
                self._render()
                return

            
            
            
            coarse_boxes = []

            coarse_points = []
            coarse_cell_array = []
            coarse_cell_types = []
            point_offset = 0

            for cell in coarse_cells:

                pts = np.array(cell.corners, dtype=np.float32)

                if pts.shape != (8, 3):
                    continue

                xs = pts[:, 0]
                ys = pts[:, 1]
                zs = pts[:, 2]

                coarse_boxes.append({
                    "xmin": float(xs.min()),
                    "xmax": float(xs.max()),
                    "ymin": float(ys.min()),
                    "ymax": float(ys.max()),
                    "zmin": float(zs.min()),
                    "zmax": float(zs.max()),
                })

                coarse_points.extend(pts)

                coarse_cell_array.extend([
                    8,
                    point_offset + 0,
                    point_offset + 1,
                    point_offset + 2,
                    point_offset + 3,
                    point_offset + 4,
                    point_offset + 5,
                    point_offset + 6,
                    point_offset + 7,
                ])

                coarse_cell_types.append(pv.CellType.HEXAHEDRON)
                point_offset += 8

            if not coarse_boxes:
                print(f"No valid coarse boxes for axis={axis}, layer={layer_index}")
                self._render()
                return

            
            

            
            
            
            all_points = []
            cell_corner_ids = []

            for row in selected_rows:
                pts = row[4:28].reshape(8, 3).astype(np.float32)
                start_idx = len(all_points)
                all_points.extend(pts)
                cell_corner_ids.append(list(range(start_idx, start_idx + 8)))

            all_points = np.array(all_points, dtype=np.float32)

            points, inverse = np.unique(
                all_points,
                axis=0,
                return_inverse=True
            )

            n_cells = len(cell_corner_ids)

            cell_array = np.empty(n_cells * 9, dtype=np.int64)
            cell_types = np.full(
                n_cells,
                pv.CellType.HEXAHEDRON,
                dtype=np.uint8
            )

            for i in range(n_cells):
                cell_array[i * 9] = 8
                ids = inverse[i * 8:(i + 1) * 8]
                cell_array[i * 9 + 1:i * 9 + 9] = ids

            grid = pv.UnstructuredGrid(
                cell_array,
                cell_types,
                points
            )

            selected_phi = selected_rows[:, phi_col].astype(np.float32)
            all_phi = cell_data[:, phi_col].astype(np.float32)

            grid.cell_data["Phi"] = selected_phi

            surface = self._build_result_property_shell_surface(grid)


            valid_values = all_phi[np.isfinite(all_phi)]

            if valid_values.size == 0:
                print("No valid values for Phi")
                self._render()
                return

            phimin = float(np.nanmin(valid_values))
            phimax = float(np.nanmax(valid_values))

            if phimin == phimax:
                delta = abs(phimin) * 0.01 if phimin != 0 else 1.0
                phimin -= delta
                phimax += delta

            
            
            
            
            actor = self.plotter.add_mesh(
                surface,
                scalars="Phi",
                cmap=get_bright_jet_cmap(),
                clim=[phimin, phimax],
                opacity=opacity,
                show_scalar_bar=False,
                show_edges=show_edges,
                edge_color=(0.18, 0.18, 0.18),
                line_width=0.3,
                lighting=False,
                smooth_shading=False,
                ambient=1.0,
                diffuse=0.0,
                specular=0.0,
                interpolate_before_map=False,
                reset_camera=False,
                render=False,
            )

            scalar_bar = self._replace_scalar_bar(
                "layer_phi_scalar_bar",
                "Phi",
                position_x=0.02,
                position_y=0.55,
                width=0.08,
                height=0.40,
                label_font_size=14,
                title_font_size=16,
                color="#2f3640",
                vertical=True,
                render=False,
            )

            self.cache["layer_phi_actor"] = actor
            self.cache["layer_phi_scalar_bar"] = scalar_bar

            self._replace_layer_grid_with_refined_grid(
                selected_rows=selected_rows,
                cache_key="layer_phi_coarse_grid_actor",
                show_grid=show_grid,
            )
            self._register_result_property_context(
                sim_data=sim_data,
                property_name="Phi",
                volume_grid=grid,
                actor=actor,
                axis=axis,
                layer_index=layer_index,
                title="Porosity",
                source_indices=selected_indices,
            )

            
            self._finish_property_switch_render()

        except Exception as exc:
            print("\n")
            print("=" * 60)
            print("ERROR IN render_corner_phi_by_layer")
            print(exc)
            print("=" * 60)
            print("\n")

    def render_corner_phi_by_layer_i(self, sim_data, i_layer: int):
        """渲染 I 方向孔隙度 Phi 剖面。"""
        self.render_corner_phi_by_layer(
            sim_data,
            axis="i",
            layer_index=i_layer
        )


    def render_corner_phi_by_layer_j(self, sim_data, j_layer: int):
        """渲染 J 方向孔隙度 Phi 剖面。"""
        self.render_corner_phi_by_layer(
            sim_data,
            axis="j",
            layer_index=j_layer
        )


    def render_corner_phi_by_layer_k(self, sim_data, k_layer: int):
        """渲染 K 方向孔隙度 Phi 层面。"""
        self.render_corner_phi_by_layer(
            sim_data,
            axis="k",
            layer_index=k_layer
        )

    
    
    

    def render_threshold_property_field(
        self,
        sim_data=None,
        property_name=None,
        min_value=None,
        max_value=None,
        opacity=RESULT_PROPERTY_OPACITY,
        show_edges=False,
    ):
        """
        对当前显示属性执行阈值过滤。

        当前属性可以来自静态预览，也可以来自模拟结果；旧 UI 继续传
        sim_data/property_name 也兼容，但只要画面已有属性场，就始终以
        当前属性上下文为准。
        """
        current = self._resolve_property_operation_context(
            sim_data=sim_data,
            property_name=property_name,
        )

        
        source_context = self.cache.get("threshold_source_context")
        if not isinstance(source_context, dict):
            source_context = current

        if not isinstance(source_context, dict):
            print("[Threshold] No active property field.")
            return None

        source_grid, scalar_name, values = self._context_cell_scalar_values(
            source_context
        )

        if (
            not self._dataset_has_cells(source_grid)
            or scalar_name is None
            or values is None
        ):
            print("[Threshold] Active property has no cell scalar data.")
            return None

        mask = np.isfinite(values)

        if min_value is not None:
            mask &= values >= float(min_value)

        if max_value is not None:
            mask &= values <= float(max_value)

        selected_ids = np.flatnonzero(mask).astype(np.int64)

        if selected_ids.size == 0:
            print(
                f"[Threshold] No cells found: "
                f"property={source_context.get('property_name')}, "
                f"min={min_value}, max={max_value}"
            )
            return None

        
        self._remove_actor(self.cache.get("threshold_actor"))
        self._remove_actor(self.cache.get("threshold_grid_actor"))
        self.cache["threshold_actor"] = None
        self.cache["threshold_grid_actor"] = None

        old_bar_title = self.cache.get("threshold_scalar_bar_title")
        if old_bar_title:
            try:
                self.plotter.remove_scalar_bar(
                    title=old_bar_title,
                    render=False,
                )
            except Exception:
                pass

        old_bar = self.cache.get("threshold_scalar_bar")
        if old_bar is not None:
            self._set_scene_actor_visibility(old_bar, False)

        self.cache["threshold_scalar_bar"] = None
        self.cache["threshold_scalar_bar_title"] = None

        try:
            filtered_grid = source_grid.extract_cells(selected_ids)
        except Exception as exc:
            print("[Threshold] extract_cells failed:", exc)
            return None

        if not self._dataset_has_cells(filtered_grid):
            return None

        
        try:
            if scalar_name not in filtered_grid.cell_data:
                filtered_grid.cell_data[scalar_name] = values[selected_ids]
        except Exception:
            pass

        try:
            surface = self._build_result_property_shell_surface(filtered_grid)
        except Exception:
            surface = filtered_grid.extract_surface()

        if scalar_name == "Pressure":
            try:
                surface = self._prepare_exact_cell_scalar_surface(
                    surface,
                    scalar_name,
                )
            except Exception:
                pass

        finite_values = values[np.isfinite(values)]
        if finite_values.size == 0:
            return None

        value_min = float(np.min(finite_values))
        value_max = float(np.max(finite_values))

        if np.isclose(value_min, value_max, rtol=1e-6, atol=1e-8):
            center = float(np.mean(finite_values))
            delta = max(abs(center) * 0.01, 0.001)
            value_min = center - delta
            value_max = center + delta

        
        if self.cache.get("threshold_source_context") is None:
            source_actors = [source_context.get("actor")]
            source_actors.extend(
                self._active_property_scalar_bar_actors(source_context)
            )
            self.cache["threshold_source_actor_states"] = (
                self._capture_actor_visibility_states(source_actors)
            )
            self.cache["threshold_source_context"] = source_context

        for state in self.cache.get("threshold_source_actor_states", []) or []:
            self._set_scene_actor_visibility(state.get("actor"), False)

        title = str(
            source_context.get(
                "title",
                source_context.get("property_name", scalar_name),
            )
        )
        unit = str(source_context.get("unit", "") or "")
        bar_title = f"Threshold: {title}"
        if unit and unit not in bar_title:
            bar_title += f" ({unit})"

        threshold_actor = self.plotter.add_mesh(
            surface,
            scalars=scalar_name,
            preference="cell",
            cmap=get_bright_jet_cmap(),
            clim=[value_min, value_max],
            opacity=float(opacity),
            show_edges=bool(show_edges),
            edge_color=(0.18, 0.18, 0.18),
            line_width=0.3,
            show_scalar_bar=False,
            lighting=False,
            smooth_shading=False,
            ambient=1.0,
            diffuse=0.0,
            specular=0.0,
            interpolate_before_map=False,
            reset_camera=False,
            render=False,
        )

        if scalar_name == "Pressure":
            try:
                self._configure_exact_cell_scalar_actor(threshold_actor)
            except Exception:
                pass

        scalar_bar = None
        try:
            scalar_bar = self.plotter.add_scalar_bar(
                title=bar_title,
                mapper=getattr(threshold_actor, "mapper", None),
                position_x=0.02,
                position_y=0.55,
                width=0.08,
                height=0.40,
                label_font_size=14,
                title_font_size=16,
                color="#2f3640",
                vertical=True,
                render=False,
            )
        except TypeError:
            scalar_bar = self.plotter.add_scalar_bar(
                title=bar_title,
                position_x=0.02,
                position_y=0.55,
                width=0.08,
                height=0.40,
                label_font_size=14,
                title_font_size=16,
                color="#2f3640",
                vertical=True,
                render=False,
            )
        except Exception:
            scalar_bar = None

        threshold_grid_visible = bool(
            self.cache.get("threshold_grid_visible", True)
        )
        threshold_grid_actor = None

        try:
            threshold_edges = filtered_grid.extract_all_edges()
            if threshold_edges.n_points > 0:
                threshold_grid_actor = self.plotter.add_mesh(
                    threshold_edges,
                    color=(0.5, 0.5, 0.5),
                    line_width=1.0,
                    opacity=1.0,
                    lighting=False,
                    render_lines_as_tubes=False,
                    show_scalar_bar=False,
                    pickable=False,
                    reset_camera=False,
                    render=False,
                )
                self._set_scene_actor_visibility(
                    threshold_grid_actor,
                    threshold_grid_visible,
                )
        except Exception:
            threshold_grid_actor = None

        self.cache["threshold_actor"] = threshold_actor
        self.cache["threshold_scalar_bar"] = scalar_bar
        self.cache["threshold_scalar_bar_title"] = bar_title
        self.cache["threshold_grid_actor"] = threshold_grid_actor
        self.cache["threshold_grid_visible"] = threshold_grid_visible

        metadata = dict(source_context.get("metadata", {}) or {})
        metadata.update({
            "operation": "threshold",
            "threshold_min": min_value,
            "threshold_max": max_value,
            "source_context": source_context,
        })

        self.set_active_property_context(
            source_mode=source_context.get("source_mode", "preview"),
            sim_data=source_context.get("sim_data", sim_data),
            property_name=source_context.get("property_name", scalar_name),
            scalar_name=scalar_name,
            volume_grid=filtered_grid,
            actor=threshold_actor,
            axis=source_context.get("axis"),
            layer_index=source_context.get("layer_index"),
            title=title,
            unit=unit,
            metadata=metadata,
        )

        print(
            f"[Threshold] source={source_context.get('source_mode')}, "
            f"property={source_context.get('property_name')}, "
            f"selected={selected_ids.size}/{values.size}"
        )

        self._render()
        return threshold_actor

    
    
    
    def set_threshold_grid_visibility(
        self,
        visible: bool,
    ):
        """
        控制阈值筛选后的网格线显示或隐藏。

        visible=True：
            显示筛选后的网格线。

        visible=False：
            隐藏筛选后的网格线。
        """

        visible = bool(visible)

        self.cache["threshold_grid_visible"] = visible

        threshold_grid_actor = self.cache.get(
            "threshold_grid_actor"
        )

        if threshold_grid_actor is None:
            self._render()
            return

        try:
            threshold_grid_actor.visibility = visible
        except Exception:
            try:
                threshold_grid_actor.SetVisibility(
                    visible
                )
            except Exception:
                pass

        self._render()


    
    
    


    def hide_threshold_property_field(self):
        """清除阈值结果并恢复进入阈值前的预览/模拟属性场。"""
        self._remove_actor(self.cache.get("threshold_actor"))
        self._remove_actor(self.cache.get("threshold_grid_actor"))
        self.cache["threshold_actor"] = None
        self.cache["threshold_grid_actor"] = None
        self.cache["threshold_grid_visible"] = True

        title = self.cache.get("threshold_scalar_bar_title")
        if title:
            try:
                self.plotter.remove_scalar_bar(
                    title=title,
                    render=False,
                )
            except Exception:
                pass

        scalar_bar = self.cache.get("threshold_scalar_bar")
        if scalar_bar is not None:
            self._set_scene_actor_visibility(scalar_bar, False)

        self.cache["threshold_scalar_bar"] = None
        self.cache["threshold_scalar_bar_title"] = None

        source_context = self.cache.get("threshold_source_context")
        source_states = self.cache.get(
            "threshold_source_actor_states",
            [],
        )

        self._restore_actor_visibility_states(source_states)

        self.cache["threshold_source_context"] = None
        self.cache["threshold_source_actor_states"] = []

        if isinstance(source_context, dict) and self._dataset_has_cells(
            source_context.get("volume_grid")
        ):
            self.set_active_property_context(
                source_mode=source_context.get("source_mode", "preview"),
                sim_data=source_context.get("sim_data"),
                property_name=source_context.get("property_name", "Property"),
                scalar_name=source_context.get("scalar_name", "Property"),
                volume_grid=source_context.get("volume_grid"),
                actor=source_context.get("actor"),
                axis=source_context.get("axis"),
                layer_index=source_context.get("layer_index"),
                title=source_context.get("title"),
                unit=source_context.get("unit", ""),
                metadata=source_context.get("metadata", {}),
            )
        else:
            self.clear_active_property_context(refresh_picking=True)

        self._render()
        return True

    def _get_current_model_bounds(self):
        """
        获取当前模型的空间范围。
        优先使用当前 plotter bounds。
        """
        try:
            bounds = self.plotter.bounds
            if bounds is not None and len(bounds) == 6:
                xmin, xmax, ymin, ymax, zmin, zmax = bounds
                if xmax > xmin and ymax > ymin and zmax >= zmin:
                    return (
                        float(xmin), float(xmax),
                        float(ymin), float(ymax),
                        float(zmin), float(zmax)
                    )
        except Exception:
            pass

        return None


    
    def _get_native_interactor(self):
        """获取底层 VTK RenderWindowInteractor。"""
        try:
            iren = getattr(self.plotter, "iren", None)
            native = getattr(iren, "interactor", None)
            if native is not None:
                return native
        except Exception:
            pass

        try:
            iren = getattr(self.vtk_widget, "iren", None)
            native = getattr(iren, "interactor", None)
            if native is not None:
                return native
        except Exception:
            pass

        
        for owner in (self.plotter, self.vtk_widget):
            try:
                candidate = getattr(owner, "iren", None)
                if candidate is not None and hasattr(candidate, "AddObserver"):
                    return candidate
            except Exception:
                pass

        return None


    def _ensure_six_view_rotation_observers(self):

        if self._six_view_rotation_observer_ids:
            return True

        interactor = self._get_native_interactor()
        if interactor is None:
            print("Six-view observer setup failed: interactor unavailable")
            return False

        observer_ids = []

        try:
            press_id = interactor.AddObserver(
                "LeftButtonPressEvent",
                self._on_six_view_left_button_press,
                1.0,
            )
            move_id = interactor.AddObserver(
                "MouseMoveEvent",
                self._on_six_view_mouse_move,
                1.0,
            )
            release_id = interactor.AddObserver(
                "LeftButtonReleaseEvent",
                self._on_six_view_left_button_release,
                1.0,
            )

            observer_ids = [press_id, move_id, release_id]

        except TypeError:
            press_id = interactor.AddObserver(
                "LeftButtonPressEvent",
                self._on_six_view_left_button_press,
            )
            move_id = interactor.AddObserver(
                "MouseMoveEvent",
                self._on_six_view_mouse_move,
            )
            release_id = interactor.AddObserver(
                "LeftButtonReleaseEvent",
                self._on_six_view_left_button_release,
            )

            observer_ids = [press_id, move_id, release_id]

        except Exception as exc:
            print("Six-view observer setup failed:", exc)
            return False

        self._six_view_rotation_interactor = interactor
        self._six_view_rotation_observer_ids = observer_ids
        return True


    def _on_six_view_left_button_press(self, obj, event):

        if not self._six_view_projection_active:
            return

        if bool(getattr(self, "camera_direction_locked", False)):
            return

        try:
            x, y = obj.GetEventPosition()
            self._six_view_press_position = (int(x), int(y))
            self._six_view_left_button_down = True
        except Exception:
            self._six_view_press_position = None
            self._six_view_left_button_down = True

        self._restore_perspective_for_free_rotation()

        self._six_view_projection_active = False


    def _on_six_view_mouse_move(self, obj, event):
        """
        兼容保留的移动监听。

        正常情况下投影已经在 LeftButtonPressEvent 中切换完成；
        此处不再等待移动距离，也不在松开鼠标时切换。
        """
        return


    def _on_six_view_left_button_release(self, obj, event):
        self._six_view_left_button_down = False
        self._six_view_press_position = None


    def _get_current_camera_visible_half_height(self):

        cam = self.plotter.camera

        try:
            if bool(getattr(cam, "parallel_projection", False)):
                scale = float(getattr(cam, "parallel_scale", 1.0))
                if np.isfinite(scale) and scale > 1e-12:
                    return scale

            position, focal_point, _ = self.plotter.camera_position
            position = np.asarray(position, dtype=np.float64)
            focal_point = np.asarray(focal_point, dtype=np.float64)

            distance = float(np.linalg.norm(position - focal_point))
            if not np.isfinite(distance) or distance <= 1e-12:
                return None

            view_angle = float(getattr(cam, "view_angle", 30.0))
            view_angle = min(max(view_angle, 1.0), 170.0)

            half_height = distance * float(
                np.tan(np.deg2rad(view_angle * 0.5))
            )

            if np.isfinite(half_height) and half_height > 1e-12:
                return half_height

        except Exception:
            pass

        return None


    @staticmethod
    def _camera_bounds_corners(bounds):

        if bounds is None or len(bounds) != 6:
            return None

        try:
            xmin, xmax, ymin, ymax, zmin, zmax = [
                float(value)
                for value in bounds
            ]
        except Exception:
            return None

        corners = np.asarray(
            [
                (xmin, ymin, zmin),
                (xmin, ymin, zmax),
                (xmin, ymax, zmin),
                (xmin, ymax, zmax),
                (xmax, ymin, zmin),
                (xmax, ymin, zmax),
                (xmax, ymax, zmin),
                (xmax, ymax, zmax),
            ],
            dtype=np.float64,
        )

        if not np.isfinite(corners).all():
            return None

        return corners


    def _get_safe_camera_distance_for_rotation(
        self,
        focal_point,
        requested_distance,
        bounds=None,
    ):

        focal_point = np.asarray(
            focal_point,
            dtype=np.float64,
        )

        requested_distance = max(
            float(requested_distance),
            1e-6,
        )

        if bounds is None:
            bounds = self._get_current_model_bounds()

        corners = self._camera_bounds_corners(bounds)

        if corners is None:
            return requested_distance

        try:
            radius = float(
                np.max(
                    np.linalg.norm(
                        corners - focal_point,
                        axis=1,
                    )
                )
            )
        except Exception:
            return requested_distance

        if not np.isfinite(radius) or radius <= 1e-12:
            return requested_distance

        clearance = max(
            radius * 0.12,
            1.0,
        )

        return max(
            requested_distance,
            radius + clearance,
        )


    def _set_safe_camera_clipping_range(
        self,
        bounds=None,
        focal_point=None,
    ):

        try:
            cam = self.plotter.camera
            position, current_focal, _ = self.plotter.camera_position

            position = np.asarray(
                position,
                dtype=np.float64,
            )

            if focal_point is None:
                focal_point = current_focal

            focal_point = np.asarray(
                focal_point,
                dtype=np.float64,
            )

            distance = float(
                np.linalg.norm(
                    position - focal_point
                )
            )

            if not np.isfinite(distance) or distance <= 1e-12:
                return False

            if bounds is None:
                bounds = self._get_current_model_bounds()

            corners = self._camera_bounds_corners(bounds)

            if corners is None:
                self.plotter.reset_camera_clipping_range()
                return True

            radius = float(
                np.max(
                    np.linalg.norm(
                        corners - focal_point,
                        axis=1,
                    )
                )
            )

            if not np.isfinite(radius) or radius <= 1e-12:
                self.plotter.reset_camera_clipping_range()
                return True

            padding = max(
                radius * 0.08,
                1.0,
            )

            near_value = distance - radius - padding
            far_value = distance + radius + padding

            
            minimum_near = max(
                far_value * 1e-6,
                1e-3,
            )

            near_value = max(
                near_value,
                minimum_near,
            )

            far_value = max(
                far_value,
                near_value + 1.0,
            )

            cam.clipping_range = (
                float(near_value),
                float(far_value),
            )

            return True

        except Exception:
            try:
                self.plotter.reset_camera_clipping_range()
                return True
            except Exception:
                return False


    def _restore_perspective_for_free_rotation(self):

        cam = self.plotter.camera

        if not bool(getattr(cam, "parallel_projection", False)):
            return False

        try:
            position, focal_point, view_up = self.plotter.camera_position

            position = np.asarray(position, dtype=np.float64)
            focal_point = np.asarray(focal_point, dtype=np.float64)
            view_up = np.asarray(view_up, dtype=np.float64)

            backward = position - focal_point
            old_distance = float(np.linalg.norm(backward))

            if old_distance <= 1e-12:
                backward = np.array([0.0, -1.0, 0.0], dtype=np.float64)
            else:
                backward = backward / old_distance

            parallel_scale = max(
                float(getattr(cam, "parallel_scale", 1.0)),
                1e-6,
            )

            view_angle = float(getattr(cam, "view_angle", 30.0))
            view_angle = min(max(view_angle, 1.0), 170.0)

            half_angle = np.deg2rad(view_angle * 0.5)
            tangent = max(float(np.tan(half_angle)), 1e-6)

            requested_distance = parallel_scale / tangent

            bounds = self._get_current_model_bounds()

            new_distance = self._get_safe_camera_distance_for_rotation(
                focal_point=focal_point,
                requested_distance=requested_distance,
                bounds=bounds,
            )

            matched_half_angle = float(
                np.arctan(
                    parallel_scale / max(new_distance, 1e-6)
                )
            )

            matched_view_angle = float(
                np.rad2deg(
                    matched_half_angle * 2.0
                )
            )

            matched_view_angle = min(
                max(matched_view_angle, 0.1),
                170.0,
            )

            new_position = focal_point + backward * new_distance

            cam.parallel_projection = False
            cam.view_angle = matched_view_angle

            self.plotter.camera_position = (
                tuple(float(v) for v in new_position),
                tuple(float(v) for v in focal_point),
                tuple(float(v) for v in view_up),
            )

            self._set_safe_camera_clipping_range(
                bounds=bounds,
                focal_point=focal_point,
            )

            if self.cache.get(
                "camera_aware_coordinate_enabled",
                False,
            ):
                self._update_camera_aware_coordinate_axes()

            self._render()
            return True

        except Exception as exc:
            print("Restore perspective for free rotation failed:", exc)
            return False


    def set_camera_by_direction(self, direction="front"):
        """
        设置标准六向视图。

        direction:
            "front"   前视图：从 -Y 看向模型
            "back"    后视图：从 +Y 看向模型
            "left"    左视图：从 -X 看向模型
            "right"   右视图：从 +X 看向模型
            "top"     俯视图：从 +Z 看向模型
            "bottom"  仰视图：从 -Z 看向模型
        """

        bounds = self._get_current_model_bounds()

        if bounds is None:
            print("No valid model bounds for camera view")
            return

        xmin, xmax, ymin, ymax, zmin, zmax = bounds

        cx = (xmin + xmax) * 0.5
        cy = (ymin + ymax) * 0.5
        cz = (zmin + zmax) * 0.5

        dx = xmax - xmin
        dy = ymax - ymin
        dz = zmax - zmin

        span = max(dx, dy, dz, 1.0)
        dist = span * 2.5

        current_visible_half_height = (
            self._get_current_camera_visible_half_height()
        )

        if current_visible_half_height is None:

            current_visible_half_height = max(span * 0.5, 1.0)

        direction = str(direction).lower()

        if direction == "front":
            
            camera_position = (
                (cx, cy - dist, cz),
                (cx, cy, cz),
                (0.0, 0.0, 1.0)
            )

        elif direction == "back":
            
            camera_position = (
                (cx, cy + dist, cz),
                (cx, cy, cz),
                (0.0, 0.0, 1.0)
            )

        elif direction == "left":
            
            camera_position = (
                (cx - dist, cy, cz),
                (cx, cy, cz),
                (0.0, 0.0, 1.0)
            )

        elif direction == "right":
            
            camera_position = (
                (cx + dist, cy, cz),
                (cx, cy, cz),
                (0.0, 0.0, 1.0)
            )

        elif direction == "top":
            
            camera_position = (
                (cx, cy, cz + dist),
                (cx, cy, cz),
                (0.0, 1.0, 0.0)
            )

        elif direction == "bottom":
            
            camera_position = (
                (cx, cy, cz - dist),
                (cx, cy, cz),
                (0.0, 1.0, 0.0)
            )

        else:
            print(f"Unknown camera direction: {direction}")
            return

        cam = self.plotter.camera
        cam.parallel_projection = True
        cam.parallel_scale = float(current_visible_half_height)

        self.plotter.camera_position = camera_position

        self._set_safe_camera_clipping_range(
            bounds=bounds,
            focal_point=(cx, cy, cz),
        )

        self._six_view_projection_active = True
        self._six_view_left_button_down = False
        self._six_view_press_position = None
        self._ensure_six_view_rotation_observers()

        if self.cache.get(
            "camera_aware_coordinate_enabled",
            False,
        ):
            self._update_camera_aware_coordinate_axes()

        self._render()


    def view_front(self):
        """前视图"""
        self.set_camera_by_direction("front")


    def view_back(self):
        """后视图"""
        self.set_camera_by_direction("back")


    def view_left(self):
        """左视图"""
        self.set_camera_by_direction("left")


    def view_right(self):
        """右视图"""
        self.set_camera_by_direction("right")


    def view_top(self):
        """俯视图"""
        self.set_camera_by_direction("top")


    def view_bottom(self):
        """仰视图"""
        self.set_camera_by_direction("bottom")


    # 渗透率场渲染：Kx / Ky / Kz
    def render_corner_permeability_field(self, sim_data, direction="x"):

        if getattr(sim_data, "cell_geometry_with_pressure", None) is None:
            return

        direction = str(direction).lower()

        perm_config = {
            "x": {
                "column": 29,
                "name": "Kx",
                "title": "Permeability X",
            },
            "kx": {
                "column": 29,
                "name": "Kx",
                "title": "Permeability X",
            },
            "y": {
                "column": 30,
                "name": "Ky",
                "title": "Permeability Y",
            },
            "ky": {
                "column": 30,
                "name": "Ky",
                "title": "Permeability Y",
            },
            "z": {
                "column": 31,
                "name": "Kz",
                "title": "Permeability Z",
            },
            "kz": {
                "column": 31,
                "name": "Kz",
                "title": "Permeability Z",
            },
        }

        if direction not in perm_config:
            print(f"Invalid permeability direction: {direction}")
            print("Use direction='x', 'y', or 'z'")
            return

        config = perm_config[direction]
        col = config["column"]
        prop_name = config["name"]
        title = config["title"]

        
        
        
        self._remove_actor(self.cache.get("perm_field_actor"))
        self.cache["perm_field_actor"] = None

        if self.cache.get("perm_scalar_bar") is not None:
            try:
                self.plotter.remove_scalar_bar(render=False)
            except Exception:
                pass
            self.cache["perm_scalar_bar"] = None

        try:
            cell_data = sim_data.cell_geometry_with_pressure
            n_cells = cell_data.shape[0]

            if n_cells == 0:
                return

            if cell_data.shape[1] <= col:
                print(
                    f"Column index out of range for {prop_name}: "
                    f"column={col}, data columns={cell_data.shape[1]}"
                )
                return

            
            
            
            perm_values = cell_data[:, col].astype(np.float32)

            valid_values = perm_values[np.isfinite(perm_values)]
            if valid_values.size == 0:
                print(f"No valid permeability values for {prop_name}")
                return

            kmin = float(np.nanmin(valid_values))
            kmax = float(np.nanmax(valid_values))

            if kmin == kmax:
                delta = abs(kmin) * 0.01 if kmin != 0 else 1.0
                kmin -= delta
                kmax += delta

            
            
            
            all_points = []
            cells = []
            offset = 0

            for i in range(n_cells):

                pts = cell_data[i, 4:28].reshape(8, 3).astype(np.float32)
                all_points.append(pts)

                cells.append([
                    8,
                    offset, offset + 1, offset + 2, offset + 3,
                    offset + 4, offset + 5, offset + 6, offset + 7
                ])
                offset += 8

            points = np.vstack(all_points)
            cells = np.hstack(cells)

            cell_types = np.full(
                n_cells,
                pv.CellType.HEXAHEDRON,
                dtype=np.uint8
            )

            grid = pv.UnstructuredGrid(cells, cell_types, points)
            grid.cell_data[prop_name] = perm_values

            surface = self._build_result_property_shell_surface(grid)


            
            
            
            actor = self.plotter.add_mesh(
                surface,
                scalars=prop_name,
                cmap=get_bright_jet_cmap(),
                clim=[kmin, kmax],
                opacity=RESULT_PROPERTY_OPACITY,
                show_edges=False,
                show_scalar_bar=False,
                lighting=False,
                smooth_shading=False,
                ambient=1.0,
                diffuse=0.0,
                specular=0.0,
                interpolate_before_map=False,
                reset_camera=False,
                render=False,
            )

            scalar_bar = self._replace_scalar_bar(
                "perm_scalar_bar",
                title,
                position_x=0.02,
                position_y=0.55,
                width=0.08,
                height=0.40,
                label_font_size=14,
                title_font_size=16,
                color="#2f3640",
                vertical=True,
                render=False,
            )

            self.cache["perm_field_actor"] = actor
            self.cache["perm_scalar_bar"] = scalar_bar

            self._register_result_property_context(
                sim_data=sim_data,
                property_name=prop_name,
                volume_grid=grid,
                actor=actor,
                title=title,
            )

            
            
            

            self._finish_property_switch_render()

        except Exception as exc:
            print("\n")
            print("=" * 60)
            print("ERROR IN render_corner_permeability_field")
            print(exc)
            print("=" * 60)
            print("\n")

    def render_corner_kx_field(self, sim_data):
        """渲染 X 方向渗透率 Kx。"""
        self.render_corner_permeability_field(sim_data, direction="x")


    def render_corner_ky_field(self, sim_data):
        """渲染 Y 方向渗透率 Ky。"""
        self.render_corner_permeability_field(sim_data, direction="y")


    def render_corner_kz_field(self, sim_data):
        """渲染 Z 方向渗透率 Kz。"""
        self.render_corner_permeability_field(sim_data, direction="z")

    def hide_permeability_field(self):
        """隐藏/清除渗透率场。"""

        self._remove_actor(self.cache.get("perm_field_actor"))
        self.cache["perm_field_actor"] = None

        if self.cache.get("perm_scalar_bar") is not None:
            try:
                self.plotter.remove_scalar_bar(render=False)
            except Exception:
                pass
            self.cache["perm_scalar_bar"] = None

        self._render()

    def render_corner_perm_by_layer(
        self,
        sim_data,
        perm_direction="x",
        axis="k",
        layer_index=0,
        opacity=RESULT_PROPERTY_OPACITY,
        show_edges=False,
        show_grid=True,
        show_fractures=True,
        show_wells=True
    ):
        """
        渲染 Kx / Ky / Kz 的 I/J/K 分层结果。
        """

        if not sim_data.corner_point_grid:
            return

        if getattr(sim_data, "cell_geometry_with_pressure", None) is None:
            return

        
        
        
        perm_direction = str(perm_direction).lower()

        perm_config = {
            "x": {
                "column": 29,
                "scalar_name": "Kx",
                "title": "Permeability X",
            },
            "y": {
                "column": 30,
                "scalar_name": "Ky",
                "title": "Permeability Y",
            },
            "z": {
                "column": 31,
                "scalar_name": "Kz",
                "title": "Permeability Z",
            },
        }

        if perm_direction not in perm_config:
            print(f"Invalid perm_direction = {perm_direction}, use 'x', 'y', or 'z'")
            return

        config = perm_config[perm_direction]
        col = int(config["column"])
        scalar_name = config["scalar_name"]
        scalar_title = config["title"]

        axis = str(axis).lower()

        if axis not in ("i", "j", "k"):
            print(f"Invalid axis = {axis}, use 'i', 'j', or 'k'")
            return

        cell_data = sim_data.cell_geometry_with_pressure

        if cell_data is None or cell_data.shape[0] == 0:
            return

        if cell_data.shape[1] <= col:
            print(
                f"Column index out of range for {scalar_name}: "
                f"column={col}, data columns={cell_data.shape[1]}"
            )
            return

        
        
        
        self._remove_actor(self.cache.get("layer_perm_actor"))
        self._remove_actor(self.cache.get("layer_perm_coarse_grid_actor"))


        self.cache["layer_perm_actor"] = None
        self.cache["layer_perm_coarse_grid_actor"] = None

        if self.cache.get("layer_perm_scalar_bar") is not None:
            try:
                self.plotter.remove_scalar_bar(render=False)
            except Exception:
                pass
            self.cache["layer_perm_scalar_bar"] = None

        try:
            
            
            
            cpg = sim_data.corner_point_grid

            nx = int(sim_data.grid_info["nx"])
            ny = int(sim_data.grid_info["ny"])
            nz = int(sim_data.grid_info["nz"])

            if axis == "i":
                if layer_index < 0 or layer_index >= nx:
                    print(f"Invalid i layer = {layer_index}")
                    return

                coarse_cells = []
                for k in range(nz):
                    for j in range(ny):
                        idx = layer_index + j * nx + k * nx * ny
                        if idx < len(cpg.cells):
                            coarse_cells.append(cpg.cells[idx])

            elif axis == "j":
                if layer_index < 0 or layer_index >= ny:
                    print(f"Invalid j layer = {layer_index}")
                    return

                coarse_cells = []
                for k in range(nz):
                    for i in range(nx):
                        idx = i + layer_index * nx + k * nx * ny
                        if idx < len(cpg.cells):
                            coarse_cells.append(cpg.cells[idx])

            else:
                if layer_index < 0 or layer_index >= nz:
                    print(f"Invalid k layer = {layer_index}")
                    return

                start = layer_index * nx * ny
                end = (layer_index + 1) * nx * ny
                coarse_cells = cpg.cells[start:end]

            if not coarse_cells:
                print(f"No coarse cells found for axis={axis}, layer={layer_index}")
                self._render()
                return

            
            
            
            coarse_boxes = []

            coarse_points = []
            coarse_cell_array = []
            coarse_cell_types = []
            point_offset = 0

            for cell in coarse_cells:

                pts = np.array(cell.corners, dtype=np.float32)

                if pts.shape != (8, 3):
                    continue

                xs = pts[:, 0]
                ys = pts[:, 1]
                zs = pts[:, 2]

                coarse_boxes.append({
                    "xmin": float(xs.min()),
                    "xmax": float(xs.max()),
                    "ymin": float(ys.min()),
                    "ymax": float(ys.max()),
                    "zmin": float(zs.min()),
                    "zmax": float(zs.max()),
                })

                coarse_points.extend(pts)

                coarse_cell_array.extend([
                    8,
                    point_offset + 0,
                    point_offset + 1,
                    point_offset + 2,
                    point_offset + 3,
                    point_offset + 4,
                    point_offset + 5,
                    point_offset + 6,
                    point_offset + 7,
                ])

                coarse_cell_types.append(pv.CellType.HEXAHEDRON)
                point_offset += 8

            if not coarse_boxes:
                print(f"No valid coarse boxes for axis={axis}, layer={layer_index}")
                self._render()
                return

            
            

            
            
            
            selected_indices = self._get_layer_row_indices_by_parent_id(
                sim_data=sim_data,
                axis=axis,
                layer_index=layer_index,
                cell_data=cell_data,
            )

            if selected_indices.size == 0:
                print(
                    f"No leaf cells found for {scalar_name}, "
                    f"axis={axis}, layer={layer_index}"
                )
                self._render()
                return

            selected_rows = cell_data[selected_indices]

            
            
            
            all_points = []
            cell_corner_ids = []

            for row in selected_rows:
                pts = row[4:28].reshape(8, 3).astype(np.float32)
                start_idx = len(all_points)
                all_points.extend(pts)
                cell_corner_ids.append(list(range(start_idx, start_idx + 8)))

            all_points = np.array(all_points, dtype=np.float32)

            points, inverse = np.unique(
                all_points,
                axis=0,
                return_inverse=True
            )

            n_cells = len(cell_corner_ids)

            cell_array = np.empty(n_cells * 9, dtype=np.int64)
            cell_types = np.full(
                n_cells,
                pv.CellType.HEXAHEDRON,
                dtype=np.uint8
            )

            for i in range(n_cells):
                cell_array[i * 9] = 8
                ids = inverse[i * 8:(i + 1) * 8]
                cell_array[i * 9 + 1:i * 9 + 9] = ids

            grid = pv.UnstructuredGrid(
                cell_array,
                cell_types,
                points
            )

            selected_perm = selected_rows[:, col].astype(np.float32)
            all_perm = cell_data[:, col].astype(np.float32)

            grid.cell_data[scalar_name] = selected_perm

            surface = self._build_result_property_shell_surface(grid)


            valid_values = all_perm[np.isfinite(all_perm)]

            if valid_values.size == 0:
                print(f"No valid values for {scalar_name}")
                self._render()
                return

            kmin = float(np.nanmin(valid_values))
            kmax = float(np.nanmax(valid_values))

            if kmin == kmax:
                delta = abs(kmin) * 0.01 if kmin != 0 else 1.0
                kmin -= delta
                kmax += delta

            
            
            
            
            actor = self.plotter.add_mesh(
                surface,
                scalars=scalar_name,
                cmap=get_bright_jet_cmap(),
                clim=[kmin, kmax],
                opacity=opacity,
                show_scalar_bar=False,
                show_edges=show_edges,
                edge_color=(0.18, 0.18, 0.18),
                line_width=0.3,
                lighting=False,
                smooth_shading=False,
                ambient=1.0,
                diffuse=0.0,
                specular=0.0,
                interpolate_before_map=False,
                reset_camera=False,
                render=False,
            )

            scalar_bar = self._replace_scalar_bar(
                "layer_perm_scalar_bar",
                scalar_title,
                position_x=0.02,
                position_y=0.55,
                width=0.08,
                height=0.40,
                label_font_size=14,
                title_font_size=16,
                color="#2f3640",
                vertical=True,
                render=False,
            )

            self.cache["layer_perm_actor"] = actor
            self.cache["layer_perm_scalar_bar"] = scalar_bar

            self._replace_layer_grid_with_refined_grid(
                selected_rows=selected_rows,
                cache_key="layer_perm_coarse_grid_actor",
                show_grid=show_grid,
            )
            self._register_result_property_context(
                sim_data=sim_data,
                property_name=scalar_name,
                volume_grid=grid,
                actor=actor,
                axis=axis,
                layer_index=layer_index,
                title=scalar_title,
                source_indices=selected_indices,
            )

            
            self._finish_property_switch_render()

        except Exception as exc:
            print("\n")
            print("=" * 60)
            print("ERROR IN render_corner_perm_by_layer")
            print(exc)
            print("=" * 60)
            print("\n")

    
    # Kx 分层
    
    def render_corner_kx_by_layer_i(self, sim_data, i_layer: int):
        self.render_corner_perm_by_layer(
            sim_data,
            perm_direction="x",
            axis="i",
            layer_index=i_layer
        )


    def render_corner_kx_by_layer_j(self, sim_data, j_layer: int):
        self.render_corner_perm_by_layer(
            sim_data,
            perm_direction="x",
            axis="j",
            layer_index=j_layer
        )


    def render_corner_kx_by_layer_k(self, sim_data, k_layer: int):
        self.render_corner_perm_by_layer(
            sim_data,
            perm_direction="x",
            axis="k",
            layer_index=k_layer
        )


    
    # Ky 分层
    
    def render_corner_ky_by_layer_i(self, sim_data, i_layer: int):
        self.render_corner_perm_by_layer(
            sim_data,
            perm_direction="y",
            axis="i",
            layer_index=i_layer
        )


    def render_corner_ky_by_layer_j(self, sim_data, j_layer: int):
        self.render_corner_perm_by_layer(
            sim_data,
            perm_direction="y",
            axis="j",
            layer_index=j_layer
        )


    def render_corner_ky_by_layer_k(self, sim_data, k_layer: int):
        self.render_corner_perm_by_layer(
            sim_data,
            perm_direction="y",
            axis="k",
            layer_index=k_layer
        )


    
    # Kz 分层
    
    def render_corner_kz_by_layer_i(self, sim_data, i_layer: int):
        self.render_corner_perm_by_layer(
            sim_data,
            perm_direction="z",
            axis="i",
            layer_index=i_layer
        )


    def render_corner_kz_by_layer_j(self, sim_data, j_layer: int):
        self.render_corner_perm_by_layer(
            sim_data,
            perm_direction="z",
            axis="j",
            layer_index=j_layer
        )


    def render_corner_kz_by_layer_k(self, sim_data, k_layer: int):
        self.render_corner_perm_by_layer(
            sim_data,
            perm_direction="z",
            axis="k",
            layer_index=k_layer
        )

    def clear_perm_layer_render(self):
        """清除渗透率分层渲染结果。"""

        self._remove_actor(self.cache.get("layer_perm_actor"))
        self._remove_actor(self.cache.get("layer_perm_coarse_grid_actor"))

        self._remove_actor_list(self.cache.get("layer_perm_frac_actors", []))
        self._remove_actor_list(self.cache.get("layer_perm_well_actors", []))

        self.cache["layer_perm_actor"] = None
        self.cache["layer_perm_coarse_grid_actor"] = None
        self.cache["layer_perm_frac_actors"] = []
        self.cache["layer_perm_well_actors"] = []

        if self.cache.get("layer_perm_scalar_bar") is not None:
            try:
                self.plotter.remove_scalar_bar(render=False)
            except Exception:
                pass

            self.cache["layer_perm_scalar_bar"] = None

        self._render()


    
    
    

    def _get_pick_property_config(
        self,
        property_name,
        quiet=False,
    ):
        """
        返回统一拾取属性配置。

        同时支持模拟结果 Pressure/Sw/Phi/Kx/Ky/Kz，
        以及静态预览 MATRIX_* / DFN_* / SIGMA。
        """
        name = str(
            property_name
            if property_name is not None
            else ""
        ).strip()

        canonical = self._normalize_scene_property_name(
            name
        )

        result_config = {
            "Pressure": {
                "column": 28,
                "title": "Pressure",
                "unit": "bar",
                "scalar_name": "Pressure",
            },
            "Kx": {
                "column": 29,
                "title": "Permeability X",
                "unit": "",
                "scalar_name": "Kx",
            },
            "Ky": {
                "column": 30,
                "title": "Permeability Y",
                "unit": "",
                "scalar_name": "Ky",
            },
            "Kz": {
                "column": 31,
                "title": "Permeability Z",
                "unit": "",
                "scalar_name": "Kz",
            },
            "Phi": {
                "column": 32,
                "title": "Porosity",
                "unit": "",
                "scalar_name": "Phi",
            },
            "Sw": {
                "column": 33,
                "title": "Water Saturation",
                "unit": "",
                "scalar_name": "Sw",
            },
        }

        if canonical in result_config:
            return dict(
                result_config[canonical]
            )

        try:
            from .pyvista_static_property_preview import (
                STATIC_PROPERTY_SPECS,
                normalize_static_property_key,
            )

            static_key = normalize_static_property_key(
                name
            )
            spec = STATIC_PROPERTY_SPECS[
                static_key
            ]

            return {
                "column": None,
                "title": spec.get(
                    "label",
                    static_key,
                ),
                "unit": spec.get(
                    "unit",
                    "",
                ),
                "scalar_name": (
                    f"Static_{static_key}"
                ),
                "static_property_key": static_key,
            }

        except Exception:
            if not quiet:
                print(
                    f"Unsupported pick property: "
                    f"{property_name}"
                )
                print(
                    "Supported result properties: "
                    f"{list(result_config.keys())}"
                )

            return None



    def set_cell_pick_property(self, property_name):
        """
        设置当前拾取时显示的属性。
        例如：
            Pressure / Kx / Ky / Kz / Phi / Sw
        """

        config = self._get_pick_property_config(property_name)

        if config is None:
            return

        self.cache["cell_pick_property"] = str(property_name).strip()


    @staticmethod
    def _grid_cell_array(
        grid,
        key,
        *,
        dtype=None,
    ):
        if grid is None:
            return None

        try:
            if key not in grid.cell_data:
                return None

            array = np.asarray(
                grid.cell_data[key],
                dtype=dtype,
            )
        except Exception:
            return None

        try:
            if len(array) != int(grid.n_cells):
                return None
        except Exception:
            return None

        return array


    def _prepare_pick_grid_from_context(
        self,
        context,
    ):
        if not isinstance(context, dict):
            return None

        source_grid = context.get(
            "volume_grid"
        )

        if not self._dataset_has_cells(
            source_grid
        ):
            return None

        try:
            grid = source_grid.copy(
                deep=True
            )
        except Exception:
            grid = source_grid

        n_cells = int(
            grid.n_cells
        )

        if self._grid_cell_array(
            grid,
            "PickCellId",
        ) is None:
            grid.cell_data["PickCellId"] = np.arange(
                n_cells,
                dtype=np.int32,
            )

        source_ids = self._grid_cell_array(
            grid,
            "SourceCellId",
            dtype=np.int64,
        )

        if source_ids is None:
            source_ids = self._grid_cell_array(
                grid,
                "OriginalRowIndex",
                dtype=np.int64,
            )

        if source_ids is None:
            source_ids = np.arange(
                n_cells,
                dtype=np.int64,
            )

        grid.cell_data["SourceCellId"] = source_ids
        grid.cell_data["OriginalRowIndex"] = source_ids

        i_values = self._grid_cell_array(
            grid,
            "I",
            dtype=np.int64,
        )
        j_values = self._grid_cell_array(
            grid,
            "J",
            dtype=np.int64,
        )
        k_values = self._grid_cell_array(
            grid,
            "K",
            dtype=np.int64,
        )

        if i_values is None:
            i_values = self._grid_cell_array(
                grid,
                "CellInfo1",
                dtype=np.int64,
            )
        if j_values is None:
            j_values = self._grid_cell_array(
                grid,
                "CellInfo2",
                dtype=np.int64,
            )
        if k_values is None:
            k_values = self._grid_cell_array(
                grid,
                "CellInfo3",
                dtype=np.int64,
            )

        if i_values is None:
            i_values = np.zeros(
                n_cells,
                dtype=np.int64,
            )
        if j_values is None:
            j_values = np.zeros(
                n_cells,
                dtype=np.int64,
            )
        if k_values is None:
            k_values = np.zeros(
                n_cells,
                dtype=np.int64,
            )

        grid.cell_data["I"] = i_values
        grid.cell_data["J"] = j_values
        grid.cell_data["K"] = k_values

        if self._grid_cell_array(
            grid,
            "CellInfo0",
        ) is None:
            grid.cell_data["CellInfo0"] = (
                source_ids.astype(np.float64)
            )
        if self._grid_cell_array(
            grid,
            "CellInfo1",
        ) is None:
            grid.cell_data["CellInfo1"] = (
                i_values.astype(np.float64)
            )
        if self._grid_cell_array(
            grid,
            "CellInfo2",
        ) is None:
            grid.cell_data["CellInfo2"] = (
                j_values.astype(np.float64)
            )
        if self._grid_cell_array(
            grid,
            "CellInfo3",
        ) is None:
            grid.cell_data["CellInfo3"] = (
                k_values.astype(np.float64)
            )

        centers_ready = all(
            self._grid_cell_array(
                grid,
                key,
            ) is not None
            for key in (
                "CenterX",
                "CenterY",
                "CenterZ",
            )
        )

        if not centers_ready:
            try:
                centers = np.asarray(
                    grid.cell_centers().points,
                    dtype=np.float64,
                )
            except Exception:
                centers = None

            if (
                centers is not None
                and centers.shape == (
                    n_cells,
                    3,
                )
            ):
                grid.cell_data["CenterX"] = (
                    centers[:, 0]
                )
                grid.cell_data["CenterY"] = (
                    centers[:, 1]
                )
                grid.cell_data["CenterZ"] = (
                    centers[:, 2]
                )

        if self._grid_cell_array(
            grid,
            "Volume",
        ) is None:
            try:
                sized = grid.compute_cell_sizes(
                    length=False,
                    area=False,
                    volume=True,
                )
                grid.cell_data["Volume"] = np.asarray(
                    sized.cell_data["Volume"],
                    dtype=np.float64,
                )
            except Exception:
                grid.cell_data["Volume"] = np.zeros(
                    n_cells,
                    dtype=np.float64,
                )

        scalar_name = str(
            context.get(
                "scalar_name",
                "",
            )
        ).strip()

        if (
            scalar_name
            and self._grid_cell_array(
                grid,
                scalar_name,
            ) is None
        ):
            property_name = context.get(
                "property_name"
            )
            config = self._get_pick_property_config(
                property_name,
                quiet=True,
            ) or {}
            fallback_name = config.get(
                "scalar_name"
            )

            if (
                fallback_name
                and self._grid_cell_array(
                    grid,
                    fallback_name,
                ) is not None
            ):
                scalar_name = fallback_name

        return grid


    def _refresh_cell_pick_target(
        self,
        *,
        render_now=False,
    ):
        cache = self.cache

        self._remove_actor(
            cache.get("cell_pick_actor")
        )
        self._remove_actor(
            cache.get(
                "cell_pick_highlight_actor"
            )
        )
        cache["cell_pick_actor"] = None
        cache["cell_pick_grid"] = None
        cache["cell_pick_highlight_actor"] = None
        cache["cell_pick_last_info"] = None

        context = self.get_active_property_context()

        if not isinstance(context, dict):
            if render_now:
                self._render()
            return False

        grid = self._prepare_pick_grid_from_context(
            context
        )

        if grid is None:
            if render_now:
                self._render()
            return False

        actor = self.plotter.add_mesh(
            grid,
            color=(1.0, 1.0, 1.0),
            opacity=0.001,
            show_edges=False,
            lighting=False,
            pickable=True,
            reset_camera=False,
            render=False,
        )

        try:
            actor.SetPickable(True)
        except Exception:
            pass

        cache["cell_pick_grid"] = grid
        cache["cell_pick_actor"] = actor
        cache["cell_pick_property"] = context.get(
            "property_name",
            "Pressure",
        )
        cache["cell_pick_scalar_name"] = context.get(
            "scalar_name",
            "",
        )
        cache["cell_pick_source_mode"] = context.get(
            "source_mode",
        )

        if render_now:
            self._render()

        return True


    def _build_cell_pick_grid(
        self,
        sim_data=None,
        axis=None,
        layer_index=None,
        use_active_context=True,
    ):
        """
        构建用于 cell picking 的 UnstructuredGrid。

        优先复用当前属性场上下文中的 volume_grid；
        没有上下文时才回退到模拟结果 cell_geometry_with_pressure。
        """
        if use_active_context:
            context = self.get_active_property_context()

            if isinstance(context, dict):
                grid = self._prepare_pick_grid_from_context(
                    context
                )
                if grid is not None:
                    return grid

        if sim_data is None:
            return None

        if getattr(sim_data, "cell_geometry_with_pressure", None) is None:
            return None

        cell_data = sim_data.cell_geometry_with_pressure

        if cell_data is None or cell_data.shape[0] == 0:
            return None

        if cell_data.shape[1] < 34:
            print(
                "cell_geometry_with_pressure columns are not enough. "
                "Expected at least 34 columns."
            )
            return None

        
        
        
        if axis is None or layer_index is None:

            selected_original_indices = np.arange(
                cell_data.shape[0],
                dtype=np.int64,
            )

        
        
        
        else:

            axis = str(axis).lower().strip()

            if axis not in ("i", "j", "k"):
                print(
                    f"Invalid picking axis = {axis}, "
                    "use 'i', 'j', or 'k'"
                )
                return None

            try:
                selected_original_indices = (
                    self._get_layer_row_indices_by_parent_id(
                        sim_data=sim_data,
                        axis=axis,
                        layer_index=layer_index,
                        cell_data=cell_data,
                    )
                )

            except ValueError as exc:
                print(exc)
                return None

        if selected_original_indices.size == 0:
            print(
                "No cells selected for picking grid. "
                f"axis={axis}, layer={layer_index}"
            )
            return None

        selected_original_indices = np.asarray(
            selected_original_indices,
            dtype=np.int64,
        )

        selected_rows = cell_data[selected_original_indices]

        n_cells = selected_rows.shape[0]

        
        
        
        all_points = []
        cells = []
        offset = 0
        centers = []

        for i in range(n_cells):

            pts = selected_rows[
                i,
                4:28,
            ].reshape(8, 3).astype(np.float32)

            all_points.append(pts)

            cells.append([
                8,
                offset + 0,
                offset + 1,
                offset + 2,
                offset + 3,
                offset + 4,
                offset + 5,
                offset + 6,
                offset + 7,
            ])

            offset += 8

            centers.append(
                pts.mean(axis=0)
            )

        points = np.vstack(all_points).astype(np.float32)

        cells = np.hstack(cells).astype(np.int64)

        cell_types = np.full(
            n_cells,
            pv.CellType.HEXAHEDRON,
            dtype=np.uint8,
        )

        grid = pv.UnstructuredGrid(
            cells,
            cell_types,
            points,
        )

        centers = np.asarray(
            centers,
            dtype=np.float32,
        )

        
        
        

        
        grid.cell_data["PickCellId"] = np.arange(
            n_cells,
            dtype=np.int32,
        )

        
        grid.cell_data["OriginalRowIndex"] = (
            selected_original_indices.astype(np.int64)
        )
        grid.cell_data["SourceCellId"] = (
            selected_original_indices.astype(np.int64)
        )

        grid.cell_data["CellInfo0"] = selected_rows[
            :,
            0,
        ].astype(np.float64)

        grid.cell_data["CellInfo1"] = selected_rows[
            :,
            1,
        ].astype(np.float64)

        grid.cell_data["CellInfo2"] = selected_rows[
            :,
            2,
        ].astype(np.float64)

        grid.cell_data["CellInfo3"] = selected_rows[
            :,
            3,
        ].astype(np.float64)

        
        
        try:
            nx = int(sim_data.grid_info["nx"])
            ny = int(sim_data.grid_info["ny"])
            parent_ids = np.rint(
                selected_rows[:, 1]
            ).astype(np.int64)
            grid.cell_data["I"] = (
                parent_ids % nx
            )
            grid.cell_data["J"] = (
                (parent_ids // nx) % ny
            )
            grid.cell_data["K"] = (
                parent_ids // (nx * ny)
            )
        except Exception:
            grid.cell_data["I"] = selected_rows[
                :,
                2,
            ].astype(np.int64)
            grid.cell_data["J"] = selected_rows[
                :,
                3,
            ].astype(np.int64)
            grid.cell_data["K"] = np.zeros(
                n_cells,
                dtype=np.int64,
            )

        grid.cell_data["Pressure"] = selected_rows[
            :,
            28,
        ].astype(np.float32)

        grid.cell_data["Kx"] = selected_rows[
            :,
            29,
        ].astype(np.float32)

        grid.cell_data["Ky"] = selected_rows[
            :,
            30,
        ].astype(np.float32)

        grid.cell_data["Kz"] = selected_rows[
            :,
            31,
        ].astype(np.float32)

        grid.cell_data["Phi"] = selected_rows[
            :,
            32,
        ].astype(np.float32)

        grid.cell_data["Sw"] = selected_rows[
            :,
            33,
        ].astype(np.float32)

        grid.cell_data["CenterX"] = centers[:, 0]
        grid.cell_data["CenterY"] = centers[:, 1]
        grid.cell_data["CenterZ"] = centers[:, 2]

        
        
        
        try:
            size_grid = grid.compute_cell_sizes(
                length=False,
                area=False,
                volume=True,
            )

            if "Volume" in size_grid.cell_data:
                grid.cell_data["Volume"] = (
                    size_grid.cell_data["Volume"]
                    .astype(np.float64)
                )
            else:
                grid.cell_data["Volume"] = np.zeros(
                    n_cells,
                    dtype=np.float64,
                )

        except Exception:

            
            volumes = []

            for i in range(n_cells):

                pts = selected_rows[
                    i,
                    4:28,
                ].reshape(8, 3).astype(np.float64)

                dx = float(
                    pts[:, 0].max()
                    - pts[:, 0].min()
                )

                dy = float(
                    pts[:, 1].max()
                    - pts[:, 1].min()
                )

                dz = float(
                    pts[:, 2].max()
                    - pts[:, 2].min()
                )

                volumes.append(
                    abs(dx * dy * dz)
                )

            grid.cell_data["Volume"] = np.asarray(
                volumes,
                dtype=np.float64,
            )

        return grid


    def enable_cell_info_picking(
        self,
        sim_data=None,
        property_name=None,
        axis=None,
        layer_index=None,
    ):
        """
        开启统一 cell picking。

        当前显示的是预览属性场时，直接拾取 static preview 的 current_grid；
        当前显示的是模拟结果时，拾取结果 volume_grid。
        旧 UI 仍可继续传 sim_data/property_name/axis/layer_index。
        """
        
        self.disable_cell_info_picking(
            clear_highlight=True,
            render_now=False,
        )

        context = self.get_active_property_context()

        if isinstance(context, dict):
            
            property_name = context.get(
                "property_name",
                property_name,
            )
            sim_data = context.get(
                "sim_data",
                sim_data,
            )
            axis = context.get(
                "axis",
                axis,
            )
            layer_index = context.get(
                "layer_index",
                layer_index,
            )
        else:
            if property_name is None:
                property_name = self.cache.get(
                    "cell_pick_property",
                    "Pressure",
                )

            config = self._get_pick_property_config(
                property_name
            )
            if config is None:
                return False

            grid = self._build_cell_pick_grid(
                sim_data,
                axis=axis,
                layer_index=layer_index,
                use_active_context=False,
            )

            if grid is None:
                print(
                    "Failed to build cell pick grid."
                )
                return False

            scalar_name = config.get(
                "scalar_name",
                str(property_name),
            )

            self.set_active_property_context(
                source_mode="result",
                sim_data=sim_data,
                property_name=property_name,
                scalar_name=scalar_name,
                volume_grid=grid,
                actor=None,
                axis=axis,
                layer_index=layer_index,
                title=config.get(
                    "title",
                    property_name,
                ),
                unit=config.get(
                    "unit",
                    "",
                ),
                refresh_picking=False,
            )

        self.cache["cell_pick_enabled"] = True

        try:
            interactor = self.plotter.iren.interactor
            observer_id = interactor.AddObserver(
                "LeftButtonPressEvent",
                self._on_cell_info_pick,
            )
            self.cache[
                "cell_pick_observer_id"
            ] = observer_id
        except Exception as exc:
            self.cache["cell_pick_enabled"] = False
            print(
                "Failed to add cell picking observer"
            )
            print(exc)
            return False

        ok = self._refresh_cell_pick_target(
            render_now=False,
        )

        if not ok:
            self.disable_cell_info_picking(
                clear_highlight=True,
                render_now=False,
            )
            print(
                "No active property grid for picking."
            )
            return False

        self._render()
        return True



    def disable_cell_info_picking(
        self,
        clear_highlight=True,
        render_now=True,
    ):
        """关闭统一 cell picking。"""
        observer_id = self.cache.get(
            "cell_pick_observer_id"
        )

        if observer_id is not None:
            try:
                interactor = self.plotter.iren.interactor
                interactor.RemoveObserver(
                    observer_id
                )
            except Exception:
                pass

        self.cache["cell_pick_observer_id"] = None
        self.cache["cell_pick_enabled"] = False

        self._remove_actor(
            self.cache.get("cell_pick_actor")
        )
        self.cache["cell_pick_actor"] = None
        self.cache["cell_pick_grid"] = None
        self.cache["cell_pick_source_mode"] = None
        self.cache["cell_pick_scalar_name"] = None

        if clear_highlight:
            self.clear_cell_pick_highlight(
                render_now=False,
            )

        if render_now:
            self._render()

        return True



    def clear_cell_pick_highlight(
        self,
        render_now=True,
    ):
        """清除当前拾取高亮 cell。"""
        self._remove_actor(
            self.cache.get(
                "cell_pick_highlight_actor"
            )
        )
        self.cache[
            "cell_pick_highlight_actor"
        ] = None
        self.cache["cell_pick_last_info"] = None

        if render_now:
            self._render()



    def _highlight_picked_cell(self, grid, cell_id):
        """
        高亮被拾取的 cell。
        """

        self._remove_actor(self.cache.get("cell_pick_highlight_actor"))
        self.cache["cell_pick_highlight_actor"] = None

        if grid is None:
            return

        if cell_id < 0 or cell_id >= grid.n_cells:
            return

        try:
            picked_cell = grid.extract_cells([cell_id])
            surface = picked_cell.extract_surface()

            actor = self.plotter.add_mesh(
                surface,
                color=(1.0, 1.0, 0.0),
                opacity=0.35,
                show_edges=True,
                edge_color=(1.0, 0.75, 0.0),
                line_width=2.0,
                lighting=False,
                pickable=False,
                reset_camera=False,
                render=False,
            )

            self.cache["cell_pick_highlight_actor"] = actor

        except Exception as exc:
            print("Failed to highlight picked cell")
            print(exc)


    def _format_picked_cell_info(
        self,
        grid,
        cell_id,
        property_name=None,
    ):
        """生成预览/模拟共用的拾取信息。"""
        if grid is None:
            return None

        if cell_id < 0 or cell_id >= grid.n_cells:
            return None

        context = self.get_active_property_context() or {}

        if property_name is None:
            property_name = context.get(
                "property_name",
                self.cache.get(
                    "cell_pick_property",
                    "Pressure",
                ),
            )

        config = self._get_pick_property_config(
            property_name,
            quiet=True,
        ) or {}

        scalar_name = str(
            context.get(
                "scalar_name",
                self.cache.get(
                    "cell_pick_scalar_name",
                    config.get(
                        "scalar_name",
                        property_name,
                    ),
                ),
            )
        ).strip()

        if (
            not scalar_name
            or scalar_name not in grid.cell_data
        ):
            preferred = config.get(
                "scalar_name"
            )

            if (
                preferred
                and preferred in grid.cell_data
            ):
                scalar_name = preferred
            else:
                metadata_names = {
                    "PickCellId",
                    "SourceCellId",
                    "OriginalRowIndex",
                    "I",
                    "J",
                    "K",
                    "CellInfo0",
                    "CellInfo1",
                    "CellInfo2",
                    "CellInfo3",
                    "CenterX",
                    "CenterY",
                    "CenterZ",
                    "Volume",
                }
                candidates = [
                    key
                    for key in grid.cell_data.keys()
                    if key not in metadata_names
                ]

                if not candidates:
                    return None

                scalar_name = candidates[0]

        try:
            value = float(
                grid.cell_data[
                    scalar_name
                ][cell_id]
            )
        except Exception:
            return None

        def _value(
            *keys,
            default=0.0,
        ):
            for key in keys:
                try:
                    if key in grid.cell_data:
                        return grid.cell_data[
                            key
                        ][cell_id]
                except Exception:
                    continue
            return default

        source_id = _value(
            "SourceCellId",
            "OriginalRowIndex",
            "CellInfo0",
            default=cell_id,
        )
        i_value = _value(
            "I",
            "CellInfo1",
            default=0,
        )
        j_value = _value(
            "J",
            "CellInfo2",
            default=0,
        )
        k_value = _value(
            "K",
            "CellInfo3",
            default=0,
        )

        cx = float(
            _value(
                "CenterX",
                default=0.0,
            )
        )
        cy = float(
            _value(
                "CenterY",
                default=0.0,
            )
        )
        cz = float(
            _value(
                "CenterZ",
                default=0.0,
            )
        )
        volume = float(
            _value(
                "Volume",
                default=0.0,
            )
        )

        try:
            cell_index_text = (
                f"id={int(source_id)}, "
                f"index=({int(i_value)}, "
                f"{int(j_value)}, "
                f"{int(k_value)})"
            )
        except Exception:
            cell_index_text = (
                f"id={source_id}, "
                f"index=({i_value}, "
                f"{j_value}, "
                f"{k_value})"
            )

        title = context.get(
            "title",
            config.get(
                "title",
                property_name,
            ),
        )
        unit = context.get(
            "unit",
            config.get(
                "unit",
                "",
            ),
        )
        source_mode = context.get(
            "source_mode",
            self.cache.get(
                "cell_pick_source_mode",
                "result",
            ),
        )

        value_text = f"{value:.6g}"
        if unit:
            value_text += f" {unit}"

        return (
            f"Source: {source_mode} | "
            f"Selected property: {title} | "
            f"Grid cell: {cell_index_text} | "
            f"Value: {value_text} | "
            f"Type: Continuous | "
            f"Volume: {volume:.3f} m3 | "
            f"x: {cx:.3f} m | "
            f"y: {cy:.3f} m | "
            f"Depth: {cz:.3f} m"
        )



    def _on_cell_info_pick(self, obj, event):
        """
        鼠标点击回调：拾取 cell 并输出信息。
        """

        if not self.cache.get("cell_pick_enabled", False):
            return

        grid = self.cache.get("cell_pick_grid")

        if grid is None:
            return

        try:
            from vtkmodules.vtkRenderingCore import vtkCellPicker

            interactor = self.plotter.iren.interactor
            x, y = interactor.GetEventPosition()

            picker = vtkCellPicker()
            picker.SetTolerance(0.0005)

            target_actor = self.cache.get("cell_pick_actor")

            if target_actor is not None:
                try:
                    picker.PickFromListOn()
                    picker.AddPickList(target_actor)
                except Exception:
                    pass

            ok = picker.Pick(
                float(x),
                float(y),
                0.0,
                self.renderer
            )

            if not ok:
                return

            cell_id = picker.GetCellId()

            if cell_id < 0:
                return

            property_name = self.cache.get(
                "cell_pick_property",
                "Pressure"
            )

            self._highlight_picked_cell(grid, cell_id)

            info_text = self._format_picked_cell_info(
                grid,
                cell_id,
                property_name
            )

            if info_text is not None:
                self.cache["cell_pick_last_info"] = info_text

                print(info_text)

                try:
                    if hasattr(self.view, "show_pick_info"):
                        self.view.show_pick_info(info_text)

                    elif hasattr(self.view, "set_status_message"):
                        self.view.set_status_message(info_text)

                except Exception:
                    pass

            self._render()

        except Exception as exc:
            print("ERROR IN _on_cell_info_pick")
            print(exc)

    
    # 动态尺子工具
    # 第一次点击确定起点，鼠标移动动态画白线并刷新测量信息；
    # 第二次点击确定终点，白线固定，测量信息固定。
    
    def enable_petrel_distance_measure(self):

        self.disable_petrel_distance_measure(clear_line=True)

        self.cache["measure_enabled"] = True
        self.cache["measure_start_point"] = None
        self.cache["measure_end_point"] = None
        self.cache["measure_line_mesh"] = None
        self.cache["measure_line_actor"] = None
        self.cache["measure_observer_ids"] = []
        self.cache["measure_is_previewing"] = False
        self.cache["measure_last_info"] = None

        try:
            interactor = self.plotter.iren.interactor

            left_id = interactor.AddObserver(
                "LeftButtonPressEvent",
                self._on_measure_left_click
            )

            move_id = interactor.AddObserver(
                "MouseMoveEvent",
                self._on_measure_mouse_move
            )

            self.cache["measure_observer_ids"] = [left_id, move_id]

            print("Distance measure enabled. Click the first point.")

        except Exception as exc:
            print("Failed to enable distance measure.")
            print(exc)


    def disable_petrel_distance_measure(self, clear_line=True):

        observer_ids = self.cache.get("measure_observer_ids", [])

        if observer_ids:
            try:
                interactor = self.plotter.iren.interactor

                for observer_id in observer_ids:
                    try:
                        interactor.RemoveObserver(observer_id)
                    except Exception:
                        pass

            except Exception:
                pass

        self.cache["measure_observer_ids"] = []
        self.cache["measure_enabled"] = False
        self.cache["measure_is_previewing"] = False
        self.cache["measure_start_point"] = None
        self.cache["measure_end_point"] = None

        if clear_line:
            self.clear_petrel_distance_measure()

        print("\nDistance measure disabled.")


    def clear_petrel_distance_measure(self):

        self._remove_actor(self.cache.get("measure_line_actor"))

        self.cache["measure_line_actor"] = None
        self.cache["measure_line_mesh"] = None
        self.cache["measure_start_point"] = None
        self.cache["measure_end_point"] = None
        self.cache["measure_is_previewing"] = False
        self.cache["measure_last_info"] = None

        self._render()


    def _measure_pick_world_point(self):

        try:
            from vtkmodules.vtkRenderingCore import vtkCellPicker

            interactor = self.plotter.iren.interactor
            x, y = interactor.GetEventPosition()

            picker = vtkCellPicker()
            picker.SetTolerance(0.0008)

            ok = picker.Pick(
                float(x),
                float(y),
                0.0,
                self.renderer
            )

            if not ok:
                return None

            picked_actor = picker.GetActor()

            
            if picked_actor is None:
                return None

            
            measure_actor = self.cache.get("measure_line_actor")
            if measure_actor is not None and picked_actor is measure_actor:
                return None

            pos = picker.GetPickPosition()

            if pos is None:
                return None

            point = np.array(
                [float(pos[0]), float(pos[1]), float(pos[2])],
                dtype=np.float64
            )

            if not np.all(np.isfinite(point)):
                return None

            return point

        except Exception:
            return None


    def _create_or_update_measure_line(self, start_point, end_point):
        """
        创建或更新白色测量线。
        不显示端点小球。
        """

        if start_point is None or end_point is None:
            return

        start_point = np.array(start_point, dtype=np.float64)
        end_point = np.array(end_point, dtype=np.float64)

        if np.linalg.norm(end_point - start_point) < 1e-9:
            return

        line_mesh = self.cache.get("measure_line_mesh")
        line_actor = self.cache.get("measure_line_actor")

        if line_mesh is None or line_actor is None:

            line_mesh = pv.PolyData()
            line_mesh.points = np.array(
                [start_point, end_point],
                dtype=np.float64
            )
            line_mesh.lines = np.array(
                [2, 0, 1],
                dtype=np.int64
            )

            line_actor = self.plotter.add_mesh(
                line_mesh,
                color=(1.0, 1.0, 1.0),
                line_width=2.5,
                opacity=1.0,
                render=False,
                pickable=False,
            )

            try:
                line_actor.SetPickable(False)
            except Exception:
                pass

            self.cache["measure_line_mesh"] = line_mesh
            self.cache["measure_line_actor"] = line_actor

        else:
            try:
                line_mesh.points = np.array(
                    [start_point, end_point],
                    dtype=np.float64
                )
                line_mesh.modified()

            except Exception:
                
                self._remove_actor(line_actor)

                line_mesh = pv.PolyData()
                line_mesh.points = np.array(
                    [start_point, end_point],
                    dtype=np.float64
                )
                line_mesh.lines = np.array(
                    [2, 0, 1],
                    dtype=np.int64
                )

                line_actor = self.plotter.add_mesh(
                    line_mesh,
                    color=(1.0, 1.0, 1.0),
                    line_width=2.5,
                    opacity=1.0,
                    render=False,
                    pickable=False,
                )

                try:
                    line_actor.SetPickable(False)
                except Exception:
                    pass

                self.cache["measure_line_mesh"] = line_mesh
                self.cache["measure_line_actor"] = line_actor


    def _format_petrel_measure_info(self, start_point, end_point):
        """
        生成测距输出：
            2D: xxx [m] | Depth: xxx [m] | Lateral vector: (dx dy) [m] | Heading: xxx
        """

        if start_point is None or end_point is None:
            return None

        p0 = np.array(start_point, dtype=np.float64)
        p1 = np.array(end_point, dtype=np.float64)

        dx = float(p1[0] - p0[0])
        dy = float(p1[1] - p0[1])
        dz = float(p1[2] - p0[2])

        distance_2d = float(np.sqrt(dx * dx + dy * dy))

        
        depth = dz

        
        heading = float(np.degrees(np.arctan2(dx, dy)))

        if heading < 0:
            heading += 360.0

        info = (
            f"2D: {distance_2d:.2f} [m] | "
            f"Depth: {depth:.3f} [m] | "
            f"Lateral vector: ({dx:.1f} {dy:.1f}) [m] | "
            f"Heading: {heading:.1f}"
        )

        return info


    def _emit_measure_info(self, info_text, dynamic=False):
        """
        输出测距信息。
        
        """

        if not info_text:
            return

        self.cache["measure_last_info"] = info_text

        if dynamic:
            print("\r" + info_text, end="", flush=True)
        else:
            print("\r" + info_text)

        try:
            if hasattr(self.view, "show_measure_info"):
                self.view.show_measure_info(info_text)
            elif hasattr(self.view, "set_status_message"):
                self.view.set_status_message(info_text)
        except Exception:
            pass


    def _on_measure_left_click(self, obj, event):
        """
        鼠标左键点击：

        """

        if not self.cache.get("measure_enabled", False):
            return

        point = self._measure_pick_world_point()

        
        if point is None:
            return

        start_point = self.cache.get("measure_start_point")
        is_previewing = self.cache.get("measure_is_previewing", False)

        
        
        
        if start_point is None or not is_previewing:

            
            self._remove_actor(self.cache.get("measure_line_actor"))

            self.cache["measure_line_actor"] = None
            self.cache["measure_line_mesh"] = None
            self.cache["measure_start_point"] = point
            self.cache["measure_end_point"] = None
            self.cache["measure_is_previewing"] = True
            self.cache["measure_last_info"] = None

            print("\nMeasure start point selected. Move mouse to preview.")

            return

        
        
        
        end_point = point

        self.cache["measure_end_point"] = end_point
        self.cache["measure_is_previewing"] = False

        self._create_or_update_measure_line(
            start_point,
            end_point
        )

        info_text = self._format_petrel_measure_info(
            start_point,
            end_point
        )

        self._emit_measure_info(
            info_text,
            dynamic=False
        )

        self._render()


    def _on_measure_mouse_move(self, obj, event):
        """
        鼠标移动：

        """

        if not self.cache.get("measure_enabled", False):
            return

        if not self.cache.get("measure_is_previewing", False):
            return

        start_point = self.cache.get("measure_start_point")

        if start_point is None:
            return

        current_point = self._measure_pick_world_point()

        
        if current_point is None:
            return

        self._create_or_update_measure_line(
            start_point,
            current_point
        )

        info_text = self._format_petrel_measure_info(
            start_point,
            current_point
        )

        self._emit_measure_info(
            info_text,
            dynamic=True
        )

        self._render()


    def export_graphic(self, filepath, scale=1):
        """
        导出当前 PyVista 渲染窗口为图片
        """

        if filepath is None or str(filepath).strip() == "":
            return None

        try:
            from pathlib import Path

            filepath = Path(filepath)

            
            if filepath.suffix == "":
                filepath = filepath.with_suffix(".png")

            filepath.parent.mkdir(parents=True, exist_ok=True)

            self._render()

            self.plotter.screenshot(
                filename=str(filepath),
                scale=scale
            )

            print(f"Export graphic saved: {filepath}")

            return str(filepath)

        except Exception as exc:
            print("\n")
            print("=" * 60)
            print("ERROR IN export_graphic")
            print(exc)
            print("=" * 60)
            print("\n")
            return None



    def lock_camera_direction(self, locked: bool):
        """
        视角方向锁定

        """
        try:
            self.camera_direction_locked = bool(locked)

            if self.camera_direction_locked:
                
                self.plotter.enable_image_style()
                print("Lock camera direction: ON")
            else:
                
                self.plotter.enable_trackball_style()
                print("Lock camera direction: OFF")

            self._render()

        except Exception as exc:
            print("lock_camera_direction error:", exc)


    def toggle_camera_direction_lock(self):

        current = getattr(self, "camera_direction_locked", False)
        self.lock_camera_direction(not current)


    
    def _get_time_playback_property_config(
        self,
        property_name,
    ):
        """
        根据属性名称返回对应时间步数据、颜色条和静态场恢复配置。
        """

        property_name = str(
            property_name
        ).lower().strip()

        aliases = {
            "pressure": "pressure",
            "p": "pressure",

            "sw": "sw",
            "water_saturation": "sw",
            "water saturation": "sw",

            "porosity": "porosity",
            "phi": "porosity",

            "permeability_x": "permeability_x",
            "kx": "permeability_x",
            "perm_x": "permeability_x",

            "permeability_y": "permeability_y",
            "ky": "permeability_y",
            "perm_y": "permeability_y",

            "permeability_z": "permeability_z",
            "kz": "permeability_z",
            "perm_z": "permeability_z",
        }

        canonical_name = aliases.get(
            property_name
        )

        if canonical_name is None:
            return None

        configs = {
            "pressure": {
                "steps_attr": "pressure_steps",
                "scalar_name": "Pressure",
                "scalar_bar_title": "Pressure (bar)",
                "cmap": get_bright_jet_cmap(),
                "fixed_clim": None,
                "restore_type": "pressure",
            },

            "sw": {
                "steps_attr": "sw_steps",
                "scalar_name": "Water Saturation",
                "scalar_bar_title": "Water Saturation (-)",
                "cmap": get_bright_jet_cmap(),
                "fixed_clim": (0.0, 1.0),
                "restore_type": "sw",
            },

            "porosity": {
                "steps_attr": "porosity_steps",
                "scalar_name": "Porosity",
                "scalar_bar_title": "Porosity (-)",
                "cmap": get_bright_jet_cmap(),
                "fixed_clim": None,
                "restore_type": "porosity",
            },

            "permeability_x": {
                "steps_attr": "permeability_x_steps",
                "scalar_name": "Permeability X",
                "scalar_bar_title": "Permeability X (mD)",
                "cmap": get_bright_jet_cmap(),
                "fixed_clim": None,
                "restore_type": "permeability_x",
            },

            "permeability_y": {
                "steps_attr": "permeability_y_steps",
                "scalar_name": "Permeability Y",
                "scalar_bar_title": "Permeability Y (mD)",
                "cmap": get_bright_jet_cmap(),
                "fixed_clim": None,
                "restore_type": "permeability_y",
            },

            "permeability_z": {
                "steps_attr": "permeability_z_steps",
                "scalar_name": "Permeability Z",
                "scalar_bar_title": "Permeability Z (mD)",
                "cmap": get_bright_jet_cmap(),
                "fixed_clim": None,
                "restore_type": "permeability_z",
            },
        }

        config = dict(
            configs[canonical_name]
        )

        config["property_name"] = canonical_name

        return config


    def _clear_time_playback_cache(
        self,
        render=True,
    ):

        self._remove_actor(
            self.cache.get("time_playback_actor")
        )

        self.cache["time_playback_actor"] = None

        if self.cache.get(
            "time_playback_scalar_bar"
        ) is not None:
            try:
                self.plotter.remove_scalar_bar(
                    render=False
                )
            except Exception:
                pass

        self.cache["time_playback_scalar_bar"] = None
        self.cache["time_playback_surface"] = None
        self.cache["time_playback_source_cell_ids"] = None

        self.cache["time_playback_steps"] = None
        self.cache["time_playback_values"] = None

        self.cache["time_playback_property"] = None
        self.cache["time_playback_scalar_name"] = None
        self.cache["time_playback_scalar_bar_title"] = None

        self.cache["time_playback_mode"] = None
        self.cache["time_playback_axis"] = None
        self.cache["time_playback_layer_index"] = None

        self.cache["time_playback_current_index"] = -1
        self.cache["time_playback_clim"] = None
        self.cache["time_playback_selected_cell_ids"] = None

        if render:
            self._render()


    def has_time_playback(self):

        return (
            self.cache.get("time_playback_actor") is not None
            and self.cache.get(
                "time_playback_surface"
            ) is not None
            and self.cache.get(
                "time_playback_source_cell_ids"
            ) is not None
            and self.cache.get(
                "time_playback_steps"
            ) is not None
            and self.cache.get(
                "time_playback_values"
            ) is not None
            and self.cache.get(
                "time_playback_property"
            ) is not None
        )


    def _validate_time_playback_data(
        self,
        sim_data,
        property_name,
    ):

        config = self._get_time_playback_property_config(
            property_name
        )

        if config is None:
            raise ValueError(
                f"不支持的时间步属性：{property_name}"
            )

        cell_data = getattr(
            sim_data,
            "cell_geometry_with_pressure",
            None,
        )

        time_steps = getattr(
            sim_data,
            "time_steps",
            None,
        )

        values = getattr(
            sim_data,
            config["steps_attr"],
            None,
        )

        if cell_data is None:
            raise ValueError(
                "缺少 cell_geometry_with_pressure"
            )

        if time_steps is None:
            raise ValueError(
                "缺少 time_steps"
            )

        if values is None:
            raise ValueError(
                f"缺少 {config['steps_attr']}"
            )

        cell_data = np.asarray(
            cell_data,
            dtype=np.float32,
        )

        time_steps = np.asarray(
            time_steps,
            dtype=np.float64,
        )

        values = np.asarray(
            values,
            dtype=np.float32,
        )

        if cell_data.ndim != 2:
            raise ValueError(
                "cell_geometry_with_pressure 必须是二维数组"
            )

        if cell_data.shape[1] < 28:
            raise ValueError(
                "cell_geometry_with_pressure 列数不足，"
                "至少需要 0~27 列顶点坐标"
            )

        if time_steps.ndim != 1:
            raise ValueError(
                "time_steps 必须是一维数组"
            )

        if values.ndim != 2:
            raise ValueError(
                f"{config['steps_attr']} 必须是二维数组"
            )

        n_cells = int(
            cell_data.shape[0]
        )

        n_steps = int(
            time_steps.shape[0]
        )

        if n_cells <= 0:
            raise ValueError(
                "网格单元数量为 0"
            )

        if n_steps <= 0:
            raise ValueError(
                "时间步数量为 0"
            )

        if values.shape[0] != n_steps:
            raise ValueError(
                f"time_steps 与 "
                f"{config['steps_attr']} 的时间步数量不一致："
                f"{n_steps} != {values.shape[0]}"
            )

        if values.shape[1] != n_cells:
            raise ValueError(
                f"{config['steps_attr']} 每帧数据数量"
                "与网格单元数量不一致："
                f"{values.shape[1]} != {n_cells}"
            )

        valid_values = values[
            np.isfinite(values)
        ]

        if valid_values.size == 0:
            raise ValueError(
                f"{config['steps_attr']} 中没有有效数值"
            )

        return (
            cell_data,
            time_steps,
            values,
            config,
        )


    def _get_time_playback_layer_cell_ids(
        self,
        sim_data,
        cell_data,
        axis,
        layer_index,
    ):
        """
        按 leaf cell 的 parent_id 筛选 I / J / K 分层。
        """

        axis = str(axis).lower().strip()

        if axis not in ("i", "j", "k"):
            raise ValueError(
                f"axis 必须是 i / j / k，当前为：{axis}"
            )

        grid_info = getattr(
            sim_data,
            "grid_info",
            {},
        ) or {}

        nx = int(
            grid_info.get("nx", 0)
        )

        ny = int(
            grid_info.get("ny", 0)
        )

        nz = int(
            grid_info.get("nz", 0)
        )

        if nx <= 0 or ny <= 0 or nz <= 0:
            raise ValueError(
                "grid_info 中 nx / ny / nz 无效："
                f"nx={nx}, ny={ny}, nz={nz}"
            )

        layer_index = int(layer_index)

        if axis == "i":
            max_index = nx - 1

        elif axis == "j":
            max_index = ny - 1

        else:
            max_index = nz - 1

        if layer_index < 0 or layer_index > max_index:
            raise ValueError(
                f"{axis.upper()} 层索引无效："
                f"{layer_index}，"
                f"有效范围为 0 ~ {max_index}"
            )

        
        parent_ids = np.rint(
            cell_data[:, 1]
        ).astype(np.int64)

        parent_i = parent_ids % nx
        parent_j = (
            parent_ids // nx
        ) % ny

        parent_k = parent_ids // (
            nx * ny
        )

        if axis == "i":
            mask = parent_i == layer_index

        elif axis == "j":
            mask = parent_j == layer_index

        else:
            mask = parent_k == layer_index

        selected_cell_ids = np.flatnonzero(
            mask
        ).astype(np.int64)

        if selected_cell_ids.size == 0:
            raise ValueError(
                f"{axis.upper()}={layer_index} "
                "没有筛选到任何 leaf cell"
            )

        return selected_cell_ids


    def _build_time_playback_surface(
        self,
        cell_data,
        selected_cell_ids,
        first_frame_values,
        scalar_name,
    ):

        selected_cell_ids = np.asarray(
            selected_cell_ids,
            dtype=np.int64,
        )

        selected_rows = cell_data[
            selected_cell_ids
        ]

        n_cells = int(
            selected_rows.shape[0]
        )

        if n_cells <= 0:
            raise ValueError(
                "没有可构建的播放网格"
            )

        all_points = []
        vtk_cells = []

        point_offset = 0

        for row in selected_rows:
            points = np.asarray(
                row[4:28],
                dtype=np.float64,
            ).reshape(
                8,
                3,
            )

            all_points.append(points)

            vtk_cells.append([
                8,
                point_offset,
                point_offset + 1,
                point_offset + 2,
                point_offset + 3,
                point_offset + 4,
                point_offset + 5,
                point_offset + 6,
                point_offset + 7,
            ])

            point_offset += 8

        points_array = np.asarray(
            np.vstack(all_points),
            dtype=np.float64,
        )

        cells_array = np.hstack(
            vtk_cells
        ).astype(
            np.int64,
            copy=False,
        )

        cell_types = np.full(
            n_cells,
            pv.CellType.HEXAHEDRON,
            dtype=np.uint8,
        )

        grid = pv.UnstructuredGrid(
            cells_array,
            cell_types,
            points_array,
        )

        grid.cell_data[
            "SourceCellId"
        ] = selected_cell_ids

        grid.cell_data[
            scalar_name
        ] = first_frame_values[
            selected_cell_ids
        ]

        surface = self._build_result_property_shell_surface(
            grid
        )

        if "SourceCellId" not in surface.cell_data:
            raise RuntimeError(
                "surface 中缺少 SourceCellId，"
                "无法建立时间步数据映射"
            )

        source_cell_ids = np.asarray(
            surface.cell_data["SourceCellId"],
            dtype=np.int64,
        )

        surface.cell_data[
            scalar_name
        ] = first_frame_values[
            source_cell_ids
        ]

        if scalar_name == "Pressure":
            surface = self._prepare_exact_cell_scalar_surface(
                surface,
                scalar_name,
            )

        return surface, source_cell_ids


    def _remove_static_field_for_time_playback(
        self,
        restore_type,
    ):
        """
        删除当前属性对应的静态 actor，
        防止时间步 actor 与静态场重叠。
        """

        actor_keys_by_property = {
            "pressure": [
                "pressure_field_actor",
                "layer_pressure_actor",
            ],

            "sw": [
                "sw_field_actor",
                "layer_sw_actor",
            ],

            "porosity": [
                "phi_field_actor",
                "layer_phi_actor",
            ],

            "permeability_x": [
                "perm_field_actor",
                "layer_perm_actor",
            ],

            "permeability_y": [
                "perm_field_actor",
                "layer_perm_actor",
            ],

            "permeability_z": [
                "perm_field_actor",
                "layer_perm_actor",
            ],
        }

        scalar_bar_keys_by_property = {
            "pressure": [
                "pressure_scalar_bar",
                "layer_pressure_scalar_bar",
            ],

            "sw": [
                "sw_scalar_bar",
                "layer_sw_scalar_bar",
            ],

            "porosity": [
                "phi_scalar_bar",
                "layer_phi_scalar_bar",
            ],

            "permeability_x": [
                "perm_scalar_bar",
                "layer_perm_scalar_bar",
            ],

            "permeability_y": [
                "perm_scalar_bar",
                "layer_perm_scalar_bar",
            ],

            "permeability_z": [
                "perm_scalar_bar",
                "layer_perm_scalar_bar",
            ],
        }

        for actor_key in actor_keys_by_property.get(
            restore_type,
            [],
        ):
            self._remove_actor(
                self.cache.get(actor_key)
            )

            self.cache[actor_key] = None

        for scalar_bar_key in scalar_bar_keys_by_property.get(
            restore_type,
            [],
        ):
            if self.cache.get(
                scalar_bar_key
            ) is not None:
                try:
                    self.plotter.remove_scalar_bar(
                        render=False
                    )
                except Exception:
                    pass

            self.cache[scalar_bar_key] = None


    def _prepare_time_playback(
        self,
        sim_data,
        property_name,
        mode="full",
        axis=None,
        layer_index=None,
        start_index=0,
        show_edges=False,
    ):
        """
        时间步播放初始化入口。
        """

        mode = str(mode).lower().strip()

        if mode not in ("full", "layer"):
            print(
                f"时间步播放初始化失败：未知模式 {mode}"
            )
            return None

        try:
            (
                cell_data,
                time_steps,
                values,
                config,
            ) = self._validate_time_playback_data(
                sim_data=sim_data,
                property_name=property_name,
            )

            n_steps = int(
                time_steps.shape[0]
            )

            start_index = int(start_index)

            start_index = max(
                0,
                min(start_index, n_steps - 1),
            )

            if mode == "full":
                selected_cell_ids = np.arange(
                    cell_data.shape[0],
                    dtype=np.int64,
                )

            else:
                selected_cell_ids = (
                    self._get_time_playback_layer_cell_ids(
                        sim_data=sim_data,
                        cell_data=cell_data,
                        axis=axis,
                        layer_index=layer_index,
                    )
                )

            selected_values = values[
                :,
                selected_cell_ids,
            ]

            valid_values = selected_values[
                np.isfinite(selected_values)
            ]

            if valid_values.size == 0:
                raise ValueError(
                    "当前播放区域没有有效属性数值"
                )

            fixed_clim = config.get(
                "fixed_clim"
            )

            if fixed_clim is not None:
                value_min = float(
                    fixed_clim[0]
                )

                value_max = float(
                    fixed_clim[1]
                )

            else:
                value_min = float(
                    np.min(valid_values)
                )

                value_max = float(
                    np.max(valid_values)
                )

                if abs(
                    value_max - value_min
                ) < 1e-12:
                    value_max = value_min + 1.0

            self._clear_time_playback_cache(
                render=False
            )

            self._remove_static_field_for_time_playback(
                config["restore_type"]
            )

            first_frame = values[
                start_index
            ]

            surface, source_cell_ids = (
                self._build_time_playback_surface(
                    cell_data=cell_data,
                    selected_cell_ids=selected_cell_ids,
                    first_frame_values=first_frame,
                    scalar_name=config["scalar_name"],
                )
            )

            pressure_exact_mode = (
                config["property_name"] == "pressure"
            )

            actor = self.plotter.add_mesh(
                surface,
                scalars=config["scalar_name"],
                preference="cell",
                cmap=config["cmap"],
                clim=[value_min, value_max],
                opacity=(
                    RESULT_PRESSURE_OPACITY
                    if pressure_exact_mode
                    else RESULT_PROPERTY_OPACITY
                ),
                show_edges=bool(show_edges),
                show_scalar_bar=False,
                lighting=False,
                smooth_shading=False,
                ambient=1.0,
                diffuse=0.0,
                specular=0.0,
                interpolate_before_map=False,
                render=False,
            )

            if pressure_exact_mode:
                self._configure_exact_cell_scalar_actor(
                    actor
                )

            scalar_bar = self._replace_scalar_bar(
                "time_playback_scalar_bar",
                config["scalar_bar_title"],
                position_x=0.02,
                position_y=0.55,
                width=0.08,
                height=0.40,
                label_font_size=14,
                title_font_size=16,
                color="#2f3640",
                vertical=True,
                render=False,
            )

            self.cache[
                "time_playback_actor"
            ] = actor

            self.cache[
                "time_playback_scalar_bar"
            ] = scalar_bar

            self.cache[
                "time_playback_surface"
            ] = surface

            self.cache[
                "time_playback_source_cell_ids"
            ] = source_cell_ids

            self.cache[
                "time_playback_steps"
            ] = time_steps

            self.cache[
                "time_playback_values"
            ] = values

            self.cache[
                "time_playback_property"
            ] = config["property_name"]

            self.cache[
                "time_playback_scalar_name"
            ] = config["scalar_name"]

            self.cache[
                "time_playback_scalar_bar_title"
            ] = config["scalar_bar_title"]

            self.cache[
                "time_playback_mode"
            ] = mode

            self.cache[
                "time_playback_axis"
            ] = axis

            self.cache[
                "time_playback_layer_index"
            ] = layer_index

            self.cache[
                "time_playback_current_index"
            ] = start_index

            self.cache[
                "time_playback_clim"
            ] = (
                value_min,
                value_max,
            )

            self.cache[
                "time_playback_selected_cell_ids"
            ] = selected_cell_ids

            self._render()

            return self.get_time_playback_info()

        except Exception as exc:
            print(
                f"时间步播放初始化失败：{exc}"
            )

            self._clear_time_playback_cache(
                render=True
            )

            return None


    
    
    

    def prepare_corner_time_playback(
        self,
        sim_data,
        property_name,
        start_index=0,
        show_edges=False,
    ):
        """
        准备整体模型时间步播放。

        property_name:
            pressure
            sw
            porosity
            permeability_x
            permeability_y
            permeability_z
        """

        return self._prepare_time_playback(
            sim_data=sim_data,
            property_name=property_name,
            mode="full",
            start_index=start_index,
            show_edges=show_edges,
        )


    
    
    

    def prepare_corner_time_playback_by_layer(
        self,
        sim_data,
        property_name,
        axis,
        layer_index,
        start_index=0,
        show_edges=False,
    ):
        """
        准备 I / J / K 分层时间步播放。
        """

        return self._prepare_time_playback(
            sim_data=sim_data,
            property_name=property_name,
            mode="layer",
            axis=axis,
            layer_index=layer_index,
            start_index=start_index,
            show_edges=show_edges,
        )


    def prepare_corner_time_playback_by_layer_i(
        self,
        sim_data,
        property_name,
        i_layer,
        start_index=0,
        show_edges=False,
    ):
        return self.prepare_corner_time_playback_by_layer(
            sim_data=sim_data,
            property_name=property_name,
            axis="i",
            layer_index=i_layer,
            start_index=start_index,
            show_edges=show_edges,
        )


    def prepare_corner_time_playback_by_layer_j(
        self,
        sim_data,
        property_name,
        j_layer,
        start_index=0,
        show_edges=False,
    ):
        return self.prepare_corner_time_playback_by_layer(
            sim_data=sim_data,
            property_name=property_name,
            axis="j",
            layer_index=j_layer,
            start_index=start_index,
            show_edges=show_edges,
        )


    def prepare_corner_time_playback_by_layer_k(
        self,
        sim_data,
        property_name,
        k_layer,
        start_index=0,
        show_edges=False,
    ):
        return self.prepare_corner_time_playback_by_layer(
            sim_data=sim_data,
            property_name=property_name,
            axis="k",
            layer_index=k_layer,
            start_index=start_index,
            show_edges=show_edges,
        )


    
    
    

    def show_corner_time_step(
        self,
        step_index,
    ):
        """
        显示指定帧。
        """

        if not self.has_time_playback():
            print(
                "时间步播放尚未初始化，"
                "请先调用 prepare_corner_time_playback()"
            )
            return None

        values = self.cache.get(
            "time_playback_values"
        )

        time_steps = self.cache.get(
            "time_playback_steps"
        )

        surface = self.cache.get(
            "time_playback_surface"
        )

        source_cell_ids = self.cache.get(
            "time_playback_source_cell_ids"
        )

        scalar_name = self.cache.get(
            "time_playback_scalar_name"
        )

        if (
            values is None
            or time_steps is None
            or surface is None
            or source_cell_ids is None
            or scalar_name is None
        ):
            print(
                "时间步播放缓存不完整"
            )
            return None

        step_count = int(
            values.shape[0]
        )

        try:
            step_index = int(step_index)
        except Exception:
            print(
                f"时间步索引无效：{step_index}"
            )
            return None

        step_index = max(
            0,
            min(step_index, step_count - 1),
        )

        current_frame = values[
            step_index
        ]

        surface.cell_data[
            scalar_name
        ] = current_frame[
            source_cell_ids
        ]

        try:
            surface.modified()
        except Exception:
            try:
                surface.Modified()
            except Exception:
                pass

        self.cache[
            "time_playback_current_index"
        ] = step_index

        self._render()

        selected_cell_ids = self.cache.get(
            "time_playback_selected_cell_ids"
        )

        current_values = current_frame[
            selected_cell_ids
        ]

        current_values = current_values[
            np.isfinite(current_values)
        ]

        if current_values.size > 0:
            current_min = float(
                np.min(current_values)
            )

            current_max = float(
                np.max(current_values)
            )
        else:
            current_min = None
            current_max = None

        return {
            "index": step_index,
            "time": float(
                time_steps[step_index]
            ),
            "property": self.cache.get(
                "time_playback_property"
            ),
            "value_min": current_min,
            "value_max": current_max,
            "mode": self.cache.get(
                "time_playback_mode"
            ),
            "axis": self.cache.get(
                "time_playback_axis"
            ),
            "layer_index": self.cache.get(
                "time_playback_layer_index"
            ),
        }


    def show_next_corner_time_step(
        self,
        loop=True,
    ):
        """
        显示下一帧。
        """

        if not self.has_time_playback():
            return None

        values = self.cache.get(
            "time_playback_values"
        )

        if values is None:
            return None

        step_count = int(
            values.shape[0]
        )

        if step_count <= 0:
            return None

        current_index = int(
            self.cache.get(
                "time_playback_current_index",
                -1,
            )
        )

        next_index = current_index + 1

        if next_index >= step_count:
            next_index = (
                0
                if loop
                else step_count - 1
            )

        return self.show_corner_time_step(
            next_index
        )


    def show_previous_corner_time_step(
        self,
        loop=True,
    ):
        """
        显示上一帧。
        """

        if not self.has_time_playback():
            return None

        values = self.cache.get(
            "time_playback_values"
        )

        if values is None:
            return None

        step_count = int(
            values.shape[0]
        )

        if step_count <= 0:
            return None

        current_index = int(
            self.cache.get(
                "time_playback_current_index",
                0,
            )
        )

        previous_index = current_index - 1

        if previous_index < 0:
            previous_index = (
                step_count - 1
                if loop
                else 0
            )

        return self.show_corner_time_step(
            previous_index
        )


    
    
    

    def get_time_playback_info(self):
        """
        获取当前通用时间步播放状态。
        """

        if not self.has_time_playback():
            return {
                "ready": False,
                "property": None,
                "step_count": 0,
                "current_index": -1,
                "current_time": None,
                "first_time": None,
                "last_time": None,
                "value_min": None,
                "value_max": None,
                "mode": None,
                "axis": None,
                "layer_index": None,
                "visible_cell_count": 0,
            }

        time_steps = self.cache[
            "time_playback_steps"
        ]

        selected_cell_ids = self.cache[
            "time_playback_selected_cell_ids"
        ]

        current_index = int(
            self.cache.get(
                "time_playback_current_index",
                0,
            )
        )

        value_min, value_max = self.cache[
            "time_playback_clim"
        ]

        current_time = None

        if 0 <= current_index < len(time_steps):
            current_time = float(
                time_steps[current_index]
            )

        return {
            "ready": True,
            "property": self.cache.get(
                "time_playback_property"
            ),
            "step_count": int(
                len(time_steps)
            ),
            "current_index": current_index,
            "current_time": current_time,
            "first_time": float(
                time_steps[0]
            ),
            "last_time": float(
                time_steps[-1]
            ),
            "value_min": float(value_min),
            "value_max": float(value_max),
            "mode": self.cache.get(
                "time_playback_mode"
            ),
            "axis": self.cache.get(
                "time_playback_axis"
            ),
            "layer_index": self.cache.get(
                "time_playback_layer_index"
            ),
            "visible_cell_count": int(
                len(selected_cell_ids)
            ),
        }


    
    
    

    def clear_corner_time_playback(
        self,
        sim_data=None,
        restore_final_field=True,
    ):
        """
        停止时间步播放。

        restore_final_field=True：
            删除时间步 actor 后，
            恢复当前属性对应的静态最终结果场。
        """

        property_name = self.cache.get(
            "time_playback_property"
        )

        self._clear_time_playback_cache(
            render=False
        )

        if (
            not restore_final_field
            or sim_data is None
            or property_name is None
        ):
            self._render()
            return

        if property_name == "pressure":
            self.render_corner_pressure_field(
                sim_data
            )

        elif property_name == "sw":
            self.render_corner_sw_field(
                sim_data
            )

        elif property_name == "porosity":
            self.render_corner_phi_field(
                sim_data
            )

        elif property_name == "permeability_x":
            self.render_corner_permeability_field(
                sim_data,
                direction="x",
            )

        elif property_name == "permeability_y":
            self.render_corner_permeability_field(
                sim_data,
                direction="y",
            )

        elif property_name == "permeability_z":
            self.render_corner_permeability_field(
                sim_data,
                direction="z",
            )

        else:
            self._render()


    
    
    
    def _is_magnify_2d_view(self):
        """
        判断当前是否为 XY 平面正交俯视图。
        """

        try:
            camera = self.plotter.camera

            if not bool(
                getattr(
                    camera,
                    "parallel_projection",
                    False,
                )
            ):
                return False

            position = np.asarray(
                camera.position,
                dtype=np.float64,
            )

            focal_point = np.asarray(
                camera.focal_point,
                dtype=np.float64,
            )

            direction = focal_point - position
            length = np.linalg.norm(direction)

            if length <= 1e-12:
                return False

            direction = direction / length

            return abs(float(direction[2])) >= 0.98

        except Exception:
            return False


    def _display_to_magnify_xy(
        self,
        display_x,
        display_y,
        world_bounds,
    ):
        """
        将鼠标像素坐标转换为 XY 世界坐标。
        直接复用已有 display_to_world_xy()。
        """

        if world_bounds is None or len(world_bounds) != 6:
            return None

        try:
            point = self.display_to_world_xy(
                float(display_x),
                float(display_y),
                world_bounds,
            )

            if point is None:
                return None

            return (
                float(point[0]),
                float(point[1]),
            )

        except Exception:
            return None


    @staticmethod
    def _normalize_magnify_xy_bounds(
        start_xy,
        end_xy,
        world_bounds,
    ):

        if start_xy is None or end_xy is None:
            return None

        if world_bounds is None or len(world_bounds) != 6:
            return None

        world_xmin = float(world_bounds[0])
        world_xmax = float(world_bounds[1])
        world_ymin = float(world_bounds[2])
        world_ymax = float(world_bounds[3])

        selected_xmin = min(
            float(start_xy[0]),
            float(end_xy[0]),
        )

        selected_xmax = max(
            float(start_xy[0]),
            float(end_xy[0]),
        )

        selected_ymin = min(
            float(start_xy[1]),
            float(end_xy[1]),
        )

        selected_ymax = max(
            float(start_xy[1]),
            float(end_xy[1]),
        )

        selected_xmin = max(
            world_xmin,
            min(world_xmax, selected_xmin),
        )

        selected_xmax = max(
            world_xmin,
            min(world_xmax, selected_xmax),
        )

        selected_ymin = max(
            world_ymin,
            min(world_ymax, selected_ymin),
        )

        selected_ymax = max(
            world_ymin,
            min(world_ymax, selected_ymax),
        )

        return (
            float(selected_xmin),
            float(selected_xmax),
            float(selected_ymin),
            float(selected_ymax),
        )


    @staticmethod
    def _magnify_xy_bounds_valid(
        xy_bounds,
        min_size=1e-8,
    ):
        """
        判断框选范围是否有效。
        """

        if xy_bounds is None or len(xy_bounds) != 4:
            return False

        xmin, xmax, ymin, ymax = [
            float(value)
            for value in xy_bounds
        ]

        return (
            xmax - xmin > float(min_size)
            and ymax - ymin > float(min_size)
        )


    def _zoom_2d_camera_to_xy_bounds(
        self,
        xy_bounds,
        padding=1.05,
    ):

        if not self._is_magnify_2d_view():
            return False

        if not self._magnify_xy_bounds_valid(
            xy_bounds
        ):
            return False

        try:
            xmin = float(xy_bounds[0])
            xmax = float(xy_bounds[1])
            ymin = float(xy_bounds[2])
            ymax = float(xy_bounds[3])

            width = xmax - xmin
            height = ymax - ymin

            center_x = (xmin + xmax) * 0.5
            center_y = (ymin + ymax) * 0.5

            window_size = getattr(
                self.plotter,
                "window_size",
                None,
            )

            if (
                window_size is None
                or len(window_size) < 2
            ):
                window_width = 1.0
                window_height = 1.0

            else:
                window_width = max(
                    float(window_size[0]),
                    1.0,
                )

                window_height = max(
                    float(window_size[1]),
                    1.0,
                )

            aspect = window_width / window_height

            target_parallel_scale = max(
                height,
                width / aspect,
            )

            target_parallel_scale *= max(
                float(padding),
                1.0,
            )

            camera = self.plotter.camera

            old_position = np.asarray(
                camera.position,
                dtype=np.float64,
            )

            old_focal = np.asarray(
                camera.focal_point,
                dtype=np.float64,
            )

            old_view_up = np.asarray(
                camera.up,
                dtype=np.float64,
            )

            camera_offset = old_position - old_focal

            new_focal = np.asarray(
                [
                    center_x,
                    center_y,
                    old_focal[2],
                ],
                dtype=np.float64,
            )

            new_position = new_focal + camera_offset

            camera.parallel_projection = True

            camera.parallel_scale = max(
                float(target_parallel_scale),
                1e-8,
            )

            self.plotter.camera_position = (
                tuple(
                    float(value)
                    for value in new_position
                ),
                tuple(
                    float(value)
                    for value in new_focal
                ),
                tuple(
                    float(value)
                    for value in old_view_up
                ),
            )

            try:
                self.plotter.reset_camera_clipping_range()
            except Exception:
                pass

            self._render()

            return True

        except Exception as exc:
            print(
                "2D Magnify zoom error:",
                exc,
            )
            return False

    def activate_2d_magnify(
        self,
        sim_data,
    ):
        """
        开启二维 Magnify。

        行为：
        1. 获取模型真实坐标范围；
        2. 当前不是 XY 二维俯视图时，自动切换到全模型二维俯视图；
        3. 当前已经是 XY 二维俯视图时，保留当前放大后的相机状态；
        4. 清除旧的框选覆盖层；
        5. 进入待框选状态。
        """

        world_bounds = self.get_corner_model_bounds(
            sim_data
        )

        if world_bounds is None:
            print(
                "2D Magnify 开启失败："
                "当前模型没有有效坐标范围。"
            )
            return None

        if not self._is_magnify_2d_view():
            self.configure_selection_camera(
                world_bounds
            )

        if not self._is_magnify_2d_view():
            print(
                "2D Magnify 开启失败："
                "无法切换到 XY 二维正交视图。"
            )
            return None

        self.clear_selection_overlay()

        self.cache["magnify_2d_active"] = True
        self.cache["magnify_2d_dragging"] = False

        self.cache[
            "magnify_2d_world_bounds"
        ] = tuple(
            float(value)
            for value in world_bounds
        )

        self.cache[
            "magnify_2d_start_xy"
        ] = None

        self._render()

        return self.cache[
            "magnify_2d_world_bounds"
        ]


    def begin_2d_magnify_drag(
        self,
        display_x,
        display_y,
    ):
        """
        UI 在鼠标左键按下时调用。
        """

        if not self.cache.get(
            "magnify_2d_active",
            False,
        ):
            return False

        world_bounds = self.cache.get(
            "magnify_2d_world_bounds"
        )

        if world_bounds is None:
            return False

        start_xy = self._display_to_magnify_xy(
            display_x,
            display_y,
            world_bounds,
        )

        if start_xy is None:
            return False

        self.clear_selection_overlay()

        self.cache[
            "magnify_2d_dragging"
        ] = True

        self.cache[
            "magnify_2d_start_xy"
        ] = start_xy

        self.show_selection_preview(
            start_xy=start_xy,
            end_xy=start_xy,
            world_bounds=world_bounds,
            finalized=False,
        )

        return True


    def update_2d_magnify_drag(
        self,
        display_x,
        display_y,
    ):

        if not self.cache.get(
            "magnify_2d_active",
            False,
        ):
            return False

        if not self.cache.get(
            "magnify_2d_dragging",
            False,
        ):
            return False

        world_bounds = self.cache.get(
            "magnify_2d_world_bounds"
        )

        start_xy = self.cache.get(
            "magnify_2d_start_xy"
        )

        if world_bounds is None or start_xy is None:
            return False

        current_xy = self._display_to_magnify_xy(
            display_x,
            display_y,
            world_bounds,
        )

        if current_xy is None:
            return False

        self.show_selection_preview(
            start_xy=start_xy,
            end_xy=current_xy,
            world_bounds=world_bounds,
            finalized=False,
        )

        return True


    def finish_2d_magnify_drag(
        self,
        display_x,
        display_y,
        padding=1.05,
    ):

        if not self.cache.get(
            "magnify_2d_active",
            False,
        ):
            return False

        if not self.cache.get(
            "magnify_2d_dragging",
            False,
        ):
            return False

        world_bounds = self.cache.get(
            "magnify_2d_world_bounds"
        )

        start_xy = self.cache.get(
            "magnify_2d_start_xy"
        )

        self.cache[
            "magnify_2d_dragging"
        ] = False

        self.cache[
            "magnify_2d_start_xy"
        ] = None

        if world_bounds is None or start_xy is None:
            self.clear_selection_overlay()

            self.deactivate_2d_magnify(
                render=False,
            )

            self._render()

            return False

        end_xy = self._display_to_magnify_xy(
            display_x,
            display_y,
            world_bounds,
        )

        if end_xy is None:
            self.clear_selection_overlay()

            self.deactivate_2d_magnify(
                render=False,
            )

            self._render()

            return False

        xy_bounds = self._normalize_magnify_xy_bounds(
            start_xy=start_xy,
            end_xy=end_xy,
            world_bounds=world_bounds,
        )

        if not self._magnify_xy_bounds_valid(
            xy_bounds
        ):
            self.clear_selection_overlay()

            self.deactivate_2d_magnify(
                render=False,
            )

            self._render()

            return False

        self.show_selection_preview(
            start_xy=(
                xy_bounds[0],
                xy_bounds[2],
            ),
            end_xy=(
                xy_bounds[1],
                xy_bounds[3],
            ),
            world_bounds=world_bounds,
            finalized=True,
        )

        success = self._zoom_2d_camera_to_xy_bounds(
            xy_bounds=xy_bounds,
            padding=padding,
        )

        self.clear_selection_overlay()

        self.deactivate_2d_magnify(
            render=False,
        )

        self._render()

        return bool(success)


    def cancel_2d_magnify_drag(
        self,
        render=True,
    ):
        """
        取消当前正在进行的一次拖拽。

        仅取消当前框选，不退出 Magnify 模式。
        """

        self.cache[
            "magnify_2d_dragging"
        ] = False

        self.cache[
            "magnify_2d_start_xy"
        ] = None

        self.clear_selection_overlay()

        if render:
            self._render()


    def deactivate_2d_magnify(
        self,
        render=True,
    ):
        """
        退出 Magnify 模式。
        """

        self.cancel_2d_magnify_drag(
            render=False,
        )

        self.cache["magnify_2d_active"] = False
        self.cache["magnify_2d_dragging"] = False

        self.cache[
            "magnify_2d_world_bounds"
        ] = None

        self.cache[
            "magnify_2d_start_xy"
        ] = None

        if render:
            self._render()


    def is_2d_magnify_active(self):
        """
        查询当前是否在 Magnify 模式。
        """
        return bool(
            self.cache.get(
                "magnify_2d_active",
                False,
            )
        )








    
    
    


    def _get_k_surface_contour_property_config(
        self,
        property_name=None,
        context=None,
    ):
        """返回当前预览/模拟属性的 K 层等值线配置。"""
        if context is None:
            context = self.get_active_property_context()

        if isinstance(context, dict):
            requested = str(property_name or "").strip()
            current_name = str(context.get("property_name", "")).strip()

            if not requested or requested == current_name:
                scalar_name = str(context.get("scalar_name", "")).strip()
                if scalar_name:
                    return {
                        "column": None,
                        "scalar_name": scalar_name,
                        "title": context.get("title", current_name or scalar_name),
                        "unit": context.get("unit", ""),
                    }

        config = self._get_pick_property_config(
            property_name,
            quiet=True,
        )

        if config is None:
            print(
                "[K Surface Contour] 当前属性不存在或没有可用标量。"
            )
            return None

        return {
            "column": config.get("column"),
            "scalar_name": config.get("scalar_name"),
            "title": config.get("title", property_name),
            "unit": config.get("unit", ""),
        }


    def _get_hexahedron_top_face_ids(
        self,
        pts8,
    ):
        """
        从一个 HEXAHEDRON 的 6 个面中，
        找平均 Z 最大的面，作为这个 leaf cell 的上表面。

        返回：
            list[int]，长度为 4。
        """

        pts8 = np.asarray(
            pts8,
            dtype=np.float64,
        )

        if pts8.shape != (8, 3):
            return None

        face_table = [
            [0, 1, 2, 3],
            [4, 5, 6, 7],
            [0, 1, 5, 4],
            [1, 2, 6, 5],
            [2, 3, 7, 6],
            [3, 0, 4, 7],
        ]

        best_face_ids = None
        best_mean_z = -np.inf

        for face_ids in face_table:
            mean_z = float(
                np.mean(
                    pts8[face_ids, 2]
                )
            )

            if mean_z > best_mean_z:
                best_mean_z = mean_z
                best_face_ids = face_ids

        return best_face_ids



    def _build_k_layer_top_faces(
        self,
        sim_data=None,
        property_name=None,
        k_layer=None,
    ):
        """
        从当前属性体网格提取 K 层 leaf cell 的真实上表面。
        适用于静态预览属性和模拟结果属性。
        """
        context = self._resolve_property_operation_context(
            sim_data=sim_data,
            property_name=property_name,
        )

        if not isinstance(context, dict):
            print("[K Surface Contour] No active property field.")
            return None, None, None, None

        grid, scalar_name, values = self._context_cell_scalar_values(context)
        if (
            not self._dataset_has_cells(grid)
            or scalar_name is None
            or values is None
        ):
            return None, None, None, None

        n_cells = int(grid.n_cells)
        selected_ids = np.arange(n_cells, dtype=np.int64)

        context_axis = str(context.get("axis") or "").lower()
        context_layer = context.get("layer_index")

        if k_layer is None:
            if context_axis == "k" and context_layer is not None:
                k_layer = int(context_layer)
            else:
                k_layer = 0

        
        if not (context_axis == "k" and context_layer is not None):
            try:
                k_values = np.asarray(grid.cell_data["K"], dtype=np.int64)
            except Exception:
                k_values = None

            if k_values is not None and k_values.size == n_cells:
                target = int(k_layer)
                selected_ids = np.flatnonzero(k_values == target).astype(np.int64)

                
                if selected_ids.size == 0 and target > 0:
                    selected_ids = np.flatnonzero(
                        k_values == (target - 1)
                    ).astype(np.int64)

        if selected_ids.size == 0:
            print(f"[K Surface Contour] K={k_layer} has no cells.")
            return None, None, None, None

        face_points = []
        face_values = []
        vertex_xy = []
        vertex_values = []
        skipped_count = 0

        for cell_id in selected_ids:
            value = float(values[int(cell_id)])
            if not np.isfinite(value):
                skipped_count += 1
                continue

            try:
                cell = grid.get_cell(int(cell_id))
                pts = np.asarray(cell.points, dtype=np.float64)
            except Exception:
                skipped_count += 1
                continue

            if pts.ndim != 2 or pts.shape[0] < 8 or pts.shape[1] != 3:
                skipped_count += 1
                continue

            pts8 = pts[:8]
            if not np.isfinite(pts8).all():
                skipped_count += 1
                continue

            top_face_ids = self._get_hexahedron_top_face_ids(pts8)
            if top_face_ids is None:
                skipped_count += 1
                continue

            top4 = pts8[top_face_ids].copy()
            face_points.append(top4)
            face_values.append(value)

            for point in top4:
                vertex_xy.append([float(point[0]), float(point[1])])
                vertex_values.append(value)

        if len(face_points) < 2:
            print("[K Surface Contour] valid top faces are insufficient.")
            return None, None, None, None

        print(
            f"[K Surface Contour] source={context.get('source_mode')}, "
            f"property={context.get('property_name')}, "
            f"K={k_layer}, top_faces={len(face_points)}, "
            f"skipped={skipped_count}"
        )

        return (
            np.asarray(face_points, dtype=np.float64),
            np.asarray(face_values, dtype=np.float64),
            np.asarray(vertex_xy, dtype=np.float64),
            np.asarray(vertex_values, dtype=np.float64),
        )


    def _merge_k_surface_duplicate_xy_samples(
        self,
        xy_samples,
        value_samples,
        decimals=7,
    ):
        """
        合并相同 XY 坐标的顶点样本。

        多个 leaf cell 共用一个顶点时，
        属性值取平均，避免插值时出现重复散点。
        """

        if xy_samples is None:
            return None, None

        if value_samples is None:
            return None, None

        xy_samples = np.asarray(
            xy_samples,
            dtype=np.float64,
        )

        value_samples = np.asarray(
            value_samples,
            dtype=np.float64,
        )

        if xy_samples.shape[0] == 0:
            return None, None

        if xy_samples.shape[0] != value_samples.shape[0]:
            print(
                "[K Surface Contour] "
                "XY 样本数与属性样本数不一致。"
            )
            return None, None

        rounded_xy = np.round(
            xy_samples,
            decimals=int(decimals),
        )

        unique_xy, inverse = np.unique(
            rounded_xy,
            axis=0,
            return_inverse=True,
        )

        counts = np.bincount(
            inverse
        ).astype(
            np.float64
        )

        value_sum = np.bincount(
            inverse,
            weights=value_samples,
        )

        merged_values = value_sum / np.maximum(
            counts,
            1.0,
        )

        return (
            unique_xy.astype(
                np.float64
            ),
            merged_values.astype(
                np.float64
            ),
        )


    def _build_k_surface_projection_data(
        self,
        face_points,
    ):
        """
        为“将 contour XY 点投影回真实 top face”建立查询结构。
        """

        try:
            from scipy.spatial import cKDTree
        except Exception:
            print(
                "[K Surface Contour] 缺少 SciPy。"
                "请在 oil 环境中执行：pip install scipy"
            )
            return None

        if face_points is None:
            return None

        face_points = np.asarray(
            face_points,
            dtype=np.float64,
        )

        if (
            face_points.ndim != 3
            or face_points.shape[1:] != (4, 3)
            or face_points.shape[0] == 0
        ):
            print(
                "[K Surface Contour] "
                "face_points 格式无效。"
            )
            return None

        face_centers_xy = np.mean(
            face_points[:, :, :2],
            axis=1,
        )

        try:
            face_tree = cKDTree(
                face_centers_xy
            )
        except Exception as exc:
            print(
                "[K Surface Contour] KDTree 创建失败：",
                exc,
            )
            return None

        return {
            "face_points": face_points,
            "face_tree": face_tree,
        }


    def _get_xy_triangle_z(
        self,
        x,
        y,
        triangle,
        tolerance=1e-8,
    ):
        """
        判断 XY 点是否落在三角形的 XY 投影范围内。
        """
        triangle = np.asarray(
            triangle,
            dtype=np.float64,
        )

        if triangle.shape != (3, 3):
            return None

        x0, y0, z0 = triangle[0]
        x1, y1, z1 = triangle[1]
        x2, y2, z2 = triangle[2]

        denominator = (
            (y1 - y2) * (x0 - x2)
            + (x2 - x1) * (y0 - y2)
        )

        if abs(denominator) < 1e-15:
            return None

        w0 = (
            (y1 - y2) * (x - x2)
            + (x2 - x1) * (y - y2)
        ) / denominator

        w1 = (
            (y2 - y0) * (x - x2)
            + (x0 - x2) * (y - y2)
        ) / denominator

        w2 = 1.0 - w0 - w1

        if (
            w0 < -tolerance
            or w1 < -tolerance
            or w2 < -tolerance
        ):
            return None

        z = (
            w0 * z0
            + w1 * z1
            + w2 * z2
        )

        return float(z)


    def _project_xy_to_k_surface(
        self,
        x,
        y,
        projection_data,
        initial_candidates=24,
    ):
        """
        将一个 XY 坐标投影回当前 K 层的真实 top face。
        """
        if projection_data is None:
            return None

        face_points = projection_data.get(
            "face_points"
        )

        face_tree = projection_data.get(
            "face_tree"
        )

        if face_points is None or face_tree is None:
            return None

        n_faces = int(
            face_points.shape[0]
        )

        if n_faces == 0:
            return None

        candidate_count = min(
            max(
                1,
                int(initial_candidates),
            ),
            n_faces,
        )

        while True:
            _, face_ids = face_tree.query(
                [float(x), float(y)],
                k=candidate_count,
            )

            face_ids = np.atleast_1d(
                face_ids
            )

            best_z = None

            for face_id in face_ids:
                face = face_points[
                    int(face_id)
                ]

                z_a = self._get_xy_triangle_z(
                    x=float(x),
                    y=float(y),
                    triangle=face[[0, 1, 2]],
                )

                z_b = self._get_xy_triangle_z(
                    x=float(x),
                    y=float(y),
                    triangle=face[[0, 2, 3]],
                )

                candidate_zs = [
                    z
                    for z in (
                        z_a,
                        z_b,
                    )
                    if z is not None
                ]

                if len(candidate_zs) == 0:
                    continue

                current_z = max(
                    candidate_zs
                )

                if (
                    best_z is None
                    or current_z > best_z
                ):
                    best_z = current_z

            if best_z is not None:
                return float(best_z)

            if candidate_count >= n_faces:
                break

            candidate_count = min(
                n_faces,
                candidate_count * 2,
            )

        return None


    def _get_k_surface_grid_resolution(
        self,
        x_min,
        x_max,
        y_min,
        y_max,
        target_resolution,
    ):
        """
        按当前 K 层 XY 长宽比生成规则二维计算网格大小。
        """

        x_span = max(
            float(x_max - x_min),
            1e-12,
        )

        y_span = max(
            float(y_max - y_min),
            1e-12,
        )

        target_resolution = int(
            max(
                80,
                min(
                    int(target_resolution),
                    260,
                ),
            )
        )

        if x_span >= y_span:
            nx = target_resolution
            ny = int(
                round(
                    target_resolution
                    * y_span
                    / x_span
                )
            )
        else:
            ny = target_resolution
            nx = int(
                round(
                    target_resolution
                    * x_span
                    / y_span
                )
            )

        nx = max(
            60,
            min(nx, 260),
        )

        ny = max(
            60,
            min(ny, 260),
        )

        return int(nx), int(ny)


    def _build_k_surface_contour_compute_mesh(
        self,
        xy_samples,
        value_samples,
        projection_data,
        scalar_name,
        target_resolution=160,
    ):
        """
        建立“仅用于计算 contour”的连续二维三角网格。
        """
        try:
            from scipy.interpolate import LinearNDInterpolator
        except Exception:
            print(
                "[K Surface Contour] 缺少 SciPy。"
                "请执行：pip install scipy"
            )
            return None

        if xy_samples is None:
            return None

        if value_samples is None:
            return None

        xy_samples = np.asarray(
            xy_samples,
            dtype=np.float64,
        )

        value_samples = np.asarray(
            value_samples,
            dtype=np.float64,
        )

        if xy_samples.shape[0] < 4:
            return None

        x_min = float(
            np.min(xy_samples[:, 0])
        )

        x_max = float(
            np.max(xy_samples[:, 0])
        )

        y_min = float(
            np.min(xy_samples[:, 1])
        )

        y_max = float(
            np.max(xy_samples[:, 1])
        )

        if np.isclose(x_min, x_max):
            return None

        if np.isclose(y_min, y_max):
            return None

        nx, ny = self._get_k_surface_grid_resolution(
            x_min=x_min,
            x_max=x_max,
            y_min=y_min,
            y_max=y_max,
            target_resolution=target_resolution,
        )

        x_axis = np.linspace(
            x_min,
            x_max,
            nx,
            dtype=np.float64,
        )

        y_axis = np.linspace(
            y_min,
            y_max,
            ny,
            dtype=np.float64,
        )

        x_grid, y_grid = np.meshgrid(
            x_axis,
            y_axis,
            indexing="ij",
        )

        try:
            interpolator = LinearNDInterpolator(
                xy_samples,
                value_samples,
                fill_value=np.nan,
            )

            value_grid = interpolator(
                x_grid,
                y_grid,
            )

        except Exception as exc:
            print(
                "[K Surface Contour] 属性插值失败：",
                exc,
            )
            return None

        value_grid = np.asarray(
            value_grid,
            dtype=np.float64,
        )

        valid_mask = np.isfinite(
            value_grid
        )

        
        
        for i in range(x_grid.shape[0]):
            for j in range(x_grid.shape[1]):
                if not valid_mask[i, j]:
                    continue

                z = self._project_xy_to_k_surface(
                    x=float(x_grid[i, j]),
                    y=float(y_grid[i, j]),
                    projection_data=projection_data,
                )

                if z is None:
                    valid_mask[i, j] = False
                    value_grid[i, j] = np.nan

        point_ids = -np.ones(
            x_grid.shape,
            dtype=np.int64,
        )

        points = []
        point_values = []

        point_id = 0

        for i in range(x_grid.shape[0]):
            for j in range(x_grid.shape[1]):
                if not valid_mask[i, j]:
                    continue

                point_ids[i, j] = point_id

                points.append([
                    float(x_grid[i, j]),
                    float(y_grid[i, j]),
                    0.0,
                ])

                point_values.append(
                    float(value_grid[i, j])
                )

                point_id += 1

        if len(points) < 4:
            print(
                "[K Surface Contour] "
                "连续 contour 计算点数量不足。"
            )
            return None

        faces = []

        for i in range(
            x_grid.shape[0] - 1
        ):
            for j in range(
                x_grid.shape[1] - 1
            ):
                p00 = point_ids[i, j]
                p10 = point_ids[i + 1, j]
                p11 = point_ids[i + 1, j + 1]
                p01 = point_ids[i, j + 1]

                if (
                    p00 < 0
                    or p10 < 0
                    or p11 < 0
                    or p01 < 0
                ):
                    continue

                faces.extend([
                    3,
                    int(p00),
                    int(p10),
                    int(p11),

                    3,
                    int(p00),
                    int(p11),
                    int(p01),
                ])

        if len(faces) == 0:
            print(
                "[K Surface Contour] "
                "连续 contour 计算三角面为空。"
            )
            return None

        try:
            compute_mesh = pv.PolyData(
                np.asarray(
                    points,
                    dtype=np.float64,
                ),
                np.asarray(
                    faces,
                    dtype=np.int64,
                ),
            )

            compute_mesh.point_data[
                scalar_name
            ] = np.asarray(
                point_values,
                dtype=np.float64,
            )

            return compute_mesh

        except Exception as exc:
            print(
                "[K Surface Contour] "
                "连续 contour 计算 mesh 创建失败：",
                exc,
            )
            return None


    def _project_contour_mesh_to_k_surface(
        self,
        contour_mesh,
        projection_data,
        sim_data,
        z_offset_ratio=1e-5,
        minimum_z_offset=0.005,
    ):
        """
        把 contour 的所有点投影回真实 K 层上表面。

        最终点坐标：
            (x, y, z_top_surface + offset)
        """

        if contour_mesh is None:
            return None

        if contour_mesh.n_points == 0:
            return None

        try:
            bounds = self.get_corner_model_bounds(
                sim_data
            )
        except Exception:
            bounds = None

        if bounds is None:
            model_span = 1.0
        else:
            xmin, xmax, ymin, ymax, zmin, zmax = [
                float(value)
                for value in bounds
            ]

            model_span = max(
                abs(xmax - xmin),
                abs(ymax - ymin),
                abs(zmax - zmin),
                1.0,
            )

        z_offset = max(
            model_span * float(z_offset_ratio),
            float(minimum_z_offset),
        )

        projected_mesh = contour_mesh.copy(
            deep=True
        )

        points = np.asarray(
            projected_mesh.points,
            dtype=np.float64,
        ).copy()

        failed_count = 0

        for point_index in range(
            points.shape[0]
        ):
            x = float(points[point_index, 0])
            y = float(points[point_index, 1])

            z = self._project_xy_to_k_surface(
                x=x,
                y=y,
                projection_data=projection_data,
            )

            if z is None:
                failed_count += 1
                continue

            points[
                point_index,
                2,
            ] = float(z) + z_offset

        projected_mesh.points = points

        if failed_count > 0:
            print(
                "[K Surface Contour] "
                f"有 {failed_count} 个 contour 点没有找到 top face，"
                "已保留原始位置。"
            )

        return projected_mesh


    def _get_nice_contour_step(
        self,
        scalar_min,
        scalar_max,
        target_count=6,
    ):
        """
        计算更适合显示的等值距。
        """
        scalar_min = float(scalar_min)
        scalar_max = float(scalar_max)

        value_range = scalar_max - scalar_min

        if value_range <= 0.0:
            return None

        target_count = max(
            2,
            int(target_count),
        )

        raw_step = value_range / float(
            target_count + 1
        )

        if raw_step <= 0.0:
            return None

        exponent = np.floor(
            np.log10(raw_step)
        )

        base = 10.0 ** exponent
        normalized = raw_step / base

        if normalized <= 1.0:
            nice_value = 1.0
        elif normalized <= 2.0:
            nice_value = 2.0
        elif normalized <= 5.0:
            nice_value = 5.0
        else:
            nice_value = 10.0

        return float(
            nice_value * base
        )


    def _build_k_surface_contour_levels(
        self,
        scalar_min,
        scalar_max,
        n_levels=6,
        contour_interval=None,
        manual_levels=None,
    ):
        """
        contour levels 优先级：

        1. manual_levels
        2. contour_interval
        3. n_levels 自动生成整齐刻度
        """

        scalar_min = float(scalar_min)
        scalar_max = float(scalar_max)

        if scalar_max <= scalar_min:
            return np.empty(
                0,
                dtype=np.float64,
            )

        
        
        
        if manual_levels is not None:
            values = np.asarray(
                manual_levels,
                dtype=np.float64,
            )

            values = values[
                np.isfinite(values)
            ]

            values = values[
                (values > scalar_min)
                & (values < scalar_max)
            ]

            return np.unique(
                np.sort(values)
            )

        
        
        
        if contour_interval is not None:
            try:
                step = abs(
                    float(contour_interval)
                )
            except Exception:
                step = None

            if step is not None and step > 0.0:
                start = np.ceil(
                    scalar_min / step
                ) * step

                end = np.floor(
                    scalar_max / step
                ) * step

                values = np.arange(
                    start,
                    end + step * 0.25,
                    step,
                    dtype=np.float64,
                )

                values = values[
                    (values > scalar_min)
                    & (values < scalar_max)
                ]

                return np.unique(
                    np.round(
                        values,
                        decimals=12,
                    )
                )

        
        
        
        step = self._get_nice_contour_step(
            scalar_min=scalar_min,
            scalar_max=scalar_max,
            target_count=n_levels,
        )

        if step is None:
            return np.empty(
                0,
                dtype=np.float64,
            )

        start = np.ceil(
            scalar_min / step
        ) * step

        end = np.floor(
            scalar_max / step
        ) * step

        values = np.arange(
            start,
            end + step * 0.25,
            step,
            dtype=np.float64,
        )

        values = values[
            (values > scalar_min)
            & (values < scalar_max)
        ]

        if values.size == 0:
            count = max(
                2,
                int(n_levels),
            )

            values = np.linspace(
                scalar_min,
                scalar_max,
                count + 2,
                dtype=np.float64,
            )[1:-1]

        return np.unique(
            np.round(
                values,
                decimals=12,
            )
        )


    def _format_k_surface_contour_value(
        self,
        value,
        contour_interval=None,
    ):
        """
        根据等值距自动确定标签的小数位数。
        """

        value = float(value)

        if contour_interval is None:
            contour_interval = abs(value)

        try:
            contour_interval = abs(
                float(contour_interval)
            )
        except Exception:
            contour_interval = 1.0

        if contour_interval >= 1.0:
            decimals = 0
        elif contour_interval >= 0.1:
            decimals = 1
        elif contour_interval >= 0.01:
            decimals = 2
        elif contour_interval >= 0.001:
            decimals = 3
        else:
            decimals = 4

        text = f"{value:.{decimals}f}"

        if float(text) == 0.0:
            text = text.replace(
                "-",
                "",
            )

        return text

    
    
    
    def _iter_contour_polylines(
        self,
        line_mesh,
    ):
        """
        将 PolyData 中的 lines 解析成多个独立 polyline 点数组。
        """

        if line_mesh is None:
            return []

        if line_mesh.n_points == 0:
            return []

        lines = np.asarray(
            line_mesh.lines,
            dtype=np.int64,
        )

        if lines.size == 0:
            return []

        all_points = np.asarray(
            line_mesh.points,
            dtype=np.float64,
        )

        result = []
        cursor = 0

        while cursor < lines.size:
            point_count = int(
                lines[cursor]
            )

            cursor += 1

            if point_count < 2:
                cursor += point_count
                continue

            point_ids = lines[
                cursor:cursor + point_count
            ]

            cursor += point_count

            if point_ids.size < 2:
                continue

            points = all_points[
                point_ids
            ].copy()

            if points.shape[0] >= 2:
                result.append(points)

        return result


    def _get_polyline_length(
        self,
        points,
    ):
        """
        计算 polyline 总长度。
        """

        points = np.asarray(
            points,
            dtype=np.float64,
        )

        if points.shape[0] < 2:
            return 0.0

        segment_vectors = np.diff(
            points,
            axis=0,
        )

        segment_lengths = np.linalg.norm(
            segment_vectors,
            axis=1,
        )

        return float(
            np.sum(segment_lengths)
        )


    def _get_polyline_point_and_tangent_at_distance(
        self,
        points,
        target_distance,
    ):
        """
        根据弧长距离，从 polyline 上取一个点和该点切线方向。

        返回：
            point:   [3]
            tangent: [3]
            actual_distance
        """

        points = np.asarray(
            points,
            dtype=np.float64,
        )

        if points.shape[0] < 2:
            return None, None, None

        segment_vectors = np.diff(
            points,
            axis=0,
        )

        segment_lengths = np.linalg.norm(
            segment_vectors,
            axis=1,
        )

        total_length = float(
            np.sum(segment_lengths)
        )

        if total_length <= 1e-12:
            return None, None, None

        target_distance = float(
            np.clip(
                target_distance,
                0.0,
                total_length,
            )
        )

        accumulated = 0.0

        for index, segment_length in enumerate(
            segment_lengths
        ):
            segment_length = float(
                segment_length
            )

            next_accumulated = accumulated + segment_length

            if (
                target_distance <= next_accumulated
                or index == len(segment_lengths) - 1
            ):
                ratio = (
                    target_distance - accumulated
                ) / max(
                    segment_length,
                    1e-12,
                )

                point = (
                    points[index]
                    + ratio
                    * (
                        points[index + 1]
                        - points[index]
                    )
                )

                tangent = segment_vectors[
                    index
                ].copy()

                tangent_norm = float(
                    np.linalg.norm(tangent)
                )

                if tangent_norm <= 1e-12:
                    return point, None, target_distance

                tangent = tangent / tangent_norm

                return point, tangent, target_distance

            accumulated = next_accumulated

        return None, None, None


    def _split_polyline_with_gap(
        self,
        points,
        center_distance,
        gap_length,
    ):
        """
        在一条 polyline 的中间切出一个缺口。

        用于把 contour 数值嵌入到等值线中，而不是把文字标在线旁边。

        返回：
            [
                line_part_1,
                line_part_2,
            ]

        某一部分过短时会自动舍弃。
        """

        points = np.asarray(
            points,
            dtype=np.float64,
        )

        if points.shape[0] < 2:
            return [points]

        total_length = self._get_polyline_length(
            points
        )

        if total_length <= 1e-12:
            return [points]

        center_distance = float(
            np.clip(
                center_distance,
                0.0,
                total_length,
            )
        )

        gap_length = max(
            0.0,
            float(gap_length),
        )

        
        max_gap = total_length * 0.45

        gap_length = min(
            gap_length,
            max_gap,
        )

        if gap_length <= 1e-12:
            return [points]

        gap_start = max(
            0.0,
            center_distance - gap_length * 0.5,
        )

        gap_end = min(
            total_length,
            center_distance + gap_length * 0.5,
        )

        start_point, _, _ = (
            self._get_polyline_point_and_tangent_at_distance(
                points,
                gap_start,
            )
        )

        end_point, _, _ = (
            self._get_polyline_point_and_tangent_at_distance(
                points,
                gap_end,
            )
        )

        if start_point is None or end_point is None:
            return [points]

        segment_vectors = np.diff(
            points,
            axis=0,
        )

        segment_lengths = np.linalg.norm(
            segment_vectors,
            axis=1,
        )

        first_part = []
        second_part = []

        accumulated = 0.0

        for index, segment_length in enumerate(
            segment_lengths
        ):
            segment_length = float(
                segment_length
            )

            next_accumulated = accumulated + segment_length

            p0 = points[index]
            p1 = points[index + 1]

            
            if accumulated < gap_start:
                if len(first_part) == 0:
                    first_part.append(
                        p0.copy()
                    )

                if next_accumulated <= gap_start:
                    first_part.append(
                        p1.copy()
                    )
                else:
                    first_part.append(
                        start_point.copy()
                    )

            
            if next_accumulated > gap_end:
                if accumulated < gap_end:
                    second_part.append(
                        end_point.copy()
                    )

                second_part.append(
                    p1.copy()
                )

            accumulated = next_accumulated

        result = []

        if len(first_part) >= 2:
            result.append(
                np.asarray(
                    first_part,
                    dtype=np.float64,
                )
            )

        if len(second_part) >= 2:
            result.append(
                np.asarray(
                    second_part,
                    dtype=np.float64,
                )
            )

        return result


    def _build_polyline_mesh(
        self,
        polyline_list,
    ):
        """
        把多个独立 polyline 点序列重新组装成一个 PolyData。
        """

        valid_lines = []

        for points in polyline_list:
            if points is None:
                continue

            points = np.asarray(
                points,
                dtype=np.float64,
            )

            if points.shape[0] < 2:
                continue

            valid_lines.append(points)

        if len(valid_lines) == 0:
            return None

        all_points = []
        line_connectivity = []

        point_offset = 0

        for points in valid_lines:
            count = int(
                points.shape[0]
            )

            all_points.append(points)

            line_connectivity.append(
                count
            )

            line_connectivity.extend(
                range(
                    point_offset,
                    point_offset + count,
                )
            )

            point_offset += count

        try:
            mesh = pv.PolyData(
                np.vstack(all_points),
                lines=np.asarray(
                    line_connectivity,
                    dtype=np.int64,
                ),
            )

            return mesh

        except Exception as exc:
            print(
                "[K Surface Contour] "
                "Polyline mesh build failed:",
                exc,
            )
            return None


    def _get_surface_normal_at_xy(
        self,
        x,
        y,
        projection_data,
        initial_candidates=24,
    ):
        """
        获取指定 XY 点所在真实 top face 的法线。

        返回：
            normal: [3]
            若找不到对应面，返回 None。
        """

        if projection_data is None:
            return None

        face_points = projection_data.get(
            "face_points"
        )

        face_tree = projection_data.get(
            "face_tree"
        )

        if face_points is None or face_tree is None:
            return None

        n_faces = int(
            face_points.shape[0]
        )

        if n_faces == 0:
            return None

        candidate_count = min(
            max(
                1,
                int(initial_candidates),
            ),
            n_faces,
        )

        while True:
            _, face_ids = face_tree.query(
                [float(x), float(y)],
                k=candidate_count,
            )

            face_ids = np.atleast_1d(
                face_ids
            )

            for face_id in face_ids:
                face = face_points[
                    int(face_id)
                ]

                tri_a = face[[0, 1, 2]]
                tri_b = face[[0, 2, 3]]

                z_a = self._get_xy_triangle_z(
                    x,
                    y,
                    tri_a,
                )

                current_triangle = None

                if z_a is not None:
                    current_triangle = tri_a
                else:
                    z_b = self._get_xy_triangle_z(
                        x,
                        y,
                        tri_b,
                    )

                    if z_b is not None:
                        current_triangle = tri_b

                if current_triangle is None:
                    continue

                edge_1 = (
                    current_triangle[1]
                    - current_triangle[0]
                )

                edge_2 = (
                    current_triangle[2]
                    - current_triangle[0]
                )

                normal = np.cross(
                    edge_1,
                    edge_2,
                )

                normal_length = float(
                    np.linalg.norm(normal)
                )

                if normal_length <= 1e-12:
                    continue

                normal = normal / normal_length

                
                if normal[2] < 0.0:
                    normal = -normal

                return normal

            if candidate_count >= n_faces:
                break

            candidate_count = min(
                n_faces,
                candidate_count * 2,
            )

        return None



    def _get_model_reference_span(self, sim_data=None):
        """获取当前预览/模拟模型最大尺寸。"""
        bounds = self._active_property_bounds()

        if bounds is None and sim_data is not None:
            try:
                bounds = self.get_corner_model_bounds(sim_data)
            except Exception:
                bounds = None

        if bounds is None:
            try:
                bounds = tuple(float(v) for v in self.plotter.bounds)
            except Exception:
                bounds = None

        if bounds is None or len(bounds) != 6:
            return 1.0

        xmin, xmax, ymin, ymax, zmin, zmax = bounds
        return max(
            abs(xmax - xmin),
            abs(ymax - ymin),
            abs(zmax - zmin),
            1.0,
        )


    def _build_surface_text_mesh(
        self,
        text,
        anchor_point,
        tangent,
        surface_normal,
        text_height,
        text_lift,
    ):
        """
        创建贴在真实 K 层上表面的 3D 文本。

        文本局部坐标：
            X：沿等值线切线方向
            Y：位于上表面内、垂直于等值线
            Z：沿表面法线方向

        返回：
            text_mesh
            text_width
        """

        try:
            raw_text = pv.Text3D(
                str(text),
                depth=0.0,
            )
        except Exception as exc:
            print(
                "[K Surface Contour] "
                "pv.Text3D 创建失败：",
                exc,
            )
            return None, 0.0

        if raw_text is None:
            return None, 0.0

        if raw_text.n_points == 0:
            return None, 0.0

        raw_points = np.asarray(
            raw_text.points,
            dtype=np.float64,
        ).copy()

        xmin, xmax, ymin, ymax, zmin, zmax = raw_text.bounds

        raw_width = max(
            float(xmax - xmin),
            1e-12,
        )

        raw_height = max(
            float(ymax - ymin),
            1e-12,
        )

        text_height = max(
            float(text_height),
            1e-8,
        )

        scale = text_height / raw_height

        text_width = raw_width * scale

        
        local_center = np.array(
            [
                (xmin + xmax) * 0.5,
                (ymin + ymax) * 0.5,
                zmin,
            ],
            dtype=np.float64,
        )

        local_points = (
            raw_points - local_center
        ) * scale

        tangent = np.asarray(
            tangent,
            dtype=np.float64,
        ).copy()

        normal = np.asarray(
            surface_normal,
            dtype=np.float64,
        ).copy()

        tangent_length = float(
            np.linalg.norm(tangent)
        )

        normal_length = float(
            np.linalg.norm(normal)
        )

        if tangent_length <= 1e-12:
            return None, 0.0

        if normal_length <= 1e-12:
            return None, 0.0

        tangent = tangent / tangent_length
        normal = normal / normal_length

        
        
        
        
        if (
            tangent[0] < 0.0
            or (
                abs(tangent[0]) < 1e-10
                and tangent[1] < 0.0
            )
        ):
            tangent = -tangent

        in_plane_vertical = np.cross(
            normal,
            tangent,
        )

        vertical_length = float(
            np.linalg.norm(in_plane_vertical)
        )

        if vertical_length <= 1e-12:
            return None, 0.0

        in_plane_vertical = (
            in_plane_vertical
            / vertical_length
        )

        
        tangent = -tangent
        in_plane_vertical = -in_plane_vertical

        anchor_point = np.asarray(
            anchor_point,
            dtype=np.float64,
        )

        world_points = (
            anchor_point
            + normal * float(text_lift)
            + np.outer(
                local_points[:, 0],
                tangent,
            )
            + np.outer(
                local_points[:, 1],
                in_plane_vertical,
            )
            + np.outer(
                local_points[:, 2],
                normal,
            )
        )

        text_mesh = raw_text.copy(
            deep=True
        )

        text_mesh.points = world_points

        return text_mesh, float(text_width)


    def _prepare_one_level_contour_with_embedded_label(
        self,
        surface_line,
        contour_value,
        projection_data,
        sim_data,
        label_height_ratio=0.014,
        label_gap_padding_ratio=0.25,
        label_lift_ratio=2e-4,
        minimum_label_lift=0.01,
    ):
        """
        对单个 contour level：

        1. 找最长的 contour polyline；
        2. 在最长线上找到中部；
        3. 在该处切开一个文字宽度对应的缺口；
        4. 创建贴在真实曲面上的 3D Text3D；
        5. 返回：
        - 切开后的 contour line mesh
        - 该 level 的 text mesh
        """

        if surface_line is None:
            return None, None

        if surface_line.n_points == 0:
            return None, None

        polyline_list = self._iter_contour_polylines(
            surface_line
        )

        if len(polyline_list) == 0:
            return surface_line, None

        line_lengths = [
            self._get_polyline_length(
                points
            )
            for points in polyline_list
        ]

        longest_index = int(
            np.argmax(line_lengths)
        )

        longest_line = polyline_list[
            longest_index
        ]

        longest_length = float(
            line_lengths[longest_index]
        )

        if longest_length <= 1e-12:
            return surface_line, None

        center_distance = longest_length * 0.5

        anchor_point, tangent, _ = (
            self._get_polyline_point_and_tangent_at_distance(
                longest_line,
                center_distance,
            )
        )

        if anchor_point is None or tangent is None:
            return surface_line, None

        surface_normal = self._get_surface_normal_at_xy(
            x=float(anchor_point[0]),
            y=float(anchor_point[1]),
            projection_data=projection_data,
        )

        if surface_normal is None:
            return surface_line, None

        model_span = self._get_model_reference_span(
            sim_data
        )

        text_height = max(
            model_span * float(
                label_height_ratio
            ),
            0.5,
        )

        text_lift = max(
            model_span * float(
                label_lift_ratio
            ),
            float(minimum_label_lift),
        )

        label_text = self._format_k_surface_contour_value(
            value=float(contour_value),
            contour_interval=None,
        )

        text_mesh, text_width = self._build_surface_text_mesh(
            text=label_text,
            anchor_point=anchor_point,
            tangent=tangent,
            surface_normal=surface_normal,
            text_height=text_height,
            text_lift=text_lift,
        )

        if text_mesh is None:
            return surface_line, None

        
        gap_length = text_width * (
            1.0
            + float(
                label_gap_padding_ratio
            )
        )

        new_polyline_list = []

        for index, points in enumerate(
            polyline_list
        ):
            if index != longest_index:
                new_polyline_list.append(
                    points
                )
                continue

            cut_parts = self._split_polyline_with_gap(
                points=points,
                center_distance=center_distance,
                gap_length=gap_length,
            )

            new_polyline_list.extend(
                cut_parts
            )

        cut_line_mesh = self._build_polyline_mesh(
            new_polyline_list
        )

        if cut_line_mesh is None:
            cut_line_mesh = surface_line

        return cut_line_mesh, text_mesh


    def clear_k_layer_top_contours(
        self,
        render=True,
    ):
        """
        清除当前 K 层三维贴面等值线和嵌入式数值文字。
        """

        self._remove_actor(
            self.cache.get(
                "k_surface_contour_actor"
            )
        )

        self._remove_actor(
            self.cache.get(
                "k_surface_contour_label_actor"
            )
        )

        self.cache[
            "k_surface_contour_actor"
        ] = None

        self.cache[
            "k_surface_contour_label_actor"
        ] = None

        self.cache[
            "k_surface_contour_surface"
        ] = None

        self.cache[
            "k_surface_contour_info"
        ] = None

        if render:
            self._render()


    def set_k_layer_top_contours_visible(
        self,
        visible,
    ):
        """
        同时控制等值线和嵌入式数值文字的显示。
        """

        visible = bool(visible)

        for actor_key in (
            "k_surface_contour_actor",
            "k_surface_contour_label_actor",
        ):
            actor = self.cache.get(
                actor_key
            )

            if actor is None:
                continue

            try:
                actor.SetVisibility(
                    visible
                )
            except Exception:
                try:
                    actor.visibility = visible
                except Exception:
                    pass

        self._render()


    def render_k_layer_top_contours(
        self,
        sim_data=None,
        property_name=None,
        layer_index=None,
        n_levels=6,
        levels=None,
        contour_interval=None,
        target_resolution=160,
        line_width=1.5,
        color=(0.02, 0.02, 0.02),
        opacity=1.0,
        render_lines_as_tubes=False,
        z_offset_ratio=1e-5,
        minimum_z_offset=0.005,
        show_labels=True,
        label_height_ratio=0.014,
        label_gap_padding_ratio=0.25,
        label_text_color=(0.02, 0.02, 0.02),
    ):
        """
        在当前 K 层真实上表面绘制三维贴面等值线。
        """
        context = self._resolve_property_operation_context(
            sim_data=sim_data,
            property_name=property_name,
        )

        if not isinstance(context, dict):
            print("[K Surface Contour] No active property field.")
            return None

        sim_data = context.get("sim_data", sim_data)
        property_name = context.get("property_name", property_name)

        if layer_index is None:
            if str(context.get("axis") or "").lower() == "k":
                layer_index = context.get("layer_index")
            if layer_index is None:
                layer_index = 0

        self.clear_k_layer_top_contours(
            render=False
        )

        
        
        
        (
            face_points,
            face_values,
            vertex_xy,
            vertex_values,
        ) = self._build_k_layer_top_faces(
            sim_data=sim_data,
            property_name=property_name,
            k_layer=layer_index,
        )

        if face_points is None:
            return None

        
        
        
        projection_data = self._build_k_surface_projection_data(
            face_points=face_points
        )

        if projection_data is None:
            return None

        
        
        
        xy_samples, value_samples = (
            self._merge_k_surface_duplicate_xy_samples(
                xy_samples=vertex_xy,
                value_samples=vertex_values,
            )
        )

        if (
            xy_samples is None
            or xy_samples.shape[0] < 4
        ):
            print(
                "[K Surface Contour] "
                "有效顶点 XY 样本不足。"
            )
            return None

        config = self._get_k_surface_contour_property_config(
            property_name=property_name,
            context=context,
        )

        if config is None:
            return None

        scalar_name = config[
            "scalar_name"
        ]

        
        
        
        compute_mesh = self._build_k_surface_contour_compute_mesh(
            xy_samples=xy_samples,
            value_samples=value_samples,
            projection_data=projection_data,
            scalar_name=scalar_name,
            target_resolution=target_resolution,
        )

        if compute_mesh is None:
            print(
                "[K Surface Contour] "
                "连续 contour 计算面构建失败。"
            )
            return None

        compute_values = np.asarray(
            compute_mesh.point_data[
                scalar_name
            ],
            dtype=np.float64,
        )

        compute_values = compute_values[
            np.isfinite(compute_values)
        ]

        if compute_values.size == 0:
            print(
                "[K Surface Contour] "
                "当前层没有有效连续属性值。"
            )
            return None

        contour_min = float(
            np.min(compute_values)
        )

        contour_max = float(
            np.max(compute_values)
        )

        if np.isclose(
            contour_min,
            contour_max,
        ):
            print(
                "[K Surface Contour] "
                "当前层属性值没有变化，无法生成等值线。"
            )
            return None

        
        
        
        contour_levels = self._build_k_surface_contour_levels(
            scalar_min=contour_min,
            scalar_max=contour_max,
            n_levels=n_levels,
            contour_interval=contour_interval,
            manual_levels=levels,
        )

        if contour_levels.size == 0:
            print(
                "[K Surface Contour] "
                "没有可绘制的 contour levels。"
            )
            return None

        
        
        
        output_line_meshes = []
        output_text_meshes = []
        rendered_levels = []

        for level in contour_levels:
            try:
                flat_line = compute_mesh.contour(
                    isosurfaces=[
                        float(level)
                    ],
                    scalars=scalar_name,
                    preference="point",
                )
            except Exception as exc:
                print(
                    "[K Surface Contour] "
                    f"level={level:.6g} contour 失败：",
                    exc,
                )
                continue

            if (
                flat_line is None
                or flat_line.n_points == 0
                or flat_line.n_cells == 0
            ):
                continue

            try:
                flat_line = flat_line.strip()
            except Exception:
                pass

            surface_line = self._project_contour_mesh_to_k_surface(
                contour_mesh=flat_line,
                projection_data=projection_data,
                sim_data=sim_data,
                z_offset_ratio=z_offset_ratio,
                minimum_z_offset=minimum_z_offset,
            )

            if (
                surface_line is None
                or surface_line.n_points == 0
                or surface_line.n_cells == 0
            ):
                continue

            try:
                surface_line = surface_line.strip()
            except Exception:
                pass

            
            
            
            if not show_labels:
                output_line_meshes.append(
                    surface_line
                )

                rendered_levels.append(
                    float(level)
                )

                continue

            
            
            
            
            line_with_gap, text_mesh = (
                self._prepare_one_level_contour_with_embedded_label(
                    surface_line=surface_line,
                    contour_value=float(level),
                    projection_data=projection_data,
                    sim_data=sim_data,
                    label_height_ratio=label_height_ratio,
                    label_gap_padding_ratio=label_gap_padding_ratio,
                )
            )

            if (
                line_with_gap is not None
                and line_with_gap.n_points > 0
            ):
                output_line_meshes.append(
                    line_with_gap
                )

            if (
                text_mesh is not None
                and text_mesh.n_points > 0
            ):
                output_text_meshes.append(
                    text_mesh
                )

            rendered_levels.append(
                float(level)
            )

        if len(output_line_meshes) == 0:
            print(
                "[K Surface Contour] "
                "没有生成可见等值线。"
            )
            return None

        
        
        
        try:
            contour_mesh = pv.merge(
                output_line_meshes,
                merge_points=False,
            )
        except Exception:
            contour_mesh = output_line_meshes[0]

            for one_mesh in output_line_meshes[1:]:
                contour_mesh = contour_mesh.merge(
                    one_mesh,
                    merge_points=False,
                )

        
        
        
        text_mesh = None

        if len(output_text_meshes) > 0:
            try:
                text_mesh = pv.merge(
                    output_text_meshes,
                    merge_points=False,
                )
            except Exception:
                text_mesh = output_text_meshes[0]

                for one_mesh in output_text_meshes[1:]:
                    text_mesh = text_mesh.merge(
                        one_mesh,
                        merge_points=False,
                    )

        
        
        
        try:
            contour_actor = self.plotter.add_mesh(
                contour_mesh,
                color=color,
                opacity=float(opacity),
                line_width=max(
                    1.0,
                    float(line_width),
                ),
                lighting=False,
                render_lines_as_tubes=bool(
                    render_lines_as_tubes
                ),
                show_scalar_bar=False,
                pickable=False,
                render=False,
            )

            try:
                contour_actor.SetPickable(False)
            except Exception:
                pass

        except Exception as exc:
            print(
                "[K Surface Contour] "
                "等值线 actor 创建失败：",
                exc,
            )
            return None

        
        
        
        text_actor = None

        if (
            text_mesh is not None
            and text_mesh.n_points > 0
        ):
            try:
                text_actor = self.plotter.add_mesh(
                    text_mesh,
                    color=label_text_color,
                    opacity=1.0,
                    lighting=False,
                    show_scalar_bar=False,
                    pickable=False,
                    render=False,
                )

                try:
                    text_actor.SetPickable(False)
                except Exception:
                    pass

            except Exception as exc:
                print(
                    "[K Surface Contour] "
                    "贴面等值线文字 actor 创建失败：",
                    exc,
                )

        
        
        
        self.cache[
            "k_surface_contour_actor"
        ] = contour_actor

        self.cache[
            "k_surface_contour_label_actor"
        ] = text_actor

        self.cache[
            "k_surface_contour_surface"
        ] = contour_mesh

        self.cache[
            "k_surface_contour_info"
        ] = {
            "property_name": str(property_name),
            "source_mode": context.get("source_mode"),
            "scalar_name": context.get("scalar_name"),
            "layer_index": int(
                layer_index
            ),
            "levels": rendered_levels,
            "requested_levels": contour_levels.tolist(),
            "top_face_count": int(
                face_points.shape[0]
            ),
            "contour_points": int(
                contour_mesh.n_points
            ),
            "contour_cells": int(
                contour_mesh.n_cells
            ),
            "label_count": int(
                len(output_text_meshes)
            ),
            "target_resolution": int(
                target_resolution
            ),
        }

        print(
            "[K Surface Contour] "
            f"property={property_name}, "
            f"K={layer_index}, "
            f"rendered_levels={rendered_levels}, "
            f"labels={len(output_text_meshes)}"
        )

        self._render()

        return contour_actor



    
    
    
    
    
    
    
    
    
    
    

    def _is_valid_bounds(self, bounds):
        """
        判断 bounds 是否有效。

        bounds 格式：
        (xmin, xmax, ymin, ymax, zmin, zmax)
        """
        if bounds is None:
            return False

        try:
            if len(bounds) != 6:
                return False

            values = [float(v) for v in bounds]

            if not np.all(np.isfinite(values)):
                return False

            xmin, xmax, ymin, ymax, zmin, zmax = values

            if xmax < xmin:
                return False

            if ymax < ymin:
                return False

            if zmax < zmin:
                return False

            return True

        except Exception:
            return False


    def _merge_bounds(self, bounds_list):
        """
        合并多个 bounds，得到一个整体模型范围。
        """
        valid_bounds = [
            bounds
            for bounds in bounds_list
            if self._is_valid_bounds(bounds)
        ]

        if not valid_bounds:
            return None

        xmin = min(float(bounds[0]) for bounds in valid_bounds)
        xmax = max(float(bounds[1]) for bounds in valid_bounds)

        ymin = min(float(bounds[2]) for bounds in valid_bounds)
        ymax = max(float(bounds[3]) for bounds in valid_bounds)

        zmin = min(float(bounds[4]) for bounds in valid_bounds)
        zmax = max(float(bounds[5]) for bounds in valid_bounds)

        return (
            xmin,
            xmax,
            ymin,
            ymax,
            zmin,
            zmax,
        )


    def _get_actor_bounds(self, actor):
        """
        获取一个可见 Actor 的 bounds。

        若 actor 不可见、无效或不支持 bounds，则返回 None。
        """
        if actor is None:
            return None

        try:
            if hasattr(actor, "visibility"):
                if not bool(actor.visibility):
                    return None
        except Exception:
            pass

        try:
            if hasattr(actor, "GetVisibility"):
                if not bool(actor.GetVisibility()):
                    return None
        except Exception:
            pass

        try:
            bounds = actor.bounds

            if self._is_valid_bounds(bounds):
                return tuple(float(v) for v in bounds)

        except Exception:
            pass

        try:
            bounds = actor.GetBounds()

            if self._is_valid_bounds(bounds):
                return tuple(float(v) for v in bounds)

        except Exception:
            pass

        return None


    def _collect_visible_model_actor_bounds(self):

        ignored_key_words = [
            "scalar_bar",
            "fixed_coordinate",
            "selection_",
            "measure_",
            "cell_pick",
            "magnify",
            "contour_label",
            "contour_info",
        ]

        bounds_list = []

        for key, value in self.cache.items():
            key_lower = str(key).lower()

            if any(
                word in key_lower
                for word in ignored_key_words
            ):
                continue

            
            if isinstance(value, (list, tuple)):
                for actor in value:
                    actor_bounds = self._get_actor_bounds(actor)

                    if actor_bounds is not None:
                        bounds_list.append(actor_bounds)

                continue

            
            actor_bounds = self._get_actor_bounds(value)

            if actor_bounds is not None:
                bounds_list.append(actor_bounds)

        return bounds_list


    def _get_fit_view_bounds(self, sim_data=None):
        """
        获取 View All 应使用的整体模型范围。
        """
        candidate_bounds = []

        if sim_data is not None:
            try:
                model_bounds = self.get_corner_model_bounds(
                    sim_data
                )

                if self._is_valid_bounds(model_bounds):
                    candidate_bounds.append(model_bounds)

            except Exception:
                pass

        magnify_bounds = self.cache.get(
            "magnify_2d_world_bounds"
        )

        if self._is_valid_bounds(magnify_bounds):
            candidate_bounds.append(magnify_bounds)

        actor_bounds = self._collect_visible_model_actor_bounds()

        candidate_bounds.extend(actor_bounds)

        merged_bounds = self._merge_bounds(candidate_bounds)

        if merged_bounds is not None:
            return merged_bounds

        try:
            renderer_bounds = self.renderer.ComputeVisiblePropBounds()

            if self._is_valid_bounds(renderer_bounds):
                return tuple(
                    float(v)
                    for v in renderer_bounds
                )

        except Exception:
            pass

        return None


    def _get_render_window_aspect_ratio(self):

        width = 1
        height = 1

        try:
            render_window = self.plotter.ren_win

            if render_window is not None:
                size = render_window.GetSize()

                if size is not None and len(size) >= 2:
                    width = max(int(size[0]), 1)
                    height = max(int(size[1]), 1)

        except Exception:
            pass

        return float(width) / float(height)


    def _bounds_to_corners(self, bounds):

        xmin, xmax, ymin, ymax, zmin, zmax = [
            float(v)
            for v in bounds
        ]

        return np.asarray(
            [
                [xmin, ymin, zmin],
                [xmin, ymin, zmax],
                [xmin, ymax, zmin],
                [xmin, ymax, zmax],
                [xmax, ymin, zmin],
                [xmax, ymin, zmax],
                [xmax, ymax, zmin],
                [xmax, ymax, zmax],
            ],
            dtype=np.float64,
        )


    def _normalize_vector(self, vector, fallback=None):

        vector = np.asarray(
            vector,
            dtype=np.float64,
        )

        length = float(np.linalg.norm(vector))

        if length > 1e-12:
            return vector / length

        if fallback is None:
            return np.array(
                [0.0, 0.0, 1.0],
                dtype=np.float64,
            )

        fallback = np.asarray(
            fallback,
            dtype=np.float64,
        )

        fallback_length = float(
            np.linalg.norm(fallback)
        )

        if fallback_length > 1e-12:
            return fallback / fallback_length

        return np.array(
            [0.0, 0.0, 1.0],
            dtype=np.float64,
        )


    def _get_current_camera_basis(self):

        position, focal_point, view_up = (
            self.plotter.camera_position
        )

        position = np.asarray(
            position,
            dtype=np.float64,
        )

        focal_point = np.asarray(
            focal_point,
            dtype=np.float64,
        )

        view_up = self._normalize_vector(
            view_up,
            fallback=(0.0, 0.0, 1.0),
        )

        backward = self._normalize_vector(
            position - focal_point,
            fallback=(1.0, 1.0, 1.0),
        )

        forward = -backward

        right = np.cross(forward, view_up)

        if np.linalg.norm(right) < 1e-12:
            right = np.cross(
                forward,
                np.array([0.0, 0.0, 1.0]),
            )

        if np.linalg.norm(right) < 1e-12:
            right = np.cross(
                forward,
                np.array([0.0, 1.0, 0.0]),
            )

        right = self._normalize_vector(
            right,
            fallback=(1.0, 0.0, 0.0),
        )

        up = np.cross(right, forward)

        up = self._normalize_vector(
            up,
            fallback=view_up,
        )

        return {
            "position": position,
            "focal_point": focal_point,
            "backward": backward,
            "forward": forward,
            "right": right,
            "up": up,
        }


    def _fit_parallel_camera_to_bounds(
        self,
        bounds,
    ):

        if not self._is_valid_bounds(bounds):
            return False

        camera_basis = self._get_current_camera_basis()

        position = camera_basis["position"]
        focal_point = camera_basis["focal_point"]
        backward = camera_basis["backward"]
        right = camera_basis["right"]
        up = camera_basis["up"]

        xmin, xmax, ymin, ymax, zmin, zmax = [
            float(v)
            for v in bounds
        ]

        model_center = np.array(
            [
                (xmin + xmax) * 0.5,
                (ymin + ymax) * 0.5,
                (zmin + zmax) * 0.5,
            ],
            dtype=np.float64,
        )

        corners = self._bounds_to_corners(bounds)

        relative_corners = corners - model_center

        horizontal_extent = float(
            np.max(
                np.abs(relative_corners @ right)
            )
        )

        vertical_extent = float(
            np.max(
                np.abs(relative_corners @ up)
            )
        )

        aspect_ratio = self._get_render_window_aspect_ratio()

        required_half_height = max(
            vertical_extent,
            horizontal_extent / max(
                aspect_ratio,
                1e-12,
            ),
            1e-6,
        )

        required_half_height *= VIEW_ALL_PADDING

        old_distance = float(
            np.linalg.norm(position - focal_point)
        )

        if old_distance < 1e-6:
            dx = xmax - xmin
            dy = ymax - ymin
            dz = zmax - zmin

            old_distance = max(
                dx,
                dy,
                dz,
                1.0,
            ) * 2.0

        cam = self.plotter.camera

        new_position = model_center + backward * old_distance

        self.plotter.camera_position = (
            tuple(float(v) for v in new_position),
            tuple(float(v) for v in model_center),
            tuple(float(v) for v in up),
        )

        cam.parallel_projection = True
        cam.parallel_scale = float(required_half_height)

        try:
            self.plotter.reset_camera_clipping_range()
        except Exception:
            pass

        return True


    def _fit_perspective_camera_to_bounds(
        self,
        bounds,
    ):

        if not self._is_valid_bounds(bounds):
            return False

        camera_basis = self._get_current_camera_basis()

        backward = camera_basis["backward"]
        right = camera_basis["right"]
        up = camera_basis["up"]

        xmin, xmax, ymin, ymax, zmin, zmax = [
            float(v)
            for v in bounds
        ]

        model_center = np.array(
            [
                (xmin + xmax) * 0.5,
                (ymin + ymax) * 0.5,
                (zmin + zmax) * 0.5,
            ],
            dtype=np.float64,
        )

        corners = self._bounds_to_corners(bounds)

        cam = self.plotter.camera

        view_angle = float(
            getattr(cam, "view_angle", 30.0)
        )

        view_angle = max(
            min(view_angle, 170.0),
            1.0,
        )

        vertical_half_angle = math.radians(
            view_angle * 0.5
        )

        vertical_tangent = math.tan(
            vertical_half_angle
        )

        vertical_tangent = max(
            vertical_tangent,
            1e-6,
        )

        aspect_ratio = self._get_render_window_aspect_ratio()

        horizontal_tangent = (
            vertical_tangent
            * max(aspect_ratio, 1e-6)
        )

        required_distance = 0.0

        for corner in corners:
            relative = corner - model_center

            horizontal = abs(
                float(np.dot(relative, right))
            )

            vertical = abs(
                float(np.dot(relative, up))
            )

            depth_offset = float(
                np.dot(relative, backward)
            )

            distance_for_corner = depth_offset + max(
                horizontal / horizontal_tangent,
                vertical / vertical_tangent,
                1e-6,
            )

            required_distance = max(
                required_distance,
                distance_for_corner,
            )

        required_distance *= VIEW_ALL_PADDING

        dx = xmax - xmin
        dy = ymax - ymin
        dz = zmax - zmin

        minimum_distance = max(
            dx,
            dy,
            dz,
            1.0,
        ) * 0.1

        required_distance = max(
            required_distance,
            minimum_distance,
        )

        new_position = (
            model_center
            + backward * required_distance
        )

        self.plotter.camera_position = (
            tuple(float(v) for v in new_position),
            tuple(float(v) for v in model_center),
            tuple(float(v) for v in up),
        )

        try:
            self.plotter.reset_camera_clipping_range()
        except Exception:
            pass

        return True


    def fit_view_all(
        self,
        sim_data=None,
    ):
        """
        View All
        """
        try:
            bounds = self._get_fit_view_bounds(
                sim_data=sim_data
            )

            if not self._is_valid_bounds(bounds):
                print(
                    "[View All] 无法获取有效模型范围。"
                )
                return False

            cam = self.plotter.camera

            is_parallel = bool(
                getattr(
                    cam,
                    "parallel_projection",
                    False,
                )
            )

            if is_parallel:
                success = self._fit_parallel_camera_to_bounds(
                    bounds=bounds,
                )

            else:
                success = self._fit_perspective_camera_to_bounds(
                    bounds=bounds,
                )

            if not success:
                return False

            if self.cache.get(
                "camera_aware_coordinate_enabled",
                False,
            ):
                signature = (
                    self._get_camera_aware_coordinate_signature(
                        bounds
                    )
                )

                self.create_fixed_3d_coordinate_axes(
                    bounds=bounds,
                    approx_divisions=COORDINATE_APPROX_DIVISIONS,
                    signature=signature,
                )

            self._render()

            return True

        except Exception as exc:
            print("=" * 60)
            print("[View All] 执行失败：")
            print(type(exc).__name__, exc)
            print("=" * 60)

            return False


    def fit_view_all_3d(
        self,
        sim_data=None,
    ):
        """
        3D 窗口专用 View All。
        """
        return self.fit_view_all(
            sim_data=sim_data,
        )


    def fit_view_all_2d(
        self,
        sim_data=None,
    ):
        """
        2D 窗口专用 View All。
        """
        return self.fit_view_all(
            sim_data=sim_data,
        )




    
    
    
    
    
    
    
    
    
    # 3. 左键单击：
    #    依次加入路径点
    
    # 4. 双击左键：
    #    当前路径结束；
    #    最后一个点自动作为 End；
    #    生成沿路径、沿 Z 方向贯穿模型的竖向折线剖面。
    

    def _get_fence_section_interactor(self):

        try:
            interactor = self.plotter.iren.interactor
            if interactor is not None:
                return interactor
        except Exception:
            pass

        try:
            interactor = self.vtk_widget.iren.interactor
            if interactor is not None:
                return interactor
        except Exception:
            pass

        return None


    def _remove_fence_section_observers(self):
        """
        移除折线垂向剖面注册的鼠标事件。
        """
        observer_ids = self.cache.get(
            "fence_section_observer_ids",
            [],
        ) or []

        interactor = self._get_fence_section_interactor()

        if interactor is not None:
            for observer_id in observer_ids:
                if observer_id is None:
                    continue

                try:
                    interactor.RemoveObserver(observer_id)
                except Exception:
                    try:
                        interactor.remove_observer(observer_id)
                    except Exception:
                        pass

        self.cache["fence_section_observer_ids"] = []


    @staticmethod
    def _fence_get_actor_opacity(actor):
        """
        获取 actor 当前透明度。
        """
        if actor is None:
            return None

        try:
            return float(actor.prop.opacity)
        except Exception:
            pass

        try:
            return float(
                actor.GetProperty().GetOpacity()
            )
        except Exception:
            return None


    @staticmethod
    def _fence_set_actor_opacity(actor, opacity):
        """
        设置 actor 透明度。
        """
        if actor is None or opacity is None:
            return

        try:
            actor.prop.opacity = float(opacity)
            return
        except Exception:
            pass

        try:
            actor.GetProperty().SetOpacity(
                float(opacity)
            )
        except Exception:
            pass


    @staticmethod
    def _fence_get_actor_visible(actor):
        """
        获取 actor 可见状态。
        """
        if actor is None:
            return None

        try:
            return bool(actor.visibility)
        except Exception:
            pass

        try:
            return bool(
                actor.GetVisibility()
            )
        except Exception:
            return None


    @staticmethod
    def _fence_set_actor_visible(actor, visible):
        """
        设置 actor 可见状态。
        """
        if actor is None or visible is None:
            return

        try:
            actor.visibility = bool(visible)
            return
        except Exception:
            pass

        try:
            actor.SetVisibility(
                bool(visible)
            )
        except Exception:
            pass



    def _iter_fence_section_context_actors(self):
        """遍历剖面模式需要暂时隐藏并随后恢复的全部场景对象。"""
        property_actor_keys = (
            "pressure_actor", "pressure_field_actor", "sw_field_actor",
            "phi_field_actor", "perm_field_actor", "threshold_actor",
            "time_playback_actor", "layer_pressure_actor", "layer_sw_actor",
            "layer_phi_actor", "layer_perm_actor",
        )
        scalar_bar_keys = (
            "scalar_bar", "pressure_scalar_bar", "sw_scalar_bar",
            "phi_scalar_bar", "perm_scalar_bar", "threshold_scalar_bar",
            "time_playback_scalar_bar", "layer_pressure_scalar_bar",
            "layer_sw_scalar_bar", "layer_phi_scalar_bar",
            "layer_perm_scalar_bar",
        )
        grid_keys = (
            "grid_lines_actor", "corner_actor", "corner_surface_actor",
            "corner_lgr_parent_grid_actor", "corner_lgr_refined_grid_actor",
            "layer_coarse_grid_actor", "layer_sw_coarse_grid_actor",
            "threshold_grid_actor", "layer_phi_coarse_grid_actor",
            "layer_perm_coarse_grid_actor",
        )

        seen = set()

        def emit(actor):
            if actor is None or id(actor) in seen:
                return None
            seen.add(id(actor))
            return actor

        for key in (*property_actor_keys, *scalar_bar_keys, *grid_keys):
            value = self.cache.get(key)
            actors = value if isinstance(value, (list, tuple, set)) else (value,)
            for actor in actors:
                actor = emit(actor)
                if actor is not None:
                    yield actor

        static_preview = getattr(self, "static_property_preview", None)
        if static_preview is not None:
            for actor in (
                getattr(static_preview, "actor", None),
                getattr(static_preview, "edge_actor", None),
                getattr(static_preview, "scalar_bar_actor", None),
            ):
                actor = emit(actor)
                if actor is not None:
                    yield actor

        geometry = getattr(self, "geometry_layers", None)
        if geometry is None:
            geometry = getattr(self, "geometry_preview", None)

        if geometry is not None:
            for actor in (
                getattr(geometry, "grid_actor", None),
                getattr(geometry, "grid_edge_actor", None),
                getattr(geometry, "grid_internal_edge_actor", None),
                *(getattr(geometry, "well_actors", None) or []),
                *(getattr(geometry, "perforation_actors", None) or []),
                *(getattr(geometry, "well_label_actors", None) or []),
                *(getattr(geometry, "natural_fracture_actors", None) or []),
                *(getattr(geometry, "hydraulic_fracture_actors", None) or []),
            ):
                actor = emit(actor)
                if actor is not None:
                    yield actor


    def _set_fence_section_well_labels_hidden(self, hidden):
        """设置剖面期间井名的强制隐藏状态。"""
        geometry = getattr(self, "geometry_layers", None)
        if geometry is None:
            geometry = getattr(self, "geometry_preview", None)

        if geometry is None:
            return False

        setter = getattr(
            geometry,
            "set_well_labels_forced_hidden",
            None,
        )

        if setter is not None:
            try:
                return bool(
                    setter(
                        hidden,
                        render_now=False,
                    )
                )
            except Exception:
                pass

        for actor in getattr(geometry, "well_label_actors", None) or []:
            self._fence_set_actor_visible(
                actor,
                not bool(hidden),
            )

        return True

    def _capture_fence_section_context(self):
        """保存进入剖面前全部相关 actor 的显示状态。"""
        self._restore_fence_section_context()

        states = []

        for actor in self._iter_fence_section_context_actors():
            states.append(
                {
                    "actor": actor,
                    "opacity": self._fence_get_actor_opacity(actor),
                    "visible": self._fence_get_actor_visible(actor),
                }
            )

        self.cache["fence_section_context_actor_states"] = states
        self.cache["fence_section_context_captured"] = True
        self.cache["fence_section_context_hidden_once"] = False

    def _restore_fence_section_context(self):
        """恢复进入剖面前以及属性切换后记录的 actor 显示状态。"""
        states = self.cache.get(
            "fence_section_context_actor_states",
            [],
        ) or []

        for state in states:
            actor = state.get("actor")
            self._fence_set_actor_opacity(
                actor,
                state.get("opacity"),
            )
            self._fence_set_actor_visible(
                actor,
                state.get("visible"),
            )

        self.cache["fence_section_context_actor_states"] = []
        self.cache["fence_section_context_captured"] = False
        self.cache["fence_section_context_hidden_once"] = False
        self._set_fence_section_well_labels_hidden(False)

    def _hide_fence_section_context(self):
        """隐藏完整属性场及几何，并动态记录属性切换后新创建的 actor。"""
        if not self.cache.get(
            "fence_section_context_captured",
            False,
        ):
            self._capture_fence_section_context()

        states = self.cache.get(
            "fence_section_context_actor_states",
            [],
        ) or []
        known_ids = {
            id(state.get("actor"))
            for state in states
            if state.get("actor") is not None
        }

        self._set_fence_section_well_labels_hidden(True)

        for actor in self._iter_fence_section_context_actors():
            if id(actor) not in known_ids:
                states.append(
                    {
                        "actor": actor,
                        "opacity": self._fence_get_actor_opacity(actor),
                        "visible": self._fence_get_actor_visible(actor),
                    }
                )
                known_ids.add(id(actor))

            self._fence_set_actor_visible(
                actor,
                False,
            )

        self.cache["fence_section_context_actor_states"] = states
        self.cache["fence_section_context_hidden_once"] = True

    def _vertical_fence_section_is_active(self):
        """返回由显示模式锁定的持久任意剖面状态。"""
        points = self.cache.get("fence_section_points", []) or []
        return bool(
            self.is_fence_property_display_mode()
            and len(points) >= 2
        )

    def _ensure_vertical_fence_section_before_render(self):
        """在最终 render 前用当前属性刷新剖面并隐藏完整模型。"""
        if not self._vertical_fence_section_is_active():
            return False

        if self.cache.get("fence_section_render_guard", False):
            return False

        self.cache["fence_section_render_guard"] = True

        try:
            self._set_fence_section_well_labels_hidden(True)

            context = self._active_property_context
            if not (
                isinstance(context, dict)
                and self._dataset_has_cells(context.get("volume_grid"))
            ):
                context = self.get_active_property_context()

            pending = bool(
                self.cache.get("fence_section_pending_property_refresh", False)
            )
            current_token = self.cache.get("fence_section_context_token")
            applied_token = self.cache.get("fence_section_applied_context_token")

            if isinstance(context, dict):
                resolved_token = (
                    id(context.get("volume_grid")),
                    id(context.get("actor")),
                    str(context.get("source_mode", "")),
                    str(context.get("property_name", "")),
                    str(context.get("scalar_name", "")),
                    context.get("axis"),
                    context.get("layer_index"),
                )

                if current_token is None:
                    current_token = resolved_token
                    self.cache["fence_section_context_token"] = current_token

                if pending or applied_token != current_token:
                    refreshed = self._refresh_vertical_fence_section_for_context(
                        context,
                        render_now=False,
                    )
                    if refreshed:
                        self.cache["fence_section_applied_context_token"] = (
                            current_token
                        )
                        self.cache["fence_section_pending_property_refresh"] = False

            self._hide_fence_section_context()
            self._set_fence_section_well_labels_hidden(True)
            return True
        finally:
            self.cache["fence_section_render_guard"] = False

    def _refresh_vertical_fence_section_for_context(
        self,
        context,
        render_now=False,
    ):
        """属性切换后沿原路径用新属性重建剖面，并保持当前剖面视角。"""
        if not self._vertical_fence_section_is_active():
            return False

        if not isinstance(context, dict):
            return False

        if self.cache.get("fence_section_refreshing_property", False):
            return False

        grid = context.get("volume_grid")
        if not self._dataset_has_cells(grid):
            return False

        property_config = self._get_fence_section_property_config(
            context=context,
        )
        if property_config is None:
            return False

        _, scalar_name, values = self._context_cell_scalar_values(
            context,
            grid=grid,
        )
        if scalar_name is None or values is None:
            return False

        property_config = dict(property_config)
        property_config["scalar_name"] = scalar_name

        self.cache["fence_section_refreshing_property"] = True

        try:
            self.cache["fence_section_sim_data"] = context.get("sim_data")
            self.cache["fence_section_property"] = str(
                context.get("property_name", scalar_name)
            )
            self.cache["fence_section_scalar_name"] = scalar_name
            self.cache["fence_section_property_context"] = context
            self.cache["fence_section_property_config"] = property_config
            self.cache["fence_section_grid"] = grid

            bounds = self._get_fence_section_grid_bounds(
                sim_data=context.get("sim_data"),
                context=context,
            )
            if bounds is not None:
                self.cache["fence_section_bounds"] = tuple(
                    float(value)
                    for value in bounds
                )

            self._hide_fence_section_context()

            refreshed = self._render_vertical_fence_section(
                reset_camera=False,
                render_now=render_now,
            )

            if refreshed:
                token = self.cache.get("fence_section_context_token")
                if token is None:
                    token = (
                        id(context.get("volume_grid")),
                        id(context.get("actor")),
                        str(context.get("source_mode", "")),
                        str(context.get("property_name", "")),
                        str(context.get("scalar_name", "")),
                        context.get("axis"),
                        context.get("layer_index"),
                    )
                    self.cache["fence_section_context_token"] = token
                self.cache["fence_section_applied_context_token"] = token
                self.cache["fence_section_pending_property_refresh"] = False

            return refreshed
        finally:
            self.cache["fence_section_refreshing_property"] = False

    def refresh_vertical_fence_section_for_current_property(
        self,
        render_now=True,
    ):
        """公开入口：使用当前属性刷新已保留的任意剖面。"""
        context = self._active_property_context
        if not (
            isinstance(context, dict)
            and self._dataset_has_cells(context.get("volume_grid"))
        ):
            context = self.get_active_property_context()

        return self._refresh_vertical_fence_section_for_context(
            context,
            render_now=render_now,
        )

    def _capture_fence_section_camera_state(self):
        """
        保存点击剖面按钮前的完整相机状态。
        """
        try:
            state = self.capture_camera_state()
        except Exception:
            state = None

        self.cache[
            "fence_section_previous_camera_state"
        ] = state


    def _restore_fence_section_camera_state(self):
        """
        恢复点击剖面按钮前的视角，但不在此处单独触发 render。
        """
        state = self.cache.get(
            "fence_section_previous_camera_state"
        )

        self.cache[
            "fence_section_previous_camera_state"
        ] = None

        if not state:
            return

        try:
            position = state.get("position")
            focal_point = state.get("focal_point")
            view_up = state.get("view_up")

            if (
                position is not None
                and focal_point is not None
                and view_up is not None
            ):
                self.plotter.camera_position = (
                    position,
                    focal_point,
                    view_up,
                )

            camera = self.plotter.camera

            if "parallel_projection" in state:
                camera.parallel_projection = bool(
                    state.get("parallel_projection")
                )

            if state.get("parallel_scale") is not None:
                camera.parallel_scale = float(
                    state["parallel_scale"]
                )

            if state.get("view_angle") is not None:
                camera.view_angle = float(
                    state["view_angle"]
                )

            if state.get("clipping_range") is not None:
                camera.clipping_range = tuple(
                    state["clipping_range"]
                )

        except Exception:
            pass



    def _get_fence_section_property_config(
        self,
        property_name=None,
        context=None,
    ):
        """返回当前预览/模拟属性的任意垂向剖面配置。"""
        if context is None:
            context = self.get_active_property_context()

        if isinstance(context, dict):
            requested = str(property_name or "").strip()
            current_name = str(context.get("property_name", "")).strip()

            if not requested or requested == current_name:
                scalar_name = str(context.get("scalar_name", "")).strip()
                if scalar_name:
                    return {
                        "column": None,
                        "title": str(
                            context.get("title", current_name or scalar_name)
                        ),
                        "unit": str(context.get("unit", "") or ""),
                        "scalar_name": scalar_name,
                    }

        config = self._get_pick_property_config(
            property_name,
            quiet=True,
        )
        if config is None:
            return None

        return {
            "column": config.get("column"),
            "title": str(config.get("title", property_name)),
            "unit": str(config.get("unit", "") or ""),
            "scalar_name": str(config.get("scalar_name", property_name)),
        }



    def _get_fence_section_grid_bounds(
        self,
        sim_data=None,
        context=None,
    ):
        """返回当前预览/模拟属性体网格范围。"""
        if context is None:
            context = self._resolve_property_operation_context(
                sim_data=sim_data,
                property_name=None,
            )

        bounds = self._active_property_bounds(context)
        if bounds is not None:
            return bounds

        
        cell_data = getattr(sim_data, "cell_geometry_with_pressure", None)
        if cell_data is None:
            return None

        try:
            points = np.asarray(
                cell_data,
                dtype=np.float64,
            )[:, 4:28].reshape(-1, 3)
        except Exception:
            return None

        points = points[np.isfinite(points).all(axis=1)]
        if points.shape[0] == 0:
            return None

        return (
            float(np.min(points[:, 0])),
            float(np.max(points[:, 0])),
            float(np.min(points[:, 1])),
            float(np.max(points[:, 1])),
            float(np.min(points[:, 2])),
            float(np.max(points[:, 2])),
        )


    @staticmethod
    def _fence_safe_clim(values):

        values = np.asarray(
            values,
            dtype=np.float64,
        )

        values = values[
            np.isfinite(values)
        ]

        if values.size == 0:
            return None

        vmin = float(
            np.min(values)
        )
        vmax = float(
            np.max(values)
        )

        if abs(vmax - vmin) <= 1e-12:
            delta = (
                abs(vmin) * 0.01
                if abs(vmin) > 1e-12
                else 1.0
            )

            vmin -= delta
            vmax += delta

        return [
            vmin,
            vmax,
        ]


    def _fence_overlay_z(self):

        bounds = self.cache.get(
            "fence_section_bounds"
        )

        if bounds is None:
            return 0.0

        xmin, xmax, ymin, ymax, zmin, zmax = [
            float(value)
            for value in bounds
        ]

        span = max(
            xmax - xmin,
            ymax - ymin,
            zmax - zmin,
            1.0,
        )

        return float(
            zmax + span * 0.002
        )


    def _fence_marker_radius(self):

        bounds = self.cache.get(
            "fence_section_bounds"
        )

        if bounds is None:
            return 1.0

        xmin, xmax, ymin, ymax, zmin, zmax = [
            float(value)
            for value in bounds
        ]

        span = max(
            xmax - xmin,
            ymax - ymin,
            zmax - zmin,
            1.0,
        )

        return float(
            span * 0.004
        )


    @staticmethod
    def _fence_make_polyline(points):

        if points is None or len(points) < 2:
            return None

        point_array = np.asarray(
            points,
            dtype=np.float64,
        )

        if (
            point_array.ndim != 2
            or point_array.shape[1] != 3
        ):
            return None

        mesh = pv.PolyData()

        mesh.points = point_array

        mesh.lines = np.hstack(
            [
                np.array(
                    [len(point_array)],
                    dtype=np.int64,
                ),
                np.arange(
                    len(point_array),
                    dtype=np.int64,
                ),
            ]
        )

        return mesh


    def _clear_fence_section_preview(
        self,
        render=False,
    ):
        """
        删除鼠标移动预览线。
        """
        self._remove_actor(
            self.cache.get(
                "fence_section_preview_actor"
            )
        )

        self.cache[
            "fence_section_preview_actor"
        ] = None

        self.cache[
            "fence_section_preview_mesh"
        ] = None

        if render:
            self._render()


    def _clear_fence_section_path_overlay(
        self,
        render=False,
    ):

        self._remove_actor(
            self.cache.get(
                "fence_section_path_actor"
            )
        )

        self._remove_actor_list(
            self.cache.get(
                "fence_section_point_actors",
                [],
            )
        )

        self.cache[
            "fence_section_path_actor"
        ] = None

        self.cache[
            "fence_section_path_mesh"
        ] = None

        self.cache[
            "fence_section_point_actors"
        ] = []

        self._clear_fence_section_preview(
            render=False,
        )

        if render:
            self._render()


    def _update_fence_section_path_overlay(self):

        self._clear_fence_section_path_overlay(
            render=False,
        )

        points = self.cache.get(
            "fence_section_points",
            [],
        ) or []

        if not points:
            self._render()
            return

        z_overlay = self._fence_overlay_z()

        draw_points = [
            (
                float(point[0]),
                float(point[1]),
                float(z_overlay),
            )
            for point in points
        ]

        path_mesh = self._fence_make_polyline(
            draw_points
        )

        if path_mesh is not None:
            path_actor = self.plotter.add_mesh(
                path_mesh,
                color=(1.0, 0.82, 0.08),
                line_width=3.0,
                opacity=1.0,
                lighting=False,
                render=False,
                pickable=False,
            )

            try:
                path_actor.SetPickable(False)
            except Exception:
                pass

            self.cache[
                "fence_section_path_mesh"
            ] = path_mesh

            self.cache[
                "fence_section_path_actor"
            ] = path_actor

        marker_radius = self._fence_marker_radius()

        is_finished = bool(
            self.cache.get(
                "fence_section_finished",
                False,
            )
        )

        marker_actors = []

        for index, point in enumerate(draw_points):
            if index == 0:
                color = (
                    0.15,
                    1.00,
                    0.22,
                )

            elif (
                is_finished
                and index == len(draw_points) - 1
            ):
                color = (
                    1.00,
                    0.15,
                    0.10,
                )

            else:
                color = (
                    1.00,
                    0.82,
                    0.08,
                )

            sphere = pv.Sphere(
                radius=marker_radius,
                center=point,
                theta_resolution=16,
                phi_resolution=16,
            )

            marker_actor = self.plotter.add_mesh(
                sphere,
                color=color,
                opacity=1.0,
                lighting=False,
                render=False,
                pickable=False,
            )

            try:
                marker_actor.SetPickable(False)
            except Exception:
                pass

            marker_actors.append(
                marker_actor
            )

        self.cache[
            "fence_section_point_actors"
        ] = marker_actors

        self._render()


    def _update_fence_section_preview(
        self,
        current_point,
    ):

        self._clear_fence_section_preview(
            render=False,
        )

        points = self.cache.get(
            "fence_section_points",
            [],
        ) or []

        if not points or current_point is None:
            self._render()
            return

        z_overlay = self._fence_overlay_z()

        start = (
            float(points[-1][0]),
            float(points[-1][1]),
            float(z_overlay),
        )

        end = (
            float(current_point[0]),
            float(current_point[1]),
            float(z_overlay),
        )

        if np.linalg.norm(
            np.asarray(end)
            - np.asarray(start)
        ) <= 1e-9:
            self._render()
            return

        mesh = self._fence_make_polyline(
            [
                start,
                end,
            ]
        )

        if mesh is None:
            return

        actor = self.plotter.add_mesh(
            mesh,
            color=(0.94, 0.94, 0.94),
            line_width=1.5,
            opacity=0.85,
            lighting=False,
            render=False,
            pickable=False,
        )

        try:
            actor.SetPickable(False)
        except Exception:
            pass

        self.cache[
            "fence_section_preview_mesh"
        ] = mesh

        self.cache[
            "fence_section_preview_actor"
        ] = actor

        self._render()


    def _get_fence_section_display_point(self):

        bounds = self.cache.get(
            "fence_section_bounds"
        )

        interactor = self._get_fence_section_interactor()

        if bounds is None or interactor is None:
            return None

        try:
            display_x, display_y = (
                interactor.GetEventPosition()
            )
        except Exception:
            return None

        point = self.display_to_world_xy(
            display_x=float(display_x),
            display_y=float(display_y),
            world_bounds=bounds,
        )

        if point is None:
            return None

        xmin, xmax, ymin, ymax, zmin, zmax = [
            float(value)
            for value in bounds
        ]

        span = max(
            xmax - xmin,
            ymax - ymin,
            zmax - zmin,
            1.0,
        )

        tolerance = span * 1e-7

        px, py, _ = point

        if (
            px < xmin - tolerance
            or px > xmax + tolerance
            or py < ymin - tolerance
            or py > ymax + tolerance
        ):
            return None

        return np.asarray(
            [
                float(px),
                float(py),
                float(zmax),
            ],
            dtype=np.float64,
        )


    def _is_new_fence_section_point(
        self,
        point,
    ):

        if point is None:
            return False

        points = self.cache.get(
            "fence_section_points",
            [],
        ) or []

        if not points:
            return True

        last_point = np.asarray(
            points[-1],
            dtype=np.float64,
        )

        point = np.asarray(
            point,
            dtype=np.float64,
        )

        bounds = self.cache.get(
            "fence_section_bounds"
        )

        if bounds is None:
            return True

        xmin, xmax, ymin, ymax, zmin, zmax = [
            float(value)
            for value in bounds
        ]

        span = max(
            xmax - xmin,
            ymax - ymin,
            zmax - zmin,
            1.0,
        )

        tolerance = span * 1e-7

        distance = float(
            np.linalg.norm(
                point[:2]
                - last_point[:2]
            )
        )

        return distance > tolerance


    def _append_fence_section_point(
        self,
        point,
    ):
        """
        将一个有效 XY 控制点加入路径。
        """
        if not self._is_new_fence_section_point(
            point
        ):
            return False

        points = self.cache.get(
            "fence_section_points",
            [],
        ) or []

        points.append(
            np.asarray(
                point,
                dtype=np.float64,
            )
        )

        self.cache[
            "fence_section_points"
        ] = points

        self._clear_fence_section_preview(
            render=False,
        )

        self._update_fence_section_path_overlay()

        print(
            "[Vertical Fence Section] "
            f"point {len(points)} selected: "
            f"x={point[0]:.3f}, "
            f"y={point[1]:.3f}"
        )

        return True


    def _emit_fence_section_info(
        self,
        text,
    ):

        if not text:
            return

        self.cache[
            "fence_section_last_info"
        ] = str(text)

        print(text)

        try:
            if hasattr(
                self.view,
                "show_fence_section_info",
            ):
                self.view.show_fence_section_info(
                    text
                )

            elif hasattr(
                self.view,
                "set_status_message",
            ):
                self.view.set_status_message(
                    text
                )

        except Exception:
            pass


    def _on_fence_section_left_button_press(
        self,
        obj,
        event,
    ):

        if not self.cache.get(
            "fence_section_drawing",
            False,
        ):
            return

        interactor = self._get_fence_section_interactor()

        if interactor is None:
            return

        try:
            display_x, display_y = (
                interactor.GetEventPosition()
            )
        except Exception:
            return

        now = time.monotonic()

        previous_time = self.cache.get(
            "fence_section_last_click_time"
        )

        previous_display = self.cache.get(
            "fence_section_last_click_display"
        )

        is_double_click = False

        if (
            previous_time is not None
            and previous_display is not None
        ):
            dt = float(
                now - previous_time
            )

            dp = float(
                np.linalg.norm(
                    np.asarray(
                        [
                            display_x,
                            display_y,
                        ],
                        dtype=np.float64,
                    )
                    - np.asarray(
                        previous_display,
                        dtype=np.float64,
                    )
                )
            )

            is_double_click = (
                dt <= 0.45
                and dp <= 6.0
            )

        point = self._get_fence_section_display_point()

        if point is not None:
            self._append_fence_section_point(
                point
            )

        self.cache[
            "fence_section_last_click_time"
        ] = now

        self.cache[
            "fence_section_last_click_display"
        ] = (
            float(display_x),
            float(display_y),
        )

        if is_double_click:
            self.complete_vertical_fence_section()


    def _on_fence_section_mouse_move(
        self,
        obj,
        event,
    ):

        if not self.cache.get(
            "fence_section_drawing",
            False,
        ):
            return

        point = self._get_fence_section_display_point()

        self._update_fence_section_preview(
            point
        )


    def _clip_fence_section_half_space(
        self,
        dataset,
        normal,
        origin,
        keep_positive,
    ):

        if dataset is None:
            return None

        try:
            if dataset.n_points == 0:
                return None
        except Exception:
            return None

        normal = np.asarray(
            normal,
            dtype=np.float64,
        )

        origin = np.asarray(
            origin,
            dtype=np.float64,
        )

        candidates = []

        for invert in (
            False,
            True,
        ):
            try:
                clipped = dataset.clip(
                    normal=normal.tolist(),
                    origin=origin.tolist(),
                    invert=bool(invert),
                )
            except Exception:
                continue

            if clipped is None:
                continue

            try:
                if clipped.n_points == 0:
                    continue

                points = np.asarray(
                    clipped.points,
                    dtype=np.float64,
                )
            except Exception:
                continue

            projection = (
                points
                - origin.reshape(1, 3)
            ) @ normal

            if projection.size == 0:
                continue

            if keep_positive:
                violation = max(
                    0.0,
                    -float(
                        np.min(projection)
                    ),
                )
            else:
                violation = max(
                    0.0,
                    float(
                        np.max(projection)
                    ),
                )

            try:
                cell_count = int(
                    clipped.n_cells
                )
            except Exception:
                cell_count = 0

            candidates.append(
                (
                    float(violation),
                    -cell_count,
                    clipped,
                )
            )

        if not candidates:
            return None

        candidates.sort(
            key=lambda item: (
                item[0],
                item[1],
            )
        )

        return candidates[0][2]


    def _slice_grid_on_fence_segment(
        self,
        grid,
        start_point,
        end_point,
    ):

        if grid is None:
            return None

        start = np.asarray(
            start_point,
            dtype=np.float64,
        ).copy()

        end = np.asarray(
            end_point,
            dtype=np.float64,
        ).copy()

        
        start[2] = 0.0
        end[2] = 0.0

        vector = end - start

        length = float(
            np.linalg.norm(
                vector[:2]
            )
        )

        if length <= 1e-9:
            return None

        tangent = np.asarray(
            [
                vector[0] / length,
                vector[1] / length,
                0.0,
            ],
            dtype=np.float64,
        )

        
        
        plane_normal = np.asarray(
            [
                -tangent[1],
                tangent[0],
                0.0,
            ],
            dtype=np.float64,
        )

        bounds = self.cache.get(
            "fence_section_bounds"
        )

        if bounds is None:
            return None

        zmid = (
            float(bounds[4])
            + float(bounds[5])
        ) * 0.5

        plane_origin = np.asarray(
            [
                (start[0] + end[0]) * 0.5,
                (start[1] + end[1]) * 0.5,
                zmid,
            ],
            dtype=np.float64,
        )

        try:
            section = grid.slice(
                normal=plane_normal.tolist(),
                origin=plane_origin.tolist(),
            )
        except Exception as exc:
            print(
                "[Vertical Fence Section] "
                "slice failed:",
                exc,
            )
            return None

        if section is None:
            return None

        try:
            if section.n_points == 0:
                return None
        except Exception:
            return None

        
        
        start_origin = np.asarray(
            [
                start[0],
                start[1],
                zmid,
            ],
            dtype=np.float64,
        )

        section = self._clip_fence_section_half_space(
            dataset=section,
            normal=tangent,
            origin=start_origin,
            keep_positive=True,
        )

        if section is None:
            return None

        
        
        end_origin = np.asarray(
            [
                end[0],
                end[1],
                zmid,
            ],
            dtype=np.float64,
        )

        section = self._clip_fence_section_half_space(
            dataset=section,
            normal=tangent,
            origin=end_origin,
            keep_positive=False,
        )

        if section is None:
            return None

        try:
            if (
                section.n_points == 0
                or section.n_cells == 0
            ):
                return None
        except Exception:
            return None

        return section


    @staticmethod
    def _merge_fence_section_blocks(
        blocks,
    ):
        """
        合并多个线段的切片结果。
        """
        valid_blocks = []

        for block in blocks:
            if block is None:
                continue

            try:
                if (
                    block.n_points == 0
                    or block.n_cells == 0
                ):
                    continue
            except Exception:
                continue

            valid_blocks.append(
                block
            )

        if not valid_blocks:
            return None

        merged = valid_blocks[0]

        for block in valid_blocks[1:]:
            try:
                merged = merged.merge(
                    block,
                    merge_points=False,
                )
            except TypeError:
                try:
                    merged = merged.merge(
                        block
                    )
                except Exception:
                    pass
            except Exception:
                pass

        return merged



    def _get_fence_section_scalar_preference(
        self,
        dataset,
        property_config,
        sim_data=None,
        source_grid=None,
    ):
        if dataset is None or property_config is None:
            return None

        scalar_name = str(property_config.get("scalar_name", ""))

        try:
            if scalar_name in dataset.cell_data:
                return "cell"
        except Exception:
            pass

        try:
            if scalar_name in dataset.point_data:
                return "point"
        except Exception:
            pass

        if not self._dataset_has_cells(source_grid):
            return None

        try:
            source_values = np.asarray(
                source_grid.cell_data[scalar_name],
                dtype=np.float32,
            )
        except Exception:
            return None

        original_ids = None
        for id_name in (
            "OriginalRowIndex",
            "SourceCellId",
            "vtkOriginalCellIds",
            "vtkOriginalCellIds_",
        ):
            try:
                if id_name in dataset.cell_data:
                    original_ids = np.asarray(
                        dataset.cell_data[id_name],
                        dtype=np.int64,
                    ).reshape(-1)
                    break
            except Exception:
                continue

        if original_ids is None or original_ids.size != int(dataset.n_cells):
            return None

        valid = (
            (original_ids >= 0)
            & (original_ids < source_values.size)
        )
        if not np.all(valid):
            return None

        dataset.cell_data[scalar_name] = source_values[original_ids]
        return "cell"


    def _clear_fence_section_scalar_bar(self):

        title = self.cache.get(
            "fence_section_scalar_bar_title"
        )

        if title:
            try:
                self.plotter.remove_scalar_bar(
                    title=title,
                    render=False,
                )
            except Exception:
                pass

        actor = self.cache.get(
            "fence_section_scalar_bar"
        )

        if actor is not None:
            try:
                actor.SetVisibility(False)
            except Exception:
                try:
                    actor.visibility = False
                except Exception:
                    pass

        self.cache[
            "fence_section_scalar_bar"
        ] = None

        self.cache[
            "fence_section_scalar_bar_title"
        ] = None


    def _add_fence_section_scalar_bar(
        self,
        mesh_actor,
        property_config,
    ):
        """
        添加剖面专用颜色条。
        """
        self._clear_fence_section_scalar_bar()

        title = property_config.get(
            "title",
            "Property",
        )

        unit = property_config.get(
            "unit",
            "",
        )

        if unit:
            bar_title = (
                f"Section: {title} ({unit})"
            )
        else:
            bar_title = (
                f"Section: {title}"
            )

        scalar_bar = None

        kwargs = {
            "title": bar_title,

            
            "position_x": 0.02,
            "position_y": 0.55,
            "width": 0.08,
            "height": 0.40,

            "label_font_size": 14,
            "title_font_size": 16,
            "color": "#2f3640",
            "vertical": True,
            "render": False,
        }
        try:
            mapper = getattr(
                mesh_actor,
                "mapper",
                None,
            )

            if mapper is not None:
                scalar_bar = self.plotter.add_scalar_bar(
                    mapper=mapper,
                    **kwargs,
                )
            else:
                scalar_bar = self.plotter.add_scalar_bar(
                    **kwargs,
                )

        except TypeError:
            try:
                scalar_bar = self.plotter.add_scalar_bar(
                    **kwargs,
                )
            except Exception:
                scalar_bar = None

        except Exception:
            scalar_bar = None

        self.cache[
            "fence_section_scalar_bar"
        ] = scalar_bar

        self.cache[
            "fence_section_scalar_bar_title"
        ] = bar_title


    def _set_fence_section_result_camera(self):

        points = self.cache.get(
            "fence_section_points",
            [],
        ) or []

        bounds = self.cache.get(
            "fence_section_bounds"
        )

        if len(points) < 2 or bounds is None:
            return

        valid_segments = []

        for start, end in zip(
            points[:-1],
            points[1:],
        ):
            vector = (
                np.asarray(
                    end,
                    dtype=np.float64,
                )
                - np.asarray(
                    start,
                    dtype=np.float64,
                )
            )

            length = float(
                np.linalg.norm(
                    vector[:2]
                )
            )

            if length > 1e-9:
                valid_segments.append(
                    (
                        length,
                        vector,
                    )
                )

        if not valid_segments:
            return

        
        
        _, main_vector = max(
            valid_segments,
            key=lambda item: item[0],
        )

        tangent = main_vector[:2] / np.linalg.norm(
            main_vector[:2]
        )

        side_normal = np.asarray(
            [
                -tangent[1],
                tangent[0],
                0.0,
            ],
            dtype=np.float64,
        )

        points_xy = np.asarray(
            [
                [
                    point[0],
                    point[1],
                ]
                for point in points
            ],
            dtype=np.float64,
        )

        center_xy = np.mean(
            points_xy,
            axis=0,
        )

        xmin, xmax, ymin, ymax, zmin, zmax = [
            float(value)
            for value in bounds
        ]

        zmid = (
            zmin + zmax
        ) * 0.5

        span = max(
            xmax - xmin,
            ymax - ymin,
            zmax - zmin,
            1.0,
        )

        distance = span * 2.2

        camera_position = (
            float(
                center_xy[0]
                + side_normal[0] * distance
            ),
            float(
                center_xy[1]
                + side_normal[1] * distance
            ),
            float(
                zmid + span * 0.65
            ),
        )

        focal_point = (
            float(center_xy[0]),
            float(center_xy[1]),
            float(zmid),
        )

        try:
            camera = self.plotter.camera

            camera.parallel_projection = True

            camera.parallel_scale = max(
                zmax - zmin,
                span * 0.80,
            )

            self.plotter.camera_position = (
                camera_position,
                focal_point,
                (0.0, 0.0, 1.0),
            )

            self.plotter.reset_camera_clipping_range()

        except Exception:
            pass



    def _render_vertical_fence_section(
        self,
        reset_camera=True,
        render_now=True,
    ):
        self._set_fence_section_well_labels_hidden(True)
        context = self.cache.get("fence_section_property_context")
        points = self.cache.get("fence_section_points", []) or []

        if not isinstance(context, dict):
            self._emit_fence_section_info(
                "[Vertical Fence Section] no active property context."
            )
            return False

        if len(points) < 2:
            self._emit_fence_section_info(
                "[Vertical Fence Section] at least two points are required."
            )
            return False

        property_config = self.cache.get("fence_section_property_config")
        if not isinstance(property_config, dict):
            property_config = self._get_fence_section_property_config(
                context=context
            )

        if property_config is None:
            return False

        grid = self.cache.get("fence_section_grid")
        if not self._dataset_has_cells(grid):
            grid = context.get("volume_grid")
            self.cache["fence_section_grid"] = grid

        if not self._dataset_has_cells(grid):
            self._emit_fence_section_info(
                "[Vertical Fence Section] active property grid is unavailable."
            )
            return False

        source_grid, scalar_name, source_values = self._context_cell_scalar_values(
            context,
            grid=grid,
        )
        if scalar_name is None or source_values is None:
            self._emit_fence_section_info(
                "[Vertical Fence Section] active scalar is unavailable."
            )
            return False

        section_blocks = []
        for start_point, end_point in zip(points[:-1], points[1:]):
            section = self._slice_grid_on_fence_segment(
                grid=source_grid,
                start_point=start_point,
                end_point=end_point,
            )
            if section is not None:
                section_blocks.append(section)

        merged_section = self._merge_fence_section_blocks(section_blocks)
        if merged_section is None:
            self._emit_fence_section_info(
                "[Vertical Fence Section] the selected path does not intersect any grid cell."
            )
            return False

        property_config = dict(property_config)
        property_config["scalar_name"] = scalar_name

        scalar_preference = self._get_fence_section_scalar_preference(
            dataset=merged_section,
            property_config=property_config,
            sim_data=context.get("sim_data"),
            source_grid=source_grid,
        )
        if scalar_preference is None:
            self._emit_fence_section_info(
                "[Vertical Fence Section] property data was not preserved by the slice."
            )
            return False

        clim = self._fence_safe_clim(source_values)
        if clim is None:
            self._emit_fence_section_info(
                "[Vertical Fence Section] all property values are invalid."
            )
            return False

        self._remove_actor(self.cache.get("fence_section_actor"))
        self.cache["fence_section_actor"] = None
        self.cache["fence_section_data"] = None
        self._clear_fence_section_scalar_bar()

        kwargs = dict(
            scalars=scalar_name,
            preference=scalar_preference,
            cmap=get_bright_jet_cmap(),
            clim=clim,
            opacity=1.0,
            show_edges=True,
            edge_color=(0.10, 0.10, 0.10),
            line_width=0.7,
            show_scalar_bar=False,
            lighting=False,
            smooth_shading=False,
            interpolate_before_map=False,
            reset_camera=False,
            render=False,
            pickable=False,
        )

        try:
            actor = self.plotter.add_mesh(merged_section, **kwargs)
        except TypeError:
            kwargs.pop("preference", None)
            kwargs.pop("pickable", None)
            kwargs.pop("reset_camera", None)
            actor = self.plotter.add_mesh(merged_section, **kwargs)
        except Exception as exc:
            self._emit_fence_section_info(
                f"[Vertical Fence Section] render failed: {type(exc).__name__}: {exc}"
            )
            return False

        try:
            actor.SetPickable(False)
        except Exception:
            pass

        self.cache["fence_section_actor"] = actor
        self.cache["fence_section_data"] = merged_section
        self.cache["fence_section_scalar_name"] = scalar_name

        self._add_fence_section_scalar_bar(
            mesh_actor=actor,
            property_config=property_config,
        )

        self._hide_fence_section_context()

        if reset_camera:
            self._set_fence_section_result_camera()

        self._set_fence_section_well_labels_hidden(True)
        self._hide_fence_section_context()

        context_token = (
            id(context.get("volume_grid")),
            id(context.get("actor")),
            str(context.get("source_mode", "")),
            str(context.get("property_name", "")),
            str(context.get("scalar_name", "")),
            context.get("axis"),
            context.get("layer_index"),
        )
        self.cache["fence_section_context_token"] = context_token
        self.cache["fence_section_applied_context_token"] = context_token
        self.cache["fence_section_pending_property_refresh"] = False

        self._emit_fence_section_info(
            "[Vertical Fence Section] "
            f"completed: points={len(points)}, "
            f"segments={len(section_blocks)}, "
            f"source={context.get('source_mode')}, "
            f"property={property_config['title']}."
        )
        if render_now:
            self._render()
        return True



    def enable_vertical_fence_section(
        self,
        sim_data=None,
        property_name=None,
    ):
        """对当前预览/模拟属性开启折线垂向剖面。"""
        context = self._resolve_property_operation_context(
            sim_data=sim_data,
            property_name=property_name,
        )

        if not isinstance(context, dict):
            self._emit_fence_section_info(
                "[Vertical Fence Section] no active property field."
            )
            return False

        property_config = self._get_fence_section_property_config(
            property_name=property_name,
            context=context,
        )
        if property_config is None:
            return False

        grid = context.get("volume_grid")
        if not self._dataset_has_cells(grid):
            self._emit_fence_section_info(
                "[Vertical Fence Section] active property grid is unavailable."
            )
            return False

        _, scalar_name, values = self._context_cell_scalar_values(
            context,
            grid=grid,
        )
        if scalar_name is None or values is None:
            self._emit_fence_section_info(
                "[Vertical Fence Section] active property scalar is unavailable."
            )
            return False

        property_config = dict(property_config)
        property_config["scalar_name"] = scalar_name

        
        self.disable_cell_info_picking(
            clear_highlight=False,
            render_now=False,
        )
        self.disable_petrel_distance_measure(clear_line=False)
        self.deactivate_2d_magnify(render=False)

        self.disable_vertical_fence_section(
            clear_result=True,
            render=False,
            force_clear=True,
        )

        bounds = self._get_fence_section_grid_bounds(
            sim_data=context.get("sim_data", sim_data),
            context=context,
        )
        if bounds is None:
            self._emit_fence_section_info(
                "[Vertical Fence Section] grid bounds are unavailable."
            )
            return False

        self._capture_fence_section_context()
        self._capture_fence_section_camera_state()

        self.cache["fence_section_sim_data"] = context.get("sim_data", sim_data)
        self.cache["fence_section_property"] = str(
            context.get("property_name", property_name or scalar_name)
        )
        self.cache["fence_section_scalar_name"] = scalar_name
        self.cache["fence_section_property_context"] = context
        self.cache["fence_section_property_config"] = property_config
        self.cache["fence_section_bounds"] = tuple(float(v) for v in bounds)
        self.cache["fence_section_grid"] = grid
        self.cache["fence_section_points"] = []
        self.cache["fence_section_drawing"] = True
        self.cache["fence_section_finished"] = False
        self.cache["fence_section_last_info"] = None
        self.cache["fence_section_last_click_time"] = None
        self.cache["fence_section_last_click_display"] = None
        self.cache["fence_section_previous_camera_locked"] = bool(
            getattr(self, "camera_direction_locked", False)
        )

        self.view_top()
        self.lock_camera_direction(True)

        interactor = self._get_fence_section_interactor()
        if interactor is None:
            self.cache["fence_section_drawing"] = False
            self.lock_camera_direction(
                self.cache.get("fence_section_previous_camera_locked", False)
            )
            self._restore_fence_section_context()
            self._restore_fence_section_camera_state()
            self._render()
            self._emit_fence_section_info(
                "[Vertical Fence Section] interactor is unavailable."
            )
            return False

        observer_ids = []
        try:
            left_click_id = interactor.AddObserver(
                "LeftButtonPressEvent",
                self._on_fence_section_left_button_press,
            )
            mouse_move_id = interactor.AddObserver(
                "MouseMoveEvent",
                self._on_fence_section_mouse_move,
            )
            observer_ids = [left_click_id, mouse_move_id]
        except Exception as exc:
            self.cache["fence_section_observer_ids"] = observer_ids
            self._remove_fence_section_observers()
            self.cache["fence_section_drawing"] = False
            self.lock_camera_direction(
                self.cache.get("fence_section_previous_camera_locked", False)
            )
            self._restore_fence_section_context()
            self._restore_fence_section_camera_state()
            self._render()
            self._emit_fence_section_info(
                "[Vertical Fence Section] "
                f"observer registration failed: {type(exc).__name__}: {exc}"
            )
            return False

        self.cache["fence_section_observer_ids"] = observer_ids
        self._emit_fence_section_info(
            "[Vertical Fence Section] drawing started. "
            "Left-click to add points; double-click to finish."
        )
        self._render()
        return True


    def complete_vertical_fence_section(self):

        if not self.cache.get(
            "fence_section_drawing",
            False,
        ):
            return False

        points = self.cache.get(
            "fence_section_points",
            [],
        ) or []

        if len(points) < 2:
            self._emit_fence_section_info(
                "[Vertical Fence Section] "
                "select at least two points before double-clicking."
            )
            return False

        self._remove_fence_section_observers()

        self._clear_fence_section_preview(
            render=False,
        )

        self.cache[
            "fence_section_drawing"
        ] = False

        self.cache[
            "fence_section_finished"
        ] = True
        self._set_property_display_mode("fence")
        self.cache["fence_section_persistent_active"] = True
        self.cache["fence_section_pending_property_refresh"] = False
        self.cache["fence_section_context_token"] = None
        self.cache["fence_section_applied_context_token"] = None
        self._set_fence_section_well_labels_hidden(True)

        previous_locked = self.cache.get(
            "fence_section_previous_camera_locked",
            False,
        )

        self.lock_camera_direction(
            bool(previous_locked)
        )

        self._update_fence_section_path_overlay()

        return self._render_vertical_fence_section()


    def cancel_vertical_fence_section(
        self,
        render=True,
    ):

        was_drawing = bool(
            self.cache.get(
                "fence_section_drawing",
                False,
            )
        )

        self._remove_fence_section_observers()

        self._clear_fence_section_preview(
            render=False,
        )

        if was_drawing:
            previous_locked = self.cache.get(
                "fence_section_previous_camera_locked",
                False,
            )

            self.lock_camera_direction(
                bool(previous_locked)
            )

        self.cache[
            "fence_section_drawing"
        ] = False
        self._set_property_display_mode("full")
        self.cache["fence_section_persistent_active"] = False
        self.cache["fence_section_pending_property_refresh"] = False
        self.cache["fence_section_context_token"] = None
        self.cache["fence_section_applied_context_token"] = None

        self.cache[
            "fence_section_points"
        ] = []

        self.cache[
            "fence_section_last_click_time"
        ] = None

        self.cache[
            "fence_section_last_click_display"
        ] = None

        self._clear_fence_section_path_overlay(
            render=False,
        )

        self._restore_fence_section_context()
        self._restore_fence_section_camera_state()

        self._emit_fence_section_info(
            "[Vertical Fence Section] "
            "drawing cancelled."
        )

        if render:
            self._render()


    def _restore_full_property_after_fence(self, context=None):
        """清除剖面后恢复当前完整属性场、颜色条和预览网格。"""
        if not isinstance(context, dict):
            context = self._active_property_context

        if not isinstance(context, dict):
            context = self.cache.get(
                "fence_section_property_context"
            )

        if not isinstance(context, dict):
            return False

        source_mode = str(
            context.get("source_mode", "")
        ).strip().lower()

        if source_mode != "preview":
            actor = context.get("actor")
            self._set_scene_actor_visibility(
                actor,
                True,
            )

            for scalar_bar_actor in self._active_property_scalar_bar_actors(
                context
            ):
                self._set_scene_actor_visibility(
                    scalar_bar_actor,
                    True,
                )

            return actor is not None

        preview = getattr(
            self,
            "static_property_preview",
            None,
        )

        if preview is None:
            return False

        sim_data = context.get("sim_data")
        if sim_data is None:
            sim_data = getattr(
                preview,
                "current_sim_data",
                None,
            )

        property_name = str(
            context.get(
                "property_name",
                getattr(
                    preview,
                    "current_property_key",
                    "",
                ),
            )
            or ""
        ).strip()

        axis = context.get("axis")
        if axis is not None:
            axis = str(axis).strip().lower()

        layer_index = context.get("layer_index")

        current_actor = getattr(
            preview,
            "actor",
            None,
        )
        current_property = str(
            getattr(
                preview,
                "current_property_key",
                "",
            )
            or ""
        ).strip()
        current_axis = getattr(
            preview,
            "current_axis",
            None,
        )
        current_layer = getattr(
            preview,
            "current_layer_index",
            None,
        )

        needs_rebuild = (
            current_actor is None
            or current_property != property_name
            or current_axis != axis
            or current_layer != layer_index
        )

        if (
            needs_rebuild
            and sim_data is not None
            and property_name
        ):
            try:
                if (
                    axis in ("i", "j", "k")
                    and layer_index is not None
                ):
                    preview.render_property_layer(
                        sim_data,
                        property_name,
                        axis=axis,
                        layer_index=int(layer_index),
                        index_base=0,
                        render_now=False,
                    )
                else:
                    preview.render_property(
                        sim_data,
                        property_name,
                        render_now=False,
                    )
            except Exception as exc:
                print(
                    "[Vertical Fence Section] "
                    "failed to rebuild preview property: "
                    f"{type(exc).__name__}: {exc}"
                )

        current_actor = getattr(
            preview,
            "actor",
            None,
        )

        self._set_scene_actor_visibility(
            current_actor,
            True,
        )
        self._set_scene_actor_visibility(
            getattr(preview, "edge_actor", None),
            True,
        )
        self._set_scene_actor_visibility(
            getattr(preview, "scalar_bar_actor", None),
            True,
        )

        current_grid = getattr(
            preview,
            "current_grid",
            None,
        )
        current_scalar_name = str(
            context.get("scalar_name", "")
            or ""
        ).strip()

        if (
            current_actor is not None
            and self._dataset_has_cells(current_grid)
            and current_scalar_name
        ):
            self.set_active_property_context(
                source_mode="preview",
                sim_data=sim_data,
                property_name=(
                    getattr(
                        preview,
                        "current_property_key",
                        property_name,
                    )
                    or property_name
                ),
                scalar_name=current_scalar_name,
                volume_grid=current_grid,
                actor=current_actor,
                axis=getattr(
                    preview,
                    "current_axis",
                    axis,
                ),
                layer_index=getattr(
                    preview,
                    "current_layer_index",
                    layer_index,
                ),
                title=(
                    getattr(
                        preview,
                        "scalar_bar_title",
                        None,
                    )
                    or context.get("title")
                    or property_name
                ),
                unit=context.get("unit", ""),
                metadata=context.get("metadata", {}),
                refresh_picking=True,
            )

        geometry = getattr(
            self,
            "geometry_layers",
            getattr(
                self,
                "geometry_preview",
                None,
            ),
        )

        if geometry is not None and sim_data is not None:
            ensure_grid = getattr(
                geometry,
                "ensure_grid_visible",
                None,
            )
            if ensure_grid is not None:
                try:
                    ensure_grid(
                        sim_data,
                        render_now=False,
                    )
                except Exception:
                    pass

            refresh_stack = getattr(
                geometry,
                "refresh_preview_stack",
                None,
            )
            if refresh_stack is not None:
                try:
                    refresh_stack(
                        render_now=False,
                    )
                except Exception:
                    pass

        refresh_order = getattr(
            preview,
            "refresh_render_order",
            None,
        )
        if refresh_order is not None:
            try:
                refresh_order(
                    render_now=False,
                )
            except Exception:
                pass

        return current_actor is not None


    def clear_vertical_fence_section(
        self,
        render=True,
    ):
        """删除持久剖面，并把属性按钮恢复为完整属性场模式。"""
        restore_context = self._active_property_context
        if not isinstance(restore_context, dict):
            restore_context = self.cache.get(
                "fence_section_property_context"
            )

        self._set_property_display_mode("full")

        self._remove_actor(
            self.cache.get(
                "fence_section_actor"
            )
        )

        self.cache[
            "fence_section_actor"
        ] = None

        self.cache[
            "fence_section_data"
        ] = None

        self._clear_fence_section_scalar_bar()

        self._clear_fence_section_path_overlay(
            render=False,
        )

        self._restore_fence_section_context()
        self._set_fence_section_well_labels_hidden(False)
        self._restore_fence_section_camera_state()

        self.cache["fence_section_refreshing_property"] = False
        self.cache["fence_section_persistent_active"] = False
        self.cache["fence_section_pending_property_refresh"] = False
        self.cache["fence_section_context_token"] = None
        self.cache["fence_section_applied_context_token"] = None

        self.cache[
            "fence_section_points"
        ] = []

        self.cache[
            "fence_section_finished"
        ] = False

        self.cache[
            "fence_section_scalar_name"
        ] = None

        self.cache[
            "fence_section_last_info"
        ] = None

        self._restore_full_property_after_fence(
            restore_context
        )

        self.cache[
            "fence_section_property_context"
        ] = self._active_property_context

        if render:
            self._render()



    def disable_vertical_fence_section(
        self,
        clear_result=True,
        render=True,
        force_clear=False,
    ):
        """停止绘制交互；已完成剖面只有显式清除或 force_clear 才会删除。"""
        if (
            clear_result
            and not force_clear
            and self.is_fence_property_display_mode()
            and self._vertical_fence_section_is_active()
        ):
            clear_result = False

        was_drawing = bool(
            self.cache.get("fence_section_drawing", False)
        )

        self._remove_fence_section_observers()
        self._clear_fence_section_preview(render=False)

        if was_drawing:
            self.lock_camera_direction(
                bool(
                    self.cache.get(
                        "fence_section_previous_camera_locked",
                        False,
                    )
                )
            )

        self.cache["fence_section_drawing"] = False
        self.cache["fence_section_last_click_time"] = None
        self.cache["fence_section_last_click_display"] = None

        if clear_result:
            self.clear_vertical_fence_section(render=False)
            self.cache["fence_section_sim_data"] = None
            self.cache["fence_section_bounds"] = None
            self.cache["fence_section_grid"] = None
            self.cache["fence_section_property"] = "Pressure"
            self.cache["fence_section_property_context"] = None
            self.cache["fence_section_property_config"] = None
        elif was_drawing:
            self._restore_fence_section_context()
            self._restore_fence_section_camera_state()

        if render:
            self._render()

        return True



    def set_vertical_fence_section_property(self, property_name=None):
        """
        兼容旧 UI。剖面始终使用当前显示属性；若传入名称与当前属性不同，
        需先在 UI 中切换属性场，再重新开启剖面。
        """
        context = self.get_active_property_context()
        if not isinstance(context, dict):
            return False

        current_name = str(context.get("property_name", "")).strip()
        requested = str(property_name or current_name).strip()

        if requested and requested != current_name:
            requested_normalized = self._normalize_scene_property_name(requested)
            current_normalized = self._normalize_scene_property_name(current_name)
            if requested_normalized != current_normalized:
                print(
                    "[Vertical Fence Section] Please render the requested "
                    "property first; the section follows the active field."
                )
                return False

        config = self._get_fence_section_property_config(
            context=context
        )
        if config is None:
            return False

        self.cache["fence_section_property"] = current_name
        self.cache["fence_section_scalar_name"] = config["scalar_name"]
        self.cache["fence_section_property_context"] = context
        self.cache["fence_section_property_config"] = config

        if self.cache.get("fence_section_finished", False):
            return self._render_vertical_fence_section()

        return True


    def is_vertical_fence_section_drawing(self):

        return bool(
            self.cache.get(
                "fence_section_drawing",
                False,
            )
        )


    
    enable_fence_section = enable_vertical_fence_section
    disable_fence_section = disable_vertical_fence_section
    clear_fence_section = clear_vertical_fence_section
