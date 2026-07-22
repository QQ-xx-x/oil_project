# -*- coding: utf-8 -*-
"""网格与空间数据模块的专用展示组件。"""

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QAbstractItemView, QFrame, QGridLayout, QGroupBox, QHBoxLayout,
    QHeaderView, QLabel, QScrollArea, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)


def _business_value(value):
    if value is None or value == "":
        return "—"
    if isinstance(value, bool):
        return "是" if value else "否"
    if isinstance(value, int):
        return f"{value:,}"
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def _value_at(values, path):
    current = values
    for part in str(path or "").split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


class GridValueCard(QFrame):
    """网格概览使用的紧凑标签/数值卡片。"""

    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setObjectName("gridMetricCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(2)
        title_label = QLabel(title)
        title_label.setObjectName("gridMetricTitle")
        self.value_label = QLabel("—")
        self.value_label.setObjectName("gridMetricValue")
        layout.addWidget(title_label)
        layout.addWidget(self.value_label)

    def set_value(self, value):
        self.value_label.setText(_business_value(value))


class GridCoordinateRangeWidget(QGroupBox):
    """包含最小点和最大点两行的 X/Y/Z 坐标范围表。"""

    def __init__(self, parent=None):
        super().__init__("坐标范围", parent)
        self.setObjectName("gridOverviewSection")
        layout = QVBoxLayout(self)
        self.table = QTableWidget(2, 3)
        self.table.setObjectName("gridCoordinateTable")
        self.table.setHorizontalHeaderLabels(("X", "Y", "Z"))
        self.table.setVerticalHeaderLabels(("最小点", "最大点"))
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.NoSelection)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setFixedHeight(104)
        layout.addWidget(self.table)
        self.set_boundary(0, None)
        self.set_boundary(1, None)

    def set_boundary(self, row, value):
        coordinates = list(value or []) if isinstance(value, (list, tuple)) else []
        for column in range(3):
            item = QTableWidgetItem(
                _business_value(coordinates[column] if column < len(coordinates) else None))
            item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, column, item)


class GridOverviewPage(QWidget):
    """用卡片式网格概览替代通用纵向表单。"""

    values_changed = pyqtSignal()

    DIMENSION_FIELDS = (
        ("grid_nx", "Nx"),
        ("grid_ny", "Ny"),
        ("grid_nz", "Nz"),
    )
    CELL_FIELDS = (
        ("total_cell_count", "总网格数"),
        ("active_cell_count", "活跃网格数"),
        ("inactive_cell_count", "非活跃网格数"),
    )
    DATA_FIELDS = (
        ("coord_value_count", "COORD 数值"),
        ("zcorn_value_count", "ZCORN 数值"),
        ("actnum_value_count", "ACTNUM 数值"),
    )

    def __init__(self, title, fields, parent=None):
        super().__init__(parent)
        self.group_title = title
        self.fields = tuple(fields or ())
        self.bindings = []
        self._field_by_key = {field.key: field for field in self.fields}
        self._controls = {}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setObjectName("gridOverviewScroll")
        scroll.setWidgetResizable(True)
        holder = QWidget()
        content = QVBoxLayout(holder)
        content.setContentsMargins(16, 12, 16, 14)
        content.setSpacing(10)
        title_label = QLabel(title)
        title_label.setObjectName("parameterTitle")
        content.addWidget(title_label)

        content.addWidget(self._card_section("网格维度", self.DIMENSION_FIELDS))
        content.addWidget(self._card_section("网格数量", self.CELL_FIELDS))

        self.coordinate_range = GridCoordinateRangeWidget()
        content.addWidget(self.coordinate_range)
        for key in ("grid_bbox_min", "grid_bbox_max"):
            if key in self._field_by_key:
                self._controls[key] = self.coordinate_range

        content.addWidget(self._card_section("数据规模", self.DATA_FIELDS))
        self.property_statistics = None
        property_fields = tuple(
            field for field in self.fields
            if field.key.startswith("matrix_") and field.key.endswith("_summary")
        )
        if property_fields:
            self.property_statistics = GridPropertyStatisticsTable()
            content.addWidget(self.property_statistics)
            for field in property_fields:
                self._controls[field.key] = self.property_statistics
        content.addStretch()
        scroll.setWidget(holder)
        outer.addWidget(scroll)

        self.bindings = [
            (field, self._controls[field.key])
            for field in self.fields
            if field.key in self._controls
        ]

    def _card_section(self, title, definitions):
        group = QGroupBox(title)
        group.setObjectName("gridOverviewSection")
        layout = QHBoxLayout(group)
        layout.setContentsMargins(12, 14, 12, 10)
        layout.setSpacing(10)
        for key, label in definitions:
            card = GridValueCard(label)
            self._controls[key] = card
            layout.addWidget(card, 1)
        return group

    def set_values(self, values, module_key):
        property_rows = []
        for field, control in self.bindings:
            value = _value_at(values, field.source_path)
            if field.key == "grid_bbox_min":
                control.set_boundary(0, value)
            elif field.key == "grid_bbox_max":
                control.set_boundary(1, value)
            elif control is self.property_statistics:
                property_rows.append((field.title, field.unit, value))
            else:
                control.set_value(value)
        if self.property_statistics is not None:
            self.property_statistics.set_rows(property_rows)

    def collect_values(self, values):
        return None

    def refresh_derived(self, values, module_key):
        return None


