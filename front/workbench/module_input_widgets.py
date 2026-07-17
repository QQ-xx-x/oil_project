# -*- coding: utf-8 -*-
"""Reusable business-only widgets for registry-driven module dialogs."""

import copy

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QDoubleValidator, QIntValidator
from PyQt5.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QFormLayout, QGroupBox,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)


def format_business_value(value):
    if value is None or value == "":
        return "—"
    if isinstance(value, bool):
        return "是" if value else "否"
    if isinstance(value, float):
        return f"{value:.10g}"
    if isinstance(value, (list, tuple)):
        return ", ".join(format_business_value(item) for item in value)
    if isinstance(value, dict):
        return f"{len(value)} 项"
    return str(value)


class BusinessScalarEditor(QWidget):
    """Editable or read-only scalar field without provenance information."""

    value_changed = pyqtSignal()

    def __init__(self, field, parent=None):
        super().__init__(parent)
        self.field = field
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        if not field.editable:
            self.editor = QLabel("—")
        elif field.widget_kind == "boolean":
            self.editor = QCheckBox()
            self.editor.toggled.connect(self.value_changed.emit)
        elif field.widget_kind == "choice":
            self.editor = QComboBox()
            self.editor.currentIndexChanged.connect(self.value_changed.emit)
        else:
            self.editor = QLineEdit()
            if field.widget_kind == "integer":
                self.editor.setValidator(QIntValidator(-2147483647, 2147483647))
            elif field.widget_kind == "number":
                validator = QDoubleValidator()
                validator.setNotation(QDoubleValidator.ScientificNotation)
                self.editor.setValidator(validator)
            self.editor.textEdited.connect(self.value_changed.emit)
        layout.addWidget(self.editor, 1)
        if field.unit:
            unit = QLabel(field.unit)
            unit.setObjectName("parameterDescription")
            layout.addWidget(unit)

    def set_value(self, value):
        if isinstance(self.editor, QLabel):
            self.editor.setText(format_business_value(value))
        elif isinstance(self.editor, QCheckBox):
            self.editor.setChecked(bool(value))
        elif isinstance(self.editor, QComboBox):
            text = "" if value is None else str(value)
            index = self.editor.findText(text)
            if index < 0 and text:
                self.editor.addItem(text)
                index = self.editor.count() - 1
            self.editor.setCurrentIndex(max(0, index))
        else:
            self.editor.setText("" if value is None else str(value))

    def value(self):
        if not self.field.editable:
            return None
        if isinstance(self.editor, QCheckBox):
            return self.editor.isChecked()
        if isinstance(self.editor, QComboBox):
            return self.editor.currentText()
        text = self.editor.text().strip()
        if not text:
            return None
        if self.field.widget_kind == "integer":
            return int(text)
        if self.field.widget_kind == "number":
            return float(text)
        return text


class SummaryCardWidget(QGroupBox):
    """Compact read-only business summary."""

    def __init__(self, title, parent=None):
        super().__init__(title, parent)
        self.form = QFormLayout(self)

    def set_value(self, value):
        while self.form.rowCount():
            self.form.removeRow(0)
        if isinstance(value, dict) and value:
            for key, item in value.items():
                if isinstance(item, (dict, list)):
                    continue
                self.form.addRow(str(key), QLabel(format_business_value(item)))
        else:
            self.form.addRow(QLabel(format_business_value(value)))


class StatisticsTableWidget(QGroupBox):
    """One-row statistics table driven by DisplayFieldRule columns."""

    def __init__(self, title, columns, parent=None):
        super().__init__(title, parent)
        self.columns = tuple(columns or ())
        layout = QVBoxLayout(self)
        self.table = QTableWidget(0, len(self.columns))
        self.table.setHorizontalHeaderLabels([title for _key, title in self.columns])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setMaximumHeight(105)
        layout.addWidget(self.table)

    def set_value(self, value):
        payload = value if isinstance(value, dict) else {}
        self.table.setRowCount(1 if payload else 0)
        if not payload:
            return
        for column, (key, _title) in enumerate(self.columns):
            self.table.setItem(
                0, column, QTableWidgetItem(
                    format_business_value(payload.get(key))))


