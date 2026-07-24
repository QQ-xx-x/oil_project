# -*- coding: utf-8 -*-
"""井轨迹、完井定义和生产控制的专用业务页面。"""

import copy
import os
import re

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QAbstractItemView, QComboBox, QDialog, QDialogButtonBox,
    QDoubleSpinBox, QFileDialog, QFormLayout, QFrame, QGroupBox,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMessageBox, QPushButton,
    QSplitter, QTabWidget, QTableWidget, QTableWidgetItem, QVBoxLayout,
    QWidget,
)

from .perforation_geometry import (
    build_hydraulic_fractures,
    calculate_perforation_geometry,
    merge_generated_fractures,
)
from .perforation_parser import parse_perforation_file
from .well_trajectory_dev_parser import (
    build_trajectory_payload,
    parse_dev_files,
)
from .wellhead_parser import parse_wellhead_file


ROW_INDEX_ROLE = Qt.UserRole + 11
FIELD_VALUE_ROLE = Qt.UserRole + 12


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


class WellheadImportPage(QWidget):
    """井位文件选择与 WELLNAME/X/Y/KB 数据预览页面。"""

    values_changed = pyqtSignal()

    COLUMNS = (
        ("well_name", "井名 / WELLNAME"),
        ("x", "X"),
        ("y", "Y"),
        ("kb", "KB"),
    )

    def __init__(self, title, fields=(), parent=None):
        super().__init__(parent)
        self.group_title = title
        self.fields = tuple(fields or ())
        self.bindings = [(field, self) for field in self.fields]
        self._payload = {}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 12, 16, 14)
        outer.setSpacing(10)

        title_label = QLabel(title)
        title_label.setObjectName("parameterTitle")
        outer.addWidget(title_label)

        file_group = QGroupBox("井位文件")
        file_layout = QHBoxLayout(file_group)
        file_layout.setContentsMargins(12, 10, 12, 10)
        file_layout.setSpacing(8)
        file_layout.addWidget(QLabel("文件名"))
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setObjectName("wellheadFilePath")
        self.file_path_edit.setReadOnly(True)
        self.file_path_edit.setPlaceholderText("请选择包含 WELLNAME、X、Y、KB 的井位文件")
        file_layout.addWidget(self.file_path_edit, 1)
        self.browse_button = QPushButton("浏览...")
        self.browse_button.setObjectName("browseWellheadFileButton")
        self.browse_button.clicked.connect(self.browse_file)
        file_layout.addWidget(self.browse_button)
        outer.addWidget(file_group)

        data_group = QGroupBox("数据浏览")
        data_layout = QVBoxLayout(data_group)
        data_layout.setContentsMargins(10, 10, 10, 10)
        data_layout.setSpacing(7)
        self.summary_label = QLabel("尚未导入井位文件")
        self.summary_label.setObjectName("parameterDescription")
        data_layout.addWidget(self.summary_label)
        self.data_table = _table(
            tuple(title for _key, title in self.COLUMNS), editable=False)
        self.data_table.setObjectName("wellheadDataTable")
        self.data_table.setSelectionMode(QAbstractItemView.SingleSelection)
        header = self.data_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        for column in range(1, len(self.COLUMNS)):
            header.setSectionResizeMode(column, QHeaderView.Stretch)
        data_layout.addWidget(self.data_table, 1)
        outer.addWidget(data_group, 1)

    @property
    def loaded_count(self):
        return len(self._payload.get("rows") or [])

    def browse_file(self):
        current_path = str(self._payload.get("source_path") or "")
        initial_dir = (
            os.path.dirname(current_path)
            if current_path else "")
        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择井位文件",
            initial_dir,
            "井位文件 (*.txt *.dat *.data *.csv);;所有文件 (*)",
        )
        if not path:
            return False
        try:
            self.load_file(path)
        except (OSError, TypeError, ValueError, UnicodeError) as exc:
            QMessageBox.warning(
                self, "井位导入失败", str(exc) or "井位文件无法解析。")
            return False
        return True

    def load_file(self, path):
        self._payload = parse_wellhead_file(path)
        self._render()
        self.values_changed.emit()
        return copy.deepcopy(self._payload)

    def set_values(self, values, module_key):
        del module_key
        self._payload = copy.deepcopy((values or {}).get("wellhead") or {})
        self._render()

    def collect_values(self, values):
        if self._payload.get("rows"):
            values["wellhead"] = copy.deepcopy(self._payload)
        else:
            values.pop("wellhead", None)

    def refresh_derived(self, values, module_key):
        del values, module_key

    def _render(self):
        path = str(self._payload.get("source_path") or "")
        rows = [
            row for row in self._payload.get("rows") or []
            if isinstance(row, dict)
        ]
        self.file_path_edit.setText(path)
        self.file_path_edit.setToolTip(path)
        self.summary_label.setText(
            f"已读取 {len(rows)} 口井；数据按文件原值显示"
            if rows else "尚未导入井位文件")

        self.data_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            display_values = (
                row.get("well_name"),
                row.get("x_text", _display_value(row.get("x"))),
                row.get("y_text", _display_value(row.get("y"))),
                row.get("kb_text", _display_value(row.get("kb"))),
            )
            for column, value in enumerate(display_values):
                alignment = Qt.AlignLeft if column == 0 else Qt.AlignRight
                self.data_table.setItem(
                    row_index, column, _item(value, alignment))
        if rows:
            self.data_table.selectRow(0)


