# -*- coding: utf-8 -*-
"""工程左侧可切换面板使用的辅助树。"""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem

from .icons import painted_icon


class SimpleTree(QTreeWidget):
    def __init__(self, object_name, spec, parent=None):
        super().__init__(parent)
        self.setObjectName(object_name)
        self.setHeaderHidden(True)
        self._populate(spec)
        self.expandToDepth(1)

    def _item(self, text, icon_name="generic", checked=False, checkable=True):
        item = QTreeWidgetItem([text])
        item.setIcon(0, painted_icon(icon_name, 16))
        if checkable:
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(0, Qt.Checked if checked else Qt.Unchecked)
        return item

    def _populate(self, spec):
        for entry in spec:
            self.addTopLevelItem(self._build_item(entry))

    def _build_item(self, entry):
        if isinstance(entry, str):
            return self._item(entry)
        text = entry.get("text", "")
        icon = entry.get("icon", "generic")
        checked = entry.get("checked", False)
        checkable = entry.get("checkable", True)
        item = self._item(text, icon, checked, checkable)
        for child in entry.get("children", []):
            item.addChild(self._build_item(child))
        return item


class CasesTree(SimpleTree):
    def __init__(self, parent=None):
        super().__init__("casesTree", [
            {
                "text": "算例", "icon": "case", "checked": True, "children": [
                    {"text": "Case", "icon": "database"},
                    {"text": "10year", "icon": "warning"},
                    {"text": "new", "icon": "warning"},
                    {"text": "11", "icon": "warning"},
                    {"text": "22", "icon": "warning"},
                    {"text": "33", "icon": "warning"},
                    {"text": "44", "icon": "warning"},
                    {"text": "55", "icon": "warning"},
                    {"text": "new1", "icon": "generic", "checked": True},
                    {"text": "400ABC", "icon": "warning"},
                    {"text": "26zhi36", "icon": "warning"},
                    {"text": "26zhi36new", "icon": "warning"},
                    {"text": "Spacing400", "icon": "warning"},
                ],
            },
        ], parent)


class TemplatesTree(SimpleTree):
    def __init__(self, parent=None):
        super().__init__("templatesTree", [
            {
                "text": "工程模板", "icon": "folder", "checked": True, "children": [
                    {"text": "黑油模型", "icon": "database"},
                    {"text": "角点网格模型", "icon": "grid"},
                    {"text": "压裂井模型", "icon": "well"},
                    {"text": "历史拟合模型", "icon": "chart"},
                ],
            },
            {
                "text": "导入模板", "icon": "folder", "checked": True, "children": [
                    {"text": "井数据模板", "icon": "well"},
                    {"text": "网格模板", "icon": "grid"},
                    {"text": "PVT 模板", "icon": "database"},
                    {"text": "结果模板", "icon": "chart"},
                ],
            },
        ], parent)


class ProcessesTree(SimpleTree):
    def __init__(self, parent=None):
        super().__init__("processesTree", [
            {"text": "输入", "icon": "process", "checked": True, "children": [
                {"text": "导入数据", "icon": "import"},
            ]},
            {"text": "地层学", "icon": "folder", "checked": True},
            {"text": "地球物理", "icon": "folder", "checked": True},
            {"text": "构造框架", "icon": "folder", "checked": True},
            {"text": "角点网格", "icon": "grid", "checked": True},
            {"text": "属性建模", "icon": "folder", "checked": True, "children": [
                {"text": "几何建模", "icon": "grid"},
                {"text": "井日志尺度化", "icon": "well"},
                {"text": "数据分析", "icon": "chart"},
                {"text": "几何趋势建模", "icon": "process"},
                {"text": "趋势建模", "icon": "process"},
                {"text": "用户自定义对象创建", "icon": "new"},
                {"text": "训练图像与模式创建", "icon": "chart"},
                {"text": "相建模", "icon": "database"},
                {"text": "岩石物理建模", "icon": "database"},
            ]},
            {"text": "升尺度", "icon": "process", "checked": True},
            {"text": "裂缝网络建模", "icon": "folder", "checked": True},
            {"text": "井工程", "icon": "well", "checked": True},
            {"text": "模拟", "icon": "monitor", "checked": True},
            {"text": "工具", "icon": "generic", "checked": True},
            {"text": "插件", "icon": "generic", "checked": True},
            {"text": "碳封存模型构建", "icon": "database", "checked": True},
            {"text": "用户资源导出", "icon": "import", "checked": True},
            {"text": "用户资源文件夹导出", "icon": "folder", "checked": True},
            {"text": "勘探评价", "icon": "search", "checked": True},
            {"text": "地质力学", "icon": "grid", "checked": True},
            {"text": "盆地建模", "icon": "folder", "checked": True},
        ], parent)


