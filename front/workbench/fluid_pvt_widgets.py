# -*- coding: utf-8 -*-
"""流体与 PVT 模块的专用参数页面和曲线预览。"""

import copy
import math

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import (
    QAbstractItemView, QApplication, QButtonGroup, QFrame, QGridLayout,
    QGroupBox, QHeaderView, QHBoxLayout, QLabel, QMessageBox, QPushButton,
    QProgressBar, QRadioButton, QSplitter, QStackedWidget, QTableWidget,
    QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget,
)

from .chart_adapters import build_gas_pvt_curve_from_values
from .module_input_widgets import BusinessScalarEditor


PVT_MODE_TABLE = "table"
PVT_MODE_PARAMETERS = "parameters"
PVT_TABLE_COLUMNS = (
    ("pressure_bar", "压力 P (bar)"),
    ("bg", "体积系数 Bg"),
    ("viscosity_cp", "气体黏度 μg (cP)"),
)
PVT_CALCULATED_COLUMNS = (
    ("pressure_bar", "压力 P (bar)"),
    ("z", "偏差因子 Z"),
    ("bg", "体积系数 Bg"),
    ("viscosity_cp", "气体黏度 μg (cP)"),
)


def _value_at(values, path):
    current = values
    for part in str(path or "").split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _set_value(values, path, value):
    parts = str(path or "").split(".")
    current = values
    for part in parts[:-1]:
        child = current.get(part)
        if not isinstance(child, dict):
            child = {}
            current[part] = child
        current = child
    if parts:
        current[parts[-1]] = copy.deepcopy(value)


def _remove_value(values, path):
    parts = str(path or "").split(".")
    current = values
    for part in parts[:-1]:
        if not isinstance(current, dict) or part not in current:
            return
        current = current[part]
    if isinstance(current, dict) and parts:
        current.pop(parts[-1], None)


def _format_metric(value):
    if value is None:
        return "—"
    return f"{float(value):.6g}"


def _pvt_cell_text(row, key):
    text = row.get(f"{key}_text")
    if text not in (None, ""):
        return str(text)
    value = row.get(key)
    return "" if value is None else f"{float(value):.12g}"


def _normalize_pvt_header(text):
    normalized = str(text or "").strip().lower()
    for token in (
            " ", "\t", "_", "-", "/", "\\", "(", ")", "（", "）",
            "[", "]", "【", "】", "·"):
        normalized = normalized.replace(token, "")
    normalized = normalized.replace("μ", "u").replace("µ", "u")
    aliases = {
        "p": "pressure_bar",
        "pres": "pressure_bar",
        "pbar": "pressure_bar",
        "pressure": "pressure_bar",
        "pressurebar": "pressure_bar",
        "压力": "pressure_bar",
        "压力bar": "pressure_bar",
        "压力pbar": "pressure_bar",
        "z": "z",
        "zfactor": "z",
        "偏差因子": "z",
        "偏差因子z": "z",
        "气体偏差因子": "z",
        "气体偏差因子z": "z",
        "bg": "bg",
        "formationvolumefactor": "bg",
        "gasformationvolumefactor": "bg",
        "体积系数": "bg",
        "体积系数bg": "bg",
        "气体体积系数": "bg",
        "气体体积系数bg": "bg",
        "ug": "viscosity_cp",
        "visg": "viscosity_cp",
        "mug": "viscosity_cp",
        "viscosity": "viscosity_cp",
        "viscositycp": "viscosity_cp",
        "gasviscosity": "viscosity_cp",
        "gasviscositycp": "viscosity_cp",
        "黏度": "viscosity_cp",
        "粘度": "viscosity_cp",
        "气体黏度": "viscosity_cp",
        "气体粘度": "viscosity_cp",
        "气体黏度cp": "viscosity_cp",
        "气体粘度cp": "viscosity_cp",
        "气体黏度ugcp": "viscosity_cp",
        "气体粘度ugcp": "viscosity_cp",
    }
    return aliases.get(normalized)


def parse_pvt_clipboard_table(text):
    """解析 Excel/文本剪贴板，返回数据矩阵和可选的列名映射。"""

    raw_lines = str(text or "").replace("\r\n", "\n").replace(
        "\r", "\n").split("\n")
    while raw_lines and not raw_lines[-1].strip():
        raw_lines.pop()
    while raw_lines and not raw_lines[0].strip():
        raw_lines.pop(0)
    if not raw_lines:
        raise ValueError("剪贴板中没有可粘贴的数据。")

    matrix = []
    for line in raw_lines:
        if "\t" in line:
            cells = line.split("\t")
        elif "," in line:
            cells = line.split(",")
        else:
            cells = [line]
        matrix.append([cell.strip() for cell in cells])

    header_keys = [_normalize_pvt_header(cell) for cell in matrix[0]]
    has_header = (
        len(matrix[0]) >= 2
        and all(key is not None for key in header_keys)
        and len(set(header_keys)) == len(header_keys)
    )
    if has_header:
        matrix.pop(0)
    else:
        header_keys = None
    if not matrix or not any(any(cell for cell in row) for row in matrix):
        raise ValueError("剪贴板中只有表头，没有 PVT 数据。")
    if any(len(row) > len(PVT_CALCULATED_COLUMNS) for row in matrix):
        raise ValueError(
            "每行最多只能粘贴 P、Bg、μg 三列数据；"
            "旧版 P、Z、Bg、μg 四列也可兼容。")
    return matrix, header_keys


