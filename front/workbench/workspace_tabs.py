# -*- coding: utf-8 -*-
"""工程打开后使用的中央多窗口工作区。"""

from PyQt5.QtCore import QSize, Qt, pyqtSignal
from PyQt5.QtWidgets import QAction, QMenu, QTabWidget, QToolButton

from .icon_registry import semantic_icon_kind
from .history_matching_panel import HistoryMatchingViewport
from .icons import painted_icon
from .production_curve_panel import ProductionCurveViewport
from .viewport_placeholders import ChartViewport, ThreeDViewport, TwoDViewport, ViewPage


class WorkspaceTabs(QTabWidget):
    workspace_message = pyqtSignal(str)
    result_property_selected = pyqtSignal(str)

    def __init__(self, parent=None, project_state=None, result_store=None):
        super().__init__(parent)
        self.project_state = project_state
        self.result_store = result_store
        self.setObjectName("workspaceTabs")
        self.setTabsClosable(True)
        self.setMovable(True)
        self.setContextMenuPolicy(Qt.CustomContextMenu)

        self._counters = {"2d": 2, "3d": 1, "chart": 1}
        self._last_context = (
            "当前结果：三维视图",
            "在结果树中选择结果或图层后，这里显示对应占位视图。",
            "pressure_field",
        )
        self._last_simulation_data = None
        self._chart_data_by_key = {}
        self._layer_states = {}

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

    def _create_page(self, view_type, display_key=None):
        if view_type == "chart" and display_key == "production_curve":
            viewport = ProductionCurveViewport(self.project_state, self.result_store)
        elif view_type == "chart" and display_key == "history_matching":
            viewport = HistoryMatchingViewport(self.project_state, self.result_store)
        else:
            viewport = {
                "2d": TwoDViewport,
                "3d": ThreeDViewport,
                "chart": ChartViewport,
            }[view_type]()
        page = ViewPage(viewport, view_type)
        page.view_message.connect(self.workspace_message.emit)
        page.result_property_selected.connect(self.result_property_selected.emit)
        page.new_window_requested.connect(lambda: self._show_new_menu_from_page(page))
        page.clone_window_requested.connect(lambda: self.clone_window(self.indexOf(page)))
        page.close_window_requested.connect(lambda: self.close_window(self.indexOf(page)))
        return page

    def _add_page(self, page, view_type, title):
        icon_map = {"2d": "window", "3d": "grid", "chart": "chart"}
        icon_kind = semantic_icon_kind(icon_map[view_type], title)
        page.setProperty("viewType", view_type)
        index = self.addTab(page, painted_icon(icon_kind, 16), title)
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
        display_key = None
        source_viewport = getattr(source, "viewport", None)
        if view_type == "chart":
            display_key = getattr(source_viewport, "display_key", None)
        page = self._create_page(view_type, display_key)
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
        target = self._target_page_for_context(preferred_view, display_key)
        if preferred_view == "chart" and display_key in {"production_curve", "history_matching"} and target is not None:
            pages = [target]
        else:
            pages = self._pages_of_type(preferred_view) if target is not None else self._pages()
        for page in pages:
            page.set_context(title, detail, display_key)
        if target is not None:
            self.setCurrentWidget(target)

    def set_layer_state(self, layer_key, enabled):
        self._layer_states[layer_key] = bool(enabled)
        for page in self._pages_of_type("3d"):
            page.set_layer_state(layer_key, enabled)

    def set_simulation_data(self, sim_data):
        self._last_simulation_data = sim_data
        for page in self._pages_of_type("3d"):
            page.set_simulation_data(sim_data)

    def set_chart_data(self, chart_key, data):
        self._chart_data_by_key[chart_key] = data
        for page in self._pages_of_type("chart"):
            page.set_chart_data(chart_key, data)

    def set_project_context(self, project_state=None, result_store=None):
        if project_state is not None:
            self.project_state = project_state
        if result_store is not None:
            self.result_store = result_store
        for page in self._pages_of_type("chart"):
            viewport = getattr(page, "viewport", None)
            if hasattr(viewport, "set_project_context"):
                viewport.set_project_context(self.project_state, self.result_store)

    def export_ui_state(self):
        pages = []
        for index in range(self.count()):
            page = self.widget(index)
            page_state = {}
            if hasattr(page, "export_ui_state"):
                page_state = page.export_ui_state()
            pages.append({
                "title": self.tabText(index),
                "view_type": self._page_view_type(page),
                "state": page_state,
            })
        return {
            "current_index": self.currentIndex(),
            "last_context": list(self._last_context),
            "layer_states": dict(self._layer_states),
            "pages": pages,
        }

    def restore_ui_state(self, state):
        if not isinstance(state, dict):
            return
        pages = state.get("pages")
        if not isinstance(pages, list) or not pages:
            return
        normalized_pages = [
            page_info for page_info in pages
            if isinstance(page_info, dict)
            and page_info.get("view_type") in {"2d", "3d", "chart"}
        ]
        if not normalized_pages:
            return

        self._layer_states = dict(state.get("layer_states") or {})
        last_context = state.get("last_context")
        if isinstance(last_context, (list, tuple)) and len(last_context) >= 3:
            self._last_context = (last_context[0], last_context[1], last_context[2])

        while self.count():
            page = self.widget(0)
            self.removeTab(0)
            page.deleteLater()

        for page_info in normalized_pages:
            view_type = page_info.get("view_type")
            title = page_info.get("title") or self._title_for(view_type, self._counters.get(view_type, 0) + 1)
            display_key = None
            state_payload = page_info.get("state") or {}
            if view_type == "chart":
                viewport_state = state_payload.get("viewport") or {}
                display_key = viewport_state.get("display_key")
            page = self._create_page(view_type, display_key)
            if hasattr(page, "restore_ui_state"):
                page.restore_ui_state(page_info.get("state") or {})
            self._add_page(page, view_type, title)

        self._rebuild_counters_from_tabs()
        current_index = state.get("current_index", 0)
        try:
            current_index = int(current_index)
        except (TypeError, ValueError):
            current_index = 0
        if 0 <= current_index < self.count():
            self.setCurrentIndex(current_index)
        self._refresh_primary_references()

    def _apply_last_context(self, page):
        title, detail, display_key = self._last_context
        page.set_context(title, detail, display_key)
        view_type = self._page_view_type(page)
        if view_type == "3d":
            if self._last_simulation_data is not None:
                page.set_simulation_data(self._last_simulation_data)
            for layer_key, enabled in self._layer_states.items():
                page.set_layer_state(layer_key, enabled)
        elif view_type == "chart":
            for chart_key, data in self._chart_data_by_key.items():
                page.set_chart_data(chart_key, data)

    def _copy_page_context(self, source, target):
        viewport = getattr(source, "viewport", None)
        title = getattr(viewport, "context_title", self._last_context[0])
        detail = getattr(viewport, "context_detail", self._last_context[1])
        display_key = getattr(viewport, "display_key", self._last_context[2])
        target.set_context(title, detail, display_key)
        view_type = self._page_view_type(target)
        if view_type == "3d":
            sim_data = getattr(viewport, "simulation_data", None) or self._last_simulation_data
            if sim_data is not None:
                target.set_simulation_data(sim_data)
            source_layers = getattr(viewport, "layers", None)
            layer_states = dict(source_layers or self._layer_states)
            for layer_key, enabled in layer_states.items():
                target.set_layer_state(layer_key, enabled)
        elif view_type == "chart":
            chart_key = getattr(viewport, "display_key", None)
            if chart_key in self._chart_data_by_key:
                target.set_chart_data(chart_key, self._chart_data_by_key[chart_key])
            else:
                for key, data in self._chart_data_by_key.items():
                    target.set_chart_data(key, data)

    def _target_page_for_context(self, preferred_view, display_key):
        if preferred_view != "chart" or display_key not in {"production_curve", "history_matching"}:
            return self._first_page_of_type(preferred_view)
        page = self._first_special_chart_page(display_key)
        if page is not None:
            return page
        page = self._create_page("chart", display_key)
        title = "历史拟合" if display_key == "history_matching" else "生产曲线"
        index = self._add_page(page, "chart", "生产曲线")
        self.setTabText(index, title)
        self._refresh_primary_references()
        self.workspace_message.emit(f"[窗口] 已新建{title}窗口")
        return self.widget(index)

    def _first_special_chart_page(self, display_key):
        viewport_type = {
            "production_curve": ProductionCurveViewport,
            "history_matching": HistoryMatchingViewport,
        }.get(display_key)
        if viewport_type is None:
            return None
        for page in self._pages_of_type("chart"):
            if isinstance(getattr(page, "viewport", None), viewport_type):
                return page
        return None

    def _first_production_curve_page(self):
        return self._first_special_chart_page("production_curve")

    def _first_page_of_type(self, view_type):
        if view_type == "2d":
            view_type = "2d"
        for page in self._pages_of_type(view_type):
            return page
        return None

    def _page_view_type(self, page):
        return getattr(page, "view_type", None) or page.property("viewType")

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

    def _rebuild_counters_from_tabs(self):
        counters = {"2d": 0, "3d": 0, "chart": 0}
        for page in self._pages():
            view_type = self._page_view_type(page)
            if view_type in counters:
                counters[view_type] += 1
        self._counters = counters

    def _title_for(self, view_type, number):
        if view_type == "chart":
            return f"图表窗口 {number}"
        label = "2D窗口" if view_type == "2d" else "3D窗口"
        return f"{label} {number}"
