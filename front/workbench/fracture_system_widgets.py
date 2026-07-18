# -*- coding: utf-8 -*-
"""裂缝系统模块的专用展示页面。"""

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QAbstractItemView, QFrame, QGroupBox, QHBoxLayout, QHeaderView, QLabel,
    QSplitter, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from .fracture_data_adapter import (
    derive_hydraulic_fractures,
    hydraulic_fracture_summary,
)
from .input_keyword_registry import MODULE_WELL_PRODUCTION
from .module_input_widgets import format_business_value


def _value(value):
    if isinstance(value, int) and not isinstance(value, bool):
        return f"{value:,}"
    return format_business_value(value)


def _item(value, alignment=Qt.AlignCenter):
    item = QTableWidgetItem(_value(value))
    item.setTextAlignment(alignment | Qt.AlignVCenter)
    return item


def _prepare_table(table, headers, stretch_first=False):
    table.setColumnCount(len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectRows)
    table.setSelectionMode(QAbstractItemView.SingleSelection)
    table.setAlternatingRowColors(True)
    table.verticalHeader().setVisible(False)
    table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    if stretch_first:
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)


class FractureMetricCard(QFrame):
    """裂缝概览使用的小型指标卡。"""

    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setObjectName("fractureMetricCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(2)
        title_label = QLabel(title)
        title_label.setObjectName("fractureMetricTitle")
        self.value_label = QLabel("—")
        self.value_label.setObjectName("fractureMetricValue")
        layout.addWidget(title_label)
        layout.addWidget(self.value_label)

    def set_value(self, value):
        self.value_label.setText(_value(value))


class NaturalFracturePage(QWidget):
    """面向天然裂缝的概览、统计及主从明细页面。"""

    values_changed = pyqtSignal()

    def __init__(self, title, fields=(), parent=None):
        super().__init__(parent)
        self.group_title = title
        self.fields = tuple(fields or ())
        self.bindings = []
        self._fractures = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 12, 16, 14)
        outer.setSpacing(9)
        title_label = QLabel(title)
        title_label.setObjectName("parameterTitle")
        outer.addWidget(title_label)

        metrics = QHBoxLayout()
        metrics.setSpacing(9)
        self.metric_cards = {}
        for key, label in (
                ("fracture_count", "裂缝数量"),
                ("node_count", "节点数量"),
                ("set_count", "裂缝集合"),
                ("property_count", "属性数量")):
            card = FractureMetricCard(label)
            metrics.addWidget(card, 1)
            self.metric_cards[key] = card
        outer.addLayout(metrics)
        self.count_warning = QLabel("")
        self.count_warning.setObjectName("fractureInlineWarning")
        self.count_warning.hide()
        outer.addWidget(self.count_warning)

        overview = QSplitter(Qt.Horizontal)
        overview.setChildrenCollapsible(False)
        overview.addWidget(self._coordinate_group())
        overview.addWidget(self._set_group())
        overview.setSizes((430, 300))
        overview.setFixedHeight(158)
        outer.addWidget(overview)

        outer.addWidget(self._statistics_group())

        self.detail_splitter = QSplitter(Qt.Vertical)
        self.detail_splitter.setObjectName("fractureDetailSplitter")
        self.detail_splitter.setChildrenCollapsible(False)
        self.detail_splitter.addWidget(self._fracture_list_group())
        self.detail_splitter.addWidget(self._selected_fracture_group())
        self.detail_splitter.setStretchFactor(0, 3)
        self.detail_splitter.setStretchFactor(1, 2)
        self.detail_splitter.setSizes((260, 225))
        outer.addWidget(self.detail_splitter, 1)

    def _coordinate_group(self):
        group = QGroupBox("空间范围")
        group.setObjectName("fractureSection")
        layout = QVBoxLayout(group)
        self.coordinate_table = QTableWidget(3, 3)
        _prepare_table(self.coordinate_table, ("最小值", "最大值", "跨度"))
        self.coordinate_table.setVerticalHeaderLabels(("X", "Y", "Z"))
        self.coordinate_table.verticalHeader().setVisible(True)
        self.coordinate_table.setSelectionMode(QAbstractItemView.NoSelection)
        self.coordinate_table.verticalHeader().setDefaultSectionSize(28)
        self.coordinate_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.coordinate_table.setFixedHeight(116)
        layout.addWidget(self.coordinate_table)
        return group

    def _set_group(self):
        group = QGroupBox("裂缝集合")
        group.setObjectName("fractureSection")
        layout = QVBoxLayout(group)
        self.set_table = QTableWidget()
        _prepare_table(self.set_table, ("集合ID", "集合名称"), stretch_first=True)
        self.set_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.set_table.setFixedHeight(116)
        layout.addWidget(self.set_table)
        return group

    def _statistics_group(self):
        group = QGroupBox("属性统计")
        group.setObjectName("fractureSection")
        layout = QVBoxLayout(group)
        self.statistics_table = QTableWidget()
        _prepare_table(
            self.statistics_table,
            ("属性", "单位", "数量", "最小值", "最大值", "平均值"),
            stretch_first=True,
        )
        self.statistics_table.verticalHeader().setDefaultSectionSize(28)
        self.statistics_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.statistics_table.setFixedHeight(116)
        layout.addWidget(self.statistics_table)
        group.setFixedHeight(150)
        return group

    def _fracture_list_group(self):
        group = QGroupBox("天然裂缝列表")
        group.setObjectName("fractureSection")
        group.setMinimumHeight(220)
        layout = QVBoxLayout(group)
        self.fracture_count_label = QLabel("暂无数据")
        self.fracture_count_label.setObjectName("parameterDescription")
        layout.addWidget(self.fracture_count_label)
        self.fracture_table = QTableWidget()
        _prepare_table(
            self.fracture_table,
            ("裂缝ID", "集合", "顶点数", "渗透率", "压缩系数", "开度"),
            stretch_first=True,
        )
        self.fracture_table.itemSelectionChanged.connect(
            self._show_selected_fracture)
        self.fracture_table.verticalHeader().setDefaultSectionSize(28)
        layout.addWidget(self.fracture_table)
        return group

    def _selected_fracture_group(self):
        group = QGroupBox("裂缝几何")
        group.setObjectName("fractureSection")
        group.setMinimumHeight(225)
        layout = QHBoxLayout(group)
        layout.setSpacing(12)

        information = QFrame()
        information.setObjectName("fractureGeometryInfo")
        information.setMinimumWidth(230)
        information.setMaximumWidth(310)
        information_layout = QVBoxLayout(information)
        information_layout.setContentsMargins(12, 10, 12, 10)
        information_layout.setSpacing(6)
        self.selected_title = QLabel("选择一条裂缝查看几何数据")
        self.selected_title.setObjectName("fractureDetailTitle")
        information_layout.addWidget(self.selected_title)
        self.selected_meta = QLabel("集合：—\n顶点数：—")
        self.selected_meta.setObjectName("parameterDescription")
        information_layout.addWidget(self.selected_meta)
        self.normal_label = QLabel("法向量：—")
        self.normal_label.setObjectName("parameterDescription")
        self.normal_label.setWordWrap(True)
        information_layout.addWidget(self.normal_label)
        information_layout.addStretch()
        layout.addWidget(information)

        vertices = QFrame()
        vertices_layout = QVBoxLayout(vertices)
        vertices_layout.setContentsMargins(0, 0, 0, 0)
        vertices_layout.setSpacing(5)
        vertices_title = QLabel("四个顶点坐标")
        vertices_title.setObjectName("fractureDetailSubtitle")
        vertices_layout.addWidget(vertices_title)
        self.vertex_table = QTableWidget()
        _prepare_table(self.vertex_table, ("顶点", "X", "Y", "Z"), stretch_first=True)
        self.vertex_table.verticalHeader().setDefaultSectionSize(28)
        self.vertex_table.setFixedHeight(148)
        self.vertex_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        vertices_layout.addWidget(self.vertex_table)
        layout.addWidget(vertices, 1)
        return group

    def set_values(self, values, module_key):
        natural = (values or {}).get("natural_fractures") or {}
        summary = natural.get("summary") or {}
        fractures = list(natural.get("fractures") or [])
        self._fractures = fractures
        declared = int(natural.get("fracture_count") or 0)
        parsed = len(fractures)
        metrics = {
            "fracture_count": declared,
            "node_count": int(natural.get("node_count") or 0),
            "set_count": len(natural.get("sets") or []),
            "property_count": int(natural.get("property_count") or 0),
        }
        for key, card in self.metric_cards.items():
            card.set_value(metrics.get(key) if natural else None)

        if natural and declared != parsed:
            self.count_warning.setText(
                f"声明数量 {declared} 条，实际解析 {parsed} 条，请检查源数据。")
            self.count_warning.show()
        else:
            self.count_warning.hide()
        self._set_coordinates(summary.get("bbox_min"), summary.get("bbox_max"))
        self._set_sets(natural.get("sets") or [])
        self._set_statistics(summary)
        self._set_fractures(fractures)

    def _set_coordinates(self, minimum, maximum):
        low = list(minimum or [])
        high = list(maximum or [])
        for axis in range(3):
            min_value = low[axis] if axis < len(low) else None
            max_value = high[axis] if axis < len(high) else None
            span = (
                max_value - min_value
                if isinstance(min_value, (int, float))
                and isinstance(max_value, (int, float)) else None)
            for column, value in enumerate((min_value, max_value, span)):
                self.coordinate_table.setItem(axis, column, _item(value))

    def _set_sets(self, rows):
        self.set_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            payload = row if isinstance(row, dict) else {}
            self.set_table.setItem(row_index, 0, _item(payload.get("set_id")))
            self.set_table.setItem(
                row_index, 1,
                _item(payload.get("set_name"), Qt.AlignLeft))

    def _set_statistics(self, summary):
        definitions = (
            ("渗透率", "mD", summary.get("permeability") or {}),
            ("压缩系数", "—", summary.get("compressibility") or {}),
            ("开度", "m", summary.get("aperture") or {}),
        )
        available = [row for row in definitions if row[2]]
        self.statistics_table.setRowCount(len(available))
        for row_index, (title, unit, values) in enumerate(available):
            row = (
                title, unit, values.get("count"), values.get("min"),
                values.get("max"), values.get("mean"),
            )
            for column, value in enumerate(row):
                alignment = Qt.AlignLeft if column == 0 else Qt.AlignCenter
                self.statistics_table.setItem(
                    row_index, column, _item(value, alignment))

    def _set_fractures(self, rows):
        self.fracture_table.setRowCount(len(rows))
        self.fracture_count_label.setText(
            f"共 {len(rows)} 条" if rows else "暂无数据")
        keys = (
            "fracture_id", "set_id", "vertex_count", "permeability",
            "compressibility", "aperture",
        )
        for row_index, row in enumerate(rows):
            payload = row if isinstance(row, dict) else {}
            for column, key in enumerate(keys):
                self.fracture_table.setItem(
                    row_index, column, _item(payload.get(key)))
        if rows:
            self.fracture_table.selectRow(0)
        else:
            self._clear_selected_fracture()

    def _show_selected_fracture(self):
        row = self.fracture_table.currentRow()
        if row < 0 or row >= len(self._fractures):
            self._clear_selected_fracture()
            return
        fracture = self._fractures[row]
        self.selected_title.setText(
            f"裂缝 { _value(fracture.get('fracture_id')) }")
        self.selected_meta.setText(
            f"集合：{_value(fracture.get('set_id'))}\n"
            f"顶点数：{_value(fracture.get('vertex_count'))}")
        normal = fracture.get("normal") or []
        self.normal_label.setText(
            "法向量：" + (", ".join(_value(value) for value in normal)
                         if normal else "—"))
        vertices = list(fracture.get("vertices") or [])
        self.vertex_table.setRowCount(len(vertices))
        for row_index, vertex in enumerate(vertices):
            coordinates = list(vertex or [])
            self.vertex_table.setItem(row_index, 0, _item(row_index + 1))
            for column in range(3):
                self.vertex_table.setItem(
                    row_index, column + 1,
                    _item(coordinates[column] if column < len(coordinates) else None))

    def _clear_selected_fracture(self):
        self.selected_title.setText("选择一条裂缝查看几何数据")
        self.selected_meta.setText("集合：—\n顶点数：—")
        self.normal_label.setText("法向量：—")
        self.vertex_table.setRowCount(0)

    def collect_values(self, values):
        return None

    def refresh_derived(self, values, module_key):
        return None


