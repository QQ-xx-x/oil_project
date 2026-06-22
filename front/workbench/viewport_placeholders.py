# -*- coding: utf-8 -*-
"""工程主界面使用的二维、三维和图表视图窗口。"""

import math

from PyQt5.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QPainter, QPen, QPolygonF
from PyQt5.QtWidgets import QFrame, QVBoxLayout, QWidget

from .view_toolbar import ViewToolbar


RESULT_STYLES = {
    "pressure_field": {
        "legend": "压力",
        "unit": "bar",
        "ticks": ("800", "500", "200"),
        "colors": ["#ff1800", "#ff9a00", "#fff35a", "#6ad348"],
        "surface": QColor("#e7c332"),
    },
    "water_saturation_field": {
        "legend": "含水饱和度",
        "unit": "0-1",
        "ticks": ("1.0", "0.5", "0.0"),
        "colors": ["#004dff", "#00a8ff", "#00e0c8", "#d7fff1"],
        "surface": QColor("#3ec8d9"),
    },
    "permeability_field": {
        "legend": "渗透率",
        "unit": "mD",
        "ticks": ("100", "10", "1"),
        "colors": ["#ff0000", "#ff9a00", "#ffff00", "#3cff00", "#00ddcc"],
        "surface": QColor("#c5d000"),
    },
    "porosity_field": {
        "legend": "孔隙度",
        "unit": "0-1",
        "ticks": ("0.30", "0.15", "0.00"),
        "colors": ["#7428d8", "#4864e8", "#2aa7ff", "#b7e3ff"],
        "surface": QColor("#7aa6ff"),
    },
}


CHART_STYLES = {
    "production_curve": {
        "title": "生产曲线",
        "x": "时间",
        "y": "产量",
        "color": QColor("#2970c8"),
    },
    "relative_permeability_curve": {
        "title": "相对渗透率曲线",
        "x": "含水饱和度 Sw",
        "y": "相对渗透率 kr",
        "color": QColor("#23a65a"),
    },
    "blasingame_curve": {
        "title": "Blasingame 曲线",
        "x": "时间函数",
        "y": "规整化流量",
        "color": QColor("#d45500"),
    },
    "pvt_curve": {
        "title": "PVT 表曲线",
        "x": "压力",
        "y": "Z 因子",
        "color": QColor("#7b4bc4"),
    },
}


