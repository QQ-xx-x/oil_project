# -*- coding: utf-8 -*-
"""Project-open shell with switchable left panels and central work tabs."""

import os

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QMenu, QSplitter, QTabWidget, QToolButton,
    QVBoxLayout, QWidget,
)

from .chart_adapters import build_gas_pvt_curve_data, build_relative_permeability_data
from .icons import painted_icon
from .input_tree import InputTree
from .message_log import MessageLogPanel
from .navigation_trees import (
    CasesTree, ModelsTree, ProcessesTree, TemplatesTree, WindowsTree,
)
from .results_tree import ResultsTree
from .workspace_tabs import WorkspaceTabs
from .workflow_runner import WorkbenchWorkflowRunner


class DockTabPanel(QFrame):
    panel_message = pyqtSignal(str)

    def __init__(self, tabs, parent=None):
        super().__init__(parent)
        self.setObjectName("dockTabPanel")
        self._pinned = True
        self._collapsed = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.header = QFrame()
        self.header.setObjectName("panelHeader")
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(8, 2, 5, 2)
        self.title = QLabel(tabs[0][0])
        self.title.setObjectName("panelTitle")
        header_layout.addWidget(self.title)
        header_layout.addStretch()
        self.menu_button = self._header_button("▾", "面板菜单")
        self.pin_button = self._header_button("⚑", "固定面板")
        self.close_button = self._header_button("×", "折叠面板")
        header_layout.addWidget(self.menu_button)
        header_layout.addWidget(self.pin_button)
        header_layout.addWidget(self.close_button)
        layout.addWidget(self.header)

        self.tab_widget = QTabWidget()
        self.tab_widget.setObjectName("leftDockTabs")
        self.tab_widget.setTabPosition(QTabWidget.South)
        self.tab_widget.setDocumentMode(True)
        for title, widget in tabs:
            self.tab_widget.addTab(widget, self._tab_icon(title), title)
        self.tab_widget.currentChanged.connect(self._sync_title)
        layout.addWidget(self.tab_widget, 1)

        self._setup_menu()

    def _sync_title(self, index):
        if index >= 0:
            self.title.setText(self.tab_widget.tabText(index))

    def _tab_icon(self, title):
        icon_map = {
            "输入": "folder",
            "算例": "database",
            "模板": "window",
            "流程": "generic",
            "模型": "database",
            "窗口": "window",
            "结果": "import",
        }
        return painted_icon(icon_map.get(title, "generic"), 16)

    def _header_button(self, text, tooltip):
        button = QToolButton()
        button.setObjectName("panelHeaderButton")
        button.setText(text)
        button.setToolTip(tooltip)
        button.setAutoRaise(True)
        return button

    def _setup_menu(self):
        menu = QMenu(self)
        menu.addAction("全部展开", self.expand_current)
        menu.addAction("全部折叠", self.collapse_current)
        menu.addAction("刷新", self.refresh_current)
        menu.addSeparator()
        menu.addAction("重置面板布局", self.reset_panel)
        self.menu_button.setMenu(menu)
        self.menu_button.setPopupMode(QToolButton.InstantPopup)
        self.pin_button.clicked.connect(self.toggle_pin)
        self.close_button.clicked.connect(self.toggle_collapsed)

    def current_panel_name(self):
        return self.tab_widget.tabText(self.tab_widget.currentIndex())

    def current_widget(self):
        return self.tab_widget.currentWidget()

    def expand_current(self):
        widget = self.current_widget()
        if hasattr(widget, "expandAll"):
            widget.expandAll()
        self.panel_message.emit(f"[面板] {self.current_panel_name()} 已全部展开")

    def collapse_current(self):
        widget = self.current_widget()
        if hasattr(widget, "collapseAll"):
            widget.collapseAll()
        self.panel_message.emit(f"[面板] {self.current_panel_name()} 已全部折叠")

    def refresh_current(self):
        self.current_widget().update()
        self.panel_message.emit(f"[面板] {self.current_panel_name()} 已刷新")

    def toggle_pin(self):
        self._pinned = not self._pinned
        self.pin_button.setText("⚑" if self._pinned else "□")
        state = "固定" if self._pinned else "自动隐藏"
        self.panel_message.emit(f"[面板] {self.current_panel_name()} 已切换为{state}")

    def toggle_collapsed(self):
        self.set_collapsed(not self._collapsed)

    def set_collapsed(self, collapsed):
        self._collapsed = bool(collapsed)
        self.tab_widget.setVisible(not self._collapsed)
        self.close_button.setText("▣" if self._collapsed else "×")
        self.close_button.setToolTip("展开面板" if self._collapsed else "折叠面板")
        self.setMaximumHeight(
            self.header.sizeHint().height() + 2 if self._collapsed else 16777215)
        state = "折叠" if self._collapsed else "展开"
        self.panel_message.emit(f"[面板] {self.current_panel_name()} 已{state}")

    def reset_panel(self):
        self._pinned = True
        self.pin_button.setText("⚑")
        self.set_collapsed(False)
        self.tab_widget.setCurrentIndex(0)
        self.panel_message.emit("[面板] 面板布局已重置")


