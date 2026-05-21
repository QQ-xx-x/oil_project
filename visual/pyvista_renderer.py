"""
基于 PyVista 的可视化渲染器。
"""

from __future__ import annotations

import sys
from pathlib import Path

def get_bright_jet_cmap():
    from matplotlib.colors import LinearSegmentedColormap
    bright_jet_colors = [
        (0.0, 0.0, 0.4),   
        (0.0, 0.0, 0.6),   # 深蓝
        (0.0, 0.2, 0.8),   # 中蓝
        (0.0, 0.6, 1.0),   # 亮蓝
        (0.0, 1.0, 1.0),   # 青
        (0.2, 1.0, 0.4),   # 绿青
        (0.8, 1.0, 0.2),   # 黄绿
        (1.0, 1.0, 0.0),   # 黄
        (1.0, 0.6, 0.0),   # 橙
        (1.0, 0.1, 0.0),   # 橙红
        
    ]
    return LinearSegmentedColormap.from_list("bright_jet", bright_jet_colors, N=512)

def get_soft_jet_cmap():
    """低饱和 jet colormap，适合浅色背景下的 pressure 结果层。"""
    from matplotlib.colors import LinearSegmentedColormap
    soft_jet_colors = [
        (0.14, 0.32, 0.74),   # 更明亮的深冷蓝
        (0.20, 0.56, 0.88),   # 更鲜明的中蓝
        (0.34, 0.82, 0.89),   # 明亮青蓝
        (0.88, 0.90, 0.46),   # 更亮的黄绿过渡
        (0.98, 0.72, 0.18),   # 更明艳的暖橙
        (0.90, 0.34, 0.24),   # 更有存在感的暖红
    ]
    return LinearSegmentedColormap.from_list("soft_jet", soft_jet_colors, N=512)