class StructuredDataTableWidget(QGroupBox):
    """Bounded structured-data table; never accepts raw numerical arrays."""

    MAX_VISIBLE_ROWS = 500
    ORIGINAL_ROW_ROLE = Qt.UserRole + 1
    value_changed = pyqtSignal()

    def __init__(self, title, columns, editable=False, parent=None):
        super().__init__(title, parent)
        self.configured_columns = tuple(columns or ())
        self.columns = self.configured_columns
        self.editable = bool(editable)
        self._original_rows = []
        self._dirty = False
        layout = QVBoxLayout(self)
        self.summary = QLabel("暂无数据")
        self.summary.setObjectName("parameterDescription")
        layout.addWidget(self.summary)
        self.table = QTableWidget()
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        if not self.editable:
            self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        else:
            self.table.itemChanged.connect(self._mark_changed)
        layout.addWidget(self.table)
        if self.editable:
            buttons = QHBoxLayout()
            add_button = QPushButton("添加")
            remove_button = QPushButton("删除")
            add_button.clicked.connect(self._add_row)
            remove_button.clicked.connect(self._remove_rows)
            buttons.addWidget(add_button)
            buttons.addWidget(remove_button)
            buttons.addStretch()
            layout.addLayout(buttons)

    def set_value(self, value):
        rows = list(value or []) if isinstance(value, (list, tuple)) else []
        self._original_rows = copy.deepcopy(rows)
        self.columns = self.configured_columns or self._infer_columns(rows)
        self.table.blockSignals(True)
        self.table.setColumnCount(len(self.columns))
        self.table.setHorizontalHeaderLabels(
            [title for _key, title in self.columns])
        visible_rows = rows[:self.MAX_VISIBLE_ROWS]
        self.table.setRowCount(len(visible_rows))
        for row_index, row in enumerate(visible_rows):
            payload = row if isinstance(row, dict) else {"value": row}
            for column, (key, _title) in enumerate(self.columns):
                original = payload.get(key)
                item = QTableWidgetItem(format_business_value(original))
                item.setData(Qt.UserRole, copy.deepcopy(original))
                item.setData(self.ORIGINAL_ROW_ROLE, copy.deepcopy(payload))
                self.table.setItem(row_index, column, item)
        self.table.blockSignals(False)
        self._dirty = False
        if not rows:
            self.summary.setText("暂无数据")
        elif len(rows) > len(visible_rows):
            self.summary.setText(
                f"共 {len(rows)} 条，仅展示前 {len(visible_rows)} 条")
        else:
            self.summary.setText(f"共 {len(rows)} 条")

    def value(self):
        if not self._dirty:
            return copy.deepcopy(self._original_rows)
        rows = []
        for row in range(self.table.rowCount()):
            first = self.table.item(row, 0)
            original_row = (
                first.data(self.ORIGINAL_ROW_ROLE)
                if first is not None else None
            )
            payload = copy.deepcopy(
                original_row if isinstance(original_row, dict) else {})
            for column, (key, _title) in enumerate(self.columns):
                item = self.table.item(row, column)
                text = item.text() if item is not None else ""
                original = item.data(Qt.UserRole) if item is not None else None
                payload[key] = _coerce_edited_value(text, original)
            rows.append(payload)
        if len(self._original_rows) > self.MAX_VISIBLE_ROWS:
            rows.extend(copy.deepcopy(
                self._original_rows[self.MAX_VISIBLE_ROWS:]))
        return rows

    def _add_row(self):
        row = self.table.rowCount()
        self.table.insertRow(row)
        for column in range(self.table.columnCount()):
            item = QTableWidgetItem("")
            item.setData(Qt.UserRole, None)
            item.setData(self.ORIGINAL_ROW_ROLE, {})
            self.table.setItem(row, column, item)
        self._mark_changed()

    def _remove_rows(self):
        rows = sorted({index.row() for index in self.table.selectedIndexes()}, reverse=True)
        for row in rows:
            self.table.removeRow(row)
        if rows:
            self._mark_changed()

    def _mark_changed(self, *args):
        self._dirty = True
        self.value_changed.emit()

    @staticmethod
    def _infer_columns(rows):
        for row in rows:
            if isinstance(row, dict):
                keys = [
                    key for key, value in row.items()
                    if not isinstance(value, (dict, list, tuple))
                ][:8]
                if keys:
                    return tuple((key, str(key)) for key in keys)
        return (("value", "值"),)


class ValidationPanel(QGroupBox):
    """Business validation messages with no source record rendering."""

    def __init__(self, parent=None):
        super().__init__("校验提示", parent)
        layout = QVBoxLayout(self)
        self.messages = QListWidget()
        self.messages.setMaximumHeight(105)
        layout.addWidget(self.messages)

    def set_validation(self, validation):
        validation = validation or {}
        self.messages.clear()
        errors = list(validation.get("errors") or [])
        warnings = list(validation.get("warnings") or [])
        checks = dict(validation.get("checks") or {})
        has_failed_check = any(
            not (payload.get("ok") if isinstance(payload, dict) else payload)
            for payload in checks.values()
        )
        if not errors and not warnings and not has_failed_check:
            self.messages.addItem("校验通过")
        elif not errors:
            self.messages.addItem("校验完成，请查看提示")
        for message in errors:
            self.messages.addItem(f"错误：{message}")
        for message in warnings:
            self.messages.addItem(f"提示：{message}")
        for name, payload in checks.items():
            check = payload if isinstance(payload, dict) else {"ok": payload}
            state = "通过" if check.get("ok") else "未通过"
            detail = str(check.get("detail") or "").strip()
            suffix = f"（{detail}）" if detail else ""
            self.messages.addItem(f"{state}：{name}{suffix}")


def _coerce_edited_value(text, original):
    """Keep original types and hidden row fields when a table is edited."""

    if text == format_business_value(original):
        return copy.deepcopy(original)
    stripped = str(text or "").strip()
    if not stripped:
        return None
    if isinstance(original, bool):
        lowered = stripped.lower()
        if lowered in {"是", "true", "1", "yes"}:
            return True
        if lowered in {"否", "false", "0", "no"}:
            return False
        return stripped
    if isinstance(original, int) and not isinstance(original, bool):
        try:
            return int(stripped)
        except ValueError:
            return stripped
    if isinstance(original, float):
        try:
            return float(stripped)
        except ValueError:
            return stripped
    return stripped
