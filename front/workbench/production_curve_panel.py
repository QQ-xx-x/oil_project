# -*- coding: utf-8 -*-
"""Reusable production curve panel backed by the visual widgets."""

import os

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QCheckBox, QColorDialog, QComboBox, QDoubleSpinBox, QFileDialog, QFrame,
    QHBoxLayout, QLabel, QPushButton, QSplitter, QVBoxLayout, QWidget,
)

try:
    from visual.production_curve_plot import ProductionCurvePlotWidget
    from visual.production_curve_table import ProductionCurveTableWidget
    PRODUCTION_CURVE_IMPORT_ERROR = ""
except Exception as exc:  # pragma: no cover - depends on optional runtime deps.
    ProductionCurvePlotWidget = None
    ProductionCurveTableWidget = None
    PRODUCTION_CURVE_IMPORT_ERROR = str(exc)


class ProductionCurvePanel(QWidget):
    """Plot + table adapter for output_sim production CSV files."""

    DEFAULT_PROPERTIES = ["CumWater", "CumGas"]
    CSV_CANDIDATES = [
        "output_sim_lgr_noWR.csv",
        "output_sim_lgr_WR.csv",
        "output_sim.csv",
        "output_sim_lgr.csv",
    ]

    def __init__(self, parent=None, compact=False):
        super().__init__(parent)
        self.csv_path = ""
        self.selected_properties = list(self.DEFAULT_PROPERTIES)
        self.compact = bool(compact)
        self.property_checkboxes = {}
        self._updating_selector = False
        self._updating_time_range = False
        self._updating_style_controls = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.message_label = QLabel()
        self.message_label.setObjectName("modulePreviewDescription")
        self.message_label.setWordWrap(True)
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.hide()
        layout.addWidget(self.message_label)

        self.selector_frame = QFrame()
        self.selector_frame.setObjectName("productionCurveSelector")
        selector_layout = QHBoxLayout(self.selector_frame)
        selector_layout.setContentsMargins(6, 4, 6, 4)
        selector_layout.setSpacing(8)
        self.selector_layout = selector_layout
        self.refresh_button = QPushButton("刷新")
        self.refresh_button.setObjectName("modulePreviewResultButton")
        self.refresh_button.clicked.connect(self.refresh_data)
        self.select_all_button = QPushButton("全选")
        self.select_all_button.setObjectName("modulePreviewResultButton")
        self.select_all_button.clicked.connect(lambda: self._set_all_properties_checked(True))
        self.clear_button = QPushButton("清空")
        self.clear_button.setObjectName("modulePreviewResultButton")
        self.clear_button.clicked.connect(lambda: self._set_all_properties_checked(False))
        self.follow_table_checkbox = QCheckBox("表格跟随选择")
        self.follow_table_checkbox.stateChanged.connect(
            lambda checked: self._refresh_table_columns())
        self.start_time_combo = QComboBox()
        self.start_time_combo.setMinimumWidth(86)
        self.start_time_combo.currentIndexChanged.connect(self._on_time_range_changed)
        self.end_time_combo = QComboBox()
        self.end_time_combo.setMinimumWidth(86)
        self.end_time_combo.currentIndexChanged.connect(self._on_time_range_changed)
        self.reset_view_button = QPushButton("重置")
        self.reset_view_button.setObjectName("modulePreviewResultButton")
        self.reset_view_button.clicked.connect(self._reset_time_range_and_view)
        self.export_button = QPushButton("导出")
        self.export_button.setObjectName("modulePreviewResultButton")
        self.export_button.clicked.connect(self._choose_export_path)
        self.style_property_combo = QComboBox()
        self.style_property_combo.setMinimumWidth(110)
        self.style_property_combo.currentIndexChanged.connect(self._on_style_property_changed)
        self.line_style_combo = QComboBox()
        self.line_style_combo.setMinimumWidth(82)
        self.line_style_combo.currentIndexChanged.connect(self._on_curve_line_style_changed)
        self.line_width_spin = QDoubleSpinBox()
        self.line_width_spin.setRange(0.5, 8.0)
        self.line_width_spin.setDecimals(1)
        self.line_width_spin.setSingleStep(0.1)
        self.line_width_spin.setValue(1.2)
        self.line_width_spin.setMinimumWidth(64)
        self.line_width_spin.valueChanged.connect(self._on_curve_width_changed)
        self.color_button = QPushButton("颜色")
        self.color_button.setObjectName("modulePreviewResultButton")
        self.color_button.clicked.connect(self._choose_curve_color)
        self.reset_style_button = QPushButton("重置样式")
        self.reset_style_button.setObjectName("modulePreviewResultButton")
        self.reset_style_button.clicked.connect(self._reset_current_curve_style)
        self.selector_frame.hide()
        layout.addWidget(self.selector_frame)

        self.plot_widget = None
        self.table_widget = None
        self.splitter = None

        if self._visual_widgets_available():
            self.plot_widget = ProductionCurvePlotWidget(self)
            self.table_widget = ProductionCurveTableWidget(self)
            self.splitter = QSplitter(Qt.Vertical, self)
            self.splitter.addWidget(self.plot_widget)
            self.splitter.addWidget(self.table_widget)
            if self.compact:
                self.splitter.setSizes([280, 180])
                self.table_widget.setMaximumHeight(220)
            else:
                self.splitter.setSizes([520, 260])
            layout.addWidget(self.splitter, 1)

            self.table_widget.row_selected.connect(
                self.plot_widget.highlight_time_index)
            self.plot_widget.point_selected.connect(
                self.table_widget.select_row_by_index)
        else:
            self._show_message(
                "生产曲线控件不可用：缺少 pyqtgraph。请先安装 pyqtgraph 后重启应用。"
            )

    def _visual_widgets_available(self):
        return ProductionCurvePlotWidget is not None and ProductionCurveTableWidget is not None

    def load_from_project(self, project_state, result_store=None):
        csv_path = self.find_project_csv(project_state, result_store)
        if not csv_path:
            self._show_message(
                "当前工程未找到 output_sim_lgr_noWR.csv，需要先运行/加载结果。"
            )
            return False
        return self.load_from_csv(csv_path)

    def load_from_csv(self, csv_path):
        self.csv_path = os.path.abspath(csv_path or "") if csv_path else ""
        if not self._visual_widgets_available():
            self._show_message(
                "生产曲线控件不可用：缺少 pyqtgraph。请先安装 pyqtgraph 后重启应用。"
            )
            return False
        if not self.csv_path or not os.path.exists(self.csv_path):
            self._show_message(
                "当前工程未找到 output_sim_lgr_noWR.csv，需要先运行/加载结果。"
            )
            return False

        ok = self.plot_widget.load_data_from_csv(self.csv_path)
        if not ok or not self.plot_widget.data:
            self._show_message(f"生产曲线 CSV 读取失败：{self.csv_path}")
            return False

        self.message_label.hide()
        self.selector_frame.show()
        if self.splitter is not None:
            self.splitter.show()
        self.table_widget.set_data(self.plot_widget.data)
        available = self.plot_widget.get_available_property_keys()
        self.selected_properties = self._default_selected_properties(available)
        self._build_property_selector(available)
        self._populate_style_controls(available)
        self._populate_time_range_controls()
        self._refresh_table_columns()
        self.plot_widget.plot_selected_properties(self.selected_properties)
        return True

    def refresh_data(self):
        if self.csv_path:
            return self.load_from_csv(self.csv_path)
        return False

    def set_selected_properties(self, properties):
        self.selected_properties = list(properties or [])
        self._sync_property_checkboxes()
        if self.plot_widget is not None and self.plot_widget.data:
            self.plot_widget.plot_selected_properties(self.selected_properties)
            self._refresh_table_columns()

    def reset_view(self):
        if self.plot_widget is not None:
            self.plot_widget.reset_view()

    def _reset_time_range_and_view(self):
        self._updating_time_range = True
        if self.start_time_combo.count():
            self.start_time_combo.setCurrentIndex(0)
        if self.end_time_combo.count():
            self.end_time_combo.setCurrentIndex(self.end_time_combo.count() - 1)
        self._updating_time_range = False
        if self.plot_widget is not None:
            self.plot_widget.clear_time_range()
            self.plot_widget.reset_view()

    def export_plot_image(self, path):
        if self.plot_widget is None:
            return False
        return self.plot_widget.export_plot_image(path)

    def _choose_export_path(self):
        if self.plot_widget is None or not self.plot_widget.data:
            return
        default_name = "production_curve.png"
        if self.csv_path:
            stem = os.path.splitext(os.path.basename(self.csv_path))[0]
            default_name = f"{stem}_curve.png"
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出生产曲线",
            default_name,
            "PNG 图像 (*.png);;JPEG 图像 (*.jpg *.jpeg);;所有文件 (*.*)",
        )
        if file_path:
            self.export_plot_image(file_path)

    def _show_message(self, message):
        if self.splitter is not None:
            self.splitter.hide()
        self.selector_frame.hide()
        self.message_label.setText(message)
        self.message_label.show()

    def _build_property_selector(self, available_properties):
        persistent_widgets = {
            self.refresh_button,
            self.select_all_button,
            self.clear_button,
            self.follow_table_checkbox,
            self.start_time_combo,
            self.end_time_combo,
            self.reset_view_button,
            self.export_button,
            self.style_property_combo,
            self.line_style_combo,
            self.line_width_spin,
            self.color_button,
            self.reset_style_button,
        }
        while self.selector_layout.count():
            item = self.selector_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                if widget in persistent_widgets:
                    widget.setParent(None)
                else:
                    widget.deleteLater()

        self.property_checkboxes = {}
        self.selector_layout.addWidget(QLabel("曲线"))
        self._updating_selector = True
        for key in available_properties:
            checkbox = QCheckBox(self._property_display_name(key))
            checkbox.setProperty("property_key", key)
            checkbox.setChecked(key in self.selected_properties)
            checkbox.stateChanged.connect(self._on_property_selection_changed)
            self.property_checkboxes[key] = checkbox
            self.selector_layout.addWidget(checkbox)
        self._updating_selector = False
        self.selector_layout.addStretch()
        self.selector_layout.addWidget(QLabel("样式"))
        self.selector_layout.addWidget(self.style_property_combo)
        self.selector_layout.addWidget(self.line_style_combo)
        self.selector_layout.addWidget(self.line_width_spin)
        self.selector_layout.addWidget(self.color_button)
        self.selector_layout.addWidget(self.reset_style_button)
        self.selector_layout.addWidget(QLabel("时间"))
        self.selector_layout.addWidget(self.start_time_combo)
        self.selector_layout.addWidget(QLabel("-"))
        self.selector_layout.addWidget(self.end_time_combo)
        self.selector_layout.addWidget(self.follow_table_checkbox)
        self.selector_layout.addWidget(self.refresh_button)
        self.selector_layout.addWidget(self.select_all_button)
        self.selector_layout.addWidget(self.clear_button)
        self.selector_layout.addWidget(self.reset_view_button)
        if not self.compact:
            self.selector_layout.addWidget(self.export_button)

    def _sync_property_checkboxes(self):
        if not self.property_checkboxes:
            return
        self._updating_selector = True
        selected = set(self.selected_properties)
        for key, checkbox in self.property_checkboxes.items():
            checkbox.setChecked(key in selected)
        self._updating_selector = False

    def _populate_style_controls(self, available_properties):
        enabled = bool(self.plot_widget is not None and available_properties)
        self._set_style_widgets_enabled(enabled)
        self._updating_style_controls = True
        self.style_property_combo.clear()
        self.line_style_combo.clear()
        if self.plot_widget is not None:
            for key in available_properties:
                self.style_property_combo.addItem(self._property_display_name(key), key)
            for style_key, display_name in self.plot_widget.get_available_line_styles():
                self.line_style_combo.addItem(display_name, style_key)
        self._updating_style_controls = False
        self._sync_style_controls_from_curve()

    def _set_style_widgets_enabled(self, enabled):
        for widget in (
            self.style_property_combo,
            self.line_style_combo,
            self.line_width_spin,
            self.color_button,
            self.reset_style_button,
        ):
            widget.setEnabled(bool(enabled))

    def _current_style_property_key(self):
        key = self.style_property_combo.currentData()
        if key:
            return str(key)
        return self.style_property_combo.currentText().strip()

    def _on_style_property_changed(self, *args):
        if self._updating_style_controls:
            return
        self._sync_style_controls_from_curve()

    def _on_curve_line_style_changed(self, *args):
        if self._updating_style_controls or self.plot_widget is None:
            return
        key = self._current_style_property_key()
        line_style = self.line_style_combo.currentData()
        if key and line_style:
            self.plot_widget.set_curve_line_style(key, line_style)

    def _on_curve_width_changed(self, value):
        if self._updating_style_controls or self.plot_widget is None:
            return
        key = self._current_style_property_key()
        if key:
            self.plot_widget.set_curve_width(key, float(value))

    def _choose_curve_color(self):
        if self.plot_widget is None:
            return
        key = self._current_style_property_key()
        if not key:
            return
        style = self.plot_widget.get_curve_style(key) or {}
        initial = self._qcolor_from_tuple(style.get("color"))
        color = QColorDialog.getColor(initial, self, "选择曲线颜色")
        if not color.isValid():
            return
        self.plot_widget.set_curve_color(key, color)
        self._set_color_button(color)

    def _reset_current_curve_style(self):
        if self.plot_widget is None:
            return
        key = self._current_style_property_key()
        if not key:
            return
        self.plot_widget.reset_curve_style(key)
        self._sync_style_controls_from_curve()

    def _sync_style_controls_from_curve(self):
        if self.plot_widget is None or self.style_property_combo.count() <= 0:
            self._set_style_widgets_enabled(False)
            return
        self._set_style_widgets_enabled(True)
        key = self._current_style_property_key()
        style = self.plot_widget.get_curve_style(key) or {}
        self._updating_style_controls = True
        line_style = style.get("line_style")
        line_index = self.line_style_combo.findData(line_style)
        if line_index >= 0:
            self.line_style_combo.setCurrentIndex(line_index)
        width = style.get("width")
        try:
            self.line_width_spin.setValue(float(width))
        except (TypeError, ValueError):
            pass
        self._set_color_button(self._qcolor_from_tuple(style.get("color")))
        self._updating_style_controls = False

    def _set_color_button(self, color):
        if not isinstance(color, QColor) or not color.isValid():
            color = QColor(0, 0, 0)
        self.color_button.setStyleSheet(
            "QPushButton {"
            f"background-color: {color.name()};"
            "color: white;"
            "border: 1px solid #8a8f98;"
            "padding: 2px 8px;"
            "}"
        )

    def _qcolor_from_tuple(self, value):
        if isinstance(value, QColor):
            return value
        if isinstance(value, (tuple, list)) and len(value) >= 3:
            try:
                return QColor(int(value[0]), int(value[1]), int(value[2]))
            except (TypeError, ValueError):
                return QColor(0, 0, 0)
        return QColor(0, 0, 0)

    def _on_property_selection_changed(self):
        if self._updating_selector:
            return
        self.selected_properties = self._selected_checkbox_keys()
        if self.plot_widget is not None and self.plot_widget.data:
            self.plot_widget.plot_selected_properties(self.selected_properties)
        self._refresh_table_columns()

    def _set_all_properties_checked(self, checked):
        if not self.property_checkboxes:
            return
        self._updating_selector = True
        for checkbox in self.property_checkboxes.values():
            checkbox.setChecked(bool(checked))
        self._updating_selector = False
        self.selected_properties = self._selected_checkbox_keys()
        if self.plot_widget is not None and self.plot_widget.data:
            self.plot_widget.plot_selected_properties(self.selected_properties)
        self._refresh_table_columns()

    def _selected_checkbox_keys(self):
        return [
            key for key, checkbox in self.property_checkboxes.items()
            if checkbox.isChecked()
        ]

    def _refresh_table_columns(self):
        if self.table_widget is None or not self.table_widget.data:
            return
        if self.follow_table_checkbox.isChecked():
            self.table_widget.show_selected_properties(self.selected_properties)
        else:
            self.table_widget.show_all_properties()

    def _default_selected_properties(self, available_properties):
        available = list(available_properties or [])
        preferred = [
            key for key in self.DEFAULT_PROPERTIES
            if key in available
        ]
        if preferred:
            return preferred
        return [
            key for key in available
            if key not in {"BHP", "AvgPressure"}
        ] or available

    def _populate_time_range_controls(self):
        if self.plot_widget is None:
            return
        labels = self.plot_widget.get_time_labels()
        self._updating_time_range = True
        self.start_time_combo.clear()
        self.end_time_combo.clear()
        self.start_time_combo.addItems(labels)
        self.end_time_combo.addItems(labels)
        if labels:
            self.start_time_combo.setCurrentIndex(0)
            self.end_time_combo.setCurrentIndex(len(labels) - 1)
        self._updating_time_range = False
        if self.plot_widget is not None:
            self.plot_widget.clear_time_range()

    def _on_time_range_changed(self):
        if self._updating_time_range:
            return
        if self.plot_widget is None or not self.plot_widget.data:
            return
        start_index = self.start_time_combo.currentIndex()
        end_index = self.end_time_combo.currentIndex()
        if start_index < 0 or end_index < 0:
            return
        self.plot_widget.set_time_range_by_index(start_index, end_index)

    def _property_display_name(self, key):
        if self.plot_widget is None:
            return str(key)
        return self.plot_widget.property_display_names.get(key, key)

    @classmethod
    def find_project_csv(cls, project_state, result_store=None):
        direct_paths = []
        if result_store is not None:
            output_path = getattr(result_store, "output_sim_path", "") or ""
            if output_path:
                direct_paths.append(output_path)

        search_dirs = []
        if result_store is not None:
            for attr in ("output_sim_path", "result_json_path"):
                path = getattr(result_store, attr, "") or ""
                if path:
                    search_dirs.append(os.path.dirname(os.path.abspath(path)))
            project_root = getattr(result_store, "project_root", "") or ""
            if project_root:
                search_dirs.append(project_root)

        if project_state is not None:
            for attr in ("project_file_path", "case_dataset_path", "case_data_path"):
                path = getattr(project_state, attr, "") or ""
                if not path:
                    continue
                if os.path.isdir(path):
                    search_dirs.append(path)
                else:
                    search_dirs.append(os.path.dirname(os.path.abspath(path)))

        for directory in cls._unique_existing_dirs(search_dirs):
            path = cls._first_candidate_in_dir(directory)
            if path:
                return path

        for path in direct_paths:
            if path and os.path.exists(path):
                return os.path.abspath(path)
        return ""

    @classmethod
    def _first_candidate_in_dir(cls, directory):
        for name in cls.CSV_CANDIDATES:
            path = os.path.join(directory, name)
            if os.path.exists(path):
                return os.path.abspath(path)
        return ""

    @staticmethod
    def _unique_existing_dirs(paths):
        seen = set()
        for path in paths:
            if not path:
                continue
            directory = os.path.abspath(path)
            if directory in seen or not os.path.isdir(directory):
                continue
            seen.add(directory)
            yield directory


