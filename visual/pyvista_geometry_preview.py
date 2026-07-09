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
PREVIEW_MAIN_LIGHT_INTENSITY = 1.6

GRID_SHOW_SURFACE = True
GRID_SHOW_EDGES = True
GRID_SURFACE_COLOR = (1.0, 1.0, 1.0)
GRID_SURFACE_OPACITY = 0.2
GRID_EDGE_COLOR = (0.5, 0.5, 0.5)
GRID_EDGE_LINE_WIDTH = 1.0

WELL_COLOR = (0.08, 0.24, 0.62)
WELL_RADIUS = 2.0
WELL_OPACITY = 0.999
WELL_TUBE_SIDES = 16
WELL_FALLBACK_LINE_WIDTH = 4.0

NATURAL_FRACTURE_COLOR = (0.0, 0.25, 0.4)
NATURAL_FRACTURE_EDGE_COLOR = (0.0, 0.15, 0.25)
HYDRAULIC_FRACTURE_COLOR = (0.72, 0.38, 0.38)
HYDRAULIC_FRACTURE_EDGE_COLOR = (0.54, 0.29, 0.29)
FRACTURE_OPACITY = 0.999
FRACTURE_SHOW_EDGES = False
FRACTURE_EDGE_LINE_WIDTH = 0

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
        self.natural_fracture_actors = []
        self.hydraulic_fracture_actors = []

    def _configure_preview_scene(self):
        if PREVIEW_ENABLE_ANTI_ALIASING:
            try:
                self.plotter.enable_anti_aliasing()
            except Exception:
                pass

        if PREVIEW_ENABLE_DEPTH_PEELING:
            try:
                self.plotter.enable_depth_peeling()
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

    def clear_grid(self, render_now=True):
        self._remove_actor(self.grid_actor)
        self._remove_actor(self.grid_edge_actor)

        self.grid_actor = None
        self.grid_edge_actor = None

        if render_now:
            self._render()

    def clear_wells(self, render_now=True):
        self._remove_actor_list(self.well_actors)
        self.well_actors = []

        if render_now:
            self._render()

    def clear_natural_fractures(self, render_now=True):
        self._remove_actor_list(self.natural_fracture_actors)
        self.natural_fracture_actors = []

        if render_now:
            self._render()

    def clear_hydraulic_fractures(self, render_now=True):
        self._remove_actor_list(self.hydraulic_fracture_actors)
        self.hydraulic_fracture_actors = []

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

        if render_now:
            self._render()

    def render_grid(
        self,
        sim_data,
        render_now=True,
    ):
        self._configure_preview_scene()
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

        if GRID_SHOW_EDGES:
            edges = grid.extract_all_edges()

            if edges is not None and edges.n_points > 0:
                self.grid_edge_actor = self.plotter.add_mesh(
                    edges,
                    color=GRID_EDGE_COLOR,
                    line_width=GRID_EDGE_LINE_WIDTH,
                    render=False,
                )

        if GRID_SHOW_SURFACE:
            surface = grid.extract_surface()

            self.grid_actor = self.plotter.add_mesh(
                surface,
                color=GRID_SURFACE_COLOR,
                opacity=GRID_SURFACE_OPACITY,
                show_edges=False,
                render=False,
            )

        try:
            self.plotter.reset_camera()
            self.plotter.reset_camera_clipping_range()
        except Exception:
            pass

        if render_now:
            self._render()

        return self.grid_actor or self.grid_edge_actor

    def render_wells(
        self,
        sim_data,
        render_now=True,
    ):
        self._configure_preview_scene()
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

            polyline = self._polyline_from_points(
                ordered_points,
            )

            if polyline is None:
                continue

            try:
                tube = polyline.tube(
                    radius=WELL_RADIUS,
                    n_sides=WELL_TUBE_SIDES,
                    capping=True,
                )

                actor = self.plotter.add_mesh(
                    tube,
                    color=WELL_COLOR,
                    opacity=WELL_OPACITY,
                    lighting=True,
                    ambient=0.9,
                    diffuse=1.0,
                    render=False,
                )

            except Exception:
                actor = self.plotter.add_mesh(
                    polyline,
                    color=WELL_COLOR,
                    line_width=WELL_FALLBACK_LINE_WIDTH,
                    opacity=WELL_OPACITY,
                    lighting=False,
                    render=False,
                )

            self.well_actors.append(actor)
            count += 1

        if render_now:
            self._render()

        return count > 0

    def render_natural_fractures(
        self,
        sim_data,
        render_now=True,
    ):
        self._configure_preview_scene()
        self.clear_natural_fractures(render_now=False)

        count = self._render_natural_fractures(
            sim_data,
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
                color=NATURAL_FRACTURE_COLOR,
                edge_color=NATURAL_FRACTURE_EDGE_COLOR,
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
        self._configure_preview_scene()
        self.clear_hydraulic_fractures(render_now=False)

        count = self._render_hydraulic_fractures(
            sim_data,
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
                    color=HYDRAULIC_FRACTURE_COLOR,
                    edge_color=HYDRAULIC_FRACTURE_EDGE_COLOR,
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
        self._configure_preview_scene()
        self.clear_fractures(render_now=False)

        total_count = 0

        total_count += self._render_natural_fractures(
            sim_data,
        )

        total_count += self._render_hydraulic_fractures(
            sim_data,
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

    def _add_fracture_polygon(
        self,
        points,
        color,
        edge_color,
    ):
        points = self._safe_points(points)

        if points is None or len(points) < 3:
            return []

        actors = []

        try:
            polygon = pv.PolyData(points)

            polygon.faces = np.asarray(
                [len(points), *range(len(points))],
                dtype=np.int32,
            )

            actor = self.plotter.add_mesh(
                polygon,
                color=color,
                opacity=FRACTURE_OPACITY,
                show_edges=FRACTURE_SHOW_EDGES,
                edge_color=edge_color,
                line_width=1.0,
                render=False,
            )

            actors.append(actor)

            if FRACTURE_EDGE_LINE_WIDTH > 0:
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
                        line_width=FRACTURE_EDGE_LINE_WIDTH,
                        render=False,
                    )

                    actors.append(edge_actor)

            return actors

        except Exception:
            return []

    def _remove_actor(self, actor):
        if actor is None:
            return

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
        if hasattr(self.host, "_render"):
            self.host._render()
        else:
            self.plotter.render()