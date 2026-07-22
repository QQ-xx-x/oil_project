# -*- coding: utf-8 -*-
"""工程打开后的业务输入树。"""

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QBrush, QColor
from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem

from .configuration_status import (
    STATUS_CONFIGURED_COLOR,
    STATUS_MISSING_COLOR,
    geometry_is_configured,
    grid_properties_are_configured,
    model_configuration_is_configured,
)
from .icons import painted_icon
from .input_keyword_registry import (
    MODULE_FRACTURE_SYSTEM,
    MODULE_FLUID_PVT,
    MODULE_GRID_SPATIAL,
    MODULE_HISTORY_MATCHING,
    MODULE_INITIAL_CONDITIONS,
    MODULE_MODEL_CONFIGURATION,
    MODULE_ROCK_PROPERTIES,
    MODULE_SOLVER_OUTPUT,
    MODULE_SPECS,
    MODULE_WELL_PRODUCTION,
)
from .module_input_dialog import ModuleInputDialog
from .grid_geometry_dialog import GridGeometryDialog
from .grid_property_dialog import GridPropertyDialog
from .project_state import MODEL_TYPE_WR, normalize_model_config
from .settings_dialog import ObjectSettingsDialog


KEY_ROLE = Qt.UserRole
TYPE_ROLE = Qt.UserRole + 1
DATA_ROLE = Qt.UserRole + 2


MODULE_ICONS = {
    MODULE_MODEL_CONFIGURATION: "settings",
    MODULE_GRID_SPATIAL: "grid",
    MODULE_ROCK_PROPERTIES: "rock",
    MODULE_FRACTURE_SYSTEM: "fracture",
    MODULE_FLUID_PVT: "fluid",
    MODULE_INITIAL_CONDITIONS: "initial",
    MODULE_WELL_PRODUCTION: "well",
    MODULE_SOLVER_OUTPUT: "solver",
    MODULE_HISTORY_MATCHING: "chart",
}


