# -*- coding: utf-8 -*-
"""仿照 COMPASS 设计的独立裂缝系统输入窗口。"""

import copy
import hashlib
import math
import os
from dataclasses import dataclass

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStyle,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..uniform_parser import parse_dfn, parse_wells
from .fracture_data_adapter import derive_hydraulic_fractures
from .input_keyword_registry import MODULE_FRACTURE_SYSTEM
from .module_import_service import (
    natural_fracture_business_data,
    validate_module_business_data,
)
from .module_input_models import ModuleInputState, ModuleParsedData
from .well_file_classifier import identify_well_file_roles


FRACTURE_TYPE_ROLE = Qt.UserRole
FRACTURE_GROUP_ROLE = Qt.UserRole + 1
FRACTURE_RECORD_ROLE = Qt.UserRole + 2
FRACTURE_TYPE_NATURAL = "natural"
FRACTURE_TYPE_HYDRAULIC = "hydraulic"


@dataclass(frozen=True)
class FracturePropertySpec:
    key: str
    title: str
    symbol: str
    unit: str = "NA"


# Only the fields explicitly retained from the COMPASS reference are listed.
# Values without a supported source remain blank; no synthetic defaults are
# introduced by this dialog.
FRACTURE_PROPERTY_SPECS = (
    FracturePropertySpec("fracture_id", "裂缝 ID", "ID"),
    FracturePropertySpec("porosity", "孔隙度", "PORO"),
    FracturePropertySpec("permeability", "渗透率", "PERM", "mD"),
    FracturePropertySpec("aperture", "裂缝开度", "APERTURE", "m"),
    FracturePropertySpec("non_darcy_beta", "非达西流系数", "β", "F"),
    FracturePropertySpec("satmap", "相渗区域编号", "SATMAP"),
    FracturePropertySpec("rockmap", "岩石区域编号", "ROCKMAP"),
    FracturePropertySpec("coalmap", "吸附区域编号", "COALMAP"),
    FracturePropertySpec("fracture_well", "压裂井", "FRACWELL"),
    FracturePropertySpec(
        "perforation_diameter", "井射孔等效直径", "PDIAM", "m"),
    FracturePropertySpec("well_branch", "井分支编号", "WBRANCH"),
    FracturePropertySpec("grid_id", "网格编号", "XBGRID"),
    FracturePropertySpec(
        "grid_permeability", "网格渗透率", "XPERM", "mD"),
    FracturePropertySpec("grid_porosity", "网格孔隙度", "XPORO"),
    FracturePropertySpec(
        "grid_fracture_aperture", "网格裂缝开度", "XAPERTURE", "m"),
)

NUMERIC_PROPERTY_KEYS = frozenset((
    "porosity",
    "permeability",
    "aperture",
    "non_darcy_beta",
    "perforation_diameter",
    "grid_permeability",
    "grid_porosity",
    "grid_fracture_aperture",
))


