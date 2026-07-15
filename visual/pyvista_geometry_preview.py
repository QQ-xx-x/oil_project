# -*- coding: utf-8 -*-
"""
几何预览渲染器。

负责模拟前几何类数据预览：
1. 角点网格预览；
2. 真实井轨迹预览；
3. 天然裂缝预览；
4. 人工裂缝几何预览。
"""

from __future__ import annotations

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

# 静态属性场显示时，白色网格表面不再额外叠加 0.7 透明度；
# 网格线仅作为弱参考线保留，避免把井和裂缝淹没。
GRID_PROPERTY_FOCUS_MODE = True
GRID_PROPERTY_SURFACE_OPACITY = 0.0
GRID_PROPERTY_EDGE_OPACITY = 0.3
GRID_PROPERTY_RENDER_LINES_AS_TUBES = False

GRID_POINT_MERGE_TOLERANCE_RATIO = 1e-9
GRID_POINT_MERGE_ABSOLUTE_TOLERANCE = 1e-8

GRID_LINE_OFFSET_FACTOR = -1.0
GRID_LINE_OFFSET_UNITS = -1.0
GRID_SURFACE_OFFSET_FACTOR = 1.0
GRID_SURFACE_OFFSET_UNITS = 1.0

WELL_COLOR = (0.08, 0.24, 0.62)
WELL_RADIUS = 2.0
WELL_OPACITY = 1.0
WELL_TUBE_SIDES = 32
WELL_FALLBACK_LINE_WIDTH = 4.0
                        
PERFORATION_COLOR = (1.0, 0.82, 0.0)
PERFORATION_OPACITY = 1.0
PERFORATION_VISIBLE = True

WELL_LABEL_FONT_SIZE = 12
WELL_LABEL_MIN_FONT_SIZE = 8
WELL_LABEL_MAX_FONT_SIZE = 36
WELL_LABEL_ZOOM_EXPONENT = 0.80
WELL_LABEL_TEXT_COLOR = (0.05, 0.05, 0.05)
WELL_LABEL_OFFSET_SCENE_RATIO = 0.012
WELL_LABEL_OFFSET_RADIUS_MULTIPLIER = 4.0
                                   
WELL_THIN_RADIUS_SCENE_RATIO = 2.0e-4
WELL_THIN_LINE_MIN_WIDTH = 1.6
WELL_THIN_LINE_MAX_WIDTH = 8.0
                                                
