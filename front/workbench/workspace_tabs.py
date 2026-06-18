# -*- coding: utf-8 -*-
"""工程打开后使用的中央多窗口工作区。"""

from PyQt5.QtCore import QSize, Qt, pyqtSignal
from PyQt5.QtWidgets import QAction, QMenu, QTabWidget, QToolButton

from .icon_registry import semantic_icon_kind
from .icons import painted_icon
from .viewport_placeholders import ChartViewport, ThreeDViewport, TwoDViewport, ViewPage


class WorkspaceTabs(QTabWidget):
    workspace_message = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("workspaceTabs")
        self.setTabsClosable(True)
        self.setMovable(True)
        self.setContextMenuPolicy(Qt.CustomContextMenu)

        self._counters = {"2d": 2, "3d": 1, "chart": 1}
        self._last_context = (
            "当前结果：三维视图",
            "在结果树中选择结果或图层后，这里显示对应占位视图。",
            "permeability_field",
        )

        self.two_d_primary = self._create_page("2d")
        self.three_d = self._create_page("3d")
        self.chart = self._create_page("chart")
        self.two_d_secondary = self._create_page("2d")

        self._add_page(self.two_d_primary, "2d", "2D窗口 1")
        self._add_page(self.three_d, "3d", "3D窗口 1")
        self._add_page(self.chart, "chart", "图表窗口 1")
        self._add_page(self.two_d_secondary, "2d", "2D窗口 2")
        self.setCurrentWidget(self.three_d)

        self.tabCloseRequested.connect(self.close_window)
        self.customContextMenuRequested.connect(self._show_tab_menu)
        self.setCornerWidget(self._create_add_button(), Qt.TopRightCorner)

    def _create_add_button(self):
        button = QToolButton()
        button.setObjectName("workspaceAddButton")
        button.setIcon(painted_icon("new", 16))
        button.setIconSize(QSize(16, 16))
        button.setToolTip("新建工作窗口")
        button.setFixedSize(24, 23)
        button.setPopupMode(QToolButton.InstantPopup)
        button.setMenu(self._new_window_menu())
        return button

    def _new_window_menu(self):
        menu = QMenu(self)
        for text, view_type, kind in [
            ("新建 2D 窗口", "2d", "window"),
            ("新建 3D 窗口", "3d", "grid"),
            ("新建图表窗口", "chart", "chart"),
        ]:
            menu.addAction(self._menu_action(
                text, kind, lambda checked=False, vt=view_type: self.add_window(vt)))
        return menu

    def _menu_action(self, text, kind, callback, enabled=True):
        icon_kind = semantic_icon_kind(kind, text)
        action = QAction(painted_icon(icon_kind, 16), text, self)
        action.setEnabled(enabled)
        if enabled:
            action.triggered.connect(callback)
        return action

    def _create_page(self, view_type):
        viewport = {
            "2d": TwoDViewport,
            "3d": ThreeDViewport,
            "chart": ChartViewport,
        }[view_type]()
        page = ViewPage(viewport, view_type)
        page.new_window_requested.connect(lambda: self._show_new_menu_from_page(page))
        page.clone_window_requested.connect(lambda: self.clone_window(self.indexOf(page)))
        page.close_window_requested.connect(lambda: self.close_window(self.indexOf(page)))
        return page

    def _add_page(self, page, view_type, title):
        icon_map = {"2d": "window", "3d": "grid", "chart": "chart"}
        icon_kind = semantic_icon_kind(icon_map[view_type], title)
        index = self.addTab(page, painted_icon(icon_kind, 16), title)
        page.setProperty("viewType", view_type)
        return index

    def _show_new_menu_from_page(self, page):
        menu = self._new_window_menu()
        toolbar = getattr(page, "toolbar", None)
        if toolbar is not None:
            menu.exec_(toolbar.mapToGlobal(toolbar.rect().bottomLeft()))

    def add_window(self, view_type):
        self._counters[view_type] += 1
        title = self._title_for(view_type, self._counters[view_type])
        page = self._create_page(view_type)
        self._apply_last_context(page)
        index = self._add_page(page, view_type, title)
        self.setCurrentIndex(index)
        self._refresh_primary_references()
        self.workspace_message.emit(f"[窗口] 已新建 {title}")

    def clone_window(self, index=None):
        index = self.currentIndex() if index is None else index
        if index < 0:
            return
        source = self.widget(index)
        view_type = source.property("viewType") or "3d"
        self._counters[view_type] += 1
        title = self._title_for(view_type, self._counters[view_type])
        page = self._create_page(view_type)
        self._copy_page_context(source, page)
        new_index = self._add_page(page, view_type, title)
        self.setCurrentIndex(new_index)
        self._refresh_primary_references()
        self.workspace_message.emit(f"[窗口] 已复制为 {title}")

    def close_window(self, index=None):
        index = self.currentIndex() if index is None else index
        if self.count() <= 1:
            self.workspace_message.emit("[窗口] 至少保留一个工作窗口")
            return
        if index < 0:
            return
        title = self.tabText(index)
        page = self.widget(index)
        self.removeTab(index)
        page.deleteLater()
        self._refresh_primary_references()
        self.workspace_message.emit(f"[窗口] 已关闭 {title}")

    def close_other_windows(self, index):
        if index < 0:
            return
        keep = self.widget(index)
        keep_title = self.tabText(index)
        for tab_index in reversed(range(self.count())):
            if self.widget(tab_index) is keep:
                continue
            page = self.widget(tab_index)
            self.removeTab(tab_index)
            page.deleteLater()
        self.setCurrentWidget(keep)
        self._refresh_primary_references()
        self.workspace_message.emit(f"[窗口] 已关闭其他窗口，保留 {keep_title}")

    def _show_tab_menu(self, pos):
        index = self.tabBar().tabAt(pos)
        if index < 0:
            return
        menu = QMenu(self)
        menu.addAction(self._menu_action("关闭窗口", "close", lambda: self.close_window(index)))
        menu.addAction(self._menu_action(
            "关闭其他窗口", "close", lambda: self.close_other_windows(index)))
        menu.addAction(self._menu_action("复制窗口", "copy", lambda: self.clone_window(index)))
        menu.addAction(self._menu_action("重命名窗口", "edit", lambda: None, enabled=False))
        menu.addSeparator()
        for text, view_type, kind in [
            ("新建 2D 窗口", "2d", "window"),
            ("新建 3D 窗口", "3d", "grid"),
            ("新建图表窗口", "chart", "chart"),
        ]:
            menu.addAction(self._menu_action(
                text, kind, lambda checked=False, vt=view_type: self.add_window(vt)))
        menu.exec_(self.tabBar().mapToGlobal(pos))

    def update_context(self, title, detail, preferred_view="3d", display_key=None):
        self._last_context = (title, detail, display_key)
        for page in self._pages():
            page.set_context(title, detail, display_key)
        target = self._first_page_of_type(preferred_view)
        if target is not None:
            self.setCurrentWidget(target)

    def set_layer_state(self, layer_key, enabled):
        for page in self._pages_of_type("3d"):
            page.set_layer_state(layer_key, enabled)

    def set_simulation_data(self, sim_data):
        for page in self._pages_of_type("3d"):
            page.set_simulation_data(sim_data)

    def set_chart_data(self, chart_key, data):
        for page in self._pages_of_type("chart"):
            page.set_chart_data(chart_key, data)

    def _apply_last_context(self, page):
        title, detail, display_key = self._last_context
        page.set_context(title, detail, display_key)

    def _copy_page_context(self, source, target):
        viewport = getattr(source, "viewport", None)
        title = getattr(viewport, "context_title", self._last_context[0])
        detail = getattr(viewport, "context_detail", self._last_context[1])
        display_key = getattr(viewport, "display_key", self._last_context[2])
        target.set_context(title, detail, display_key)

    def _first_page_of_type(self, view_type):
        if view_type == "2d":
            view_type = "2d"
        for page in self._pages_of_type(view_type):
            return page
        return None

    def _pages_of_type(self, view_type):
        return [
            self.widget(index)
            for index in range(self.count())
            if self.widget(index).property("viewType") == view_type
        ]

    def _pages(self):
        return [self.widget(index) for index in range(self.count())]

    def _refresh_primary_references(self):
        self.two_d_primary = self._first_page_of_type("2d")
        self.three_d = self._first_page_of_type("3d")
        self.chart = self._first_page_of_type("chart")
        self.two_d_secondary = None
        for page in self._pages_of_type("2d"):
            if page is not self.two_d_primary:
                self.two_d_secondary = page
                break

    def _title_for(self, view_type, number):
        if view_type == "chart":
            return f"图表窗口 {number}"
        label = "2D窗口" if view_type == "2d" else "3D窗口"
        return f"{label} {number}"
