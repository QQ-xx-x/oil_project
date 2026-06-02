# -*- coding: utf-8 -*-
"""Placeholder 2D/3D/chart viewports for the project-state shell."""

import math

from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import QColor, QFont, QPainter, QPen
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
        self.context_title = "当前结果：三维视图"
        self.context_detail = "在结果树中选择结果或图层后，这里显示对应占位视图。"
        self.display_key = "permeability_field"
        self.layers = {
            "grid": True,
            "well": True,
            "natural_fractures": True,
            "hydraulic_fractures": True,
            "dual_porosity": False,
            "grid_refinement": False,
        }

    def set_context(self, title, detail, display_key=None):
        self.context_title = title
        self.context_detail = detail
        if display_key:
            self.display_key = display_key
        self.update()

    def set_layer_state(self, layer_key, enabled):
        if layer_key in self.layers:
            self.layers[layer_key] = bool(enabled)
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#050505"))

        style = RESULT_STYLES.get(self.display_key, RESULT_STYLES["permeability_field"])
        w, h = self.width(), self.height()
        origin = QPointF(w * 0.18, h * 0.72)
        x_vec = QPointF(w * 0.58, -h * 0.19)
        y_vec = QPointF(w * 0.22, h * 0.18)

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
            painter.setPen(QPen(QColor("#f0a000"), 2))
            painter.drawLine(
                origin + QPointF(w * 0.06, h * 0.10),
                origin + QPointF(w * 0.56, -h * 0.10),
            )

        if self.layers["hydraulic_fractures"]:
            painter.setPen(QPen(QColor("#00a8ff"), 2))
            painter.drawLine(
                origin + QPointF(w * 0.42, -h * 0.32),
                origin + QPointF(w * 0.49, -h * 0.05),
            )
            painter.drawLine(
                origin + QPointF(w * 0.51, -h * 0.38),
                origin + QPointF(w * 0.58, -h * 0.10),
            )

        if self.layers["well"]:
            painter.setPen(QPen(QColor("#e21b1b"), 3))
            painter.drawPolyline(
                origin + QPointF(w * 0.25, -h * 0.05),
                origin + QPointF(w * 0.31, -h * 0.16),
                origin + QPointF(w * 0.35, -h * 0.37),
                origin + QPointF(w * 0.38, -h * 0.56),
            )

        self._draw_color_bar(painter, style)
        self._draw_context(painter)
        self._draw_layer_status(painter)
        self._draw_axis_glyph(painter)
        painter.end()

    def _draw_result_surface(self, painter, origin, x_vec, y_vec, style):
        surface_color = style["surface"]
        painter.setPen(QPen(surface_color, 1))
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
        painter.fillRect(self.rect(), QColor("#f6f7fa"))
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        painter.setPen(QPen(QColor("#1c4fff"), 1))
        for x in [0.36, 0.50, 0.64]:
            x0 = w * x
            painter.drawLine(QPointF(x0, h * 0.20), QPointF(x0, h * 0.78))
            for i in range(38):
                yy = h * (0.24 + i * 0.012)
                painter.drawLine(
                    QPointF(x0 - 42, yy),
                    QPointF(x0 + 42, yy + (i % 5 - 2) * 3),
                )
        painter.setPen(QPen(QColor("#b11d1d"), 3))
        painter.drawPolyline(
            QPointF(w * 0.48, h * 0.78),
            QPointF(w * 0.48, h * 0.62),
            QPointF(w * 0.47, h * 0.50),
            QPointF(w * 0.46, h * 0.44),
        )
        painter.setPen(QColor("#20242b"))
        painter.setFont(QFont("Microsoft YaHei UI", 10, QFont.Bold))
        painter.drawText(18, 24, self.context_title)
        painter.setFont(QFont("Microsoft YaHei UI", 9))
        painter.drawText(18, 44, self.context_detail)
        painter.setFont(QFont("Arial", 11))
        painter.drawText(QPointF(w * 0.47, h * 0.43), "H01")
        painter.end()


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
        painter.setPen(QPen(style["color"], 2))
        points = []
        for i in range(50):
            t = i / 49
            x_value = axis["x_min"] + (axis["x_max"] - axis["x_min"]) * t
            if self.display_key == "relative_permeability_curve":
                y_norm = t ** 1.8
            elif self.display_key == "blasingame_curve":
                y_norm = 0.75 - 0.42 * math.log10(1 + 9 * t)
            else:
                y_norm = 0.08 + 0.78 * (1 - 0.86 ** (i / 2))
            y_value = axis["y_min"] + (axis["y_max"] - axis["y_min"]) * max(0.04, min(0.96, y_norm))
            points.append(QPointF(self._map_x(x_value, rect, axis), self._map_y(y_value, rect, axis)))
        painter.drawPolyline(*points)
        if self.display_key == "relative_permeability_curve":
            painter.setPen(QPen(QColor("#d45500"), 2))
            oil_points = []
            for i in range(50):
                t = i / 49
                x_value = axis["x_min"] + (axis["x_max"] - axis["x_min"]) * t
                y_value = axis["y_min"] + (axis["y_max"] - axis["y_min"]) * ((1 - t) ** 1.6)
                oil_points.append(
                    QPointF(self._map_x(x_value, rect, axis), self._map_y(y_value, rect, axis))
                )
            painter.drawPolyline(*oil_points)

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
    def __init__(self, viewport, parent=None):
        super().__init__(parent)
        self.viewport = viewport
        self.setObjectName("viewPage")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(ViewToolbar())
        layout.addWidget(viewport, 1)

    def set_context(self, title, detail, display_key=None):
        if hasattr(self.viewport, "set_context"):
            self.viewport.set_context(title, detail, display_key)

    def set_layer_state(self, layer_key, enabled):
        if hasattr(self.viewport, "set_layer_state"):
            self.viewport.set_layer_state(layer_key, enabled)

    def set_chart_data(self, chart_key, data):
        if hasattr(self.viewport, "set_chart_data"):
            self.viewport.set_chart_data(chart_key, data)
