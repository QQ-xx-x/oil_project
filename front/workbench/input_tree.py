# -*- coding: utf-8 -*-
"""工程打开后的输入数据树。"""

import copy

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QBrush, QColor
from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem

from .case_data_panel import CaseDataPanel, CaseKeywordPanel
from .icons import painted_icon
from .parameter_panels import (
    WorkbenchDualPorosityPanel, WorkbenchGasPvtPanel, WorkbenchGridPanel,
    WorkbenchHydraulicFracturesPanel, WorkbenchInitialStatePanel,
    WorkbenchMatrixPanel, WorkbenchNaturalFracturesPanel,
    WorkbenchOilWaterPanel, WorkbenchSimulationPanel, WorkbenchWellPanel,
)
from .settings_dialog import ObjectSettingsDialog, ParameterSettingsDialog


KEY_ROLE = Qt.UserRole
TYPE_ROLE = Qt.UserRole + 1

DEFAULT_CASE_SECTION_NAMES = [
    "GRID", "ROCK", "FRACTURE", "LGR", "FLUID", "GAS",
    "INITIAL", "WELL", "SOLVER", "OUTPUT", "WR",
]


class InputTree(QTreeWidget):
    module_selected = pyqtSignal(str, str)
    module_checked = pyqtSignal(str, str, bool)
    parameters_saved = pyqtSignal(str, str, dict)
    case_dataset_built = pyqtSignal(str, dict)

    def __init__(self, project_state=None, parent=None):
        super().__init__(parent)
        self.project_state = project_state
        self._building = False
        self._panel_factories = {
            "case_data_manifest": lambda: CaseDataPanel(self.project_state),
            "grid_basic": WorkbenchGridPanel,
            "initial_state": WorkbenchInitialStatePanel,
            "matrix_properties": WorkbenchMatrixPanel,
            "dual_porosity": WorkbenchDualPorosityPanel,
            "simulation_control": WorkbenchSimulationPanel,
            "oil_water_properties": WorkbenchOilWaterPanel,
            "gas_pvt": WorkbenchGasPvtPanel,
            "well_parameters": WorkbenchWellPanel,
            "natural_fractures": WorkbenchNaturalFracturesPanel,
            "hydraulic_fractures": WorkbenchHydraulicFracturesPanel,
        }
        self.setObjectName("inputTree")
        self.setHeaderHidden(True)
        self.setExpandsOnDoubleClick(False)
        self.currentItemChanged.connect(self._emit_selection)
        self.itemChanged.connect(self._store_check_state)
        self.itemDoubleClicked.connect(self._open_settings)
        self._populate()
        self.expandToDepth(0)
        self.refresh_case_data_sections(preserve_expanded=False)

    def _item(self, text, key, object_type="参数模块", checked=False,
              icon_name="generic", icon_status=None, tooltip=None,
              foreground=None):
        item = QTreeWidgetItem([text])
        item.setData(0, KEY_ROLE, key)
        item.setData(0, TYPE_ROLE, object_type)
        item.setIcon(0, painted_icon(icon_name, 16, icon_status))
        if tooltip:
            item.setToolTip(0, tooltip)
        if foreground:
            item.setForeground(0, QBrush(QColor(foreground)))
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
        effective_checked = checked
        if self.project_state is not None:
            if key in getattr(self.project_state, "checked_items", {}):
                effective_checked = self.project_state.is_checked(key, checked)
            else:
                self.project_state.set_checked(key, checked)
        item.setCheckState(0, Qt.Checked if effective_checked else Qt.Unchecked)
        return item

    def _populate(self):
        self._building = True
        module_tree = [
            ("CaseData 原始输入", "case_data_manifest", "CaseData 文件", "case_root", True, [
                (section, f"case_data_section:{section}", "CaseData Section",
                 self._case_section_icon(section), True)
                for section in self._case_section_names()
            ]),
            ("网格与导入", "grid_input", "功能模块", "grid", True, [
                ("网格数量、尺寸与文件", "grid_basic", "网格参数", "grid", True),
            ]),
            ("储层基础属性", "reservoir_properties", "功能模块", "matrix", True, [
                ("初始状态", "initial_state", "初始状态参数", "initial", True),
                ("基质属性", "matrix_properties", "岩石参数", "matrix", True),
                ("双重介质", "dual_porosity", "岩石参数", "dual_porosity", False),
            ]),
            ("流体与 PVT", "fluid_pvt", "功能模块", "fluid", True, [
                ("油水相基础参数", "oil_water_properties", "流体参数", "oil_water", True),
                ("气相真实气体 PVT", "gas_pvt", "流体参数", "gas", False),
            ]),
            ("井参数", "well_system", "功能模块", "well", True, [
                ("井位置与控制", "well_parameters", "井参数", "well", True),
            ]),
            ("裂缝参数", "fracture_system", "功能模块", "fracture", True, [
                ("天然裂缝", "natural_fractures", "裂缝参数", "fracture", True),
                ("人工裂缝", "hydraulic_fractures", "裂缝参数", "fracture", True),
            ]),
            ("模拟控制", "simulation_system", "功能模块", "solver", True, [
                ("时间控制", "simulation_control", "模拟参数", "solver", True),
            ]),
        ]

        for folder_name, folder_key, folder_type, folder_icon, folder_checked, children in module_tree:
            folder = self._item(
                folder_name, folder_key, folder_type, folder_checked, folder_icon)
            for child_name, child_key, child_type, child_icon, child_checked in children:
                folder.addChild(self._item(
                    child_name, child_key, child_type, child_checked, child_icon))
            self.addTopLevelItem(folder)
        self._building = False

    def _store_check_state(self, item, column):
        if self._building or column != 0 or self.project_state is None:
            return
        key = item.data(0, KEY_ROLE)
        checked = item.checkState(0) == Qt.Checked
        self.project_state.set_checked(key, checked)
        self.module_checked.emit(key, item.text(0), checked)

    def _emit_selection(self, current, previous):
        if current is None:
            return
        key = current.data(0, KEY_ROLE)
        if self.project_state is not None:
            self.project_state.ui_state["input_tree_current_key"] = key
        self.module_selected.emit(key, current.text(0))

    def _open_settings(self, item, column):
        key = item.data(0, KEY_ROLE)
        before_signature = self._case_data_signature()
        before_case_data = self._case_data_snapshot()
        root = self._find_item("case_data_manifest")
        expanded_keys_before_dialog = self._expanded_keys(root) if root is not None else set()
        object_type = item.data(0, TYPE_ROLE) or "工程对象"
        panel_factory = self._panel_factories.get(key)
        if isinstance(key, str) and key.startswith("case_data_section:"):
            section_name = key.split(":", 1)[1]
            panel_factory = lambda section=section_name: CaseDataPanel(
                self.project_state, initial_section=section, section_locked=True)
        elif isinstance(key, str) and key.startswith("case_data_keyword:"):
            section_name, keyword_key = key.split(":", 2)[1:]
            panel_factory = lambda section=section_name, keyword=keyword_key: (
                CaseKeywordPanel(self.project_state, section, keyword))
        if panel_factory and self.project_state is not None:
            dialog = ParameterSettingsDialog(
                key, item.text(0), panel_factory, self.project_state,
                object_type, self)
            dialog.values_applied.connect(
                lambda values, module_key=key, title=item.text(0):
                    self.parameters_saved.emit(module_key, title, values))
            if hasattr(dialog.panel, "case_data_saved"):
                dialog.panel.case_data_saved.connect(
                    lambda: self.refresh_case_data_sections(preserve_expanded=True))
            if hasattr(dialog.panel, "case_dataset_built"):
                dialog.panel.case_dataset_built.connect(self.case_dataset_built.emit)
        else:
            dialog = ObjectSettingsDialog(item.text(0), object_type, self)
        result = dialog.exec_()
        if key == "case_data_manifest":
            confirmed = (
                result == dialog.Accepted
                or getattr(dialog, "values_were_applied", False)
                or getattr(getattr(dialog, "panel", None), "values_were_saved", False)
            )
            if confirmed:
                if self._case_data_signature() != before_signature:
                    self.refresh_case_data_sections(preserve_expanded=True)
                else:
                    self._restore_case_tree_expanded_state(expanded_keys_before_dialog)
            else:
                self._restore_case_data_snapshot(before_case_data)
                self._restore_case_tree_expanded_state(expanded_keys_before_dialog)
        elif isinstance(key, str) and key.startswith("case_data_"):
            confirmed = (
                result == dialog.Accepted
                or getattr(dialog, "values_were_applied", False)
                or getattr(getattr(dialog, "panel", None), "values_were_saved", False)
            )
            if confirmed:
                if self._case_data_signature() != before_signature:
                    self.refresh_case_data_sections(preserve_expanded=True)
                else:
                    self._restore_case_tree_expanded_state(expanded_keys_before_dialog)
            else:
                self._restore_case_data_snapshot(before_case_data)
                self._restore_case_tree_expanded_state(expanded_keys_before_dialog)

    def _case_data_signature(self):
        summary = getattr(self.project_state, "case_data_summary", {}) or {}
        sections = self._case_section_names()
        keyword_values = []
        for section in getattr(self.project_state, "case_data_sections", []) or []:
            if not isinstance(section, dict):
                continue
            section_name = section.get("name", "")
            for keyword in section.get("keywords", []) or []:
                if not isinstance(keyword, dict):
                    continue
                keyword_values.append((
                    section_name,
                    keyword.get("key", ""),
                    keyword.get("raw_value", ""),
                    bool(keyword.get("is_file_ref")),
                    bool(keyword.get("file_exists")),
                ))
        return (
            getattr(self.project_state, "case_data_path", ""),
            tuple(sections),
            tuple(keyword_values),
            summary.get("keyword_count"),
            summary.get("file_ref_count"),
            summary.get("missing_file_ref_count"),
            summary.get("error_count"),
        )

    def _case_data_snapshot(self):
        if self.project_state is None:
            return None
        return {
            "case_data_path": getattr(self.project_state, "case_data_path", ""),
            "case_data_summary": copy.deepcopy(
                getattr(self.project_state, "case_data_summary", {}) or {}),
            "case_data_sections": copy.deepcopy(
                getattr(self.project_state, "case_data_sections", []) or []),
            "case_data_schema": copy.deepcopy(
                getattr(self.project_state, "case_data_schema", {}) or {}),
        }

    def _restore_case_data_snapshot(self, snapshot):
        if self.project_state is None or snapshot is None:
            return
        self.project_state.case_data_path = snapshot["case_data_path"]
        self.project_state.case_data_summary = snapshot["case_data_summary"]
        self.project_state.case_data_sections = snapshot["case_data_sections"]
        self.project_state.case_data_schema = snapshot["case_data_schema"]

    def _case_section_names(self):
        sections = getattr(self.project_state, "case_data_sections", []) or []
        names = [
            section.get("name")
            for section in sections
            if isinstance(section, dict) and section.get("name")
        ]
        return names or list(DEFAULT_CASE_SECTION_NAMES)

    def refresh_case_data_sections(self, preserve_expanded=True):
        root = self._find_item("case_data_manifest")
        if root is None:
            return
        current_key = None
        if self.currentItem() is not None:
            current_key = self.currentItem().data(0, KEY_ROLE)
        expanded_keys = self._expanded_keys(root) if preserve_expanded else set()
        self._building = True
        root.takeChildren()
        for section in self._case_section_names():
            section_item = self._item(
                section, f"case_data_section:{section}",
                "CaseData Section", True, self._case_section_icon(section),
                tooltip=self._case_section_tooltip(section))
            for keyword in self._case_section_keywords(section):
                icon_name, icon_status = self._case_keyword_icon(keyword)
                section_item.addChild(self._item(
                    self._keyword_label(keyword),
                    f"case_data_keyword:{section}:{keyword.get('key', '')}",
                    "CaseData Keyword",
                    True,
                    icon_name,
                    icon_status=icon_status,
                    tooltip=self._case_keyword_tooltip(section, keyword),
                    foreground=self._case_keyword_foreground(keyword),
                ))
            root.addChild(section_item)
        if preserve_expanded:
            self._restore_expanded_keys(root, expanded_keys)
        root.setExpanded(True)
        self._building = False
        if current_key:
            self.select_key(current_key)

    def export_ui_state(self):
        """导出输入树当前展开和选中状态。"""
        current_key = None
        if self.currentItem() is not None:
            current_key = self.currentItem().data(0, KEY_ROLE)
        return {
            "current_key": current_key,
            "expanded_keys": sorted(self._all_expanded_keys()),
        }

    def restore_ui_state(self, state):
        """恢复输入树展开和选中状态。"""
        state = state or {}
        if "expanded_keys" in state:
            self.collapseAll()
        self._restore_expanded_keys_for_all(set(state.get("expanded_keys") or []))
        current_key = state.get("current_key")
        if current_key:
            self.select_key(current_key)

    def _expanded_keys(self, root):
        keys = set()

        def visit(item):
            key = item.data(0, KEY_ROLE)
            if item.isExpanded() and key:
                keys.add(key)
            for index in range(item.childCount()):
                visit(item.child(index))

        visit(root)
        return keys

    def _all_expanded_keys(self):
        keys = set()
        for index in range(self.topLevelItemCount()):
            keys.update(self._expanded_keys(self.topLevelItem(index)))
        return keys

    def _restore_expanded_keys_for_all(self, keys):
        for index in range(self.topLevelItemCount()):
            self._restore_expanded_keys(self.topLevelItem(index), keys)

    def _restore_expanded_keys(self, root, keys):
        def visit(item):
            key = item.data(0, KEY_ROLE)
            if key in keys:
                item.setExpanded(True)
            for index in range(item.childCount()):
                visit(item.child(index))

        visit(root)

    def _restore_case_tree_expanded_state(self, keys):
        root = self._find_item("case_data_manifest")
        if root is None:
            return
        self._restore_expanded_keys(root, keys)
        root.setExpanded(True)

    def _case_section_keywords(self, section_name):
        sections = getattr(self.project_state, "case_data_sections", []) or []
        for section in sections:
            if not isinstance(section, dict):
                continue
            if section.get("name") == section_name:
                return section.get("keywords", []) or []
        return []

    def _case_section_icon(self, section_name):
        name = str(section_name or "").upper()
        return {
            "GRID": "grid",
            "ROCK": "rock",
            "FRACTURE": "fracture",
            "LGR": "lgr",
            "FLUID": "fluid",
            "GAS": "gas",
            "INITIAL": "initial",
            "WELL": "well",
            "SOLVER": "solver",
            "OUTPUT": "output",
            "WR": "wr",
            "RETURN_SCHEMA": "case_section",
        }.get(name, "case_section")

    def _case_section_tooltip(self, section_name):
        count = len(self._case_section_keywords(section_name))
        return f"CaseData section: {section_name}\n关键字数量: {count}"

    def _case_keyword_icon(self, keyword):
        key = str(keyword.get("key", "") or "").lower()
        is_file = bool(keyword.get("is_file_ref"))
        dirty = bool(keyword.get("dirty"))
        exists = bool(keyword.get("file_exists"))
        if is_file:
            if key == "grid_file":
                icon_name = "grid_file"
            elif key == "fracture_file":
                icon_name = "dfn_file"
            elif key == "actnum_file":
                icon_name = "actnum_file"
            elif key == "sigma_file":
                icon_name = "sigma_file"
            elif key.startswith("matrix_"):
                icon_name = "matrix_property_file"
            elif key.startswith("fracture_"):
                icon_name = "fracture_property_file"
            elif key.endswith("_file"):
                icon_name = "property_file"
            else:
                icon_name = "file"
            if not exists:
                return icon_name, "missing"
            if dirty:
                return icon_name, "dirty"
            return icon_name, "ok"
        if dirty:
            return "keyword_param", "dirty"
        return "keyword_param", None

    def _case_keyword_foreground(self, keyword):
        if keyword.get("is_file_ref") and not keyword.get("file_exists"):
            return "#b42318"
        if keyword.get("dirty"):
            return "#9a6700"
        return None

    def _case_keyword_tooltip(self, section_name, keyword):
        lines = [
            f"section: {section_name}",
            f"key: {keyword.get('key', '')}",
            f"value: {keyword.get('raw_value', '')}",
            f"type: {keyword.get('value_type', '')}",
        ]
        if keyword.get("is_file_ref"):
            status = "文件已找到" if keyword.get("file_exists") else "文件缺失"
            lines.extend([
                "kind: 文件引用",
                f"status: {status}",
                f"path: {keyword.get('file_path', '')}",
            ])
        else:
            lines.append("kind: 普通参数")
        if keyword.get("dirty"):
            lines.append("保存状态: 已修改，未保存")
        return "\n".join(lines)

    def _keyword_label(self, keyword):
        key = keyword.get("key", "")
        value = keyword.get("raw_value", "")
        if value == "":
            return key
        text = f"{key} = {value}"
        return text if len(text) <= 72 else text[:69] + "..."

    def select_key(self, key):
        item = self._find_item(key)
        if item is None:
            return False
        self.setCurrentItem(item)
        self.scrollToItem(item)
        return True

    def _find_item(self, key):
        for index in range(self.topLevelItemCount()):
            found = self._find_item_recursive(self.topLevelItem(index), key)
            if found is not None:
                return found
        return None

    def _find_item_recursive(self, item, key):
        if item.data(0, KEY_ROLE) == key:
            return item
        for index in range(item.childCount()):
            found = self._find_item_recursive(item.child(index), key)
            if found is not None:
                return found
        return None