class InputTree(QTreeWidget):
    """由注册表驱动的业务输入模块导航树。源数据段、关键字名、文件路径和文件状态节点会被刻意排除；它们仍是后端导入细节，由模块导入服务处理。"""

    module_selected = pyqtSignal(str, str)
    parameters_saved = pyqtSignal(str, str, dict)
    result_requested = pyqtSignal(str)
    workflow_requested = pyqtSignal(str, str, str)
    model_config_requested = pyqtSignal()

    def __init__(self, project_state=None, parent=None):
        super().__init__(parent)
        self.project_state = project_state
        self._building = False
        self.setObjectName("inputTree")
        self.setHeaderHidden(True)
        self.setExpandsOnDoubleClick(False)
        self.currentItemChanged.connect(self._emit_selection)
        self.itemDoubleClicked.connect(self._open_settings)
        self._populate()
        self.expandToDepth(0)
        self.refresh_model_config_visibility()

    def _item(self, text, key, object_type="参数模块", icon_name="generic",
              tooltip=None):
        item = QTreeWidgetItem([text])
        item.setData(0, KEY_ROLE, key)
        item.setData(0, TYPE_ROLE, object_type)
        item.setIcon(0, painted_icon(icon_name, 16))
        if tooltip:
            item.setToolTip(0, tooltip)
        return item

    def _populate(self):
        """根据规范注册表构建完整可见树。"""

        self._building = True
        self.clear()
        for module in MODULE_SPECS:
            icon_name = MODULE_ICONS.get(module.key, "generic")
            module_item = self._item(
                module.title,
                module.key,
                "功能模块",
                icon_name,
                self._module_tooltip(module),
            )
            module_item.setData(0, DATA_ROLE, {
                "kind": "module",
                "module_key": module.key,
            })
            self._add_business_groups(module_item, module, icon_name)
            self.addTopLevelItem(module_item)
        self._building = False

    def _add_business_groups(self, module_item, module, icon_name):
        for group in module.groups:
            tree_key = self.group_tree_key(module.key, group.key)
            group_item = self._item(
                group.title,
                tree_key,
                "业务分组",
                icon_name,
                f"{module.title} / {group.title}",
            )
            group_item.setData(0, DATA_ROLE, {
                "kind": "group",
                "module_key": module.key,
                "child_key": group.key,
                "group_title": group.title,
            })
            module_item.addChild(group_item)

    @staticmethod
    def group_tree_key(module_key, group_key):
        return f"input_group:{module_key}:{group_key}"

    @staticmethod
    def _module_tooltip(module):
        if not module.groups:
            return module.title
        return f"{module.title}\n业务分组数量: {len(module.groups)}"

    def _emit_selection(self, current, previous):
        if current is None:
            return
        key = current.data(0, KEY_ROLE)
        if self.project_state is not None:
            self.project_state.ui_state["input_tree_current_key"] = key
        self.module_selected.emit(key, current.text(0))

    def _open_settings(self, item, column):
        if item.isDisabled():
            return
        data = item.data(0, DATA_ROLE) or {}
        module_key = data.get("module_key")

        if module_key == MODULE_MODEL_CONFIGURATION:
            self.model_config_requested.emit()
            return
        if module_key == MODULE_HISTORY_MATCHING:
            self.workflow_requested.emit(
                "history_matching", "历史拟合", "chart")
            return

        # “网格与空间数据”仅作为导航容器；具体配置统一从其小节点进入。
        if (module_key == MODULE_GRID_SPATIAL
                and not data.get("child_key")):
            return

        if (module_key == MODULE_GRID_SPATIAL
                and data.get("child_key") == "geometry"
                and self.project_state is not None):
            dialog = GridGeometryDialog(self.project_state, self)
            dialog.values_applied.connect(self._forward_values_applied)
            dialog.exec_()
            return

        if (module_key == MODULE_GRID_SPATIAL
                and data.get("child_key") == "grid_properties"
                and self.project_state is not None):
            dialog = GridPropertyDialog(self.project_state, self)
            dialog.values_applied.connect(self._forward_values_applied)
            dialog.exec_()
            return

        if module_key in MODULE_ICONS and self.project_state is not None:
            dialog = ModuleInputDialog(
                module_key, self.project_state, data.get("child_key"), self)
            dialog.values_applied.connect(self._forward_values_applied)
            dialog.exec_()
            self.refresh_model_config_visibility()
            return

        dialog = ObjectSettingsDialog(
            item.text(0), item.data(0, TYPE_ROLE) or "工程对象", self)
        dialog.exec_()

    def _forward_values_applied(self, module_key, title, values):
        self.refresh_configuration_statuses()
        self.parameters_saved.emit(module_key, title, values)

    def refresh_case_data_sections(self, preserve_expanded=True):
        """旧版兼容入口；不再构建原始 CaseData 节点。"""

        return None

    def refresh_model_config_visibility(self):
        """保持树结构稳定，同时反映依赖模型的分组状态。"""

        if self.project_state is None:
            return
        config = normalize_model_config(
            getattr(self.project_state, "model_config", None))
        is_wr = config.get("model_type") == MODEL_TYPE_WR
        enabled_by_group = {
            (MODULE_ROCK_PROPERTIES, "shape_factor"): is_wr,
            (MODULE_FRACTURE_SYSTEM,
             "equivalent_fracture_properties"): is_wr,
            (MODULE_FLUID_PVT, "gas_components"): bool(
                config.get("enable_real_gas_pvt")),
            (MODULE_FLUID_PVT, "pvt_table"): bool(
                config.get("enable_real_gas_pvt")),
        }
        for index in range(self.topLevelItemCount()):
            module_item = self.topLevelItem(index)
            for child_index in range(module_item.childCount()):
                child = module_item.child(child_index)
                data = child.data(0, DATA_ROLE) or {}
                identity = (
                    data.get("module_key"), data.get("child_key"))
                if identity in enabled_by_group:
                    child.setDisabled(not enabled_by_group[identity])
                else:
                    child.setDisabled(False)
        current = self.currentItem()
        if current is not None and current.isDisabled():
            self.setCurrentItem(None)
        self.refresh_configuration_statuses()

    def refresh_configuration_statuses(self):
        """Apply red/green status text to the three configured workflow nodes."""
        if self.project_state is None:
            return
        targets = (
            (
                self._find_item(MODULE_MODEL_CONFIGURATION),
                model_configuration_is_configured(self.project_state),
            ),
            (
                self._find_item(self.group_tree_key(
                    MODULE_GRID_SPATIAL, "geometry")),
                geometry_is_configured(self.project_state),
            ),
            (
                self._find_item(self.group_tree_key(
                    MODULE_GRID_SPATIAL, "grid_properties")),
                grid_properties_are_configured(self.project_state),
            ),
        )
        for item, configured in targets:
            if item is None:
                continue
            color = (
                STATUS_CONFIGURED_COLOR
                if configured else STATUS_MISSING_COLOR)
            item.setForeground(0, QBrush(QColor(color)))
            font = item.font(0)
            font.setBold(True)
            item.setFont(0, font)
            item.setToolTip(
                0, "配置状态：已配置" if configured else "配置状态：尚未配置或数据无效")

    def export_ui_state(self):
        current_key = None
        if self.currentItem() is not None:
            current_key = self.currentItem().data(0, KEY_ROLE)
        return {
            "current_key": current_key,
            "expanded_keys": sorted(self._all_expanded_keys()),
        }

    def restore_ui_state(self, state):
        state = state or {}
        if "expanded_keys" in state:
            self.collapseAll()
        self._restore_expanded_keys(set(state.get("expanded_keys") or []))
        current_key = state.get("current_key")
        if current_key:
            self.select_key(current_key)

    def select_key(self, key):
        item = self._find_item(key)
        if (item is None or item.isDisabled()
                or self._item_or_ancestor_hidden(item)):
            return False
        self.setCurrentItem(item)
        self.scrollToItem(item)
        return True

    def _all_expanded_keys(self):
        keys = set()

        def visit(item):
            key = item.data(0, KEY_ROLE)
            if item.isExpanded() and key:
                keys.add(key)
            for index in range(item.childCount()):
                visit(item.child(index))

        for index in range(self.topLevelItemCount()):
            visit(self.topLevelItem(index))
        return keys

    def _restore_expanded_keys(self, keys):
        def visit(item):
            if item.data(0, KEY_ROLE) in keys:
                item.setExpanded(True)
            for index in range(item.childCount()):
                visit(item.child(index))

        for index in range(self.topLevelItemCount()):
            visit(self.topLevelItem(index))

    @staticmethod
    def _item_or_ancestor_hidden(item):
        current = item
        while current is not None:
            if current.isHidden():
                return True
            current = current.parent()
        return False

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
