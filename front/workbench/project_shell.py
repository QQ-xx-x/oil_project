# -*- coding: utf-8 -*-
"""工程打开后的主界面，包含左侧切换面板和中央工作窗口。"""

import os

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QMenu, QSplitter, QTabWidget, QToolButton,
    QVBoxLayout, QWidget,
)

from .chart_adapters import build_gas_pvt_curve_data, build_relative_permeability_data
from .icon_registry import semantic_icon_kind
from .icons import painted_icon
from .input_tree import InputTree
from .message_log import MessageLogPanel
from .navigation_trees import (
    CasesTree, ModelsTree, ProcessesTree, TemplatesTree, WindowsTree,
)
from .project_state import ProjectState
from .results_tree import ResultsTree
from .simulation_service import WorkbenchSimulationService
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
            "输入": "case_root",
            "算例": "case",
            "模板": "folder",
            "流程": "process",
            "模型": "grid",
            "窗口": "window",
            "结果": "result",
        }
        return painted_icon(semantic_icon_kind(icon_map.get(title, "generic"), title), 16)

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
        self.project_state = project_state or ProjectState(project_name=project_name)
        self.project_root = project_root or os.getcwd()
        self.workflow_runner = WorkbenchWorkflowRunner(self.project_root)
        self.result_store = self.workflow_runner.discover_results()
        self.simulation_service = WorkbenchSimulationService(self.project_root, self)
        self._last_simulation_params = {}
        self.setObjectName("projectShell")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.input_tree = InputTree(self.project_state)
        self.input_tree.module_selected.connect(self._handle_module_selected)
        self.input_tree.module_checked.connect(self._handle_module_checked)
        self.input_tree.parameters_saved.connect(self._handle_parameters_saved)
        self.input_tree.case_dataset_built.connect(self._handle_case_dataset_built)

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
        self.simulation_service.started.connect(self._handle_simulation_started)
        self.simulation_service.log_message.connect(self.message_log.append_message)
        self.simulation_service.finished.connect(self._handle_simulation_finished)
        self.simulation_service.failed.connect(self._handle_simulation_failed)
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
        self.workspace.workspace_message.connect(self._handle_workspace_message)
        main_splitter = QSplitter(Qt.Horizontal)
        main_splitter.addWidget(left_container)
        main_splitter.addWidget(self.workspace)
        main_splitter.setSizes([450, 1350])
        main_splitter.setCollapsible(0, False)
        layout.addWidget(main_splitter)

    def _handle_workspace_message(self, message):
        self.message_log.append_message(message)
        self._show_status(message.replace("[窗口] ", ""))

    def activate_module(self, module_key):
        routes = {
            "reservoir_model": ("input", "grid_basic"),
            "grid_import": ("input", "grid_basic"),
            "fracture_modeling": ("input", "natural_fractures"),
            "well_engineering": ("input", "well_parameters"),
            "fluid_pvt": ("input", "gas_pvt"),
            "simulation": ("input", "simulation_control"),
            "results_visualization": ("result", "pressure_field"),
            "relative_perm": ("result", "relative_permeability_curve"),
            "reservoir_analysis": ("result", "production_curve"),
            "project_management": ("input", "grid_foundation"),
        }
        route = routes.get(module_key)
        if route is None:
            self.message_log.append_message(f"[启动] 模块 {module_key} 暂未接入。")
            return

        area, key = route
        if area == "input":
            index = self.upper_tabs.tab_widget.indexOf(self.input_tree)
            if index >= 0:
                self.upper_tabs.tab_widget.setCurrentIndex(index)
            self.input_tree.select_key(key)
        elif area == "result":
            index = self.lower_tabs.tab_widget.indexOf(self.results_tree)
            if index >= 0:
                self.lower_tabs.tab_widget.setCurrentIndex(index)
            self.results_tree.select_key(key)

        title = self._module_title(module_key)
        self.message_log.append_message(f"[启动] 已进入模块：{title}")
        self._show_status(f"当前模块：{title}")

    def _module_title(self, module_key):
        titles = {
            "reservoir_model": "储层建模",
            "grid_import": "网格导入",
            "fracture_modeling": "裂缝建模",
            "well_engineering": "井工程",
            "fluid_pvt": "流体与 PVT",
            "simulation": "数值模拟",
            "results_visualization": "结果可视化",
            "relative_perm": "相渗设计",
            "reservoir_analysis": "储层分析",
            "project_management": "工程管理",
        }
        return titles.get(module_key, module_key)

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

    def _handle_case_dataset_built(self, dataset_path, manifest):
        validation = manifest.get("validation", {}) if isinstance(manifest, dict) else {}
        array_count = len(manifest.get("arrays", {}) or {}) if isinstance(manifest, dict) else 0
        source_file_count = len(manifest.get("source_files", []) or []) if isinstance(manifest, dict) else 0
        error_count = validation.get("error_count")
        warning_count = validation.get("warning_count")
        if error_count is None:
            error_count = len(validation.get("errors", []) or [])
        if warning_count is None:
            warning_count = len(validation.get("warnings", []) or [])
        self.message_log.append_message(f"[CaseData] Dataset 已生成：{dataset_path}")
        self.message_log.append_message(
            f"[CaseData] Dataset 校验：数组 {array_count} 个，文件 {source_file_count} 个，"
            f"错误 {error_count} 个，警告 {warning_count} 个")
        self._show_status("CaseData Dataset 已生成")

    def _handle_result_selected(self, key, title, view):
        if key == "layer_control":
            self.workspace.update_context(*self._result_context(key, title), "3d", key)
            self.message_log.append_message("[结果] 已激活图层控制")
            self._show_status("当前查看结果图层控制")
            return
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
        self.message_log.append_message("[运行] 正在收集 Corner Grid LGR 输入参数")
        self.simulation_service.run(self.project_state)

    def _handle_simulation_started(self, params):
        self._last_simulation_params = dict(params)
        self.result_store.run_status = "running"
        self.message_log.append_message(
            f"[运行] 算法=corner_edfm，加密={params.get('corner_grid_refinement')}")
        self.message_log.append_message(
            f"[运行] COORD={os.path.basename(params.get('coord_file', ''))}, "
            f"ZCORN={os.path.basename(params.get('zcorn_file', ''))}")
        self.message_log.append_message(
            f"[运行] HF count={params.get('hf_count')}, "
            f"center=({params.get('hf_center_x')}, {params.get('hf_center_y')}, {params.get('hf_center_z')})")
        self._show_status("Corner Grid LGR 模拟运行中")

    def _handle_simulation_finished(self, sim_data, result_path):
        self._augment_corner_visual_layers(sim_data)
        self.result_store.run_status = "done"
        self.result_store.simulation_data = sim_data
        self.result_store.result_json_path = result_path
        self.workspace.set_simulation_data(sim_data)
        self.workspace.update_context(
            "当前结果：Corner Grid 压力场",
            "三维窗口显示导入角点网格的 LGR 加密模拟结果。",
            "3d",
            "pressure_field",
        )
        self._publish_loaded_charts()
        self._log_simulation_summary(sim_data)
        self.message_log.append_message(f"[结果] 已加载模拟结果 JSON：{result_path}")
        self._show_status("Corner Grid LGR 模拟完成")

    def _handle_simulation_failed(self, message):
        self.result_store.run_status = "failed"
        self.message_log.append_message(f"[运行] {message}")
        self._show_status("Corner Grid LGR 模拟失败")

    def _publish_loaded_charts(self):
        for key in ["production_curve", "pvt_curve"]:
            data = self.result_store.chart_data(key)
            if data:
                self.workspace.set_chart_data(key, data)

    def _augment_corner_visual_layers(self, sim_data):
        params = self._last_simulation_params or {}
        fractures = getattr(sim_data, "fractures", []) or []
        self._apply_corner_origin_offset(sim_data, fractures)
        natural_count = int(params.get("num_fracs", 0) or 0)
        region_count = int(params.get("region_num_fracs", 0) or 0)
        hydraulic_count = int(params.get("hf_count", 0) or 0)
        region_start = natural_count
        hydraulic_start = natural_count + region_count
        hydraulic_end = hydraulic_start + hydraulic_count
        hydraulic_centers = []

        for index, frac in enumerate(fractures):
            try:
                frac_id = int(frac.get("id", index))
            except (TypeError, ValueError):
                frac_id = index

            is_region = region_start <= frac_id < hydraulic_start
            is_hydraulic = hydraulic_start <= frac_id < hydraulic_end
            if is_hydraulic:
                frac["type"] = "hydraulic"
                frac["is_hydraulic"] = 1
                points = frac.get("points", []) or []
                if points:
                    hydraulic_centers.append(tuple(
                        sum(float(point[axis]) for point in points) / len(points)
                        for axis in range(3)
                    ))
            elif is_region:
                frac["type"] = "region"
                frac["is_hydraulic"] = 0
            else:
                frac["type"] = "natural"
                frac["is_hydraulic"] = 0

        if hydraulic_centers and not getattr(sim_data, "wells", None):
            hydraulic_centers.sort(key=lambda point: point[0])
            mid = hydraulic_centers[len(hydraulic_centers) // 2]
            sim_data.wells = [{
                "id": 0,
                "node_idx": 0,
                "type": "Fracture",
                "x": mid[0],
                "y": mid[1],
                "z": mid[2],
                "WI": 0.0,
                "P_bhp": float(params.get("well_pressure", 50.0)),
            }]

    def _apply_corner_origin_offset(self, sim_data, fractures):
        if not fractures:
            return

        bounds = self._corner_grid_bounds(sim_data)
        if bounds is None:
            return
        min_x, max_x, min_y, max_y, min_z, max_z = bounds
        origin = (min_x, min_y, min_z)
        if all(abs(value) < 1e-9 for value in origin):
            return

        margin = max(max_x - min_x, max_y - min_y, max_z - min_z, 1.0) * 1e-6
        for frac in fractures:
            for point in frac.get("points", []) or []:
                x, y, z = (float(point[0]), float(point[1]), float(point[2]))
                if (min_x - margin <= x <= max_x + margin
                        and min_y - margin <= y <= max_y + margin
                        and min_z - margin <= z <= max_z + margin):
                    return

        for frac in fractures:
            shifted = []
            for point in frac.get("points", []) or []:
                shifted.append((
                    float(point[0]) + origin[0],
                    float(point[1]) + origin[1],
                    float(point[2]) + origin[2],
                ))
            frac["points"] = shifted

    def _corner_grid_bounds(self, sim_data):
        cpg = getattr(sim_data, "corner_point_grid", None)
        if cpg is not None and getattr(cpg, "cells", None):
            xs, ys, zs = [], [], []
            for cell in cpg.cells:
                for corner in cell.corners:
                    xs.append(float(corner[0]))
                    ys.append(float(corner[1]))
                    zs.append(float(corner[2]))
            if xs:
                return min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)

        cell_geometry = getattr(sim_data, "cell_geometry_with_pressure", None)
        if cell_geometry is None:
            return None
        xs, ys, zs = [], [], []
        for row in cell_geometry:
            if len(row) < 28:
                continue
            for offset in range(4, 28, 3):
                xs.append(float(row[offset]))
                ys.append(float(row[offset + 1]))
                zs.append(float(row[offset + 2]))
        if not xs:
            return None
        return min(xs), max(xs), min(ys), max(ys), min(zs), max(zs)

    def _log_simulation_summary(self, sim_data):
        pressures = []
        cell_geometry = getattr(sim_data, "cell_geometry_with_pressure", None)
        if cell_geometry is not None:
            for row in cell_geometry:
                if len(row) > 0:
                    try:
                        pressures.append(float(row[-1]))
                    except (TypeError, ValueError):
                        pass
        if not pressures:
            for item in getattr(sim_data, "pressure_field", []) or []:
                if len(item) >= 4:
                    try:
                        pressures.append(float(item[3]))
                    except (TypeError, ValueError):
                        pass

        fractures = len(getattr(sim_data, "fractures", []) or [])
        wells = len(getattr(sim_data, "wells", []) or [])
        if pressures:
            min_p = min(pressures)
            max_p = max(pressures)
            unique_count = len(set(pressures))
            self.message_log.append_message(
                f"[诊断] 压力范围={min_p:.6g} - {max_p:.6g} bar，唯一值数量={unique_count}")
            if unique_count <= 1:
                self.message_log.append_message(
                    "[诊断] 压力场仍为常数，优先检查人工裂缝是否生成、井是否接入。")
        else:
            self.message_log.append_message("[诊断] 未读取到压力数据。")
        self.message_log.append_message(f"[诊断] 裂缝数量={fractures}，井数量={wells}")

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
