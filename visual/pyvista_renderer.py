"""
基于 PyVista 的可视化渲染器。
"""

from __future__ import annotations

import sys
from pathlib import Path


"""def get_bright_jet_cmap():
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
    return LinearSegmentedColormap.from_list("bright_jet", bright_jet_colors, N=512)"""

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
        不移除动态相机监听器。
        """

        self._remove_actor_list(
            self.cache.get("fixed_coordinate_axis_actors", [])
        )

        self._remove_actor(
            self.cache.get("fixed_coordinate_label_actor")
        )

        self.cache["fixed_coordinate_axis_actors"] = []
        self.cache["fixed_coordinate_label_actor"] = None
        self.cache["fixed_coordinate_bounds"] = None
        self.cache["fixed_coordinate_visible"] = False


    @staticmethod
    def _nice_grid_step(value):
        """
        将普通数值转为适合显示的坐标刻度步长。
        """

        value = float(value)

        if value <= 0.0:
            return 1.0

        exponent = np.floor(np.log10(value))
        fraction = value / (10.0 ** exponent)

        if fraction < 1.5:
            nice_fraction = 1.0
        elif fraction < 3.0:
            nice_fraction = 2.0
        elif fraction < 7.0:
            nice_fraction = 5.0
        else:
            nice_fraction = 10.0

        return float(
            nice_fraction * (10.0 ** exponent)
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
        X、Y、Z 三个方向共用同一套间隔。
        """

        x_span = abs(float(xmax) - float(xmin))
        y_span = abs(float(ymax) - float(ymin))
        z_span = abs(float(zmax) - float(zmin))

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

        return self._nice_grid_step(raw_step)


    @staticmethod
    def _make_fixed_axis_ticks(
        vmin,
        vmax,
        step,
    ):
        """
        根据真实模型坐标范围生成刻度。
        最小值和最大值一定保留。
        """

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
        """
        以真实工程坐标显示。
        不显示科学计数法。
        """

        value = float(value)

        if abs(value) >= 1.0:
            return f"{value:.0f}"

        return f"{value:.3f}"


    def _add_fixed_coordinate_line(
        self,
        start_point,
        end_point,
        color=(0.58, 0.58, 0.58),
        line_width=1.0,
        opacity=0.65,
    ):
        """
        添加坐标轴线、边框线、网格线或刻度短线。
        """

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


    def _create_fixed_coordinate_labels(
        self,
        label_points,
        label_texts,
    ):
        """
        创建刻度数字和坐标轴标题。
        """

        self._remove_actor(
            self.cache.get("fixed_coordinate_label_actor")
        )

        self.cache["fixed_coordinate_label_actor"] = None

        if not label_points or not label_texts:
            return

        try:
            points = np.asarray(
                label_points,
                dtype=np.float64,
            )

            labels = [
                str(text)
                for text in label_texts
            ]

            actor = self.plotter.add_point_labels(
                points=points,
                labels=labels,
                font_size=COORDINATE_LABEL_FONT_SIZE,
                text_color=(0.0, 0.0, 0.0),
                show_points=False,
                fill_shape=False,
                shape_opacity=0.0,
                always_visible=True,
                render=False,
            )

            self.cache[
                "fixed_coordinate_label_actor"
            ] = actor

        except Exception as exc:
            print("=" * 60)
            print("创建动态坐标文字失败：")
            print(type(exc).__name__, exc)
            print("=" * 60)


    def get_corner_model_bounds(self, sim_data):
        """
        从 cell_geometry_with_pressure 中获取模型真实坐标范围。
        """

        cell_data = getattr(
            sim_data,
            "cell_geometry_with_pressure",
            None,
        )

        if cell_data is None:
            return None

        if len(cell_data) == 0:
            return None

        try:
            # 第 4 ~ 27 列为每个单元 8 个顶点的 XYZ 坐标
            raw_points = cell_data[:, 4:28].reshape(
                -1,
                3,
            )

            return (
                float(np.min(raw_points[:, 0])),
                float(np.max(raw_points[:, 0])),

                float(np.min(raw_points[:, 1])),
                float(np.max(raw_points[:, 1])),

                float(np.min(raw_points[:, 2])),
                float(np.max(raw_points[:, 2])),
            )

        except Exception as exc:
            print("=" * 60)
            print("获取当前模型坐标范围失败：")
            print(type(exc).__name__, exc)
            print("=" * 60)
            return None


    def _get_camera_aware_coordinate_signature(
        self,
        bounds,
    ):
        """
        判断相机在模型哪个方向。
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

        # 相机在 +X 侧，看向模型时，坐标面放到 xmin
        x_side = (
            "xmin"
            if camera_position[0] >= center_x
            else "xmax"
        )

        # 相机在 +Y 侧，看向模型时，坐标面放到 ymin
        y_side = (
            "ymin"
            if camera_position[1] >= center_y
            else "ymax"
        )

        # 相机在 +Z 上方，看向模型时，坐标面放到 zmin
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
            signature = self._get_camera_aware_coordinate_signature(
                bounds
            )

        if signature is None:
            signature = (
                "xmin",
                "ymin",
                "zmin",
            )

        x_side, y_side, z_side = signature

        # 三个“背面”
        x_plane = xmin if x_side == "xmin" else xmax
        y_plane = ymin if y_side == "ymin" else ymax
        z_plane = zmin if z_side == "zmin" else zmax

        # 对应的另一侧边界
        x_outer = xmax if x_side == "xmin" else xmin
        y_outer = ymax if y_side == "ymin" else ymin
        z_outer = zmax if z_side == "zmin" else zmin

        # 从坐标面向外偏移的方向
        sign_x_plane = -1.0 if x_side == "xmin" else 1.0
        sign_y_plane = -1.0 if y_side == "ymin" else 1.0
        sign_z_plane = -1.0 if z_side == "zmin" else 1.0

        # 从外侧边向外偏移的方向
        sign_x_outer = 1.0 if x_outer == xmax else -1.0
        sign_y_outer = 1.0 if y_outer == ymax else -1.0
        sign_z_outer = 1.0 if z_outer == zmax else -1.0

        self._clear_fixed_coordinate_axes()

        # ---------------------------------------------------------
        # 统一网格步长和真实刻度
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
        # 标签和刻度向外偏移距离
        # ---------------------------------------------------------
        offset_x = max(
            abs(x_span) * 0.035,
            grid_step * 0.40,
        )

        offset_y = max(
            abs(y_span) * 0.035,
            grid_step * 0.40,
        )

        offset_z = max(
            abs(z_span) * 0.035,
            grid_step * 0.40,
        )

        tick_x = max(
            abs(x_span) * 0.012,
            grid_step * 0.10,
        )

        tick_y = max(
            abs(y_span) * 0.012,
            grid_step * 0.10,
        )

        # =========================================================
        # 统一 X / Y / Z 标题到各自刻度数字之间的真实距离
        # =========================================================
        axis_title_to_tick_gap = (
            offset_y * (3.0 - 1.35)
        )

        # Y 轴刻度数字到 Y 边框的距离
        y_axis_tick_label_offset = (
            offset_x * 1.35
        )

        # Z 轴刻度数字到 Z 边框的距离
        z_axis_tick_label_offset = (
            offset_x * 1.35
        )

        # Y-axis 到 Y 轴边框的最终距离
        y_axis_title_offset = (
            y_axis_tick_label_offset
            + axis_title_to_tick_gap
        )

        # Z-axis 到 Z 轴边框的最终距离
        z_axis_title_offset = (
            z_axis_tick_label_offset
            + axis_title_to_tick_gap
        )

        # 带刻度的边：黑色加粗
        axis_color = (0.12, 0.12, 0.12)
        axis_line_width = 1.8

        # 普通边框
        edge_color = (0.58, 0.58, 0.58)
        edge_line_width = 1.0

        # 内部网格
        grid_color = (0.62, 0.62, 0.62)
        grid_line_width = 0.7

        label_points = []
        label_texts = []

        # =========================================================
        # 1. XY 平面
        # z = z_plane
        # =========================================================

        # 前方 X 刻度边
        self._add_fixed_coordinate_line(
            (xmin, y_outer, z_plane),
            (xmax, y_outer, z_plane),
            color=axis_color,
            line_width=axis_line_width,
            opacity=1.0,
        )

        # 前方 Y 刻度边
        self._add_fixed_coordinate_line(
            (x_outer, ymin, z_plane),
            (x_outer, ymax, z_plane),
            color=axis_color,
            line_width=axis_line_width,
            opacity=1.0,
        )

        # XY 面另外两条普通边
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

        # XY 面 X 向网格
        for x in x_ticks:
            self._add_fixed_coordinate_line(
                (x, ymin, z_plane),
                (x, ymax, z_plane),
                color=grid_color,
                line_width=grid_line_width,
                opacity=0.45,
            )

        # XY 面 Y 向网格
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

        # 左侧 Z 刻度边
        self._add_fixed_coordinate_line(
            (x_plane, y_outer, zmin),
            (x_plane, y_outer, zmax),
            color=axis_color,
            line_width=axis_line_width,
            opacity=1.0,
        )

        # 顶部 Y 刻度边
        self._add_fixed_coordinate_line(
            (x_plane, ymin, z_outer),
            (x_plane, ymax, z_outer),
            color=axis_color,
            line_width=axis_line_width,
            opacity=1.0,
        )

        # YZ 面另一条竖边
        self._add_fixed_coordinate_line(
            (x_plane, y_plane, zmin),
            (x_plane, y_plane, zmax),
            color=edge_color,
            line_width=edge_line_width,
            opacity=0.75,
        )

        # YZ 面底边
        self._add_fixed_coordinate_line(
            (x_plane, ymin, z_plane),
            (x_plane, ymax, z_plane),
            color=edge_color,
            line_width=edge_line_width,
            opacity=0.75,
        )

        # YZ 面 Y 向网格
        for y in y_ticks:
            self._add_fixed_coordinate_line(
                (x_plane, y, zmin),
                (x_plane, y, zmax),
                color=grid_color,
                line_width=grid_line_width,
                opacity=0.45,
            )

        # YZ 面 Z 向网格
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

        # 右侧 Z 刻度边
        self._add_fixed_coordinate_line(
            (x_outer, y_plane, zmin),
            (x_outer, y_plane, zmax),
            color=axis_color,
            line_width=axis_line_width,
            opacity=1.0,
        )

        # 顶部 X 刻度边
        self._add_fixed_coordinate_line(
            (xmin, y_plane, z_outer),
            (xmax, y_plane, z_outer),
            color=axis_color,
            line_width=axis_line_width,
            opacity=1.0,
        )

        # XZ 面另一条竖边
        self._add_fixed_coordinate_line(
            (x_plane, y_plane, zmin),
            (x_plane, y_plane, zmax),
            color=edge_color,
            line_width=edge_line_width,
            opacity=0.75,
        )

        # XZ 面底边
        self._add_fixed_coordinate_line(
            (xmin, y_plane, z_plane),
            (xmax, y_plane, z_plane),
            color=edge_color,
            line_width=edge_line_width,
            opacity=0.75,
        )

        # XZ 面 X 向网格
        for x in x_ticks:
            self._add_fixed_coordinate_line(
                (x, y_plane, zmin),
                (x, y_plane, zmax),
                color=grid_color,
                line_width=grid_line_width,
                opacity=0.45,
            )

        # XZ 面 Z 向网格
        for z in z_ticks:
            self._add_fixed_coordinate_line(
                (xmin, y_plane, z),
                (xmax, y_plane, z),
                color=grid_color,
                line_width=grid_line_width,
                opacity=0.45,
            )

        # =========================================================
        # 上方 X 轴刻度
        # =========================================================
        for x in x_ticks:
            self._add_fixed_coordinate_line(
                (x, y_plane, z_outer),
                (
                    x,
                    y_plane + sign_y_plane * tick_y,
                    z_outer,
                ),
                color=axis_color,
                line_width=1.2,
                opacity=1.0,
            )

            label_points.append(
                (
                    x,
                    y_plane + sign_y_plane * offset_y * 1.35,
                    z_outer + sign_z_outer * offset_z * 0.08,
                )
            )

            label_texts.append(
                self._format_fixed_coordinate_value(x)
            )

        # =========================================================
        # 上方 Y 轴刻度
        # =========================================================
        for y in y_ticks:
            self._add_fixed_coordinate_line(
                (x_plane, y, z_outer),
                (
                    x_plane + sign_x_plane * tick_x,
                    y,
                    z_outer,
                ),
                color=axis_color,
                line_width=1.2,
                opacity=1.0,
            )

            label_points.append(
                (
                    x_plane + sign_x_plane * offset_x * 1.35,
                    y,
                    z_outer + sign_z_outer * offset_z * 0.08,
                )
            )

            label_texts.append(
                self._format_fixed_coordinate_value(y)
            )

        # =========================================================
        # 前方 X 轴刻度
        # =========================================================
        for x in x_ticks:
            self._add_fixed_coordinate_line(
                (x, y_outer, z_plane),
                (
                    x,
                    y_outer + sign_y_outer * tick_y,
                    z_plane,
                ),
                color=axis_color,
                line_width=1.2,
                opacity=1.0,
            )

            label_points.append(
                (
                    x,
                    y_outer + sign_y_outer * offset_y * 1.35,
                    z_plane + sign_z_plane * offset_z * 0.10,
                )
            )

            label_texts.append(
                self._format_fixed_coordinate_value(x)
            )

        # =========================================================
        # 前方 Y 轴刻度
        # =========================================================
        for y in y_ticks:
            self._add_fixed_coordinate_line(
                (x_outer, y, z_plane),
                (
                    x_outer + sign_x_outer * tick_x,
                    y,
                    z_plane,
                ),
                color=axis_color,
                line_width=1.2,
                opacity=1.0,
            )

            label_points.append(
                (
                    x_outer + sign_x_outer * offset_x * 1.35,
                    y,
                    z_plane + sign_z_plane * offset_z * 0.10,
                )
            )

            label_texts.append(
                self._format_fixed_coordinate_value(y)
            )

        # =========================================================
        # 左右两侧 Z 轴刻度
        # =========================================================
        for z in z_ticks:

            # YZ 面外侧 Z 边
            self._add_fixed_coordinate_line(
                (x_plane, y_outer, z),
                (
                    x_plane + sign_x_plane * tick_x,
                    y_outer,
                    z,
                ),
                color=axis_color,
                line_width=1.2,
                opacity=1.0,
            )

            label_points.append(
                (
                    x_plane + sign_x_plane * offset_x * 1.35,
                    y_outer,
                    z,
                )
            )

            label_texts.append(
                self._format_fixed_coordinate_value(z)
            )

            # XZ 面外侧 Z 边
            self._add_fixed_coordinate_line(
                (x_outer, y_plane, z),
                (
                    x_outer + sign_x_outer * tick_x,
                    y_plane,
                    z,
                ),
                color=axis_color,
                line_width=1.2,
                opacity=1.0,
            )

            label_points.append(
                (
                    x_outer + sign_x_outer * offset_x * 1.35,
                    y_plane,
                    z,
                )
            )

            label_texts.append(
                self._format_fixed_coordinate_value(z)
            )

        # =========================================================
        # 坐标轴标题
        #
        # X-axis 保持原位置。
        #
        # Y-axis、Z-axis 到各自刻度数字的真实三维距离，
        # 均与 X-axis 到 X 轴刻度数字的距离一致。
        # =========================================================
        label_points.extend([
            # X-axis
            (
                (xmin + xmax) * 0.5,
                y_outer + sign_y_outer * offset_y * 3.0,
                z_plane + sign_z_plane * offset_z * 0.10,
            ),

            # Y-axis
            (
                x_outer + sign_x_outer * y_axis_title_offset,
                (ymin + ymax) * 0.5,
                z_plane + sign_z_plane * offset_z * 0.10,
            ),

            # Z-axis
            (
                x_plane + sign_x_plane * z_axis_title_offset,
                y_outer,
                (zmin + zmax) * 0.5,
            ),
        ])

        label_texts.extend([
            "X-axis",
            "Y-axis",
            "Z-axis",
        ])

        self._create_fixed_coordinate_labels(
            label_points=label_points,
            label_texts=label_texts,
        )

        self.cache["fixed_coordinate_bounds"] = (
            xmin,
            xmax,
            ymin,
            ymax,
            zmin,
            zmax,
        )

        self.cache["fixed_coordinate_visible"] = True
        self.cache["camera_aware_coordinate_signature"] = signature


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

            if inner_interactor is not None and (
                hasattr(inner_interactor, "add_observer")
                or hasattr(inner_interactor, "AddObserver")
            ):
                return inner_interactor

        return None


    def _remove_camera_aware_coordinate_observers(self):
        """
        取消动态坐标系的相机监听器。
        """

        observers = self.cache.get(
            "camera_aware_coordinate_observers",
            [],
        ) or []

        for interactor, observer_id in observers:
            if interactor is None or observer_id is None:
                continue

            try:
                if hasattr(interactor, "remove_observer"):
                    interactor.remove_observer(observer_id)

                elif hasattr(interactor, "RemoveObserver"):
                    interactor.RemoveObserver(observer_id)

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
        监听旋转、平移、缩放过程中的相机变化。
        """

        interactor = self._get_render_interactor_for_coordinate_axes()

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
        拖动旋转过程中自动执行。
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

        new_signature = self._get_camera_aware_coordinate_signature(
            bounds
        )

        if new_signature is None:
            return

        old_signature = self.cache.get(
            "camera_aware_coordinate_signature"
        )

        if new_signature == old_signature:
            return

        self.create_fixed_3d_coordinate_axes(
            bounds=bounds,
            approx_divisions=COORDINATE_APPROX_DIVISIONS,
            signature=new_signature,
        )

        self._render()


    # =====================================================================
    # UI 调用接口
    # =====================================================================

    def show_coordinate_axes_for_model(self, sim_data):
        """
        根据当前模型显示动态坐标系。
        """

        model_bounds = self.get_corner_model_bounds(
            sim_data
        )

        if model_bounds is None:
            print("=" * 60)
            print("显示坐标系失败：当前模型没有有效角点网格。")
            print("需要 cell_geometry_with_pressure 数据。")
            print("=" * 60)
            return False

        try:
            self.cache[
                "camera_aware_coordinate_enabled"
            ] = True

            signature = self._get_camera_aware_coordinate_signature(
                model_bounds
            )

            self.create_fixed_3d_coordinate_axes(
                bounds=model_bounds,
                approx_divisions=COORDINATE_APPROX_DIVISIONS,
                signature=signature,
            )

            # 防止重复点击“显示坐标系”后注册多个监听器
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
        不影响压力场、井、裂缝。
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

        label_actor = self.cache.get(
            "fixed_coordinate_label_actor"
        )

        if label_actor is not None:
            try:
                label_actor.visibility = False
            except Exception:
                try:
                    label_actor.SetVisibility(False)
                except Exception:
                    pass

        self.cache["fixed_coordinate_visible"] = False

        self._render()


    def disable_camera_aware_coordinate_axes(
        self,
        clear_axes=True,
    ):
        """
        完全关闭动态坐标系。

        clear_axes=True：
            删除坐标系 actor。

        clear_axes=False：
            只停止监听，保留当前显示结果。
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

            #动态三面坐标系
            "fixed_coordinate_axis_actors": [],
            "fixed_coordinate_label_actor": None,
            "fixed_coordinate_bounds": None,
            "fixed_coordinate_visible": False,

            "camera_aware_coordinate_enabled": False,
            "camera_aware_coordinate_signature": None,
            "camera_aware_coordinate_observers": [],

            # 2D Magnify
            "magnify_2d_active": False,
            "magnify_2d_dragging": False,
            "magnify_2d_world_bounds": None,
            "magnify_2d_start_xy": None,
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

    """def _get_active_parent_cells_from_leaf_data(self, sim_data):
        
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

        self.plotter.render()"""

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
                show_edges=False,
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
        #
        # 初次阈值渲染时默认 True。
        # 用户通过按钮关闭后，再次筛选会保持关闭。
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

        # =========================================================
        # 1. 选择渗透率方向
        # 数据结构：
        # 28 P
        # 29 Kx
        # 30 Ky
        # 31 Kz
        # 32 Phi
        # 33 Sw
        # =========================================================
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
            # 颜色条范围和压力场一样：当前属性全场 min/max
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
            # 和压力场 render_corner_pressure_field 的逻辑保持一致
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
            # 参数模仿压力场
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

        perm_direction:
            "x" -> Kx，第 29 列
            "y" -> Ky，第 30 列
            "z" -> Kz，第 31 列

        axis:
            "i" -> 固定 i，显示 I 方向剖面
            "j" -> 固定 j，显示 J 方向剖面
            "k" -> 固定 k，显示 K 层平面

        layer_index:
            层号，从 0 开始。
        """

        if not sim_data.corner_point_grid:
            return

        if getattr(sim_data, "cell_geometry_with_pressure", None) is None:
            return

        # =========================================================
        # 1. 渗透率方向配置
        # 数据结构：
        # 28 P
        # 29 Kx
        # 30 Ky
        # 31 Kz
        # 32 Phi
        # 33 Sw
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

        axis=None：
            构建全场拾取网格。

        axis="i" / "j" / "k"：
            只构建当前逻辑 I/J/K 层的拾取网格。

        分层筛选规则：
            根据 leaf 对应的 parent_id 推导逻辑 I/J/K，
            不再通过粗网格的 AABB 包围盒筛选。
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