class _PVTDataTable(QTableWidget):
    """支持 Excel 剪贴板格式的 PVT 数据表。"""

    paste_requested = pyqtSignal(str)
    copy_requested = pyqtSignal()

    def __init__(self, rows, columns, parent=None):
        super().__init__(rows, columns, parent)
        self._paste_enabled = False

    def set_paste_enabled(self, enabled):
        self._paste_enabled = bool(enabled)

    def keyPressEvent(self, event):
        if self._paste_enabled and event.matches(QKeySequence.Paste):
            self.paste_requested.emit(QApplication.clipboard().text())
            return
        if event.matches(QKeySequence.Copy):
            self.copy_requested.emit()
            return
        if (self._paste_enabled
                and event.key() in (Qt.Key_Delete, Qt.Key_Backspace)):
            for item in self.selectedItems():
                item.setText("")
            return
        super().keyPressEvent(event)


class FluidParameterCard(QFrame):
    """带名称和编辑器的统一参数卡。"""

    def __init__(self, title, control, parent=None):
        super().__init__(parent)
        self.setObjectName("fluidParameterCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 9, 12, 10)
        layout.setSpacing(6)
        label = QLabel(title)
        label.setObjectName("fluidParameterTitle")
        layout.addWidget(label)
        layout.addWidget(control)


class FluidMetricCard(QFrame):
    """PVT 曲线顶部使用的小型只读指标卡。"""

    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setObjectName("fluidMetricCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(1)
        title_label = QLabel(title)
        title_label.setObjectName("fluidMetricTitle")
        self.value_label = QLabel("—")
        self.value_label.setObjectName("fluidMetricValue")
        layout.addWidget(title_label)
        layout.addWidget(self.value_label)

    def set_value(self, value):
        self.value_label.setText(str(value) if isinstance(value, str)
                                 else _format_metric(value))


class _EditableFluidPage(QWidget):
    """三个流体专属页面共享的编辑值收集逻辑。"""

    values_changed = pyqtSignal()

    def __init__(self, title, fields=(), parent=None):
        super().__init__(parent)
        self.group_title = title
        self.fields = tuple(fields or ())
        self.bindings = []
        self._controls = {}

    def _control(self, field, handler=None):
        control = BusinessScalarEditor(field)
        control.setObjectName("fluidParameterControl")
        if hasattr(control.editor, "setObjectName"):
            control.editor.setObjectName("fluidParameterEditor")
        control.value_changed.connect(handler or self.values_changed.emit)
        self._controls[field.key] = control
        self.bindings.append((field, control))
        return control

    def set_values(self, values, module_key):
        for field, control in self.bindings:
            control.set_value(_value_at(values, field.source_path))

    def collect_values(self, values):
        for field, control in self.bindings:
            if not field.editable:
                continue
            value = control.value()
            if value is None:
                _remove_value(values, field.source_path)
            else:
                _set_value(values, field.source_path, value)

    def refresh_derived(self, values, module_key):
        return None


class BasicFluidParametersPage(_EditableFluidPage):
    """组织气水模型中的水相基础参数和压力基准。"""

    def __init__(self, title, fields=(), parent=None):
        super().__init__(title, fields, parent)
        by_key = {field.key: field for field in self.fields}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 12, 16, 14)
        outer.setSpacing(12)
        title_label = QLabel(title)
        title_label.setObjectName("parameterTitle")
        outer.addWidget(title_label)

        properties = QGroupBox("流体性质")
        properties.setObjectName("fluidSection")
        grid = QGridLayout(properties)
        grid.setContentsMargins(14, 18, 14, 14)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(9)
        for column, text in enumerate(("参数", "水相")):
            label = QLabel(text)
            label.setObjectName("fluidTableHeader")
            label.setAlignment(Qt.AlignCenter)
            grid.addWidget(label, 0, column)
        for row, (label_text, water_key) in enumerate((
                ("黏度", "mu_w"),
                ("压缩系数", "cw")), start=1):
            label = QLabel(label_text)
            label.setObjectName("fluidRowLabel")
            grid.addWidget(label, row, 0)
            grid.addWidget(self._control(by_key[water_key]), row, 1)
        grid.setColumnStretch(1, 1)
        outer.addWidget(properties)

        reference = QGroupBox("压力基准")
        reference.setObjectName("fluidSection")
        reference_layout = QHBoxLayout(reference)
        reference_layout.setContentsMargins(14, 18, 14, 12)
        reference_control = self._control(by_key["p_ref"])
        reference_control.setMaximumWidth(310)
        reference_layout.addWidget(
            FluidParameterCard("参考压力", reference_control))
        reference_layout.addStretch()
        outer.addWidget(reference)

        outer.addStretch()


class GasCompositionPage(_EditableFluidPage):
    """使用卡片网格和实时总和状态展示气体组分。"""

    COMPOSITION_KEYS = (
        "mole_ch4", "mole_c2h6", "mole_c3h8", "mole_n2",
        "mole_co2", "mole_h2o", "mole_unknown",
    )

    def __init__(self, title, fields=(), parent=None):
        super().__init__(title, fields, parent)
        by_key = {field.key: field for field in self.fields}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 12, 16, 14)
        outer.setSpacing(12)
        title_label = QLabel(title)
        title_label.setObjectName("parameterTitle")
        outer.addWidget(title_label)

        conditions = QGroupBox("气藏条件")
        conditions.setObjectName("fluidSection")
        condition_layout = QHBoxLayout(conditions)
        condition_layout.setContentsMargins(14, 18, 14, 12)
        temperature = self._control(
            by_key["temperature_c"], self._on_value_changed)
        temperature.setMaximumWidth(310)
        condition_layout.addWidget(FluidParameterCard("气藏温度", temperature))
        condition_layout.addStretch()
        outer.addWidget(conditions)

        components = QGroupBox("摩尔组成")
        components.setObjectName("fluidSection")
        component_grid = QGridLayout(components)
        component_grid.setContentsMargins(14, 18, 14, 14)
        component_grid.setHorizontalSpacing(10)
        component_grid.setVerticalSpacing(10)
        labels = {
            "mole_ch4": "CH4",
            "mole_c2h6": "C2H6",
            "mole_c3h8": "C3H8",
            "mole_n2": "N2",
            "mole_co2": "CO2",
            "mole_h2o": "H2O",
            "mole_unknown": "其他组分",
        }
        for index, key in enumerate(self.COMPOSITION_KEYS):
            control = self._control(by_key[key], self._on_value_changed)
            component_grid.addWidget(
                FluidParameterCard(f"{labels[key]} 摩尔分数", control),
                index // 4, index % 4,
            )
        for column in range(4):
            component_grid.setColumnStretch(column, 1)
        outer.addWidget(components)

        total = QFrame()
        total.setObjectName("gasCompositionTotal")
        total_layout = QVBoxLayout(total)
        total_layout.setContentsMargins(12, 8, 12, 9)
        total_layout.setSpacing(5)
        self.total_status = QLabel("○ 尚未输入气体组分")
        self.total_status.setObjectName("gasCompositionStatus")
        total_layout.addWidget(self.total_status)
        self.total_progress = QProgressBar()
        self.total_progress.setObjectName("gasCompositionProgress")
        self.total_progress.setRange(0, 10000)
        self.total_progress.setTextVisible(False)
        self.total_progress.setFixedHeight(8)
        total_layout.addWidget(self.total_progress)
        outer.addWidget(total)
        outer.addStretch()

    def set_values(self, values, module_key):
        super().set_values(values, module_key)
        self._update_total()

    def _on_value_changed(self):
        self._update_total()
        self.values_changed.emit()

    def _update_total(self):
        numbers = []
        try:
            for key in self.COMPOSITION_KEYS:
                value = self._controls[key].value()
                if value is not None:
                    numbers.append(float(value))
        except (TypeError, ValueError):
            self._set_total_state("warning", "组分中存在无法计算的数值", 0.0)
            return
        if not numbers:
            self._set_total_state("empty", "○ 尚未输入气体组分", 0.0)
            return
        total = sum(numbers)
        if math.isclose(total, 1.0, rel_tol=1e-6, abs_tol=1e-6):
            self._set_total_state(
                "success", f"✓ 组分总和 {total:.4f}，校验通过", total)
        else:
            self._set_total_state(
                "warning",
                f"组分总和 {total:.4f}，与 1 相差 {abs(1.0 - total):.4f}",
                total,
            )

    def _set_total_state(self, state, text, total):
        self.total_status.setText(text)
        self.total_status.setProperty("state", state)
        self.total_progress.setProperty("state", state)
        self.total_progress.setValue(
            max(0, min(10000, int(round(total * 10000)))))
        for widget in (self.total_status, self.total_progress):
            widget.style().unpolish(widget)
            widget.style().polish(widget)