class FractureSystemCompassDialog(QDialog):
    """Three-pane fracture editor shell; data adapters arrive in later steps."""

    import_requested = pyqtSignal(str)
    values_applied = pyqtSignal(str, str, dict)

    def __init__(self, project_state, parent=None):
        super().__init__(parent)
        if project_state is None:
            raise ValueError("project_state is required")
        self.project_state = project_state
        self.values_were_applied = False
        existing = project_state.get_module_input_state(
            MODULE_FRACTURE_SYSTEM)
        self._working_state = (
            ModuleInputState.from_dict(existing)
            if existing is not None else ModuleInputState(
                module_key=MODULE_FRACTURE_SYSTEM,
                parsed_data=ModuleParsedData(),
                validation={
                    "ok": None,
                    "status": "empty",
                    "errors": [],
                    "warnings": [],
                },
            )
        )
        self._working_values = copy.deepcopy(
            self._working_state.parsed_data.values)
        self._working_source = copy.deepcopy(
            self._working_state.source)
        self._refreshing_ui = False
        self._visible_records = []
        self._current_record = None
        self._current_fracture_type = ""

        self.setObjectName("fractureSystemCompassDialog")
        self.setWindowTitle("裂缝系统")
        self.resize(1120, 730)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(9)
        root.addWidget(self._build_header())

        splitter = QSplitter(Qt.Horizontal)
        splitter.setObjectName("fractureSystemCompassSplitter")
        splitter.addWidget(self._build_group_panel())
        splitter.addWidget(self._build_id_panel())
        splitter.addWidget(self._build_property_panel())
        splitter.setSizes([205, 220, 695])
        root.addWidget(splitter, 1)

        buttons = QDialogButtonBox()
        self.ok_button = QPushButton("确定")
        self.cancel_button = QPushButton("取消")
        buttons.addButton(self.ok_button, QDialogButtonBox.AcceptRole)
        buttons.addButton(self.cancel_button, QDialogButtonBox.RejectRole)
        self.ok_button.clicked.connect(self._accept_values)
        self.cancel_button.clicked.connect(self.reject)
        root.addWidget(buttons)

        self._refresh_natural_groups()
        self._refresh_hydraulic_groups()
        self.group_tree.setCurrentItem(self.natural_item)

    def _build_header(self):
        frame = QFrame()
        frame.setObjectName("fractureSystemCompassHeader")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(12, 8, 12, 8)
        title = QLabel("裂缝系统")
        title.setObjectName("parameterTitle")
        layout.addWidget(title)
        layout.addStretch()
        self.import_status = QLabel("等待导入裂缝数据")
        self.import_status.setObjectName("parameterDescription")
        layout.addWidget(self.import_status)
        self.import_button = QPushButton("导入")
        self.import_button.setObjectName("importFractureSystemDataButton")
        self.import_button.clicked.connect(self._request_import)
        layout.addWidget(self.import_button)
        return frame

    def _build_group_panel(self):
        panel, layout = self._panel("裂缝分组")
        self.group_tree = QTreeWidget()
        self.group_tree.setObjectName("fractureGroupTree")
        self.group_tree.setHeaderHidden(True)
        self.group_tree.setSelectionMode(QAbstractItemView.SingleSelection)

        self.natural_item = self._fracture_type_item(
            "天然裂缝", FRACTURE_TYPE_NATURAL)
        self.hydraulic_item = self._fracture_type_item(
            "人工裂缝", FRACTURE_TYPE_HYDRAULIC)
        self.group_tree.addTopLevelItem(self.natural_item)
        self.group_tree.addTopLevelItem(self.hydraulic_item)
        self.natural_item.setExpanded(True)
        self.hydraulic_item.setExpanded(True)
        self.group_tree.currentItemChanged.connect(
            self._group_selection_changed)
        layout.addWidget(self.group_tree, 1)
        return panel

    def _build_id_panel(self):
        panel, layout = self._panel("裂缝 ID")
        self.fracture_id_table = QTableWidget(0, 1)
        self.fracture_id_table.setObjectName("fractureIdTable")
        self.fracture_id_table.setHorizontalHeaderLabels(("裂缝 ID",))
        self.fracture_id_table.setEditTriggers(
            QAbstractItemView.NoEditTriggers)
        self.fracture_id_table.setSelectionBehavior(
            QAbstractItemView.SelectRows)
        self.fracture_id_table.setSelectionMode(
            QAbstractItemView.SingleSelection)
        self.fracture_id_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch)
        self.fracture_id_table.currentCellChanged.connect(
            self._fracture_selection_changed)
        layout.addWidget(self.fracture_id_table, 1)
        return panel

    def _build_property_panel(self):
        panel, layout = self._panel("裂缝属性")
        self.property_table = QTableWidget(
            len(FRACTURE_PROPERTY_SPECS), 4)
        self.property_table.setObjectName("fracturePropertyTable")
        self.property_table.setHorizontalHeaderLabels(
            ("参数", "标识", "单位", "参数值"))
        self.property_table.setVerticalHeaderLabels(tuple(
            str(index) for index in range(
                1, len(FRACTURE_PROPERTY_SPECS) + 1)))
        for row, spec in enumerate(FRACTURE_PROPERTY_SPECS):
            self.property_table.setItem(
                row, 0, self._readonly_item(spec.title))
            self.property_table.setItem(
                row, 1, self._readonly_item(spec.symbol))
            self.property_table.setItem(
                row, 2, self._readonly_item(spec.unit))
            self.property_table.setItem(row, 3, QTableWidgetItem(""))
        header = self.property_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        self.property_table.verticalHeader().setDefaultSectionSize(34)
        layout.addWidget(self.property_table, 1)
        return panel

    @staticmethod
    def _panel(title):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(7)
        label = QLabel(title)
        label.setObjectName("parameterTitle")
        layout.addWidget(label)
        return panel, layout

    def _fracture_type_item(self, title, fracture_type):
        item = QTreeWidgetItem([title])
        item.setData(0, FRACTURE_TYPE_ROLE, fracture_type)
        item.setIcon(
            0, self.style().standardIcon(QStyle.SP_DirOpenIcon))
        return item

    @staticmethod
    def _readonly_item(text):
        item = QTableWidgetItem(str(text))
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        item.setTextAlignment(Qt.AlignCenter)
        return item

    def _request_import(self):
        item = self.group_tree.currentItem()
        while item is not None and not item.data(0, FRACTURE_TYPE_ROLE):
            item = item.parent()
        fracture_type = (
            str(item.data(0, FRACTURE_TYPE_ROLE) or "")
            if item is not None else ""
        )
        if not fracture_type:
            self.import_status.setText("请先选择天然裂缝或人工裂缝")
            return
        if not self._commit_visible_property_edits():
            return
        self.import_requested.emit(fracture_type)
        if fracture_type == FRACTURE_TYPE_NATURAL:
            self._import_natural_fractures()
        else:
            self._import_hydraulic_fractures()

    def _import_natural_fractures(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择天然裂缝 DFN 数据",
            "",
            "DFN 数据 (*.txt *.dfn);;所有文件 (*)",
        )
        if not path:
            return
        try:
            natural = natural_fracture_business_data(parse_dfn(path))
        except (OSError, TypeError, ValueError, UnicodeError):
            QMessageBox.warning(
                self, "导入失败",
                "天然裂缝数据解析失败，请检查 DFN 文件内容。")
            return
        fractures = list(natural.get("fractures") or [])
        if not fractures:
            QMessageBox.warning(
                self, "导入失败", "所选文件中没有解析到天然裂缝数据。")
            return

        self._working_values["natural_fractures"] = copy.deepcopy(natural)
        absolute_path = os.path.abspath(path)
        self._working_source["natural_fractures"] = {
            "path": absolute_path,
            "source_mode": "direct_dfn_file",
        }
        keywords = dict(self._working_source.get("keywords") or {})
        keywords["FRACTURE.fracture_file"] = _direct_source_record(
            absolute_path,
            module_key=MODULE_FRACTURE_SYSTEM,
            value_key="natural_fractures",
        )
        self._working_source["keywords"] = keywords
        direct_imports = dict(
            self._working_source.get("direct_imports") or {})
        direct_imports["natural_fractures"] = {
            "dfn_file": absolute_path,
        }
        self._working_source["direct_imports"] = direct_imports
        self._refresh_natural_groups(select_first=True)
        group_count = self.natural_item.childCount()
        self.import_status.setText(
            f"已预览 {len(fractures)} 条天然裂缝、{group_count} 个组别；点击确定后保存")

    def _import_hydraulic_fractures(self):
        first_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择第一个人工裂缝井数据文件",
            "",
            "井数据 (*.csv);;所有文件 (*)",
        )
        if not first_path:
            return
        second_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择第二个人工裂缝井数据文件",
            os.path.dirname(os.path.abspath(first_path)),
            "井数据 (*.csv);;所有文件 (*)",
        )
        if not second_path:
            return

        try:
            track_path, completion_path = identify_well_file_roles(
                first_path, second_path)
        except (OSError, UnicodeError, ValueError) as exc:
            QMessageBox.warning(
                self,
                "文件识别失败",
                str(exc) or "无法根据CSV表头识别人工裂缝井数据文件。",
            )
            return
        try:
            parsed_wells = parse_wells(track_path, completion_path)
            records = derive_hydraulic_fractures(parsed_wells)
        except (OSError, TypeError, ValueError, UnicodeError):
            QMessageBox.warning(
                self, "导入失败",
                "人工裂缝数据解析失败，请检查完井文件及配套井轨迹文件。")
            return
        if not records:
            QMessageBox.warning(
                self, "导入失败",
                "完井数据中没有带完整几何信息的人工裂缝 PERF 记录。")
            return

        self._working_values["hydraulic_fractures"] = copy.deepcopy(records)
        self._working_source["hydraulic_fractures"] = {
            "completion_path": os.path.abspath(completion_path),
            "track_path": os.path.abspath(track_path),
            "source_mode": "well_completion_and_track",
        }
        direct_imports = dict(
            self._working_source.get("direct_imports") or {})
        direct_imports["hydraulic_fractures"] = {
            "well_completions": os.path.abspath(completion_path),
            "well_tracks": os.path.abspath(track_path),
        }
        self._working_source["direct_imports"] = direct_imports
        self._refresh_hydraulic_groups(select_first=True)
        group_count = self.hydraulic_item.childCount()
        self.import_status.setText(
            f"已预览 {len(records)} 条人工裂缝、{group_count} 个组别；点击确定后保存")

    def _refresh_natural_groups(self, select_first=False):
        natural = self._working_values.get("natural_fractures") or {}
        fractures = [
            row for row in natural.get("fractures") or []
            if isinstance(row, dict)
        ]
        set_names = {
            str(item.get("set_id")): str(item.get("set_name") or "").strip()
            for item in natural.get("sets") or []
            if isinstance(item, dict) and item.get("set_id") is not None
        }
        group_ids = {
            str(row.get("set_id"))
            for row in fractures if row.get("set_id") is not None
        }
        group_ids.update(set_names)
        if fractures and not group_ids:
            group_ids.add("1")

        target = None
        prior_refresh = self._refreshing_ui
        self._refreshing_ui = True
        try:
            while self.natural_item.childCount():
                self.natural_item.takeChild(0)
            for group_id in sorted(group_ids, key=_group_sort_key):
                default_name = f"组别{group_id}"
                source_name = set_names.get(group_id, "")
                title = (
                    f"{default_name}（{source_name}）"
                    if source_name and source_name != default_name
                    else default_name
                )
                item = QTreeWidgetItem([title])
                item.setData(0, FRACTURE_TYPE_ROLE, FRACTURE_TYPE_NATURAL)
                item.setData(0, FRACTURE_GROUP_ROLE, group_id)
                item.setIcon(
                    0, self.style().standardIcon(QStyle.SP_DirIcon))
                self.natural_item.addChild(item)

            self.natural_item.setExpanded(True)
            if select_first and self.natural_item.childCount():
                target = self.natural_item.child(0)
                self.group_tree.setCurrentItem(target)
            elif self.group_tree.currentItem() is self.natural_item:
                target = self.natural_item
        finally:
            self._refreshing_ui = prior_refresh
        if target is not None and not prior_refresh:
            self._group_selection_changed(target, None)

    def _refresh_hydraulic_groups(self, select_first=False):
        records = [
            row for row in self._working_values.get(
                "hydraulic_fractures") or []
            if isinstance(row, dict)
        ]
        well_names = sorted({
            str(row.get("well_name") or "").strip()
            for row in records
        }, key=lambda value: (not value, value))
        if records and not well_names:
            well_names = [""]

        target = None
        prior_refresh = self._refreshing_ui
        self._refreshing_ui = True
        try:
            while self.hydraulic_item.childCount():
                self.hydraulic_item.takeChild(0)
            for index, well_name in enumerate(well_names, start=1):
                default_name = f"组别{index}"
                title = (
                    f"{default_name}（{well_name}）"
                    if well_name else default_name
                )
                item = QTreeWidgetItem([title])
                item.setData(0, FRACTURE_TYPE_ROLE, FRACTURE_TYPE_HYDRAULIC)
                item.setData(0, FRACTURE_GROUP_ROLE, well_name)
                item.setIcon(
                    0, self.style().standardIcon(QStyle.SP_DirIcon))
                self.hydraulic_item.addChild(item)

            self.hydraulic_item.setExpanded(True)
            if select_first and self.hydraulic_item.childCount():
                target = self.hydraulic_item.child(0)
                self.group_tree.setCurrentItem(target)
            elif self.group_tree.currentItem() is self.hydraulic_item:
                target = self.hydraulic_item
        finally:
            self._refreshing_ui = prior_refresh
        if target is not None and not prior_refresh:
            self._group_selection_changed(target, None)

    def _group_selection_changed(self, current, previous):
        if self._refreshing_ui:
            return
        if not self._commit_visible_property_edits():
            if previous is not None:
                self._refreshing_ui = True
                try:
                    self.group_tree.setCurrentItem(previous)
                finally:
                    self._refreshing_ui = False
            return
        if current is None:
            self._populate_fracture_ids((), "")
            return
        fracture_type = self._item_fracture_type(current)
        if fracture_type == FRACTURE_TYPE_NATURAL:
            natural = self._working_values.get("natural_fractures") or {}
            fractures = [
                row for row in natural.get("fractures") or []
                if isinstance(row, dict)
            ]
            group_id = current.data(0, FRACTURE_GROUP_ROLE)
            if group_id not in (None, ""):
                fractures = [
                    row for row in fractures
                    if str(row.get("set_id")) == str(group_id)
                ]
        elif fracture_type == FRACTURE_TYPE_HYDRAULIC:
            fractures = [
                row for row in self._working_values.get(
                    "hydraulic_fractures") or []
                if isinstance(row, dict)
            ]
            if current is not self.hydraulic_item:
                well_name = str(
                    current.data(0, FRACTURE_GROUP_ROLE) or "")
                fractures = [
                    row for row in fractures
                    if str(row.get("well_name") or "").strip() == well_name
                ]
        else:
            self._populate_fracture_ids((), "")
            return
        fractures.sort(key=lambda row: _fracture_id_sort_key(
            row.get("fracture_id")))
        self._populate_fracture_ids(fractures, fracture_type)

    def _populate_fracture_ids(self, fractures, fracture_type):
        rows = list(fractures or ())
        prior_refresh = self._refreshing_ui
        self._refreshing_ui = True
        try:
            self._current_record = None
            self._current_fracture_type = ""
            self._visible_records = [
                (fracture_type, row) for row in rows
            ]
            self.fracture_id_table.setUpdatesEnabled(False)
            try:
                self.fracture_id_table.setRowCount(len(rows))
                for row_index, fracture in enumerate(rows):
                    item = self._readonly_item(
                        _display_value(fracture.get("fracture_id")))
                    item.setData(FRACTURE_RECORD_ROLE, fracture)
                    self.fracture_id_table.setItem(row_index, 0, item)
            finally:
                self.fracture_id_table.setUpdatesEnabled(True)
            if rows:
                self.fracture_id_table.setCurrentCell(0, 0)
                self._show_fracture_properties(rows[0], fracture_type)
            else:
                self._show_fracture_properties({}, "")
        finally:
            self._refreshing_ui = prior_refresh

    def _fracture_selection_changed(
            self, current_row, current_column, previous_row,
            previous_column):
        del current_column, previous_column
        if self._refreshing_ui:
            return
        if not self._commit_visible_property_edits():
            if previous_row >= 0:
                self._refreshing_ui = True
                try:
                    self.fracture_id_table.setCurrentCell(previous_row, 0)
                finally:
                    self._refreshing_ui = False
            return
        if 0 <= current_row < len(self._visible_records):
            fracture_type, fracture = self._visible_records[current_row]
            self._show_fracture_properties(fracture, fracture_type)
        else:
            self._show_fracture_properties({}, "")

    def _show_fracture_properties(self, fracture, fracture_type):
        prior_refresh = self._refreshing_ui
        self._refreshing_ui = True
        self._current_record = fracture if fracture else None
        self._current_fracture_type = fracture_type if fracture else ""
        aliases = {
            "fracture_id": ("fracture_id",),
            "porosity": ("porosity", "poro"),
            "permeability": ("permeability", "perm"),
            "aperture": ("aperture",),
            "non_darcy_beta": ("non_darcy_beta", "beta"),
            "satmap": ("satmap",),
            "rockmap": ("rockmap",),
            "coalmap": ("coalmap",),
            "fracture_well": ("fracture_well", "well_name"),
            "perforation_diameter": (
                "perforation_diameter", "pdiam"),
            "well_branch": ("well_branch", "wbranch"),
            "grid_id": ("grid_id", "xbgrid"),
            "grid_permeability": ("grid_permeability", "xperm"),
            "grid_porosity": ("grid_porosity", "xporo"),
            "grid_fracture_aperture": (
                "grid_fracture_aperture", "xaperture"),
        }
        for row, spec in enumerate(FRACTURE_PROPERTY_SPECS):
            value = None
            for key in aliases.get(spec.key, (spec.key,)):
                if fracture.get(key) is not None:
                    value = fracture.get(key)
                    break
            self.property_table.item(row, 3).setText(
                _display_value(value))
        self._refreshing_ui = prior_refresh

    def _commit_visible_property_edits(self):
        if self._refreshing_ui or self._current_record is None:
            return True
        record = self._current_record
        fracture_type = self._current_fracture_type
        for row, spec in enumerate(FRACTURE_PROPERTY_SPECS):
            text = self.property_table.item(row, 3).text().strip()
            storage_key = _property_storage_key(spec.key, fracture_type)
            if (spec.key == "fracture_id"
                    and text == _display_value(record.get(storage_key))):
                continue
            try:
                value = _coerce_property_value(spec.key, text)
            except ValueError:
                self.property_table.setCurrentCell(row, 3)
                QMessageBox.warning(
                    self, "参数无效", f"{spec.title}必须填写有效数字。")
                return False
            if value is None:
                record.pop(storage_key, None)
                if storage_key != spec.key:
                    record.pop(spec.key, None)
            else:
                record[storage_key] = value
                if storage_key != spec.key:
                    record.pop(spec.key, None)

            if (spec.key == "fracture_id"
                    and fracture_type == FRACTURE_TYPE_HYDRAULIC):
                record["comp_id"] = "" if value is None else str(value)

        for row, (_kind, visible_record) in enumerate(self._visible_records):
            if visible_record is record:
                item = self.fracture_id_table.item(row, 0)
                if item is not None:
                    item.setText(_display_value(record.get("fracture_id")))
                break
        return True

    def _accept_values(self):
        if not self._commit_visible_property_edits():
            return

        errors = _validate_fracture_records(self._working_values)
        business_validation = validate_module_business_data(
            MODULE_FRACTURE_SYSTEM, self._working_values)
        errors.extend(business_validation.get("errors") or [])
        if errors:
            QMessageBox.warning(
                self, "裂缝属性校验未通过", "\n".join(dict.fromkeys(errors)))
            return

        draft = ModuleInputState.from_dict(self._working_state)
        draft.parsed_data = ModuleParsedData(
            values=copy.deepcopy(self._working_values))
        draft.source = copy.deepcopy(self._working_source)
        current_validation = copy.deepcopy(draft.validation or {})
        checks = dict(current_validation.get("checks") or {})
        checks.update(business_validation.get("checks") or {})
        warnings = list(dict.fromkeys(
            list(current_validation.get("warnings") or [])
            + list(business_validation.get("warnings") or [])
        ))
        current_validation.update({
            "ok": True,
            "errors": [],
            "warnings": warnings,
            "checks": checks,
        })
        draft.validation = current_validation
        draft.dirty = True

        current = self.project_state.get_module_input_state(
            MODULE_FRACTURE_SYSTEM)
        if current is not None and _state_content(current) == _state_content(draft):
            self.accept()
            return
        if current is None and not self._working_values:
            self.accept()
            return
        try:
            committed = self.project_state.replace_module_input_state(
                MODULE_FRACTURE_SYSTEM, draft)
        except (TypeError, ValueError):
            QMessageBox.warning(self, "保存失败", "裂缝系统数据未能保存。")
            return

        self._working_state = committed
        self._working_values = copy.deepcopy(
            committed.parsed_data.values)
        self._working_source = copy.deepcopy(committed.source)
        self.values_were_applied = True
        self.values_applied.emit(
            MODULE_FRACTURE_SYSTEM,
            "裂缝系统",
            _compact_values(self._working_values),
        )
        self.accept()

    @staticmethod
    def _item_fracture_type(item):
        current = item
        while current is not None:
            value = current.data(0, FRACTURE_TYPE_ROLE)
            if value:
                return str(value)
            current = current.parent()
        return ""


