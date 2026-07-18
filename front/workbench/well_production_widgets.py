# -*- coding: utf-8 -*-
"""井轨迹、完井定义和生产控制的专用业务页面。"""

import copy
import re

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QAbstractItemView, QFrame, QGroupBox, QHBoxLayout, QHeaderView, QLabel,
    QPushButton, QSplitter, QTabWidget, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)


ROW_INDEX_ROLE = Qt.UserRole + 11
FIELD_VALUE_ROLE = Qt.UserRole + 12


WELL_TYPE_LABELS = {
    "PRODUCER": "生产井 (PRODUCER)",
    "INJECTOR": "注入井 (INJECTOR)",
}
WELL_TYPE_COMPACT_LABELS = {
    "PRODUCER": "生产井",
    "INJECTOR": "注入井",
}
EVENT_LABELS = {
    "PERF": "完井定义 (PERF)",
    "OPEN": "开启 (OPEN)",
    "SHUT": "关闭 (SHUT)",
    "CONTROL": "控制调整 (CONTROL)",
}
CONNECTION_LABELS = {
    "matrix": "基质 (matrix)",
    "fracture": "裂缝 (fracture)",
    "matrix_and_fracture": "基质与裂缝 (matrix + fracture)",
    "none": "未连接 (none)",
}


def _display_value(value):
    if value is None or value == "":
        return "—"
    if isinstance(value, bool):
        return "是" if value else "否"
    if isinstance(value, float):
        return f"{value:.10g}"
    if isinstance(value, int):
        return f"{value:,}"
    return str(value)