class HydraulicFracturePage(QWidget):
    """从井完井记录实时派生的人工裂缝只读页面。"""

    values_changed = pyqtSignal()

    def __init__(self, title, fields=(), project_state=None, parent=None):
        super().__init__(parent)
        self.group_title = title
        self.fields = tuple(fields or ())
        self.bindings = []
        self.project_state = project_state
        self._records = []
        self._local_records = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 12, 16, 14)
        outer.setSpacing(9)
        title_label = QLabel(title)
        title_label.setObjectName("parameterTitle")
        outer.addWidget(title_label)

        metrics = QHBoxLayout()
        metrics.setSpacing(9)
        self.metric_cards = {}
        for key, label in (
                ("fracture_count", "人工裂缝"),
                ("well_count", "关联井"),
                ("open_count", "当前开启"),
                ("shut_count", "当前关闭")):
            card = FractureMetricCard(label)
            metrics.addWidget(card, 1)
            self.metric_cards[key] = card
        outer.addLayout(metrics)

        self.source_status = QLabel("")
        self.source_status.setObjectName("fractureSourceStatus")
        outer.addWidget(self.source_status)

        details = QSplitter(Qt.Horizontal)
        details.setChildrenCollapsible(False)
        details.addWidget(self._list_group())
        details.addWidget(self._detail_group())
        details.setSizes((590, 300))
        outer.addWidget(details, 1)

    def _list_group(self):
        group = QGroupBox("人工裂缝列表")
        group.setObjectName("fractureSection")
        layout = QVBoxLayout(group)
        self.fracture_table = QTableWidget()
        _prepare_table(
            self.fracture_table,
            ("裂缝ID", "井名", "压裂段", "MD范围(m)", "中心坐标(m)",
             "长度(m)", "缝高(m)", "状态"),
            stretch_first=True,
        )
        self.fracture_table.itemSelectionChanged.connect(self._show_selected)
        layout.addWidget(self.fracture_table)
        return group

    def _detail_group(self):
        group = QGroupBox("裂缝详情")
        group.setObjectName("fractureSection")
        layout = QVBoxLayout(group)
        self.selected_title = QLabel("选择一条人工裂缝查看详情")
        self.selected_title.setObjectName("fractureDetailTitle")
        layout.addWidget(self.selected_title)

        self.property_table = QTableWidget()
        _prepare_table(self.property_table, ("参数", "数值", "单位"), stretch_first=True)
        self.property_table.setMaximumHeight(190)
        layout.addWidget(self.property_table)

        corners_title = QLabel("四角点坐标")
        corners_title.setObjectName("fractureDetailSubtitle")
        layout.addWidget(corners_title)
        self.corner_table = QTableWidget()
        _prepare_table(self.corner_table, ("角点", "X", "Y", "Z"), stretch_first=True)
        self.corner_table.setMaximumHeight(160)
        layout.addWidget(self.corner_table)

        events_title = QLabel("调度历史")
        events_title.setObjectName("fractureDetailSubtitle")
        layout.addWidget(events_title)
        self.event_table = QTableWidget()
        _prepare_table(self.event_table, ("时间(d)", "事件"), stretch_first=True)
        layout.addWidget(self.event_table)
        return group

    def set_values(self, values, module_key):
        self._local_records = list(
            (values or {}).get("hydraulic_fractures") or [])
        self.refresh_from_project_state()

    def refresh_from_project_state(self):
        state = (
            self.project_state.get_module_input_state(MODULE_WELL_PRODUCTION)
            if self.project_state is not None else None)
        well_values = state.parsed_data.values if state is not None else {}
        linked_records = derive_hydraulic_fractures(well_values)
        self._records = self._local_records or linked_records
        summary = hydraulic_fracture_summary(self._records)
        for key, card in self.metric_cards.items():
            card.set_value(summary.get(key))
        if self._local_records:
            self.source_status.setText(
                f"✓ 已从裂缝模块导入 {len(self._records)} 条人工裂缝")
            self.source_status.setProperty("state", "success")
        elif state is None:
            self.source_status.setText("○ 尚未导入井与生产控制数据")
            self.source_status.setProperty("state", "empty")
        elif not self._records:
            self.source_status.setText("○ 井数据中未发现带完整几何信息的人工裂缝 PERF 记录")
            self.source_status.setProperty("state", "empty")
        else:
            self.source_status.setText(
                f"✓ 已从井完井数据识别 {len(self._records)} 条人工裂缝，无需手动输入")
            self.source_status.setProperty("state", "success")
        self.source_status.style().unpolish(self.source_status)
        self.source_status.style().polish(self.source_status)
        self._set_records(self._records)

    def _set_records(self, rows):
        self.fracture_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            md_range = _range_text(row.get("md_top_m"), row.get("md_bottom_m"))
            center = " / ".join(_value(row.get(key)) for key in (
                "center_x", "center_y", "center_z"))
            values = (
                row.get("fracture_id"), row.get("well_name"), row.get("stage"),
                md_range, center, row.get("length"), row.get("height"),
                row.get("status"),
            )
            for column, value in enumerate(values):
                alignment = Qt.AlignLeft if column in (0, 1) else Qt.AlignCenter
                item = _item(value, alignment)
                if column == 7:
                    if value == "开启":
                        item.setForeground(QColor("#2f6845"))
                    elif value == "关闭":
                        item.setForeground(QColor("#8a6500"))
                self.fracture_table.setItem(row_index, column, item)
        if rows:
            self.fracture_table.selectRow(0)
        else:
            self._clear_detail()

    def _show_selected(self):
        row_index = self.fracture_table.currentRow()
        if row_index < 0 or row_index >= len(self._records):
            self._clear_detail()
            return
        row = self._records[row_index]
        self.selected_title.setText(
            f"{row.get('fracture_id', '—')} · {row.get('well_name', '—')}")
        properties = (
            ("裂缝序号", row.get("frac_id"), "—"),
            ("开度", row.get("aperture"), "m"),
            ("渗透率", row.get("perm"), "mD"),
            ("导流能力", row.get("conductivity"), "mD·m"),
        )
        self.property_table.setRowCount(len(properties))
        for row_number, values in enumerate(properties):
            for column, value in enumerate(values):
                alignment = Qt.AlignLeft if column == 0 else Qt.AlignCenter
                self.property_table.setItem(
                    row_number, column, _item(value, alignment))

        corners = list(row.get("corners") or [])
        self.corner_table.setRowCount(len(corners))
        for row_number, corner in enumerate(corners):
            values = (
                corner.get("corner_id", row_number + 1), corner.get("x_m"),
                corner.get("y_m"), corner.get("z_m"),
            )
            for column, value in enumerate(values):
                self.corner_table.setItem(row_number, column, _item(value))

        events = list(row.get("events") or [])
        self.event_table.setRowCount(len(events))
        for row_number, event in enumerate(events):
            self.event_table.setItem(row_number, 0, _item(event.get("date")))
            self.event_table.setItem(
                row_number, 1, _item(event.get("event_label"), Qt.AlignLeft))

    def _clear_detail(self):
        self.selected_title.setText("选择一条人工裂缝查看详情")
        self.property_table.setRowCount(0)
        self.corner_table.setRowCount(0)
        self.event_table.setRowCount(0)

    def collect_values(self, values):
        return None

    def refresh_derived(self, values, module_key):
        self.refresh_from_project_state()


def _range_text(minimum, maximum):
    if minimum is None and maximum is None:
        return "—"
    return f"{_value(minimum)} – {_value(maximum)}"
