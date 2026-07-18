# -*- coding: utf-8 -*-
"""初始状态模块的专用压力与三相饱和度页面。"""

import copy
import math

from PyQt5.QtCore import QRectF, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QPainter, QPainterPath
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


class InitialParameterCard(QFrame):
    """初始状态页面使用的名称/编辑器参数卡。"""

    def __init__(self, title, control, parent=None):
        super().__init__(parent)
        self.setObjectName("initialParameterCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 12)
        layout.setSpacing(7)
        label = QLabel(title)
        label.setObjectName("initialParameterTitle")
        layout.addWidget(label)
        layout.addWidget(control)


class SaturationBar(QWidget):
    """按水、气、油三相比例绘制的紧凑水平条。"""

    COLORS = (
        QColor("#4f8fcf"),
        QColor("#d5a63b"),
        QColor("#55a472"),
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self._values = None
        self.setMinimumHeight(38)
        self.setMaximumHeight(46)

    def set_values(self, sw, sg, so):
        values = (sw, sg, so)
        valid = all(
            isinstance(value, (int, float)) and math.isfinite(value)
            and value >= 0.0 for value in values)
        self._values = values if valid else None
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        area = QRectF(0.5, 4.5, self.width() - 1.0, self.height() - 9.0)
        path = QPainterPath()
        path.addRoundedRect(area, 5.0, 5.0)
        painter.fillPath(path, QColor("#e6eaf0"))
        if not self._values:
            return

        total = sum(self._values)
        if total <= 0.0:
            return
        painter.save()
        painter.setClipPath(path)
        left = area.left()
        for index, value in enumerate(self._values):
            width = area.width() * value / total
            painter.fillRect(
                QRectF(left, area.top(), width, area.height()),
                self.COLORS[index],
            )
            left += width
        painter.restore()


class _InitialEditablePage(QWidget):
    """初始状态专属页面共享的编辑值收集逻辑。"""

    values_changed = pyqtSignal()

    def __init__(self, title, fields=(), parent=None):
        super().__init__(parent)
        self.group_title = title
        self.fields = tuple(fields or ())
        self.bindings = []

    @staticmethod
    def _style_control(control):
        control.setObjectName("initialParameterControl")
        if hasattr(control.editor, "setObjectName"):
            control.editor.setObjectName("initialParameterEditor")
        return control

    def collect_values(self, values):
        for field, control in self.bindings:
            if not field.editable:
                continue
            value = control.value()
            if value is None:
                _remove_value(values, field.source_path)
            else:
                _set_value(values, field.source_path, value)


class InitialPressurePage(_InitialEditablePage):
    """只展示一个紧凑压力卡的初始压力页面。"""

    def __init__(self, title, fields=(), parent=None):
        super().__init__(title, fields, parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 12, 16, 14)
        outer.setSpacing(12)
        title_label = QLabel(title)
        title_label.setObjectName("parameterTitle")
        outer.addWidget(title_label)

        section = QGroupBox("压力设置")
        section.setObjectName("initialSection")
        section.setMaximumWidth(620)
        section_layout = QHBoxLayout(section)
        section_layout.setContentsMargins(14, 18, 14, 14)
        for field in self.fields:
            control = self._style_control(BusinessScalarEditor(field))
            control.setMinimumWidth(290)
            control.value_changed.connect(self.values_changed.emit)
            self.bindings.append((field, control))
            section_layout.addWidget(
                InitialParameterCard("初始压力", control), 1)
        outer.addWidget(section, 0, Qt.AlignLeft)
        outer.addStretch()

    def set_values(self, values, module_key):
        for field, control in self.bindings:
            control.set_value(_value_at(values, field.source_path))

    def refresh_derived(self, values, module_key):
        return None


class InitialSaturationPage(_InitialEditablePage):
    """带派生油相、比例条和实时状态的初始饱和度页面。"""

    def __init__(self, title, fields=(), parent=None):
        super().__init__(title, fields, parent)
        self._field_by_key = {field.key: field for field in self.fields}
        self._controls = {}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 12, 16, 14)
        outer.setSpacing(12)
        title_label = QLabel(title)
        title_label.setObjectName("parameterTitle")
        outer.addWidget(title_label)

        section = QGroupBox("三相饱和度")
        section.setObjectName("initialSection")
        section_layout = QHBoxLayout(section)
        section_layout.setContentsMargins(14, 18, 14, 14)
        section_layout.setSpacing(10)
        definitions = (
            ("initial_sw", "初始含水饱和度 Sw"),
            ("initial_sg", "初始含气饱和度 Sg"),
            ("initial_so", "初始含油饱和度 So"),
        )
        for key, label in definitions:
            field = self._field_by_key[key]
            control = self._style_control(BusinessScalarEditor(field))
            if field.editable:
                control.value_changed.connect(self._on_value_changed)
            self._controls[key] = control
            self.bindings.append((field, control))
            card = InitialParameterCard(label, control)
            if not field.editable:
                card.setObjectName("initialDerivedCard")
            section_layout.addWidget(card, 1)
        outer.addWidget(section)

        composition = QGroupBox("相组成")
        composition.setObjectName("initialSection")
        composition_layout = QVBoxLayout(composition)
        composition_layout.setContentsMargins(14, 18, 14, 12)
        composition_layout.setSpacing(9)
        self.saturation_bar = SaturationBar()
        composition_layout.addWidget(self.saturation_bar)

        legend = QHBoxLayout()
        legend.setSpacing(18)
        self.legend_labels = {}
        for key, title, color in (
                ("sw", "水相", "#4f8fcf"),
                ("sg", "气相", "#d5a63b"),
                ("so", "油相", "#55a472")):
            label = QLabel(f"● {title} —")
            label.setObjectName("saturationLegend")
            label.setStyleSheet(f"color: {color};")
            legend.addWidget(label)
            self.legend_labels[key] = label
        legend.addStretch()
        composition_layout.addLayout(legend)

        self.status = QLabel("○ 尚未导入饱和度数据")
        self.status.setObjectName("saturationStatus")
        composition_layout.addWidget(self.status)
        outer.addWidget(composition)
        outer.addStretch()

    def set_values(self, values, module_key):
        for key in ("initial_sw", "initial_sg"):
            field = self._field_by_key[key]
            self._controls[key].set_value(
                _value_at(values, field.source_path))
        self._update_saturation(values)

    def refresh_derived(self, values, module_key):
        self._update_saturation(values)

    def _on_value_changed(self):
        preview = {}
        try:
            for key in ("initial_sw", "initial_sg"):
                field = self._field_by_key[key]
                value = self._controls[key].value()
                if value is not None:
                    _set_value(preview, field.source_path, value)
        except (TypeError, ValueError):
            preview = {}
        self._update_saturation(preview)
        self.values_changed.emit()

    def _update_saturation(self, values):
        sw = _number_or_none(values.get("sw") if isinstance(values, dict) else None)
        sg = _number_or_none(values.get("sg") if isinstance(values, dict) else None)
        if sw is None or sg is None:
            self._show_saturation(None, None, None, "empty")
            return
        so = 1.0 - sw - sg
        valid = 0.0 <= sw <= 1.0 and 0.0 <= sg <= 1.0 and so >= -1e-9
        if not valid:
            self._show_saturation(sw, sg, None, "error")
            return
        so = max(0.0, so)
        self._show_saturation(sw, sg, so, "success")

    def _show_saturation(self, sw, sg, so, state):
        self._controls["initial_so"].set_value(so)
        self.saturation_bar.set_values(sw, sg, so)
        values = {"sw": sw, "sg": sg, "so": so}
        titles = {"sw": "水相", "sg": "气相", "so": "油相"}
        for key, label in self.legend_labels.items():
            value = values[key]
            text = "—" if value is None else f"{value * 100:.1f}%"
            label.setText(f"● {titles[key]} {text}")
        if state == "success":
            self.status.setText("✓ 饱和度总和 1.0000")
        elif state == "error":
            self.status.setText("初始饱和度无效：Sw、Sg 应在 0 到 1 之间且 Sw + Sg ≤ 1")
        else:
            self.status.setText("○ 尚未导入饱和度数据")
        self.status.setProperty("state", state)
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)


def _number_or_none(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None