class ThreeDViewport(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("threeDViewport")
        self.setMinimumHeight(360)
        self._real_view = None
        self._real_renderer = None
        self._real_view_error = ""
        self.simulation_data = None
        self.context_title = "当前结果：三维视图"
        self.context_detail = "在结果树中选择结果或图层后，这里显示对应占位视图。"
        self.display_key = "permeability_field"
        self._rendered_display_key = None
        self.layers = {
            "grid": True,
            "well": True,
            "natural_fractures": True,
            "hydraulic_fractures": True,
            "dual_porosity": False,
            "grid_refinement": True,
        }

    def set_context(self, title, detail, display_key=None):
        self.context_title = title
        self.context_detail = detail
        if display_key:
            self.display_key = display_key
        should_render = (
            self.simulation_data is not None
            and self._rendered_display_key != self.display_key
        )
        if should_render and self._ensure_real_view():
            self._render_real_result()
        self.update()

    def set_simulation_data(self, sim_data):
        self.simulation_data = sim_data
        if self._ensure_real_view():
            self._render_real_result()
        self.update()

    def set_layer_state(self, layer_key, enabled):
        if layer_key in self.layers:
            self.layers[layer_key] = bool(enabled)
            if self.simulation_data is not None and self._real_renderer is not None:
                self._apply_real_layer_state(layer_key, enabled)
            self.update()

    def _ensure_real_view(self):
        if self._real_renderer is not None:
            return True
        if self._real_view_error:
            return False
        try:
            from visual.pyvista_renderer import PyVistaRenderer
            from visual.pyvista_view import PyVistaView
        except Exception as exc:
            self._real_view_error = str(exc)
            return False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._real_view = PyVistaView(self)
        layout.addWidget(self._real_view)
        self._real_renderer = PyVistaRenderer(self._real_view)
        self._real_view.show()
        return True

    def _render_real_result(self):
        renderer = self._real_renderer
        sim_data = self.simulation_data
        if renderer is None or sim_data is None:
            return
        renderer.clear_cache()
        self._rendered_display_key = self.display_key
        if getattr(sim_data, "corner_point_grid", None) is not None:
            renderer.render_corner_point_grid(sim_data)
        if getattr(sim_data, "cell_geometry_with_pressure", None) is not None:
            renderer.render_corner_pressure_field(sim_data)
        elif getattr(sim_data, "pressure_field", None):
            renderer.render_mode3_smooth_pressure(sim_data)
        if getattr(sim_data, "corner_lgr_parent_grid_geometry", None) is not None or (
                getattr(sim_data, "corner_lgr_refined_grid_geometry", None) is not None):
            renderer.render_corner_lgr_grid(sim_data)
        if getattr(sim_data, "fractures", None):
            if hasattr(renderer, "render_corner_fractures"):
                renderer.render_corner_fractures(sim_data)
            else:
                renderer.render_fractures(sim_data)
        if getattr(sim_data, "wells", None):
            renderer.render_wells(sim_data)
        for layer_key, enabled in self.layers.items():
            self._apply_real_layer_state(layer_key, enabled)

    def _apply_real_layer_state(self, layer_key, enabled):
        renderer = self._real_renderer
        sim_data = self.simulation_data
        if renderer is None or sim_data is None:
            return
        if layer_key == "grid":
            if hasattr(renderer, "toggle_grid_visibility"):
                renderer.toggle_grid_visibility(bool(enabled))
            elif hasattr(renderer, "ensure_grid_lines"):
                renderer.ensure_grid_lines(sim_data)
                renderer.toggle_grid_lines(bool(enabled))
        elif layer_key == "grid_refinement":
            if hasattr(renderer, "toggle_corner_lgr_grid_visibility"):
                renderer.toggle_corner_lgr_grid_visibility(bool(enabled))
        elif layer_key in {"natural_fractures", "hydraulic_fractures"}:
            if hasattr(renderer, "ensure_fractures"):
                renderer.ensure_fractures(sim_data)
            fracture_type = "hydraulic" if layer_key == "hydraulic_fractures" else "natural"
            if hasattr(renderer, "toggle_fractures_visibility"):
                try:
                    renderer.toggle_fractures_visibility(bool(enabled), fracture_type)
                except TypeError:
                    renderer.toggle_fractures_visibility(bool(enabled))
            elif hasattr(renderer, "toggle_fractures"):
                try:
                    renderer.toggle_fractures(bool(enabled), fracture_type)
                except TypeError:
                    renderer.toggle_fractures(bool(enabled))
        elif layer_key == "well":
            if enabled and hasattr(renderer, "render_wells"):
                renderer.render_wells(sim_data)
            if hasattr(renderer, "toggle_wells_visibility"):
                renderer.toggle_wells_visibility(bool(enabled))
        elif layer_key == "pressure":
            if hasattr(renderer, "toggle_pressure_visibility"):
                renderer.toggle_pressure_visibility(bool(enabled))

    def paintEvent(self, event):
        if self._real_view is not None and self._real_view.isVisible():
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#050505"))

        style = RESULT_STYLES.get(self.display_key, RESULT_STYLES["permeability_field"])
        w, h = self.width(), self.height()
        origin = QPointF(w * 0.16, h * 0.72)
        x_vec = QPointF(w * 0.60, -h * 0.20)
        y_vec = QPointF(w * 0.24, h * 0.18)

        if self.layers["grid"]:
            self._draw_result_surface(painter, origin, x_vec, y_vec, style)

        if self.layers["grid_refinement"]:
            painter.setPen(QPen(QColor("#ffcc33"), 2))
            refined = QRectF(
                origin + QPointF(w * 0.34, -h * 0.10),
                origin + QPointF(w * 0.53, h * 0.04),
            )
            painter.drawRect(refined.normalized())

        if self.layers["natural_fractures"]:
            self._draw_fracture_swarm(painter, origin, x_vec, y_vec, QColor("#f0a000"))

        if self.layers["hydraulic_fractures"]:
            self._draw_hydraulic_fractures(painter, origin, w, h)

        if self.layers["well"]:
            self._draw_wells(painter, origin, w, h)

        self._draw_color_bar(painter, style)
        self._draw_context(painter)
        self._draw_layer_status(painter)
        self._draw_axis_glyph(painter)
        painter.end()

    def _draw_result_surface(self, painter, origin, x_vec, y_vec, style):
        surface_color = style["surface"]
        plane = QPolygonF([origin, origin + x_vec, origin + x_vec + y_vec, origin + y_vec])
        fill_color = QColor(surface_color)
        fill_color.setAlpha(78)
        painter.setPen(Qt.NoPen)
        painter.setBrush(fill_color)
        painter.drawPolygon(plane)

        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor(surface_color).darker(130), 1))
        rows, cols = 46, 70
        for i in range(rows + 1):
            t = i / rows
            p1 = origin + y_vec * t
            painter.drawLine(p1, p1 + x_vec)
        for j in range(cols + 1):
            t = j / cols
            p1 = origin + x_vec * t
            painter.drawLine(p1, p1 + y_vec)
        painter.setPen(QPen(QColor(surface_color).lighter(135), 2))
        for band in [0.18, 0.38, 0.62]:
            painter.drawLine(
                origin + x_vec * band + y_vec * 0.04,
                origin + x_vec * (band + 0.18) + y_vec * 0.82,
            )
        self._draw_result_patches(painter, origin, x_vec, y_vec, style)

    def _draw_result_patches(self, painter, origin, x_vec, y_vec, style):
        colors = [QColor(color) for color in style["colors"]]
        patches = [
            (0.18, 0.22, 0.18, 0.20, colors[1]),
            (0.43, 0.34, 0.22, 0.18, colors[2]),
            (0.62, 0.56, 0.18, 0.22, colors[-1]),
        ]
        painter.setPen(Qt.NoPen)
        for sx, sy, sw, sh, color in patches:
            color.setAlpha(115)
            polygon = QPolygonF([
                origin + x_vec * sx + y_vec * sy,
                origin + x_vec * (sx + sw) + y_vec * sy,
                origin + x_vec * (sx + sw) + y_vec * (sy + sh),
                origin + x_vec * sx + y_vec * (sy + sh),
            ])
            painter.setBrush(color)
            painter.drawPolygon(polygon)

    def _draw_fracture_swarm(self, painter, origin, x_vec, y_vec, color):
        painter.setPen(QPen(color, 1.8))
        for offset in [0.08, 0.16, 0.24, 0.34, 0.46, 0.58]:
            start = origin + x_vec * offset + y_vec * (0.12 + offset * 0.25)
            end = origin + x_vec * (offset + 0.10) + y_vec * (0.58 + offset * 0.10)
            painter.drawLine(start, end)

    def _draw_hydraulic_fractures(self, painter, origin, w, h):
        painter.setPen(QPen(QColor("#00a8ff"), 2))
        for base_x, label in [(0.42, "HF-1"), (0.50, "HF-2"), (0.58, "HF-3")]:
            start = origin + QPointF(w * base_x, -h * 0.34)
            end = origin + QPointF(w * (base_x + 0.055), -h * 0.06)
            painter.drawLine(start, end)
            painter.setPen(QPen(QColor("#00d2ff"), 1))
            painter.drawLine(start + QPointF(-12, 20), start + QPointF(14, 44))
            painter.setPen(QPen(QColor("#00a8ff"), 2))
            painter.setFont(QFont("Arial", 8))
            painter.drawText(end + QPointF(5, 4), label)

    def _draw_wells(self, painter, origin, w, h):
        painter.setFont(QFont("Arial", 9, QFont.Bold))
        main_points = [
            origin + QPointF(w * 0.25, -h * 0.05),
            origin + QPointF(w * 0.31, -h * 0.16),
            origin + QPointF(w * 0.35, -h * 0.37),
            origin + QPointF(w * 0.38, -h * 0.56),
        ]
        painter.setPen(QPen(QColor("#e21b1b"), 3))
        painter.drawPolyline(*main_points)
        painter.setPen(QColor("#ffffff"))
        painter.drawText(main_points[-1] + QPointF(5, -3), "MHVW37520")

        for idx, x in enumerate([0.48, 0.57, 0.66], start=1):
            points = [
                origin + QPointF(w * x, -h * 0.05),
                origin + QPointF(w * (x + 0.035), -h * 0.26),
                origin + QPointF(w * (x + 0.02), -h * 0.50),
            ]
            painter.setPen(QPen(QColor("#00a8ff"), 2))
            painter.drawPolyline(*points)
            painter.setPen(QColor("#cdeeff"))
            painter.drawText(points[-1] + QPointF(5, 2), f"W-{idx}")

    def _draw_color_bar(self, painter, style):
        x, y = 18, 56
        colors = style["colors"]
        step = 110 / len(colors)
        for i, color in enumerate(colors):
            painter.fillRect(x, int(y + i * step), 38, int(step) + 1, QColor(color))
        painter.setPen(QColor("#ffffff"))
        painter.setFont(QFont("Microsoft YaHei UI", 8))
        painter.drawText(x, y - 8, f"{style['legend']} ({style['unit']})")
        for index, tick in enumerate(style["ticks"]):
            painter.drawText(x + 46, y + 8 + index * 46, tick)

    def _draw_context(self, painter):
        painter.setPen(QColor("#ffffff"))
        painter.setFont(QFont("Microsoft YaHei UI", 10, QFont.Bold))
        painter.drawText(18, 22, self.context_title)
        painter.setFont(QFont("Microsoft YaHei UI", 9))
        painter.setPen(QColor("#cfd7e6"))
        painter.drawText(18, 40, self.context_detail)

    def _draw_layer_status(self, painter):
        labels = [
            ("网格", "grid"),
            ("加密", "grid_refinement"),
            ("井", "well"),
            ("天然裂缝", "natural_fractures"),
            ("人工裂缝", "hydraulic_fractures"),
            ("双重介质", "dual_porosity"),
        ]
        x = self.width() - 190
        y = 42
        painter.setFont(QFont("Microsoft YaHei UI", 8))
        for index, (text, key) in enumerate(labels):
            enabled = self.layers[key]
            painter.setPen(QColor("#3ccf62") if enabled else QColor("#6a6f7a"))
            painter.drawText(x, y + index * 18, f"{'■' if enabled else '□'} {text}")

    def _draw_axis_glyph(self, painter):
        base = QPointF(self.width() - 84, self.height() - 42)
        painter.setBrush(QColor("#1ed33a"))
        painter.setPen(QPen(QColor("#0d751d"), 1))
        painter.drawPolygon(base, base + QPointF(34, -16), base + QPointF(20, -50))
        painter.setBrush(QColor("#e32424"))
        painter.drawPolygon(
            base + QPointF(30, -2),
            base + QPointF(62, -19),
            base + QPointF(52, -32),
        )