class ModelsTree(SimpleTree):
    def __init__(self, parent=None):
        super().__init__("modelsTree", [
            {"text": "构造框架", "icon": "grid", "checked": False},
            {"text": "New model", "icon": "folder", "checked": False},
            {"text": "4.21", "icon": "folder", "checked": False},
            {"text": "Kinetix zone sets", "icon": "folder", "checked": False},
            {"text": "Kinetix fracture simulation jobs", "icon": "warning", "checked": False},
            {"text": "Kinetix production grids for Zone set 1", "icon": "warning", "checked": False},
            {"text": "Kinetix production grids for Zone", "icon": "folder", "checked": True, "children": [
                {"text": "Production grid 1 HFN", "icon": "grid"},
                {"text": "Production grid 1", "icon": "grid"},
                {"text": "Production grid 2_Fracture grid", "icon": "grid"},
                {"text": "Production grid 2 HFN", "icon": "grid"},
                {"text": "Production grid 2", "icon": "grid"},
                {"text": "Production grid 3 HFN", "icon": "grid"},
                {"text": "Production grid 3", "icon": "grid"},
                {"text": "Production grid 3_Fracture grid", "icon": "grid", "checked": True, "children": [
                    {"text": "Intersections", "icon": "process", "checked": True},
                    {"text": "Properties", "icon": "database", "checked": True, "children": [
                        {"text": "Cell volume", "icon": "chart"},
                        {"text": "Porosity", "icon": "chart"},
                        {"text": "Permeability", "icon": "chart"},
                    ]},
                ]},
            ]},
        ], parent)


class WindowsTree(SimpleTree):
    def __init__(self, parent=None):
        super().__init__("windowsTree", [
            {"text": "Cursor tracking", "icon": "generic", "checked": False},
            {"text": "Output sheet", "icon": "window", "checked": False},
            {"text": "Stratigraphy", "icon": "folder", "checked": False},
            {"text": "Map window 1", "icon": "chart", "checked": False},
            {"text": "3D window 7 [Any]", "icon": "grid", "checked": False},
            {"text": "2D window 7 [Any]", "icon": "window", "checked": True},
            {"text": "3D window 1 [Any]", "icon": "grid", "checked": False},
            {"text": "3D window 2 [Any]", "icon": "grid", "checked": False},
            {"text": "3D window 3 [Any]", "icon": "grid", "checked": False},
            {"text": "3D window 4 [Any]", "icon": "grid", "checked": False},
            {"text": "3D window 5 [Any]", "icon": "grid", "checked": True},
            {"text": "2D window 1 [Any]", "icon": "window", "checked": False},
            {"text": "Charting window 1", "icon": "chart", "checked": True},
            {"text": "Custom window manager", "icon": "warning", "checked": False},
            {"text": "3D window 6 [Any]", "icon": "grid", "checked": False},
            {"text": "3D window 8 [Any]", "icon": "grid", "checked": False},
            {"text": "2D window 2 [Any]", "icon": "window", "checked": False},
            {"text": "3D window 9 [Any]", "icon": "grid", "checked": False},
        ], parent)
