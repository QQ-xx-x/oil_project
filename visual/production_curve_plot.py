import csv
import os
import math

from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QPointF
from PyQt5.QtGui import QColor, QPainter, QPen

import pyqtgraph as pg


class _LegendLineSample(QWidget):
    """
    底部图例中的真实线型示例控件。

    不使用字符“━━━━”“----”模拟线型，
    直接使用 QPainter 按曲线的真实颜色、宽度和 Qt 线型绘制。
    """

    def __init__(
        self,
        color,
        line_width,
        qt_line_style,
        parent=None,
    ):
        super().__init__(parent)

        self._color = QColor(*color)
        self._line_width = float(line_width)
        self._qt_line_style = qt_line_style

        # 宽度稍大，保证点划线、双点划线也能看清。
        self.setFixedSize(54, 18)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        pen = QPen(self._color)

        # 图例线宽至少为 1，避免很细时看不见。
        pen.setWidthF(max(1.0, self._line_width))
        pen.setStyle(self._qt_line_style)
        pen.setCosmetic(True)

        painter.setPen(pen)

        y = self.height() / 2.0

        painter.drawLine(
            QPointF(3.0, y),
            QPointF(self.width() - 3.0, y),
        )

        painter.end()


class ProductionCurvePlotWidget(QWidget):
    """
    Production curve line chart widget.

    功能：
    1. 从 output_sim_lgr_noWR.csv 读取生产动态数据
    2. 时间列：Time
    3. 曲线字段：CumWater / CumGas / Qw / Qg
    4. 支持中文属性名显示
    5. 支持固定属性颜色
    6. 支持外部修改曲线颜色、粗细和线型
    7. 鼠标悬停在真实数据点上时显示时间和该点的值
    8. 支持表格点击某一行后，高亮线图对应时间点
    9. 支持点击线图真实数据点后，向外发送 point_selected(row_index)，用于表格自动跳转
    10. 支持用户选择时间范围，只绘制该时间范围内的曲线
    11. 支持导出当前线图图片
    """

    point_selected = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.data = None
        self.curve_items = {}
        self.curve_data = {}
        self.current_property_names = []

        # =========================
        # 英文 key -> 中文显示名
        # =========================
        self.property_display_names = {
            "CumOil": "累积产油量",
            "CumWater": "累积产水量",
            "CumGas": "累积产气",
            "Qo": "产油速率",
            "Qw": "产水速率",
            "Qg": "产气速率",
            "BHP": "井底流压",
            "AvgPressure": "平均压力",
        }

        # 中文显示名 -> 英文 key
        self.display_name_to_key = {
            display_name: key
            for key, display_name in self.property_display_names.items()
        }

        # 控制属性显示顺序
        self.property_order = [
            "CumOil",
            "CumWater",
            "CumGas",
            "Qo",
            "Qw",
            "Qg",
            "BHP",
            "AvgPressure",
        ]

        # =========================
        # 默认固定颜色
        # =========================
        self.default_property_colors = {
            "CumOil": (30, 120, 60),
            "CumWater": (0, 0, 255),
            "CumGas": (180, 0, 255),
            "Qo": (60, 160, 80),
            "Qw": (0, 120, 255),
            "Qg": (160, 0, 200),
            "BHP": (210, 80, 30),
            "AvgPressure": (220, 140, 40),
        }

        self.property_colors = dict(self.default_property_colors)

        # =========================
        # 默认线宽
        # =========================
        self.default_line_width = 1.2

        self.property_line_widths = {
            key: self.default_line_width
            for key in self.property_order
        }

        # =========================
        # 默认线型
        # =========================
        self.default_line_style = "solid"

        self.property_line_styles = {
            key: self.default_line_style
            for key in self.property_order
        }

        # 内部线型 key -> Qt 线型
        self.line_style_map = {
            "solid": Qt.SolidLine,
            "dash": Qt.DashLine,
            "dot": Qt.DotLine,
            "dashdot": Qt.DashDotLine,
            "dashdotdot": Qt.DashDotDotLine,
        }

        self.line_style_display_names = {
            "solid": "实线",
            "dash": "虚线",
            "dot": "点线",
            "dashdot": "点划线",
            "dashdotdot": "双点划线",
        }

        # 当前视图范围
        self.current_view_x_range = None
        self.current_view_y_range = None

        # Y 轴上下预留比例
        self.view_y_padding_ratio = 0.05

        # 悬停提示
        self.hover_text = None
        self.hover_point = None
        self.mouse_move_proxy = None

        self.hover_delay_ms = 150
        self.pending_hover_scene_pos = None

        self.hover_delay_timer = QTimer(self)
        self.hover_delay_timer.setSingleShot(True)
        self.hover_delay_timer.timeout.connect(
            self._show_delayed_hover
        )

        # 单击与双击区分
        self.mouse_click_proxy = None
        self.single_click_delay_ms = 220
        self.pending_single_click_scene_pos = None

        self.single_click_timer = QTimer(self)
        self.single_click_timer.setSingleShot(True)
        self.single_click_timer.timeout.connect(
            self._handle_pending_single_click
        )

        # 表格点击产生的红色竖直虚线
        self.selected_time_index = None
        self.selected_time_line = None

        # 双击探针
        self.probe_active = False
        self.probe_time_index = None
        self.probe_vertical_line = None
        self.probe_horizontal_line = None
        self.probe_points = None
        self.probe_text = None

        # 时间范围
        self.time_range_start_index = None
        self.time_range_end_index = None

        self.init_ui()

    # =========================================================
    # UI
    # =========================================================
    def init_ui(self):
        pg.setConfigOptions(antialias=True)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setMenuEnabled(False)

        self.plot_widget.setBackground("w")
        self.plot_widget.showGrid(
            x=True,
            y=True,
            alpha=0.25,
        )

        self.plot_widget.setTitle("")
        self.plot_widget.setLabel("bottom", "时间")
        self.plot_widget.setLabel("left", "数值")

        # 坐标轴自身不绘制边框，
        # 统一由 ViewBox 绘制一圈黑色边框。
        for axis_name in ["bottom", "left", "top", "right"]:
            axis = self.plot_widget.getAxis(axis_name)

            axis.setPen(
                pg.mkPen(
                    color=(0, 0, 0, 0),
                    width=0,
                )
            )

            axis.setTextPen(
                pg.mkPen(
                    color=(60, 60, 60),
                )
            )

        border_pen = pg.mkPen(
            color=(0, 0, 0),
            width=1,
        )
        border_pen.setCosmetic(True)

        self.plot_widget.getViewBox().setBorder(border_pen)

        root_layout.addWidget(self.plot_widget, 1)

        self._create_hover_items()
        self._create_table_marker_items()
        self._create_probe_items()

        self.mouse_move_proxy = pg.SignalProxy(
            self.plot_widget.scene().sigMouseMoved,
            rateLimit=60,
            slot=self._on_mouse_moved,
        )

        self.mouse_click_proxy = pg.SignalProxy(
            self.plot_widget.scene().sigMouseClicked,
            rateLimit=60,
            slot=self._on_mouse_clicked,
        )

        # =========================
        # Bottom centered legend
        # =========================
        self.legend_widget = QWidget()

        self.legend_layout = QHBoxLayout(self.legend_widget)
        self.legend_layout.setContentsMargins(10, 6, 10, 6)
        self.legend_layout.setSpacing(18)

        self.legend_layout.addStretch()
        self.legend_layout.addStretch()

        root_layout.addWidget(self.legend_widget)

    # =========================================================
    # 图表交互对象
    # =========================================================
    def _create_hover_items(self):
        """
        创建悬停点和悬停提示框。
        """

        self.hover_point = pg.ScatterPlotItem(
            size=9,
            brush=pg.mkBrush(255, 255, 255),
            pen=pg.mkPen(
                color=(0, 0, 0),
                width=1,
            ),
        )

        self.plot_widget.addItem(
            self.hover_point,
            ignoreBounds=True,
        )

        self.hover_point.setZValue(5000)
        self.hover_point.hide()

        # 使用 QLabel 而不是 TextItem，
        # 可按像素坐标定位，避免文字框超出图表边缘。
        self.hover_text = QLabel(self.plot_widget)
        self.hover_text.setTextFormat(Qt.RichText)
        self.hover_text.setFrameShape(QFrame.Box)

        self.hover_text.setStyleSheet("""
            QLabel {
                background-color: rgb(255, 255, 230);
                border: 1px solid rgb(100, 100, 100);
                color: black;
                padding: 4px;
                font-size: 16px;
            }
        """)

        self.hover_text.hide()

    def _create_table_marker_items(self):
        """
        创建表格联动时的红色竖直虚线。
        """

        pen = pg.mkPen(
            color=(255, 0, 0),
            width=1,
            style=Qt.DashLine,
        )
        pen.setCosmetic(True)

        self.selected_time_line = pg.InfiniteLine(
            angle=90,
            movable=False,
            pen=pen,
        )

        self.plot_widget.addItem(
            self.selected_time_line,
            ignoreBounds=True,
        )

        self.selected_time_line.setZValue(3000)
        self.selected_time_line.hide()

    def _create_probe_items(self):
        """
        创建双击探针对象：
        灰色十字线、点位、数值框。
        """

        probe_pen = pg.mkPen(
            color=(125, 125, 125),
            width=0.9,
            style=Qt.DashLine,
        )

        self.probe_vertical_line = pg.InfiniteLine(
            angle=90,
            movable=False,
            pen=probe_pen,
        )

        self.plot_widget.addItem(
            self.probe_vertical_line,
            ignoreBounds=True,
        )

        self.probe_vertical_line.setZValue(700)
        self.probe_vertical_line.hide()

        self.probe_horizontal_line = pg.InfiniteLine(
            angle=0,
            movable=False,
            pen=probe_pen,
        )

        self.plot_widget.addItem(
            self.probe_horizontal_line,
            ignoreBounds=True,
        )

        self.probe_horizontal_line.setZValue(700)
        self.probe_horizontal_line.hide()

        self.probe_points = pg.ScatterPlotItem(
            size=7,
            brush=pg.mkBrush(255, 255, 255),
            pen=pg.mkPen(
                color=(100, 100, 100),
                width=0.9,
            ),
        )

        self.plot_widget.addItem(
            self.probe_points,
            ignoreBounds=True,
        )

        self.probe_points.setZValue(701)
        self.probe_points.hide()

        self.probe_text = pg.TextItem(
            text="",
            color=(0, 0, 0),
            anchor=(0, 1),
            fill=(255, 252, 240, 240),
            border=pg.mkPen(
                color=(120, 120, 120),
                width=0.9,
            ),
        )

        self.plot_widget.addItem(
            self.probe_text,
            ignoreBounds=True,
        )

        self.probe_text.setZValue(702)
        self.probe_text.hide()

    # =========================================================
    # 数据读取
    # =========================================================
    def set_data(self, data):
        """
        设置生产动态数据。
        """
        self.data = data

    def load_data_from_csv(self, csv_path, time_column="Time"):
        """
        从 output_sim_lgr_noWR.csv 加载生产动态曲线数据。

        读取字段：
            Time
            CumWater
            CumGas
            Qw
            Qg
        """

        if not csv_path:
            print("CSV path is empty.")
            return False

        if not os.path.exists(csv_path):
            print(f"CSV file not found: {csv_path}")
            return False

        try:
            with open(
                csv_path,
                "r",
                encoding="utf-8-sig",
                newline="",
            ) as f:
                reader = csv.DictReader(f)

                if reader.fieldnames is None:
                    print("CSV file has no header.")
                    return False

                fieldnames = [
                    name.strip()
                    for name in reader.fieldnames
                ]

                if time_column not in fieldnames:
                    print(
                        f"Time column '{time_column}' "
                        f"not found in CSV."
                    )
                    print("Available columns:", fieldnames)
                    return False

                data = {
                    "date": []
                }

                required_fields = [
                    field
                    for field in self.property_order
                    if field in fieldnames
                ]

                if not required_fields:
                    required_fields = self._detect_numeric_fields(
                        csv_path,
                        fieldnames,
                        exclude={time_column},
                    )

                for field in required_fields:
                    if field in fieldnames:
                        data[field] = []
                    else:
                        print(
                            f"Warning: field '{field}' "
                            f"not found in CSV."
                        )

                row_count = 0
                invalid_count = 0

                for row in reader:
                    row_count += 1

                    time_value = row.get(time_column, "")
                    data["date"].append(str(time_value))

                    for field in required_fields:
                        if field not in data:
                            continue

                        raw_value = row.get(field, "")

                        try:
                            value = float(raw_value)

                            if not math.isfinite(value):
                                value = None
                                invalid_count += 1

                        except Exception:
                            value = None
                            invalid_count += 1

                        data[field].append(value)

                self.set_data(data)

                print(f"CSV loaded successfully: {csv_path}")
                print(f"CSV row count: {row_count}")
                print(f"Invalid value count: {invalid_count}")
                print(
                    "Available properties:",
                    self.get_available_properties(),
                )

                return True

        except Exception as exc:
            print(f"load_data_from_csv error: {exc}")
            return False

    def _detect_numeric_fields(
        self,
        csv_path,
        fieldnames,
        exclude=None,
    ):
        """
        自动识别 CSV 中的数值型字段。
        """

        exclude = set(exclude or [])
        detected = []

        try:
            with open(
                csv_path,
                "r",
                encoding="utf-8-sig",
                newline="",
            ) as f:
                reader = csv.DictReader(f)
                sample_rows = []

                for index, row in enumerate(reader):
                    sample_rows.append(row)

                    if index >= 19:
                        break

        except Exception:
            return detected

        for field in fieldnames:
            if field in exclude:
                continue

            for row in sample_rows:
                raw_value = row.get(field, "")

                try:
                    value = float(raw_value)
                except Exception:
                    continue

                if math.isfinite(value):
                    detected.append(field)
                    break

        return detected

    def get_available_property_keys(self):
        """
        获取当前数据中可绘制的英文字段 key。
        """

        if not self.data:
            return []

        ordered = [
            key
            for key in self.property_order
            if key in self.data and key != "date"
        ]

        extra = [
            key
            for key in self.data.keys()
            if key not in ordered and key != "date"
        ]

        return ordered + extra

    def get_available_properties(self):
        """
        获取当前可绘制属性，返回中文显示名。
        """

        if not self.data:
            return []

        return [
            self.property_display_names.get(key, key)
            for key in self.get_available_property_keys()
        ]

    def get_time_labels(self):
        """
        获取当前数据中的时间标签列表。
        """

        if self.data is None:
            return []

        if "date" not in self.data:
            return []

        return [
            str(value)
            for value in self.data["date"]
        ]

    # =========================================================
    # 时间范围
    # =========================================================
    def set_time_range_by_index(self, start_index, end_index):
        """
        设置线图显示的时间范围。
        """

        if not self.data or "date" not in self.data:
            return

        total_count = len(self.data["date"])

        if total_count == 0:
            return

        try:
            start_index = int(start_index)
            end_index = int(end_index)
        except Exception:
            print("Invalid time range index.")
            return

        start_index = max(
            0,
            min(total_count - 1, start_index),
        )

        end_index = max(
            0,
            min(total_count - 1, end_index),
        )

        if start_index > end_index:
            start_index, end_index = end_index, start_index

        self.time_range_start_index = start_index
        self.time_range_end_index = end_index

        self.clear_table_marker()
        self._clear_probe_and_hover()
        self._refresh_current_plot()

    def clear_time_range(self):
        """
        清除时间范围限制，恢复显示全部时间。
        """

        self.time_range_start_index = None
        self.time_range_end_index = None

        self.clear_table_marker()
        self._clear_probe_and_hover()
        self._refresh_current_plot()

    def _get_active_row_indices(self):
        """
        获取当前应该绘制的数据行索引。
        """

        if self.data is None or "date" not in self.data:
            return []

        n = len(self.data["date"])

        if n == 0:
            return []

        if (
            self.time_range_start_index is None
            or self.time_range_end_index is None
        ):
            return list(range(n))

        start_index = max(
            0,
            min(n - 1, int(self.time_range_start_index)),
        )

        end_index = max(
            0,
            min(n - 1, int(self.time_range_end_index)),
        )

        if start_index > end_index:
            start_index, end_index = end_index, start_index

        return list(range(start_index, end_index + 1))

    # =========================================================
    # 绘图
    # =========================================================
    def clear_plot(self):
        """
        清空曲线、图例和临时交互对象。
        """

        old_selected_index = self.selected_time_index

        self.hover_delay_timer.stop()
        self.single_click_timer.stop()

        self.pending_hover_scene_pos = None
        self.pending_single_click_scene_pos = None

        self._hide_hover_items()

        if self.hover_text is not None:
            self.hover_text.deleteLater()
            self.hover_text = None

        self.plot_widget.clear()

        self.curve_items = {}
        self.curve_data = {}
        self.current_property_names = []

        self.selected_time_index = old_selected_index

        self.probe_time_index = None
        self.probe_active = False

        self.current_view_x_range = None
        self.current_view_y_range = None

        self._create_hover_items()
        self._create_table_marker_items()
        self._create_probe_items()

        while self.legend_layout.count():
            item = self.legend_layout.takeAt(0)
            widget = item.widget()

            if widget is not None:
                widget.deleteLater()

        self.legend_layout.addStretch()
        self.legend_layout.addStretch()

    def plot_selected_properties(self, property_names):
        """
        绘制选中的属性。
        property_names 可以传中文，也可以传英文。
        """

        if self.data is None:
            print("No data. Cannot plot curves.")
            return

        if "date" not in self.data:
            print("Data does not contain 'date'.")
            return

        old_selected_index = self.selected_time_index

        self.clear_plot()

        dates = self.data["date"]
        active_row_indices = self._get_active_row_indices()

        if not active_row_indices:
            print("No data in selected time range.")
            return

        self._update_date_axis(
            dates,
            active_row_indices,
        )

        for index, property_name in enumerate(property_names):
            key = self._normalize_property_name(property_name)

            if key not in self.data:
                print(
                    f"Property not found in data: "
                    f"{property_name}"
                )
                continue

            raw_y = self.data[key]

            if len(raw_y) != len(dates):
                print(
                    f"Data length mismatch: "
                    f"{property_name}"
                )
                continue

            x = []
            y = []

            for i in active_row_indices:
                if i < 0 or i >= len(raw_y):
                    continue

                value = raw_y[i]

                if value is None:
                    continue

                try:
                    value = float(value)
                except Exception:
                    continue

                if not math.isfinite(value):
                    continue

                x.append(i)
                y.append(value)

            if not x or not y:
                print(
                    f"No valid data to plot: "
                    f"{property_name}"
                )
                continue

            display_name = self._get_display_name(key)

            color = self._get_property_color(
                key,
                fallback_index=index,
            )

            is_history = self._is_history_property(
                display_name
            )

            pen = self._make_curve_pen(
                property_key=key,
                color=color,
                is_history=is_history,
            )

            curve_item = self.plot_widget.plot(
                x,
                y,
                pen=pen,
            )

            self.curve_items[key] = curve_item
            self.current_property_names.append(key)

            self.curve_data[key] = {
                "x": x,
                "y": y,
                "color": color,
                "display_name": display_name,
            }

            # 这里传入 key，图例会读取该属性当前的真实线型和线宽。
            self._add_bottom_legend_item(
                property_key=key,
                display_name=display_name,
                color=color,
                is_history=is_history,
            )

        self._fit_view_to_current_data_range()

        if (
            old_selected_index is not None
            and old_selected_index
            in self._get_active_row_indices()
        ):
            self.show_table_marker(old_selected_index)
        else:
            self.clear_table_marker()

    def plot_one_property(self, property_name):
        """
        只绘制一个属性。
        """

        self.plot_selected_properties([property_name])

    def set_chart_title(self, title):
        """
        设置图表标题。
        """

        self.plot_widget.setTitle(
            title,
            color="#222222",
            size="10pt",
        )

    def set_y_axis_title(self, title):
        """
        设置 Y 轴标题。
        """

        self.plot_widget.setLabel("left", title)

    def reset_view(self):
        """
        重置为当前数据范围。
        """

        self._fit_view_to_current_data_range()

        if self.selected_time_index is not None:
            self.show_table_marker(
                self.selected_time_index
            )

    def _fit_view_to_current_data_range(self):
        """
        根据当前正在绘制的曲线，固定 X/Y 显示范围。

        X 轴严格使用当前数据范围；
        Y 轴上下保留一定比例的空白；
        防止缩放或拖动后显示到无意义的空区域。
        """

        if not self.curve_data:
            return

        all_x = []
        all_y = []

        for curve_info in self.curve_data.values():
            all_x.extend(curve_info.get("x", []))
            all_y.extend(curve_info.get("y", []))

        if not all_x or not all_y:
            return

        try:
            x_min = float(min(all_x))
            x_max = float(max(all_x))
            y_min = float(min(all_y))
            y_max = float(max(all_y))
        except Exception:
            return

        if not (
            math.isfinite(x_min)
            and math.isfinite(x_max)
            and math.isfinite(y_min)
            and math.isfinite(y_max)
        ):
            return

        # 防止只有一个 X 值时范围为 0。
        if abs(x_max - x_min) < 1e-12:
            x_min -= 0.5
            x_max += 0.5

        # 防止只有一个 Y 值时范围为 0。
        if abs(y_max - y_min) < 1e-12:
            base = max(abs(y_max), 1.0)

            y_min -= base * 0.05
            y_max += base * 0.05

        else:
            y_padding = (
                y_max - y_min
            ) * self.view_y_padding_ratio

            y_min -= y_padding
            y_max += y_padding

        self.current_view_x_range = (x_min, x_max)
        self.current_view_y_range = (y_min, y_max)

        view_box = self.plot_widget.getViewBox()

        # 先清除旧范围限制。
        view_box.setLimits(
            xMin=None,
            xMax=None,
            yMin=None,
            yMax=None,
        )

        # 设置当前显示范围。
        view_box.setRange(
            xRange=self.current_view_x_range,
            yRange=self.current_view_y_range,
            padding=0.0,
        )

        # 再限制缩放和平移不可超出数据范围。
        view_box.setLimits(
            xMin=x_min,
            xMax=x_max,
            yMin=y_min,
            yMax=y_max,
        )

        view_box.disableAutoRange()

    # =========================================================
    # 表格联动
    # =========================================================
    def highlight_time_index(self, row_index):
        """
        表格点击某行时调用。
        显示红色竖直虚线。
        """

        try:
            row_index = int(row_index)
        except Exception:
            self.clear_table_marker()
            return

        if row_index < 0:
            self.clear_table_marker()
            return

        self.show_table_marker(row_index)

    def show_table_marker(self, row_index):
        """
        显示指定时间点的红色竖直虚线。
        """

        self.hover_delay_timer.stop()
        self.pending_hover_scene_pos = None
        self._hide_hover_items()

        try:
            row_index = int(row_index)
        except Exception:
            return

        if not self.data or "date" not in self.data:
            return

        if row_index < 0:
            return

        if row_index >= len(self.data["date"]):
            return

        if row_index not in self._get_active_row_indices():
            return

        self.selected_time_index = row_index

        if self.selected_time_line is not None:
            self.selected_time_line.setValue(row_index)
            self.selected_time_line.show()

        self._render_plot()

    def clear_table_marker(self):
        """
        清除表格联动产生的红色竖线。
        """

        self.selected_time_index = None

        if self.selected_time_line is not None:
            self.selected_time_line.hide()

        self._render_plot()

    # =========================================================
    # 双击探针
    # =========================================================
    def _clear_probe_and_hover(self):
        """
        清除探针、悬停和延迟点击状态。
        """

        self.hover_delay_timer.stop()
        self.single_click_timer.stop()

        self.pending_hover_scene_pos = None
        self.pending_single_click_scene_pos = None

        self.probe_time_index = None
        self.probe_active = False

        self._hide_hover_items()
        self._hide_probe_items()

    def _activate_probe(self, scene_pos):
        """
        激活双击探针。
        """

        self.hover_delay_timer.stop()
        self.pending_hover_scene_pos = None

        self._hide_hover_items()

        self.probe_active = True

        self._update_probe_from_scene_pos(scene_pos)

    def _deactivate_probe(self):
        """
        关闭双击探针。
        """

        self.probe_active = False
        self.probe_time_index = None

        self._hide_probe_items()
        self._render_plot()

    def _get_nearest_active_time_index(self, x_value):
        """
        根据鼠标所在 X 坐标，返回最近的有效时间索引。
        """

        active_indices = self._get_active_row_indices()

        if not active_indices:
            return None

        try:
            x_value = float(x_value)
        except Exception:
            return None

        return min(
            active_indices,
            key=lambda index: abs(index - x_value),
        )

    def _update_probe_from_scene_pos(self, scene_pos):
        """
        根据鼠标位置更新十字探针。
        """

        if not self.probe_active:
            return

        if not self.data:
            return

        if not self.curve_data:
            return

        view_box = self.plot_widget.getViewBox()

        if not view_box.sceneBoundingRect().contains(scene_pos):
            return

        mouse_point = view_box.mapSceneToView(scene_pos)

        mouse_x = mouse_point.x()
        mouse_y = mouse_point.y()

        time_index = self._get_nearest_active_time_index(mouse_x)

        if time_index is None:
            return

        self.probe_time_index = time_index

        self.probe_vertical_line.setValue(time_index)
        self.probe_vertical_line.show()

        self.probe_horizontal_line.setValue(mouse_y)
        self.probe_horizontal_line.show()

        x_values = []
        y_values = []
        brushes = []

        info_lines = [
            f"<b>时间:</b> "
            f"{self.data['date'][time_index]}"
        ]

        for key in self.current_property_names:
            value = self._get_data_value(
                property_key=key,
                row_index=time_index,
            )

            if value is None:
                continue

            color = self._get_property_color(key)
            display_name = self._get_display_name(key)

            x_values.append(time_index)
            y_values.append(value)

            brushes.append(pg.mkBrush(*color))

            info_lines.append(
                f"<span style='color:rgb("
                f"{color[0]},{color[1]},{color[2]}"
                f");'>"
                f"<b>{display_name}:</b>"
                f"</span> "
                f"{value:.6g}"
            )

        if x_values:
            self.probe_points.setData(
                x_values,
                y_values,
                brush=brushes,
                pen=pg.mkPen(
                    color=(100, 100, 100),
                    width=0.9,
                ),
            )

            self.probe_points.show()

        else:
            self.probe_points.hide()

        self.probe_text.setHtml("<br>".join(info_lines))
        self.probe_text.show()

        self._place_text_inside_view(
            text_item=self.probe_text,
            desired_x=time_index,
            desired_y=mouse_y,
        )

        self._render_plot()

    def _hide_probe_items(self):
        """
        隐藏双击探针。
        """

        if self.probe_vertical_line is not None:
            self.probe_vertical_line.hide()

        if self.probe_horizontal_line is not None:
            self.probe_horizontal_line.hide()

        if self.probe_points is not None:
            self.probe_points.hide()

        if self.probe_text is not None:
            self.probe_text.hide()

    # =========================================================
    # 悬停与点击
    # =========================================================
    def _render_plot(self):
        """
        强制刷新图表。
        """

        try:
            self.plot_widget.repaint()
        except Exception:
            pass

    def leaveEvent(self, event):
        """
        鼠标离开组件后隐藏悬停提示。
        """

        self.hover_delay_timer.stop()
        self.pending_hover_scene_pos = None

        self._hide_hover_items()

        super().leaveEvent(event)

    def _find_nearest_curve_point(self, scene_pos):
        """
        根据鼠标在 scene 中的位置，
        寻找距离最近的真实曲线数据点。
        """

        if not self.data or not self.curve_data:
            return None

        view_box = self.plot_widget.getViewBox()

        if not view_box.sceneBoundingRect().contains(scene_pos):
            return None

        mouse_point = view_box.mapSceneToView(scene_pos)

        mouse_x = mouse_point.x()
        mouse_y = mouse_point.y()

        x_range, y_range = view_box.viewRange()

        x_span = max(
            abs(x_range[1] - x_range[0]),
            1e-12,
        )

        y_span = max(
            abs(y_range[1] - y_range[0]),
            1e-12,
        )

        x_tolerance = x_span * 0.008
        y_tolerance = y_span * 0.025

        nearest = None

        for key, curve_info in self.curve_data.items():
            x_values = curve_info["x"]
            y_values = curve_info["y"]

            for index, point_x in enumerate(x_values):
                point_y = y_values[index]

                dx = abs(mouse_x - point_x)
                dy = abs(mouse_y - point_y)

                if dx > x_tolerance or dy > y_tolerance:
                    continue

                normalized_distance = (
                    (dx / x_tolerance) ** 2
                    + (dy / y_tolerance) ** 2
                )

                if (
                    nearest is None
                    or normalized_distance < nearest["distance"]
                ):
                    nearest = {
                        "key": key,
                        "display_name": curve_info[
                            "display_name"
                        ],
                        "x": point_x,
                        "y": point_y,
                        "color": curve_info["color"],
                        "distance": normalized_distance,
                    }

        return nearest

    def _get_data_value(self, property_key, row_index):
        """
        获取指定属性、指定行的数据值。
        无效时返回 None。
        """

        if self.data is None:
            return None

        values = self.data.get(property_key, [])

        if row_index < 0:
            return None

        if row_index >= len(values):
            return None

        value = values[row_index]

        if value is None:
            return None

        try:
            value = float(value)
        except Exception:
            return None

        if not math.isfinite(value):
            return None

        return value

    def _on_mouse_clicked(self, event):
        """
        鼠标左键事件：

        1. 单击真实曲线点：
           向外发送 point_selected(row_index)，联动表格。

        2. 双击：
           开启或关闭十字探针。
        """

        if not self.data or not self.curve_data:
            return

        mouse_event = event[0]

        if mouse_event.button() != Qt.LeftButton:
            return

        scene_pos = mouse_event.scenePos()

        if self._is_double_click_event(mouse_event):
            self.single_click_timer.stop()
            self.pending_single_click_scene_pos = None

            if self.probe_active:
                self._deactivate_probe()
            else:
                self._activate_probe(scene_pos)

            return

        if self.probe_active:
            return

        self.pending_single_click_scene_pos = scene_pos

        self.single_click_timer.stop()

        self.single_click_timer.start(
            self.single_click_delay_ms
        )

    def _is_double_click_event(self, mouse_event):
        """
        判断是否为双击。
        """

        try:
            return bool(mouse_event.double())
        except Exception:
            return False

    def _handle_pending_single_click(self):
        """
        延迟处理单击，避免双击时单击事件被触发。
        """

        scene_pos = self.pending_single_click_scene_pos
        self.pending_single_click_scene_pos = None

        if scene_pos is None:
            return

        if self.probe_active:
            return

        nearest = self._find_nearest_curve_point(scene_pos)

        if nearest is None:
            return

        row_index = int(nearest["x"])

        # 点击曲线时清除表格点击产生的红线。
        self.clear_table_marker()

        # 通知表格高亮对应行。
        self.point_selected.emit(row_index)

    # =========================================================
    # 曲线样式接口
    # =========================================================
    def set_curve_color(self, property_name, color):
        """
        修改某条曲线颜色。

        color 支持：
        - (r, g, b)
        - "#rrggbb"
        - QColor
        """

        key = self._normalize_property_name(property_name)

        if not self._is_known_property_key(key):
            print(
                f"Cannot set color. "
                f"Unknown property: {property_name}"
            )
            return

        rgb = self._normalize_color(color)

        if rgb is None:
            print(f"Invalid color: {color}")
            return

        self.property_colors[key] = rgb
        self._refresh_current_plot()

    def set_curve_width(self, property_name, width):
        """
        修改某条曲线线宽。
        """

        key = self._normalize_property_name(property_name)

        if not self._is_known_property_key(key):
            print(
                f"Cannot set width. "
                f"Unknown property: {property_name}"
            )
            return

        try:
            width = float(width)
        except Exception:
            print(f"Invalid width: {width}")
            return

        if width <= 0:
            print(
                f"Width must be greater than 0: "
                f"{width}"
            )
            return

        self.property_line_widths[key] = width
        self._refresh_current_plot()

    def set_curve_line_style(self, property_name, line_style):
        """
        修改某条曲线线型。

        支持：
        solid / dash / dot / dashdot / dashdotdot

        也支持：
        实线 / 虚线 / 点线 / 点划线 / 双点划线
        """

        key = self._normalize_property_name(property_name)

        if not self._is_known_property_key(key):
            print(
                f"Cannot set line style. "
                f"Unknown property: {property_name}"
            )
            return

        normalized_style = self._normalize_line_style(line_style)

        if normalized_style is None:
            print(f"Invalid line style: {line_style}")
            return

        self.property_line_styles[key] = normalized_style
        self._refresh_current_plot()

    def set_curve_style(
        self,
        property_name,
        color=None,
        width=None,
        line_style=None,
    ):
        """
        同时修改颜色、线宽和线型。

        示例：
        self.set_curve_style(
            "累计产水量",
            color=(0, 90, 220),
            width=1.5,
            line_style="dash",
        )
        """

        key = self._normalize_property_name(property_name)

        if not self._is_known_property_key(key):
            print(
                f"Cannot set style. "
                f"Unknown property: {property_name}"
            )
            return

        if color is not None:
            rgb = self._normalize_color(color)

            if rgb is None:
                print(f"Invalid color: {color}")
                return

            self.property_colors[key] = rgb

        if width is not None:
            try:
                width = float(width)
            except Exception:
                print(f"Invalid width: {width}")
                return

            if width <= 0:
                print(
                    f"Width must be greater than 0: "
                    f"{width}"
                )
                return

            self.property_line_widths[key] = width

        if line_style is not None:
            normalized_style = self._normalize_line_style(
                line_style
            )

            if normalized_style is None:
                print(f"Invalid line style: {line_style}")
                return

            self.property_line_styles[key] = normalized_style

        self._refresh_current_plot()

    def reset_curve_style(self, property_name=None):
        """
        恢复默认颜色、线宽和线型。

        property_name 为 None 时，
        恢复所有曲线的默认样式。
        """

        if property_name is None:
            self.property_colors = dict(
                self.default_property_colors
            )

            self.property_line_widths = {
                key: self.default_line_width
                for key in self.property_order
            }

            self.property_line_styles = {
                key: self.default_line_style
                for key in self.property_order
            }

            self._refresh_current_plot()
            return

        key = self._normalize_property_name(property_name)

        if not self._is_known_property_key(key):
            print(
                f"Cannot reset style. "
                f"Unknown property: {property_name}"
            )
            return

        if key in self.default_property_colors:
            self.property_colors[key] = (
                self.default_property_colors[key]
            )
        else:
            self.property_colors.pop(key, None)

        self.property_line_widths[key] = self.default_line_width
        self.property_line_styles[key] = self.default_line_style

        self._refresh_current_plot()

    def get_curve_style(self, property_name):
        """
        获取某条曲线当前样式。
        """

        key = self._normalize_property_name(property_name)

        if not self._is_known_property_key(key):
            return None

        line_style = self.property_line_styles.get(
            key,
            self.default_line_style,
        )

        return {
            "property_key": key,
            "display_name": self._get_display_name(key),
            "color": self._get_property_color(key),
            "width": self.property_line_widths.get(
                key,
                self.default_line_width,
            ),
            "line_style": line_style,
            "line_style_display": self.line_style_display_names.get(
                line_style,
                line_style,
            ),
        }

    def get_available_line_styles(self):
        """
        返回可用线型列表。
        """

        return [
            ("solid", "实线"),
            ("dash", "虚线"),
            ("dot", "点线"),
            ("dashdot", "点划线"),
            ("dashdotdot", "双点划线"),
        ]

    def _refresh_current_plot(self):
        """
        曲线样式、时间范围改变后刷新当前图表。
        """

        if not self.current_property_names:
            return

        current_names = list(self.current_property_names)

        self.plot_selected_properties(current_names)

    # =========================================================
    # 属性、颜色、线型工具
    # =========================================================
    def _normalize_property_name(self, property_name):
        """
        中文属性名转英文 key。
        若本来就是英文 key，则直接返回。
        """

        if property_name in self.display_name_to_key:
            return self.display_name_to_key[property_name]

        return property_name

    def _is_known_property_key(self, key):
        """
        判断属性是否允许设置样式。
        """

        if key in self.property_order:
            return True

        return (
            self.data is not None
            and key in self.data
            and key != "date"
        )

    def _get_display_name(self, property_key):
        """
        获取中文显示名。
        """

        return self.property_display_names.get(
            property_key,
            property_key,
        )

    def _get_property_color(self, property_key, fallback_index=0):
        """
        根据英文 key 获取当前颜色。
        """

        if property_key in self.property_colors:
            return self.property_colors[property_key]

        fallback_colors = [
            (180, 0, 255),
            (0, 0, 255),
            (255, 0, 0),
            (0, 150, 0),
            (255, 140, 0),
            (0, 180, 180),
            (130, 80, 20),
        ]

        return fallback_colors[
            fallback_index % len(fallback_colors)
        ]

    def _normalize_line_style(self, line_style):
        """
        将中文、英文线型名称统一转为内部 key。
        """

        if line_style is None:
            return None

        style_text = str(line_style).strip().lower()

        alias_map = {
            "solid": "solid",
            "实线": "solid",

            "dash": "dash",
            "dashed": "dash",
            "虚线": "dash",

            "dot": "dot",
            "dotted": "dot",
            "点线": "dot",

            "dashdot": "dashdot",
            "dash-dot": "dashdot",
            "点划线": "dashdot",

            "dashdotdot": "dashdotdot",
            "dash-dot-dot": "dashdotdot",
            "双点划线": "dashdotdot",
        }

        normalized_style = alias_map.get(style_text)

        if normalized_style not in self.line_style_map:
            return None

        return normalized_style

    def _normalize_color(self, color):
        """
        把不同颜色格式转换成 RGB tuple。

        支持：
        - (r, g, b)
        - [r, g, b]
        - "#rrggbb"
        - QColor
        """

        if isinstance(color, (tuple, list)):
            if len(color) < 3:
                return None

            try:
                r = int(color[0])
                g = int(color[1])
                b = int(color[2])
            except Exception:
                return None

            if not self._is_valid_rgb_value(r):
                return None

            if not self._is_valid_rgb_value(g):
                return None

            if not self._is_valid_rgb_value(b):
                return None

            return (r, g, b)

        if isinstance(color, str):
            qcolor = QColor(color)

            if not qcolor.isValid():
                return None

            return (
                qcolor.red(),
                qcolor.green(),
                qcolor.blue(),
            )

        if isinstance(color, QColor):
            if not color.isValid():
                return None

            return (
                color.red(),
                color.green(),
                color.blue(),
            )

        return None

    def _is_valid_rgb_value(self, value):
        """
        判断 RGB 数值是否合法。
        """

        return 0 <= value <= 255

    def _get_qt_line_style(
        self,
        property_key,
        is_history=False,
    ):
        """
        获取该曲线真实使用的 Qt 线型。

        历史曲线始终优先使用虚线，
        与 _make_curve_pen() 的规则完全一致。
        """

        if is_history:
            return Qt.DashLine

        line_style = self.property_line_styles.get(
            property_key,
            self.default_line_style,
        )

        return self.line_style_map.get(
            line_style,
            Qt.SolidLine,
        )

    def _make_curve_pen(self, property_key, color, is_history=False):
        """
        根据当前颜色、线宽和线型创建曲线画笔。

        普通曲线使用用户设置的线型；
        历史曲线沿用原有规则，始终优先使用虚线。
        """

        line_width = self.property_line_widths.get(
            property_key,
            self.default_line_width,
        )

        qt_line_style = self._get_qt_line_style(
            property_key=property_key,
            is_history=is_history,
        )

        pen = pg.mkPen(
            color=color,
            width=line_width,
            style=qt_line_style,
        )

        pen.setCosmetic(True)

        return pen

    # =========================================================
    # 坐标轴与文字位置
    # =========================================================
    def _update_date_axis(self, dates, row_indices=None):
        """
        更新 X 轴时间刻度。
        """

        axis = self.plot_widget.getAxis("bottom")

        if not dates:
            axis.setTicks([[]])
            return

        if row_indices is None:
            row_indices = list(range(len(dates)))

        if not row_indices:
            axis.setTicks([[]])
            return

        row_indices = list(row_indices)
        total = len(row_indices)

        if total <= 8:
            ticks = [
                (i, str(dates[i]))
                for i in row_indices
                if 0 <= i < len(dates)
            ]

            axis.setTicks([ticks])
            return

        target_tick_count = 8
        tick_step = max(1, total // target_tick_count)

        tick_indices = row_indices[::tick_step]

        first_index = row_indices[0]

        if first_index not in tick_indices:
            tick_indices.insert(0, first_index)

        last_index = row_indices[-1]

        if tick_indices:
            prev_index = tick_indices[-1]
            min_gap = max(1, tick_step // 2)

            if last_index - prev_index >= min_gap:
                tick_indices.append(last_index)
        else:
            tick_indices.append(last_index)

        final_indices = []
        seen = set()

        for i in tick_indices:
            if i in seen:
                continue

            if 0 <= i < len(dates):
                final_indices.append(i)
                seen.add(i)

        ticks = [
            (i, str(dates[i]))
            for i in final_indices
        ]

        axis.setTicks([ticks])

    def _place_text_inside_view(
        self,
        text_item,
        desired_x,
        desired_y,
        margin_px=8,
    ):
        """
        将 TextItem 尽量限制在绘图区内部。
        """

        if text_item is None:
            return

        view_box = self.plot_widget.getViewBox()

        try:
            text_item.setPos(
                float(desired_x),
                float(desired_y),
            )

            item_scene_rect = text_item.mapRectToScene(
                text_item.boundingRect()
            )

            view_scene_rect = view_box.sceneBoundingRect()

            left_limit = view_scene_rect.left() + margin_px
            right_limit = view_scene_rect.right() - margin_px
            top_limit = view_scene_rect.top() + margin_px
            bottom_limit = view_scene_rect.bottom() - margin_px

            offset_x = 0.0
            offset_y = 0.0

            if item_scene_rect.left() < left_limit:
                offset_x = left_limit - item_scene_rect.left()

            elif item_scene_rect.right() > right_limit:
                offset_x = right_limit - item_scene_rect.right()

            if item_scene_rect.top() < top_limit:
                offset_y = top_limit - item_scene_rect.top()

            elif item_scene_rect.bottom() > bottom_limit:
                offset_y = bottom_limit - item_scene_rect.bottom()

            if abs(offset_x) < 0.01 and abs(offset_y) < 0.01:
                return

            anchor_scene = text_item.mapToScene(
                QPointF(0.0, 0.0)
            )

            corrected_scene = QPointF(
                anchor_scene.x() + offset_x,
                anchor_scene.y() + offset_y,
            )

            corrected_view = view_box.mapSceneToView(
                corrected_scene
            )

            text_item.setPos(
                corrected_view.x(),
                corrected_view.y(),
            )

        except Exception:
            pass

    def _is_history_property(self, property_name):
        """
        判断是否为历史数据曲线。
        历史曲线始终优先使用虚线。
        """

        name = str(property_name).lower()

        return (
            "history" in name
            or "hist" in name
            or "历史" in str(property_name)
        )

    def _add_bottom_legend_item(
        self,
        property_key,
        display_name,
        color,
        is_history=False,
    ):
        """
        添加底部居中图例。

        图例左侧线段由 _LegendLineSample 绘制，
        会与对应曲线保持完全一致的：
        - 颜色；
        - 线宽；
        - 线型；
        - 历史曲线的虚线规则。
        """

        line_width = self.property_line_widths.get(
            property_key,
            self.default_line_width,
        )

        qt_line_style = self._get_qt_line_style(
            property_key=property_key,
            is_history=is_history,
        )

        legend_item = QWidget()
        legend_item.setFixedHeight(22)

        item_layout = QHBoxLayout(legend_item)
        item_layout.setContentsMargins(0, 0, 0, 0)
        item_layout.setSpacing(6)

        line_sample = _LegendLineSample(
            color=color,
            line_width=line_width,
            qt_line_style=qt_line_style,
            parent=legend_item,
        )

        name_label = QLabel(display_name)
        name_label.setStyleSheet("""
            QLabel {
                color: #333333;
                font-size: 11px;
            }
        """)

        item_layout.addWidget(line_sample)
        item_layout.addWidget(name_label)

        insert_index = max(
            0,
            self.legend_layout.count() - 1,
        )

        self.legend_layout.insertWidget(
            insert_index,
            legend_item,
        )

    # =========================================================
    # 悬停
    # =========================================================
    def _on_mouse_moved(self, event):
        """
        鼠标移动时：
        - 探针开启：更新探针；
        - 探针关闭：等待 150ms 后显示悬停提示。
        """

        scene_pos = event[0]

        if self.probe_active:
            self.hover_delay_timer.stop()
            self.pending_hover_scene_pos = None

            self._hide_hover_items()
            self._update_probe_from_scene_pos(scene_pos)
            return

        if not self.data or not self.curve_data:
            self.hover_delay_timer.stop()
            self.pending_hover_scene_pos = None

            self._hide_hover_items()
            return

        self._hide_hover_items()
        self.hover_delay_timer.stop()

        nearest = self._find_nearest_curve_point(scene_pos)

        if nearest is None:
            self.pending_hover_scene_pos = None
            return

        self.pending_hover_scene_pos = scene_pos
        self.hover_delay_timer.start(self.hover_delay_ms)

    def _show_delayed_hover(self):
        """
        停留一小段时间后显示悬停提示。
        """

        if self.probe_active:
            self._hide_hover_items()
            return

        if self.pending_hover_scene_pos is None:
            return

        nearest = self._find_nearest_curve_point(
            self.pending_hover_scene_pos
        )

        if nearest is None:
            self._hide_hover_items()
            return

        self._show_hover_for_nearest_point(nearest)

    def _show_hover_for_nearest_point(self, nearest):
        """
        显示悬停点和悬停文字框。
        """

        if nearest is None:
            self._hide_hover_items()
            return

        value = nearest["y"]
        point_index = int(nearest["x"])
        display_name = nearest["display_name"]
        color = nearest["color"]

        try:
            value_text = f"{float(value):.6g}"
        except Exception:
            value_text = str(value)

        dates = self.data.get("date", [])

        if 0 <= point_index < len(dates):
            date_text = str(dates[point_index])
        else:
            date_text = ""

        if date_text:
            html = (
                f"<b>时间:</b> {date_text}<br>"
                f"<b>{display_name}:</b> {value_text}"
            )
        else:
            html = f"<b>{display_name}:</b> {value_text}"

        self.hover_point.setData(
            [nearest["x"]],
            [nearest["y"]],
            brush=pg.mkBrush(*color),
            pen=pg.mkPen(
                color=(0, 0, 0),
                width=1,
            ),
        )

        self.hover_point.show()

        self.hover_text.setText(html)
        self.hover_text.adjustSize()

        view_box = self.plot_widget.getViewBox()

        scene_pos = view_box.mapViewToScene(
            QPointF(
                nearest["x"],
                nearest["y"],
            )
        )

        widget_pos = self.plot_widget.mapFromScene(scene_pos)

        x = widget_pos.x() + 12
        y = widget_pos.y() - self.hover_text.height() - 8

        # 右侧空间不足时，放到点的左边。
        if x + self.hover_text.width() > self.plot_widget.width():
            x = (
                widget_pos.x()
                - self.hover_text.width()
                - 12
            )

        # 上方空间不足时，放到点的下方。
        if y < 0:
            y = widget_pos.y() + 12

        # 仍超出下方边界时，贴近下边缘。
        if y + self.hover_text.height() > self.plot_widget.height():
            y = (
                self.plot_widget.height()
                - self.hover_text.height()
                - 8
            )

        max_x = max(
            0,
            self.plot_widget.width()
            - self.hover_text.width()
            - 4,
        )

        max_y = max(
            0,
            self.plot_widget.height()
            - self.hover_text.height()
            - 4,
        )

        x = max(4, min(x, max_x))
        y = max(4, min(y, max_y))

        self.hover_text.move(int(x), int(y))
        self.hover_text.show()
        self.hover_text.raise_()

    def _hide_hover_items(self):
        """
        隐藏悬停点和悬停框。
        """

        if self.hover_text is not None:
            self.hover_text.hide()

        if self.hover_point is not None:
            self.hover_point.hide()

    # =========================================================
    # 导出
    # =========================================================
    def export_plot_image(self, file_path):
        """
        导出当前曲线图图片。

        若 file_path 不带扩展名，默认保存为 PNG。
        """

        if not file_path:
            print(
                "export_plot_image failed: "
                "file_path is empty."
            )
            return False

        try:
            file_path = str(file_path)

            _, ext = os.path.splitext(file_path)

            if ext == "":
                file_path = file_path + ".png"

            folder = os.path.dirname(file_path)

            if folder and not os.path.exists(folder):
                os.makedirs(folder, exist_ok=True)

            pixmap = self.grab()
            ok = pixmap.save(file_path)

            if not ok:
                print(
                    f"export_plot_image failed: "
                    f"cannot save to {file_path}"
                )
                return False

            print(f"Plot image exported: {file_path}")
            return True

        except Exception as exc:
            print(f"export_plot_image error: {exc}")
            return False