class TwoDViewport(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("twoDViewport")
        self.context_title = "当前结果：二维视图"
        self.context_detail = "二维窗口用于查看井、网格与结果投影。"
        self.display_key = None

    def set_context(self, title, detail, display_key=None):
        self.context_title = title
        self.context_detail = detail
        self.display_key = display_key
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#f6f7fa"))

        w, h = self.width(), self.height()
        map_rect = QRectF(w * 0.12, h * 0.14, w * 0.76, h * 0.70)
        boundary = QPolygonF([
            QPointF(map_rect.left() + map_rect.width() * 0.04, map_rect.top() + map_rect.height() * 0.18),
            QPointF(map_rect.left() + map_rect.width() * 0.84, map_rect.top() + map_rect.height() * 0.04),
            QPointF(map_rect.left() + map_rect.width() * 0.96, map_rect.top() + map_rect.height() * 0.76),
            QPointF(map_rect.left() + map_rect.width() * 0.18, map_rect.top() + map_rect.height() * 0.95),
        ])
        painter.setPen(QPen(QColor("#9aa8ba"), 1.2))
        painter.setBrush(QColor("#eef2f6"))
        painter.drawPolygon(boundary)

        painter.setClipRect(map_rect)
        painter.setPen(QPen(QColor("#d4dbe5"), 1))
        for i in range(1, 18):
            x = map_rect.left() + map_rect.width() * i / 18
            painter.drawLine(QPointF(x, map_rect.top()), QPointF(x - 20, map_rect.bottom()))
        for i in range(1, 13):
            y = map_rect.top() + map_rect.height() * i / 13
            painter.drawLine(QPointF(map_rect.left(), y + 8), QPointF(map_rect.right(), y - 12))
        painter.setClipping(False)

        self._draw_plan_fractures(painter, map_rect)
        self._draw_plan_wells(painter, map_rect)
        self._draw_plan_scale(painter, map_rect)

        painter.setPen(QColor("#20242b"))
        painter.setFont(QFont("Microsoft YaHei UI", 10, QFont.Bold))
        painter.drawText(18, 24, self.context_title)
        painter.setFont(QFont("Microsoft YaHei UI", 9))
        painter.drawText(18, 44, self.context_detail)
        painter.setFont(QFont("Microsoft YaHei UI", 8))
        painter.setPen(QColor("#596273"))
        painter.drawText(QRectF(w - 190, 18, 170, 22), Qt.AlignRight, "图层：井轨迹 / 裂缝 / 网格")
        painter.end()

    def _draw_plan_fractures(self, painter, rect):
        painter.setPen(QPen(QColor("#d8962f"), 1.6))
        for idx, t in enumerate([0.18, 0.28, 0.38, 0.52, 0.67, 0.78]):
            start = QPointF(rect.left() + rect.width() * t, rect.top() + rect.height() * 0.20)
            end = QPointF(rect.left() + rect.width() * (t + 0.12), rect.top() + rect.height() * 0.76)
            painter.drawLine(start, end)
        painter.setPen(QPen(QColor("#16a9d8"), 2))
        for t in [0.46, 0.56, 0.66]:
            x = rect.left() + rect.width() * t
            painter.drawLine(
                QPointF(x, rect.top() + rect.height() * 0.16),
                QPointF(x + rect.width() * 0.04, rect.top() + rect.height() * 0.72),
            )

    def _draw_plan_wells(self, painter, rect):
        wells = [
            ("MHVW37520", QColor("#d32323"), [
                (0.30, 0.80), (0.38, 0.62), (0.43, 0.43), (0.45, 0.24),
            ]),
            ("400A1200", QColor("#126bd6"), [(0.58, 0.18), (0.60, 0.46), (0.56, 0.72)]),
            ("400B1200", QColor("#126bd6"), [(0.70, 0.15), (0.72, 0.45), (0.69, 0.74)]),
        ]
        painter.setFont(QFont("Arial", 9, QFont.Bold))
        for name, color, coords in wells:
            points = [
                QPointF(rect.left() + rect.width() * x, rect.top() + rect.height() * y)
                for x, y in coords
            ]
            painter.setPen(QPen(color, 2.5))
            painter.drawPolyline(*points)
            painter.setBrush(color)
            painter.drawEllipse(points[-1], 4, 4)
            painter.setPen(QColor("#20242b"))
            painter.drawText(points[-1] + QPointF(6, -4), name)

    def _draw_plan_scale(self, painter, rect):
        base = QPointF(rect.left() + 16, rect.bottom() - 20)
        painter.setPen(QPen(QColor("#697386"), 2))
        painter.drawLine(base, base + QPointF(90, 0))
        painter.drawLine(base, base + QPointF(0, -9))
        painter.drawLine(base + QPointF(90, 0), base + QPointF(90, -9))
        painter.setPen(QColor("#697386"))
        painter.setFont(QFont("Microsoft YaHei UI", 8))
        painter.drawText(base + QPointF(24, -12), "750 m")


class ChartViewport(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("chartViewport")
        self.context_title = "当前图表：生产曲线"
        self.context_detail = "图表窗口用于显示模拟结果曲线。"
        self.display_key = "production_curve"
        self.chart_data = {}

    def set_context(self, title, detail, display_key=None):
        self.context_title = title
        self.context_detail = detail
        if display_key:
            self.display_key = display_key
        self.update()

    def set_chart_data(self, chart_key, data):
        if chart_key:
            self.chart_data[chart_key] = dict(data or {})
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#ffffff"))
        painter.setRenderHint(QPainter.Antialiasing)

        style = CHART_STYLES.get(self.display_key, CHART_STYLES["production_curve"])
        data = self.chart_data.get(self.display_key) or {}
        axis = self._axis_info(style, data)
        rect = QRectF(82, 82, max(120, self.width() - 128), max(100, self.height() - 154))

        self._draw_titles(painter, data, style)
        self._draw_chart_frame(painter, rect, axis)

        if data.get("series"):
            self._draw_series_curves(painter, rect, style, data, axis)
        elif data.get("points"):
            self._draw_data_curve(painter, rect, style, data, axis)
        else:
            self._draw_curve(painter, rect, style, axis)

        self._draw_axis_titles(painter, rect, axis)
        painter.end()

    def _draw_titles(self, painter, data, style):
        title = data.get("title") or self.context_title
        detail = self.context_detail
        painter.setPen(QColor("#30343a"))
        painter.setFont(QFont("Microsoft YaHei UI", 10, QFont.Bold))
        painter.drawText(18, 24, title)
        painter.setFont(QFont("Microsoft YaHei UI", 9))
        painter.drawText(18, 44, detail or style["title"])

    def _axis_info(self, style, data):
        if self.display_key == "relative_permeability_curve":
            ticks = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
            return {
                "x_min": 0.0,
                "x_max": 1.0,
                "y_min": 0.0,
                "y_max": 1.0,
                "x_ticks": ticks,
                "y_ticks": ticks,
                "x_label": data.get("x_label", style["x"]),
                "y_label": data.get("y_label", style["y"]),
            }

        points = self._collect_points(data)
        if points:
            xs = [point[0] for point in points]
            ys = [point[1] for point in points]
            x_min, x_max = min(xs), max(xs)
            y_min, y_max = min(ys), max(ys)
        else:
            x_min, x_max = 0.0, 1.0
            y_min, y_max = 0.0, 1.0

        x_min, x_max = self._expand_range(x_min, x_max, 0.04)
        y_min, y_max = self._expand_range(y_min, y_max, 0.08)
        return {
            "x_min": x_min,
            "x_max": x_max,
            "y_min": y_min,
            "y_max": y_max,
            "x_ticks": self._make_ticks(x_min, x_max, 5),
            "y_ticks": self._make_ticks(y_min, y_max, 5),
            "x_label": data.get("x_label", style["x"]),
            "y_label": data.get("y_label", style["y"]),
        }

    def _collect_points(self, data):
        if data.get("series"):
            return [
                point
                for item in data.get("series", [])
                for point in item.get("points", [])
                if len(point) >= 2
            ]
        return [point for point in data.get("points", []) if len(point) >= 2]

    def _expand_range(self, min_value, max_value, ratio):
        if max_value == min_value:
            base = abs(min_value) or 1.0
            return min_value - base * ratio, max_value + base * ratio
        pad = (max_value - min_value) * ratio
        return min_value - pad, max_value + pad

    def _make_ticks(self, min_value, max_value, count):
        if count <= 1:
            return [min_value]
        return [
            min_value + (max_value - min_value) * index / (count - 1)
            for index in range(count)
        ]

    def _draw_chart_frame(self, painter, rect, axis):
        painter.fillRect(rect, QColor("#ffffff"))
        painter.setFont(QFont("Microsoft YaHei UI", 8))

        grid_pen = QPen(QColor("#d2d8e2"), 1)
        axis_pen = QPen(QColor("#7f8794"), 1)
        text_color = QColor("#4a5160")

        painter.setPen(grid_pen)
        for tick in axis["y_ticks"]:
            y = self._map_y(tick, rect, axis)
            painter.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))
        for tick in axis["x_ticks"]:
            x = self._map_x(tick, rect, axis)
            painter.drawLine(QPointF(x, rect.top()), QPointF(x, rect.bottom()))

        painter.setPen(axis_pen)
        painter.drawRect(rect)
        painter.setPen(text_color)
        for tick in axis["y_ticks"]:
            y = self._map_y(tick, rect, axis)
            painter.drawText(
                QRectF(12, y - 9, rect.left() - 20, 18),
                Qt.AlignRight | Qt.AlignVCenter,
                self._format_tick(tick),
            )
        for tick in axis["x_ticks"]:
            x = self._map_x(tick, rect, axis)
            painter.drawText(
                QRectF(x - 28, rect.bottom() + 6, 56, 18),
                Qt.AlignHCenter | Qt.AlignTop,
                self._format_tick(tick),
            )

    def _draw_axis_titles(self, painter, rect, axis):
        painter.setPen(QColor("#30343a"))
        painter.setFont(QFont("Microsoft YaHei UI", 9))
        painter.drawText(
            QRectF(rect.left(), self.height() - 36, rect.width(), 24),
            Qt.AlignHCenter | Qt.AlignVCenter,
            axis["x_label"],
        )

        painter.save()
        painter.translate(18, rect.center().y())
        painter.rotate(-90)
        painter.drawText(
            QRectF(-rect.height() / 2, 0, rect.height(), 24),
            Qt.AlignHCenter | Qt.AlignVCenter,
            axis["y_label"],
        )
        painter.restore()

    def _draw_series_curves(self, painter, rect, style, data, axis):
        series = data.get("series", [])
        legend_items = []

        for index, item in enumerate(series):
            color = QColor(item.get("color", style["color"]))
            mapped = []
            points = item.get("points", [])
            step = max(1, len(points) // 700)
            for x_value, y_value in points[::step]:
                mapped.append(
                    QPointF(
                        self._map_x(x_value, rect, axis),
                        self._map_y(y_value, rect, axis),
                    )
                )
            if len(mapped) >= 2:
                painter.setPen(QPen(color, 2))
                painter.drawPolyline(*mapped)
            for point in mapped[:: max(1, len(mapped) // 24)]:
                painter.setPen(QPen(color, 1))
                painter.setBrush(color)
                painter.drawEllipse(point, 2.2, 2.2)
            legend_items.append((item.get("name", f"series {index + 1}"), color))

        self._draw_legend(painter, rect, legend_items)
        if "so_fixed" in data:
            painter.setPen(QColor("#5d6675"))
            painter.setFont(QFont("Microsoft YaHei UI", 8))
            painter.drawText(
                int(rect.left() + 148),
                int(rect.top() + 25),
                f"So_fixed={data['so_fixed']:.4f}",
            )

    def _draw_legend(self, painter, rect, legend_items):
        if not legend_items:
            return
        width = 132
        height = 22 + len(legend_items) * 18
        box = QRectF(rect.left() + 10, rect.top() + 10, width, height)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#ffffff"))
        painter.drawRect(box)
        painter.setPen(QPen(QColor("#c8ced8"), 1))
        painter.drawRect(box)
        painter.setFont(QFont("Microsoft YaHei UI", 8))
        for index, (name, color) in enumerate(legend_items):
            y = box.top() + 20 + index * 18
            painter.setPen(QPen(color, 2))
            painter.drawLine(QPointF(box.left() + 10, y - 4), QPointF(box.left() + 34, y - 4))
            painter.setPen(QColor("#30343a"))
            painter.drawText(int(box.left() + 42), int(y), name)

    def _draw_data_curve(self, painter, rect, style, data, axis):
        points = data.get("points", [])
        if len(points) < 2:
            return
        mapped = []
        step = max(1, len(points) // 700)
        for x_value, y_value in points[::step]:
            mapped.append(
                QPointF(self._map_x(x_value, rect, axis), self._map_y(y_value, rect, axis))
            )
        painter.setPen(QPen(style["color"], 2))
        painter.drawPolyline(*mapped)
        painter.setPen(QColor("#5d6675"))
        painter.setFont(QFont("Microsoft YaHei UI", 8))
        painter.drawText(
            int(rect.left() + 10),
            int(rect.top() + 24),
            f"{data.get('y_field', 'Y')} / {data.get('x_field', 'X')}  点数: {len(points)}",
        )

    def _draw_curve(self, painter, rect, style, axis):
        if self.display_key == "relative_permeability_curve":
            curves = [
                ("krw", QColor("#13a85a"), lambda t: t ** 1.8),
                ("kro", QColor("#d45500"), lambda t: (1 - t) ** 1.6),
            ]
        elif self.display_key == "production_curve":
            curves = [
                ("日产油", QColor("#1f66c2"), lambda t: 0.82 * math.exp(-2.2 * t) + 0.10),
                ("日产水", QColor("#00a6d6"), lambda t: 0.10 + 0.70 * (t ** 1.35)),
                ("日产气", QColor("#db8b1f"), lambda t: 0.32 + 0.20 * math.sin(t * math.pi * 1.3)),
            ]
        elif self.display_key == "blasingame_curve":
            curves = [
                ("规整化流量", QColor("#d45500"), lambda t: 0.82 - 0.46 * math.log10(1 + 9 * t)),
                ("积分函数", QColor("#7b4bc4"), lambda t: 0.74 - 0.34 * math.sqrt(t)),
            ]
        elif self.display_key == "pvt_curve":
            curves = [
                ("Z 因子", QColor("#7b4bc4"), lambda t: 0.28 + 0.50 * (1 - math.exp(-2.4 * t))),
            ]
        else:
            curves = [
                (style["title"], style["color"], lambda t: 0.08 + 0.78 * (1 - 0.86 ** (t * 24))),
            ]

        legend_items = []
        for name, color, formula in curves:
            painter.setPen(QPen(color, 2))
            points = []
            for i in range(70):
                t = i / 69
                x_value = axis["x_min"] + (axis["x_max"] - axis["x_min"]) * t
                y_norm = max(0.04, min(0.96, formula(t)))
                y_value = axis["y_min"] + (axis["y_max"] - axis["y_min"]) * y_norm
                points.append(QPointF(self._map_x(x_value, rect, axis), self._map_y(y_value, rect, axis)))
            painter.drawPolyline(*points)
            legend_items.append((name, color))
        self._draw_legend(painter, rect, legend_items)

    def _map_x(self, value, rect, axis):
        span = axis["x_max"] - axis["x_min"] or 1.0
        return rect.left() + rect.width() * ((value - axis["x_min"]) / span)

    def _map_y(self, value, rect, axis):
        span = axis["y_max"] - axis["y_min"] or 1.0
        return rect.bottom() - rect.height() * ((value - axis["y_min"]) / span)

    def _format_tick(self, value):
        if abs(value) >= 1000:
            return f"{value:.0f}"
        if abs(value) >= 10:
            return f"{value:.1f}"
        return f"{value:.2f}".rstrip("0").rstrip(".")


class ViewPage(QFrame):
    new_window_requested = pyqtSignal()
    clone_window_requested = pyqtSignal()
    close_window_requested = pyqtSignal()

    def __init__(self, viewport, view_type="3d", parent=None):
        super().__init__(parent)
        self.viewport = viewport
        self.view_type = view_type
        self.setObjectName("viewPage")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.toolbar = ViewToolbar(view_type)
        self.toolbar.new_window_requested.connect(self.new_window_requested)
        self.toolbar.clone_window_requested.connect(self.clone_window_requested)
        self.toolbar.close_window_requested.connect(self.close_window_requested)
        layout.addWidget(self.toolbar)
        layout.addWidget(viewport, 1)

    def set_context(self, title, detail, display_key=None):
        if hasattr(self.viewport, "set_context"):
            self.viewport.set_context(title, detail, display_key)

    def set_layer_state(self, layer_key, enabled):
        if hasattr(self.viewport, "set_layer_state"):
            self.viewport.set_layer_state(layer_key, enabled)

    def set_simulation_data(self, sim_data):
        if hasattr(self.viewport, "set_simulation_data"):
            self.viewport.set_simulation_data(sim_data)

    def set_chart_data(self, chart_key, data):
        if hasattr(self.viewport, "set_chart_data"):
            self.viewport.set_chart_data(chart_key, data)
