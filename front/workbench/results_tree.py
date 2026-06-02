# -*- coding: utf-8 -*-
"""Result tree used after a project is opened."""

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem

from .icons import painted_icon


KEY_ROLE = Qt.UserRole
TYPE_ROLE = Qt.UserRole + 1
VIEW_ROLE = Qt.UserRole + 2
LAYER_ROLE = Qt.UserRole + 3


class ResultsTree(QTreeWidget):
    result_selected = pyqtSignal(str, str, str)
    layer_checked = pyqtSignal(str, str, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._building = False
        self.setObjectName("resultsTree")
        self.setHeaderHidden(True)
        self.currentItemChanged.connect(self._emit_selection)
        self.itemChanged.connect(self._emit_layer_state)
        self._populate()
        self.expandToDepth(2)

    def _item(self, text, key, item_type="folder", view="3d",
              layer_key=None, checked=False, icon_name="folder"):
        item = QTreeWidgetItem([text])
        item.setData(0, KEY_ROLE, key)
        item.setData(0, TYPE_ROLE, item_type)
        item.setData(0, VIEW_ROLE, view)
        item.setData(0, LAYER_ROLE, layer_key)
        item.setIcon(0, painted_icon(icon_name, 16))
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
        item.setCheckState(0, Qt.Checked if checked else Qt.Unchecked)
        return item

    def _populate(self):
        self._building = True

        root = self._item("Results", "results_root", checked=True, icon_name="chart")
        root.addChild(self._item("Files", "result_files", checked=False, icon_name="folder"))
        root.addChild(self._item(
            "Dynamic results data", "dynamic_results_data", checked=False, icon_name="database"))
        root.addChild(self._item("Identifier", "identifier", checked=False, icon_name="folder"))

        source = self._item("Source data type", "source_data_type", checked=True, icon_name="folder")
        source.addChild(self._item("Observed data", "observed_data", checked=False, icon_name="database"))
        root.addChild(source)

        root.addChild(self._item("RFT/PLT studies", "rft_plt_studies", checked=False, icon_name="folder"))
        root.addChild(self._item("Volumetrics", "volumetrics", checked=False, icon_name="database"))

        simulation = self._item(
            "Simulation grid results", "simulation_grid_results",
            checked=True, icon_name="grid")
        for text, key in [
            ("压力场", "pressure_field"),
            ("含水饱和度场", "water_saturation_field"),
            ("渗透率场", "permeability_field"),
            ("孔隙度场", "porosity_field"),
        ]:
            simulation.addChild(self._item(
                text, key, "result", "3d", checked=(key == "pressure_field"),
                icon_name="database"))
        root.addChild(simulation)

        charts = self._item(
            "Results charts and analyses", "chart_analysis",
            "folder", "chart", checked=True, icon_name="folder")
        study_1 = self._item("Study 1", "study_1", "folder", "chart", checked=True, icon_name="folder")
        study_1.addChild(self._item(
            "Chart 1 - 生产曲线", "production_curve", "chart", "chart",
            checked=False, icon_name="chart"))
        study_2 = self._item("Study 2", "study_2", "folder", "chart", checked=True, icon_name="folder")
        study_2.addChild(self._item(
            "Chart 1 - 相对渗透率曲线", "relative_permeability_curve",
            "chart", "chart", checked=False, icon_name="chart"))
        study_2.addChild(self._item(
            "PVT 表曲线", "pvt_curve", "chart", "chart",
            checked=False, icon_name="chart"))
        study_2.addChild(self._item(
            "Blasingame 曲线", "blasingame_curve", "chart", "chart",
            checked=False, icon_name="chart"))
        charts.addChild(study_1)
        charts.addChild(study_2)
        charts.addChild(self._item("Chart themes", "chart_themes", checked=False, icon_name="chart"))
        charts.addChild(self._item("Series styles", "series_styles", checked=False, icon_name="chart"))
        charts.addChild(self._item("Splits and groups", "splits_groups", checked=False, icon_name="process"))
        root.addChild(charts)

        layers = self._item("图层控制", "layer_control", "folder", "3d", checked=True, icon_name="folder")
        for text, key, layer_key, checked in [
            ("网格", "layer_grid", "grid", True),
            ("网格加密区域", "layer_grid_refinement", "grid_refinement", False),
            ("井轨迹", "layer_well", "well", True),
            ("天然裂缝", "layer_natural_fractures", "natural_fractures", True),
            ("人工裂缝", "layer_hydraulic_fractures", "hydraulic_fractures", True),
        ]:
            layers.addChild(self._item(
                text, key, "layer", "3d", layer_key, checked, icon_name="window"))
        root.addChild(layers)

        self.addTopLevelItem(root)
        self._building = False

    def _emit_selection(self, current, previous):
        if current is None:
            return
        key = current.data(0, KEY_ROLE)
        item_type = current.data(0, TYPE_ROLE)
        view = current.data(0, VIEW_ROLE) or "3d"
        self.result_selected.emit(key, current.text(0), view)
        if item_type == "layer":
            layer_key = current.data(0, LAYER_ROLE)
            self.layer_checked.emit(
                layer_key, current.text(0), current.checkState(0) == Qt.Checked)

    def _emit_layer_state(self, item, column):
        if self._building or column != 0:
            return
        if item.data(0, TYPE_ROLE) != "layer":
            return
        layer_key = item.data(0, LAYER_ROLE)
        self.layer_checked.emit(
            layer_key, item.text(0), item.checkState(0) == Qt.Checked)