def _table(headers, editable=False):
    table = QTableWidget()
    table.setColumnCount(len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.verticalHeader().setVisible(False)
    table.verticalHeader().setDefaultSectionSize(29)
    table.setAlternatingRowColors(True)
    table.setSelectionBehavior(QAbstractItemView.SelectRows)
    table.setSelectionMode(QAbstractItemView.ExtendedSelection)
    table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    if not editable:
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    return table


def _item(value, alignment=Qt.AlignCenter, row_index=None):
    item = QTableWidgetItem(_display_value(value))
    item.setTextAlignment(alignment | Qt.AlignVCenter)
    item.setData(FIELD_VALUE_ROLE, copy.deepcopy(value))
    if row_index is not None:
        item.setData(ROW_INDEX_ROLE, int(row_index))
    return item


class WellMetricCard(QFrame):
    """井模块概览使用的小型指标卡。"""

    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setObjectName("wellMetricCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(11, 7, 11, 7)
        layout.setSpacing(1)
        title_label = QLabel(title)
        title_label.setObjectName("wellMetricTitle")
        self.value_label = QLabel("—")
        self.value_label.setObjectName("wellMetricValue")
        layout.addWidget(title_label)
        layout.addWidget(self.value_label)

    def set_value(self, value):
        self.value_label.setText(_display_value(value))


class WellTrajectoryPage(QWidget):
    """以井列表选择驱动单井轨迹明细的主从页面。"""

    values_changed = pyqtSignal()

    TRACK_COLUMNS = (
        ("md_m", "测深 MD (m)"),
        ("x_m", "X (m)"),
        ("y_m", "Y (m)"),
        ("z_m", "Z (m)"),
    )

    def __init__(self, title, fields=(), parent=None):
        super().__init__(parent)
        self.group_title = title
        self.fields = tuple(fields or ())
        self.bindings = [(field, self) for field in self.fields]
        self._well_list = []
        self._tracks = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 12, 16, 14)
        outer.setSpacing(9)
        title_label = QLabel(title)
        title_label.setObjectName("parameterTitle")
        outer.addWidget(title_label)

        metrics = QHBoxLayout()
        metrics.setSpacing(8)
        self.metric_cards = {}
        for key, label in (
                ("well_count", "井数量 / Wells"),
                ("track_count", "轨迹点 / Track points"),
                ("completion_count", "完井段 / Completions"),
                ("event_count", "井控事件 / Events")):
            card = WellMetricCard(label)
            metrics.addWidget(card, 1)
            self.metric_cards[key] = card
        outer.addLayout(metrics)

        self.content_splitter = QSplitter(Qt.Horizontal)
        self.content_splitter.setChildrenCollapsible(False)
        self.content_splitter.addWidget(self._well_group())
        self.content_splitter.addWidget(self._track_group())
        self.content_splitter.setStretchFactor(0, 0)
        self.content_splitter.setStretchFactor(1, 1)
        self.content_splitter.setSizes((350, 650))
        outer.addWidget(self.content_splitter, 1)

    def _well_group(self):
        group = QGroupBox("井列表 / Well list")
        group.setObjectName("wellSection")
        group.setMinimumWidth(330)
        layout = QVBoxLayout(group)
        self.well_table = _table((
            "井名", "井类型", "轨迹点", "MD范围 (m)"))
        self.well_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.well_table.itemSelectionChanged.connect(self._render_selected_tracks)
        header = self.well_table.horizontalHeader()
        header.setMinimumSectionSize(52)
        for column in (0, 1, 2):
            header.setSectionResizeMode(column, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        for column, tooltip in enumerate((
                "井名 / Well name",
                "井类型 / Well type",
                "轨迹点数量 / Track points",
                "测深范围 / MD range (m)")):
            self.well_table.horizontalHeaderItem(column).setToolTip(tooltip)
        layout.addWidget(self.well_table)
        return group

    def _track_group(self):
        group = QGroupBox("选中井轨迹 / Selected well track")
        group.setObjectName("wellSection")
        layout = QVBoxLayout(group)
        self.track_title = QLabel("请选择一口井")
        self.track_title.setObjectName("wellDetailTitle")
        layout.addWidget(self.track_title)
        self.track_table = _table(
            tuple(title for _key, title in self.TRACK_COLUMNS), editable=True)
        self.track_table.itemChanged.connect(self._track_item_changed)
        layout.addWidget(self.track_table)
        buttons = QHBoxLayout()
        add_button = QPushButton("添加轨迹点")
        remove_button = QPushButton("删除选中点")
        add_button.clicked.connect(self._add_track_point)
        remove_button.clicked.connect(self._remove_track_points)
        buttons.addWidget(add_button)
        buttons.addWidget(remove_button)
        buttons.addStretch()
        layout.addLayout(buttons)
        return group

    def set_values(self, values, module_key):
        wells = (values or {}).get("wells") or {}
        self._well_list = copy.deepcopy(list(wells.get("well_list") or []))
        self._tracks = copy.deepcopy(list(wells.get("tracks") or []))
        summary = wells.get("summary") or {}
        metrics = {
            "well_count": len(self._well_list),
            "track_count": len(self._tracks),
            "completion_count": summary.get("completion_definition_count"),
            "event_count": summary.get("event_count"),
        }
        for key, card in self.metric_cards.items():
            card.set_value(metrics.get(key))
        self._render_wells()

    def _render_wells(self):
        previous = self._selected_well_name()
        self.well_table.blockSignals(True)
        self.well_table.setRowCount(len(self._well_list))
        selected_row = 0
        for row_index, row in enumerate(self._well_list):
            name = str(row.get("well_name") or "")
            if name == previous:
                selected_row = row_index
            well_type = str(row.get("well_type") or "").upper()
            md_range = _range_text(row.get("md_min"), row.get("md_max"))
            values = (
                name,
                WELL_TYPE_COMPACT_LABELS.get(well_type, well_type or "—"),
                row.get("track_point_count"), md_range,
            )
            for column, value in enumerate(values):
                alignment = Qt.AlignLeft if column in (0, 1) else Qt.AlignCenter
                item = _item(value, alignment)
                item.setData(Qt.UserRole, name)
                if column == 1:
                    item.setToolTip(
                        WELL_TYPE_LABELS.get(well_type, well_type or "—"))
                self.well_table.setItem(row_index, column, item)
        self.well_table.blockSignals(False)
        if self._well_list:
            self.well_table.selectRow(selected_row)
        else:
            self._render_selected_tracks()

    def _selected_well_name(self):
        row = self.well_table.currentRow()
        item = self.well_table.item(row, 0) if row >= 0 else None
        return str(item.data(Qt.UserRole) or "") if item is not None else ""

    def _render_selected_tracks(self):
        well_name = self._selected_well_name()
        self.track_title.setText(
            f"{well_name} · 轨迹坐标" if well_name else "请选择一口井")
        selected = [
            (index, row) for index, row in enumerate(self._tracks)
            if str(row.get("well_name") or "") == well_name
        ]
        self.track_table.blockSignals(True)
        self.track_table.setRowCount(len(selected))
        for row_index, (source_index, row) in enumerate(selected):
            for column, (key, _title) in enumerate(self.TRACK_COLUMNS):
                self.track_table.setItem(
                    row_index, column,
                    _item(row.get(key), row_index=source_index))
        self.track_table.blockSignals(False)

    def _track_item_changed(self, item):
        source_index = item.data(ROW_INDEX_ROLE)
        if source_index is None or not 0 <= int(source_index) < len(self._tracks):
            return
        key = self.TRACK_COLUMNS[item.column()][0]
        original = item.data(FIELD_VALUE_ROLE)
        self._tracks[int(source_index)][key] = _coerce_value(item.text(), original)
        self.values_changed.emit()

    def _add_track_point(self):
        well_name = self._selected_well_name()
        if not well_name:
            return
        self._tracks.append({
            "well_name": well_name,
            "md_m": None, "x_m": None, "y_m": None, "z_m": None,
        })
        self._render_selected_tracks()
        self.track_table.selectRow(self.track_table.rowCount() - 1)
        self.values_changed.emit()

    def _remove_track_points(self):
        indexes = {
            self.track_table.item(index.row(), 0).data(ROW_INDEX_ROLE)
            for index in self.track_table.selectedIndexes()
            if self.track_table.item(index.row(), 0) is not None
        }
        for source_index in sorted(
                (int(index) for index in indexes if index is not None), reverse=True):
            if 0 <= source_index < len(self._tracks):
                self._tracks.pop(source_index)
        if indexes:
            self._render_selected_tracks()
            self.values_changed.emit()

    def collect_values(self, values):
        wells = dict(values.get("wells") or {})
        wells["tracks"] = copy.deepcopy(self._tracks)
        values["wells"] = wells

    def refresh_derived(self, values, module_key):
        return None


class CompletionControlPage(QWidget):
    """把 PERF 定义与 OPEN/SHUT/CONTROL 调度分开编辑。"""

    values_changed = pyqtSignal()

    DEFINITION_COLUMNS = (
        ("well_name", "井名 / Well"),
        ("comp_id", "完井段 ID"),
        ("md_range", "MD范围 (m)"),
        ("rw_m", "井半径 (m)"),
        ("control_type", "控制方式"),
        ("bhp_bar", "井底压力 BHP (bar)"),
        ("connection_target", "连接对象 / Target"),
    )
    EVENT_COLUMNS = (
        ("date", "时间 / Day"),
        ("well_name", "井名 / Well"),
        ("event", "事件 / Event"),
        ("comp_id", "关联完井段 ID"),
        ("control_type", "控制方式"),
        ("bhp_bar", "井底压力 BHP (bar)"),
    )

    def __init__(self, title, fields=(), parent=None):
        super().__init__(parent)
        self.group_title = title
        self.fields = tuple(fields or ())
        self.bindings = [(field, self) for field in self.fields]
        self._completions = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 12, 16, 14)
        outer.setSpacing(9)
        title_label = QLabel(title)
        title_label.setObjectName("parameterTitle")
        outer.addWidget(title_label)

        metrics = QHBoxLayout()
        metrics.setSpacing(7)
        self.metric_cards = {}
        for key, label in (
                ("PERF", "完井定义 / PERF"),
                ("OPEN", "开启 / OPEN"),
                ("SHUT", "关闭 / SHUT"),
                ("CONTROL", "控制 / CONTROL"),
                ("matrix", "基质连接"),
                ("fracture", "裂缝连接")):
            card = WellMetricCard(label)
            metrics.addWidget(card, 1)
            self.metric_cards[key] = card
        outer.addLayout(metrics)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("wellControlTabs")
        self.definition_table = self._editable_tab(
            "完井定义 / PERF", self.DEFINITION_COLUMNS, "PERF")
        self.event_table = self._editable_tab(
            "调度与井控 / Schedule", self.EVENT_COLUMNS, "OPEN")
        outer.addWidget(self.tabs, 1)

    def _editable_tab(self, title, columns, default_event):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(10, 10, 10, 10)
        table = _table(tuple(label for _key, label in columns), editable=True)
        table.itemChanged.connect(
            lambda item, definitions=columns: self._item_changed(item, definitions))
        layout.addWidget(table)
        buttons = QHBoxLayout()
        add_button = QPushButton("添加记录")
        remove_button = QPushButton("删除选中记录")
        add_button.clicked.connect(
            lambda _checked=False, event=default_event: self._add_record(event))
        remove_button.clicked.connect(
            lambda _checked=False, target=table: self._remove_records(target))
        buttons.addWidget(add_button)
        buttons.addWidget(remove_button)
        buttons.addStretch()
        layout.addLayout(buttons)
        self.tabs.addTab(page, title)
        return table

    def set_values(self, values, module_key):
        wells = (values or {}).get("wells") or {}
        self._completions = copy.deepcopy(
            list(wells.get("completions") or []))
        self._update_metrics()
        self._render_tables()

    def _update_metrics(self):
        counts = {key: 0 for key in ("PERF", "OPEN", "SHUT", "CONTROL")}
        matrix = 0
        fracture = 0
        for row in self._completions:
            event = str(row.get("event") or "").upper()
            if event in counts:
                counts[event] += 1
            if event == "PERF" and row.get("connect_matrix"):
                matrix += 1
            if event == "PERF" and row.get("connect_fracture"):
                fracture += 1
        counts.update({"matrix": matrix, "fracture": fracture})
        for key, card in self.metric_cards.items():
            card.set_value(counts.get(key, 0))

    def _render_tables(self):
        definitions = [
            (index, row) for index, row in enumerate(self._completions)
            if str(row.get("event") or "").upper() == "PERF"
        ]
        events = [
            (index, row) for index, row in enumerate(self._completions)
            if str(row.get("event") or "").upper() != "PERF"
        ]
        self._render_table(
            self.definition_table, definitions, self.DEFINITION_COLUMNS)
        self._render_table(self.event_table, events, self.EVENT_COLUMNS)

    def _render_table(self, table, rows, columns):
        table.blockSignals(True)
        table.setRowCount(len(rows))
        for table_row, (source_index, row) in enumerate(rows):
            for column, (key, _title) in enumerate(columns):
                raw = _row_value(row, key)
                display = _business_label(key, raw)
                alignment = Qt.AlignLeft if key in {
                    "well_name", "comp_id", "connection_target"} else Qt.AlignCenter
                item = _item(display, alignment, source_index)
                item.setData(FIELD_VALUE_ROLE, copy.deepcopy(raw))
                if key == "event":
                    event = str(raw or "").upper()
                    item.setForeground(_event_color(event))
                table.setItem(table_row, column, item)
        table.blockSignals(False)

    def _item_changed(self, item, columns):
        source_index = item.data(ROW_INDEX_ROLE)
        if source_index is None or not 0 <= int(source_index) < len(self._completions):
            return
        key = columns[item.column()][0]
        row = self._completions[int(source_index)]
        text = item.text().strip()
        if key == "md_range":
            parsed = _parse_range(text)
            if parsed is not None:
                row["md_top_m"], row["md_bottom_m"] = parsed
        elif key == "event":
            row[key] = _internal_event(text)
        elif key == "connection_target":
            row[key] = _internal_connection(text)
        else:
            row[key] = _coerce_value(text, item.data(FIELD_VALUE_ROLE))
        self._update_metrics()
        self.values_changed.emit()

    def _add_record(self, event):
        row = {
            "event": event,
            "well_name": "",
            "comp_id": "",
            "date": 0.0,
            "date_day": 0.0,
            "md_top_m": None,
            "md_bottom_m": None,
            "rw_m": None,
            "control_type": "BHP",
            "bhp_bar": None,
            "connection_target": "none",
        }
        self._completions.append(row)
        self._update_metrics()
        self._render_tables()
        target = self.definition_table if event == "PERF" else self.event_table
        target.selectRow(target.rowCount() - 1)
        self.values_changed.emit()

    def _remove_records(self, table):
        indexes = {
            table.item(index.row(), 0).data(ROW_INDEX_ROLE)
            for index in table.selectedIndexes()
            if table.item(index.row(), 0) is not None
        }
        for source_index in sorted(
                (int(index) for index in indexes if index is not None), reverse=True):
            if 0 <= source_index < len(self._completions):
                self._completions.pop(source_index)
        if indexes:
            self._update_metrics()
            self._render_tables()
            self.values_changed.emit()

    def collect_values(self, values):
        wells = dict(values.get("wells") or {})
        wells["completions"] = copy.deepcopy(self._completions)
        values["wells"] = wells

    def refresh_derived(self, values, module_key):
        return None


def _row_value(row, key):
    if key == "md_range":
        return _range_text(row.get("md_top_m"), row.get("md_bottom_m"))
    if key == "date":
        return row.get("date", row.get("date_day"))
    return row.get(key)


def _range_text(minimum, maximum):
    if minimum is None and maximum is None:
        return "—"
    return f"{_display_value(minimum)} – {_display_value(maximum)}"


def _parse_range(text):
    parts = [part.strip() for part in re.split(r"\s*(?:–|—|~|至)\s*", text)]
    if len(parts) != 2:
        return None
    try:
        return float(parts[0]), float(parts[1])
    except ValueError:
        return None


def _business_label(key, value):
    if key == "event":
        event = str(value or "").upper()
        return EVENT_LABELS.get(event, event)
    if key == "connection_target":
        target = str(value or "")
        return CONNECTION_LABELS.get(target, target)
    return value


def _internal_event(text):
    upper = str(text or "").upper()
    for event in EVENT_LABELS:
        if event in upper:
            return event
    return upper


def _internal_connection(text):
    lowered = str(text or "").lower()
    for target in (
            "matrix_and_fracture", "fracture", "matrix", "none"):
        if target in lowered:
            return target
    return lowered


def _coerce_value(text, original):
    stripped = str(text or "").strip()
    if stripped in {"", "—"}:
        return None
    if isinstance(original, bool):
        return stripped.lower() in {"1", "true", "yes", "是"}
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


def _event_color(event):
    return {
        "PERF": QColor("#3f68b1"),
        "OPEN": QColor("#2f7b4e"),
        "SHUT": QColor("#b25d32"),
        "CONTROL": QColor("#74559a"),
    }.get(event, QColor("#26364a"))
