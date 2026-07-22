# -*- coding: utf-8 -*-
"""岩石物理输入模块的专用页面。"""

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


class RockRelativePermeabilityPage(QWidget):
    """气水相渗指数和饱和度端点编辑器。"""

    values_changed = pyqtSignal()

    def __init__(self, title, fields, parent=None):
        super().__init__(parent)
        self.group_title = title
        self.fields = tuple(fields or ())
        self.bindings = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 12, 16, 14)
        outer.setSpacing(12)
        title_label = QLabel(title)
        title_label.setObjectName("parameterTitle")
        outer.addWidget(title_label)

        section = QGroupBox("参数设置")
        section.setObjectName("rockParameterSection")
        section.setMaximumWidth(680)
        section_layout = QVBoxLayout(section)
        section_layout.setContentsMargins(14, 18, 14, 14)

        labels = {
            "relperm_exponent_n": "相渗指数 n",
            "swi": "束缚水饱和度 Swi",
            # 内部字段名保留 sgc，界面按其实际物理含义显示为 Sgr。
            "sgc": "残余气饱和度 Sgr",
        }
        for field in self.fields:
            card = QFrame()
            card.setObjectName("rockParameterCard")
            row = QHBoxLayout(card)
            row.setContentsMargins(14, 12, 14, 12)
            row.setSpacing(12)
            label = QLabel(labels.get(field.key, field.title))
            label.setObjectName("rockParameterLabel")
            row.addWidget(label)
            row.addStretch()

            control = BusinessScalarEditor(field)
            control.setObjectName("rockParameterControl")
            control.setFixedWidth(270)
            if hasattr(control.editor, "setPlaceholderText"):
                control.editor.setPlaceholderText("等待导入")
                control.editor.setObjectName("rockParameterEditor")
            control.value_changed.connect(self.values_changed.emit)
            row.addWidget(control)
            self.bindings.append((field, control))
            section_layout.addWidget(card)
        outer.addWidget(section, 0, Qt.AlignLeft)
        outer.addStretch()

    def set_values(self, values, module_key):
        for field, control in self.bindings:
            control.set_value(_value_at(values, field.source_path))

    def collect_values(self, values):
        for field, control in self.bindings:
            value = control.value()
            if value is None:
                _remove_value(values, field.source_path)
            else:
                _set_value(values, field.source_path, value)

    def refresh_derived(self, values, module_key):
        return None


class RockEmptyStatePage(QWidget):
    """为计划中的岩石物理功能提供中性占位页。"""

    values_changed = pyqtSignal()

    def __init__(self, title, fields=(), parent=None):
        super().__init__(parent)
        self.group_title = title
        self.fields = tuple(fields or ())
        self.bindings = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 12, 16, 14)
        title_label = QLabel(title)
        title_label.setObjectName("parameterTitle")
        outer.addWidget(title_label)
        empty = QFrame()
        empty.setObjectName("rockEmptyState")
        empty_layout = QVBoxLayout(empty)
        empty_layout.setContentsMargins(18, 24, 18, 24)
        message = QLabel(f"当前尚未导入{title}数据")
        message.setObjectName("rockEmptyStateText")
        message.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(message)
        outer.addWidget(empty)
        outer.addStretch()

    def set_values(self, values, module_key):
        return None

    def collect_values(self, values):
        return None

    def refresh_derived(self, values, module_key):
        return None