class PVTTablePage(_EditableFluidPage):
    """可粘贴表格或按参数计算的气体 PVT 数据页。"""

    REQUIRED_KEYS = (
        "temperature_c", "gas_table_pmin_bar",
        "gas_table_pmax_bar", "gas_table_n",
    )
    CHART_SPECS = (
        ("z", "P–Z", "Z", "#3f68b1"),
        ("bg", "P–Bg", "Bg", "#2f8f83"),
        ("viscosity_cp", "P–μg", "μg (cP)", "#d17a2f"),
    )

    def __init__(self, title, fields=(), parent=None):
        super().__init__(title, fields, parent)
        self._context_values = {}
        self._table_cells = []
        self._generated_rows = []
        self._active_rows = []
        self._available_chart_keys = []
        self._active_mode = PVT_MODE_PARAMETERS
        self._rendering_table = False
        self._loading_values = False
        by_key = {field.key: field for field in self.fields}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 12, 16, 14)
        outer.setSpacing(9)
        title_label = QLabel(title)
        title_label.setObjectName("parameterTitle")
        outer.addWidget(title_label)

        mode_group = QGroupBox("数据模式")
        mode_group.setObjectName("fluidSection")
        mode_layout = QHBoxLayout(mode_group)
        mode_layout.setContentsMargins(14, 16, 14, 9)
        self.mode_buttons = QButtonGroup(self)
        self.table_mode_radio = QRadioButton("表格粘贴")
        self.parameter_mode_radio = QRadioButton("参数计算")
        self.mode_buttons.addButton(self.table_mode_radio)
        self.mode_buttons.addButton(self.parameter_mode_radio)
        mode_layout.addWidget(self.table_mode_radio)
        mode_layout.addWidget(self.parameter_mode_radio)
        mode_layout.addStretch()
        self.table_mode_radio.toggled.connect(
            lambda checked: checked and self._select_mode(PVT_MODE_TABLE))
        self.parameter_mode_radio.toggled.connect(
            lambda checked: checked and self._select_mode(PVT_MODE_PARAMETERS))
        outer.addWidget(mode_group)

        self.settings_group = QGroupBox("参数计算设置")
        self.settings_group.setObjectName("fluidSection")
        settings_layout = QHBoxLayout(self.settings_group)
        settings_layout.setContentsMargins(14, 18, 14, 12)
        settings_layout.setSpacing(10)
        for key, label in (
                ("gas_table_pmin_bar", "最小压力"),
                ("gas_table_pmax_bar", "最大压力"),
                ("gas_table_n", "采样点数")):
            control = self._control(by_key[key], self._on_value_changed)
            settings_layout.addWidget(FluidParameterCard(label, control), 1)
        outer.addWidget(self.settings_group)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self._build_table_panel())
        splitter.addWidget(self._build_chart_panel())
        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 5)
        splitter.setSizes([470, 470])
        outer.addWidget(splitter, 1)

        self.parameter_mode_radio.setChecked(True)
        self._apply_mode()

    def _build_table_panel(self):
        group = QGroupBox("PVT 数据表")
        group.setObjectName("fluidSection")
        group.setMinimumWidth(280)
        layout = QVBoxLayout(group)
        layout.setContentsMargins(10, 15, 10, 9)
        layout.setSpacing(7)

        actions = QGridLayout()
        actions.setSpacing(6)
        self.paste_button = QPushButton("粘贴")
        self.paste_button.clicked.connect(self._paste_clipboard)
        actions.addWidget(self.paste_button, 0, 0)
        self.add_row_button = QPushButton("添加行")
        self.add_row_button.clicked.connect(self._add_table_row)
        actions.addWidget(self.add_row_button, 0, 1)
        self.delete_row_button = QPushButton("删除选中行")
        self.delete_row_button.clicked.connect(self._delete_selected_rows)
        actions.addWidget(self.delete_row_button, 0, 2)
        self.clear_table_button = QPushButton("清空")
        self.clear_table_button.clicked.connect(self._clear_table)
        actions.addWidget(self.clear_table_button, 1, 0)
        self.copy_table_button = QPushButton("复制表格")
        self.copy_table_button.clicked.connect(self._copy_table)
        actions.addWidget(self.copy_table_button, 1, 1)
        actions.setColumnStretch(2, 1)
        layout.addLayout(actions)

        self.table_note = QLabel(
            "从 Excel 复制 P、Bg、μg 三列后，选中起始单元格按 Ctrl+V；"
            "支持中英文表头，也可双击单元格输入。")
        self.table_note.setObjectName("parameterDescription")
        self.table_note.setWordWrap(True)
        layout.addWidget(self.table_note)

        self.data_table = _PVTDataTable(
            10, len(PVT_TABLE_COLUMNS), group)
        self.data_table.setObjectName("pvtEditableTable")
        self.data_table.setHorizontalHeaderLabels(
            [label for _key, label in PVT_TABLE_COLUMNS])
        self.data_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch)
        self.data_table.verticalHeader().setDefaultSectionSize(25)
        self.data_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.data_table.setSelectionBehavior(QAbstractItemView.SelectItems)
        self.data_table.setAlternatingRowColors(True)
        self.data_table.itemChanged.connect(self._table_item_changed)
        self.data_table.paste_requested.connect(self._paste_text)
        self.data_table.copy_requested.connect(self._copy_table)
        layout.addWidget(self.data_table, 1)

        self.table_status = QLabel("尚未生成或粘贴 PVT 数据")
        self.table_status.setObjectName("pvtTableStatus")
        self.table_status.setWordWrap(True)
        layout.addWidget(self.table_status)
        return group

    def _build_chart_panel(self):
        group = QGroupBox("PVT 曲线预览")
        group.setObjectName("fluidSection")
        group.setMinimumWidth(280)
        layout = QVBoxLayout(group)
        layout.setContentsMargins(10, 15, 10, 9)
        layout.setSpacing(7)

        metrics = QGridLayout()
        metrics.setSpacing(6)
        self.metric_cards = {}
        for index, (key, label) in enumerate((
                ("source", "数据来源"),
                ("point_count", "数据点"),
                ("pressure_range", "压力范围 (bar)"),
                ("current_min", "当前曲线最小值"),
                ("current_max", "当前曲线最大值"))):
            card = FluidMetricCard(label)
            metrics.addWidget(card, index // 3, index % 3)
            self.metric_cards[key] = card
        layout.addLayout(metrics)

        self.chart_stack = QStackedWidget()
        self.chart_placeholder = QLabel(
            "输入至少两行完整 PVT 数据后显示曲线")
        self.chart_placeholder.setObjectName("pvtChartPlaceholder")
        self.chart_placeholder.setAlignment(Qt.AlignCenter)
        self.chart_placeholder.setWordWrap(True)
        self.chart_stack.addWidget(self.chart_placeholder)

        self.chart_tabs = QTabWidget()
        self.chart_tabs.setObjectName("pvtChartTabs")
        self._charts = {}
        for key, tab_title, y_label, color in self.CHART_SPECS:
            figure = Figure(facecolor="white")
            canvas = FigureCanvas(figure)
            canvas.setObjectName(f"pvtChartCanvas_{key}")
            canvas.setMinimumHeight(210)
            self.chart_tabs.addTab(canvas, tab_title)
            self._charts[key] = {
                "figure": figure,
                "canvas": canvas,
                "y_label": y_label,
                "color": color,
            }
        self.chart_tabs.currentChanged.connect(
            self._update_current_metric_cards)
        self.chart_stack.addWidget(self.chart_tabs)
        layout.addWidget(self.chart_stack, 1)
        return group

    def set_values(self, values, module_key):
        self._loading_values = True
        try:
            self._context_values = copy.deepcopy(values or {})
            super().set_values(values, module_key)
            payload = (values or {}).get("gas_pvt_table") or {}
            saved_rows = (
                payload.get("rows") if isinstance(payload, dict) else [])
            self._table_cells = [
                [_pvt_cell_text(row, key) for key, _label in PVT_TABLE_COLUMNS]
                for row in (saved_rows or []) if isinstance(row, dict)
            ]
            mode = str(
                (values or {}).get("pvt_input_mode")
                or PVT_MODE_PARAMETERS).strip().lower()
            if mode not in {PVT_MODE_TABLE, PVT_MODE_PARAMETERS}:
                mode = PVT_MODE_PARAMETERS
            self.table_mode_radio.blockSignals(True)
            self.parameter_mode_radio.blockSignals(True)
            self.table_mode_radio.setChecked(mode == PVT_MODE_TABLE)
            self.parameter_mode_radio.setChecked(mode == PVT_MODE_PARAMETERS)
            self.table_mode_radio.blockSignals(False)
            self.parameter_mode_radio.blockSignals(False)
            self._active_mode = mode
            self._apply_mode()
        finally:
            self._loading_values = False

    def collect_values(self, values):
        super().collect_values(values)
        values["pvt_input_mode"] = self._active_mode
        if self._active_mode == PVT_MODE_TABLE:
            self._capture_table_cells()
            rows = self._read_table_rows(minimum_points=2)
        else:
            try:
                rows = self._build_parameter_rows(values)
            except (TypeError, ValueError, OverflowError):
                rows = []
        if rows:
            stored_columns = (
                PVT_CALCULATED_COLUMNS
                if self._active_mode == PVT_MODE_PARAMETERS
                else PVT_TABLE_COLUMNS
            )
            values["gas_pvt_table"] = {
                "schema_version": 2,
                "source_mode": self._active_mode,
                "columns": [key for key, _label in stored_columns],
                "rows": copy.deepcopy(rows),
            }
        else:
            values.pop("gas_pvt_table", None)

    def refresh_derived(self, values, module_key):
        self._context_values = copy.deepcopy(values or {})
        if self._active_mode == PVT_MODE_PARAMETERS:
            self._update_parameter_preview()
        else:
            self._update_table_preview()

    def _select_mode(self, mode):
        if self._loading_values or mode == self._active_mode:
            return
        if self._active_mode == PVT_MODE_TABLE:
            self._capture_table_cells()
        self._active_mode = mode
        self._apply_mode()
        self.values_changed.emit()

    def _apply_mode(self):
        table_mode = self._active_mode == PVT_MODE_TABLE
        self.settings_group.setVisible(not table_mode)
        for button in (
                self.paste_button, self.add_row_button,
                self.delete_row_button, self.clear_table_button):
            button.setEnabled(table_mode)
        self.data_table.set_paste_enabled(table_mode)
        if table_mode:
            self.table_note.setText(
                "从 Excel 复制 P、Bg、μg 三列后，选中起始单元格按 "
                "Ctrl+V；支持中英文表头，也可双击单元格输入。")
            self._render_table_cells()
            self._update_table_preview()
        else:
            self.table_note.setText(
                "表格由气藏温度、气体组分和压力设置自动计算；"
                "计算结果只读，但可点击“复制表格”粘贴到 Excel。")
            self._update_parameter_preview()

    def _on_value_changed(self):
        if self._loading_values:
            return
        if self._active_mode == PVT_MODE_PARAMETERS:
            self._update_parameter_preview()
        self.values_changed.emit()

    def _preview_values(self):
        values = copy.deepcopy(self._context_values)
        for field, control in self.bindings:
            value = control.value()
            if value is None:
                _remove_value(values, field.source_path)
            else:
                _set_value(values, field.source_path, value)
        return values

    def _build_parameter_rows(self, values):
        if any(values.get(key) is None for key in self.REQUIRED_KEYS):
            raise ValueError("请先完整填写温度、气体组分和 PVT 表设置。")
        curve = build_gas_pvt_curve_from_values(values)
        points = list(curve.get("points") or [])
        pvdg_rows = list(curve.get("pvdg_rows") or [])
        if not points or len(points) != len(pvdg_rows):
            raise ValueError("当前参数没有生成完整的 PVT 数据。")
        rows = []
        for point, pvdg in zip(points, pvdg_rows):
            pressure, z_value = point
            pvdg_pressure, bg, viscosity = pvdg
            if not math.isclose(
                    float(pressure), float(pvdg_pressure),
                    rel_tol=1e-10, abs_tol=1e-10):
                raise ValueError("PVT 计算结果中的压力列不一致。")
            rows.append({
                "pressure_bar": float(pressure),
                "z": float(z_value),
                "bg": float(bg),
                "viscosity_cp": float(viscosity),
            })
        return rows

    def _update_parameter_preview(self):
        try:
            rows = self._build_parameter_rows(self._preview_values())
        except (TypeError, ValueError, OverflowError) as exc:
            self._generated_rows = []
            self._render_data_rows([], editable=False)
            message = str(exc) or "当前参数无法生成 PVT 数据。"
            self.table_status.setText(message)
            self._show_placeholder(message)
            return
        self._generated_rows = rows
        self._render_data_rows(rows, editable=False)
        self.table_status.setText(
            f"已根据当前参数生成 {len(rows)} 行 PVT 数据；表格只读，可复制。")
        self._render_charts(rows, "参数计算")

    def _render_table_cells(self):
        row_count = max(10, len(self._table_cells) + 1)
        self._rendering_table = True
        self.data_table.setUpdatesEnabled(False)
        try:
            self.data_table.clearContents()
            self.data_table.setRowCount(row_count)
            for row_index in range(row_count):
                source = (
                    self._table_cells[row_index]
                    if row_index < len(self._table_cells) else ())
                for column in range(len(PVT_TABLE_COLUMNS)):
                    text = source[column] if column < len(source) else ""
                    item = QTableWidgetItem(str(text))
                    item.setTextAlignment(Qt.AlignCenter)
                    self.data_table.setItem(row_index, column, item)
        finally:
            self.data_table.setUpdatesEnabled(True)
            self._rendering_table = False

    def _render_data_rows(self, rows, editable=False):
        row_count = max(1, len(rows))
        self._rendering_table = True
        self.data_table.setUpdatesEnabled(False)
        try:
            self.data_table.clearContents()
            self.data_table.setRowCount(row_count)
            for row_index, row in enumerate(rows):
                for column, (key, _label) in enumerate(PVT_TABLE_COLUMNS):
                    item = QTableWidgetItem(_pvt_cell_text(row, key))
                    item.setTextAlignment(Qt.AlignCenter)
                    if not editable:
                        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                    self.data_table.setItem(row_index, column, item)
        finally:
            self.data_table.setUpdatesEnabled(True)
            self._rendering_table = False

    def _table_item_changed(self, _item):
        if self._rendering_table or self._active_mode != PVT_MODE_TABLE:
            return
        self._capture_table_cells()
        self._ensure_trailing_blank_row()
        self._update_table_preview()
        self.values_changed.emit()

    def _capture_table_cells(self):
        if self._active_mode != PVT_MODE_TABLE:
            return
        cells = []
        for row_index in range(self.data_table.rowCount()):
            row = []
            for column in range(len(PVT_TABLE_COLUMNS)):
                item = self.data_table.item(row_index, column)
                row.append(item.text().strip() if item is not None else "")
            cells.append(row)
        while cells and not any(cells[-1]):
            cells.pop()
        self._table_cells = cells

    def _ensure_trailing_blank_row(self):
        self._rendering_table = True
        try:
            if self.data_table.rowCount() < 10:
                self.data_table.setRowCount(10)
            last_row = self.data_table.rowCount() - 1
            if any(
                    self.data_table.item(last_row, column) is not None
                    and self.data_table.item(
                        last_row, column).text().strip()
                    for column in range(len(PVT_TABLE_COLUMNS))):
                self.data_table.insertRow(self.data_table.rowCount())
                last_row += 1
            for column in range(len(PVT_TABLE_COLUMNS)):
                if self.data_table.item(last_row, column) is None:
                    self.data_table.setItem(
                        last_row, column, QTableWidgetItem(""))
        finally:
            self._rendering_table = False

    def _read_table_rows(self, minimum_points=0):
        rows = []
        previous_pressure = None
        for row_index, cells in enumerate(self._table_cells, 1):
            texts = [
                str(value).strip()
                for value in cells[:len(PVT_TABLE_COLUMNS)]
            ]
            if not any(texts):
                continue
            if len(texts) < len(PVT_TABLE_COLUMNS) or not all(texts):
                raise ValueError(
                    f"PVT 表格第 {row_index} 行不完整，请填写 P、Bg、μg。")
            try:
                numbers = [float(text) for text in texts]
            except ValueError as exc:
                raise ValueError(
                    f"PVT 表格第 {row_index} 行包含非数字内容。") from exc
            if not all(math.isfinite(value) for value in numbers):
                raise ValueError(
                    f"PVT 表格第 {row_index} 行必须填写有限数字。")
            if not all(value > 0.0 for value in numbers):
                raise ValueError(
                    f"PVT 表格第 {row_index} 行的 P、Bg、μg 必须大于零。")
            if previous_pressure is not None and numbers[0] <= previous_pressure:
                raise ValueError(
                    f"PVT 表格第 {row_index} 行的压力必须严格大于上一行。")
            previous_pressure = numbers[0]
            row = {}
            for column, (key, _label) in enumerate(PVT_TABLE_COLUMNS):
                row[key] = numbers[column]
                row[f"{key}_text"] = texts[column]
            rows.append(row)
        if len(rows) < int(minimum_points):
            raise ValueError("PVT 表格至少需要两行完整数据。")
        return rows

    def _update_table_preview(self):
        try:
            rows = self._read_table_rows()
        except (TypeError, ValueError, OverflowError) as exc:
            message = str(exc)
            self.table_status.setText(message)
            self._show_placeholder(message)
            return
        if not rows:
            message = "请从 Excel 粘贴 P、Bg、μg 三列数据。"
            self.table_status.setText(message)
            self._show_placeholder(message)
        elif len(rows) == 1:
            message = "已有 1 行有效数据；保存和预览至少需要 2 行。"
            self.table_status.setText(message)
            self._show_placeholder(message)
        else:
            self.table_status.setText(
                f"已有 {len(rows)} 行有效 PVT 数据；数据按输入原值保存。")
            self._render_charts(rows, "表格粘贴")

    def _render_charts(self, rows, source):
        valid_rows = [
            row for row in rows or [] if isinstance(row, dict)
            and all(row.get(key) is not None for key, _ in PVT_TABLE_COLUMNS)
        ]
        if len(valid_rows) < 2:
            self._show_placeholder("输入至少两行完整 PVT 数据后显示曲线。")
            return
        pressures = [float(row["pressure_bar"]) for row in valid_rows]
        available_chart_keys = []
        for index, (key, _tab_title, y_label, color) in enumerate(
                self.CHART_SPECS):
            has_data = all(row.get(key) is not None for row in valid_rows)
            self.chart_tabs.setTabVisible(index, has_data)
            if not has_data:
                continue
            available_chart_keys.append(key)
            values = [float(row[key]) for row in valid_rows]
            chart = self._charts[key]
            figure = chart["figure"]
            figure.clear()
            axis = figure.add_subplot(111)
            axis.set_facecolor("#ffffff")
            axis.plot(
                pressures, values, color=color, linewidth=2.1,
                marker="o" if len(values) <= 60 else None,
                markersize=3.2, label=y_label,
            )
            axis.fill_between(
                pressures, values, min(values), color=color, alpha=0.10)
            axis.set_xlabel("P (bar)")
            axis.set_ylabel(y_label)
            axis.grid(True, linestyle="--", linewidth=0.8, alpha=0.38)
            axis.legend(loc="best", frameon=False)
            axis.margins(x=0.02, y=0.12)
            for spine in axis.spines.values():
                spine.set_color("#9ba8b8")
            figure.tight_layout(pad=1.1)
            chart["canvas"].draw_idle()

        self._active_rows = copy.deepcopy(valid_rows)
        self._available_chart_keys = available_chart_keys
        self.metric_cards["source"].set_value(source)
        self.metric_cards["point_count"].set_value(str(len(valid_rows)))
        self.metric_cards["pressure_range"].set_value(
            f"{pressures[0]:.6g} – {pressures[-1]:.6g}")
        current_index = self.chart_tabs.currentIndex()
        if (current_index < 0
                or self.CHART_SPECS[current_index][0]
                not in self._available_chart_keys):
            for index, (key, *_rest) in enumerate(self.CHART_SPECS):
                if key in self._available_chart_keys:
                    self.chart_tabs.setCurrentIndex(index)
                    break
        self._update_current_metric_cards()
        self.chart_stack.setCurrentWidget(self.chart_tabs)

    def _update_current_metric_cards(self, _index=None):
        if not self._active_rows:
            self.metric_cards["current_min"].set_value(None)
            self.metric_cards["current_max"].set_value(None)
            return
        index = max(0, self.chart_tabs.currentIndex())
        key = self.CHART_SPECS[index][0]
        if key not in self._available_chart_keys:
            self.metric_cards["current_min"].set_value(None)
            self.metric_cards["current_max"].set_value(None)
            return
        values = [float(row[key]) for row in self._active_rows]
        self.metric_cards["current_min"].set_value(min(values))
        self.metric_cards["current_max"].set_value(max(values))

    def _show_placeholder(self, message):
        self._active_rows = []
        self._available_chart_keys = []
        self.chart_placeholder.setText(
            str(message or "输入有效数据后显示 PVT 曲线。"))
        for card in self.metric_cards.values():
            card.set_value(None)
        self.chart_stack.setCurrentWidget(self.chart_placeholder)

    def _paste_clipboard(self):
        self._paste_text(QApplication.clipboard().text())

    def _paste_text(self, text):
        if self._active_mode != PVT_MODE_TABLE:
            return
        try:
            matrix, header_keys = parse_pvt_clipboard_table(text)
        except ValueError as exc:
            QMessageBox.warning(self, "粘贴失败", str(exc))
            return

        key_to_column = {
            key: index for index, (key, _label)
            in enumerate(PVT_TABLE_COLUMNS)
        }
        start_row = max(0, self.data_table.currentRow())
        start_column = max(0, self.data_table.currentColumn())
        if header_keys:
            target_columns = [
                key_to_column.get(key) for key in header_keys
            ]
        else:
            widest = max(len(row) for row in matrix)
            if widest == len(PVT_CALCULATED_COLUMNS):
                if start_column != 0:
                    QMessageBox.warning(
                        self, "粘贴失败",
                        "旧版 P、Z、Bg、μg 四列数据请从第一列开始粘贴。")
                    return
                target_columns = [0, None, 1, 2]
            elif start_column + widest > len(PVT_TABLE_COLUMNS):
                QMessageBox.warning(
                    self, "粘贴失败",
                    "粘贴数据超出 P、Bg、μg 三列，请重新选择起始单元格。")
                return
            else:
                target_columns = list(
                    range(start_column, start_column + widest))

        required_rows = start_row + len(matrix)
        if self.data_table.rowCount() <= required_rows:
            self.data_table.setRowCount(required_rows + 1)
        self._rendering_table = True
        try:
            for row_offset, row in enumerate(matrix):
                for source_column, value in enumerate(row):
                    if source_column >= len(target_columns):
                        continue
                    row_index = start_row + row_offset
                    target_column = target_columns[source_column]
                    if target_column is None:
                        continue
                    item = self.data_table.item(row_index, target_column)
                    if item is None:
                        item = QTableWidgetItem()
                        self.data_table.setItem(
                            row_index, target_column, item)
                    item.setText(value.strip())
                    item.setTextAlignment(Qt.AlignCenter)
        finally:
            self._rendering_table = False
        self._capture_table_cells()
        self._ensure_trailing_blank_row()
        self._update_table_preview()
        self.values_changed.emit()

    def _add_table_row(self):
        if self._active_mode != PVT_MODE_TABLE:
            return
        current = self.data_table.currentRow()
        target = current + 1 if current >= 0 else self.data_table.rowCount()
        self._rendering_table = True
        try:
            self.data_table.insertRow(target)
            for column in range(len(PVT_TABLE_COLUMNS)):
                self.data_table.setItem(
                    target, column, QTableWidgetItem(""))
        finally:
            self._rendering_table = False
        self._capture_table_cells()
        self.data_table.setCurrentCell(target, 0)
        self.data_table.editItem(self.data_table.item(target, 0))

    def _delete_selected_rows(self):
        if self._active_mode != PVT_MODE_TABLE:
            return
        rows = sorted({
            index.row() for index in self.data_table.selectedIndexes()
        }, reverse=True)
        if not rows and self.data_table.currentRow() >= 0:
            rows = [self.data_table.currentRow()]
        self._rendering_table = True
        try:
            for row in rows:
                self.data_table.removeRow(row)
        finally:
            self._rendering_table = False
        self._capture_table_cells()
        self._ensure_trailing_blank_row()
        self._update_table_preview()
        self.values_changed.emit()

    def _clear_table(self):
        if self._active_mode != PVT_MODE_TABLE:
            return
        self._table_cells = []
        self._render_table_cells()
        self._update_table_preview()
        self.values_changed.emit()

    def _copy_table(self):
        if self._active_mode == PVT_MODE_TABLE:
            self._capture_table_cells()
            rows = [
                row for row in self._table_cells if any(
                    str(value).strip() for value in row)
            ]
        else:
            rows = [
                [_pvt_cell_text(row, key)
                 for key, _label in PVT_TABLE_COLUMNS]
                for row in self._generated_rows
            ]
        if not rows:
            return
        header = "\t".join(label for _key, label in PVT_TABLE_COLUMNS)
        body = "\n".join(
            "\t".join(str(value) for value in row) for row in rows)
        QApplication.clipboard().setText(f"{header}\n{body}")