class HydraulicFractureGenerationDialog(QDialog):
    """为选中射孔统一设置矩形人工裂缝几何与物性。"""

    def __init__(self, initial=None, parent=None):
        super().__init__(parent)
        values = {
            "prefix": "HF",
            "length": 100.0,
            "height": 50.0,
            "azimuth_deg": 90.0,
            "dip_deg": 90.0,
            "aperture": 0.001,
            "perm": 1000.0,
            "conductivity": 1.0,
        }
        values.update(dict(initial or {}))

        self.setWindowTitle("添加人工裂缝")
        self.setObjectName("hydraulicFractureGenerationDialog")
        self.resize(470, 430)
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)

        note = QLabel(
            "每条选中射孔生成一条矩形人工裂缝；裂缝中心取射孔中心坐标。"
            "方位角从正北顺时针计，倾角为0°到90°。")
        note.setObjectName("parameterDescription")
        note.setWordWrap(True)
        root.addWidget(note)

        form = QFormLayout()
        form.setSpacing(10)
        self.prefix_edit = QLineEdit(str(values["prefix"]))
        self.prefix_edit.setObjectName("generatedFracturePrefix")
        form.addRow("裂缝编号前缀", self.prefix_edit)

        self.parameter_editors = {}
        specs = (
            ("length", "裂缝长度", " m", 0.000001, 1000000.0, 6),
            ("height", "裂缝高度", " m", 0.000001, 1000000.0, 6),
            ("azimuth_deg", "裂缝方位角", " °", 0.0, 360.0, 4),
            ("dip_deg", "裂缝倾角", " °", 0.0, 90.0, 4),
            ("aperture", "裂缝开度", " m", 0.000000001, 1000.0, 9),
            ("perm", "裂缝渗透率", " mD", 0.000001, 1000000000.0, 6),
            (
                "conductivity", "裂缝导流能力", " mD·m",
                0.000001, 1000000000.0, 6,
            ),
        )
        for key, label, suffix, minimum, maximum, decimals in specs:
            editor = QDoubleSpinBox()
            editor.setObjectName(f"generatedFracture_{key}")
            editor.setDecimals(decimals)
            editor.setRange(minimum, maximum)
            editor.setValue(float(values[key]))
            editor.setSuffix(suffix)
            editor.setKeyboardTracking(False)
            form.addRow(label, editor)
            self.parameter_editors[key] = editor
        root.addLayout(form)

        buttons = QDialogButtonBox()
        ok_button = QPushButton("生成")
        cancel_button = QPushButton("取消")
        buttons.addButton(ok_button, QDialogButtonBox.AcceptRole)
        buttons.addButton(cancel_button, QDialogButtonBox.RejectRole)
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        root.addWidget(buttons)

    def parameters(self):
        return {
            "prefix": self.prefix_edit.text().strip(),
            **{
                key: editor.value()
                for key, editor in self.parameter_editors.items()
            },
        }


