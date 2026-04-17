"""
基于 PyVista 的可视化渲染器。
"""

from __future__ import annotations

import sys
from pathlib import Path


def _ensure_local_pyvista_site() -> None:
    """当基础环境无法直接读取时，补充项目内的 PyVista 依赖路径。"""
    project_root = Path(__file__).resolve().parent.parent
    local_site = project_root / ".deps" / "pyvista_site"
    local_site_str = str(local_site)
    if local_site.exists() and local_site_str not in sys.path:
        # 追加到 sys.path 末尾，优先继续使用当前环境里的基础库，
        # 避免把 numpy、matplotlib 等整体切换到 .deps 版本。
        sys.path.append(local_site_str)


_ensure_local_pyvista_site()

import numpy as np
import pyvista as pv


class PyVistaRenderer:
    """基于 PyVista 的渲染器，并保留对旧 VTK 渲染器接口的兼容面。"""

    def __init__(self, qt_view):
        self.vtk_widget = qt_view
        self.plotter = qt_view.plotter
        self.renderer = qt_view.renderer
        self.cache = self._new_cache()

        # 命名收口：迁移期仍保留旧字段，但新逻辑优先使用更贴近 PyVista 的命名。
        self.view = qt_view
        self.pv_renderer = qt_view.renderer
        
        # 全局配置，避免空网格报错
        pv.global_theme.allow_empty_mesh = True

        # 框选 overlay 的内部状态（仅渲染器维护；主窗口不应感知）
        self._selection_overlay_state = {
            "world_bounds": None,
            "handle_radius": None,
            "outline_mesh": None,
            "fill_mesh": None,
        }

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
            "well_actors": [],
            "pressure_field_actor": None,
            "pressure_scalar_bar": None,
            "original_grid_opacity": None,
            "original_pressure_opacity": None,
            "corner_lgr_parent_grid_actor": None,
            "corner_lgr_refined_grid_actor": None,
            # 框选覆盖层（由渲染器内部创建/销毁，主窗口不应直接操控 actor）
            "selection_outline_actor": None,
            "selection_fill_actor": None,
            "selection_handle_actors": [],
        }

    def _render(self):
        self.plotter.render()

    def render_now(self):
        self._render()

    def capture_camera_state(self):
        """捕获当前相机状态，供主窗口在交互模式切换时保存/恢复。

        这里尽量使用 PyVista 的相机表达方式（camera_position + Camera 属性），
        避免把 VTK 风格 Get* 调用散落在渲染链路中。
        """
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
        """恢复相机状态。"""
        if not state:
            return
        try:
            self.plotter.camera_position = (
                state.get("position"),
                state.get("focal_point"),
                state.get("view_up"),
            )
            cam = self.plotter.camera
            # 通过 PyVista Camera 属性恢复相机参数
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

    def configure_selection_camera(self, world_bounds) -> None:
        """配置框选模式的相机参数。

        目标：让屏幕坐标到世界坐标的映射尽量稳定（典型用法是俯视/正交）。
        """
        if not world_bounds or len(world_bounds) != 6:
            return
        xmin, xmax, ymin, ymax, zmin, zmax = (float(v) for v in world_bounds)
        cx = (xmin + xmax) * 0.5
        cy = (ymin + ymax) * 0.5
        cz = (zmin + zmax) * 0.5
        span = max(xmax - xmin, ymax - ymin, 1.0)

        # 使用 PyVista 的 Camera 属性表达“俯视 + 正交”
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
        """选区投影平面 Z（默认使用 bounds 顶面）。"""
        if not world_bounds or len(world_bounds) != 6:
            return 0.0
        return float(world_bounds[5])

    def _display_world_ray(self, display_x: float, display_y: float):
        """把显示坐标转换为一条世界坐标射线（近裁剪面->远裁剪面）。

        注意：屏幕到世界的精确转换本质上依赖底层渲染器变换矩阵。
        这里把必要的底层调用压缩到单一位置，避免扩散到其它逻辑。
        """
        renderer = self.pv_renderer
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
        """把显示坐标（像素）映射到世界坐标（落在选区投影平面上）。"""
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
        """确保框选 overlay 的对象存在并与当前 world_bounds 匹配。"""
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
        """应用框选 overlay 的样式（finalized/preview 统一在此收口）。"""
        outline_color = (0.2, 1.0, 0.2) if not finalized else (1.0, 0.8, 0.2)
        fill_color = outline_color
        fill_opacity = 0.08 if not finalized else 0.12

        outline_actor = self.cache.get("selection_outline_actor")
        if outline_actor is not None:
            prop = outline_actor.GetProperty()
            prop.SetColor(*outline_color)
            prop.SetOpacity(1.0)

        fill_actor = self.cache.get("selection_fill_actor")
        if fill_actor is not None:
            prop = fill_actor.GetProperty()
            prop.SetColor(*fill_color)
            prop.SetOpacity(float(fill_opacity))

        for actor in self.cache.get("selection_handle_actors", []) or []:
            prop = actor.GetProperty()
            prop.SetColor(*outline_color)
            prop.SetOpacity(0.9)

    def _update_selection_overlay_geometry(self, xmin, xmax, ymin, ymax, z_plane: float) -> None:
        """更新框选 overlay 的几何（不重复创建/移除 actor）。"""
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
            outline_mesh.Modified()

        fill_mesh = self._selection_overlay_state.get("fill_mesh")
        if fill_mesh is not None:
            fill_mesh.points = np.array(corners, dtype=float)
            fill_mesh.Modified()

        handle_actors = self.cache.get("selection_handle_actors") or []
        for actor, pt in zip(handle_actors, corners):
            actor.SetPosition(float(pt[0]), float(pt[1]), float(pt[2]))

    def show_selection_preview(self, start_xy, end_xy, world_bounds, finalized: bool = False) -> None:
        """显示框选预览（边框 + 半透明填充 + 角点 handle）。

        约定：start_xy / end_xy 为世界坐标系下的 (x, y)，z 由 world_bounds 决定。
        """
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
        """清除框选覆盖层（预览/边框/handle）。"""
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

    def clear_scene(self):
        self.plotter.clear_actors()
        self.cache["selection_outline_actor"] = None
        self.cache["selection_fill_actor"] = None
        self.cache["selection_handle_actors"] = []
        self._selection_overlay_state["outline_mesh"] = None
        self._selection_overlay_state["fill_mesh"] = None
        self._selection_overlay_state["world_bounds"] = None
        self._selection_overlay_state["handle_radius"] = None
        self._render()

    def clear_cache(self):
        self.plotter.clear_actors()
        self.cache = self._new_cache()
        self._selection_overlay_state["outline_mesh"] = None
        self._selection_overlay_state["fill_mesh"] = None
        self._selection_overlay_state["world_bounds"] = None
        self._selection_overlay_state["handle_radius"] = None
        self._render()

    def _remove_actor(self, actor):
        if actor is None:
            return
        try:
            self.plotter.remove_actor(actor, render=False)
        except Exception:
            pass

    def _remove_actor_list(self, actors):
        for actor in actors:
            self._remove_actor(actor)

    def _replace_scalar_bar(self, cache_key, title, **kwargs):
        existing = self.cache.get(cache_key)
        if existing is not None:
            try:
                self.renderer.RemoveActor2D(existing)
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
        """把线段列表合并成单一 PolyData，避免大量小对象导致渲染崩溃。"""
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
        """渲染平滑压力场。"""
        field_data = sim_data.interpolated_pressure or sim_data.pressure_field
        if not field_data:
            return

        data_hash = hash((len(field_data), tuple(field_data[0]), tuple(field_data[-1])))
        if self.cache["data_hash"] == data_hash and self.cache["pressure_actor"] is not None:
            self.cache["pressure_actor"].SetVisibility(True)
            if self.cache["scalar_bar"] is not None:
                self.cache["scalar_bar"].SetVisibility(True)
            self.setup_camera(sim_data)
            self._render()
            return

        self._remove_actor(self.cache["pressure_actor"])
        if self.cache["scalar_bar"] is not None:
            try:
                self.renderer.RemoveActor2D(self.cache["scalar_bar"])
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

        surface = grid.extract_surface()
        min_p = float(np.min(scalars))
        max_p = float(np.max(scalars))

        actor = self.plotter.add_mesh(
            surface,
            scalars="Pressure",
            cmap="jet",
            clim=[min_p, max_p],
            show_scalar_bar=False,
            opacity=1.0,
            render=False,
        )
        scalar_bar = self._replace_scalar_bar(
            "scalar_bar",
            "Pressure (MPa)",
            label_font_size=10,
            title_font_size=12,
            color="white",
            position_x=0.85,
            position_y=0.15,
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

    def render_fractures(self, sim_data):
        """渲染裂缝。"""
        self._remove_actor_list(self.cache["fracture_actors"])
        self.cache["fracture_actors"] = []

        if not sim_data.fractures:
            return

        for fracture in sim_data.fractures:
            frac_points = fracture["points"]
            if len(frac_points) >= 3:
                points = np.array(frac_points, dtype=float)
                polygon = pv.PolyData(points)
                polygon.faces = np.array([len(frac_points), *range(len(frac_points))], dtype=np.int32)

                actor = self.plotter.add_mesh(
                    polygon,
                    color=(1.0, 0.5, 0.0),
                    opacity=0.6,
                    show_edges=True,
                    edge_color=(0.8, 0.4, 0.0),
                    line_width=1.0,
                    render=False,
                )
                self.cache["fracture_actors"].append(actor)

                edge_lines = []
                for index in range(len(frac_points)):
                    edge_lines.append(pv.Line(frac_points[index], frac_points[(index + 1) % len(frac_points)]))
                if edge_lines:
                    edge_actor = self.plotter.add_mesh(
                        pv.MultiBlock(edge_lines),
                        color=(0.0, 0.0, 0.0),
                        line_width=1.5,
                        render=False,
                    )
                    self.cache["fracture_actors"].append(edge_actor)

        self._render()

    def create_grid_lines(self, sim_data):
        """创建网格线。"""
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
            color=(0.8, 0.8, 0.8),
            line_width=1.0,
            opacity=0.8,
            render=False,
        )
        self.cache["grid_lines_actor"] = actor
        self._render()
        return actor

    def has_grid_lines(self) -> bool:
        """是否已创建网格线对象。"""
        return self.cache.get("grid_lines_actor") is not None

    def ensure_grid_lines(self, sim_data):
        """确保网格线对象存在（用于主窗口按需显示）。"""
        if self.has_grid_lines():
            return self.cache.get("grid_lines_actor")
        return self.create_grid_lines(sim_data)

    def toggle_grid_lines(self, show):
        if self.cache["grid_lines_actor"] is not None:
            self.cache["grid_lines_actor"].SetVisibility(show)
        self._render()

    def has_fractures(self) -> bool:
        """是否已创建裂缝对象。"""
        actors = self.cache.get("fracture_actors") or []
        return len(actors) > 0

    def ensure_fractures(self, sim_data) -> bool:
        """确保裂缝对象存在（用于主窗口按需显示）。"""
        if self.has_fractures():
            return True
        if not getattr(sim_data, "fractures", None):
            return False
        self.render_fractures(sim_data)
        return self.has_fractures()

    def toggle_fractures(self, show):
        if self.cache["pressure_actor"] is not None:
            self.cache["pressure_actor"].GetProperty().SetOpacity(0.3 if show else 1.0)
        for actor in self.cache["fracture_actors"]:
            actor.SetVisibility(show)
        self._render()

    def setup_camera(self, sim_data):
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
        self.plotter.clear_actors()
        if sim_data.fractures:
            self.render_fractures(sim_data)
        self.setup_camera(sim_data)
        self._render()

    def render_corner_point_grid(self, sim_data):
        if not sim_data.corner_point_grid or not sim_data.corner_point_grid.cells:
            return

        cpg = sim_data.corner_point_grid
        data_hash = hash((len(cpg.cells), tuple(cpg.cells[0].corners[0]) if cpg.cells else ()))
        if self.cache["corner_grid_hash"] == data_hash and self.cache["corner_actor"] is not None:
            self.cache["corner_actor"].SetVisibility(True)
            if self.cache["corner_surface_actor"] is not None:
                self.cache["corner_surface_actor"].SetVisibility(True)
            self.setup_camera_for_corner_grid(cpg)
            self._render()
            return

        self._remove_actor(self.cache["corner_actor"])
        self._remove_actor(self.cache["corner_surface_actor"])

        n_cells = len(cpg.cells)
        points = np.zeros((n_cells * 8, 3), dtype=np.float32)
        cell_types = np.full(n_cells, pv.CellType.HEXAHEDRON, dtype=np.uint8)
        cell_array = np.zeros(n_cells * 9, dtype=np.int64)
        
        for i, cell in enumerate(cpg.cells):
            points[i*8 : (i+1)*8] = cell.corners
            cell_array[i*9] = 8
            cell_array[i*9+1 : (i+1)*9] = np.arange(i*8, (i+1)*8)

        grid = pv.UnstructuredGrid(cell_array, cell_types, points)
        
        # 提取边和表面，如果为空则不显示
        if grid.n_points > 0 and grid.n_cells > 0:
            edges = grid.extract_feature_edges(boundary_edges=True, feature_edges=False, manifold_edges=False)
            if edges.n_points > 0:
                actor = self.plotter.add_mesh(edges, color="white", line_width=1.0, render=False)
                self.cache["corner_actor"] = actor
            
            surface = grid.extract_surface()
            if surface.n_points > 0:
                surface_actor = self.plotter.add_mesh(
                    surface,
                    color="gray",
                    opacity=0.15,
                    show_edges=False,
                    render=False,
                )
                self.cache["corner_surface_actor"] = surface_actor
        
        self.cache["corner_grid_hash"] = data_hash
        self.setup_camera_for_corner_grid(cpg)
        self._render()

    def setup_camera_for_corner_grid(self, cpg):
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
        self._remove_actor_list(self.cache["fracture_actors"])
        self.cache["fracture_actors"] = []
        if not sim_data.fractures:
            return

        grid_min_x = grid_min_y = grid_min_z = 0.0
        grid_max_x = sim_data.grid_info.get("Lx", 1000.0)
        grid_max_y = sim_data.grid_info.get("Ly", 500.0)
        grid_max_z = sim_data.grid_info.get("Lz", 100.0)

        for fracture in sim_data.fractures:
            all_pts = [list(pt) for pt in fracture["points"]]
            margin = 1.0
            out_of_bounds = False
            for pt in all_pts:
                if not (
                    grid_min_x - margin <= pt[0] <= grid_max_x + margin
                    and grid_min_y - margin <= pt[1] <= grid_max_y + margin
                    and grid_min_z - margin <= pt[2] <= grid_max_z + margin
                ):
                    out_of_bounds = True
                    break
            if out_of_bounds:
                continue

            center = np.mean(all_pts, axis=0)
            found_cell = None
            if sim_data.corner_point_grid:
                for cell in sim_data.corner_point_grid.cells:
                    xs = [corner[0] for corner in cell.corners]
                    ys = [corner[1] for corner in cell.corners]
                    zs = [corner[2] for corner in cell.corners]
                    if (
                        min(xs) <= center[0] <= max(xs)
                        and min(ys) <= center[1] <= max(ys)
                        and min(zs) <= center[2] <= max(zs)
                    ):
                        found_cell = cell
                        break

            if found_cell is not None:
                xs = [corner[0] for corner in found_cell.corners]
                ys = [corner[1] for corner in found_cell.corners]
                zs = [corner[2] for corner in found_cell.corners]
                for pt in all_pts:
                    pt[0] = max(min(xs), min(max(xs), pt[0]))
                    pt[1] = max(min(ys), min(max(ys), pt[1]))
                    pt[2] = max(min(zs), min(max(zs), pt[2]))

            polygon = pv.PolyData(np.array(all_pts, dtype=float))
            polygon.faces = np.array([4, 0, 1, 2, 3], dtype=np.int32)
            actor = self.plotter.add_mesh(
                polygon,
                color="red",
                opacity=0.8,
                show_edges=True,
                edge_color="darkred",
                line_width=2,
                render=False,
            )
            self.cache["fracture_actors"].append(actor)

            center_pos = np.mean(np.array(all_pts, dtype=float), axis=0)
            label_actor = self.plotter.add_point_labels(
                np.array([center_pos]),
                [str(fracture["id"])],
                point_size=0,
                font_size=12,
                text_color="green",
                always_visible=True,
                render=False,
            )
            self.cache["fracture_actors"].append(label_actor)

        self._render()

    def hide_fractures(self):
        self._remove_actor_list(self.cache["fracture_actors"])
        self.cache["fracture_actors"] = []
        self._render()

    def render_wells(self, sim_data):
        self._remove_actor_list(self.cache["well_actors"])
        self.cache["well_actors"] = []
        if not sim_data.wells:
            return

        for well in sim_data.wells:
            sphere = pv.Sphere(radius=5.0, center=(well["x"], well["y"], well["z"]))
            color = (0.0, 1.0, 0.0) if well["type"] == "Fracture" else (1.0, 1.0, 0.0)
            actor = self.plotter.add_mesh(sphere, color=color, smooth_shading=True, render=False)
            self.cache["well_actors"].append(actor)

        self._render()

    def hide_wells(self):
        self._remove_actor_list(self.cache["well_actors"])
        self.cache["well_actors"] = []
        self._render()

    def render_corner_wells(self, sim_data):
        self.render_wells(sim_data)

    def render_pressure_field(self, sim_data):
        if not sim_data.pressure_field:
            print("No pressure field data")
            return

        self._remove_actor(self.cache["pressure_field_actor"])
        if self.cache["pressure_scalar_bar"] is not None:
            try:
                self.renderer.RemoveActor2D(self.cache["pressure_scalar_bar"])
            except Exception:
                pass
            self.cache["pressure_scalar_bar"] = None

        self._render_pressure_field_points(sim_data.pressure_field)

    def render_corner_pressure_field(self, sim_data):
        if getattr(sim_data, "cell_geometry_with_pressure", None) is None:
            return

        self._remove_actor(self.cache["pressure_field_actor"])
        if self.cache["pressure_scalar_bar"] is not None:
            try:
                self.renderer.RemoveActor2D(self.cache["pressure_scalar_bar"])
            except Exception:
                pass
            self.cache["pressure_scalar_bar"] = None

        try:
            cell_data = sim_data.cell_geometry_with_pressure
            n_cells = cell_data.shape[0]
            if n_cells == 0:
                return

            # 使用 numpy 向量化提取数据
            pressures = cell_data[:, 28].astype(np.float32)
            # 提取 8 个角点坐标 (列 4-27)
            points = cell_data[:, 4:28].reshape(-1, 3).astype(np.float32)
            
            cell_types = np.full(n_cells, pv.CellType.HEXAHEDRON, dtype=np.uint8)
            cell_array = np.zeros(n_cells * 9, dtype=np.int64)
            cell_array[0::9] = 8
            for i in range(8):
                cell_array[i+1::9] = np.arange(i, n_cells * 8, 8)

            grid = pv.UnstructuredGrid(cell_array, cell_types, points)
            grid.cell_data["Pressure"] = pressures
            
            if grid.n_points > 0 and grid.n_cells > 0:
                surface = grid.cell_data_to_point_data().extract_surface()
                if surface.n_points > 0:
                    pressure_min = float(np.min(pressures))
                    pressure_max = float(np.max(pressures))
                    actor = self.plotter.add_mesh(
                        surface,
                        scalars="Pressure",
                        cmap="jet",
                        clim=[pressure_min, pressure_max],
                        opacity=0.9,
                        show_scalar_bar=False,
                        render=False,
                    )
                    scalar_bar = self._replace_scalar_bar(
                        "pressure_scalar_bar",
                        "Pressure (bar)",
                        position_x=0.82,
                        position_y=0.15,
                        width=0.08,
                        height=0.4,
                        label_font_size=10,
                        title_font_size=12,
                        color="white",
                        vertical=True,
                        render=False,
                    )

                    self.cache["pressure_field_actor"] = actor
                    self.cache["pressure_scalar_bar"] = scalar_bar
            
            self._render()
        except Exception as exc:
            print(f"ERROR in render_corner_pressure_field: {exc}")

    def _render_pressure_field_points(self, field_data):
        points = np.array([[x, y, z] for x, y, z, _ in field_data], dtype=float)
        pressures = np.array([p for _, _, _, p in field_data], dtype=float)
        pressure_min = float(np.min(pressures))
        pressure_max = float(np.max(pressures))

        cloud = pv.PolyData(points)
        cloud.point_data["Pressure"] = pressures
        actor = self.plotter.add_mesh(
            cloud,
            scalars="Pressure",
            cmap="jet",
            point_size=10,
            render_points_as_spheres=True,
            clim=[pressure_min, pressure_max],
            show_scalar_bar=False,
            render=False,
        )
        scalar_bar = self._replace_scalar_bar(
            "pressure_scalar_bar",
            "Pressure (bar)",
            position_x=0.82,
            position_y=0.15,
            width=0.08,
            height=0.4,
            label_font_size=10,
            title_font_size=12,
            color="white",
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
                self.renderer.RemoveActor2D(self.cache["pressure_scalar_bar"])
            except Exception:
                pass
            self.cache["pressure_scalar_bar"] = None
        self._render()

    def toggle_grid_visibility(self, visible):
        if self.cache["corner_actor"] is not None:
            self.cache["corner_actor"].SetVisibility(visible)
        if self.cache["corner_surface_actor"] is not None:
            self.cache["corner_surface_actor"].SetVisibility(visible)
        self._render()

    def toggle_fractures_visibility(self, visible):
        for actor in self.cache["fracture_actors"]:
            actor.SetVisibility(visible)

        if visible:
            if self.cache["corner_actor"] is not None:
                prop = self.cache["corner_actor"].GetProperty()
                if self.cache["original_grid_opacity"] is None:
                    self.cache["original_grid_opacity"] = prop.GetOpacity()
                prop.SetOpacity(0.1)

            if self.cache["pressure_field_actor"] is not None:
                prop = self.cache["pressure_field_actor"].GetProperty()
                if self.cache["original_pressure_opacity"] is None:
                    self.cache["original_pressure_opacity"] = prop.GetOpacity()
                prop.SetOpacity(0.1)
        else:
            if self.cache["corner_actor"] is not None and self.cache["original_grid_opacity"] is not None:
                self.cache["corner_actor"].GetProperty().SetOpacity(self.cache["original_grid_opacity"])

            if (
                self.cache["pressure_field_actor"] is not None
                and self.cache["original_pressure_opacity"] is not None
            ):
                self.cache["pressure_field_actor"].GetProperty().SetOpacity(self.cache["original_pressure_opacity"])

        self._render()

    def toggle_wells_visibility(self, visible):
        for actor in self.cache["well_actors"]:
            actor.SetVisibility(visible)
        self._render()

    def toggle_pressure_visibility(self, visible):
        if self.cache["pressure_field_actor"] is not None:
            self.cache["pressure_field_actor"].SetVisibility(visible)
        if self.cache["pressure_scalar_bar"] is not None:
            self.cache["pressure_scalar_bar"].SetVisibility(visible)
        self._render()

    def _create_grid_lines_actor(self, grid_geom, color, line_width, opacity):
        if grid_geom is None or grid_geom.shape[0] == 0:
            return None

        edges = [
            (0, 1), (1, 2), (2, 3), (3, 0),
            (4, 5), (5, 6), (6, 7), (7, 4),
            (0, 4), (1, 5), (2, 6), (3, 7),
        ]
        segments = []
        for cell_index in range(grid_geom.shape[0]):
            corners = []
            for corner_index in range(8):
                x = grid_geom[cell_index, corner_index * 3 + 0]
                y = grid_geom[cell_index, corner_index * 3 + 1]
                z = grid_geom[cell_index, corner_index * 3 + 2]
                corners.append((x, y, z))
            for start, end in edges:
                segments.append((corners[start], corners[end]))

        line_poly_data = self._polydata_from_line_segments(segments)
        if line_poly_data is None:
            return None

        return self.plotter.add_mesh(
            line_poly_data,
            color=color,
            line_width=line_width,
            opacity=opacity,
            render=False,
        )

    def render_corner_lgr_grid(self, sim_data):
        self._remove_actor(self.cache["corner_lgr_parent_grid_actor"])
        self._remove_actor(self.cache["corner_lgr_refined_grid_actor"])
        self.cache["corner_lgr_parent_grid_actor"] = None
        self.cache["corner_lgr_refined_grid_actor"] = None

        if getattr(sim_data, "corner_lgr_parent_grid_geometry", None) is not None:
            self.cache["corner_lgr_parent_grid_actor"] = self._create_grid_lines_actor(
                sim_data.corner_lgr_parent_grid_geometry,
                (0.5, 0.5, 0.5),
                0.5,
                0.3,
            )

        if getattr(sim_data, "corner_lgr_refined_grid_geometry", None) is not None:
            self.cache["corner_lgr_refined_grid_actor"] = self._create_grid_lines_actor(
                sim_data.corner_lgr_refined_grid_geometry,
                (0.2, 0.2, 0.2),
                1.0,
                0.8,
            )

        self._render()

    def toggle_corner_lgr_grid_visibility(self, visible):
        if self.cache["corner_lgr_parent_grid_actor"] is not None:
            self.cache["corner_lgr_parent_grid_actor"].SetVisibility(visible)
        if self.cache["corner_lgr_refined_grid_actor"] is not None:
            self.cache["corner_lgr_refined_grid_actor"].SetVisibility(visible)
        self._render()