class ProjectShell(QWidget):
    def __init__(self, project_name, project_state=None, project_root=None, parent=None):
        super().__init__(parent)
        self.project_name = project_name
        self.project_state = project_state
        self.project_root = project_root or os.getcwd()
        self.workflow_runner = WorkbenchWorkflowRunner(self.project_root)
        self.result_store = self.workflow_runner.discover_results()
        self.setObjectName("projectShell")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.input_tree = InputTree(self.project_state)
        self.input_tree.module_selected.connect(self._handle_module_selected)
        self.input_tree.module_checked.connect(self._handle_module_checked)
        self.input_tree.parameters_saved.connect(self._handle_parameters_saved)

        self.results_tree = ResultsTree()
        self.results_tree.result_selected.connect(self._handle_result_selected)
        self.results_tree.layer_checked.connect(self._handle_result_layer_checked)

        self.upper_tabs = DockTabPanel([
            ("输入", self.input_tree),
            ("算例", CasesTree()),
            ("模板", TemplatesTree()),
        ])
        self.lower_tabs = DockTabPanel([
            ("流程", ProcessesTree()),
            ("模型", ModelsTree()),
            ("窗口", WindowsTree()),
            ("结果", self.results_tree),
        ])
        self.lower_tabs.tab_widget.setCurrentIndex(3)

        left_splitter = QSplitter(Qt.Vertical)
        self.message_log = MessageLogPanel()
        self.upper_tabs.panel_message.connect(self.message_log.append_message)
        self.lower_tabs.panel_message.connect(self.message_log.append_message)
        self.message_log.append_message(f"[工程] 已打开 {project_name}")
        self._report_discovered_results(prefix="[结果]")
        left_splitter.addWidget(self.upper_tabs)
        left_splitter.addWidget(self.lower_tabs)
        left_splitter.addWidget(self.message_log)
        left_splitter.setSizes([340, 325, 135])
        left_splitter.setCollapsible(0, False)
        left_splitter.setCollapsible(1, False)

        left_container = QFrame()
        left_container.setObjectName("projectLeftDock")
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)
        left_layout.addWidget(left_splitter, 1)
        left_container.setMinimumWidth(380)
        left_container.setMaximumWidth(570)

        self.workspace = WorkspaceTabs()
        main_splitter = QSplitter(Qt.Horizontal)
        main_splitter.addWidget(left_container)
        main_splitter.addWidget(self.workspace)
        main_splitter.setSizes([450, 1350])
        main_splitter.setCollapsible(0, False)
        layout.addWidget(main_splitter)

    def _handle_module_selected(self, key, title):
        self.message_log.append_message(f"[选择] 当前输入模块：{title}")
        self._show_status(f"当前输入模块：{title}")

    def _handle_module_checked(self, key, title, checked):
        state_text = "启用" if checked else "关闭"
        self.message_log.append_message(f"[输入] {title} 已{state_text}")
        self._show_status(f"{title} 已{state_text}")

    def _handle_parameters_saved(self, key, title, values):
        self.message_log.append_message(
            f"[参数] 已更新 {title}：{self._compact_values(values)}")
        self._show_status(f"已更新参数：{title}")

    def _handle_result_selected(self, key, title, view):
        context_title, detail = self._result_context(key, title)
        if view == "chart":
            self._load_chart_data(key, title)
        self.workspace.update_context(context_title, detail, view, key)
        prefix = "图表" if view == "chart" else "结果"
        self.message_log.append_message(f"[{prefix}] 已激活：{title}")
        self._show_status(f"当前查看{prefix}：{title}")

    def _handle_result_layer_checked(self, layer_key, title, checked):
        if not layer_key:
            return
        self.workspace.set_layer_state(layer_key, checked)
        state_text = "显示" if checked else "隐藏"
        self.message_log.append_message(f"[图层] {title} 已{state_text}")
        self._show_status(f"{title} 已{state_text}")

    def _result_context(self, key, title):
        contexts = {
            "pressure_field": (
                "当前结果：压力场",
                "三维窗口显示压力场占位结果，后续接入真实压力数据。"),
            "water_saturation_field": (
                "当前结果：含水饱和度场",
                "三维窗口显示含水饱和度场占位结果。"),
            "permeability_field": (
                "当前结果：渗透率场",
                "三维窗口显示渗透率属性场占位结果。"),
            "porosity_field": (
                "当前结果：孔隙度场",
                "三维窗口显示孔隙度属性场占位结果。"),
            "production_curve": (
                "当前图表：生产曲线",
                "图表窗口显示生产曲线结果或占位曲线。"),
            "relative_permeability_curve": (
                "当前图表：相对渗透率曲线",
                "图表窗口根据当前输入参数显示相对渗透率曲线。"),
            "blasingame_curve": (
                "当前图表：Blasingame 曲线",
                "图表窗口显示 Blasingame 分析曲线占位结果。"),
            "pvt_curve": (
                "当前图表：PVT 表曲线",
                "图表窗口根据当前气相 PVT 参数显示 P-Z 曲线。"),
            "layer_control": (
                "结果图层控制",
                "勾选图层节点可以控制三维窗口里的占位图层显示。"),
        }
        return contexts.get(
            key, (f"当前结果：{title}", "该结果节点后续接入真实模拟输出。"))

    def run_simulation_scan(self):
        self.message_log.append_message("[运行] 正在收集输入参数")
        self.result_store, messages = self.workflow_runner.run_simulation(self.project_state)
        for message in messages:
            self.message_log.append_message(message)
        self._publish_loaded_charts()
        self._show_status("运行模拟扫描完成")

    def _publish_loaded_charts(self):
        for key in ["production_curve", "pvt_curve"]:
            data = self.result_store.chart_data(key)
            if data:
                self.workspace.set_chart_data(key, data)

    def _load_chart_data(self, key, title):
        if key == "relative_permeability_curve":
            try:
                data = build_relative_permeability_data(self.project_state)
            except ValueError as exc:
                self.message_log.append_message(f"[图表] {title} 参数无效：{exc}")
                self._show_status(f"{title} 参数无效")
                return
            self.workspace.set_chart_data(key, data)
            points_count = sum(len(item.get("points", [])) for item in data.get("series", []))
            self.message_log.append_message(
                f"[图表] 已根据当前输入参数生成 {title}：{points_count} 个点")
            return

        if key == "pvt_curve":
            try:
                data = build_gas_pvt_curve_data(self.project_state)
            except ValueError as exc:
                self.message_log.append_message(f"[图表] {title} 参数无效：{exc}")
                data = self.result_store.chart_data(key)
                if not data:
                    self._show_status(f"{title} 参数无效")
                    return
                self.message_log.append_message("[图表] 改用已扫描的 PVT 结果文件")
            self.workspace.set_chart_data(key, data)
            self.message_log.append_message(
                f"[图表] 已加载 {title}：{len(data.get('points', []))} 个点")
            return

        data = self.result_store.chart_data(key)
        if data:
            self.workspace.set_chart_data(key, data)
            self.message_log.append_message(
                f"[图表] 已加载 {title}：{len(data.get('points', []))} 个点")
        elif key in {"production_curve", "pvt_curve"}:
            self.message_log.append_message(
                f"[图表] 未发现 {title} 对应结果文件，显示占位曲线")

    def _report_discovered_results(self, prefix="[结果]"):
        found = []
        if self.result_store.output_sim_path:
            found.append(os.path.basename(self.result_store.output_sim_path))
        if self.result_store.gas_pvt_table_path:
            found.append(os.path.basename(self.result_store.gas_pvt_table_path))
        if self.result_store.final_field_path:
            found.append(os.path.basename(self.result_store.final_field_path))
        if found:
            self.message_log.append_message(f"{prefix} 已识别结果文件：{', '.join(found)}")

    def _compact_values(self, values):
        if not values:
            return "无参数"
        parts = []
        for index, (key, value) in enumerate(values.items()):
            if index >= 4:
                parts.append("...")
                break
            parts.append(f"{key}={value}")
        return ", ".join(parts)

    def _show_status(self, message):
        window = self.window()
        if hasattr(window, "statusBar"):
            window.statusBar().showMessage(message, 4500)
