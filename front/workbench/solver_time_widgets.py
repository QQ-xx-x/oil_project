# -*- coding: utf-8 -*-
"""模拟时间控制模块的专用参数页面。"""

import copy

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QFrame, QGroupBox, QHBoxLayout, QLabel, QVBoxLayout, QWidget,
)

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


def _format_step(value):
    return "—" if value is None else f"{value:.10g}"


class TimeParameterCard(QFrame):
    """带中英文名称和数学符号的时间参数卡。"""

    def __init__(self, title, symbol, control, prominent=False, parent=None):
        super().__init__(parent)
        self.setObjectName(
            "timePrimaryParameterCard" if prominent else "timeParameterCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 12)
        layout.setSpacing(7)

        heading = QHBoxLayout()
        title_label = QLabel(title)
        title_label.setObjectName("timeParameterTitle")
        symbol_label = QLabel(symbol)
        symbol_label.setObjectName("timeParameterSymbol")
        heading.addWidget(title_label)
        heading.addStretch()
        heading.addWidget(symbol_label)
        layout.addLayout(heading)
        layout.addWidget(control)


class SimulationTimeControlPage(QWidget):
    """模拟周期与自适应时间步的紧凑编辑页面。"""

    values_changed = pyqtSignal()

    LABELS = {
        "total_time": ("总模拟时间 / Total time", "T"),
        "dt_init": ("初始时间步 / Initial step", "Δt₀"),
        "dt_min": ("最小时间步 / Minimum step", "Δt min"),
        "dt_max": ("最大时间步 / Maximum step", "Δt max"),
    }

    def __init__(self, title, fields=(), parent=None):
        super().__init__(parent)
        self.group_title = title
        self.fields = tuple(fields or ())
        self.bindings = []
        self._controls = {}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 16, 20, 18)
        outer.setSpacing(13)

        title_label = QLabel("时间参数 / Time parameters")
        title_label.setObjectName("parameterTitle")
        outer.addWidget(title_label)

        cycle = QGroupBox("模拟周期 / Simulation period")
        cycle.setObjectName("timeControlSection")
        cycle_layout = QHBoxLayout(cycle)
        cycle_layout.setContentsMargins(14, 19, 14, 14)
        total_field = self._field("total_time")
        total_control = self._make_control(total_field)
        total_card = TimeParameterCard(
            *self.LABELS["total_time"], total_control, prominent=True)
        total_card.setMaximumWidth(520)
        cycle_layout.addWidget(total_card, 1)
        cycle_layout.addStretch(1)
        outer.addWidget(cycle)

        steps = QGroupBox("时间步设置 / Time-step settings")
        steps.setObjectName("timeControlSection")
        steps_layout = QHBoxLayout(steps)
        steps_layout.setContentsMargins(14, 19, 14, 14)
        steps_layout.setSpacing(10)
        for key in ("dt_min", "dt_init", "dt_max"):
            field = self._field(key)
            control = self._make_control(field)
            steps_layout.addWidget(
                TimeParameterCard(*self.LABELS[key], control), 1)
        outer.addWidget(steps)

        relation = QFrame()
        relation.setObjectName("timeStepRelation")
        relation_layout = QHBoxLayout(relation)
        relation_layout.setContentsMargins(12, 8, 12, 8)
        relation_layout.setSpacing(10)
        relation_title = QLabel("时间步关系 / Step relation")
        relation_title.setObjectName("timeStepRelationTitle")
        self.relation_value = QLabel("Δt min ≤ Δt₀ ≤ Δt max")
        self.relation_value.setObjectName("timeStepRelationValue")
        self.relation_status = QLabel("○ 等待输入")
        self.relation_status.setObjectName("timeStepRelationStatus")
        relation_layout.addWidget(relation_title)
        relation_layout.addWidget(self.relation_value, 1, Qt.AlignCenter)
        relation_layout.addWidget(self.relation_status)
        outer.addWidget(relation)
        outer.addStretch()

    def _field(self, key):
        return next(field for field in self.fields if field.key == key)

    def _make_control(self, field):
        control = BusinessScalarEditor(field)
        control.setObjectName("timeParameterControl")
        control.editor.setObjectName("timeParameterEditor")
        control.value_changed.connect(self._on_value_changed)
        self._controls[field.key] = control
        self.bindings.append((field, control))
        return control

    def set_values(self, values, module_key):
        for field, control in self.bindings:
            control.set_value(_value_at(values, field.source_path))
        self._update_relation()

    def collect_values(self, values):
        for field, control in self.bindings:
            try:
                value = control.value()
            except ValueError:
                continue
            if value is None:
                _remove_value(values, field.source_path)
            else:
                _set_value(values, field.source_path, value)

    def refresh_derived(self, values, module_key):
        self._update_relation()

    def _on_value_changed(self):
        self._update_relation()
        self.values_changed.emit()

    def _update_relation(self):
        values = {}
        for key in ("dt_min", "dt_init", "dt_max"):
            try:
                values[key] = self._controls[key].value()
            except ValueError:
                values[key] = None

        complete = all(values[key] is not None for key in values)
        valid = complete and (
            values["dt_min"] <= values["dt_init"] <= values["dt_max"])
        self.relation_value.setText(
            f'{_format_step(values["dt_min"])} ≤ '
            f'{_format_step(values["dt_init"])} ≤ '
            f'{_format_step(values["dt_max"])} day')
        if not complete:
            state, status = "pending", "○ 等待完整输入"
        elif valid:
            state, status = "success", "✓ 关系正确"
        else:
            state, status = "error", "× 时间步关系错误"
        self.relation_status.setText(status)
        self.relation_status.setProperty("state", state)
        self.relation_status.style().unpolish(self.relation_status)
        self.relation_status.style().polish(self.relation_status)

        for key in ("dt_min", "dt_init", "dt_max"):
            editor = self._controls[key].editor
            editor.setProperty("relationError", bool(complete and not valid))
            editor.style().unpolish(editor)
            editor.style().polish(editor)
