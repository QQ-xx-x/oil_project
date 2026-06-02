# -*- coding: utf-8 -*-
"""Input-data tree used after a project is opened."""

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem

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


class InputTree(QTreeWidget):
    module_selected = pyqtSignal(str, str)
    module_checked = pyqtSignal(str, str, bool)
    parameters_saved = pyqtSignal(str, str, dict)

    def __init__(self, project_state=None, parent=None):
        super().__init__(parent)
        self.project_state = project_state
        self._building = False
        self._panel_factories = {
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
        self.currentItemChanged.connect(self._emit_selection)
        self.itemChanged.connect(self._store_check_state)
        self.itemDoubleClicked.connect(self._open_settings)
        self._populate()
        self.expandToDepth(1)

    def _item(self, text, key, object_type="参数模块", checked=False,
              icon_name="generic"):
        item = QTreeWidgetItem([text])
        item.setData(0, KEY_ROLE, key)
        item.setData(0, TYPE_ROLE, object_type)
        item.setIcon(0, painted_icon(icon_name, 16))
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
        item.setCheckState(0, Qt.Checked if checked else Qt.Unchecked)
        if self.project_state is not None:
            self.project_state.set_checked(key, checked)
        return item

    def _populate(self):
        self._building = True
        module_tree = [
            ("网格与基础参数", "grid_foundation", "文件夹", "folder", True, [
                ("网格加密", "grid_refinement_enabled", "网格开关", "generic", False),
                ("网格文件导入", "grid_file_import", "导入操作", "import", False),
                ("网格参数", "grid_basic", "网格参数", "window", True),
                ("初始状态", "initial_state", "初始状态参数", "generic", True),
                ("基质属性", "matrix_properties", "岩石参数", "database", True),
                ("双重介质", "dual_porosity", "岩石参数", "database", False),
                ("模拟控制", "simulation_control", "模拟参数", "window", True),
            ]),
            ("流体属性", "fluid_properties", "文件夹", "folder", True, [
                ("油水相基础参数", "oil_water_properties", "流体参数", "database", True),
                ("气相真实气体 PVT", "gas_pvt", "流体参数", "database", False),
            ]),
            ("井参数", "well_system", "文件夹", "folder", True, [
                ("井基础参数", "well_parameters", "井参数", "generic", True),
            ]),
            ("裂缝参数", "fracture_system", "文件夹", "folder", True, [
                ("启用人工裂缝", "enable_hydraulic_fractures", "裂缝开关", "generic", True),
                ("天然裂缝", "natural_fractures", "裂缝参数", "generic", True),
                ("人工裂缝", "hydraulic_fractures", "裂缝参数", "generic", True),
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
        self.module_selected.emit(current.data(0, KEY_ROLE), current.text(0))

    def _open_settings(self, item, column):
        key = item.data(0, KEY_ROLE)
        object_type = item.data(0, TYPE_ROLE) or "工程对象"
        panel_factory = self._panel_factories.get(key)
        if panel_factory and self.project_state is not None:
            dialog = ParameterSettingsDialog(
                key, item.text(0), panel_factory, self.project_state,
                object_type, self)
            dialog.values_applied.connect(
                lambda values, module_key=key, title=item.text(0):
                    self.parameters_saved.emit(module_key, title, values))
        else:
            dialog = ObjectSettingsDialog(item.text(0), object_type, self)
        dialog.exec_()