GEOMETRY_CLIPPING_MARGIN_RATIO = 0.12
GEOMETRY_CLIPPING_MIN_NEAR = 1.0e-6
GEOMETRY_CLIPPING_NEAR_FAR_RATIO = 1.0e-8
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
        self.well_actors = []
        self.perforation_actors = []
        self.well_label_actors = []
        self.natural_fracture_actors = []
        self.hydraulic_fracture_actors = []

        self._last_sim_data = None

        self.well_color = tuple(WELL_COLOR)
        self.well_radius = float(WELL_RADIUS)
        self.perforation_color = tuple(PERFORATION_COLOR)
        self.show_perforations = bool(PERFORATION_VISIBLE)

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

    def _remember_sim_data(self, sim_data):
        if sim_data is not None:
            self._last_sim_data = sim_data

    def get_geometry_style(self):
        return {
            "well_color": self.well_color,
            "well_radius": self.well_radius,
            "perforation_color": self.perforation_color,
            "show_perforations": self.show_perforations,
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

        if natural_visible:
            self._render_natural_fractures(data)

        if hydraulic_visible:
            self._render_hydraulic_fractures(data)

        self.refresh_preview_stack(render_now=False)
        return True

    def set_geometry_style(
        self,
        *,
        well_color=None,
        well_radius=None,
        perforation_color=None,
        show_perforations=None,
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
        perforation_visibility_changed = False
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

            well_geometry_changed = not np.isclose(value, self.well_radius)
            self.well_radius = value

        if perforation_color is not None:
            value = self._normalize_color(
                perforation_color
            )
            perforation_color_changed = (
                value != self.perforation_color
            )
            self.perforation_color = value

        if show_perforations is not None:
            value = bool(show_perforations)
            perforation_visibility_changed = (
                value != self.show_perforations
            )
            self.show_perforations = value

        if fracture_color is not None:
            value = self._normalize_color(fracture_color)

            if value != self.natural_fracture_color or value != self.hydraulic_fracture_color:
                fracture_style_changed = True

            self.natural_fracture_color = value
            self.hydraulic_fracture_color = value

        if natural_fracture_color is not None:
            value = self._normalize_color(natural_fracture_color)
            fracture_style_changed = fracture_style_changed or value != self.natural_fracture_color
            self.natural_fracture_color = value

        if hydraulic_fracture_color is not None:
            value = self._normalize_color(hydraulic_fracture_color)
            fracture_style_changed = fracture_style_changed or value != self.hydraulic_fracture_color
            self.hydraulic_fracture_color = value

        if fracture_edge_color is not None:
            value = self._normalize_color(fracture_edge_color)

            if value != self.natural_fracture_edge_color or value != self.hydraulic_fracture_edge_color:
                fracture_style_changed = True

            self.natural_fracture_edge_color = value
            self.hydraulic_fracture_edge_color = value

        if natural_fracture_edge_color is not None:
            value = self._normalize_color(natural_fracture_edge_color)
            fracture_style_changed = fracture_style_changed or value != self.natural_fracture_edge_color
            self.natural_fracture_edge_color = value

        if hydraulic_fracture_edge_color is not None:
            value = self._normalize_color(hydraulic_fracture_edge_color)
            fracture_style_changed = fracture_style_changed or value != self.hydraulic_fracture_edge_color
            self.hydraulic_fracture_edge_color = value

        if fracture_show_edges is not None:
            value = bool(fracture_show_edges)
            fracture_style_changed = fracture_style_changed or value != self.fracture_show_edges
            self.fracture_show_edges = value

            if value and fracture_edge_line_width is None and self.fracture_edge_line_width <= 0.0:
                self.fracture_edge_line_width = 1.0
                fracture_style_changed = True

        if fracture_edge_line_width is not None:
            value = float(fracture_edge_line_width)

            if not np.isfinite(value) or value < 0.0:
                raise ValueError("裂缝边框宽度必须是大于等于 0 的有限数值")

            fracture_style_changed = fracture_style_changed or not np.isclose(
                value,
                self.fracture_edge_line_width,
            )
            self.fracture_edge_line_width = value

        rebuilt = False

        if well_geometry_changed or perforation_visibility_changed:
            rebuilt = self._rebuild_visible_wells(sim_data) or rebuilt
        elif well_color_changed:
            self._update_well_actor_colors()

        if perforation_color_changed:
            self._update_perforation_actor_colors()

        if fracture_style_changed:
            rebuilt = self._rebuild_visible_fractures(sim_data) or rebuilt

        if render_now and (
            rebuilt
            or well_color_changed
            or perforation_color_changed
            or perforation_visibility_changed
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

        render_window = getattr(
            self.plotter,
            "ren_win",
            None,
        )

        if (
            render_window is not None
            and hasattr(render_window, "AddObserver")
            and not getattr(
                self.host,
                "_geometry_preview_clipping_observer_installed",
                False,
            )
        ):
            try:
                observer_id = render_window.AddObserver(
                    "StartEvent",
                    self._on_geometry_render_start,
                )
                self._geometry_render_observer_ids.append(
                    (
                        render_window,
                        observer_id,
                    )
                )
                setattr(
                    self.host,
                    "_geometry_preview_clipping_observer_installed",
                    True,
                )
            except Exception:
                pass

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

        self._update_well_label_font_size()

    def _on_geometry_render_start(self, *_args):
        if self._geometry_clipping_guard:
            return

        if not (
            self._geometry_top_actors()
            or self._has_visible_preview_background()
        ):
            return

        self._update_well_label_font_size()
        self._apply_stable_scene_clipping_range()

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

        current_scale = self._camera_view_scale()

        if current_scale is None:
            return False

        reference_scale = self._well_label_reference_view_scale

        if (
            reference_scale is None
            or not np.isfinite(reference_scale)
            or reference_scale <= 1.0e-12
        ):
            self._well_label_reference_view_scale = current_scale
            reference_scale = current_scale

        zoom_ratio = reference_scale / current_scale
        zoom_ratio = max(
            float(zoom_ratio),
            1.0e-6,
        )

        font_size = WELL_LABEL_FONT_SIZE * (
            zoom_ratio ** WELL_LABEL_ZOOM_EXPONENT
        )

        return self._set_well_label_font_size(
            font_size
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
            direction = -first_segment / segment_length


            if abs(float(direction[2])) < 0.25:
                direction = direction + np.asarray(
                    [0.0, 0.0, 0.35],
                    dtype=np.float64,
                )
                direction_length = float(
                    np.linalg.norm(direction)
                )

                if direction_length > 1.0e-12:
                    direction = direction / direction_length

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

    def _has_visible_preview_background(self) -> bool:
        if self._actor_is_visible(self.grid_actor):
            return True

        if self._actor_is_visible(self.grid_edge_actor):
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
        corners = self._bounds_corners(bounds)

        if corners is None:
            return False

        camera = getattr(
            self.plotter,
            "camera",
            None,
        )

        if camera is None:
            return False

        try:
            position = np.asarray(
                camera.GetPosition(),
                dtype=np.float64,
            )
            focal_point = np.asarray(
                camera.GetFocalPoint(),
                dtype=np.float64,
            )
        except Exception:
            return False

        view_direction = focal_point - position
        direction_length = float(
            np.linalg.norm(view_direction)
        )

        if (
            not np.isfinite(direction_length)
            or direction_length <= 1.0e-12
        ):
            return False

        view_direction /= direction_length

        depths = np.dot(
            corners - position,
            view_direction,
        )
        depths = depths[
            np.isfinite(depths)
        ]

        if depths.size == 0:
            return False

        positive_depths = depths[
            depths > 0.0
        ]

        if positive_depths.size == 0:
            return False

        far_depth = float(
            np.max(positive_depths)
        )

        span_vector = np.asarray(
            [
                float(bounds[1]) - float(bounds[0]),
                float(bounds[3]) - float(bounds[2]),
                float(bounds[5]) - float(bounds[4]),
            ],
            dtype=np.float64,
        )
        scene_diagonal = max(
            float(np.linalg.norm(span_vector)),
            float(self.well_radius) * 2.0,
            GEOMETRY_CLIPPING_MIN_NEAR,
        )

        margin = max(
            scene_diagonal
            * GEOMETRY_CLIPPING_MARGIN_RATIO,
            float(self.well_radius)
            * GEOMETRY_CLIPPING_WELL_RADIUS_MARGIN,
            GEOMETRY_CLIPPING_MIN_NEAR,
        )

        minimum_depth = float(
            np.min(depths)
        )

        if minimum_depth <= margin:

                                        
            near_value = max(
                GEOMETRY_CLIPPING_MIN_NEAR,
                far_depth
                * GEOMETRY_CLIPPING_NEAR_FAR_RATIO,
            )
        else:
            near_value = max(
                minimum_depth - margin,
                GEOMETRY_CLIPPING_MIN_NEAR,
                far_depth
                * GEOMETRY_CLIPPING_NEAR_FAR_RATIO,
            )

        far_value = max(
            far_depth + margin,
            near_value * 1.01,
        )

        if (
            not np.isfinite(near_value)
            or not np.isfinite(far_value)
            or far_value <= near_value
        ):
            return False

        try:
            self._geometry_clipping_guard = True
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
    def _completion_perforation_intervals(well):
        if not isinstance(well, dict):
            return []

        completions = well.get(
            "completion_definitions",
            [],
        )

        if not isinstance(completions, list):
            return []

        intervals = []

        for completion in completions:
            if not isinstance(completion, dict):
                continue

            event = str(
                completion.get(
                    "event",
                    "",
                )
                or ""
            ).strip().upper()

            if event and event != "PERF":
                continue

            try:
                md_top = float(
                    completion["md_top_m"]
                )
                md_bottom = float(
                    completion["md_bottom_m"]
                )
            except (
                KeyError,
                TypeError,
                ValueError,
            ):
                continue

            if not np.isfinite(
                [md_top, md_bottom]
            ).all():
                continue

            start = min(md_top, md_bottom)
            end = max(md_top, md_bottom)

            if end - start <= 1.0e-10:
                continue

            intervals.append(
                (
                    float(start),
                    float(end),
                )
            )

        if not intervals:
            return []

        intervals.sort(
            key=lambda item: item[0]
        )

        merged = []

        for start, end in intervals:
            if (
                not merged
                or start > merged[-1][1] + 1.0e-8
            ):
                merged.append(
                    [start, end]
                )
            else:
                merged[-1][1] = max(
                    merged[-1][1],
                    end,
                )

        return [
            (
                float(start),
                float(end),
            )
            for start, end in merged
        ]

    @staticmethod
    def _interpolate_track_point_at_md(
        track_md,
        track_points,
        target_md,
    ):
        track_md = np.asarray(
            track_md,
            dtype=np.float64,
        ).reshape(-1)
        track_points = np.asarray(
            track_points,
            dtype=np.float64,
        ).reshape(-1, 3)

        if (
            track_md.size < 2
            or track_points.shape[0] != track_md.size
        ):
            return None

        target_md = float(target_md)

        if target_md <= track_md[0]:
            return track_points[0].copy()

        if target_md >= track_md[-1]:
            return track_points[-1].copy()

        right = int(
            np.searchsorted(
                track_md,
                target_md,
                side="right",
            )
        )
        left = max(
            right - 1,
            0,
        )
        right = min(
            right,
            track_md.size - 1,
        )

        md0 = float(track_md[left])
        md1 = float(track_md[right])

        if abs(md1 - md0) <= 1.0e-12:
            return track_points[left].copy()

        ratio = (
            target_md - md0
        ) / (
            md1 - md0
        )

        return (
            track_points[left]
            + ratio
            * (
                track_points[right]
                - track_points[left]
            )
        )

    def _split_track_by_perforations(
        self,
        valid_points,
        perforation_intervals,
    ):
        if not valid_points:
            return []

        clean_md = []
        clean_points = []

        for md, xyz in valid_points:
            md = float(md)
            xyz = np.asarray(
                xyz,
                dtype=np.float64,
            ).reshape(3)

            if not np.isfinite(
                [md, *xyz]
            ).all():
                continue

            if (
                clean_md
                and abs(md - clean_md[-1]) <= 1.0e-10
            ):
                clean_points[-1] = xyz
                continue

            clean_md.append(md)
            clean_points.append(xyz)

        if len(clean_md) < 2:
            return []

        track_md = np.asarray(
            clean_md,
            dtype=np.float64,
        )
        track_points = np.asarray(
            clean_points,
            dtype=np.float64,
        )

        track_min = float(track_md[0])
        track_max = float(track_md[-1])

        clipped_intervals = []

        for start, end in perforation_intervals or []:
            start = max(
                float(start),
                track_min,
            )
            end = min(
                float(end),
                track_max,
            )

            if end - start > 1.0e-10:
                clipped_intervals.append(
                    (
                        start,
                        end,
                    )
                )

        breakpoints = list(
            track_md.tolist()
        )

        for start, end in clipped_intervals:
            breakpoints.extend(
                [
                    start,
                    end,
                ]
            )

        breakpoints = np.asarray(
            sorted(set(breakpoints)),
            dtype=np.float64,
        )

        samples = []

        for md in breakpoints:
            point = self._interpolate_track_point_at_md(
                track_md,
                track_points,
                md,
            )

            if point is None:
                continue

            samples.append(
                (
                    float(md),
                    point,
                )
            )

        if len(samples) < 2:
            return []

        def is_perforation_md(md):
            for start, end in clipped_intervals:
                if (
                    md >= start - 1.0e-9
                    and md <= end + 1.0e-9
                ):
                    return True
            return False

        result = []

        for index in range(len(samples) - 1):
            md0, point0 = samples[index]
            md1, point1 = samples[index + 1]

            if md1 - md0 <= 1.0e-12:
                continue

            segment_is_perforation = (
                is_perforation_md(
                    (md0 + md1) * 0.5
                )
            )

            if (
                result
                and result[-1]["is_perforation"]
                == segment_is_perforation
            ):
                last_point = result[-1]["points"][-1]

                if np.linalg.norm(
                    point0 - last_point
                ) > 1.0e-8:
                    result[-1]["points"].append(
                        point0
                    )

                result[-1]["points"].append(
                    point1
                )
            else:
                result.append(
                    {
                        "is_perforation": (
                            segment_is_perforation
                        ),
                        "points": [
                            point0,
                            point1,
                        ],
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
                    or np.linalg.norm(
                        point - points[-1]
                    ) > 1.0e-8
                ):
                    points.append(point)

            if len(points) >= 2:
                normalized.append(
                    {
                        "is_perforation": item[
                            "is_perforation"
                        ],
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

        self.grid_actor = None
        self.grid_edge_actor = None

        if self._geometry_top_actors():
            self.refresh_preview_stack(
                render_now=False,
            )
            self._apply_stable_scene_clipping_range()

        if render_now:
            self._render()

    def clear_wells(self, render_now=True):
        self._remove_actor_list(self.well_actors)
        self._remove_actor_list(
            self.perforation_actors
        )
        self._remove_actor_list(self.well_label_actors)
        self.well_actors = []
        self.perforation_actors = []
        self.well_label_actors = []
        self._well_label_reference_view_scale = None
        self._well_label_current_font_size = None

        self._sync_geometry_overlay_attachment()

        if render_now:
            self._render()

    def clear_natural_fractures(self, render_now=True):
        self._remove_actor_list(self.natural_fracture_actors)
        self.natural_fracture_actors = []

        self._sync_geometry_overlay_attachment()

        if render_now:
            self._render()

    def clear_hydraulic_fractures(self, render_now=True):
        self._remove_actor_list(self.hydraulic_fracture_actors)
        self.hydraulic_fracture_actors = []

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
        return self.grid_actor is not None or self.grid_edge_actor is not None

    def is_wells_visible(self) -> bool:
        return bool(
            self.well_actors
            or self.perforation_actors
        )

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
        return [
            actor
            for actor in [
                *self._geometry_mesh_actors(),
                *(self.well_label_actors or []),
            ]
            if actor is not None
        ]

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

        if self.grid_edge_actor is not None:
            if property_visible:
                try:
                    self.grid_edge_actor.ForceOpaqueOff()
                except Exception:
                    try:
                        self.grid_edge_actor.SetForceOpaque(False)
                    except Exception:
                        pass

                try:
                    self.grid_edge_actor.ForceTranslucentOn()
                except Exception:
                    try:
                        self.grid_edge_actor.SetForceTranslucent(True)
                    except Exception:
                        pass

                self._set_actor_opacity(
                    self.grid_edge_actor,
                    GRID_PROPERTY_EDGE_OPACITY,
                )

                try:
                    prop = self.grid_edge_actor.GetProperty()

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
                    self.grid_edge_actor
                )

    def refresh_preview_stack(
        self,
        render_now=False,
    ) -> None:

        self._move_actor_to_renderer_end(
            self.grid_actor,
        )
        self._move_actor_to_renderer_end(
            self.grid_edge_actor,
        )

        static_preview = getattr(
            self.host,
            "static_property_preview",
            None,
        )

        if static_preview is not None and hasattr(
            static_preview,
            "refresh_render_order",
        ):
            static_preview.refresh_render_order(
                render_now=False,
            )

        self._apply_property_focus_grid_style()

        top_actors = self._geometry_top_actors()
        has_background = self._has_visible_preview_background()

        if not PREVIEW_USE_GEOMETRY_OVERLAY:
            # 属性场、裂缝、井和射孔段全部放回主 renderer。
            # 它们共用同一个深度缓冲，由 VTK 的 opaque/translucent pass
            # 和 depth peeling 决定真实的前后遮挡关系。
            for actor in top_actors:
                self._configure_depth_sorted_geometry_actor(actor)
                self._move_actor_to_renderer_end(actor)

            self._set_geometry_overlay_attached(False)

            if top_actors or has_background:
                self._apply_stable_scene_clipping_range()

        elif top_actors and has_background:
            overlay_renderer = self._ensure_geometry_overlay_renderer(
                attach_to_window=True,
            )

            for actor in top_actors:
                self._configure_depth_sorted_geometry_actor(actor)
                self._move_actor_to_geometry_overlay(actor)

            if overlay_renderer is not None:
                main_renderer = self._main_renderer()

                if main_renderer is not None:
                    try:
                        overlay_renderer.SetActiveCamera(
                            main_renderer.GetActiveCamera()
                        )
                    except Exception:
                        pass

        elif top_actors:
            for actor in top_actors:
                self._configure_depth_sorted_geometry_actor(actor)
                self._move_actor_to_renderer_end(actor)

            self._set_geometry_overlay_attached(False)
            self._apply_stable_scene_clipping_range()

        else:
            self._set_geometry_overlay_attached(False)

        if static_preview is not None and hasattr(
            static_preview,
            "refresh_layer_clipping_range",
        ):
            static_preview.refresh_layer_clipping_range(
                render_now=False,
            )

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


    def _build_stable_corner_grid_surface_and_edges(
        self,
        grid,
    ):

        if grid is None:
            return None, None

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
        edges = None

        try:
            surface = stable_grid.extract_surface()
        except Exception:
            surface = None

        if GRID_SHOW_EDGES:
            try:
                edges = stable_grid.extract_all_edges()
            except Exception:
                edges = None

        return surface, edges


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

        surface, edges = (
            self._build_stable_corner_grid_surface_and_edges(
                grid
            )
        )

        if (
            GRID_SHOW_EDGES
            and edges is not None
            and edges.n_points > 0
            and edges.n_cells > 0
        ):
            self.grid_edge_actor = self.plotter.add_mesh(
                edges,
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

        combined_bounds = self._merge_bounds(
            grid.bounds,
            self.get_visible_geometry_bounds(),
        )
        self._reset_clipping_range_for_bounds(
            combined_bounds
        )

        if render_now:
            self._render()

        return self.grid_actor or self.grid_edge_actor


    @staticmethod
    def _new_billboard_text_actor():
        vtk_namespace = getattr(
            pv,
            "_vtk",
            None,
        )

        actor_class = getattr(
            vtk_namespace,
            "vtkBillboardTextActor3D",
            None,
        ) if vtk_namespace is not None else None

        if actor_class is None:
            try:
                from vtkmodules.vtkRenderingCore import (
                    vtkBillboardTextActor3D,
                )
                actor_class = vtkBillboardTextActor3D
            except Exception:
                return None

        try:
            return actor_class()
        except Exception:
            return None

    def _add_well_name_labels(
        self,
        well_head_points,
        well_names,
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

        renderer = self._main_renderer()

        if renderer is None:
            return []

        actors = []

        for point, label in zip(points, labels):
            if not label or not np.isfinite(point).all():
                continue

            actor = self._new_billboard_text_actor()

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
                    int(WELL_LABEL_FONT_SIZE)
                )
                text_property.SetColor(
                    *WELL_LABEL_TEXT_COLOR
                )

                try:
                    text_property.SetBackgroundOpacity(0.0)
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

        return actors


    def render_wells(
        self,
        sim_data,
        render_now=True,
    ):
        self._remember_sim_data(sim_data)
        self._configure_preview_scene()

        if self.is_wells_visible():
            self.clear_wells(render_now=render_now)
            return False

        self.clear_wells(render_now=False)

        well_data = getattr(
            sim_data,
            "parsed_well_data",
            None,
        )

        if not isinstance(well_data, dict):
            if render_now:
                self._render()
            return False

        wells = well_data.get(
            "wells",
            [],
        )

        if not isinstance(wells, list) or not wells:
            if render_now:
                self._render()
            return False

        count = 0
        well_head_points = []
        well_names = []

        for well in wells:
            if not isinstance(well, dict):
                continue

            raw_track = well.get(
                "track",
                [],
            )

            if not isinstance(raw_track, list):
                continue

            valid_points = []

            for point in raw_track:
                if not isinstance(point, dict):
                    continue

                try:
                    md = float(point["md_m"])
                    x = float(point["x_m"])
                    y = float(point["y_m"])
                    z = float(point["z_m"])
                except (
                    KeyError,
                    TypeError,
                    ValueError,
                ):
                    continue

                if not np.isfinite([md, x, y, z]).all():
                    continue

                valid_points.append(
                    (
                        md,
                        np.array(
                            [x, y, z],
                            dtype=float,
                        ),
                    )
                )

            if len(valid_points) < 2:
                continue

            valid_points.sort(
                key=lambda item: item[0],
            )

            ordered_points = []

            for _, xyz in valid_points:
                if not ordered_points:
                    ordered_points.append(xyz)
                    continue

                if np.linalg.norm(xyz - ordered_points[-1]) > 1e-8:
                    ordered_points.append(xyz)

            if len(ordered_points) < 2:
                continue

            if self.show_perforations:
                perforation_intervals = (
                    self._completion_perforation_intervals(
                        well
                    )
                )
            else:
                perforation_intervals = []

            track_segments = (
                self._split_track_by_perforations(
                    valid_points,
                    perforation_intervals,
                )
            )

            if not track_segments:
                continue

            rendered_segment_count = 0

            for segment in track_segments:
                is_perforation = bool(
                    segment["is_perforation"]
                )
                segment_color = (
                    self.perforation_color
                    if is_perforation
                    else self.well_color
                )
                segment_opacity = (
                    PERFORATION_OPACITY
                    if is_perforation
                    else WELL_OPACITY
                )

                actor = (
                    self._add_well_track_segment_actor(
                        sim_data=sim_data,
                        points=segment["points"],
                        color=segment_color,
                        opacity=segment_opacity,
                    )
                )

                if actor is None:
                    continue

                if is_perforation:
                    self.perforation_actors.append(
                        actor
                    )
                else:
                    self.well_actors.append(
                        actor
                    )

                rendered_segment_count += 1

            if rendered_segment_count == 0:
                continue

            well_name = str(
                well.get(
                    "well_name",
                    well.get("name", ""),
                )
                or ""
            ).strip()

            if well_name:
                label_point = self._well_name_label_point(
                    sim_data=sim_data,
                    ordered_points=ordered_points,
                )

                if label_point is not None:
                    well_head_points.append(
                        label_point
                    )
                    well_names.append(well_name)

            count += 1

        if well_head_points and well_names:
            label_actors = self._add_well_name_labels(
                well_head_points=well_head_points,
                well_names=well_names,
            )

            if label_actors:
                self.well_label_actors.extend(
                    label_actors
                )

        if count > 0:
            self._initialize_preview_camera_once(
                sim_data=sim_data,
                bounds=self._actors_bounds(
                    [
                        *(self.well_actors or []),
                        *(
                            self.perforation_actors
                            or []
                        ),
                    ],
                ),
            )
            self.refresh_preview_stack(
                render_now=False,
            )

            if self.well_label_actors:
                self._reset_well_label_zoom_reference()

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
            self._initialize_preview_camera_once(
                sim_data=sim_data,
                bounds=self._actors_bounds(
                    self.natural_fracture_actors,
                ),
            )
            self.refresh_preview_stack(
                render_now=False,
            )

        if render_now:
            self._render()

        return count > 0

    def _render_natural_fractures(
        self,
        sim_data,
    ):
        dfn_data = getattr(
            sim_data,
            "static_dfn_data",
            None,
        )

        if not isinstance(dfn_data, dict):
            return 0

        fractures = dfn_data.get(
            "fractures",
            [],
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
            self._initialize_preview_camera_once(
                sim_data=sim_data,
                bounds=self._actors_bounds(
                    self.hydraulic_fracture_actors,
                ),
            )
            self.refresh_preview_stack(
                render_now=False,
            )

        if render_now:
            self._render()

        return count > 0

    def _render_hydraulic_fractures(
        self,
        sim_data,
    ):
        well_data = getattr(
            sim_data,
            "parsed_well_data",
            None,
        )

        if not isinstance(well_data, dict):
            return 0

        wells = well_data.get(
            "wells",
            [],
        )

        if not isinstance(wells, list):
            return 0

        grid_z_bounds = self._static_grid_z_bounds(sim_data)

        z_transform = self._build_geometry_z_transform(
            z_values=self._hydraulic_fracture_z_values(wells),
            grid_z_bounds=grid_z_bounds,
        )

        count = 0

        for well in wells:
            if not isinstance(well, dict):
                continue

            completions = well.get(
                "completion_definitions",
                [],
            )

            if not isinstance(completions, list):
                continue

            for completion in completions:
                if not isinstance(completion, dict):
                    continue

                if not completion.get("is_fractured", False):
                    continue

                fracture_data = completion.get(
                    "fracture",
                    None,
                )

                if not isinstance(fracture_data, dict):
                    continue

                if not fracture_data.get("geometry_available", False):
                    continue

                corners = fracture_data.get(
                    "corners",
                    [],
                )

                if not isinstance(corners, list) or len(corners) < 3:
                    continue

                raw_points = []

                for corner in corners:
                    if not isinstance(corner, dict):
                        continue

                    try:
                        raw_points.append(
                            (
                                float(corner["x_m"]),
                                float(corner["y_m"]),
                                float(corner["z_m"]),
                            )
                        )

                    except (
                        KeyError,
                        TypeError,
                        ValueError,
                    ):
                        continue

                points = self._safe_points(raw_points)

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
                    color=self.hydraulic_fracture_color,
                    edge_color=self.hydraulic_fracture_edge_color,
                )

                if actors:
                    self.hydraulic_fracture_actors.extend(actors)
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

        total_count = 0

        total_count += self._render_natural_fractures(
            sim_data,
        )

        total_count += self._render_hydraulic_fractures(
            sim_data,
        )

        if total_count > 0:
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
    def _hydraulic_fracture_z_values(wells):
        z_values = []

        if not isinstance(wells, list):
            return z_values

        for well in wells:
            if not isinstance(well, dict):
                continue

            completions = well.get(
                "completion_definitions",
                [],
            )

            if not isinstance(completions, list):
                continue

            for completion in completions:
                if not isinstance(completion, dict):
                    continue

                if not completion.get("is_fractured", False):
                    continue

                fracture_data = completion.get(
                    "fracture",
                    None,
                )

                if not isinstance(fracture_data, dict):
                    continue

                if not fracture_data.get("geometry_available", False):
                    continue

                corners = fracture_data.get(
                    "corners",
                    [],
                )

                if not isinstance(corners, list):
                    continue

                for corner in corners:
                    if not isinstance(corner, dict):
                        continue

                    try:
                        z = float(
                            corner["z_m"]
                        )

                    except (
                        KeyError,
                        TypeError,
                        ValueError,
                    ):
                        continue

                    if np.isfinite(z):
                        z_values.append(z)

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
                overlay_renderer.RemoveActor(actor)
            except Exception:
                try:
                    overlay_renderer.RemoveViewProp(actor)
                except Exception:
                    pass

        main_renderer = self._main_renderer()

        if main_renderer is not None:
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
        if self._geometry_top_actors():
            self.refresh_preview_stack(
                render_now=False,
            )

        if (
            self._geometry_top_actors()
            or self._has_visible_preview_background()
        ):
            self._apply_stable_scene_clipping_range()

        if hasattr(self.host, "_render"):
            self.host._render()
        else:
            self.plotter.render()

        static_preview = getattr(
            self.host,
            "static_property_preview",
            None,
        )

        if static_preview is not None and hasattr(
            static_preview,
            "refresh_layer_clipping_range",
        ):
            layer_preview_active = (
                static_preview.refresh_layer_clipping_range(
                    render_now=False,
                )
            )

            if layer_preview_active:
                try:
                    self.plotter.render()
                except Exception:
                    pass