def _display_value(value):
    if value in (None, ""):
        return ""
    if isinstance(value, float):
        return f"{value:.12g}"
    return str(value)


def _group_sort_key(value):
    try:
        return 0, float(value)
    except (TypeError, ValueError):
        return 1, str(value)


def _fracture_id_sort_key(value):
    try:
        return 0, float(value)
    except (TypeError, ValueError):
        return 1, str(value or "")


def _coerce_property_value(key, text):
    value = str(text or "").strip()
    if not value:
        return None
    if key not in NUMERIC_PROPERTY_KEYS:
        return value
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid numeric property") from exc
    if not math.isfinite(number):
        raise ValueError("invalid numeric property")
    return number


def _property_storage_key(key, fracture_type):
    if (fracture_type == FRACTURE_TYPE_HYDRAULIC
            and key == "permeability"):
        return "perm"
    if (fracture_type == FRACTURE_TYPE_HYDRAULIC
            and key == "fracture_well"):
        return "well_name"
    return key


def _direct_source_record(path, *, module_key, value_key):
    absolute_path = os.path.abspath(path)
    try:
        stat = os.stat(absolute_path)
        source_size = int(stat.st_size)
        modified_ns = int(stat.st_mtime_ns)
        digest = hashlib.sha256()
        with open(absolute_path, "rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
        source_sha256 = digest.hexdigest()
    except OSError:
        source_size = 0
        modified_ns = 0
        source_sha256 = ""
    return {
        "raw_value": absolute_path,
        "resolved_path": absolute_path,
        "exists": os.path.isfile(absolute_path),
        "source_mode": "direct_dfn_file",
        "module_key": module_key,
        "value_key": value_key,
        "source_size": source_size,
        "modified_ns": modified_ns,
        "source_sha256": source_sha256,
    }


def _validate_fracture_records(values):
    errors = []
    natural = values.get("natural_fractures") or {}
    collections = (
        ("天然裂缝", [
            row for row in natural.get("fractures") or []
            if isinstance(row, dict)
        ]),
        ("人工裂缝", [
            row for row in values.get("hydraulic_fractures") or []
            if isinstance(row, dict)
        ]),
    )
    for title, records in collections:
        identifiers = [
            str(row.get("fracture_id") or "").strip()
            for row in records
        ]
        if any(not value for value in identifiers):
            errors.append(f"{title}的裂缝 ID 不能为空。")
        available = [value for value in identifiers if value]
        if len(available) != len(set(available)):
            errors.append(f"{title}的裂缝 ID 不能重复。")
        for record in records:
            for key in ("porosity", "grid_porosity"):
                value = record.get(key)
                number = _finite_number(value)
                if value is not None and (
                        number is None or not 0.0 <= number <= 1.0):
                    errors.append(f"{title}的孔隙度必须在 0 到 1 之间。")
            for key in (
                    "permeability", "perm", "non_darcy_beta",
                    "grid_permeability"):
                value = record.get(key)
                number = _finite_number(value)
                if value is not None and (number is None or number < 0.0):
                    errors.append(f"{title}的物性参数不能小于 0。")
            for key in (
                    "aperture", "perforation_diameter",
                    "grid_fracture_aperture"):
                value = record.get(key)
                number = _finite_number(value)
                if value is not None and (number is None or number <= 0.0):
                    errors.append(f"{title}的开度或直径必须大于 0。")
    return list(dict.fromkeys(errors))


def _finite_number(value):
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def _state_content(state):
    return {
        "raw_values": copy.deepcopy(state.raw_values),
        "parsed_data": state.parsed_data.to_dict(),
        "validation": copy.deepcopy(state.validation),
        "source": copy.deepcopy(state.source),
    }


def _compact_values(values):
    result = {}
    for key, value in (values or {}).items():
        if isinstance(value, dict):
            result[key] = f"{len(value)} 项业务属性"
        elif isinstance(value, (list, tuple)):
            result[key] = f"{len(value)} 条业务记录"
        else:
            result[key] = value
    return result


__all__ = [
    "FRACTURE_PROPERTY_SPECS",
    "FRACTURE_TYPE_HYDRAULIC",
    "FRACTURE_TYPE_NATURAL",
    "FracturePropertySpec",
    "FractureSystemCompassDialog",
]
