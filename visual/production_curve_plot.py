import csv
import os
import math

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor
import pyqtgraph as pg


class ProductionCurvePlotWidget(QWidget):
    """
    Production curve line chart widget.

    功能：
    1. 从 output_sim_lgr_noWR.csv 读取生产动态数据
    2. 时间列：Time
    3. 曲线字段：CumWater / CumGas / Qw / Qg
    4. 支持中文属性名显示
    5. 支持固定属性颜色
    6. 支持外部修改曲线颜色和粗细
    7. 鼠标悬停在真实数据点上时显示时间和该点的值
    8. 支持表格点击某一行后，高亮线图对应时间点
    9. 支持点击线图真实数据点后，向外发送 point_selected(row_index)，用于表格自动跳转
    10. 支持用户选择时间范围，只绘制该时间范围内的曲线
    11. 支持导出当前线图图片
    """

    # 点击线图真实数据点时，向外发送对应的数据行号
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
            "CumWater": "累积产水量",
            "CumGas": "累积产气",
            "Qw": "产水速率",
            "Qg": "产气速率",
        }

        # 中文显示名 -> 英文 key
        self.display_name_to_key = {
            display_name: key
            for key, display_name in self.property_display_names.items()
        }

        # 控制属性显示顺序
        self.property_order = [
            "CumWater",
            "CumGas",
            "Qw",
            "Qg",
        ]

        # =========================
        # 默认固定颜色
        # =========================
        self.default_property_colors = {
            "CumWater": (0, 0, 255),
            "CumGas": (180, 0, 255),
            "Qw": (0, 120, 255),
            "Qg": (160, 0, 200),
        }

        # 当前颜色，可以被外部修改
        self.property_colors = dict(self.default_property_colors)

        # =========================
        # 默认线宽
        # =========================
        self.default_line_width = 1.2

        # 当前每条曲线的线宽，可以被外部修改
        self.property_line_widths = {
            key: self.default_line_width
            for key in self.property_order
        }

        # 鼠标悬停提示
        self.hover_text = None
        self.hover_point = None
        self.mouse_move_proxy = None

        # 鼠标点击数据点
        self.mouse_click_proxy = None

        # 表格点击某一行后，用于高亮对应时间点
        self.selected_time_index = None
        self.selected_time_line = None
        self.selected_time_points = None
        self.selected_time_text = None

        # 用户选择的时间范围
        # None 表示显示全部时间
        self.time_range_start_index = None
        self.time_range_end_index = None

        self.init_ui()

    def init_ui(self):
        pg.setConfigOptions(antialias=True)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # =========================
        # Plot area
        # =========================
        self.plot_widget = pg.PlotWidget()

        # 关闭 pyqtgraph 自带右键菜单
        self.plot_widget.setMenuEnabled(False)

        root_layout.addWidget(self.plot_widget, 1)

        self.plot_widget.setBackground("w")
        self.plot_widget.showGrid(x=True, y=True, alpha=0.25)

        # 不显示图表标题
        self.plot_widget.setTitle("")

        self.plot_widget.setLabel("bottom", "时间")
        self.plot_widget.setLabel("left", "数值")

        for axis_name in ["bottom", "left", "top", "right"]:
            axis = self.plot_widget.getAxis(axis_name)
            axis.setPen(pg.mkPen("#666666"))
            axis.setTextPen(pg.mkPen("#444444"))

        self._create_hover_items()
        self._create_selected_time_items()

        self.mouse_move_proxy = pg.SignalProxy(
            self.plot_widget.scene().sigMouseMoved,
            rateLimit=60,
            slot=self._on_mouse_moved
        )

        self.mouse_click_proxy = pg.SignalProxy(
            self.plot_widget.scene().sigMouseClicked,
            rateLimit=60,
            slot=self._on_mouse_clicked
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
    # Hover / selected items
    # =========================================================
    def _create_hover_items(self):
        """
        创建鼠标悬停提示。
        ignoreBounds=True 可以避免提示点/提示框影响图表范围。
        """
        self.hover_point = pg.ScatterPlotItem(
            size=9,
            brush=pg.mkBrush(255, 255, 255),
            pen=pg.mkPen(0, 0, 0, width=1)
        )

        self.plot_widget.addItem(self.hover_point, ignoreBounds=True)
        self.hover_point.hide()

        self.hover_text = pg.TextItem(
            text="",
            color=(0, 0, 0),
            anchor=(0, 1),
            fill=(255, 255, 230, 230),
            border=pg.mkPen("#666666")
        )

        self.plot_widget.addItem(self.hover_text, ignoreBounds=True)
        self.hover_text.hide()

    def _create_selected_time_items(self):
        """
        创建表格点击行后，线图上的高亮时间线和高亮点。
        """
        self.selected_time_line = pg.InfiniteLine(
            angle=90,
            movable=False,
            pen=pg.mkPen(
                color=(30, 30, 30),
                width=1.2,
                style=Qt.DashLine
            )
        )

        self.plot_widget.addItem(
            self.selected_time_line,
            ignoreBounds=True
        )
        self.selected_time_line.hide()

        self.selected_time_points = pg.ScatterPlotItem(
            size=10,
            brush=pg.mkBrush(255, 255, 0),
            pen=pg.mkPen(0, 0, 0, width=1)
        )

        self.plot_widget.addItem(
            self.selected_time_points,
            ignoreBounds=True
        )
        self.selected_time_points.hide()

        self.selected_time_text = pg.TextItem(
            text="",
            color=(0, 0, 0),
            anchor=(0, 1),
            fill=(240, 248, 255, 230),
            border=pg.mkPen("#666666")
        )

        self.plot_widget.addItem(
            self.selected_time_text,
            ignoreBounds=True
        )
        self.selected_time_text.hide()

    # =========================================================
    # Data interface
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
            with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)

                if reader.fieldnames is None:
                    print("CSV file has no header.")
                    return False

                fieldnames = [name.strip() for name in reader.fieldnames]

                if time_column not in fieldnames:
                    print(f"Time column '{time_column}' not found in CSV.")
                    print("Available columns:", fieldnames)
                    return False

                data = {
                    "date": []
                }

                required_fields = [
                    "CumWater",
                    "CumGas",
                    "Qw",
                    "Qg",
                ]

                for field in required_fields:
                    if field in fieldnames:
                        data[field] = []
                    else:
                        print(f"Warning: field '{field}' not found in CSV.")

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
                print("Available properties:", self.get_available_properties())

                return True

        except Exception as exc:
            print(f"load_data_from_csv error: {exc}")
            return False

    def get_available_properties(self):
        """
        获取当前可绘制属性，返回中文显示名。
        """
        if not self.data:
            return []

        result = []

        for key in self.property_order:
            if key in self.data:
                display_name = self.property_display_names.get(key, key)
                result.append(display_name)

        return result

    # =========================================================
    # Time range interface
    # =========================================================
    def get_time_labels(self):
        """
        获取当前数据中的时间标签列表。
        UI 层可以用这个函数刷新开始时间 / 结束时间下拉框。
        """
        if self.data is None:
            return []

        if "date" not in self.data:
            return []

        return [str(v) for v in self.data["date"]]

    def set_time_range_by_index(self, start_index, end_index):
        """
        设置线图显示的时间范围。

        start_index / end_index 是 data["date"] 的索引。
        """
        if self.data is None or "date" not in self.data:
            return

        dates = self.data["date"]
        n = len(dates)

        if n == 0:
            return

        try:
            start_index = int(start_index)
            end_index = int(end_index)
        except Exception:
            print("Invalid time range index.")
            return

        start_index = max(0, min(n - 1, start_index))
        end_index = max(0, min(n - 1, end_index))

        if start_index > end_index:
            start_index, end_index = end_index, start_index

        self.time_range_start_index = start_index
        self.time_range_end_index = end_index

        self._hide_selected_time_items()
        self.selected_time_index = None

        self._refresh_current_plot()

    def clear_time_range(self):
        """
        清除时间范围限制，恢复显示全部时间。
        """
        self.time_range_start_index = None
        self.time_range_end_index = None

        self._hide_selected_time_items()
        self.selected_time_index = None

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

        if self.time_range_start_index is None or self.time_range_end_index is None:
            return list(range(n))

        start_index = max(0, min(n - 1, int(self.time_range_start_index)))
        end_index = max(0, min(n - 1, int(self.time_range_end_index)))

        if start_index > end_index:
            start_index, end_index = end_index, start_index

        return list(range(start_index, end_index + 1))

    # =========================================================
    # Plot
    # =========================================================
    def clear_plot(self):
        """
        清空曲线和底部图例。
        """
        self.plot_widget.clear()

        self.curve_items = {}
        self.curve_data = {}
        self.current_property_names = []

        self._create_hover_items()
        self._create_selected_time_items()

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

        self.clear_plot()

        dates = self.data["date"]
        active_row_indices = self._get_active_row_indices()

        if not active_row_indices:
            print("No data in selected time range.")
            return

        self._update_date_axis(dates, active_row_indices)

        for index, property_name in enumerate(property_names):
            key = self._normalize_property_name(property_name)

            if key not in self.data:
                print(f"Property not found in data: {property_name}")
                continue

            if key not in self.property_order:
                print(f"Property is not allowed to plot: {property_name}")
                continue

            raw_y = self.data[key]

            if len(raw_y) != len(dates):
                print(f"Data length mismatch: {property_name}")
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
                print(f"No valid data to plot: {property_name}")
                continue

            display_name = self._get_display_name(key)
            color = self._get_property_color(key, fallback_index=index)
            is_history = self._is_history_property(display_name)

            pen = self._make_curve_pen(
                property_key=key,
                color=color,
                is_history=is_history
            )

            curve_item = self.plot_widget.plot(
                x,
                y,
                pen=pen
            )

            self.curve_items[key] = curve_item
            self.current_property_names.append(key)

            self.curve_data[key] = {
                "x": x,
                "y": y,
                "color": color,
                "display_name": display_name
            }

            self._add_bottom_legend_item(
                display_name,
                color,
                is_history=is_history
            )

        self.plot_widget.enableAutoRange()
        self.plot_widget.getViewBox().disableAutoRange()

        if self.selected_time_index is not None:
            self.highlight_time_index(self.selected_time_index)

    def plot_one_property(self, property_name):
        """
        只绘制一个属性。
        """
        self.plot_selected_properties([property_name])

    def set_chart_title(self, title):
        """
        设置图表标题。
        """
        self.plot_widget.setTitle(title, color="#222222", size="10pt")

    def set_y_axis_title(self, title):
        """
        设置 Y 轴标题。
        """
        self.plot_widget.setLabel("left", title)

    def reset_view(self):
        """
        重置视图范围。
        """
        self.plot_widget.enableAutoRange()
        self.plot_widget.getViewBox().disableAutoRange()

    # =========================================================
    # Table linkage highlight
    # =========================================================
    def highlight_time_index(self, row_index):
        """
        高亮表格点击的某一行对应的时间点。

        再次点击同一行：
            隐藏竖线、高亮点和文本框。
        """
        if self.data is None:
            self._hide_selected_time_items()
            self.selected_time_index = None
            return

        if "date" not in self.data:
            self._hide_selected_time_items()
            self.selected_time_index = None
            return

        dates = self.data["date"]

        try:
            row_index = int(row_index)
        except Exception:
            self._hide_selected_time_items()
            self.selected_time_index = None
            return

        if row_index < 0 or row_index >= len(dates):
            self._hide_selected_time_items()
            self.selected_time_index = None
            return

        if self.time_range_start_index is not None and self.time_range_end_index is not None:
            start_index = min(self.time_range_start_index, self.time_range_end_index)
            end_index = max(self.time_range_start_index, self.time_range_end_index)

            if row_index < start_index or row_index > end_index:
                self._hide_selected_time_items()
                self.selected_time_index = None
                self._render_plot()
                return

        if self.selected_time_index == row_index:
            visible = False

            try:
                if self.selected_time_text is not None:
                    visible = self.selected_time_text.isVisible()
            except Exception:
                visible = False

            if visible:
                self._hide_selected_time_items()
                self.selected_time_index = None
                self._render_plot()
                return

        self.selected_time_index = row_index

        if self.selected_time_line is None:
            self._create_selected_time_items()

        self.selected_time_line.setValue(row_index)
        self.selected_time_line.show()

        x_values = []
        y_values = []

        date_text = str(dates[row_index])
        info_lines = [
            f"<b>时间:</b> {date_text}"
        ]

        for key in self.current_property_names:
            values = self.data.get(key, [])

            if row_index >= len(values):
                continue

            value = values[row_index]

            if value is None:
                continue

            try:
                value = float(value)
            except Exception:
                continue

            if not math.isfinite(value):
                continue

            x_values.append(row_index)
            y_values.append(value)

            display_name = self._get_display_name(key)
            value_text = f"{value:.6g}"

            info_lines.append(
                f"<b>{display_name}:</b> {value_text}"
            )

        if x_values and y_values:
            self.selected_time_points.setData(
                x_values,
                y_values,
                brush=pg.mkBrush(255, 255, 0),
                pen=pg.mkPen(0, 0, 0, width=1)
            )
            self.selected_time_points.show()

            label_y = max(y_values)
        else:
            self.selected_time_points.hide()

            try:
                _, y_range = self.plot_widget.getViewBox().viewRange()
                label_y = y_range[1]
            except Exception:
                label_y = 0.0

        html = "<br>".join(info_lines)

        self.selected_time_text.setHtml(html)
        self.selected_time_text.setPos(row_index, label_y)
        self.selected_time_text.show()

        self._render_plot()

    def _hide_selected_time_items(self):
        """
        隐藏表格点击产生的高亮时间线和点。
        """
        if self.selected_time_line is not None:
            self.selected_time_line.hide()

        if self.selected_time_points is not None:
            self.selected_time_points.hide()

        if self.selected_time_text is not None:
            self.selected_time_text.hide()

    def _render_plot(self):
        """
        刷新 pyqtgraph 线图。
        """
        try:
            self.plot_widget.repaint()
        except Exception:
            pass

    # =========================================================
    # Mouse click / hover shared helper
    # =========================================================
    def _find_nearest_curve_point(self, scene_pos):
        """
        根据鼠标在 scene 中的位置，寻找最近的真实曲线数据点。
        """
        if self.data is None:
            return None

        if not self.curve_data:
            return None

        view_box = self.plot_widget.getViewBox()

        if not view_box.sceneBoundingRect().contains(scene_pos):
            return None

        mouse_point = view_box.mapSceneToView(scene_pos)
        mouse_x = mouse_point.x()
        mouse_y = mouse_point.y()

        x_range, y_range = view_box.viewRange()
        x_span = max(abs(x_range[1] - x_range[0]), 1e-12)
        y_span = max(abs(y_range[1] - y_range[0]), 1e-12)

        x_tolerance = x_span * 0.008
        y_tolerance = y_span * 0.025

        nearest = None

        for key, item in self.curve_data.items():
            x_values = item["x"]
            y_values = item["y"]
            color = item["color"]
            display_name = item["display_name"]

            if not x_values or not y_values:
                continue

            for i in range(len(x_values)):
                point_x = x_values[i]
                point_y = y_values[i]

                dx = abs(mouse_x - point_x)
                dy = abs(mouse_y - point_y)

                if dx > x_tolerance or dy > y_tolerance:
                    continue

                normalized_distance = (
                    (dx / x_tolerance) ** 2
                    + (dy / y_tolerance) ** 2
                )

                if nearest is None or normalized_distance < nearest["distance"]:
                    nearest = {
                        "key": key,
                        "display_name": display_name,
                        "x": point_x,
                        "y": point_y,
                        "color": color,
                        "distance": normalized_distance
                    }

        return nearest

    def _on_mouse_clicked(self, event):
        """
        鼠标点击线图数据点：
        1. 找到最近的真实数据点
        2. 线图高亮该时间点
        3. 发出 point_selected(row_index)，让表格自动跳到对应行
        """
        if self.data is None:
            return

        if not self.curve_data:
            return

        mouse_event = event[0]

        if mouse_event.button() != Qt.LeftButton:
            return

        scene_pos = mouse_event.scenePos()

        nearest = self._find_nearest_curve_point(scene_pos)

        if nearest is None:
            return

        row_index = int(nearest["x"])

        self.highlight_time_index(row_index)
        self.point_selected.emit(row_index)

    # =========================================================
    # Style external interface
    # =========================================================
    def set_curve_color(self, property_name, color):
        """
        修改某条曲线颜色。
        """
        key = self._normalize_property_name(property_name)

        if key not in self.property_order:
            print(f"Cannot set color. Unknown property: {property_name}")
            return

        rgb = self._normalize_color(color)

        if rgb is None:
            print(f"Invalid color: {color}")
            return

        self.property_colors[key] = rgb
        self._refresh_current_plot()

    def set_curve_width(self, property_name, width):
        """
        修改某条曲线粗细。
        """
        key = self._normalize_property_name(property_name)

        if key not in self.property_order:
            print(f"Cannot set width. Unknown property: {property_name}")
            return

        try:
            width = float(width)
        except Exception:
            print(f"Invalid width: {width}")
            return

        if width <= 0:
            print(f"Width must be greater than 0: {width}")
            return

        self.property_line_widths[key] = width
        self._refresh_current_plot()

    def set_curve_style(self, property_name, color=None, width=None):
        """
        同时修改颜色和粗细。
        """
        key = self._normalize_property_name(property_name)

        if key not in self.property_order:
            print(f"Cannot set style. Unknown property: {property_name}")
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
                print(f"Width must be greater than 0: {width}")
                return

            self.property_line_widths[key] = width

        self._refresh_current_plot()

    def reset_curve_style(self, property_name=None):
        """
        恢复默认颜色和粗细。
        """
        if property_name is None:
            self.property_colors = dict(self.default_property_colors)
            self.property_line_widths = {
                key: self.default_line_width
                for key in self.property_order
            }
            self._refresh_current_plot()
            return

        key = self._normalize_property_name(property_name)

        if key not in self.property_order:
            print(f"Cannot reset style. Unknown property: {property_name}")
            return

        if key in self.default_property_colors:
            self.property_colors[key] = self.default_property_colors[key]

        self.property_line_widths[key] = self.default_line_width

        self._refresh_current_plot()

    def get_curve_style(self, property_name):
        """
        获取某条曲线当前样式。
        """
        key = self._normalize_property_name(property_name)

        if key not in self.property_order:
            return None

        return {
            "property_key": key,
            "display_name": self._get_display_name(key),
            "color": self._get_property_color(key),
            "width": self.property_line_widths.get(key, self.default_line_width),
        }

    def _refresh_current_plot(self):
        """
        修改颜色/粗细/时间范围后，刷新当前已经绘制的曲线。
        """
        if not self.current_property_names:
            return

        current_names = list(self.current_property_names)
        self.plot_selected_properties(current_names)

    # =========================================================
    # Property name / style
    # =========================================================
    def _normalize_property_name(self, property_name):
        """
        中文属性名转英文 key。
        如果本来就是英文 key，则直接返回。
        """
        if property_name in self.display_name_to_key:
            return self.display_name_to_key[property_name]

        return property_name

    def _get_display_name(self, property_key):
        """
        获取中文显示名。
        """
        return self.property_display_names.get(property_key, property_key)

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

        return fallback_colors[fallback_index % len(fallback_colors)]

    def _normalize_color(self, color):
        """
        把不同颜色格式转换成 RGB tuple。
        支持：
        - (r, g, b)
        - "#rrggbb"
        - QColor
        """
        if isinstance(color, tuple) or isinstance(color, list):
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

            return (qcolor.red(), qcolor.green(), qcolor.blue())

        if isinstance(color, QColor):
            if not color.isValid():
                return None

            return (color.red(), color.green(), color.blue())

        return None

    def _is_valid_rgb_value(self, value):
        return 0 <= value <= 255

    def _make_curve_pen(self, property_key, color, is_history=False):
        """
        创建曲线画笔。
        线宽从 self.property_line_widths 里读取。
        """
        line_width = self.property_line_widths.get(
            property_key,
            self.default_line_width
        )

        if is_history:
            pen = pg.mkPen(
                color=color,
                width=line_width,
                style=Qt.DashLine
            )
        else:
            pen = pg.mkPen(
                color=color,
                width=line_width
            )

        pen.setCosmetic(True)
        return pen

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

    def _is_history_property(self, property_name):
        """
        判断是否为历史曲线。
        """
        name = str(property_name).lower()

        return (
            "history" in name
            or "hist" in name
            or "历史" in str(property_name)
        )

    def _add_bottom_legend_item(self, display_name, color, is_history=False):
        """
        添加底部居中图例。
        """
        r, g, b = color

        if is_history:
            line_text = "----"
        else:
            line_text = "━━━━"

        label = QLabel(
            f"<span style='color: rgb({r},{g},{b}); font-size: 16px;'>{line_text}</span>"
            f"<span style='margin-left:6px; color:#333333; font-size:11px;'>{display_name}</span>"
        )

        insert_index = max(0, self.legend_layout.count() - 1)
        self.legend_layout.insertWidget(insert_index, label)

    # =========================================================
    # Mouse hover
    # =========================================================
    def _on_mouse_moved(self, event):
        """
        鼠标悬停提示。
        """
        if self.data is None:
            return

        if not self.curve_data:
            return

        pos = event[0]

        nearest = self._find_nearest_curve_point(pos)

        if nearest is None:
            self._hide_hover_items()
            return

        display_name = nearest["display_name"]
        value = nearest["y"]
        color = nearest["color"]
        point_index = int(nearest["x"])

        if isinstance(value, float):
            value_text = f"{value:.6g}"
        else:
            value_text = str(value)

        date_text = ""

        try:
            if "date" in self.data:
                dates = self.data["date"]
                if 0 <= point_index < len(dates):
                    date_text = str(dates[point_index])
        except Exception:
            date_text = ""

        if date_text:
            html = (
                f"<b>时间:</b> {date_text}<br>"
                f"<b>{display_name}:</b> {value_text}"
            )
        else:
            html = f"<b>{display_name}:</b> {value_text}"

        self.hover_text.setHtml(html)

        self.hover_point.setData(
            [nearest["x"]],
            [nearest["y"]],
            brush=pg.mkBrush(*color),
            pen=pg.mkPen(0, 0, 0, width=1)
        )
        self.hover_point.show()

        self.hover_text.setPos(nearest["x"], nearest["y"])
        self.hover_text.show()

    def _hide_hover_items(self):
        """
        隐藏鼠标悬停提示。
        """
        if self.hover_text is not None:
            self.hover_text.hide()

        if self.hover_point is not None:
            self.hover_point.hide()

    def export_plot_image(self, file_path):
        """
        导出当前线图为图片。
        """
        if not file_path:
            print("export_plot_image failed: file_path is empty.")
            return False

        try:
            file_path = str(file_path)

            root, ext = os.path.splitext(file_path)
            if ext == "":
                file_path = file_path + ".png"

            folder = os.path.dirname(file_path)
            if folder and not os.path.exists(folder):
                os.makedirs(folder, exist_ok=True)

            pixmap = self.grab()
            ok = pixmap.save(file_path)

            if not ok:
                print(f"export_plot_image failed: cannot save to {file_path}")
                return False

            print(f"Plot image exported: {file_path}")
            return True

        except Exception as exc:
            print(f"export_plot_image error: {exc}")
            return False