class PerforationImportPage(QWidget):
    """射孔导入、轨迹插值计算及可选人工裂缝生成页面。"""

    values_changed = pyqtSignal()

    COLUMNS = (
        ("well_name", "井名 / WELLNAME"),
        ("md1", "起始测深 / MD1"),
        ("md2", "结束测深 / MD2"),
    )

    def __init__(self, title, fields=(), parent=None):
        super().__init__(parent)
        self.group_title = title
        self.fields = tuple(fields or ())
        self.bindings = [(field, self) for field in self.fields]
        self._payload = {}
        self._trajectory_payload = {}
        self._trajectory_signature_value = ()
        self._generated_fractures = []
        self._fracture_parameters = {}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 12, 16, 14)
        outer.setSpacing(10)

        title_label = QLabel(title)
        title_label.setObjectName("parameterTitle")
        outer.addWidget(title_label)

        file_group = QGroupBox("射孔文件")
        file_layout = QHBoxLayout(file_group)
        file_layout.setContentsMargins(12, 10, 12, 10)
        file_layout.setSpacing(8)
        file_layout.addWidget(QLabel("文件名"))
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setObjectName("perforationFilePath")
        self.file_path_edit.setReadOnly(True)
        self.file_path_edit.setPlaceholderText(
            "请选择包含 WELLNAME、MD1、MD2 的射孔文件")
        file_layout.addWidget(self.file_path_edit, 1)
        self.browse_button = QPushButton("浏览...")
        self.browse_button.setObjectName("browsePerforationFileButton")
        self.browse_button.clicked.connect(self.browse_file)
        file_layout.addWidget(self.browse_button)
        outer.addWidget(file_group)

        calculation_group = QGroupBox("射孔空间计算")
        calculation_layout = QVBoxLayout(calculation_group)
        calculation_layout.setContentsMargins(12, 10, 12, 10)
        calculation_layout.setSpacing(7)
        action_row = QHBoxLayout()
        self.calculate_button = QPushButton("计算射孔位置")
        self.calculate_button.setObjectName("calculatePerforationPositionButton")
        self.calculate_button.clicked.connect(self.calculate_positions)
        action_row.addWidget(self.calculate_button)
        self.clear_calculation_button = QPushButton("清除计算结果")
        self.clear_calculation_button.setObjectName(
            "clearPerforationCalculationButton")
        self.clear_calculation_button.clicked.connect(
            self.clear_calculation)
        action_row.addWidget(self.clear_calculation_button)
        action_row.addSpacing(12)
        self.select_all_button = QPushButton("全选成功项")
        self.select_all_button.clicked.connect(
            lambda: self._set_all_calculated_checked(True))
        action_row.addWidget(self.select_all_button)
        self.select_none_button = QPushButton("取消全选")
        self.select_none_button.clicked.connect(
            lambda: self._set_all_calculated_checked(False))
        action_row.addWidget(self.select_none_button)
        self.add_fracture_button = QPushButton("为选中射孔添加人工裂缝")
        self.add_fracture_button.setObjectName(
            "addHydraulicFracturesFromPerforationButton")
        self.add_fracture_button.clicked.connect(
            self._open_fracture_generation)
        action_row.addWidget(self.add_fracture_button)
        action_row.addStretch()
        calculation_layout.addLayout(action_row)
        self.calculation_summary_label = QLabel(
            "导入射孔和DEV井轨迹后，可计算射孔起点、终点及中心坐标")
        self.calculation_summary_label.setObjectName("parameterDescription")
        calculation_layout.addWidget(self.calculation_summary_label)
        self.generated_fracture_label = QLabel("")
        self.generated_fracture_label.setObjectName("parameterDescription")
        calculation_layout.addWidget(self.generated_fracture_label)
        outer.addWidget(calculation_group)

        data_group = QGroupBox("数据浏览与计算结果")
        data_layout = QVBoxLayout(data_group)
        data_layout.setContentsMargins(10, 10, 10, 10)
        data_layout.setSpacing(7)
        self.summary_label = QLabel("尚未导入射孔文件")
        self.summary_label.setObjectName("parameterDescription")
        data_layout.addWidget(self.summary_label)

        self.data_tabs = QTabWidget()
        self.data_tabs.setObjectName("perforationDataTabs")
        self.data_table = _table(
            tuple(title for _key, title in self.COLUMNS), editable=False)
        self.data_table.setObjectName("perforationDataTable")
        self.data_table.setSelectionMode(QAbstractItemView.SingleSelection)
        header = self.data_table.horizontalHeader()
        for column in range(len(self.COLUMNS)):
            header.setSectionResizeMode(column, QHeaderView.Stretch)
        self.data_tabs.addTab(self.data_table, "原始射孔数据")

        self.calculated_table = _table((
            "添加裂缝", "射孔ID", "井名", "MD范围 (m)",
            "起点 XYZ (m)", "终点 XYZ (m)", "中心 XYZ (m)",
            "井段/弦长 (m)", "计算状态",
        ), editable=False)
        self.calculated_table.setObjectName("calculatedPerforationTable")
        self.calculated_table.setSelectionMode(
            QAbstractItemView.SingleSelection)
        calculated_header = self.calculated_table.horizontalHeader()
        for column in (0, 1, 2, 3, 7, 8):
            calculated_header.setSectionResizeMode(
                column, QHeaderView.ResizeToContents)
        for column in (4, 5, 6):
            calculated_header.setSectionResizeMode(
                column, QHeaderView.Stretch)
        self.data_tabs.addTab(self.calculated_table, "射孔计算结果")
        data_layout.addWidget(self.data_tabs, 1)
        outer.addWidget(data_group, 1)

    @property
    def loaded_count(self):
        return len(self._payload.get("rows") or [])

    def browse_file(self):
        current_path = str(self._payload.get("source_path") or "")
        initial_dir = (
            os.path.dirname(current_path)
            if current_path else "")
        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择射孔文件",
            initial_dir,
            "射孔文件 (*.txt *.dat *.data *.csv);;所有文件 (*)",
        )
        if not path:
            return False
        try:
            self.load_file(path)
        except (OSError, TypeError, ValueError, UnicodeError) as exc:
            QMessageBox.warning(
                self, "射孔导入失败", str(exc) or "射孔文件无法解析。")
            return False
        return True

    def load_file(self, path):
        self._payload = parse_perforation_file(path)
        self._payload.pop("calculation", None)
        self._generated_fractures = []
        self._render()
        self.values_changed.emit()
        return copy.deepcopy(self._payload)

    def set_values(self, values, module_key):
        del module_key
        source_values = values or {}
        self._payload = copy.deepcopy(
            source_values.get("perforation") or {})
        self._trajectory_payload = copy.deepcopy(
            source_values.get("well_trajectory") or {})
        self._trajectory_signature_value = _trajectory_signature(
            self._trajectory_payload)
        self._generated_fractures = copy.deepcopy(list(
            source_values.get("generated_hydraulic_fractures") or []))
        self._fracture_parameters = copy.deepcopy(
            source_values.get("generated_fracture_parameters") or {})
        self._render()

    def collect_values(self, values):
        if self._payload.get("rows"):
            values["perforation"] = copy.deepcopy(self._payload)
        else:
            values.pop("perforation", None)
        if self._generated_fractures:
            values["generated_hydraulic_fractures"] = copy.deepcopy(
                self._generated_fractures)
            values["generated_fracture_parameters"] = copy.deepcopy(
                self._fracture_parameters)
        else:
            values.pop("generated_hydraulic_fractures", None)
            values.pop("generated_fracture_parameters", None)

    def refresh_derived(self, values, module_key):
        del module_key
        trajectory = copy.deepcopy(
            (values or {}).get("well_trajectory") or {})
        signature = _trajectory_signature(trajectory)
        trajectory_changed = (
            signature != self._trajectory_signature_value)
        self._trajectory_payload = trajectory
        self._trajectory_signature_value = signature
        if trajectory_changed and self._payload.get("calculation"):
            self._payload.pop("calculation", None)
            self._generated_fractures = []
            self._render_calculated()
            self._render_generated_fracture_status()
            self.calculation_summary_label.setText(
                "井轨迹已变化，原射孔计算和由其生成的人工裂缝已清除，请重新计算")
            return
        self._update_calculation_summary()

    def calculate_positions(self):
        if not self._payload.get("rows"):
            QMessageBox.warning(
                self, "无法计算", "请先导入射孔文件。")
            return None
        calculation = calculate_perforation_geometry(
            self._payload, self._trajectory_payload)
        self._payload["calculation"] = calculation
        self._render_calculated()
        self.data_tabs.setCurrentWidget(self.calculated_table)
        self.values_changed.emit()
        return copy.deepcopy(calculation)

    def clear_calculation(self):
        self._payload.pop("calculation", None)
        self._render_calculated()
        self.values_changed.emit()

    def _set_all_calculated_checked(self, checked):
        for row_index in range(self.calculated_table.rowCount()):
            item = self.calculated_table.item(row_index, 0)
            if item is not None and item.flags() & Qt.ItemIsUserCheckable:
                item.setCheckState(Qt.Checked if checked else Qt.Unchecked)

    def _selected_calculated_rows(self):
        rows = list(
            (self._payload.get("calculation") or {}).get("rows") or [])
        selected = []
        for row_index, row in enumerate(rows):
            item = self.calculated_table.item(row_index, 0)
            if (
                    item is not None
                    and item.checkState() == Qt.Checked
                    and row.get("status") == "success"):
                selected.append({
                    **copy.deepcopy(row),
                    "eligible_for_fracture": True,
                })
        return selected

    def _open_fracture_generation(self):
        selected = self._selected_calculated_rows()
        if not selected:
            QMessageBox.warning(
                self, "没有选中射孔",
                "请先勾选至少一条计算成功的射孔记录。")
            return
        dialog = HydraulicFractureGenerationDialog(
            self._fracture_parameters, self)
        if dialog.exec_() != QDialog.Accepted:
            return
        parameters = dialog.parameters()
        try:
            candidates = build_hydraulic_fractures(selected, parameters)
        except (TypeError, ValueError) as exc:
            QMessageBox.warning(
                self, "人工裂缝参数无效", str(exc) or "无法生成人工裂缝。")
            return

        existing_ids = {
            str(row.get("fracture_id") or "")
            for row in self._generated_fractures
            if isinstance(row, dict)
        }
        duplicate_ids = [
            str(row.get("fracture_id") or "")
            for row in candidates
            if str(row.get("fracture_id") or "") in existing_ids
        ]
        replace_duplicates = True
        if duplicate_ids:
            answer = QMessageBox.question(
                self,
                "发现重复人工裂缝",
                f"有 {len(duplicate_ids)} 条裂缝已存在。\n"
                "选择“是”替换已有裂缝，选择“否”跳过重复项。",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                QMessageBox.Yes,
            )
            if answer == QMessageBox.Cancel:
                return
            replace_duplicates = answer == QMessageBox.Yes
        self._merge_fracture_candidates(
            candidates, parameters, replace_duplicates)

    def add_selected_fractures(
            self, parameters, replace_duplicates=True):
        selected = self._selected_calculated_rows()
        candidates = build_hydraulic_fractures(selected, parameters)
        return self._merge_fracture_candidates(
            candidates, parameters, replace_duplicates)

    def _merge_fracture_candidates(
            self, candidates, parameters, replace_duplicates):
        merged, added, affected = merge_generated_fractures(
            self._generated_fractures,
            candidates,
            replace_duplicates=replace_duplicates,
        )
        self._generated_fractures = merged
        self._fracture_parameters = copy.deepcopy(parameters)
        self._render_generated_fracture_status()
        self.values_changed.emit()
        return {
            "fractures": copy.deepcopy(merged),
            "added_count": added,
            "replaced_or_skipped_count": affected,
            "replace_duplicates": bool(replace_duplicates),
        }

    def _render(self):
        path = str(self._payload.get("source_path") or "")
        rows = [
            row for row in self._payload.get("rows") or []
            if isinstance(row, dict)
        ]
        summary = self._payload.get("summary") or {}
        well_count = int(summary.get("well_count") or 0)
        self.file_path_edit.setText(path)
        self.file_path_edit.setToolTip(path)
        self.summary_label.setText(
            f"已读取 {len(rows)} 条射孔记录，涉及 {well_count} 口井；"
            "数据按文件原值和原始顺序显示"
            if rows else "尚未导入射孔文件")

        self.data_table.setUpdatesEnabled(False)
        try:
            self.data_table.setRowCount(len(rows))
            for row_index, row in enumerate(rows):
                display_values = (
                    row.get("well_name"),
                    row.get("md1_text", _display_value(row.get("md1"))),
                    row.get("md2_text", _display_value(row.get("md2"))),
                )
                for column, value in enumerate(display_values):
                    alignment = Qt.AlignLeft if column == 0 else Qt.AlignRight
                    self.data_table.setItem(
                        row_index, column, _item(value, alignment))
        finally:
            self.data_table.setUpdatesEnabled(True)
        if rows:
            self.data_table.selectRow(0)
        self._render_calculated()
        if (self._payload.get("calculation") or {}).get("rows"):
            self.data_tabs.setCurrentWidget(self.calculated_table)
        self._render_generated_fracture_status()

    def _render_calculated(self):
        calculation = self._payload.get("calculation") or {}
        rows = [
            row for row in calculation.get("rows") or []
            if isinstance(row, dict)
        ]
        self.calculated_table.setUpdatesEnabled(False)
        try:
            self.calculated_table.setRowCount(len(rows))
            for row_index, row in enumerate(rows):
                check_item = QTableWidgetItem()
                check_item.setTextAlignment(Qt.AlignCenter)
                if row.get("status") == "success":
                    check_item.setFlags(
                        Qt.ItemIsEnabled
                        | Qt.ItemIsSelectable
                        | Qt.ItemIsUserCheckable)
                    check_item.setCheckState(Qt.Unchecked)
                else:
                    check_item.setFlags(Qt.ItemIsEnabled)
                self.calculated_table.setItem(row_index, 0, check_item)

                length_text = "—"
                if row.get("status") == "success":
                    length_text = (
                        f"{float(row['measured_length']):.6g} / "
                        f"{float(row['spatial_chord_length']):.6g}")
                values = (
                    row.get("perforation_id"),
                    row.get("well_name"),
                    _range_text(row.get("md1"), row.get("md2")),
                    _xyz_text(row, "start"),
                    _xyz_text(row, "end"),
                    _xyz_text(row, "center"),
                    length_text,
                    row.get("status_text"),
                )
                for column, value in enumerate(values, 1):
                    alignment = (
                        Qt.AlignLeft if column in (1, 2, 8)
                        else Qt.AlignCenter)
                    item = _item(value, alignment)
                    if column == 8:
                        item.setForeground(
                            QColor("#2f7b4e")
                            if row.get("status") == "success"
                            else QColor("#b25d32"))
                    self.calculated_table.setItem(
                        row_index, column, item)
        finally:
            self.calculated_table.setUpdatesEnabled(True)
        self._update_calculation_summary()
        self.clear_calculation_button.setEnabled(bool(rows))
        self.select_all_button.setEnabled(bool(rows))
        self.select_none_button.setEnabled(bool(rows))
        self.add_fracture_button.setEnabled(any(
            row.get("status") == "success" for row in rows))

    def _update_calculation_summary(self):
        trajectory_count = len([
            well for well in self._trajectory_payload.get("wells") or []
            if isinstance(well, dict)
        ])
        summary = (
            (self._payload.get("calculation") or {}).get("summary") or {})
        if summary:
            self.calculation_summary_label.setText(
                f"计算完成：成功 {int(summary.get('success_count') or 0)} 条，"
                f"失败 {int(summary.get('error_count') or 0)} 条；"
                f"当前已导入 {trajectory_count} 口DEV井轨迹")
        else:
            self.calculation_summary_label.setText(
                f"当前已导入 {trajectory_count} 口DEV井轨迹；"
                "点击“计算射孔位置”生成空间坐标")

    def _render_generated_fracture_status(self):
        count = len(self._generated_fractures)
        self.generated_fracture_label.setText(
            f"已生成 {count} 条人工裂缝；应用后可在人工裂缝模块中查看"
            if count else "尚未从射孔生成任何人工裂缝")


