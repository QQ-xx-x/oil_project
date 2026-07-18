# -*- coding: utf-8 -*-
"""流体与 PVT 模块的专用参数页面和曲线预览。"""

import copy
import math

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QFrame, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QProgressBar,
    QStackedWidget, QVBoxLayout, QWidget,
)

from .chart_adapters import build_gas_pvt_curve_from_values
from .module_input_widgets import BusinessScalarEditor


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
    """按水相/油相对比和饱和度端点组织基础流体参数。"""

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
        for column, text in enumerate(("参数", "水相", "油相")):
            label = QLabel(text)
            label.setObjectName("fluidTableHeader")
            label.setAlignment(Qt.AlignCenter)
            grid.addWidget(label, 0, column)
        for row, (label_text, water_key, oil_key) in enumerate((
                ("黏度", "mu_w", "mu_o"),
                ("压缩系数", "cw", "co")), start=1):
            label = QLabel(label_text)
            label.setObjectName("fluidRowLabel")
            grid.addWidget(label, row, 0)
            grid.addWidget(self._control(by_key[water_key]), row, 1)
            grid.addWidget(self._control(by_key[oil_key]), row, 2)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 1)
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

        endpoints = QGroupBox("饱和度端点")
        endpoints.setObjectName("fluidSection")
        endpoint_layout = QHBoxLayout(endpoints)
        endpoint_layout.setContentsMargins(14, 18, 14, 12)
        endpoint_layout.setSpacing(10)
        for key, label in (
                ("swi", "束缚水饱和度 Swi"),
                ("sor", "残余油饱和度 Sor"),
                ("sgc", "临界气饱和度 Sgc")):
            endpoint_layout.addWidget(
                FluidParameterCard(label, self._control(by_key[key])), 1)
        outer.addWidget(endpoints)
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
    """紧凑的 PVT 表设置和实时气体偏差因子曲线。"""

    REQUIRED_KEYS = (
        "temperature_c", "gas_table_pmin_bar",
        "gas_table_pmax_bar", "gas_table_n",
    )

    def __init__(self, title, fields=(), parent=None):
        super().__init__(title, fields, parent)
        self._context_values = {}
        by_key = {field.key: field for field in self.fields}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 12, 16, 14)
        outer.setSpacing(10)
        title_label = QLabel(title)
        title_label.setObjectName("parameterTitle")
        outer.addWidget(title_label)

        settings = QGroupBox("PVT表设置")
        settings.setObjectName("fluidSection")
        settings_layout = QHBoxLayout(settings)
        settings_layout.setContentsMargins(14, 18, 14, 12)
        settings_layout.setSpacing(10)
        for key, label in (
                ("gas_table_pmin_bar", "最小压力"),
                ("gas_table_pmax_bar", "最大压力"),
                ("gas_table_n", "采样点数")):
            control = self._control(by_key[key], self._on_value_changed)
            settings_layout.addWidget(FluidParameterCard(label, control), 1)
        outer.addWidget(settings)

        chart = QGroupBox("PVT曲线预览")
        chart.setObjectName("fluidSection")
        chart_layout = QVBoxLayout(chart)
        chart_layout.setContentsMargins(12, 16, 12, 10)
        chart_layout.setSpacing(7)
        metrics = QHBoxLayout()
        metrics.setSpacing(8)
        self.metric_cards = {}
        for key, label in (
                ("pressure_range", "压力范围 (bar)"),
                ("z_min", "Z 最小值"),
                ("z_max", "Z 最大值")):
            card = FluidMetricCard(label)
            metrics.addWidget(card, 1)
            self.metric_cards[key] = card
        chart_layout.addLayout(metrics)

        self.chart_stack = QStackedWidget()
        self.chart_placeholder = QLabel("导入数据后显示 PVT 曲线")
        self.chart_placeholder.setObjectName("pvtChartPlaceholder")
        self.chart_placeholder.setAlignment(Qt.AlignCenter)
        self.chart_stack.addWidget(self.chart_placeholder)
        self.figure = Figure(facecolor="white")
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setObjectName("pvtChartCanvas")
        self.canvas.setMinimumHeight(330)
        self.chart_stack.addWidget(self.canvas)
        chart_layout.addWidget(self.chart_stack, 1)
        outer.addWidget(chart, 1)

    def set_values(self, values, module_key):
        self._context_values = copy.deepcopy(values or {})
        super().set_values(values, module_key)
        self._render_curve()

    def refresh_derived(self, values, module_key):
        self._context_values = copy.deepcopy(values or {})
        self._render_curve()

    def _on_value_changed(self):
        self._render_curve()
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

    def _render_curve(self):
        try:
            values = self._preview_values()
        except (TypeError, ValueError):
            self._show_placeholder("当前参数无法生成 PVT 曲线")
            return
        if any(values.get(key) is None for key in self.REQUIRED_KEYS):
            self._show_placeholder("导入完整参数后显示 PVT 曲线")
            return
        try:
            curve = build_gas_pvt_curve_from_values(values)
        except (TypeError, ValueError) as exc:
            self._show_placeholder(str(exc))
            return

        points = list(curve.get("points") or [])
        if not points:
            self._show_placeholder("当前参数没有生成可展示的曲线数据")
            return
        pressures = [point[0] for point in points]
        z_values = [point[1] for point in points]
        self.figure.clear()
        axis = self.figure.add_subplot(111)
        axis.set_facecolor("#ffffff")
        axis.plot(
            pressures, z_values, color="#3f68b1", linewidth=2.2,
            label="气体偏差因子 Z",
        )
        axis.fill_between(
            pressures, z_values, min(z_values),
            color="#dce7f5", alpha=0.55,
        )
        axis.set_xlabel("压力 P (bar)")
        axis.set_ylabel("气体偏差因子 Z")
        axis.grid(True, linestyle="--", linewidth=0.8, alpha=0.38)
        axis.legend(loc="best", frameon=False)
        axis.margins(x=0.01, y=0.12)
        for spine in axis.spines.values():
            spine.set_color("#9ba8b8")
        self.figure.tight_layout(pad=1.2)
        self.canvas.draw_idle()
        self.metric_cards["pressure_range"].set_value(
            f"{pressures[0]:.6g} – {pressures[-1]:.6g}")
        self.metric_cards["z_min"].set_value(min(z_values))
        self.metric_cards["z_max"].set_value(max(z_values))
        self.chart_stack.setCurrentWidget(self.canvas)

    def _show_placeholder(self, message):
        self.chart_placeholder.setText(str(message or "导入数据后显示 PVT 曲线"))
        for card in self.metric_cards.values():
            card.set_value(None)
        self.chart_stack.setCurrentWidget(self.chart_placeholder)
