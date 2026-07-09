"""
基于 PyVista 的可视化渲染器。
"""

from __future__ import annotations

import sys
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

        # 绿色区缩短
        (0.26, (0.00, 1.00, 0.35)),
        (0.30, (0.08, 1.00, 0.22)),
        (0.34, (0.18, 1.00, 0.10)),

        # 绿到黄的过渡拉长
        (0.38, (0.32, 1.00, 0.02)),
        (0.42, (0.48, 1.00, 0.00)),
        (0.46, (0.62, 1.00, 0.00)),
        (0.50, (0.78, 1.00, 0.00)),
        (0.54, (0.92, 1.00, 0.00)),

        # 黄色区加宽
        (0.58, (1.00, 1.00, 0.00)),
        (0.63, (1.00, 0.94, 0.00)),
        (0.68, (1.00, 0.86, 0.00)),
        (0.73, (1.00, 0.76, 0.00)),

        # 黄橙红
        (0.78, (1.00, 0.64, 0.00)),
        (0.84, (1.00, 0.48, 0.00)),
        (0.90, (1.00, 0.34, 0.00)),
        (0.95, (1.00, 0.18, 0.00)),
        (1.00, (1.00, 0.00, 0.00)),
    ]
    return LinearSegmentedColormap.from_list("bright_jet", bright_jet_colors, N=4096)

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
# 固定三面坐标系网格密度。
COORDINATE_APPROX_DIVISIONS = 6
COORDINATE_LABEL_FONT_SIZE = 12
COORDINATE_TICK_LENGTH_RATIO = 0.010
COORDINATE_TICK_LABEL_OFFSET_RATIO = 0.025
COORDINATE_AXIS_TITLE_GAP_RATIO = 0.028
COORDINATE_LABEL_DEPTH_OFFSET_RATIO = 0.003
COORDINATE_LABEL_SCREEN_EPSILON_PX = 2.0
# 相机视线与 X / Y / Z 轴足够接近时，认为是标准六向视图。
COORDINATE_STANDARD_VIEW_COS_THRESHOLD = 0.999

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

        pv.global_theme.allow_empty_mesh = True

        self.plotter.enable_anti_aliasing()
        self.plotter.enable_depth_peeling()
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
        # 静态属性预览渲染器
        from .pyvista_static_property_preview import StaticPropertyPreviewRenderer
        self.static_property_preview = StaticPropertyPreviewRenderer(self)
        # 几何预览渲染器
        from .pyvista_geometry_preview import GeometryPreviewRenderer
        self.geometry_preview = GeometryPreviewRenderer(self)


    #箭头
    def _add_petrel_arrow(self):

        shaft = pv.Box(
            bounds=(
                0.0, 0.62,
                -0.14, 0.14,
                -0.05, 0.05
            )
        )
        pts = np.array([

            # 前面
            [0.62, -0.30, -0.05],
            [0.62,  0.30, -0.05],
            [1.08,  0.00, -0.05],

            # 后面
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

    # =====================================================================
    # 动态三面三维坐标系
    # =====================================================================
    def _clear_fixed_coordinate_axes(self):
        """
        删除当前坐标系的网格、刻度线、边框和文字。
        不移除相机监听器。
        """
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
        """
        将普通数值转换为适合显示的坐标刻度步长。
        """
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

        # ---------------------------------------------------------
        # 标准六视图隐藏轴规则。
        # ---------------------------------------------------------
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

        # 左视图 / 右视图时：
        # X 是屏幕深度方向。
        # 因此 Z 轴刻度和 Z 标签要沿 Y 方向偏移。
        is_side_x_view = (
            hidden_axis == "x"
        )

        # 当前三个坐标面。
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

        # 对应另一侧边界。
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

        # 从坐标面向外偏移的方向。
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

        # 从外侧边向外偏移的方向。
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

        # ---------------------------------------------------------
        # 网格刻度。
        # ---------------------------------------------------------
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

        # ---------------------------------------------------------
        # 基于模型最大尺寸计算距离。
        # ---------------------------------------------------------
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

        # 主轴样式。
        axis_color = (0.12, 0.12, 0.12)
        axis_line_width = 1.8

        # 普通灰色边框样式。
        edge_color = (0.58, 0.58, 0.58)
        edge_line_width = 1.0

        # 内部网格样式。
        grid_color = (0.62, 0.62, 0.62)
        grid_line_width = 0.7

        label_specs = []

        # =========================================================
        # 1. XY 平面
        # z = z_plane
        # =========================================================

        # 前方 X 主轴。
        if show_x_axis:
            self._add_fixed_coordinate_line(
                (xmin, y_outer, z_plane),
                (xmax, y_outer, z_plane),
                color=axis_color,
                line_width=axis_line_width,
                opacity=1.0,
            )

        # 前方 Y 主轴。
        if show_y_axis:
            self._add_fixed_coordinate_line(
                (x_outer, ymin, z_plane),
                (x_outer, ymax, z_plane),
                color=axis_color,
                line_width=axis_line_width,
                opacity=1.0,
            )

        # XY 面普通边框。
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

        # XY 面 X 向网格。
        for x in x_ticks:
            self._add_fixed_coordinate_line(
                (x, ymin, z_plane),
                (x, ymax, z_plane),
                color=grid_color,
                line_width=grid_line_width,
                opacity=0.45,
            )

        # XY 面 Y 向网格。
        for y in y_ticks:
            self._add_fixed_coordinate_line(
                (xmin, y, z_plane),
                (xmax, y, z_plane),
                color=grid_color,
                line_width=grid_line_width,
                opacity=0.45,
            )

        # =========================================================
        # 2. YZ 平面
        # x = x_plane
        # =========================================================

        # 左侧 Z 主轴。
        if show_z_axis:
            self._add_fixed_coordinate_line(
                (x_plane, y_outer, zmin),
                (x_plane, y_outer, zmax),
                color=axis_color,
                line_width=axis_line_width,
                opacity=1.0,
            )

        # 顶部 Y 主轴。
        if show_y_axis:
            self._add_fixed_coordinate_line(
                (x_plane, ymin, z_outer),
                (x_plane, ymax, z_outer),
                color=axis_color,
                line_width=axis_line_width,
                opacity=1.0,
            )

        # YZ 面普通边框。
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

        # YZ 面 Y 向网格。
        for y in y_ticks:
            self._add_fixed_coordinate_line(
                (x_plane, y, zmin),
                (x_plane, y, zmax),
                color=grid_color,
                line_width=grid_line_width,
                opacity=0.45,
            )

        # YZ 面 Z 向网格。
        for z in z_ticks:
            self._add_fixed_coordinate_line(
                (x_plane, ymin, z),
                (x_plane, ymax, z),
                color=grid_color,
                line_width=grid_line_width,
                opacity=0.45,
            )

        # =========================================================
        # 3. XZ 平面
        # y = y_plane
        # =========================================================

        # 右侧 Z 主轴。
        if show_z_axis:
            self._add_fixed_coordinate_line(
                (x_outer, y_plane, zmin),
                (x_outer, y_plane, zmax),
                color=axis_color,
                line_width=axis_line_width,
                opacity=1.0,
            )

        # 顶部 X 主轴。
        if show_x_axis:
            self._add_fixed_coordinate_line(
                (xmin, y_plane, z_outer),
                (xmax, y_plane, z_outer),
                color=axis_color,
                line_width=axis_line_width,
                opacity=1.0,
            )

        # XZ 面普通边框。
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

        # XZ 面 X 向网格。
        for x in x_ticks:
            self._add_fixed_coordinate_line(
                (x, y_plane, zmin),
                (x, y_plane, zmax),
                color=grid_color,
                line_width=grid_line_width,
                opacity=0.45,
            )

        # XZ 面 Z 向网格。
        for z in z_ticks:
            self._add_fixed_coordinate_line(
                (xmin, y_plane, z),
                (xmax, y_plane, z),
                color=grid_color,
                line_width=grid_line_width,
                opacity=0.45,
            )

        # =========================================================
        # 顶部 X 轴刻度与数字
        # =========================================================
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

        # =========================================================
        # 顶部 Y 轴刻度与数字
        # =========================================================
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

        # =========================================================
        # 前方 X 轴刻度与数字
        # =========================================================
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

        # =========================================================
        # 前方 Y 轴刻度与数字
        # =========================================================
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

        # =========================================================
        # 左右两侧 Z 轴刻度与数字
        # =========================================================
        if show_z_axis:
            for z in z_ticks:

                # -------------------------------------------------
                # 第一条 Z 边：YZ 面外侧
                # 位置：x_plane, y_outer
                # -------------------------------------------------
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

                # -------------------------------------------------
                # 第二条 Z 边：XZ 面外侧
                # 位置：x_outer, y_plane
                # -------------------------------------------------
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

        # =========================================================
        # 坐标轴标题
        # =========================================================

        # X-axis
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

        # Y-axis
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

        # Z-axis
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

    # =====================================================================
    # 相机旋转监听
    # =====================================================================
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


    # =====================================================================
    # UI 调用接口
    # =====================================================================
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
            "well_actors": [],

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
            
            "sw_field_actor": None,
            "sw_scalar_bar": None,
            "layer_sw_actor": None,
            "layer_sw_scalar_bar": None,
            "layer_sw_coarse_grid_actor": None,
            "layer_sw_frac_actors": [],
            "layer_sw_well_actors": [],

            "phi_field_actor": None,
            "phi_scalar_bar": None,
            "layer_phi_actor": None,
            "layer_phi_scalar_bar": None,
            "layer_phi_coarse_grid_actor": None,
            "layer_phi_frac_actors": [],
            "layer_phi_well_actors": [],

            "threshold_actor": None,
            "threshold_scalar_bar": None,
            "threshold_grid_actor": None,
            "threshold_grid_visible": True,

            "perm_field_actor": None,
            "perm_scalar_bar": None,
            "layer_perm_actor": None,
            "layer_perm_scalar_bar": None,
            "layer_perm_coarse_grid_actor": None,
            "layer_perm_frac_actors": [],
            "layer_perm_well_actors": [],

            # 单元拾取 / cell picking
            "cell_pick_grid": None,
            "cell_pick_actor": None,
            "cell_pick_highlight_actor": None,
            "cell_pick_observer_id": None,
            "cell_pick_enabled": False,
            "cell_pick_property": "Pressure",
            "cell_pick_last_info": None,

            # 动态测距
            "measure_enabled": False,
            "measure_start_point": None,
            "measure_end_point": None,
            "measure_line_mesh": None,
            "measure_line_actor": None,
            "measure_observer_ids": [],
            "measure_is_previewing": False,
            "measure_last_info": None,

            # 时间步播放
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

            # 动态三面坐标系
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

            # 2D Magnify
            "magnify_2d_active": False,
            "magnify_2d_dragging": False,
            "magnify_2d_world_bounds": None,
            "magnify_2d_start_xy": None,

            # 折线垂向剖面
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
            "fence_section_context_actor_states": [],
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
            )
        
        # 清除静态属性预览渲染器
        if hasattr(self, "static_property_preview") and self.static_property_preview is not None:
            self.static_property_preview.clear(render_now=False)
        # 清除几何预览渲染器
        if hasattr(self, "geometry_preview") and self.geometry_preview is not None:
            self.geometry_preview.clear_all(render_now=False)

        self.disable_camera_aware_coordinate_axes(clear_axes=True)
        
        self.deactivate_2d_magnify(
            render=False,
        )

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
            cmap=get_bright_jet_cmap(),
            clim=[min_p, max_p],
            show_scalar_bar=False,
            opacity=0.96,
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
    
    #裂缝旧接口
    def render_fractures(self, sim_data):
        self.render_corner_fractures(sim_data)
 
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

    def _get_active_parent_cells_from_leaf_data(self, sim_data):
        
        #根据 cell_geometry_with_pressure 中的 parent_id，
        #获取所有参与计算的 active 父网格。
        
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

            self.plotter.render()
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
            line_width=1.0,
            render=False,
        )

        surface = grid.extract_surface()

        surface_actor = self.plotter.add_mesh(
            surface,
            color=(1.0, 1.0, 1.0),
            opacity=0.2,
            show_edges=False,
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

        self._remove_actor_list(
            self.cache["fracture_actors"]
        )
        self.cache["fracture_actors"] = []

        if not sim_data.fractures:
            return

        for fracture in sim_data.fractures:
            frac_points = fracture.get("points", []) or []

            if len(frac_points) < 3:
                continue

            # -----------------------------------------------------
            # 裂缝类型判断
            # -----------------------------------------------------
            is_hydraulic = (
                int(fracture.get("is_hydraulic", 0)) == 1
                or fracture.get("type") == "hydraulic"
            )

            if is_hydraulic:
                # 人工裂缝：红色
                frac_color = (0.72, 0.38, 0.38)
                edge_color = (0.54, 0.29, 0.29)
            else:
                # 天然裂缝：深蓝色
                frac_color = (0.0, 0.25, 0.4)
                edge_color = (0.0, 0.15, 0.25)

            points = np.array(
                frac_points,
                dtype=float,
            )

            polygon = pv.PolyData(points)

            polygon.faces = np.array(
                [len(frac_points), *range(len(frac_points))],
                dtype=np.int32,
            )

            actor = self.plotter.add_mesh(
                polygon,
                color=frac_color,
                opacity=0.999,
                show_edges=False,
                edge_color=edge_color,
                line_width=1.0,
                render=False,
            )

            self.cache["fracture_actors"].append(actor)

            edge_lines = []

            for index in range(len(frac_points)):
                start_point = frac_points[index]
                end_point = frac_points[
                    (index + 1) % len(frac_points)
                ]

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
                    line_width=0,
                    render=False,
                )

                self.cache["fracture_actors"].append(
                    edge_actor
                )

        self._render()

    def hide_fractures(self):
        self._remove_actor_list(self.cache["fracture_actors"])
        self.cache["fracture_actors"] = []
        self._render()

    #井
    def set_parsed_well_data(self, well_data):
        """
        保存 uniform_parser.parse_wells() 返回的井数据。
        """
        if not isinstance(well_data, dict):
            print("[WellRender] 设置井数据失败：well_data 不是 dict。")
            self._parsed_well_data = None
            return
        wells = well_data.get("wells", [])
        if not isinstance(wells, list):
            print("[WellRender] 设置井数据失败：well_data 中没有 wells 列表。")
            self._parsed_well_data = None
            return

        self._parsed_well_data = well_data
        print(
            f"[WellRender] 已保存解析井数据：{len(wells)} 口井"
        )

    # =====================================================================
    # 渲染井
    #
    # 数据来源：
    # uniform_parser.parse_wells() 返回的 well_data
    # =====================================================================

    def render_wells(self, sim_data):
        """
        根据 parse_wells() 返回的 JSON/dict 直接渲染真实井轨迹。
        井轨迹数据来自 self._parsed_well_data。
        """
        self._remove_actor_list(
            self.cache["well_actors"]
        )
        self.cache["well_actors"] = []
        # -------------------------------------------------------------
        # 1. 获取 parse_wells() 保存的数据
        # -------------------------------------------------------------
        # 模拟完成后，优先从当前 sim_data 获取 parser 解析出的井 JSON。
        well_data = getattr(
            sim_data,
            "parsed_well_data",
            None,
        )
        # 以后做“模拟前井预览”时，仍可通过 set_parsed_well_data() 使用这个备用入口。
        if not isinstance(well_data, dict):
            well_data = getattr(
                self,
                "_parsed_well_data",
                None,
            )
        if not isinstance(well_data, dict):
            print(
                "[WellRender] 当前没有井数据。"
            )
            print(
                "[WellRender] 请先调用："
                "renderer.set_parsed_well_data(well_data)"
            )
            self._render()
            return
        wells = well_data.get(
            "wells",
            [],
        )
        if not isinstance(wells, list) or not wells:
            print(
                "[WellRender] well_data 中没有可渲染的井。"
            )
            self._render()
            return

        rendered_count = 0
        # -------------------------------------------------------------
        # 2. 每口井单独绘制
        # -------------------------------------------------------------
        for well in wells:
            if not isinstance(well, dict):
                continue

            well_name = str(
                well.get(
                    "well_name",
                    "Unknown",
                )
            ).strip()

            raw_track = well.get(
                "track",
                [],
            )
            if not isinstance(raw_track, list):
                continue
            # ---------------------------------------------------------
            # 3. 从 track 中提取真实 XYZ 坐标
            # ---------------------------------------------------------
            valid_points = []
            for point in raw_track:
                if not isinstance(point, dict):
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
                    [md, x, y, z]
                ).all():
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
                print(
                    f"[WellRender] {well_name} "
                    "有效轨迹点少于 2 个，跳过。"
                )
                continue
            # ---------------------------------------------------------
            # 4. 按 md_m 排序
            # ---------------------------------------------------------
            valid_points.sort(
                key=lambda item: item[0]
            )
            ordered_points = []
            for _, xyz in valid_points:
                if not ordered_points:
                    ordered_points.append(
                        xyz
                    )
                    continue
                # 过滤连续重复点，防止出现零长度 tube
                if np.linalg.norm(
                    xyz - ordered_points[-1]
                ) > 1e-8:
                    ordered_points.append(
                        xyz
                    )
            if len(ordered_points) < 2:
                print(
                    f"[WellRender] {well_name} "
                    "去重后轨迹点少于 2 个，跳过。"
                )
                continue
            # ---------------------------------------------------------
            # 5. 相邻轨迹点连接成线段
            # ---------------------------------------------------------
            segments = [
                (
                    ordered_points[index].tolist(),
                    ordered_points[index + 1].tolist(),
                )
                for index in range(
                    len(ordered_points) - 1
                )
            ]
            well_line = self._polydata_from_line_segments(
                segments
            )
            if well_line is None:
                continue
            # ---------------------------------------------------------
            # 6. 生成井筒 tube
            # ---------------------------------------------------------
            well_tube = well_line.tube(
                radius=2.0,
                n_sides=16,
                capping=True,
            )
            actor = self.plotter.add_mesh(
                well_tube,
                color=(0.08, 0.24, 0.62),
                opacity=0.999,
                lighting=True,
                ambient=0.9,
                diffuse=1.0,
                render=False,
            )
            self.cache["well_actors"].append(
                actor
            )
            rendered_count += 1
            print(
                f"[WellRender] 已渲染井：{well_name}，"
                f"轨迹点数={len(ordered_points)}"
            )
        print(
            f"[WellRender] 井渲染完成："
            f"{rendered_count}/{len(wells)} 口井"
        )
        self._render()

    def hide_wells(self):
        self._remove_actor_list(
            self.cache["well_actors"]
        )
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
            pmin, pmax = float(np.min(pressures)), float(np.max(pressures))

            all_points = []
            cells = []
            offset = 0

            for i in range(n_cells):

                pts = cell_data[i, 4:28].reshape(8, 3).astype(np.float32)
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

            surface = grid.extract_surface()

            surface = surface.compute_normals(
                consistent_normals=True,
                auto_orient_normals=True
            )
            actor = self.plotter.add_mesh(
                surface,
                scalars="Pressure",
                cmap=get_bright_jet_cmap(),
                clim=[pmin, pmax],
                opacity=0.95,
                show_edges=False,
                show_scalar_bar=False,
                lighting=False,
                smooth_shading=False,
                ambient=1.0,
                diffuse=0.0,
                specular=0.0,
                interpolate_before_map=False,
                render=False,
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
            cloud,
            scalars="Pressure",
            cmap=get_bright_jet_cmap(),
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

        #父网格（灰色）
        if getattr(sim_data, "corner_lgr_parent_grid_geometry", None) is not None:

            self.cache["corner_lgr_parent_grid_actor"] = self._create_grid_lines_actor(
                sim_data.corner_lgr_parent_grid_geometry,
                #(0.78, 0.82, 0.87),
                (0.5, 0.5, 0.5),
                0.4,
                1.0,
            )

        # 加密网格（稍深灰蓝，层次清晰）
        refined_geom = getattr(sim_data, "corner_lgr_refined_grid_geometry", None)

        if refined_geom is not None:

            self.cache["corner_lgr_refined_grid_actor"] = self._create_grid_lines_actor(
                refined_geom,
                (0.64, 0.69, 0.76),
                0.45,
                0.0,
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


    def _get_layer_row_indices_by_parent_id(
        self,
        sim_data,
        axis,
        layer_index,
        cell_data=None,
    ):
        """
        根据 leaf 网格的 parent_id，
        筛选指定逻辑 I / J / K 层。

        不使用粗网格的 AABB 包围盒，
        可用于不规则角点网格。
        """

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

        # 第 1 列是 leaf 对应的 parent_id
        parent_ids = np.rint(
            cell_data[:, 1]
        ).astype(np.int64)

        # C++ 的 parent_id 规则：
        # parent_id = i + j * nx + k * nx * ny
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

        actor = self.plotter.add_mesh(
            surface,
            scalars="Pressure",
            cmap=get_bright_jet_cmap(),
            clim=[
                float(np.min(pressures_all)),
                float(np.max(pressures_all))
            ],
            opacity=0.72,
            show_scalar_bar=False,
            show_edges=False,
            lighting=False,
            smooth_shading=False,
            ambient=1.0,
            diffuse=0.0,
            specular=0.0,
            interpolate_before_map=False,
            render=False,
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

        self._remove_actor_list(self.cache.get("layer_frac_actors", []))
        self._remove_actor_list(self.cache.get("layer_well_actors", []))

        self.cache["layer_frac_actors"] = []
        self.cache["layer_pressure_actor"] = None
        self.cache["layer_well_actors"] = []
        self.cache["layer_coarse_grid_actor"] = None

        # 移除之前的颜色条，确保分层渲染时显示正确的颜色条
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
        pressures = selected_rows[:, 28].astype(np.float32)
        pressures_all = sim_data.cell_geometry_with_pressure[:, 28].astype(np.float32)
        grid.cell_data["Pressure"] = pressures
        #grid = grid.cell_data_to_point_data()

        surface = grid.extract_surface()
        self._add_layer_pressure_mesh(
            surface,
            pressures_all
        )

        # -------------------------
        # 天然裂缝保持原逻辑
        # -------------------------
        if hasattr(sim_data, "fractures"):
            for frac in sim_data.fractures:
                if int(frac.get("is_hydraulic", 0)) == 1 or frac.get("type") == "hydraulic":
                    continue

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

    #i方向
    def render_corner_grid_by_layer_i(self, sim_data, i_layer: int):

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

        if i_layer < 0 or i_layer >= nx:
            print(f"Invalid i_layer = {i_layer}")
            return

        # -------------------------------------------------
        # 提取 I 方向 coarse cells
        # -------------------------------------------------
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

        # -------------------------------------------------
        # 渲染 coarse grid
        # -------------------------------------------------
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

        pressures = selected_rows[:, 28].astype(np.float32)

        pressures_all = sim_data.cell_geometry_with_pressure[:, 28].astype(np.float32)

        grid.cell_data["Pressure"] = pressures

        #grid = grid.cell_data_to_point_data()

        surface = grid.extract_surface()
        self._add_layer_pressure_mesh(
            surface,
            pressures_all
        )

        #天然裂缝
        if hasattr(sim_data, "fractures"):

            for frac in sim_data.fractures:

                # 跳过人工裂缝
                if int(frac.get("is_hydraulic", 0)) == 1 or frac.get("type") == "hydraulic":
                    continue

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
        #人工裂缝
        if hasattr(sim_data, "fractures"):

            for frac in sim_data.fractures:

                # 只处理人工裂缝
                if not (
                    int(frac.get("is_hydraulic", 0)) == 1 or
                    frac.get("type") == "hydraulic"
                ):
                    continue

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

        # -------------------------------------------------
        # 井线（只连接当前层内人工裂缝）
        # -------------------------------------------------
        well_centers = []

        if hasattr(sim_data, "fractures"):

            for frac in sim_data.fractures:

                if not (
                    int(frac.get("is_hydraulic", 0)) == 1 or
                    frac.get("type") == "hydraulic"
                ):
                    continue

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

                if inside:
                    well_centers.append([cx, cy, cz])

        if len(well_centers) >= 2:

            well_centers = np.array(well_centers)

            well_centers = well_centers[
                np.argsort(well_centers[:, 1])
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

    # j方向
    def render_corner_grid_by_layer_j(self, sim_data, j_layer: int):

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

        pressures = selected_rows[:, 28].astype(np.float32)

        pressures_all = sim_data.cell_geometry_with_pressure[:, 28].astype(np.float32)

        grid.cell_data["Pressure"] = pressures

        #grid = grid.cell_data_to_point_data()

        surface = grid.extract_surface()
        self._add_layer_pressure_mesh(
            surface,
            pressures_all
        )

        # -------------------------------------------------
        # 天然裂缝
        # -------------------------------------------------
        if hasattr(sim_data, "fractures"):

            for frac in sim_data.fractures:

                if int(frac.get("is_hydraulic", 0)) == 1 or frac.get("type") == "hydraulic":
                    continue

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

        # -------------------------------------------------
        # 人工裂缝
        # -------------------------------------------------
        if hasattr(sim_data, "fractures"):

            for frac in sim_data.fractures:

                if not (
                    int(frac.get("is_hydraulic", 0)) == 1 or
                    frac.get("type") == "hydraulic"
                ):
                    continue

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

        # -------------------------------------------------
        # 井线
        # -------------------------------------------------
        well_centers = []

        if hasattr(sim_data, "fractures"):

            for frac in sim_data.fractures:

                if not (
                    int(frac.get("is_hydraulic", 0)) == 1 or
                    frac.get("type") == "hydraulic"
                ):
                    continue

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

                if inside:
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

            # 水饱和度在第 33 列
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

            surface = grid.extract_surface()

            surface = surface.compute_normals(
                consistent_normals=True,
                auto_orient_normals=True
            )

            actor = self.plotter.add_mesh(
                surface,
                scalars="Sw",
                cmap=get_bright_jet_cmap(),
                clim=[smin, smax],
                opacity=0.95,
                show_edges=False,
                show_scalar_bar=False,
                lighting=False,
                smooth_shading=False,
                ambient=1.0,
                diffuse=0.0,
                specular=0.0,
                interpolate_before_map=False,
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

            if getattr(sim_data, "fractures", None):
                self.render_corner_fractures(sim_data)

            if getattr(sim_data, "wells", None):
                self.render_corner_wells(sim_data)

            print(
                f"[Sw Field] "
                f"cell_count={n_cells}, "
                f"sw_range=[{smin:.6f}, {smax:.6f}]"
            )

            self._render()

        except Exception as exc:
            print("\n")
            print("=" * 60)
            print("ERROR IN render_corner_sw_field")
            print(type(exc).__name__, exc)
            print("=" * 60)
            print("\n")



    # =====================================================================
    # 水饱和度 Sw 分层渲染
    # =====================================================================

    def render_corner_sw_by_layer(
        self,
        sim_data,
        axis="k",
        layer_index=0,
        opacity=0.72,
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

        # Sw 对应 cell_geometry_with_pressure 第 33 列
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

        self._remove_actor_list(
            self.cache.get("layer_sw_frac_actors", [])
        )

        self._remove_actor_list(
            self.cache.get("layer_sw_well_actors", [])
        )

        self.cache["layer_sw_actor"] = None
        self.cache["layer_sw_coarse_grid_actor"] = None
        self.cache["layer_sw_frac_actors"] = []
        self.cache["layer_sw_well_actors"] = []

        if self.cache.get("layer_sw_scalar_bar") is not None:
            try:
                self.plotter.remove_scalar_bar(
                    render=False
                )
            except Exception:
                pass

            self.cache["layer_sw_scalar_bar"] = None

        try:
            # =========================================================
            # 2. 根据 I/J/K 方向选当前 coarse cells
            # =========================================================
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

            # =========================================================
            # 3. 构建 coarse_boxes，并绘制 Sw 当前层粗网格边线
            # =========================================================
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

            if show_grid and coarse_points:

                coarse_grid = pv.UnstructuredGrid(
                    np.asarray(
                        coarse_cell_array,
                        dtype=np.int64,
                    ),
                    np.asarray(
                        coarse_cell_types,
                        dtype=np.uint8,
                    ),
                    np.asarray(
                        coarse_points,
                        dtype=np.float32,
                    ),
                )

                if coarse_grid.n_points > 0:

                    coarse_edges = (
                        coarse_grid.extract_all_edges()
                    )

                    if coarse_edges.n_points > 0:

                        coarse_actor = self.plotter.add_mesh(
                            coarse_edges,
                            color=(0.78, 0.82, 0.87),
                            line_width=1.0,
                            opacity=1.0,
                            lighting=False,
                            render=False,
                        )

                        self.cache[
                            "layer_sw_coarse_grid_actor"
                        ] = coarse_actor

            # =========================================================
            # 4. 按 parent_id 获取当前 I/J/K 逻辑层 active leaf
            # =========================================================
            selected_indices = (
                self._get_layer_row_indices_by_parent_id(
                    sim_data=sim_data,
                    axis=axis,
                    layer_index=layer_index,
                    cell_data=cell_data,
                )
            )

            if selected_indices.size == 0:
                print(
                    f"No leaf cells found for Sw, "
                    f"axis={axis}, "
                    f"layer={layer_index}"
                )
                self._render()
                return

            selected_rows = cell_data[selected_indices]

            # =========================================================
            # 5. 构建当前层 Sw UnstructuredGrid
            # =========================================================
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

            surface = grid.extract_surface()

            surface = surface.compute_normals(
                consistent_normals=True,
                auto_orient_normals=True,
            )

            # =========================================================
            # 6. 计算全场 Sw min/max，作为所有 Sw 切片统一颜色范围
            # =========================================================
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

            # =========================================================
            # 7. 渲染当前层 Sw
            # =========================================================
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

            # =========================================================
            # 8. 当前层 / 剖面裂缝显示
            #
            # 天然裂缝：
            #   I/J/K 都只显示中心处于当前 coarse_boxes 内的裂缝。
            #
            # 人工裂缝：
            #   K 层：当前 K 层命中任意人工裂缝，显示所有人工裂缝；
            #   I/J：仅显示当前剖面内人工裂缝。
            # =========================================================
            selected_hydraulic_fracs = []
            show_all_hydraulic = False

            if (
                show_fractures
                and getattr(sim_data, "fractures", None)
            ):

                # -----------------------------------------------------
                # 8.1 显示天然裂缝，并判断人工裂缝是否属于当前层
                # -----------------------------------------------------
                for frac in sim_data.fractures:

                    is_hydraulic = (
                        int(
                            frac.get(
                                "is_hydraulic",
                                0,
                            )
                        ) == 1
                        or frac.get("type") == "hydraulic"
                    )

                    pts = np.asarray(
                        frac.get("points", []),
                        dtype=np.float64,
                    )

                    if len(pts) < 3:
                        continue

                    cx, cy, cz = pts.mean(axis=0)

                    inside = any(
                        box["xmin"] <= cx <= box["xmax"]
                        and box["ymin"] <= cy <= box["ymax"]
                        and box["zmin"] <= cz <= box["zmax"]
                        for box in coarse_boxes
                    )

                    # -------------------------------------------------
                    # 人工裂缝
                    # -------------------------------------------------
                    if is_hydraulic:

                        if axis == "k":
                            if inside:
                                show_all_hydraulic = True

                        else:
                            if inside:
                                selected_hydraulic_fracs.append(
                                    frac
                                )

                        continue

                    # -------------------------------------------------
                    # 天然裂缝
                    # -------------------------------------------------
                    if not inside:
                        continue

                    poly = pv.PolyData(pts)

                    poly.faces = np.asarray(
                        [
                            len(pts),
                            *range(len(pts)),
                        ],
                        dtype=np.int32,
                    )

                    frac_actor = self.plotter.add_mesh(
                        poly,
                        color=(0.0, 0.25, 0.40),
                        edge_color=(0.0, 0.15, 0.25),
                        show_edges=True,
                        line_width=1.5,
                        opacity=0.9,
                        lighting=False,
                        render=False,
                    )

                    self.cache[
                        "layer_sw_frac_actors"
                    ].append(
                        frac_actor
                    )

                # -----------------------------------------------------
                # 8.2 按 I/J/K 的规则显示人工裂缝
                # -----------------------------------------------------
                if axis == "k" and show_all_hydraulic:

                    hydraulic_fracs_to_render = [
                        frac
                        for frac in sim_data.fractures
                        if (
                            int(
                                frac.get(
                                    "is_hydraulic",
                                    0,
                                )
                            ) == 1
                            or frac.get("type")
                            == "hydraulic"
                        )
                    ]

                else:
                    hydraulic_fracs_to_render = (
                        selected_hydraulic_fracs
                    )

                for frac in hydraulic_fracs_to_render:

                    pts = np.asarray(
                        frac.get("points", []),
                        dtype=np.float64,
                    )

                    if len(pts) < 3:
                        continue

                    poly = pv.PolyData(pts)

                    poly.faces = np.asarray(
                        [
                            len(pts),
                            *range(len(pts)),
                        ],
                        dtype=np.int32,
                    )

                    frac_actor = self.plotter.add_mesh(
                        poly,
                        color=(0.72, 0.38, 0.38),
                        edge_color=(0.54, 0.29, 0.29),
                        show_edges=True,
                        line_width=1.5,
                        opacity=0.9,
                        lighting=False,
                        render=False,
                    )

                    self.cache[
                        "layer_sw_frac_actors"
                    ].append(
                        frac_actor
                    )

            # =========================================================
            # 9. 当前层 / 剖面井线显示
            # =========================================================
            if (
                show_wells
                and getattr(sim_data, "fractures", None)
            ):

                well_centers = []

                if axis == "k" and show_all_hydraulic:

                    well_source_fracs = [
                        frac
                        for frac in sim_data.fractures
                        if (
                            int(
                                frac.get(
                                    "is_hydraulic",
                                    0,
                                )
                            ) == 1
                            or frac.get("type")
                            == "hydraulic"
                        )
                    ]

                else:
                    well_source_fracs = (
                        selected_hydraulic_fracs
                    )

                for frac in well_source_fracs:

                    pts = np.asarray(
                        frac.get("points", []),
                        dtype=np.float64,
                    )

                    if len(pts) < 3:
                        continue

                    well_centers.append(
                        pts.mean(axis=0)
                    )

                if len(well_centers) >= 2:

                    well_centers = np.asarray(
                        well_centers,
                        dtype=np.float64,
                    )

                    # I 剖面固定 I，显示 Y-Z 面，所以按 Y 排序；
                    # J 剖面固定 J，显示 X-Z 面，所以按 X 排序；
                    # K 平面显示 X-Y 面，仍按 X 排序。
                    if axis == "i":
                        sorted_idx = np.argsort(
                            well_centers[:, 1]
                        )
                    else:
                        sorted_idx = np.argsort(
                            well_centers[:, 0]
                        )

                    ordered_centers = well_centers[
                        sorted_idx
                    ]

                    segments = [
                        (
                            ordered_centers[i].tolist(),
                            ordered_centers[
                                i + 1
                            ].tolist(),
                        )
                        for i in range(
                            len(ordered_centers) - 1
                        )
                    ]

                    well_line = self._polydata_from_line_segments(
                        segments
                    )

                    if well_line is not None:

                        well_actor = self.plotter.add_mesh(
                            well_line.tube(radius=2.0),
                            color=(0.31, 0.35, 0.40),
                            opacity=1.0,
                            lighting=True,
                            ambient=0.9,
                            diffuse=1.0,
                            render=False,
                        )

                        self.cache[
                            "layer_sw_well_actors"
                        ].append(
                            well_actor
                        )

            # =========================================================
            # 10. 输出检查信息
            # =========================================================
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
                f"sw_range=[{sw_min:.6f}, {sw_max:.6f}], "
                f"fracture_actor_count="
                f"{len(self.cache['layer_sw_frac_actors'])}, "
                f"well_actor_count="
                f"{len(self.cache['layer_sw_well_actors'])}"
            )

            self._render()

        except Exception as exc:
            print("\n")
            print("=" * 60)
            print("ERROR IN render_corner_sw_by_layer")
            print(type(exc).__name__, exc)
            print("=" * 60)
            print("\n")


    # =====================================================================
    # I 方向 Sw 剖面
    # =====================================================================

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


    # =====================================================================
    # J 方向 Sw 剖面
    # =====================================================================

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


    # =====================================================================
    # K 方向 Sw 层面
    # =====================================================================

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

            # 孔隙度在第 32 列
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

            surface = grid.extract_surface()

            surface = surface.compute_normals(
                consistent_normals=True,
                auto_orient_normals=True
            )

            actor = self.plotter.add_mesh(
                surface,
                scalars="Phi",
                cmap=get_bright_jet_cmap(),
                clim=[pmin, pmax],
                opacity=0.95,
                show_edges=False,
                show_scalar_bar=False,
                lighting=False,
                smooth_shading=False,
                ambient=1.0,
                diffuse=0.0,
                specular=0.0,
                interpolate_before_map=False,
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

            if getattr(sim_data, "fractures", None):
                self.render_corner_fractures(sim_data)

            if getattr(sim_data, "wells", None):
                self.render_corner_wells(sim_data)

            self._render()

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
        opacity=0.72,
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

        # =========================================================
        # 1. 清除上一帧孔隙度分层渲染
        # =========================================================
        self._remove_actor(self.cache.get("layer_phi_actor"))
        self._remove_actor(self.cache.get("layer_phi_coarse_grid_actor"))

        self._remove_actor_list(self.cache.get("layer_phi_frac_actors", []))
        self._remove_actor_list(self.cache.get("layer_phi_well_actors", []))

        self.cache["layer_phi_actor"] = None
        self.cache["layer_phi_coarse_grid_actor"] = None
        self.cache["layer_phi_frac_actors"] = []
        self.cache["layer_phi_well_actors"] = []

        if self.cache.get("layer_phi_scalar_bar") is not None:
            try:
                self.plotter.remove_scalar_bar(render=False)
            except Exception:
                pass
            self.cache["layer_phi_scalar_bar"] = None

        try:
            # =========================================================
            # 2. 根据 I/J/K 方向选 coarse cells
            # =========================================================
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

            # =========================================================
            # 3. 构建 coarse boxes，并渲染当前层 coarse grid 边线
            # =========================================================
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

            if show_grid and coarse_points:
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
                            opacity=1.0,
                            render=False,
                        )

                        self.cache["layer_phi_coarse_grid_actor"] = coarse_actor

            # =========================================================
            # 4. 从 cell_geometry_with_pressure 里筛当前层 refined cells
            # =========================================================
            selected_indices = self._get_layer_row_indices_by_parent_id(
                sim_data=sim_data,
                axis=axis,
                layer_index=layer_index,
                cell_data=cell_data,
            )

            if selected_indices.size == 0:
                print(
                    f"No leaf cells found for Phi, "
                    f"axis={axis}, layer={layer_index}"
                )
                self._render()
                return

            selected_rows = cell_data[selected_indices]

            # =========================================================
            # 5. 构建当前层孔隙度 UnstructuredGrid
            # =========================================================
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

            surface = grid.extract_surface()

            surface = surface.compute_normals(
                consistent_normals=True,
                auto_orient_normals=True
            )

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

            # =========================================================
            # 6. 渲染当前层孔隙度
            # 颜色条范围：Phi 全场 min/max，模仿 pressure 分层
            # =========================================================
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

            # =========================================================
            # 7. 当前层/剖面裂缝显示
            #
            # 规则：
            #   天然裂缝：
            #       I/J/K 都只显示中心落在当前层/剖面内的天然裂缝
            #
            #   人工裂缝：
            #       K 层：只要有一个人工裂缝中心在当前 K 层内，
            #            就显示所有人工裂缝，适合平面图展示完整压裂段
            #
            #       I/J 剖面：只显示中心落在当前 I/J 剖面内的人工裂缝，
            #            不显示所有人工裂缝，避免剖面图混乱
            # =========================================================
            selected_hydraulic_fracs = []
            show_all_hydraulic = False

            if show_fractures and getattr(sim_data, "fractures", None):

                # -----------------------------------------------------
                # 7.1 第一遍：判断哪些裂缝属于当前层/剖面
                # -----------------------------------------------------
                for frac in sim_data.fractures:

                    is_hydraulic = (
                        int(frac.get("is_hydraulic", 0)) == 1
                        or frac.get("type") == "hydraulic"
                    )

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

                    # -------------------------------------------------
                    # 人工裂缝
                    # -------------------------------------------------
                    if is_hydraulic:

                        if axis == "k":
                            # K 层平面图：
                            # 只要有一个人工裂缝中心落在当前 K 层内，
                            # 就显示所有人工裂缝。
                            if inside:
                                show_all_hydraulic = True

                        else:
                            # I/J 剖面：
                            # 只显示当前剖面内的人工裂缝。
                            if inside:
                                selected_hydraulic_fracs.append(frac)

                        continue

                    # -------------------------------------------------
                    # 天然裂缝：
                    # I/J/K 都只显示当前层/剖面内的天然裂缝。
                    # -------------------------------------------------
                    if not inside:
                        continue

                    poly = pv.PolyData(pts)
                    poly.faces = np.array(
                        [len(pts), *range(len(pts))],
                        dtype=np.int32
                    )

                    fac = self.plotter.add_mesh(
                        poly,
                        color=(0.0, 0.25, 0.4),
                        edge_color=(0.0, 0.15, 0.25),
                        show_edges=True,
                        line_width=1.5,
                        opacity=0.9,
                        render=False,
                    )

                    self.cache["layer_phi_frac_actors"].append(fac)

                # -----------------------------------------------------
                # 7.2 根据 I/J/K 规则渲染人工裂缝
                # -----------------------------------------------------
                if axis == "k" and show_all_hydraulic:
                    # K 层：显示所有人工裂缝
                    hydraulic_fracs_to_render = [
                        frac for frac in sim_data.fractures
                        if (
                            int(frac.get("is_hydraulic", 0)) == 1
                            or frac.get("type") == "hydraulic"
                        )
                    ]
                else:
                    # I/J 剖面：只显示当前剖面内的人工裂缝
                    hydraulic_fracs_to_render = selected_hydraulic_fracs

                for frac in hydraulic_fracs_to_render:

                    pts = np.array(frac["points"], dtype=np.float64)

                    if len(pts) < 3:
                        continue

                    poly = pv.PolyData(pts)
                    poly.faces = np.array(
                        [len(pts), *range(len(pts))],
                        dtype=np.int32
                    )

                    fac = self.plotter.add_mesh(
                        poly,
                        color=(0.72, 0.38, 0.38),
                        edge_color=(0.54, 0.29, 0.29),
                        show_edges=True,
                        line_width=1.5,
                        opacity=0.9,
                        render=False,
                    )

                    self.cache["layer_phi_frac_actors"].append(fac)

            # =========================================================
            # 8. 当前层/剖面井显示
            #
            # 规则：
            #   K 层：
            #       如果当前 K 层命中人工裂缝，则用所有人工裂缝中心连井线
            #
            #   I 剖面：
            #       只用当前 I 剖面内的人工裂缝中心连井线
            #       因为 I 剖面是固定 i，看的是 Y-Z 面，所以按 Y 排序
            #
            #   J 剖面：
            #       只用当前 J 剖面内的人工裂缝中心连井线
            #       因为 J 剖面是固定 j，看的是 X-Z 面，所以按 X 排序
            # =========================================================
            if show_wells and getattr(sim_data, "fractures", None):

                well_centers = []

                if axis == "k" and show_all_hydraulic:
                    # K 层平面图：使用所有人工裂缝中心生成完整井线
                    well_source_fracs = [
                        frac for frac in sim_data.fractures
                        if (
                            int(frac.get("is_hydraulic", 0)) == 1
                            or frac.get("type") == "hydraulic"
                        )
                    ]
                else:
                    # I/J 剖面：只使用当前剖面内的人工裂缝中心
                    well_source_fracs = selected_hydraulic_fracs

                for frac in well_source_fracs:

                    pts = np.array(frac["points"], dtype=np.float64)

                    if len(pts) < 3:
                        continue

                    center = pts.mean(axis=0)
                    well_centers.append(center)

                if len(well_centers) >= 2:

                    well_centers = np.array(well_centers)

                    # 排序方式根据剖面方向区分：
                    # I 剖面固定 i，看 Y-Z，所以按 Y 排序；
                    # J 剖面固定 j，看 X-Z，所以按 X 排序；
                    # K 层平面图看 X-Y，仍按 X 排序。
                    if axis == "i":
                        sorted_idx = np.argsort(well_centers[:, 1])
                    else:
                        sorted_idx = np.argsort(well_centers[:, 0])

                    ordered_centers = well_centers[sorted_idx]

                    segments = [
                        (
                            ordered_centers[i].tolist(),
                            ordered_centers[i + 1].tolist()
                        )
                        for i in range(len(ordered_centers) - 1)
                    ]

                    well_line = self._polydata_from_line_segments(segments)

                    if well_line is not None:
                        wactor = self.plotter.add_mesh(
                            well_line.tube(radius=2.0),
                            color=(0.31, 0.35, 0.40),
                            opacity=1.0,
                            lighting=True,
                            ambient=0.9,
                            diffuse=1.0,
                            render=False,
                        )

                        self.cache["layer_phi_well_actors"].append(wactor)

            self._render()

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

    # =====================================================================
    # 阈值过滤
    # =====================================================================
    def render_threshold_property_field(
        self,
        sim_data,
        property_name="Pressure",
        min_value=None,
        max_value=None,
        opacity=0.95,
        show_edges=False,
    ):

        if getattr(
            sim_data,
            "cell_geometry_with_pressure",
            None,
        ) is None:
            print("No cell_geometry_with_pressure data")
            return

        # =========================================================
        # 1. 属性列配置
        # =========================================================
        property_config = {
            "Pressure": {
                "column": 28,
                "title": "Pressure (bar)",
            },

            "Kx": {
                "column": 29,
                "title": "Permeability X",
            },

            "Ky": {
                "column": 30,
                "title": "Permeability Y",
            },

            "Kz": {
                "column": 31,
                "title": "Permeability Z",
            },

            "Phi": {
                "column": 32,
                "title": "Phi",
            },

            "Sw": {
                "column": 33,
                "title": "Sw",
            },
        }

        if property_name not in property_config:
            print(
                f"Unsupported property_name: {property_name}"
            )
            print(
                f"Supported properties: "
                f"{list(property_config.keys())}"
            )
            return

        config = property_config[property_name]
        col = int(config["column"])

        cell_data = sim_data.cell_geometry_with_pressure

        if cell_data is None or cell_data.shape[0] == 0:
            print("Empty cell_geometry_with_pressure")
            return

        if cell_data.shape[1] <= col:
            print(
                f"Column index out of range: "
                f"property={property_name}, "
                f"column={col}, "
                f"data columns={cell_data.shape[1]}"
            )
            return

        # =========================================================
        # 2. 记录筛选网格线当前显示状态
        # =========================================================
        threshold_grid_visible = bool(
            self.cache.get(
                "threshold_grid_visible",
                True,
            )
        )

        # =========================================================
        # 3. 清理上一次阈值过滤结果
        # =========================================================
        self._remove_actor(
            self.cache.get("threshold_actor")
        )

        self._remove_actor(
            self.cache.get("threshold_grid_actor")
        )

        self.cache["threshold_actor"] = None
        self.cache["threshold_grid_actor"] = None

        if self.cache.get("threshold_scalar_bar") is not None:
            try:
                self.plotter.remove_scalar_bar(
                    render=False
                )
            except Exception:
                pass

            self.cache["threshold_scalar_bar"] = None

        try:
            # =========================================================
            # 4. 读取属性值并生成阈值 mask
            # =========================================================
            values = cell_data[
                :,
                col,
            ].astype(
                np.float32
            )

            # NaN / Inf 不参与筛选和渲染。
            mask = np.isfinite(values)

            if min_value is not None:
                mask &= values >= float(min_value)

            if max_value is not None:
                mask &= values <= float(max_value)

            selected_rows = cell_data[mask]
            selected_values = values[mask]

            if selected_rows.shape[0] == 0:
                print(
                    f"No cells found for {property_name} threshold: "
                    f"min={min_value}, max={max_value}"
                )
                self._render()
                return

            print(
                f"Threshold render: {property_name}, "
                f"selected {selected_rows.shape[0]} / "
                f"{cell_data.shape[0]} cells"
            )

            # =========================================================
            # 5. 只用筛选后的单元构建 UnstructuredGrid
            # =========================================================
            all_points = []
            vtk_cells = []
            offset = 0

            for row in selected_rows:

                pts = row[
                    4:28
                ].reshape(
                    8,
                    3,
                ).astype(
                    np.float32
                )

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

            points = np.vstack(
                all_points
            ).astype(
                np.float32
            )

            cells = np.hstack(
                vtk_cells
            ).astype(
                np.int64
            )

            cell_types = np.full(
                selected_rows.shape[0],
                pv.CellType.HEXAHEDRON,
                dtype=np.uint8,
            )

            grid = pv.UnstructuredGrid(
                cells,
                cell_types,
                points,
            )

            grid.cell_data[property_name] = (
                selected_values
            )

            # =========================================================
            # 6. 提取筛选后属性表面
            # =========================================================
            surface = grid.extract_surface()

            surface = surface.compute_normals(
                consistent_normals=True,
                auto_orient_normals=True,
            )

            # =========================================================
            # 7. 计算全场有效值的颜色范围
            # =========================================================
            valid_values = values[
                np.isfinite(values)
            ]

            if valid_values.size == 0:
                print(
                    f"No valid values for {property_name}"
                )
                self._render()
                return

            value_min = float(
                np.nanmin(valid_values)
            )

            value_max = float(
                np.nanmax(valid_values)
            )

            # 全场数值相同或差异极小时，
            # 防止 clim=[x, x] 或浮点误差导致颜色异常。
            if np.isclose(
                value_min,
                value_max,
                rtol=1e-6,
                atol=1e-8,
            ):
                center_value = float(
                    np.nanmean(valid_values)
                )

                delta = max(
                    abs(center_value) * 0.01,
                    0.001,
                )

                value_min = center_value - delta
                value_max = center_value + delta

            clim = [
                value_min,
                value_max,
            ]

            # =========================================================
            # 8. 绘制阈值过滤属性场
            # =========================================================
            threshold_actor = self.plotter.add_mesh(
                surface,
                scalars=property_name,
                cmap=get_bright_jet_cmap(),
                clim=clim,
                opacity=opacity,
                show_edges=show_edges,
                edge_color=(0.18, 0.18, 0.18),
                line_width=0.3,

                # 禁止默认横向颜色条
                show_scalar_bar=False,

                lighting=False,
                smooth_shading=False,
                ambient=1.0,
                diffuse=0.0,
                specular=0.0,
                interpolate_before_map=False,
                render=False,
            )

            # =========================================================
            # 9. 创建颜色条
            # =========================================================
            scalar_bar = self._replace_scalar_bar(
                "threshold_scalar_bar",
                config["title"],
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

            self.cache["threshold_actor"] = threshold_actor
            self.cache["threshold_scalar_bar"] = scalar_bar

            # =========================================================
            # 10. 创建阈值筛选后的网格线
            # =========================================================
            threshold_edges = grid.extract_all_edges()

            if threshold_edges.n_points > 0:

                threshold_grid_actor = self.plotter.add_mesh(
                    threshold_edges,
                    color=(0.5, 0.5, 0.5),
                    line_width=1.0,
                    opacity=1.0,
                    lighting=False,
                    render_lines_as_tubes=True,
                    show_scalar_bar=False,
                    render=False,
                )

                try:
                    threshold_grid_actor.visibility = (
                        threshold_grid_visible
                    )
                except Exception:
                    try:
                        threshold_grid_actor.SetVisibility(
                            threshold_grid_visible
                        )
                    except Exception:
                        pass

                self.cache[
                    "threshold_grid_actor"
                ] = threshold_grid_actor

            self.cache["threshold_grid_visible"] = (
                threshold_grid_visible
            )

            # =========================================================
            # 11. 可选叠加裂缝和井
            # =========================================================
            if getattr(sim_data, "fractures", None):
                self.render_corner_fractures(
                    sim_data
                )

            if getattr(sim_data, "wells", None):
                self.render_corner_wells(
                    sim_data
                )

            print(
                f"[Threshold] "
                f"property={property_name}, "
                f"selected={selected_rows.shape[0]}, "
                f"total={cell_data.shape[0]}, "
                f"range=[{value_min:.6f}, "
                f"{value_max:.6f}], "
                f"grid_visible={threshold_grid_visible}"
            )

            self._render()

        except Exception as exc:
            print("\n")
            print("=" * 60)
            print(
                "ERROR IN "
                "render_threshold_property_field"
            )
            print(type(exc).__name__, exc)
            print("=" * 60)
            print("\n")

    # =====================================================================
    # 阈值过滤网格线显示 / 隐藏
    # =====================================================================
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


    # =====================================================================
    # 隐藏 / 清除阈值过滤结果
    # =====================================================================

    def hide_threshold_property_field(self):
        """
        删除当前阈值过滤属性场、竖直颜色条和筛选后的网格线。

        清除后，下一次阈值过滤会默认显示网格线。
        """

        self._remove_actor(
            self.cache.get("threshold_actor")
        )

        self._remove_actor(
            self.cache.get("threshold_grid_actor")
        )

        self.cache["threshold_actor"] = None
        self.cache["threshold_grid_actor"] = None

        # 下一次阈值筛选默认显示网格线。
        self.cache["threshold_grid_visible"] = True

        if self.cache.get("threshold_scalar_bar") is not None:
            try:
                self.plotter.remove_scalar_bar(
                    render=False
                )
            except Exception:
                pass

            self.cache["threshold_scalar_bar"] = None

        self._render()

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

        direction = str(direction).lower()

        if direction == "front":
            # 从 -Y 方向看向模型
            camera_position = (
                (cx, cy - dist, cz),
                (cx, cy, cz),
                (0.0, 0.0, 1.0)
            )
            parallel_scale = max(dx, dz) * 0.6

        elif direction == "back":
            # 从 +Y 方向看向模型
            camera_position = (
                (cx, cy + dist, cz),
                (cx, cy, cz),
                (0.0, 0.0, 1.0)
            )
            parallel_scale = max(dx, dz) * 0.6

        elif direction == "left":
            # 从 -X 方向看向模型
            camera_position = (
                (cx - dist, cy, cz),
                (cx, cy, cz),
                (0.0, 0.0, 1.0)
            )
            parallel_scale = max(dy, dz) * 0.6

        elif direction == "right":
            # 从 +X 方向看向模型
            camera_position = (
                (cx + dist, cy, cz),
                (cx, cy, cz),
                (0.0, 0.0, 1.0)
            )
            parallel_scale = max(dy, dz) * 0.6

        elif direction == "top":
            # 俯视图：从 +Z 往下看
            camera_position = (
                (cx, cy, cz + dist),
                (cx, cy, cz),
                (0.0, 1.0, 0.0)
            )
            parallel_scale = max(dx, dy) * 0.6

        elif direction == "bottom":
            # 仰视图：从 -Z 往上看
            camera_position = (
                (cx, cy, cz - dist),
                (cx, cy, cz),
                (0.0, 1.0, 0.0)
            )
            parallel_scale = max(dx, dy) * 0.6

        else:
            print(f"Unknown camera direction: {direction}")
            return

        cam = self.plotter.camera
        cam.parallel_projection = True
        cam.parallel_scale = parallel_scale

        self.plotter.camera_position = camera_position
        self.plotter.reset_camera_clipping_range()
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

        # =========================================================
        # 2. 清除上一次渗透率 actor 和颜色条
        # =========================================================
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

            # =========================================================
            # 3. 读取 Kx / Ky / Kz
            # =========================================================
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

            # =========================================================
            # 4. 构建 UnstructuredGrid
            # =========================================================
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

            surface = grid.extract_surface()

            surface = surface.compute_normals(
                consistent_normals=True,
                auto_orient_normals=True
            )

            # =========================================================
            # 5. 渲染渗透率场
            # =========================================================
            actor = self.plotter.add_mesh(
                surface,
                scalars=prop_name,
                cmap=get_bright_jet_cmap(),
                clim=[kmin, kmax],
                opacity=0.95,
                show_edges=False,
                show_scalar_bar=False,
                lighting=False,
                smooth_shading=False,
                ambient=1.0,
                diffuse=0.0,
                specular=0.0,
                interpolate_before_map=False,
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

            # =========================================================
            # 6. 叠加裂缝和井
            # =========================================================
            if getattr(sim_data, "fractures", None):
                self.render_corner_fractures(sim_data)

            if getattr(sim_data, "wells", None):
                self.render_corner_wells(sim_data)

            self._render()

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
        opacity=0.72,
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

        # =========================================================
        # 1. 渗透率方向配置
        # =========================================================
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

        # =========================================================
        # 2. 清除上一帧渗透率分层渲染
        # =========================================================
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

        try:
            # =========================================================
            # 3. 根据 I/J/K 方向选 coarse cells
            # =========================================================
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

            # =========================================================
            # 4. 构建 coarse boxes，并渲染当前层 coarse grid 边线
            # =========================================================
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

            if show_grid and coarse_points:
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
                            opacity=1.0,
                            render=False,
                        )

                        self.cache["layer_perm_coarse_grid_actor"] = coarse_actor

            # =========================================================
            # 5. 从 cell_geometry_with_pressure 里筛当前层 refined cells
            # =========================================================
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

            # =========================================================
            # 6. 构建当前层渗透率 UnstructuredGrid
            # =========================================================
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

            surface = grid.extract_surface()

            surface = surface.compute_normals(
                consistent_normals=True,
                auto_orient_normals=True
            )

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

            # =========================================================
            # 7. 渲染当前层渗透率
            # 颜色条范围：当前渗透率方向全场 min/max
            # =========================================================
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

            # =========================================================
            # 8. 当前层裂缝显示
            # 天然裂缝：中心在当前层/剖面内才显示
            # 人工裂缝：只要一个人工裂缝中心在当前层/剖面内，就显示所有人工裂缝
            # =========================================================
            show_all_hydraulic = False

            if show_fractures and getattr(sim_data, "fractures", None):

                # 8.1 天然裂缝
                for frac in sim_data.fractures:

                    is_hydraulic = (
                        int(frac.get("is_hydraulic", 0)) == 1
                        or frac.get("type") == "hydraulic"
                    )

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

                    if is_hydraulic:
                        if inside:
                            show_all_hydraulic = True
                        continue

                    if not inside:
                        continue

                    poly = pv.PolyData(pts)
                    poly.faces = np.array(
                        [len(pts), *range(len(pts))],
                        dtype=np.int32
                    )

                    fac = self.plotter.add_mesh(
                        poly,
                        color=(0.0, 0.25, 0.4),
                        edge_color=(0.0, 0.15, 0.25),
                        show_edges=True,
                        line_width=1.5,
                        opacity=0.9,
                        render=False,
                    )

                    self.cache["layer_perm_frac_actors"].append(fac)

                # 8.2 人工裂缝：只要一个在层内，就显示所有人工裂缝
                if show_all_hydraulic:
                    for frac in sim_data.fractures:

                        is_hydraulic = (
                            int(frac.get("is_hydraulic", 0)) == 1
                            or frac.get("type") == "hydraulic"
                        )

                        if not is_hydraulic:
                            continue

                        pts = np.array(frac["points"], dtype=np.float64)

                        if len(pts) < 3:
                            continue

                        poly = pv.PolyData(pts)
                        poly.faces = np.array(
                            [len(pts), *range(len(pts))],
                            dtype=np.int32
                        )

                        fac = self.plotter.add_mesh(
                            poly,
                            color=(0.72, 0.38, 0.38),
                            edge_color=(0.54, 0.29, 0.29),
                            show_edges=True,
                            line_width=1.5,
                            opacity=0.9,
                            render=False,
                        )

                        self.cache["layer_perm_frac_actors"].append(fac)

            # =========================================================
            # 9. 当前层井显示
            # 沿用你现有逻辑：人工裂缝中心连线作为井线
            # =========================================================
            if show_wells and show_all_hydraulic and getattr(sim_data, "fractures", None):

                well_centers = []

                for frac in sim_data.fractures:

                    is_hydraulic = (
                        int(frac.get("is_hydraulic", 0)) == 1
                        or frac.get("type") == "hydraulic"
                    )

                    if not is_hydraulic:
                        continue

                    pts = np.array(frac["points"], dtype=np.float64)

                    if len(pts) < 3:
                        continue

                    center = pts.mean(axis=0)
                    well_centers.append(center)

                if len(well_centers) >= 2:

                    well_centers = np.array(well_centers)

                    sorted_idx = np.argsort(well_centers[:, 0])
                    ordered_centers = well_centers[sorted_idx]

                    segments = [
                        (
                            ordered_centers[i].tolist(),
                            ordered_centers[i + 1].tolist()
                        )
                        for i in range(len(ordered_centers) - 1)
                    ]

                    well_line = self._polydata_from_line_segments(segments)

                    if well_line is not None:
                        wactor = self.plotter.add_mesh(
                            well_line.tube(radius=2.0),
                            color=(0.31, 0.35, 0.40),
                            opacity=1.0,
                            lighting=True,
                            ambient=0.9,
                            diffuse=1.0,
                            render=False,
                        )

                        self.cache["layer_perm_well_actors"].append(wactor)

            self._render()

        except Exception as exc:
            print("\n")
            print("=" * 60)
            print("ERROR IN render_corner_perm_by_layer")
            print(exc)
            print("=" * 60)
            print("\n")

    # =========================================================
    # Kx 分层
    # =========================================================
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


    # =========================================================
    # Ky 分层
    # =========================================================
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


    # =========================================================
    # Kz 分层
    # =========================================================
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


    # =========================================================
    # Cell Picking：单元拾取信息显示
    # =========================================================

    def _get_pick_property_config(self, property_name):
        """
        根据属性名返回属性列号和显示标题。
        数据结构：
            28 P
            29 Kx
            30 Ky
            31 Kz
            32 Phi
            33 Sw
        """

        name = str(property_name).strip()

        config = {
            "Pressure": {
                "column": 28,
                "title": "Pressure",
                "unit": "bar",
            },
            "P": {
                "column": 28,
                "title": "Pressure",
                "unit": "bar",
            },
            "Kx": {
                "column": 29,
                "title": "PermeabilityX",
                "unit": "",
            },
            "Ky": {
                "column": 30,
                "title": "PermeabilityY",
                "unit": "",
            },
            "Kz": {
                "column": 31,
                "title": "PermeabilityZ",
                "unit": "",
            },
            "Phi": {
                "column": 32,
                "title": "Phi",
                "unit": "",
            },
            "Porosity": {
                "column": 32,
                "title": "Porosity",
                "unit": "",
            },
            "Sw": {
                "column": 33,
                "title": "Sw",
                "unit": "",
            },
        }

        if name not in config:
            print(f"Unsupported pick property: {property_name}")
            print(f"Supported properties: {list(config.keys())}")
            return None

        return config[name]


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


    def _build_cell_pick_grid(
        self,
        sim_data,
        axis=None,
        layer_index=None,
    ):
        """
        构建用于 cell picking 的 UnstructuredGrid。
        """

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

        # =========================================================
        # 1. 整体场：直接使用全部 leaf cell
        # =========================================================
        if axis is None or layer_index is None:

            selected_original_indices = np.arange(
                cell_data.shape[0],
                dtype=np.int64,
            )

        # =========================================================
        # 2. 分层场：根据 parent_id 推导 I/J/K 后筛选 leaf cell
        # =========================================================
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

        # =========================================================
        # 3. 构建拾取网格
        # =========================================================
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

        # =========================================================
        # 4. 保存 cell 信息
        # =========================================================

        # 当前 picking 网格中的本地编号
        grid.cell_data["PickCellId"] = np.arange(
            n_cells,
            dtype=np.int32,
        )

        # 对应 cell_geometry_with_pressure 中的原始行号
        grid.cell_data["OriginalRowIndex"] = (
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

        # =========================================================
        # 5. 计算单元体积
        # =========================================================
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

            # 失败时使用 AABB 近似体积，作为兜底。
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
        sim_data,
        property_name="Pressure",
        axis=None,
        layer_index=None
    ):
        """
        开启 cell picking。

        整体场：
            axis=None, layer_index=None
            拾取全场 cell

        分层场：
            axis="i"/"j"/"k", layer_index=层号
            只拾取当前 I/J/K 层的 cell
        """

        config = self._get_pick_property_config(property_name)

        if config is None:
            return

        self.cache["cell_pick_property"] = str(property_name).strip()

        # 先清除旧的 picking
        self.disable_cell_info_picking(clear_highlight=True)

        grid = self._build_cell_pick_grid(
            sim_data,
            axis=axis,
            layer_index=layer_index
        )

        if grid is None:
            print("Failed to build cell pick grid.")
            return

        self.cache["cell_pick_grid"] = grid

        actor = self.plotter.add_mesh(
            grid,
            color=(1.0, 1.0, 1.0),
            opacity=0.01,
            show_edges=False,
            pickable=True,
            render=False,
        )

        try:
            actor.SetPickable(True)
        except Exception:
            pass

        self.cache["cell_pick_actor"] = actor
        self.cache["cell_pick_enabled"] = True

        try:
            interactor = self.plotter.iren.interactor

            observer_id = interactor.AddObserver(
                "LeftButtonPressEvent",
                self._on_cell_info_pick
            )

            self.cache["cell_pick_observer_id"] = observer_id

        except Exception as exc:
            print("Failed to add cell picking observer")
            print(exc)

        self._render()


    def disable_cell_info_picking(self, clear_highlight=True):
        """
        关闭 cell picking。
        """

        observer_id = self.cache.get("cell_pick_observer_id")

        if observer_id is not None:
            try:
                interactor = self.plotter.iren.interactor
                interactor.RemoveObserver(observer_id)
            except Exception:
                pass

        self.cache["cell_pick_observer_id"] = None
        self.cache["cell_pick_enabled"] = False

        self._remove_actor(self.cache.get("cell_pick_actor"))
        self.cache["cell_pick_actor"] = None
        self.cache["cell_pick_grid"] = None

        if clear_highlight:
            self.clear_cell_pick_highlight()

        self._render()


    def clear_cell_pick_highlight(self):
        """
        清除当前拾取高亮 cell。
        """

        self._remove_actor(self.cache.get("cell_pick_highlight_actor"))
        self.cache["cell_pick_highlight_actor"] = None
        self.cache["cell_pick_last_info"] = None
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
                render=False,
            )

            self.cache["cell_pick_highlight_actor"] = actor

        except Exception as exc:
            print("Failed to highlight picked cell")
            print(exc)


    def _format_picked_cell_info(self, grid, cell_id, property_name):
        """
        生成状态栏的拾取信息。
        """

        config = self._get_pick_property_config(property_name)

        if config is None:
            return None

        if grid is None:
            return None

        if cell_id < 0 or cell_id >= grid.n_cells:
            return None

        col_title = config["title"]
        prop_key = None

        if property_name in ("Pressure", "P"):
            prop_key = "Pressure"
        elif property_name == "Kx":
            prop_key = "Kx"
        elif property_name == "Ky":
            prop_key = "Ky"
        elif property_name == "Kz":
            prop_key = "Kz"
        elif property_name in ("Phi", "Porosity"):
            prop_key = "Phi"
        elif property_name == "Sw":
            prop_key = "Sw"

        if prop_key is None or prop_key not in grid.cell_data:
            return None

        value = float(grid.cell_data[prop_key][cell_id])

        info0 = grid.cell_data["CellInfo0"][cell_id]
        info1 = grid.cell_data["CellInfo1"][cell_id]
        info2 = grid.cell_data["CellInfo2"][cell_id]
        info3 = grid.cell_data["CellInfo3"][cell_id]

        cx = float(grid.cell_data["CenterX"][cell_id])
        cy = float(grid.cell_data["CenterY"][cell_id])
        cz = float(grid.cell_data["CenterZ"][cell_id])
        volume = float(grid.cell_data["Volume"][cell_id])

        try:
            info0_i = int(info0)
            info1_i = int(info1)
            info2_i = int(info2)
            info3_i = int(info3)

            cell_index_text = (
                f"id={info0_i}, "
                f"index=({info1_i}, {info2_i}, {info3_i})"
            )

        except Exception:
            cell_index_text = (
                f"id/index=({info0}, {info1}, {info2}, {info3})"
            )

        unit = config.get("unit", "")

        if unit:
            value_text = f"{value:.6g} {unit}"
        else:
            value_text = f"{value:.6g}"

        info_text = (
            f"Selected property: {col_title} | "
            f"Grid cell: {cell_index_text} | "
            f"Value: {value_text} | "
            f"Type: Continuous | "
            f"Volume: {volume:.3f} m3 | "
            f"x: {cx:.3f} m | "
            f"y: {cy:.3f} m | "
            f"Depth: {cz:.3f} m"
        )

        return info_text


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

    # =========================================================
    # 动态尺子工具
    # 第一次点击确定起点，鼠标移动动态画白线并刷新测量信息；
    # 第二次点击确定终点，白线固定，测量信息固定。
    # =========================================================
    def enable_petrel_distance_measure(self):

        # 如果之前已经开过，先关闭旧事件，保留干净状态
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
        """
        关闭测距工具。
        """

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
        """
        清除当前测距线。
        """

        self._remove_actor(self.cache.get("measure_line_actor"))

        self.cache["measure_line_actor"] = None
        self.cache["measure_line_mesh"] = None
        self.cache["measure_start_point"] = None
        self.cache["measure_end_point"] = None
        self.cache["measure_is_previewing"] = False
        self.cache["measure_last_info"] = None

        self._render()


    def _measure_pick_world_point(self):
        """
        拾取鼠标当前位置对应的模型表面三维坐标。

        规则：
            1. 鼠标点在模型上，返回真实拾取点。
            2. 鼠标点在模型外，返回 None。
            3. 不再使用起点所在 Z 平面做退化计算，避免模型外也更新距离。
        """

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

            # 没有真正拾取到 actor，说明点在模型外
            if picked_actor is None:
                return None

            # 如果点到的是测距线本身，也不算有效模型点
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
                # 如果原地更新失败，就重建
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

        # Petrel 这里显示 Depth 差值，沿用 dz。
        depth = dz

        # Heading：按北向顺时针角度，常用 atan2(dx, dy)
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

        # 点击在模型外：不设置起点、不设置终点、不更新结果
        if point is None:
            return

        start_point = self.cache.get("measure_start_point")
        is_previewing = self.cache.get("measure_is_previewing", False)

        # =========================================================
        # 第一次点击，或者上一次已经测完后重新开始
        # =========================================================
        if start_point is None or not is_previewing:

            # 开始新测量前清除旧线
            self._remove_actor(self.cache.get("measure_line_actor"))

            self.cache["measure_line_actor"] = None
            self.cache["measure_line_mesh"] = None
            self.cache["measure_start_point"] = point
            self.cache["measure_end_point"] = None
            self.cache["measure_is_previewing"] = True
            self.cache["measure_last_info"] = None

            print("\nMeasure start point selected. Move mouse to preview.")

            return

        # =========================================================
        # 第二次点击：只有点在模型内部/表面，才固定终点
        # =========================================================
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

        # 鼠标在模型外：不更新线、不更新数值
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

            # 如果用户没写后缀，默认保存为 png
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
                # 只切换交互模式：禁止旋转
                self.plotter.enable_image_style()
                print("Lock camera direction: ON")
            else:
                # 恢复正常 3D 旋转
                self.plotter.enable_trackball_style()
                print("Lock camera direction: OFF")

            self._render()

        except Exception as exc:
            print("lock_camera_direction error:", exc)


    def toggle_camera_direction_lock(self):
        """
        工具栏按钮用这个：
        第一次点击锁定当前角度；
        第二次点击恢复自由旋转。
        """
        current = getattr(self, "camera_direction_locked", False)
        self.lock_camera_direction(not current)


    # 时间步播放
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
        """
        删除通用时间步播放 actor 并清空播放缓存。
        不恢复静态场。
        """

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

        # 第 1 列为 parent_id。
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
            points = row[4:28].reshape(
                8,
                3,
            ).astype(
                np.float32,
                copy=False,
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

        points_array = np.vstack(
            all_points
        ).astype(
            np.float32,
            copy=False,
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

        surface = grid.extract_surface(
            pass_pointid=False,
            pass_cellid=False,
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

        try:
            surface = surface.compute_normals(
                consistent_normals=True,
                auto_orient_normals=True,
                split_vertices=False,
            )
        except Exception:
            pass

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

            actor = self.plotter.add_mesh(
                surface,
                scalars=config["scalar_name"],
                cmap=config["cmap"],
                clim=[value_min, value_max],
                opacity=0.95,
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


    # =====================================================================
    # 对外入口：整体模型播放
    # =====================================================================

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


    # =====================================================================
    # 对外入口：I / J / K 分层播放
    # =====================================================================

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


    # =====================================================================
    # 切换时间步
    # =====================================================================

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


    # =====================================================================
    # 播放状态信息
    # =====================================================================

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


    # =====================================================================
    # 停止播放
    # =====================================================================

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


    # =====================================================================
    # 2D Magnify
    # =====================================================================
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








    # =========================================================
    # K 层真实三维上表面等值线：基础依赖函数
    # =========================================================

    def _get_k_surface_contour_property_config(
        self,
        property_name,
    ):
        """
        cell_geometry_with_pressure 属性列：

        28: Pressure
        29: Kx
        30: Ky
        31: Kz
        32: Phi
        33: Sw
        """

        name = str(property_name).strip()

        config_map = {
            "Pressure": {
                "column": 28,
                "scalar_name": "Pressure",
            },
            "P": {
                "column": 28,
                "scalar_name": "Pressure",
            },
            "Kx": {
                "column": 29,
                "scalar_name": "Kx",
            },
            "Ky": {
                "column": 30,
                "scalar_name": "Ky",
            },
            "Kz": {
                "column": 31,
                "scalar_name": "Kz",
            },
            "Phi": {
                "column": 32,
                "scalar_name": "Phi",
            },
            "Porosity": {
                "column": 32,
                "scalar_name": "Phi",
            },
            "Sw": {
                "column": 33,
                "scalar_name": "Sw",
            },
        }

        if name not in config_map:
            print("=" * 60)
            print(
                "[K Surface Contour] 不支持属性：",
                property_name,
            )
            print(
                "[K Surface Contour] 支持属性："
                "Pressure / P / Kx / Ky / Kz / "
                "Phi / Porosity / Sw"
            )
            print("=" * 60)
            return None

        return config_map[name]


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
        sim_data,
        property_name,
        k_layer,
    ):
        """
        提取当前 K 层所有 leaf cell 的真实上表面。
        """
        cell_data = getattr(
            sim_data,
            "cell_geometry_with_pressure",
            None,
        )

        if cell_data is None:
            print(
                "[K Surface Contour] "
                "cell_geometry_with_pressure 不存在。"
            )
            return None, None, None, None

        cell_data = np.asarray(
            cell_data,
            dtype=np.float64,
        )

        if (
            cell_data.ndim != 2
            or cell_data.shape[0] == 0
        ):
            print(
                "[K Surface Contour] "
                "cell_geometry_with_pressure 为空。"
            )
            return None, None, None, None

        config = self._get_k_surface_contour_property_config(
            property_name
        )

        if config is None:
            return None, None, None, None

        property_column = int(
            config["column"]
        )

        if cell_data.shape[1] <= property_column:
            print(
                "[K Surface Contour] "
                f"属性列不存在：column={property_column}, "
                f"当前列数={cell_data.shape[1]}"
            )
            return None, None, None, None

        try:
            row_indices = self._get_layer_row_indices_by_parent_id(
                sim_data=sim_data,
                axis="k",
                layer_index=int(k_layer),
                cell_data=cell_data,
            )
        except Exception as exc:
            print("=" * 60)
            print("[K Surface Contour] K 层 leaf cell 筛选失败：")
            print(type(exc).__name__, exc)
            print("=" * 60)
            return None, None, None, None

        row_indices = np.asarray(
            row_indices,
            dtype=np.int64,
        )

        if row_indices.size == 0:
            print(
                f"[K Surface Contour] K={k_layer} 没有 leaf cell。"
            )
            return None, None, None, None

        selected_rows = cell_data[
            row_indices
        ]

        selected_values = selected_rows[
            :,
            property_column,
        ].astype(
            np.float64
        )

        valid_mask = np.isfinite(
            selected_values
        )

        selected_rows = selected_rows[
            valid_mask
        ]

        selected_values = selected_values[
            valid_mask
        ]

        if selected_rows.shape[0] == 0:
            print(
                f"[K Surface Contour] K={k_layer} 没有有效属性值。"
            )
            return None, None, None, None

        face_points = []
        face_values = []

        vertex_xy = []
        vertex_values = []

        skipped_count = 0

        for row, value in zip(
            selected_rows,
            selected_values,
        ):
            try:
                pts8 = np.asarray(
                    row[4:28],
                    dtype=np.float64,
                ).reshape(8, 3)
            except Exception:
                skipped_count += 1
                continue

            if not np.all(
                np.isfinite(pts8)
            ):
                skipped_count += 1
                continue

            top_face_ids = self._get_hexahedron_top_face_ids(
                pts8
            )

            if top_face_ids is None:
                skipped_count += 1
                continue

            top4 = pts8[
                top_face_ids
            ].copy()

            if top4.shape != (4, 3):
                skipped_count += 1
                continue

            face_points.append(
                top4
            )

            face_values.append(
                float(value)
            )

            for point in top4:
                vertex_xy.append([
                    float(point[0]),
                    float(point[1]),
                ])

                vertex_values.append(
                    float(value)
                )

        if len(face_points) < 2:
            print(
                "[K Surface Contour] "
                "有效上表面 face 数量不足。"
            )
            return None, None, None, None

        print(
            "[K Surface Contour] "
            f"K={k_layer}, "
            f"top_faces={len(face_points)}, "
            f"skipped={skipped_count}"
        )

        return (
            np.asarray(
                face_points,
                dtype=np.float64,
            ),
            np.asarray(
                face_values,
                dtype=np.float64,
            ),
            np.asarray(
                vertex_xy,
                dtype=np.float64,
            ),
            np.asarray(
                vertex_values,
                dtype=np.float64,
            ),
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

        # 只保留真实 top surface 覆盖范围内的格点。
        # 这样 contour 不会跑到模型外部。
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

        # ---------------------------------------------------------
        # 1. 用户手动指定具体 levels
        # ---------------------------------------------------------
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

        # ---------------------------------------------------------
        # 2. 用户指定固定等值距
        # ---------------------------------------------------------
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

        # ---------------------------------------------------------
        # 3. 根据 n_levels 自动生成整齐刻度
        # ---------------------------------------------------------
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

    # =========================================================
    # K 层真实三维上表面等值线
    # =========================================================
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

        # 文字太长时，最多只占总线长的 45%
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

            # 缺口前的线段
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

            # 缺口后的线段
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

                # K 层上表面标签默认朝外、朝上
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


    def _get_model_reference_span(
        self,
        sim_data,
    ):
        """
        获取模型最大尺寸，用于计算文字大小、偏移距离。
        """

        bounds = self.get_corner_model_bounds(
            sim_data
        )

        if bounds is None:
            return 1.0

        xmin, xmax, ymin, ymax, zmin, zmax = [
            float(value)
            for value in bounds
        ]

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

        # 让文字在自身局部坐标中以中心为原点
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

        # 确保文字在模型局部 XY 上尽量保持统一阅读方向
        #
        # 这样从上方看时，文字不会因为 contour 切线方向反过来
        # 而全部倒置。
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

        # 将文字在当前曲面内旋转 180 度
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

        # 文字两侧额外留一点空隙
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
        sim_data,
        property_name="Pressure",
        layer_index=0,
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
        self.clear_k_layer_top_contours(
            render=False
        )

        # ---------------------------------------------------------
        # 1. 提取当前 K 层真实 top face 与属性值
        # ---------------------------------------------------------
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

        # ---------------------------------------------------------
        # 2. 构建真实上表面投影器
        # ---------------------------------------------------------
        projection_data = self._build_k_surface_projection_data(
            face_points=face_points
        )

        if projection_data is None:
            return None

        # ---------------------------------------------------------
        # 3. 合并共享顶点属性
        # ---------------------------------------------------------
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
            property_name
        )

        if config is None:
            return None

        scalar_name = config[
            "scalar_name"
        ]

        # ---------------------------------------------------------
        # 4. 构建连续 contour 计算面
        # ---------------------------------------------------------
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

        # ---------------------------------------------------------
        # 5. 构建较疏、规整的 contour levels
        # ---------------------------------------------------------
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

        # ---------------------------------------------------------
        # 6. 每个等值等级单独生成 contour
        # ---------------------------------------------------------
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

            # -----------------------------------------------------
            # 不显示标签：直接保留整条线
            # -----------------------------------------------------
            if not show_labels:
                output_line_meshes.append(
                    surface_line
                )

                rendered_levels.append(
                    float(level)
                )

                continue

            # -----------------------------------------------------
            # 显示标签：
            # 切开 contour 中部 + 嵌入真实 3D Text3D
            # -----------------------------------------------------
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

        # ---------------------------------------------------------
        # 7. 合并所有等值线
        # ---------------------------------------------------------
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

        # ---------------------------------------------------------
        # 8. 合并所有 3D 数值文字
        # ---------------------------------------------------------
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

        # ---------------------------------------------------------
        # 9. 绘制 contour actor
        # ---------------------------------------------------------
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

        # ---------------------------------------------------------
        # 10. 绘制贴面 3D 数值文字 actor
        # ---------------------------------------------------------
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

        # ---------------------------------------------------------
        # 11. 缓存
        # ---------------------------------------------------------
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
            "property_name": str(
                property_name
            ),
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



    # =====================================================================
    # View All / Fit To View
    #
    # 功能：
    # 1. 保持当前 2D / 3D 观察方向；
    # 2. 不旋转模型；
    # 3. 自动移动相机焦点到模型中心；
    # 4. 自动调整缩放或相机距离；
    # 5. 让整个模型显示在当前窗口内；
    # 6. 模型与窗口边缘留白由 VIEW_ALL_PADDING 固定控制；
    # =====================================================================

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

            # actor 列表，例如 fracture_actors、well_actors
            if isinstance(value, (list, tuple)):
                for actor in value:
                    actor_bounds = self._get_actor_bounds(actor)

                    if actor_bounds is not None:
                        bounds_list.append(actor_bounds)

                continue

            # 单 actor
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




    # =========================================================
    # 折线垂向剖面 / Vertical Fence Section
    #
    # 操作方式：
    #
    # 1. enable_vertical_fence_section(sim_data, "Pressure")
    #
    # 2. 自动切到俯视图；
    #
    # 3. 左键单击：
    #    依次加入路径点 P1 -> P2 -> P3 ...
    #
    # 4. 双击左键：
    #    当前路径结束；
    #    最后一个点自动作为 End；
    #    生成沿路径、沿 Z 方向贯穿模型的竖向折线剖面。
    #
    # 注意：
    #
    # 本功能只使用每个点的 XY 坐标。
    #
    # 即使用户点击的几个点原始 Z 不一样，
    # 也不会生成一张倾斜平面，
    # 而是按每一个 XY 线段向 Z 方向拉通，
    # 形成“折线幕布式 / Fence Section”剖面。
    # =========================================================

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


    def _restore_fence_section_context(self):
        """
        恢复进入剖面功能前，
        压力场 / 孔隙度 / 渗透率等外部模型 actor 的透明度。
        """
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

        self.cache[
            "fence_section_context_actor_states"
        ] = []


    def _make_fence_section_context_transparent(self):

        self._restore_fence_section_context()

        actor_keys = (
            "pressure_field_actor",
            "sw_field_actor",
            "phi_field_actor",
            "perm_field_actor",
            "threshold_actor",
            "time_playback_actor",

            "layer_pressure_actor",
            "layer_sw_actor",
            "layer_phi_actor",
            "layer_perm_actor",
        )

        states = []

        for key in actor_keys:
            actor = self.cache.get(key)

            if actor is None:
                continue

            opacity = self._fence_get_actor_opacity(actor)
            visible = self._fence_get_actor_visible(actor)

            states.append(
                {
                    "actor": actor,
                    "opacity": opacity,
                    "visible": visible,
                }
            )

            if opacity is not None:
                self._fence_set_actor_opacity(
                    actor,
                    min(float(opacity), 0.18),
                )

        self.cache[
            "fence_section_context_actor_states"
        ] = states


    def _get_fence_section_property_config(
        self,
        property_name,
    ):
        config = self._get_pick_property_config(
            property_name
        )

        if config is None:
            return None

        name = str(property_name).strip()

        scalar_name_map = {
            "Pressure": "Pressure",
            "P": "Pressure",

            "Kx": "Kx",
            "Ky": "Ky",
            "Kz": "Kz",

            "Phi": "Phi",
            "Porosity": "Phi",

            "Sw": "Sw",
        }

        scalar_name = scalar_name_map.get(name)

        if scalar_name is None:
            return None

        return {
            "column": int(config["column"]),
            "title": str(
                config.get(
                    "title",
                    scalar_name,
                )
            ),
            "unit": str(
                config.get(
                    "unit",
                    "",
                )
            ),
            "scalar_name": scalar_name,
        }


    def _get_fence_section_grid_bounds(
        self,
        sim_data,
    ):

        cell_data = getattr(
            sim_data,
            "cell_geometry_with_pressure",
            None,
        )

        if cell_data is None:
            return None

        try:
            cell_data = np.asarray(
                cell_data,
                dtype=np.float64,
            )
        except Exception:
            return None

        if (
            cell_data.ndim != 2
            or cell_data.shape[0] == 0
            or cell_data.shape[1] < 28
        ):
            return None

        try:
            points = cell_data[
                :,
                4:28,
            ].reshape(
                -1,
                3,
            )
        except Exception:
            return None

        valid_mask = np.isfinite(
            points
        ).all(
            axis=1
        )

        points = points[
            valid_mask
        ]

        if points.shape[0] == 0:
            return None

        xmin = float(
            np.min(points[:, 0])
        )
        xmax = float(
            np.max(points[:, 0])
        )

        ymin = float(
            np.min(points[:, 1])
        )
        ymax = float(
            np.max(points[:, 1])
        )

        zmin = float(
            np.min(points[:, 2])
        )
        zmax = float(
            np.max(points[:, 2])
        )

        if (
            xmax <= xmin
            or ymax <= ymin
            or zmax < zmin
        ):
            return None

        return (
            xmin,
            xmax,
            ymin,
            ymax,
            zmin,
            zmax,
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

        # 路径只看 XY。
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

        # 平面法向与路径段垂直，
        # 且位于 XY 平面中。
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

        # 保留：
        # dot(P - start, tangent) >= 0
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

        # 保留：
        # dot(P - end, tangent) <= 0
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
        sim_data,
    ):

        if dataset is None or property_config is None:
            return None

        scalar_name = property_config[
            "scalar_name"
        ]

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

        cell_data = getattr(
            sim_data,
            "cell_geometry_with_pressure",
            None,
        )

        if cell_data is None:
            return None

        original_ids = None

        for id_name in (
            "OriginalRowIndex",
            "vtkOriginalCellIds",
            "vtkOriginalCellIds_",
        ):
            try:
                if id_name in dataset.cell_data:
                    original_ids = np.asarray(
                        dataset.cell_data[id_name],
                        dtype=np.int64,
                    )
                    break
            except Exception:
                pass

        if original_ids is None:
            return None

        if len(original_ids) != dataset.n_cells:
            return None

        column = int(
            property_config["column"]
        )

        try:
            source_values = np.asarray(
                cell_data[
                    original_ids,
                    column,
                ],
                dtype=np.float32,
            )
        except Exception:
            return None

        dataset.cell_data[
            scalar_name
        ] = source_values

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

            # 与 Pressure / Sw / Phi / Permeability
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

        # 使用最长路径段作为主方向，
        # 比取首尾点方向更稳定。
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


    def _render_vertical_fence_section(self):

        sim_data = self.cache.get(
            "fence_section_sim_data"
        )

        points = self.cache.get(
            "fence_section_points",
            [],
        ) or []

        property_name = self.cache.get(
            "fence_section_property",
            "Pressure",
        )

        if sim_data is None:
            self._emit_fence_section_info(
                "[Vertical Fence Section] "
                "no simulation data."
            )
            return False

        if len(points) < 2:
            self._emit_fence_section_info(
                "[Vertical Fence Section] "
                "at least two points are required."
            )
            return False

        property_config = self._get_fence_section_property_config(
            property_name
        )

        if property_config is None:
            return False

        cell_data = getattr(
            sim_data,
            "cell_geometry_with_pressure",
            None,
        )

        if cell_data is None:
            self._emit_fence_section_info(
                "[Vertical Fence Section] "
                "cell_geometry_with_pressure is missing."
            )
            return False

        try:
            cell_data = np.asarray(
                cell_data,
                dtype=np.float64,
            )
        except Exception:
            return False

        column = int(
            property_config["column"]
        )

        if (
            cell_data.ndim != 2
            or cell_data.shape[1] <= column
        ):
            self._emit_fence_section_info(
                "[Vertical Fence Section] "
                "requested property column is unavailable."
            )
            return False

        grid = self.cache.get(
            "fence_section_grid"
        )

        if grid is None:
            grid = self._build_cell_pick_grid(
                sim_data=sim_data,
                axis=None,
                layer_index=None,
            )

            self.cache[
                "fence_section_grid"
            ] = grid

        if grid is None:
            self._emit_fence_section_info(
                "[Vertical Fence Section] "
                "failed to build corner-point grid."
            )
            return False

        section_blocks = []

        for start_point, end_point in zip(
            points[:-1],
            points[1:],
        ):
            section = self._slice_grid_on_fence_segment(
                grid=grid,
                start_point=start_point,
                end_point=end_point,
            )

            if section is not None:
                section_blocks.append(
                    section
                )

        merged_section = self._merge_fence_section_blocks(
            section_blocks
        )

        if merged_section is None:
            self._emit_fence_section_info(
                "[Vertical Fence Section] "
                "the selected path does not intersect any grid cell."
            )
            return False

        scalar_preference = self._get_fence_section_scalar_preference(
            dataset=merged_section,
            property_config=property_config,
            sim_data=sim_data,
        )

        if scalar_preference is None:
            self._emit_fence_section_info(
                "[Vertical Fence Section] "
                "property data was not preserved by the slice."
            )
            return False

        scalar_name = property_config[
            "scalar_name"
        ]

        clim = self._fence_safe_clim(
            cell_data[
                :,
                column,
            ]
        )

        if clim is None:
            self._emit_fence_section_info(
                "[Vertical Fence Section] "
                "all property values are invalid."
            )
            return False

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

        try:
            actor = self.plotter.add_mesh(
                merged_section,
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
                render=False,
                pickable=False,
            )

        except TypeError:
            # 兼容旧版 PyVista。
            actor = self.plotter.add_mesh(
                merged_section,
                scalars=scalar_name,
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
                render=False,
            )

        except Exception as exc:
            self._emit_fence_section_info(
                "[Vertical Fence Section] "
                f"render failed: {type(exc).__name__}: {exc}"
            )
            return False

        try:
            actor.SetPickable(False)
        except Exception:
            pass

        self.cache[
            "fence_section_actor"
        ] = actor

        self.cache[
            "fence_section_data"
        ] = merged_section

        self.cache[
            "fence_section_scalar_name"
        ] = scalar_name

        self._add_fence_section_scalar_bar(
            mesh_actor=actor,
            property_config=property_config,
        )

        # 外部模型变透明，剖面保持不透明。
        self._make_fence_section_context_transparent()

        # 自动切换到便于观察剖面的角度。
        self._set_fence_section_result_camera()

        self._emit_fence_section_info(
            "[Vertical Fence Section] "
            f"completed: points={len(points)}, "
            f"segments={len(section_blocks)}, "
            f"property={property_config['title']}."
        )

        self._render()

        return True


    def enable_vertical_fence_section(
        self,
        sim_data,
        property_name="Pressure",
    ):

        property_config = self._get_fence_section_property_config(
            property_name
        )

        if property_config is None:
            return False

        cell_data = getattr(
            sim_data,
            "cell_geometry_with_pressure",
            None,
        )

        if cell_data is None:
            self._emit_fence_section_info(
                "[Vertical Fence Section] "
                "cell_geometry_with_pressure is missing."
            )
            return False

        try:
            cell_data = np.asarray(
                cell_data,
                dtype=np.float64,
            )
        except Exception:
            self._emit_fence_section_info(
                "[Vertical Fence Section] "
                "invalid cell_geometry_with_pressure."
            )
            return False

        if (
            cell_data.ndim != 2
            or cell_data.shape[0] == 0
            or cell_data.shape[1] < 34
        ):
            self._emit_fence_section_info(
                "[Vertical Fence Section] "
                "at least 34 columns are required."
            )
            return False

        # 避免测距、Cell Picking、框选放大和剖面抢同一个左键事件。
        self.disable_cell_info_picking(
            clear_highlight=False,
        )

        self.disable_petrel_distance_measure(
            clear_line=False,
        )

        self.deactivate_2d_magnify(
            render=False,
        )

        # 如果上一次已经有剖面，先完整清理。
        self.disable_vertical_fence_section(
            clear_result=True,
            render=False,
        )

        bounds = self._get_fence_section_grid_bounds(
            sim_data
        )

        if bounds is None:
            self._emit_fence_section_info(
                "[Vertical Fence Section] "
                "grid bounds are unavailable."
            )
            return False

        self.cache[
            "fence_section_sim_data"
        ] = sim_data

        self.cache[
            "fence_section_property"
        ] = str(property_name).strip()

        self.cache[
            "fence_section_scalar_name"
        ] = property_config[
            "scalar_name"
        ]

        self.cache[
            "fence_section_bounds"
        ] = tuple(
            float(value)
            for value in bounds
        )

        self.cache[
            "fence_section_grid"
        ] = None

        self.cache[
            "fence_section_points"
        ] = []

        self.cache[
            "fence_section_drawing"
        ] = True

        self.cache[
            "fence_section_finished"
        ] = False

        self.cache[
            "fence_section_last_info"
        ] = None

        self.cache[
            "fence_section_last_click_time"
        ] = None

        self.cache[
            "fence_section_last_click_display"
        ] = None

        self.cache[
            "fence_section_previous_camera_locked"
        ] = bool(
            getattr(
                self,
                "camera_direction_locked",
                False,
            )
        )

        # 自动转到俯视图。
        self.view_top()

        # 选点阶段禁止旋转，保证点击一定落在 XY 平面。
        self.lock_camera_direction(
            True
        )

        interactor = self._get_fence_section_interactor()

        if interactor is None:
            self.cache[
                "fence_section_drawing"
            ] = False

            self.lock_camera_direction(
                self.cache.get(
                    "fence_section_previous_camera_locked",
                    False,
                )
            )

            self._emit_fence_section_info(
                "[Vertical Fence Section] "
                "interactor is unavailable."
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

            observer_ids = [
                left_click_id,
                mouse_move_id,
            ]

        except Exception as exc:
            self.cache[
                "fence_section_observer_ids"
            ] = observer_ids

            self._remove_fence_section_observers()

            self.cache[
                "fence_section_drawing"
            ] = False

            self.lock_camera_direction(
                self.cache.get(
                    "fence_section_previous_camera_locked",
                    False,
                )
            )

            self._emit_fence_section_info(
                "[Vertical Fence Section] "
                f"observer registration failed: "
                f"{type(exc).__name__}: {exc}"
            )

            return False

        self.cache[
            "fence_section_observer_ids"
        ] = observer_ids

        self._emit_fence_section_info(
            "[Vertical Fence Section] "
            "drawing started. "
            "Left-click to add points; "
            "double-click to finish."
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

        self._emit_fence_section_info(
            "[Vertical Fence Section] "
            "drawing cancelled."
        )

        if render:
            self._render()


    def clear_vertical_fence_section(
        self,
        render=True,
    ):

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

        if render:
            self._render()


    def disable_vertical_fence_section(
        self,
        clear_result=True,
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

        self.cache[
            "fence_section_last_click_time"
        ] = None

        self.cache[
            "fence_section_last_click_display"
        ] = None

        if clear_result:
            self.clear_vertical_fence_section(
                render=False,
            )

            self.cache[
                "fence_section_sim_data"
            ] = None

            self.cache[
                "fence_section_bounds"
            ] = None

            self.cache[
                "fence_section_grid"
            ] = None

            self.cache[
                "fence_section_property"
            ] = "Pressure"

        if render:
            self._render()


    def set_vertical_fence_section_property(
        self,
        property_name,
    ):

        config = self._get_fence_section_property_config(
            property_name
        )

        if config is None:
            return False

        self.cache[
            "fence_section_property"
        ] = str(property_name).strip()

        self.cache[
            "fence_section_scalar_name"
        ] = config[
            "scalar_name"
        ]

        if self.cache.get(
            "fence_section_finished",
            False,
        ):
            return self._render_vertical_fence_section()

        return True


    def is_vertical_fence_section_drawing(self):

        return bool(
            self.cache.get(
                "fence_section_drawing",
                False,
            )
        )


    # 给 UI 调用的简短别名。
    enable_fence_section = enable_vertical_fence_section
    disable_fence_section = disable_vertical_fence_section
    clear_fence_section = clear_vertical_fence_section