class GridPropertyStatisticsTable(QGroupBox):
    """汇总全部基质属性统计信息的紧凑表格。"""

    COLUMNS = (
        "属性", "单位", "总数量", "有效值", "空值", "最小值", "最大值", "平均值",
    )

    def __init__(self, parent=None):
        super().__init__("属性统计", parent)
        self.setObjectName("gridOverviewSection")
        layout = QVBoxLayout(self)
        self.table = QTableWidget(0, len(self.COLUMNS))
        self.table.setObjectName("gridPropertyTable")
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.setMinimumHeight(210)
        layout.addWidget(self.table)

    def set_rows(self, rows):
        self.table.setRowCount(len(rows))
        for row_index, (title, unit, summary) in enumerate(rows):
            payload = summary if isinstance(summary, dict) else {}
            values = (
                title,
                unit or "—",
                payload.get("count"),
                payload.get("valid_count"),
                payload.get("null_count"),
                payload.get("min"),
                payload.get("max"),
                payload.get("mean"),
            )
            null_count = payload.get("null_count")
            for column, value in enumerate(values):
                item = QTableWidgetItem(_business_value(value))
                item.setTextAlignment(
                    Qt.AlignLeft | Qt.AlignVCenter
                    if column == 0 else Qt.AlignCenter)
                if column == 4 and isinstance(null_count, (int, float)) and null_count > 0:
                    item.setBackground(QColor("#fff3cd"))
                    item.setForeground(QColor("#7a5200"))
                self.table.setItem(row_index, column, item)
            self.table.setRowHeight(row_index, 34)


class GridPropertyStatisticsPage(QWidget):
    """统一的孔隙度/渗透率统计页面。"""

    values_changed = pyqtSignal()

    def __init__(self, title, fields, parent=None):
        super().__init__(parent)
        self.group_title = title
        self.fields = tuple(fields or ())
        self.statistics = GridPropertyStatisticsTable()
        self.bindings = [(field, self.statistics) for field in self.fields]

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 12, 16, 14)
        outer.setSpacing(10)
        title_label = QLabel(title)
        title_label.setObjectName("parameterTitle")
        outer.addWidget(title_label)
        outer.addWidget(self.statistics)
        outer.addStretch()

    def set_values(self, values, module_key):
        rows = []
        for field in self.fields:
            rows.append((
                field.title,
                field.unit,
                _value_at(values, field.source_path),
            ))
        self.statistics.set_rows(rows)

    def collect_values(self, values):
        return None

    def refresh_derived(self, values, module_key):
        return None