class ProductionCurveViewport(ProductionCurvePanel):
    """Workspace viewport wrapper for the production chart result."""

    def __init__(self, project_state=None, result_store=None, parent=None):
        super().__init__(parent)
        self.project_state = project_state
        self.result_store = result_store
        self.context_title = "生产曲线"
        self.context_detail = ""
        self.display_key = "production_curve"

    def set_project_context(self, project_state=None, result_store=None):
        if project_state is not None:
            self.project_state = project_state
        if result_store is not None:
            self.result_store = result_store

    def refresh_data(self):
        return self.load_from_project(self.project_state, self.result_store)

    def set_context(self, title, detail, display_key=None):
        self.context_title = title
        self.context_detail = detail
        if display_key:
            self.display_key = display_key
        if self.display_key == "production_curve":
            self.load_from_project(self.project_state, self.result_store)

    def set_chart_data(self, chart_key, data):
        if chart_key == "production_curve":
            self.load_from_project(self.project_state, self.result_store)

    def export_ui_state(self):
        return {
            "context_title": self.context_title,
            "context_detail": self.context_detail,
            "display_key": self.display_key,
            "csv_path": self.csv_path,
        }

    def restore_ui_state(self, state):
        if not isinstance(state, dict):
            return
        self.context_title = state.get("context_title") or self.context_title
        self.context_detail = state.get("context_detail") or self.context_detail
        self.display_key = state.get("display_key") or self.display_key
        csv_path = state.get("csv_path") or ""
        if csv_path and os.path.exists(csv_path):
            self.load_from_csv(csv_path)
        elif self.display_key == "production_curve":
            self.load_from_project(self.project_state, self.result_store)