class WellTrajectoryPage(QWidget):
    """Petrel DEV 文件导入、井口匹配和单井轨迹预览页面。"""

    values_changed = pyqtSignal()

    TRACK_COLUMNS = (
        ("md_m", "测深 MD (m)"),
        ("x_m", "X (m)"),
        ("y_m", "Y (m)"),
        ("z_m", "Z 高程 (m)"),
        ("tvd_m", "TVD (m)"),
        ("dx_m", "DX (m)"),
        ("dy_m", "DY (m)"),
        ("azim_deg", "方位角 AZIM (°)"),
        ("incl_deg", "井斜角 INCL (°)"),
        ("dls", "狗腿度 DLS"),
    )
    VERTICAL_MODES = (
        ("elevation_z", "原始 Z 高程（向上为正）"),
        ("tvd", "TVD（从 KB 向下为正）"),
        ("subsea_depth", "海拔以下深度 -Z（向下为正）"),
    )

    def __init__(self, title, fields=(), parent=None):
        super().__init__(parent)
        self.group_title = title
        self.fields = tuple(fields or ())
        self.bindings = [(field, self) for field in self.fields]
        self._payload = {}
        self._wellheads = {}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 12, 16, 14)
        outer.setSpacing(10)
        title_label = QLabel(title)
        title_label.setObjectName("parameterTitle")
        outer.addWidget(title_label)

        file_group = QGroupBox("Petrel DEV 井轨迹文件")
        file_layout = QVBoxLayout(file_group)
        file_layout.setContentsMargins(12, 10, 12, 10)
        file_layout.setSpacing(8)

        file_row = QHBoxLayout()
        file_row.addWidget(QLabel("文件名"))
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setObjectName("wellTrajectoryDevFilePath")
        self.file_path_edit.setReadOnly(True)
        self.file_path_edit.setPlaceholderText(
            "请选择一个或多个 Petrel 井轨迹 DEV 文件")
        file_row.addWidget(self.file_path_edit, 1)
        self.browse_button = QPushButton("浏览...")
        self.browse_button.setObjectName("browseWellTrajectoryDevButton")
        self.browse_button.clicked.connect(self.browse_files)
        file_row.addWidget(self.browse_button)
        self.remove_button = QPushButton("移除选中井")
        self.remove_button.setObjectName("removeSelectedWellTrajectoryButton")
        self.remove_button.clicked.connect(self._remove_selected_well)
        file_row.addWidget(self.remove_button)
        self.clear_button = QPushButton("清空")
        self.clear_button.setObjectName("clearWellTrajectoryButton")
        self.clear_button.clicked.connect(self._clear_trajectories)
        file_row.addWidget(self.clear_button)
        file_layout.addLayout(file_row)

        setting_row = QHBoxLayout()
        setting_row.addWidget(QLabel("垂向坐标解释"))
        self.vertical_mode_combo = QComboBox()
        self.vertical_mode_combo.setObjectName(
            "wellTrajectoryVerticalModeCombo")
        for key, label in self.VERTICAL_MODES:
            self.vertical_mode_combo.addItem(label, key)
        self.vertical_mode_combo.currentIndexChanged.connect(
            self._vertical_mode_changed)
        setting_row.addWidget(self.vertical_mode_combo)
        self.file_summary_label = QLabel("尚未导入 DEV 井轨迹")
        self.file_summary_label.setObjectName("parameterDescription")
        setting_row.addWidget(self.file_summary_label, 1)
        file_layout.addLayout(setting_row)
        outer.addWidget(file_group)

        metrics = QHBoxLayout()
        metrics.setSpacing(8)
        self.metric_cards = {}
        for key, label in (
                ("well_count", "井数量 / Wells"),
                ("track_count", "轨迹点 / Track points"),
                ("matched_count", "井位匹配 / Matched"),
                ("warning_count", "质量提示 / Warnings")):
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
            "井名", "轨迹点", "MD范围 (m)", "井位匹配"))
        self.well_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.well_table.itemSelectionChanged.connect(
            self._render_selected_well)
        header = self.well_table.horizontalHeader()
        header.setMinimumSectionSize(52)
        for column in (0, 1):
            header.setSectionResizeMode(column, QHeaderView.ResizeToContents)
        for column in (2, 3):
            header.setSectionResizeMode(column, QHeaderView.Stretch)
        for column, tooltip in enumerate((
                "井名 / Well name",
                "轨迹点数量 / Track points",
                "测深范围 / MD range (m)",
                "与井位模块中同名井的坐标匹配状态")):
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

        self.detail_tabs = QTabWidget()
        self.detail_tabs.setObjectName("wellTrajectoryDetailTabs")

        self.track_table = _table(
            tuple(title for _key, title in self.TRACK_COLUMNS),
            editable=False,
        )
        self.track_table.setObjectName("wellTrajectoryDataTable")
        self.track_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.track_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents)
        self.detail_tabs.addTab(self.track_table, "轨迹数据")

        self.metadata_table = _table(("项目", "值"), editable=False)
        self.metadata_table.setObjectName("wellTrajectoryMetadataTable")
        self.metadata_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.metadata_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeToContents)
        self.metadata_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.Stretch)
        self.detail_tabs.addTab(self.metadata_table, "井信息")

        self.quality_table = _table(("级别", "质量检查"), editable=False)
        self.quality_table.setObjectName("wellTrajectoryQualityTable")
        self.quality_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.quality_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeToContents)
        self.quality_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.Stretch)
        self.detail_tabs.addTab(self.quality_table, "质量检查")
        layout.addWidget(self.detail_tabs, 1)
        return group

    def set_values(self, values, module_key):
        del module_key
        source_values = values or {}
        self._wellheads = _wellhead_index(source_values.get("wellhead") or {})
        payload = copy.deepcopy(source_values.get("well_trajectory") or {})
        if not (payload.get("wells") or []):
            payload = _legacy_trajectory_payload(
                source_values.get("wells") or {})
        self._payload = payload
        self._render()

    @property
    def loaded_count(self):
        return int(
            (self._payload.get("summary") or {}).get(
                "track_point_count") or 0)

    @property
    def loaded_well_count(self):
        return len(self._trajectory_wells())

    def browse_files(self):
        paths = list(self._payload.get("source_paths") or [])
        initial_dir = os.path.dirname(paths[0]) if paths else ""
        selected, _ = QFileDialog.getOpenFileNames(
            self,
            "选择 Petrel DEV 井轨迹文件",
            initial_dir,
            "Petrel 井轨迹 (*.dev);;所有文件 (*)",
        )
        if not selected:
            return False
        try:
            self.load_files(selected, merge=True)
        except (OSError, TypeError, ValueError, UnicodeError) as exc:
            QMessageBox.warning(
                self, "井轨迹导入失败", str(exc) or "DEV 文件无法解析。")
            return False
        return True

    def load_file(self, path):
        return self.load_files([path], merge=True)

    def load_files(self, paths, merge=True):
        imported = parse_dev_files(paths)
        imported_wells = list(imported.get("wells") or [])
        if merge:
            order = []
            by_name = {}
            for well in self._trajectory_wells() + imported_wells:
                name = str(well.get("well_name") or "")
                if name not in by_name:
                    order.append(name)
                by_name[name] = copy.deepcopy(well)
            wells = [by_name[name] for name in order if name in by_name]
        else:
            wells = copy.deepcopy(imported_wells)
        self._payload = build_trajectory_payload(
            wells, self._vertical_mode())
        self._render(select_well=(
            imported_wells[0].get("well_name") if imported_wells else ""))
        self.values_changed.emit()
        return copy.deepcopy(self._payload)

    def collect_values(self, values):
        if self._trajectory_wells():
            self._payload["vertical_mode"] = self._vertical_mode()
            values["well_trajectory"] = copy.deepcopy(self._payload)
        else:
            values.pop("well_trajectory", None)

    def refresh_derived(self, values, module_key):
        del module_key
        self._wellheads = _wellhead_index(
            (values or {}).get("wellhead") or {})
        self._render_well_list()
        self._render_selected_well()

    def _trajectory_wells(self):
        return [
            well for well in self._payload.get("wells") or []
            if isinstance(well, dict)
        ]

    def _vertical_mode(self):
        value = self.vertical_mode_combo.currentData()
        return str(value or "elevation_z")

    def _vertical_mode_changed(self):
        if not self._payload:
            return
        self._payload["vertical_mode"] = self._vertical_mode()
        self._update_file_summary()
        self.values_changed.emit()

    def _render(self, select_well=""):
        mode = str(self._payload.get("vertical_mode") or "elevation_z")
        index = self.vertical_mode_combo.findData(mode)
        self.vertical_mode_combo.blockSignals(True)
        self.vertical_mode_combo.setCurrentIndex(max(0, index))
        self.vertical_mode_combo.blockSignals(False)
        self._update_file_summary()
        self._render_metrics()
        self._render_well_list(select_well=select_well)

    def _update_file_summary(self):
        wells = self._trajectory_wells()
        paths = [
            str(well.get("source_path") or "") for well in wells
            if str(well.get("source_path") or "")
        ]
        if len(paths) == 1:
            path_text = paths[0]
        elif paths:
            path_text = f"已选择 {len(paths)} 个 DEV 文件"
        else:
            path_text = ""
        self.file_path_edit.setText(path_text)
        self.file_path_edit.setToolTip("\n".join(paths))
        if wells:
            point_count = sum(len(well.get("rows") or []) for well in wells)
            mode_label = self.vertical_mode_combo.currentText()
            self.file_summary_label.setText(
                f"已读取 {len(wells)} 口井、{point_count} 个轨迹点；"
                f"垂向解释：{mode_label}")
        else:
            self.file_summary_label.setText("尚未导入 DEV 井轨迹")

    def _render_metrics(self):
        wells = self._trajectory_wells()
        matches = sum(
            self._wellhead_match(well)[0] == "match" for well in wells)
        warning_count = sum(
            level != "通过"
            for well in wells
            for level, _message in self._quality_messages(well)
        )
        metrics = {
            "well_count": len(wells),
            "track_count": sum(
                len(well.get("rows") or []) for well in wells),
            "matched_count": f"{matches}/{len(wells)}" if wells else None,
            "warning_count": warning_count,
        }
        for key, card in self.metric_cards.items():
            card.set_value(metrics.get(key))

    def _render_well_list(self, select_well=""):
        previous = self._selected_well_name()
        target = str(select_well or previous)
        wells = self._trajectory_wells()
        self.well_table.blockSignals(True)
        self.well_table.setRowCount(len(wells))
        selected_row = 0
        for row_index, well in enumerate(wells):
            name = str(well.get("well_name") or "")
            if name == target:
                selected_row = row_index
            summary = well.get("summary") or {}
            match_key, match_text, match_detail = self._wellhead_match(well)
            values = (
                name,
                len(well.get("rows") or []),
                _range_text(summary.get("md_min"), summary.get("md_max")),
                match_text,
            )
            for column, value in enumerate(values):
                alignment = Qt.AlignLeft if column == 0 else Qt.AlignCenter
                item = _item(value, alignment)
                item.setData(Qt.UserRole, name)
                if column == 3:
                    item.setToolTip(match_detail)
                    item.setForeground({
                        "match": QColor("#2f7b4e"),
                        "mismatch": QColor("#b25d32"),
                    }.get(match_key, QColor("#946200")))
                self.well_table.setItem(row_index, column, item)
        self.well_table.blockSignals(False)
        if wells:
            self.well_table.selectRow(selected_row)
        else:
            self._render_selected_well()

    def _selected_well_name(self):
        row = self.well_table.currentRow()
        item = self.well_table.item(row, 0) if row >= 0 else None
        return str(item.data(Qt.UserRole) or "") if item is not None else ""

    def _selected_well(self):
        well_name = self._selected_well_name()
        return next((
            well for well in self._trajectory_wells()
            if str(well.get("well_name") or "") == well_name
        ), None)

    def _render_selected_well(self):
        well = self._selected_well()
        well_name = str((well or {}).get("well_name") or "")
        self.track_title.setText(
            f"{well_name} · DEV 井轨迹" if well_name else "请选择一口井")
        rows = list((well or {}).get("rows") or [])
        self.track_table.setUpdatesEnabled(False)
        self.track_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            for column, (key, _title) in enumerate(self.TRACK_COLUMNS):
                display = row.get(
                    f"{key}_text", _display_value(row.get(key)))
                self.track_table.setItem(
                    row_index, column,
                    _item(display, Qt.AlignRight))
        self.track_table.setUpdatesEnabled(True)
        self._render_metadata(well)
        self._render_quality(well)

    def _render_metadata(self, well):
        metadata = (well or {}).get("metadata") or {}
        summary = (well or {}).get("summary") or {}
        items = (
            ("文件", (well or {}).get("file_name")),
            ("井名", (well or {}).get("well_name")),
            ("测斜名称", metadata.get("survey_name")),
            ("井口 X (m)", metadata.get("wellhead_x")),
            ("井口 Y (m)", metadata.get("wellhead_y")),
            ("KB (m)", metadata.get("wellhead_kb")),
            ("井类型", metadata.get("well_type")),
            ("坐标系", metadata.get("coordinate_system")),
            ("方位角参考", metadata.get("azimuth_reference")),
            ("深度参考", metadata.get("depth_reference")),
            ("轨迹点数", summary.get("track_point_count")),
            ("MD范围 (m)", _range_text(
                summary.get("md_min"), summary.get("md_max"))),
            ("最大井斜角 (°)", summary.get("incl_max")),
            ("最大DLS", summary.get("dls_max")),
        )
        self.metadata_table.setRowCount(len(items) if well else 0)
        for row_index, (label, value) in enumerate(items if well else ()):
            self.metadata_table.setItem(
                row_index, 0, _item(label, Qt.AlignLeft))
            self.metadata_table.setItem(
                row_index, 1, _item(value, Qt.AlignLeft))

    def _render_quality(self, well):
        messages = self._quality_messages(well) if well else []
        self.quality_table.setRowCount(len(messages))
        for row_index, (level, message) in enumerate(messages):
            level_item = _item(level, Qt.AlignCenter)
            level_item.setForeground(
                QColor("#2f7b4e") if level == "通过" else QColor("#946200"))
            self.quality_table.setItem(row_index, 0, level_item)
            self.quality_table.setItem(
                row_index, 1, _item(message, Qt.AlignLeft))

    def _quality_messages(self, well):
        if not well:
            return []
        messages = [
            ("提示", str(message))
            for message in well.get("warnings") or []
        ]
        match_key, match_text, match_detail = self._wellhead_match(well)
        messages.append((
            "通过" if match_key == "match" else "提示",
            f"井位匹配：{match_text}。{match_detail}",
        ))
        summary = well.get("summary") or {}
        if summary.get("tvd_z_consistent") is True:
            messages.append((
                "通过",
                "TVD 与 KB-Z 一致，最大误差 "
                f"{float(summary.get('tvd_z_max_error') or 0.0):.6g} m。",
            ))
        messages.append(("通过", "MD 严格递增，轨迹点数不少于 2。"))
        return messages

    def _wellhead_match(self, well):
        well_name = str((well or {}).get("well_name") or "")
        wellhead = self._wellheads.get(well_name)
        if wellhead is None:
            return (
                "unmatched",
                "未找到井位",
                f"井位模块中没有同名井 {well_name}。",
            )
        metadata = (well or {}).get("metadata") or {}
        values = (
            metadata.get("wellhead_x"),
            metadata.get("wellhead_y"),
            metadata.get("wellhead_kb"),
        )
        if any(value is None for value in values):
            return (
                "unavailable",
                "DEV井口不完整",
                "DEV 文件头缺少 X、Y 或 KB，无法进行坐标匹配。",
            )
        differences = (
            abs(float(values[0]) - float(wellhead["x"])),
            abs(float(values[1]) - float(wellhead["y"])),
            abs(float(values[2]) - float(wellhead["kb"])),
        )
        detail = (
            f"ΔX={differences[0]:.6g} m，"
            f"ΔY={differences[1]:.6g} m，"
            f"ΔKB={differences[2]:.6g} m"
        )
        if all(difference <= 0.01 for difference in differences):
            return "match", "一致", detail
        return "mismatch", "不一致", detail

    def _remove_selected_well(self):
        well_name = self._selected_well_name()
        if not well_name:
            return
        wells = [
            copy.deepcopy(well) for well in self._trajectory_wells()
            if str(well.get("well_name") or "") != well_name
        ]
        self._payload = build_trajectory_payload(
            wells, self._vertical_mode())
        self._render()
        self.values_changed.emit()

    def _clear_trajectories(self):
        self._payload = build_trajectory_payload(
            [], self._vertical_mode())
        self._render()
        self.values_changed.emit()