def _ensure_local_pyvista_site() -> None:
    project_root = Path(__file__).resolve().parent.parent
    local_site = project_root / ".deps" / "pyvista_site"
    local_site_str = str(local_site)
    if local_site.exists() and local_site_str not in sys.path:
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

        self.view = qt_view
        self.pv_renderer = qt_view.renderer

        pv.global_theme.allow_empty_mesh = True

        self.plotter.enable_anti_aliasing()
        self.plotter.enable_depth_peeling()

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
            "selection_outline_actor": None,
            "selection_fill_actor": None,
            "selection_handle_actors": [],
            "layer_pressure_actor": None,
            "layer_pressure_scalar_bar": None,
            "layer_coarse_grid_actor": None,
            "layer_frac_actors": [],
            "layer_well_actors": [],
        }

    def _render(self):
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

    def clear_scene(self):

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
        self._remove_actor_list(self.cache.get("selection_handle_actors", []))

        try:
            self.plotter.remove_scalar_bar(render=False)
        except Exception:
            pass

        self.cache = self._new_cache()

        self._render()

    def clear_cache(self):
        self.plotter.clear()  # 彻底清空所有actor
        self.cache = self._new_cache()
        self._selection_overlay_state = {
            "world_bounds": None,
            "handle_radius": None,
            "outline_mesh": None,
            "fill_mesh": None,
        }
        self._render()
    # ========================================================================

    def _remove_actor(self, actor):
        if actor is None:
            return
        try:
            self.plotter.remove_actor(
                actor,
                render=False
            )
        except Exception:
            pass

    def _remove_actor_list(self, actors):
        for actor in actors:
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

        surface = grid.extract_surface()
        min_p = float(np.min(scalars))
        max_p = float(np.max(scalars))

        actor = self.plotter.add_mesh(
            surface,
            scalars="Pressure",
            cmap=get_soft_jet_cmap(),
            clim=[min_p, max_p],
            show_scalar_bar=False,
            opacity=0.96,
            render=False,
        )

        scalar_bar = self._replace_scalar_bar(
            "scalar_bar",
            "Pressure (MPa)",
            label_font_size=18,
            title_font_size=20,
            color="#2f3640",
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
                    color=(0.72, 0.38, 0.38),
                    opacity=0.85,
                    show_edges=False,
                    edge_color=(0.54, 0.29, 0.29),
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
                        color=(0.54, 0.29, 0.29),
                        line_width=1.5,
                        render=False,
                    )
                    self.cache["fracture_actors"].append(edge_actor)

        self._render()

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

    def has_fractures(self) -> bool:
        actors = self.cache.get("fracture_actors") or []
        return len(actors) > 0

    def ensure_fractures(self, sim_data) -> bool:
        if self.has_fractures():
            return True
        if not getattr(sim_data, "fractures", None):
            return False
        self.render_fractures(sim_data)
        return self.has_fractures()

    def toggle_fractures(self, show):
        if self.cache["pressure_actor"] is not None:
            self.cache["pressure_actor"].prop.opacity = 0.3 if show else 1.0
        for actor in self.cache["fracture_actors"]:
            actor.visibility = show
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

        data_hash = hash(str(len(cpg.cells)) + str(cpg.cells[0].corners[0]) if cpg.cells else 0)

        if self.cache.get('corner_grid_hash') == data_hash and self.cache.get('corner_actor') is not None:
            self.cache['corner_actor'].visibility = True
            self.cache['corner_surface_actor'].visibility = True
            self.setup_camera_for_corner_grid(cpg)
            self.plotter.render()
            return

        self._remove_actor(self.cache.get('corner_actor'))
        self._remove_actor(self.cache.get('corner_surface_actor'))

        all_points = []
        cells = []
        offset = 0

        for cell in cpg.cells:
            pts = np.array(cell.corners)
            all_points.append(pts)
            cells.append([8, offset, offset+1, offset+2, offset+3, offset+4, offset+5, offset+6, offset+7])
            offset += 8

        all_points = np.vstack(all_points)
        cells = np.hstack(cells)
        cell_types = np.full(len(cpg.cells), pv.CellType.HEXAHEDRON, dtype=np.uint8)

        grid = pv.UnstructuredGrid(cells, cell_types, all_points)

        edges = grid.extract_all_edges()

        actor = self.plotter.add_mesh(
            edges,
            color=(0.67, 0.72, 0.78),
            line_width=1.0,
            render=False
        )

        surface = grid.extract_surface()
        surface_actor = self.plotter.add_mesh(
            surface,
            color=(0.82, 0.85, 0.89),
            opacity=0.15,
            show_edges=False,
            render=False
        )

        self.cache['corner_grid_hash'] = data_hash
        self.cache['corner_actor'] = actor
        self.cache['corner_surface_actor'] = surface_actor

        self.setup_camera_for_corner_grid(cpg)
        self.plotter.render()

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

    # 旧实现（注释块，不执行）——生效版本见下方 render_corner_fractures()
    """def render_corner_fractures(self, sim_data):
        self._remove_actor_list(self.cache["fracture_actors"])
        self.cache["fracture_actors"] = []

        if not sim_data.fractures:
            return

        grid_min_x = grid_min_y = grid_min_z = 0.0
        grid_max_x = sim_data.grid_info.get("Lx", 1000.0)
        grid_max_y = sim_data.grid_info.get("Ly", 500.0)
        grid_max_z = sim_data.grid_info.get("Lz", 100.0)

        for fracture in sim_data.fractures:

            # =========================================================
            # 裂缝类型判断
            # is_hydraulic:
            #   1 -> 人工裂缝
            #   0 -> 天然裂缝
            # =========================================================

            is_hydraulic = int(fracture.get("is_hydraulic", 0)) == 1 or fracture.get("type") == "hydraulic"

            if is_hydraulic:
                # 人工裂缝
                frac_color = (1.0, 0.0, 0.0)
                edge_color = (0.75, 0.0, 0.0)

                ambient = 0.85
                diffuse = 0.35
                specular = 0.45

            else:
                # 天然裂缝
                frac_color = (0.0, 0.25, 0.4)
                edge_color = (0.0, 0.15, 0.25)

                ambient = 0.85
                diffuse = 0.65
                specular = 0.10

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

            points = np.array(all_pts, dtype=float)

            polygon = pv.PolyData(points)

            polygon.faces = np.array(
                [len(all_pts), *range(len(all_pts))],
                dtype=np.int32
            )

            actor = self.plotter.add_mesh(
                polygon,

                color=frac_color,
                edge_color=edge_color,

                opacity=0.92,

                show_edges=True,
                line_width=1.5,

                lighting=True,
                smooth_shading=True,

                ambient=ambient,
                diffuse=diffuse,
                specular=specular,
                specular_power=20,

                render=False,
            )

            self.cache["fracture_actors"].append(actor)

        self._render()"""

    #不处理裂缝数据，直接渲染
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

            # =========================================================
            # 裂缝类型判断
            # is_hydraulic:
            #   1 -> 人工裂缝
            #   0 -> 天然裂缝
            # =========================================================
            is_hydraulic = int(fracture.get("is_hydraulic", 0)) == 1 or fracture.get("type") == "hydraulic"

            if is_hydraulic:
                # 人工裂缝
                frac_color = (0.72, 0.38, 0.38)
                edge_color = (0.54, 0.29, 0.29)
                ambient = 0.85
                diffuse = 0.35
                specular = 0.45
            else:
                # 天然裂缝
                frac_color = (0.0, 0.25, 0.4)
                edge_color = (0.0, 0.15, 0.25)
                ambient = 0.85
                diffuse = 0.65
                specular = 0.10

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

            points = np.array(all_pts, dtype=float)
            polygon = pv.PolyData(points)
            polygon.faces = np.array(
                [len(all_pts), *range(len(all_pts))],
                dtype=np.int32
            )

            actor = self.plotter.add_mesh(
                polygon,
                color=frac_color,
                edge_color=edge_color,
                opacity=0.92,
                show_edges=True,
                line_width=1.5,
                lighting=True,
                smooth_shading=True,
                ambient=ambient,
                diffuse=diffuse,
                specular=specular,
                specular_power=20,
                render=False,
            )
            self.cache["fracture_actors"].append(actor)

        self._render()

    def hide_fractures(self):
        self._remove_actor_list(self.cache["fracture_actors"])
        self.cache["fracture_actors"] = []
        self._render()

    #渲染井
    def render_wells(self, sim_data):
        self._remove_actor_list(self.cache["well_actors"])
        self.cache["well_actors"] = []

        if not getattr(sim_data, "fractures", None):
            return

        centers = []

        grid_min_x = grid_min_y = grid_min_z = 0.0
        grid_max_x = sim_data.grid_info.get("Lx", 1000.0)
        grid_max_y = sim_data.grid_info.get("Ly", 500.0)
        grid_max_z = sim_data.grid_info.get("Lz", 100.0)

        for frac in sim_data.fractures:

            if not (int(frac.get("is_hydraulic", 0)) == 1 or frac.get("type") == "hydraulic"):
                continue

            all_pts = np.array(frac["points"], dtype=float)
            if len(all_pts) < 3:  
                continue

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

            real_center = np.mean(all_pts, axis=0)
            centers.append(real_center)

        if len(centers) < 2:
            return

        centers = np.array(centers)
        sorted_idx = np.argsort(centers[:, 0])
        ordered_centers = centers[sorted_idx]

        segments = [
            (ordered_centers[i].tolist(), ordered_centers[i+1].tolist())
            for i in range(len(ordered_centers)-1)
        ]

        well_line = self._polydata_from_line_segments(segments)
        if well_line is not None:
            actor = self.plotter.add_mesh(
                well_line.tube(radius=2.0),
                color=(0.31, 0.35, 0.40),
                opacity=1.0,
                lighting=True,
                ambient=0.9,
                diffuse=1.0,
                render=False
            )
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

            pressures = cell_data[:, 28].astype(np.float32)
            pressure_min = float(np.min(pressures))
            pressure_max = float(np.max(pressures))

            raw_points = cell_data[:, 4:28].reshape(-1, 3).astype(np.float32)

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

            #体渲染
            """
            actor = self.plotter.add_volume(
                grid,
                scalars="Pressure",
                cmap=get_bright_jet_cmap(),
                clim=[pressure_min, pressure_max],
                opacity=np.full(256, 1.0),
                opacity_unit_distance=25.0,
                blending="composite",
                shade=False,
                mapper="gpu",
                diffuse=1.0,
                ambient=0.55,
                specular=0.15,
                specular_power=30,
                show_scalar_bar=False,
                render=False,
            )
            """
            #面渲染

            surface = grid.extract_surface()
            
            actor = self.plotter.add_mesh(
                surface,
                scalars="Pressure",
                cmap=get_soft_jet_cmap(),
                clim=[pressure_min, pressure_max],
                show_edges=False,
                opacity=0.72,
                show_scalar_bar=False,
                render=False,
                lighting=False,
                smooth_shading=True,
                ambient=1.0,
                diffuse=0.0,
                specular=0.0,
                specular_power=50,
                interpolate_before_map=True,
            )

            scalar_bar = self._replace_scalar_bar(
                "pressure_scalar_bar",
                "Pressure (bar)",
                position_x=0.82,
                position_y=0.15,
                width=0.08,
                height=0.40,
                label_font_size=18,
                title_font_size=20,
                color="#2f3640",
                vertical=True,
                render=False,
            )

            self.cache["pressure_field_actor"] = actor
            self.cache["pressure_scalar_bar"] = scalar_bar

            if getattr(sim_data, "fractures", None):
                self.render_corner_fractures(sim_data)

            if getattr(sim_data, "wells", None):
                self.render_corner_wells(sim_data)

            self._render()

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
            grid,
            scalars="Pressure",
            cmap=get_soft_jet_cmap(),
            clim=[pressure_min, pressure_max],
            opacity=0.7,
            opacity_unit_distance=50,
            blending="maximum",
            shade=False,
            mapper="gpu",
        )
        scalar_bar = self._replace_scalar_bar(
            "pressure_scalar_bar",
            "Pressure (bar)",
            position_x=0.82,
            position_y=0.15,
            width=0.08,
            height=0.4,
            label_font_size=18,
            title_font_size=20,
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
        if self.cache["corner_actor"] is not None:
            self.cache["corner_actor"].visibility = visible
        if self.cache["corner_surface_actor"] is not None:
            self.cache["corner_surface_actor"].visibility = visible
        if self.cache.get("layer_coarse_grid_actor") is not None:
            self.cache["layer_coarse_grid_actor"].visibility = visible
        self._render()

    def toggle_fractures_visibility(self, visible):
        for actor in self.cache.get("fracture_actors", []):
            try:
                actor.visibility = visible
            except Exception:
                pass

        for actor in self.cache.get("layer_frac_actors", []):
            try:
                actor.visibility = visible
            except Exception:
                pass

        pressure_actor = self.cache.get("pressure_field_actor")

        if pressure_actor is not None:
            try:
                prop = pressure_actor.GetProperty()

                if visible:
                    prop.SetAmbient(0.45)
                    prop.SetDiffuse(0.85)

                else:
                    prop.SetAmbient(0.25)
                    prop.SetDiffuse(1.0)

            except Exception:
                pass

        self._render()

    def toggle_wells_visibility(self, visible):
        for actor in self.cache["well_actors"]:
            actor.visibility = visible
        for actor in self.cache.get("layer_well_actors", []):
            try:
                actor.visibility = visible
            except Exception:
                pass
        self._render()

    def toggle_pressure_visibility(self, visible):
        pressure_actor = self.cache.get("pressure_field_actor")
        if pressure_actor is not None:
            try:
                pressure_actor.SetVisibility(visible)
            except Exception:
                pass

        scalar_bar = self.cache.get("pressure_scalar_bar")
        if scalar_bar is not None:
            try:
                scalar_bar.visibility = visible
            except Exception:
                pass

        layer_pressure = self.cache.get("layer_pressure_actor")
        if layer_pressure is not None:
            try:
                layer_pressure.SetVisibility(visible)
            except Exception:
                pass

        layer_scalar_bar = self.cache.get("layer_pressure_scalar_bar")
        if layer_scalar_bar is not None:
            try:
                layer_scalar_bar.visibility = visible
            except Exception:
                pass

        self._render()

    def apply_layer_visibility(self, show_grid, show_fractures, show_wells, show_pressure):
        """Apply visibility only to layer-render actors."""
        layer_grid = self.cache.get("layer_coarse_grid_actor")
        if layer_grid is not None:
            try:
                layer_grid.visibility = show_grid
            except Exception:
                pass

        for actor in self.cache.get("layer_frac_actors", []):
            try:
                actor.visibility = show_fractures
            except Exception:
                pass

        for actor in self.cache.get("layer_well_actors", []):
            try:
                actor.visibility = show_wells
            except Exception:
                pass

        layer_pressure = self.cache.get("layer_pressure_actor")
        if layer_pressure is not None:
            try:
                layer_pressure.SetVisibility(show_pressure)
            except Exception:
                pass

        layer_scalar_bar = self.cache.get("layer_pressure_scalar_bar")
        if layer_scalar_bar is not None:
            try:
                layer_scalar_bar.visibility = show_pressure
            except Exception:
                pass

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

    # 旧实现（注释块，不执行）——生效版本见下方 render_corner_lgr_grid()
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

            surface = grid.extract_surface()
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

        self._remove_actor(self.cache["corner_lgr_parent_grid_actor"])
        self._remove_actor(self.cache["corner_lgr_refined_grid_actor"])

        self.cache["corner_lgr_parent_grid_actor"] = None
        self.cache["corner_lgr_refined_grid_actor"] = None

        #父网格（浅灰蓝）
        if getattr(sim_data, "corner_lgr_parent_grid_geometry", None) is not None:

            self.cache["corner_lgr_parent_grid_actor"] = self._create_grid_lines_actor(
                sim_data.corner_lgr_parent_grid_geometry,
                (0.78, 0.82, 0.87),
                0.4,
                0.15,
            )

        # 加密网格（稍深灰蓝，层次清晰）
        refined_geom = getattr(sim_data, "corner_lgr_refined_grid_geometry", None)

        if refined_geom is not None:

            self.cache["corner_lgr_refined_grid_actor"] = self._create_grid_lines_actor(
                refined_geom,
                (0.64, 0.69, 0.76),
                0.45,
                0.20,
            )

        self._render()

    def toggle_corner_lgr_grid_visibility(self, visible):
        if self.cache["corner_lgr_parent_grid_actor"] is not None:
            self.cache["corner_lgr_parent_grid_actor"].visibility = visible
        if self.cache["corner_lgr_refined_grid_actor"] is not None:
            self.cache["corner_lgr_refined_grid_actor"].visibility = visible
        self._render()

    def set_full_corner_result_visibility(self, visible):
        """Hide/show full-field corner result actors without affecting layer actors."""
        if self.cache.get("corner_actor") is not None:
            self.cache["corner_actor"].visibility = visible
        if self.cache.get("corner_surface_actor") is not None:
            self.cache["corner_surface_actor"].visibility = visible

        pressure_actor = self.cache.get("pressure_field_actor")
        if pressure_actor is not None:
            try:
                pressure_actor.SetVisibility(visible)
            except Exception:
                pass

        scalar_bar = self.cache.get("pressure_scalar_bar")
        if scalar_bar is not None:
            try:
                scalar_bar.visibility = visible
            except Exception:
                pass

        for actor in self.cache.get("fracture_actors", []):
            try:
                actor.visibility = visible
            except Exception:
                pass

        for actor in self.cache.get("well_actors", []):
            try:
                actor.visibility = visible
            except Exception:
                pass

        if self.cache.get("corner_lgr_parent_grid_actor") is not None:
            self.cache["corner_lgr_parent_grid_actor"].visibility = visible
        if self.cache.get("corner_lgr_refined_grid_actor") is not None:
            self.cache["corner_lgr_refined_grid_actor"].visibility = visible

        self._render()

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

    # 新增：根据 Z 坐标渲染地质切片  
    def render_corner_grid_by_layer_k(self, sim_data, k_layer: int):

        self._remove_actor(self.cache.get("layer_pressure_actor"))
        self._remove_actor(self.cache.get("layer_coarse_grid_actor"))

        self._remove_actor_list(self.cache.get("layer_frac_actors", []))
        self._remove_actor_list(self.cache.get("layer_well_actors", []))

        self.cache["layer_frac_actors"] = []
        self.cache["layer_pressure_actor"] = None
        self.cache["layer_well_actors"] = []
        self.cache["layer_coarse_grid_actor"] = None

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

        if coarse_points:
            coarse_grid = pv.UnstructuredGrid(
                np.array(coarse_cell_array, dtype=np.int64),
                np.array(coarse_cell_types, dtype=np.uint8),
                np.array(coarse_points, dtype=np.float32)
            )

            if coarse_grid.n_points > 0:
                coarse_edges = coarse_grid.extract_all_edges()
                if coarse_edges.n_points > 0:
                    coarse_actor = self.plotter.add_mesh(
                        coarse_edges,
                        color=(0.78, 0.82, 0.87),
                        line_width=1,
                        opacity=1,
                        render=False,
                    )
                    self.cache["layer_coarse_grid_actor"] = coarse_actor

        all_data = sim_data.cell_geometry_with_pressure
        selected_rows = []

        for row in all_data:
            pts = row[4:28].reshape(8, 3)
            cx, cy, cz = pts.mean(axis=0)
            inside = any(
                box["xmin"] <= cx <= box["xmax"] and
                box["ymin"] <= cy <= box["ymax"] and
                box["zmin"] <= cz <= box["zmax"]
                for box in coarse_boxes
            )
            if inside:
                selected_rows.append(row)

        if not selected_rows:
            print(f"No refined cells found for k layer = {k_layer}")
            self._render()
            return

        selected_rows = np.array(selected_rows)

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
        pressures = selected_rows[:, 28].astype(np.float32)
        pressures_all = sim_data.cell_geometry_with_pressure[:, 28].astype(np.float32)
        grid.cell_data["Pressure"] = pressures
        grid = grid.cell_data_to_point_data()

        surface = grid.extract_surface()
        actor = self.plotter.add_mesh(
            surface,
            scalars="Pressure",
            cmap=get_soft_jet_cmap(),
            clim=[float(np.min(pressures_all)), float(np.max(pressures_all))],
            opacity=0.72,
            show_scalar_bar=False,
            show_edges=False,
            lighting=False,
            smooth_shading=False,
            ambient=1.0,
            diffuse=0.0,
            specular=0.0,
            interpolate_before_map=True,
            render=False,
        )

        scalar_bar = self._replace_scalar_bar(
            "layer_pressure_scalar_bar",
            "Pressure (bar)",
            position_x=0.82,
            position_y=0.15,
            width=0.08,
            height=0.4,
            label_font_size=18,
            title_font_size=20,
            color="#2f3640",
            vertical=True,
            render=False,
        )

        self.cache["layer_pressure_actor"] = actor
        self.cache["layer_pressure_scalar_bar"] = scalar_bar

        # -------------------------
        # 天然裂缝保持原逻辑
        # -------------------------
        if hasattr(sim_data, "fractures"):
            for frac in sim_data.fractures:
                if int(frac.get("is_hydraulic", 0)) == 1 or frac.get("type") == "hydraulic":
                    continue  # 人工裂缝单独处理

                pts = np.array(frac["points"], dtype=np.float64)
                if len(pts) < 3:
                    continue

                cx, cy, cz = pts.mean(axis=0)
                inside = any(
                    box["xmin"] <= cx <= box["xmax"] and
                    box["ymin"] <= cy <= box["ymax"] and
                    box["zmin"] <= cz <= box["zmax"]
                    for box in coarse_boxes
                )
                if not inside:
                    continue

                poly = pv.PolyData(pts)
                poly.faces = [len(pts), *range(len(pts))]

                fcolor = (0.0, 0.25, 0.4)
                ecolor = (0.0, 0.15, 0.25)

                fac = self.plotter.add_mesh(
                    poly,
                    color=fcolor,
                    edge_color=ecolor,
                    show_edges=True,
                    line_width=1.5,
                    opacity=0.9,
                    render=False
                )
                self.cache["layer_frac_actors"].append(fac)

        # -------------------------
        # 人工裂缝显示规则：只要一个人工裂缝在层内，显示所有人工裂缝
        # -------------------------
        show_all_hydraulic = False
        for frac in sim_data.fractures:
            if not (int(frac.get("is_hydraulic", 0)) == 1 or frac.get("type") == "hydraulic"):
                continue
            pts = np.array(frac["points"], dtype=np.float64)
            if len(pts) < 3:
                continue
            cx, cy, cz = pts.mean(axis=0)
            if any(box["xmin"] <= cx <= box["xmax"] and
                box["ymin"] <= cy <= box["ymax"] and
                box["zmin"] <= cz <= box["zmax"] for box in coarse_boxes):
                show_all_hydraulic = True
                break

        if show_all_hydraulic:
            for frac in sim_data.fractures:
                if not (int(frac.get("is_hydraulic", 0)) == 1 or frac.get("type") == "hydraulic"):
                    continue  # 只显示人工裂缝
                pts = np.array(frac["points"], dtype=np.float64)
                if len(pts) < 3:
                    continue
                poly = pv.PolyData(pts)
                poly.faces = [len(pts), *range(len(pts))]
                fcolor = (0.72, 0.38, 0.38)
                ecolor = (0.54, 0.29, 0.29)
                fac = self.plotter.add_mesh(
                    poly,
                    color=fcolor,
                    edge_color=ecolor,
                    show_edges=True,
                    line_width=1.5,
                    opacity=0.9,
                    render=False
                )
                self.cache["layer_frac_actors"].append(fac)

        well_centers = []

        if show_all_hydraulic:

            for frac in sim_data.fractures:

                if not (int(frac.get("is_hydraulic", 0)) == 1 or frac.get("type") == "hydraulic"):
                    continue

                pts = np.array(frac["points"], dtype=np.float64)

                if len(pts) < 3:
                    continue

                cx, cy, cz = pts.mean(axis=0)

                well_centers.append([cx, cy, cz])

        if len(well_centers) >= 2:

            well_centers = np.array(well_centers)

            well_centers = well_centers[
                np.argsort(well_centers[:, 0])
            ]

            segments = [
                (
                    well_centers[i].tolist(),
                    well_centers[i + 1].tolist()
                )
                for i in range(len(well_centers) - 1)
            ]

            well_line = self._polydata_from_line_segments(segments)

            if well_line:

                actor = self.plotter.add_mesh(
                    well_line.tube(radius=2.0),
                    color=(0.31, 0.35, 0.40),
                    opacity=1.0,
                    lighting=True,
                    ambient=0.9,
                    diffuse=1.0,
                    render=False
                )

                self.cache["layer_well_actors"].append(actor)

        self._render()
