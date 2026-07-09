# -*- coding: utf-8 -*-
"""工程打开后使用的结果树。"""

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem

from .icons import painted_icon


KEY_ROLE = Qt.UserRole
TYPE_ROLE = Qt.UserRole + 1
VIEW_ROLE = Qt.UserRole + 2


class ResultsTree(QTreeWidget):
    result_selected = pyqtSignal(str, str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._building = False
        self.setObjectName("resultsTree")
        self.setHeaderHidden(True)
        self.currentItemChanged.connect(self._emit_selection)
        self._populate()

    def _item(self, text, key, item_type="folder", view="3d",
              layer_key=None, checked=False, icon_name="folder",
              icon_status=None, tooltip=None):
        item = QTreeWidgetItem([text])
        item.setData(0, KEY_ROLE, key)
        item.setData(0, TYPE_ROLE, item_type)
        item.setData(0, VIEW_ROLE, view)
        item.setIcon(0, painted_icon(icon_name, 16, icon_status))
        if tooltip:
            item.setToolTip(0, tooltip)
        return item

    def _populate(self):
        self._building = True

        root = self._item(
            "结果",
            "results_root",
            icon_name="result",
            tooltip="模拟结果与分析入口",
        )

        simulation = self._item(
            "三维网格结果",
            "simulation_grid_results",
            icon_name="grid",
            tooltip="三维网格属性场结果",
        )
        result_icons = {
            "pressure_field": "pressure",
            "water_saturation_field": "saturation",
            "porosity_field": "porosity",
            "permeability_x_field": "permeability",
            "permeability_y_field": "permeability",
            "permeability_z_field": "permeability",
        }
        for text, key in [
            ("压力场", "pressure_field"),
            ("含水饱和度场", "water_saturation_field"),
            ("孔隙度场", "porosity_field"),
            ("Kx 渗透率场", "permeability_x_field"),
            ("Ky 渗透率场", "permeability_y_field"),
            ("Kz 渗透率场", "permeability_z_field"),
        ]:
            simulation.addChild(self._item(
                text,
                key,
                "result",
                "3d",
                icon_name=result_icons.get(key, "result"),
                tooltip=f"在 3D 窗口中查看{text}",
            ))
        root.addChild(simulation)

        charts = self._item(
            "曲线与分析",
            "chart_analysis",
            "folder",
            "chart",
            icon_name="chart",
            tooltip="曲线、图表和分析结果",
        )
        for text, key, icon_name, tooltip in [
            ("生产曲线", "production_curve", "chart", "打开生产曲线图表"),
            ("历史拟合", "history_matching", "chart", "打开历史拟合参数和结果页"),
            ("相对渗透率曲线", "relative_permeability_curve", "permeability", "打开相对渗透率曲线"),
            ("PVT 表曲线", "pvt_curve", "fluid", "打开 PVT 表曲线"),
            ("Blasingame 曲线", "blasingame_curve", "chart", "打开 Blasingame 分析曲线"),
        ]:
            charts.addChild(self._item(
                text,
                key,
                "chart",
                "chart",
                icon_name=icon_name,
                tooltip=tooltip,
            ))
        root.addChild(charts)

        self.addTopLevelItem(root)
        self._building = False
        self._expand_default_nodes()

    def _expand_default_nodes(self):
        for key in {"results_root", "simulation_grid_results", "chart_analysis"}:
            item = self._find_item(key)
            if item is not None:
                item.setExpanded(True)

    def _emit_selection(self, current, previous):
        if current is None:
            return
        key = current.data(0, KEY_ROLE)
        view = current.data(0, VIEW_ROLE) or "3d"
        self.result_selected.emit(key, current.text(0), view)

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

    def export_ui_state(self):
        expanded_keys = []
        for item in self._iter_items():
            key = item.data(0, KEY_ROLE)
            if key and item.isExpanded():
                expanded_keys.append(key)
        current = self.currentItem()
        return {
            "current_key": current.data(0, KEY_ROLE) if current is not None else None,
            "expanded_keys": expanded_keys,
        }

    def restore_ui_state(self, state):
        if not isinstance(state, dict):
            self._expand_default_nodes()
            return
        self._building = True
        try:
            expanded_keys = set(state.get("expanded_keys") or [])
            for item in self._iter_items():
                key = item.data(0, KEY_ROLE)
                if key:
                    item.setExpanded(key in expanded_keys)
        finally:
            self._building = False
        self._expand_default_nodes()
        current_key = state.get("current_key")
        if current_key:
            item = self._find_item(current_key)
            if item is not None:
                self.setCurrentItem(item)
                self.scrollToItem(item)

    def _iter_items(self):
        for index in range(self.topLevelItemCount()):
            yield from self._iter_item_recursive(self.topLevelItem(index))

    def _iter_item_recursive(self, item):
        yield item
        for index in range(item.childCount()):
            yield from self._iter_item_recursive(item.child(index))