def _wellhead_index(payload):
    return {
        str(row.get("well_name") or "").strip(): row
        for row in (payload or {}).get("rows") or []
        if isinstance(row, dict)
        and str(row.get("well_name") or "").strip()
        and all(row.get(key) is not None for key in ("x", "y", "kb"))
    }


def _legacy_trajectory_payload(wells_payload):
    tracks = [
        copy.deepcopy(row)
        for row in (wells_payload or {}).get("tracks") or []
        if isinstance(row, dict)
        and str(row.get("well_name") or "").strip()
    ]
    if not tracks:
        return {}

    order = []
    grouped = {}
    for row in tracks:
        well_name = str(row.get("well_name") or "").strip()
        if well_name not in grouped:
            grouped[well_name] = []
            order.append(well_name)
        grouped[well_name].append(row)

    wells = []
    for well_name in order:
        rows = grouped[well_name]
        md_values = [
            float(row["md_m"]) for row in rows
            if row.get("md_m") is not None
        ]
        z_values = [
            float(row["z_m"]) for row in rows
            if row.get("z_m") is not None
        ]
        wells.append({
            "well_name": well_name,
            "source_path": "",
            "file_name": "旧版井轨迹数据",
            "columns": ["MD", "X", "Y", "Z"],
            "metadata": {},
            "rows": rows,
            "summary": {
                "track_point_count": len(rows),
                "md_min": min(md_values) if md_values else None,
                "md_max": max(md_values) if md_values else None,
                "z_min": min(z_values) if z_values else None,
                "z_max": max(z_values) if z_values else None,
                "incl_max": None,
                "dls_max": None,
                "tvd_z_max_error": None,
                "tvd_z_consistent": None,
            },
            "warnings": [
                "当前显示的是旧版 CSV 井轨迹；可重新导入 DEV 文件升级数据。"
            ],
        })
    return build_trajectory_payload(wells)


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


def _xyz_text(row, prefix):
    values = [
        row.get(f"{prefix}_{axis}") for axis in ("x", "y", "z")
    ]
    if any(value is None for value in values):
        return "—"
    return " / ".join(f"{float(value):.6f}" for value in values)


def _trajectory_signature(payload):
    signature = []
    for well in (payload or {}).get("wells") or []:
        if not isinstance(well, dict):
            continue
        summary = well.get("summary") or {}
        signature.append((
            str(well.get("well_name") or ""),
            str(well.get("source_path") or ""),
            int(summary.get("track_point_count") or 0),
            summary.get("md_min"),
            summary.get("md_max"),
        ))
    return tuple(signature)


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
