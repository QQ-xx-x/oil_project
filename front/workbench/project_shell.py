# -*- coding: utf-8 -*-
"""工程打开后的主界面，包含左侧切换面板和中央工作窗口。"""

import os

from PyQt5.QtCore import QObject, Qt, QThread, QTimer, pyqtSignal
from PyQt5.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QMenu, QSplitter, QTabWidget, QToolButton,
    QVBoxLayout, QWidget,
)

from ..data_models import SimulationData
from ..simulation_runner import (
    _corner_point_grid_from_dataset,
    _normalize_parsed_wells_z_to_grid,
)
from .case_manager_panel import CaseManagerPanel
from .case_artifact_repository import CaseArtifactRepository
from .case_models import (
    RUN_STATUS_COMPLETED,
    RUN_TYPE_HISTORY_MATCHING,
    RUN_TYPE_SIMULATION,
    RunRecord,
)
from .case_dataset_reader import CaseDatasetReadError, load_case_dataset
from .chart_adapters import build_gas_pvt_curve_data, build_relative_permeability_data
from .icon_registry import semantic_icon_kind
from .icons import painted_icon
from .input_tree import InputTree
from .message_log import MessageLogPanel
from .model_config_dialog import (
    ensure_model_config_confirmed,
    model_config_summary,
)
from .project_state import ProjectState
from .results_tree import ResultsTree
from .result_catalog import RESULT_AVAILABLE, RunResultCatalog
from .simulation_service import WorkbenchSimulationService
from .simulation_run_manager import (
    SimulationRunContext,
    SimulationRunError,
    SimulationRunManager,
)
from .workspace_tabs import WorkspaceTabs
from .workflow_runner import WorkbenchWorkflowRunner
from visual.pyvista_static_property_preview import (
    attach_static_property_preview_data_from_files,
)
from front.uniform_parser import parse_dfn


LAZY_SIMULATION_DATA_KEYS = {
    "pressure_field",
    "water_saturation_field",
    "porosity_field",
    "permeability_x_field",
    "permeability_y_field",
    "permeability_z_field",
    "permeability_field",  # legacy alias for Kx
}


class SimulationResultLoadWorker(QObject):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, result_path):
        super().__init__()
        self.result_path = result_path

    def run(self):
        try:
            self.progress.emit(15, "准备读取 3D 结果")
            sim_data = SimulationData()
            self.progress.emit(35, "读取 simulation_result.json")
            sim_data.load_json(self.result_path)
            self.progress.emit(75, "3D 结果 JSON 读取完成")
        except Exception as exc:
            self.failed.emit(str(exc))
            return
        self.finished.emit(sim_data)


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
    command_requested = pyqtSignal(str)

    def __init__(self, project_name, project_state=None, project_root=None, parent=None):
        super().__init__(parent)
        self.project_name = project_name
        self.project_state = project_state or ProjectState(project_name=project_name)
        self.project_root = project_root or os.getcwd()
        self.artifact_repository = CaseArtifactRepository(
            self.project_state,
            self.project_root,
        )
        self.project_state.attach_artifact_repository(self.artifact_repository)
        self.simulation_run_manager = SimulationRunManager(
            self.project_state,
            self.artifact_repository,
        )
        self.workflow_runner = WorkbenchWorkflowRunner(self.project_root)
        self.result_store = self.workflow_runner.discover_results()
        self.simulation_service = WorkbenchSimulationService(self.project_root, self)
        self._last_simulation_params = {}
        self._last_simulation_context = {}
        self._preview_data = None
        self._result_load_thread = None
        self._result_load_worker = None
        self._result_load_context = {}
        self._pending_result_load = None
        self._autoload_result_path = ""
        self._bound_case_id = self.project_state.active_case_id or ""
        self.setObjectName("projectShell")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.case_manager = CaseManagerPanel(self.project_state)
        self.case_manager.command_requested.connect(self.command_requested.emit)
        self.case_manager.case_selected.connect(self._handle_case_selected)
        self.case_manager.case_created.connect(self._handle_case_created)
        self.case_manager.cases_changed.connect(self._refresh_case_input_state)

        self.input_tree = InputTree(self.project_state)
        self.input_tree.module_selected.connect(self._handle_module_selected)
        self.input_tree.parameters_saved.connect(self._handle_parameters_saved)
        self.input_tree.case_dataset_built.connect(self._handle_case_dataset_built)
        self.input_tree.result_requested.connect(self._handle_input_related_result_requested)
        self.input_tree.workflow_requested.connect(self._handle_workflow_requested)

        self.results_tree = ResultsTree()
        self.results_tree.bind_case(self.project_state.active_case())
        self.results_tree.run_selected.connect(self._handle_run_selected)
        self.results_tree.run_result_selected.connect(
            self._handle_run_result_selected)
        self.results_tree.analysis_result_selected.connect(
            self._handle_result_selected)

        self.upper_tabs = DockTabPanel([
            ("算例", self.case_manager),
            ("输入", self.input_tree),
        ])
        self.lower_tabs = DockTabPanel([
            ("结果", self.results_tree),
        ])

        left_splitter = QSplitter(Qt.Vertical)
        self.message_log = MessageLogPanel()
        self.upper_tabs.panel_message.connect(self.message_log.append_message)
        self.lower_tabs.panel_message.connect(self.message_log.append_message)
        self.simulation_service.run_started.connect(self._handle_simulation_started)
        self.simulation_service.log_message.connect(self.message_log.append_message)
        self.simulation_service.run_finished.connect(self._handle_simulation_finished)
        self.simulation_service.run_failed.connect(self._handle_simulation_failed)
        self.message_log.append_message(f"[工程] 已打开 {project_name}")
        self._report_discovered_results(prefix="[结果]")
        left_splitter.addWidget(self.upper_tabs)
        left_splitter.addWidget(self.lower_tabs)
        left_splitter.setSizes([430, 430])
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

        self.workspace = WorkspaceTabs(
            project_state=self.project_state,
            result_store=self.result_store,
        )
        self.workspace.workspace_message.connect(self._handle_workspace_message)
        self.workspace.result_property_selected.connect(self._handle_workspace_result_property_selected)
        self.workspace.preview_requested.connect(self._handle_workspace_preview_requested)
        self.workspace.history_run_state_changed.connect(
            self._handle_history_run_state_changed)
        self.workspace.derived_case_created.connect(
            self._handle_history_derived_case_created)
        main_splitter = QSplitter(Qt.Horizontal)
        main_splitter.addWidget(left_container)
        main_splitter.addWidget(self.workspace)
        main_splitter.setSizes([450, 1350])
        main_splitter.setCollapsible(0, False)

        root_splitter = QSplitter(Qt.Vertical)
        root_splitter.setObjectName("projectRootSplitter")
        root_splitter.addWidget(main_splitter)
        root_splitter.addWidget(self.message_log)
        root_splitter.setSizes([820, 150])
        root_splitter.setCollapsible(0, False)
        root_splitter.setCollapsible(1, False)
        layout.addWidget(root_splitter, 1)
        self.restore_ui_state()
        self._refresh_case_input_state(stay_on_case_tab=True)
        self._restore_packaged_simulation_result()

    def _handle_case_selected(self, case_id):
        case = self.project_state.case_by_id(case_id)
        if case is None:
            return
        self._save_bound_case_result_state()
        self._bind_active_case_results(restore=True)
        self._refresh_case_input_state(stay_on_case_tab=True)
        self.message_log.append_message(f"[算例] 当前算例：{case.case_name}")
        self._show_status(f"当前算例：{case.case_name}")

    def _handle_case_created(self, case_id):
        case = self.project_state.case_by_id(case_id)
        self._save_bound_case_result_state()
        self._bind_active_case_results(restore=True)
        self._refresh_case_input_state(stay_on_case_tab=False)
        if case is not None:
            self.message_log.append_message(f"[算例] 已创建气水模拟算例：{case.case_name}")
            self._show_status(f"已创建算例：{case.case_name}")

    def _handle_history_run_state_changed(self, case_id, run_id):
        case = self.project_state.case_by_id(case_id)
        if case is None:
            return
        if case_id == self.project_state.active_case_id:
            self.results_tree.refresh()
            self._sync_result_store_for_active_case()
        self.case_manager.refresh()
        record = case.run_by_id(run_id)
        status = record.status if record is not None else "unknown"
        self.message_log.append_message(
            f"[HistoryMatching] {run_id}: {status}")

    def _handle_history_derived_case_created(self, case_id):
        case = self.project_state.case_by_id(case_id)
        if case is None:
            return
        self._save_bound_case_result_state()
        self._bind_active_case_results(restore=True)
        self._refresh_case_input_state(stay_on_case_tab=True)
        self.message_log.append_message(
            f"[HistoryMatching] Derived case created: {case.case_name}")
        self._show_status(f"Derived case created: {case.case_name}")

    def _refresh_case_input_state(self, *args, stay_on_case_tab=True):
        has_case = bool(self.project_state.has_active_case())
        input_index = self.upper_tabs.tab_widget.indexOf(self.input_tree)
        case_index = self.upper_tabs.tab_widget.indexOf(self.case_manager)
        if input_index >= 0:
            self.upper_tabs.tab_widget.setTabEnabled(input_index, has_case)
        self.input_tree.setEnabled(has_case)
        self.input_tree.refresh_case_data_sections(preserve_expanded=True)
        self.input_tree.refresh_model_config_visibility()
        self.case_manager.refresh()
        self.workspace.set_project_context(
            project_state=self.project_state,
            result_store=self.result_store,
        )
        if stay_on_case_tab and case_index >= 0:
            self.upper_tabs.tab_widget.setCurrentIndex(case_index)
        elif has_case and not stay_on_case_tab and input_index >= 0:
            self.upper_tabs.tab_widget.setCurrentIndex(input_index)

    def _sync_result_store_for_active_case(self):
        self.result_store.clear_run()
        case = self.project_state.active_case()
        record = case.active_run() if case is not None else None
        if record is None:
            return
        self.result_store.case_id = case.case_id
        self.result_store.run_id = record.run_id
        self.result_store.dataset_id = record.dataset_id
        descriptor = RunResultCatalog.from_case(case).by_run_id(record.run_id)
        self.result_store.descriptor = descriptor
        self.result_store.run_status = (
            "done" if record.status == RUN_STATUS_COMPLETED else record.status)
        if record.run_type != RUN_TYPE_SIMULATION:
            self.result_store.load_status = (
                descriptor.availability if descriptor is not None else "unavailable")
            return
        if descriptor is None or descriptor.availability != RESULT_AVAILABLE:
            if descriptor is not None and descriptor.errors:
                self.result_store.load_status = descriptor.availability
                self.result_store.load_error = "; ".join(descriptor.errors)
            return
        artifacts = record.artifacts or {}
        self.result_store.result_json_path = artifacts.get("result_json", "")
        self.result_store.load_status = "indexed"
        run_dir = artifacts.get("run_dir", "")
        if run_dir and os.path.isdir(run_dir):
            restored = WorkbenchWorkflowRunner(run_dir).discover_results()
            self._copy_result_file_state(restored)

    def _save_bound_case_result_state(self):
        if not self._bound_case_id:
            return
        case = self.project_state.case_by_id(self._bound_case_id)
        if case is None:
            return
        case.ui_state["result_view"] = {
            "results_tree": self.results_tree.export_ui_state(),
            "workspace": self.workspace.export_ui_state(),
        }

    def _bind_active_case_results(self, restore=True):
        case = self.project_state.active_case()
        self._bound_case_id = case.case_id if case is not None else ""
        self._preview_data = None
        self.workspace.clear_result_data()
        self.result_store.clear_run()
        self.results_tree.bind_case(case)
        self._sync_result_store_for_active_case()
        record = case.active_run() if case is not None else None
        self.workspace.set_result_context(
            case_id=case.case_id if case is not None else "",
            run_id=record.run_id if record is not None else "",
            dataset_id=record.dataset_id if record is not None else "",
        )
        state = (
            (case.ui_state or {}).get("result_view")
            if case is not None else None
        ) or {}
        if restore and state:
            self.workspace.restore_ui_state(state.get("workspace") or {})
            self.results_tree.restore_ui_state(
                state.get("results_tree") or {})
            self.results_tree.activate_current()
        elif record is not None:
            self.results_tree.select_run(record.run_id, emit=False)

    def _handle_workspace_message(self, message):
        self.message_log.append_message(message)
        self._show_status(message.replace("[窗口] ", ""))

    def _handle_workspace_result_property_selected(self, property_key):
        if property_key not in LAZY_SIMULATION_DATA_KEYS:
            return
        record = self.project_state.active_run_record()
        self.results_tree.select_key(
            property_key,
            run_id=record.run_id if record is not None else None,
        )

    def _handle_workspace_preview_requested(self, page, preview_type, key, axis, layer):
        sim_data = self._ensure_preview_data_loaded()
        if sim_data is None:
            return
        self.workspace.set_preview_data(sim_data)
        if page is not None and hasattr(page, "set_preview_data"):
            page.set_preview_data(sim_data)
        if page is not None and hasattr(page, "handle_preview_request"):
            page.handle_preview_request(preview_type, key, axis, layer)
        else:
            self.message_log.append_message("[预览] 当前 3D 窗口不可用")

    def _handle_input_related_result_requested(self, result_key):
        index = self.lower_tabs.tab_widget.indexOf(self.results_tree)
        if index >= 0:
            self.lower_tabs.tab_widget.setCurrentIndex(index)
        if self.results_tree.select_key(result_key):
            self.message_log.append_message(f"[输入] 已定位关联结果：{result_key}")
            self._show_status(f"已定位关联结果：{result_key}")
        else:
            self.message_log.append_message(f"[输入] 未找到关联结果：{result_key}")
            self._show_status(f"未找到关联结果：{result_key}")

    def _handle_workflow_requested(self, workflow_key, title, view):
        if workflow_key == "history_matching":
            self.workspace.update_context(
                "历史拟合",
                "确认模型和历史数据，设置观测与拟合参数，然后运行历史拟合。",
                view,
                workflow_key,
            )
            self.message_log.append_message("[历史拟合] 已打开历史拟合工作页")
            self._show_status("历史拟合")
            return
        self._handle_result_selected(workflow_key, title, view)

    def collect_ui_state(self):
        """Persist project-level layout and active case result context."""
        self._save_bound_case_result_state()
        """保存工程前收集当前界面状态。"""
        state = dict(getattr(self.project_state, "ui_state", {}) or {})
        state["input_tree"] = self.input_tree.export_ui_state()
        state["results_tree"] = self.results_tree.export_ui_state()
        state["workspace"] = self.workspace.export_ui_state()
        state["upper_tab_index"] = self.upper_tabs.tab_widget.currentIndex()
        state["lower_tab_index"] = self.lower_tabs.tab_widget.currentIndex()
        state["workspace_tab_index"] = self.workspace.currentIndex()
        state.pop("loaded_result_json_path", None)
        state.pop("loaded_results_dir", None)
        self.project_state.ui_state = state
        return state

    def restore_ui_state(self):
        """打开工程后恢复可恢复的界面状态。"""
        state = getattr(self.project_state, "ui_state", {}) or {}
        tree_state = state.get("input_tree") or {}
        if not tree_state and state.get("input_tree_current_key"):
            tree_state = {"current_key": state.get("input_tree_current_key")}
        self.input_tree.restore_ui_state(tree_state)
        case = self.project_state.active_case()
        case_result_state = (
            (case.ui_state or {}).get("result_view")
            if case is not None else None
        ) or {}
        self.results_tree.bind_case(case)
        self._bound_case_id = case.case_id if case is not None else ""
        self.workspace.restore_ui_state(
            case_result_state.get("workspace")
            or state.get("workspace")
            or {}
        )
        self.results_tree.restore_ui_state(
            case_result_state.get("results_tree")
            or state.get("results_tree")
            or {}
        )
        self._sync_result_store_for_active_case()
        record = self.project_state.active_run_record()
        self.workspace.set_result_context(
            case_id=self.project_state.active_case_id,
            run_id=record.run_id if record is not None else "",
            dataset_id=record.dataset_id if record is not None else "",
        )
        self.results_tree.activate_current()
        self._restore_tab_index(self.upper_tabs.tab_widget, state.get("upper_tab_index"))
        self._restore_tab_index(self.lower_tabs.tab_widget, state.get("lower_tab_index"))
        if not state.get("workspace"):
            self._restore_tab_index(self.workspace, state.get("workspace_tab_index"))

    def _has_saved_workspace_state(self):
        state = getattr(self.project_state, "ui_state", {}) or {}
        workspace_state = state.get("workspace") or {}
        case = self.project_state.active_case()
        case_result_state = (
            (case.ui_state or {}).get("result_view")
            if case is not None else None
        ) or {}
        workspace_state = (
            case_result_state.get("workspace") or workspace_state)
        pages = workspace_state.get("pages") if isinstance(workspace_state, dict) else None
        return bool(pages)

    def _restore_packaged_simulation_result(self):
        state = getattr(self.project_state, "ui_state", {}) or {}
        self._migrate_legacy_packaged_result(state)
        active_run = self.project_state.active_run_record()
        if active_run is not None and active_run.run_type != RUN_TYPE_SIMULATION:
            # History matching has its own payload/view loader. Treating its
            # run_result.json as SimulationData corrupts the restore chain.
            self._bind_active_case_results(restore=True)
            return
        run_artifacts = (
            active_run.artifacts
            if active_run is not None and active_run.status == RUN_STATUS_COMPLETED
            else {}
        )
        result_path = (
            run_artifacts.get("result_json")
            or state.get("loaded_result_json_path")
            or ""
        )
        if not result_path:
            self._bind_active_case_results(restore=True)
            return
        if not os.path.exists(result_path):
            self.message_log.append_message(
                f"[结果] 工程包内结果 JSON 不存在：{result_path}")
            return
        self.result_store.run_status = "done"
        self.result_store.case_id = (
            active_run.case_id if active_run is not None else "")
        self.result_store.run_id = (
            active_run.run_id if active_run is not None else "")
        self.result_store.dataset_id = (
            active_run.dataset_id if active_run is not None else "")
        self.result_store.simulation_data = None
        self.result_store.result_json_path = result_path
        self.result_store.load_status = "indexed"
        run_dir = run_artifacts.get("run_dir") or ""
        if run_dir:
            self._restore_packaged_result_files(run_dir)
        else:
            self._restore_packaged_result_files(
                state.get("loaded_results_dir") or "")
        self._publish_loaded_charts()
        self.message_log.append_message(
            f"[结果] 已恢复工程包模拟结果索引，正在自动加载 3D 结果：{result_path}")
        tree_state = (
            ((self.project_state.active_case().ui_state or {}).get("result_view") or {})
            .get("results_tree")
            if self.project_state.active_case() is not None else {}
        ) or state.get("results_tree") or {}
        selected_key = (
            tree_state.get("current_result_key")
            or tree_state.get("current_key")
            or ""
        )
        if selected_key in LAZY_SIMULATION_DATA_KEYS:
            QTimer.singleShot(
                0,
                lambda key=selected_key, run=active_run.run_id:
                self.results_tree.select_key(key, run_id=run),
            )
        else:
            self.message_log.append_message(
                f"[Result] Indexed run={active_run.run_id}; data remains lazy")

    def _migrate_legacy_packaged_result(self, state):
        if self.project_state.active_run_record() is not None:
            return None
        result_path = str(state.get("loaded_result_json_path") or "")
        if not result_path or not os.path.isfile(result_path):
            return None
        case = self.project_state.active_case()
        if case is None:
            return None
        dataset = case.active_dataset()
        results_dir = str(state.get("loaded_results_dir") or "")
        artifacts = {
            "result_json": os.path.abspath(result_path),
            "run_dir": (
                os.path.abspath(results_dir)
                if results_dir and os.path.isdir(results_dir)
                else os.path.dirname(os.path.abspath(result_path))
            ),
        }
        discovered = WorkbenchWorkflowRunner(
            artifacts["run_dir"]).discover_results()
        for key in (
            "output_sim_path",
            "final_field_path",
            "gas_pvt_table_path",
        ):
            path = getattr(discovered, key, "") or ""
            if path:
                artifacts[key] = path
        record = RunRecord(
            case_id=case.case_id,
            dataset_id=dataset.dataset_id if dataset is not None else "",
            dataset_path=dataset.path if dataset is not None else "",
            input_revision=(
                dataset.input_revision
                if dataset is not None else case.input_state.input_revision),
            input_fingerprint=(
                dataset.input_fingerprint
                if dataset is not None else case.input_state.input_fingerprint),
            model_type=case.input_state.model_config.get("model_type", "normal"),
            status=RUN_STATUS_COMPLETED,
            parameters={"interface_source": "legacy_project_result"},
            artifacts=artifacts,
            summary={"migrated_from_legacy_result": True},
        )
        record.mark_completed()
        case.add_run(record, activate=True)
        self.results_tree.bind_case(case)
        self._bound_case_id = case.case_id
        self._sync_result_store_for_active_case()
        self.workspace.set_result_context(
            case_id=case.case_id,
            run_id=record.run_id,
            dataset_id=record.dataset_id,
        )
        self.message_log.append_message(
            f"[Result] Migrated legacy project result to run={record.run_id}")
        return record

    def _start_initial_3d_result_load(self, result_path, run_context=None):
        if not result_path or not os.path.exists(result_path):
            return
        if self.result_store.simulation_data is not None:
            return
        if self._result_load_thread is not None:
            context = run_context or self._active_result_load_context(result_path)
            if context != self._result_load_context:
                self._pending_result_load = (result_path, context)
            return
        context = run_context or self._active_result_load_context(result_path)
        self._autoload_result_path = result_path
        self._result_load_context = dict(context or {})
        self.result_store.load_status = "loading"
        self.result_store.load_error = ""
        self._show_progress("加载 3D 结果", 5, "准备加载工程包结果")
        self.message_log.append_message("[结果] 开始自动加载 3D 模拟结果")

        thread = QThread(self)
        worker = SimulationResultLoadWorker(result_path)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.progress.connect(self._handle_initial_result_load_progress)
        worker.finished.connect(self._handle_initial_result_load_finished)
        worker.failed.connect(self._handle_initial_result_load_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        worker.failed.connect(worker.deleteLater)
        thread.finished.connect(self._cleanup_initial_result_load_thread)

        self._result_load_thread = thread
        self._result_load_worker = worker
        thread.start()

    def _handle_initial_result_load_progress(self, percent, detail):
        self._show_progress("加载 3D 结果", percent, detail)
        self._show_status(f"加载 3D 结果：{detail}")

    def _handle_initial_result_load_finished(self, sim_data):
        context = dict(self._result_load_context or {})
        if not self._is_current_result_context(context):
            self.message_log.append_message(
                f"[Result] Discarded stale load callback for run={context.get('run_id', '')}")
            self._finish_progress("Stale result load discarded")
            return
        record = self.project_state.run_record(
            context.get("case_id", ""), context.get("run_id", ""))
        if record is not None:
            record.summary.pop("result_load_error", None)
            record.summary["result_load_status"] = "loaded"
        sim_data.result_context = dict(context)
        self._show_progress("加载 3D 结果", 82, "补齐 Corner Point Grid")
        dataset_path = context.get("dataset_path") or ""
        self._ensure_corner_point_grid_for_slice(sim_data, dataset_path)
        self._attach_parsed_wells_to_sim_data(sim_data, dataset_path)
        self._attach_static_property_preview_data(sim_data, dataset_path)
        self._attach_static_fracture_preview_data(sim_data, dataset_path)
        self._augment_corner_visual_layers(sim_data)
        self._show_progress("加载 3D 结果", 90, "推送到 3D 窗口")
        self.result_store.simulation_data = sim_data
        self.result_store.load_status = "loaded"
        self.result_store.load_error = ""
        self._preview_data = sim_data
        self.workspace.set_simulation_data(sim_data)
        self.workspace.set_preview_data(sim_data)
        if not self._has_saved_workspace_state():
            self.workspace.update_context(
                *self._result_context("pressure_field", "压力场"),
                "3d",
                "pressure_field",
            )
        self._log_simulation_summary(sim_data)
        self.message_log.append_message(
            f"[结果] 已自动加载 3D 模拟结果：{self._autoload_result_path}")
        self._finish_progress("3D 结果加载完成")
        self._show_status("3D 结果加载完成")

    def _handle_initial_result_load_failed(self, message):
        context = dict(self._result_load_context or {})
        record = self.project_state.run_record(
            context.get("case_id", ""), context.get("run_id", ""))
        if record is not None:
            record.summary["result_load_error"] = str(message)
            if record.case_id == self._bound_case_id:
                self.results_tree.refresh()
        if self._is_current_result_context(context):
            self.result_store.load_status = "error"
            self.result_store.load_error = str(message)
        self.message_log.append_message(f"[结果] 自动加载 3D 模拟结果失败：{message}")
        self._fail_progress(f"3D 结果加载失败：{message}")
        self._show_status("3D 结果加载失败")

    def _cleanup_initial_result_load_thread(self):
        thread = self._result_load_thread
        self._result_load_thread = None
        self._result_load_worker = None
        self._result_load_context = {}
        if thread is not None:
            thread.deleteLater()
        pending = self._pending_result_load
        self._pending_result_load = None
        if pending is not None:
            path, context = pending
            QTimer.singleShot(
                0,
                lambda p=path, c=context: self._start_initial_3d_result_load(
                    p, c),
            )

    def _active_result_load_context(self, result_path=""):
        case = self.project_state.active_case()
        record = case.active_run() if case is not None else None
        return {
            "case_id": case.case_id if case is not None else "",
            "run_id": record.run_id if record is not None else "",
            "dataset_id": record.dataset_id if record is not None else "",
            "dataset_path": record.dataset_path if record is not None else "",
            "result_path": result_path or self.result_store.result_json_path,
        }

    def _is_current_result_context(self, context):
        record = self.project_state.active_run_record()
        return bool(
            record is not None
            and context.get("case_id") == self.project_state.active_case_id
            and context.get("run_id") == record.run_id
            and os.path.abspath(context.get("result_path") or "")
            == os.path.abspath(self.result_store.result_json_path or "")
        )

    def _restore_packaged_result_files(self, results_dir):
        if not results_dir or not os.path.isdir(results_dir):
            return
        restored = WorkbenchWorkflowRunner(results_dir).discover_results()
        self._copy_result_file_state(restored)

    def _copy_result_file_state(self, source_store):
        if source_store.output_sim_path:
            self.result_store.output_sim_path = source_store.output_sim_path
            self.result_store.production_data = source_store.production_data
        if source_store.final_field_path:
            self.result_store.final_field_path = source_store.final_field_path
        if source_store.gas_pvt_table_path:
            self.result_store.gas_pvt_table_path = source_store.gas_pvt_table_path
            self.result_store.pvt_data = source_store.pvt_data

    def _refresh_result_file_paths(self, result_root=None):
        result_root = (
            result_root
            or getattr(self.simulation_service, "app_root", self.project_root)
        )
        discovered = WorkbenchWorkflowRunner(result_root).discover_results()
        self._copy_result_file_state(discovered)

    def _restore_tab_index(self, tab_widget, index):
        try:
            index = int(index)
        except (TypeError, ValueError):
            return
        if 0 <= index < tab_widget.count():
            tab_widget.setCurrentIndex(index)

    def log_project_references(self, validation=None):
        """在日志里报告工程引用的数据状态。"""
        case_data_path = getattr(self.project_state, "case_data_path", "")
        dataset_path = getattr(self.project_state, "case_dataset_path", "")
        if case_data_path:
            self.message_log.append_message(f"[工程] CaseData：{case_data_path}")
        else:
            self.message_log.append_message("[工程] 尚未绑定 CaseData 文件")
        if dataset_path:
            summary = getattr(self.project_state, "case_dataset_summary", {}) or {}
            self.message_log.append_message(
                f"[工程] Dataset：{dataset_path} | "
                f"数组 {summary.get('array_count', 0)} 个，"
                f"错误 {summary.get('error_count', 0)} 个，"
                f"警告 {summary.get('warning_count', 0)} 个")
        else:
            self.message_log.append_message("[工程] 尚未绑定 Dataset 目录")
        validation = validation or {}
        for warning in validation.get("warnings", []) or []:
            self.message_log.append_message(f"[工程警告] {warning}")
        for error in validation.get("errors", []) or []:
            self.message_log.append_message(f"[工程错误] {error}")
        self._log_package_checks(validation)

    def _log_package_checks(self, validation):
        checks = (validation or {}).get("package_checks") or {}
        if not checks:
            return
        if checks.get("errors"):
            status = "存在问题"
        elif checks.get("warnings"):
            status = "有警告"
        else:
            status = "通过"
        self.message_log.append_message(f"[工程包] 自检{status}")
        for item in checks.get("info", []) or []:
            self.message_log.append_message(f"[工程包] {item}")
        summary = checks.get("result_summary") or {}
        if summary:
            self._log_package_result_summary(summary)

    def _log_package_result_summary(self, summary):
        result_files = summary.get("result_files") or {}
        self.message_log.append_message(
            "[工程包] 结果摘要："
            f"3D JSON={'有' if summary.get('has_3d_json') else '无'}，"
            f"大小={self._format_bytes(summary.get('simulation_result_size_bytes', 0))}，"
            f"压力点={summary.get('pressure_points', 0)}，"
            f"角点单元={summary.get('corner_cell_count', 0)}，"
            f"裂缝={summary.get('fracture_count', 0)}，"
            f"井={summary.get('well_count', 0)}，"
            f"时间步={summary.get('time_step_count', 0)}，"
            f"结果文件={len(result_files)} 个")
        if summary.get("summary_error"):
            self.message_log.append_message(
                f"[工程包警告] 结果摘要读取失败：{summary.get('summary_error')}")

    def _format_bytes(self, value):
        try:
            size = float(value or 0)
        except (TypeError, ValueError):
            size = 0.0
        units = ["B", "KB", "MB", "GB"]
        unit_index = 0
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024.0
            unit_index += 1
        if unit_index == 0:
            return f"{int(size)} {units[unit_index]}"
        return f"{size:.2f} {units[unit_index]}"

    def activate_module(self, module_key):
        routes = {
            "reservoir_model": ("input", "rock_properties"),
            "grid_import": ("input", "input_group:grid_spatial:grid_files"),
            "fracture_modeling": ("input", "fracture_system_inputs"),
            "well_engineering": ("input", "well_production"),
            "fluid_pvt": ("input", "fluid_pvt_inputs"),
            "simulation": ("input", "solver_output"),
            "results_visualization": ("result", "pressure_field"),
            "relative_perm": ("result", "relative_permeability_curve"),
            "reservoir_analysis": ("result", "production_curve"),
            "project_management": ("input", "input_overview"),
        }
        route = routes.get(module_key)
        if route is None:
            self.message_log.append_message(f"[启动] 模块 {module_key} 暂未接入。")
            return

        area, key = route
        if area == "input":
            if not self.project_state.has_active_case():
                index = self.upper_tabs.tab_widget.indexOf(self.case_manager)
                if index >= 0:
                    self.upper_tabs.tab_widget.setCurrentIndex(index)
                self.message_log.append_message("[算例] 请先新建或选择一个算例。")
                self._show_status("请先新建或选择一个算例")
                return
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

    def _handle_parameters_saved(self, key, title, values):
        self.message_log.append_message(
            f"[参数] 已更新 {title}：{self._compact_values(values)}")
        self._show_status(f"已更新参数：{title}")

    def _handle_case_dataset_built(self, dataset_path, manifest):
        self._preview_data = None
        self.workspace.set_preview_data(None)
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

    def _ensure_preview_data_loaded(self):
        sim_data = self.result_store.simulation_data
        if sim_data is None:
            dataset_path = getattr(self.project_state, "case_dataset_path", "") or ""
            if not dataset_path or not os.path.isdir(dataset_path):
                self.message_log.append_message(
                    "[预览] 请先构建 CaseDataset 后再预览输入数据。")
                self._show_status("预览数据不可用")
                return None
            if self._preview_data is None:
                self._preview_data = SimulationData()
            sim_data = self._preview_data

        record = self.project_state.active_run_record()
        dataset_path = (
            record.dataset_path
            if record is not None and record.dataset_path
            else getattr(self.project_state, "case_dataset_path", "") or ""
        )
        self._ensure_corner_point_grid_for_slice(sim_data, dataset_path)
        self._attach_parsed_wells_to_sim_data(sim_data, dataset_path)
        self._attach_static_property_preview_data(sim_data, dataset_path)
        self._attach_static_fracture_preview_data(sim_data, dataset_path)
        self._augment_corner_visual_layers(sim_data)
        sim_data.result_context = self._active_result_load_context()

        if not self._has_any_preview_payload(sim_data):
            self.message_log.append_message(
                "[预览] 当前没有可用预览数据，请检查 CaseDataset 中的网格、属性、井或裂缝文件。")
            self._show_status("预览数据不可用")
            return None
        return sim_data

    def _has_any_preview_payload(self, sim_data):
        if getattr(sim_data, "static_grid_data", None) is not None:
            return True
        if getattr(sim_data, "static_properties", None):
            return True
        parsed_well_data = getattr(sim_data, "parsed_well_data", None)
        if isinstance(parsed_well_data, dict) and parsed_well_data.get("wells"):
            return True
        dfn_data = getattr(sim_data, "static_dfn_data", None)
        if isinstance(dfn_data, dict) and dfn_data.get("fractures"):
            return True
        return False

    def show_model_config_dialog(self, force=True):
        if not ensure_model_config_confirmed(self.project_state, self, force=force):
            self.message_log.append_message("[模型方案] 已取消模型方案选择")
            self._show_status("已取消模型方案选择")
            return False
        self.input_tree.refresh_model_config_visibility()
        summary = model_config_summary(getattr(self.project_state, "model_config", {}))
        self.message_log.append_message(f"[模型方案] {summary}")
        self._show_status(f"模型方案：{summary}")
        return True

    def _handle_run_selected(self, run_id):
        if not self.project_state.select_run(run_id):
            self.message_log.append_message(
                f"[Result] Run does not belong to the active case: {run_id}")
            return
        self._preview_data = None
        self.workspace.clear_result_data()
        self._sync_result_store_for_active_case()
        record = self.project_state.active_run_record()
        self.workspace.set_result_context(
            case_id=self.project_state.active_case_id,
            run_id=record.run_id if record is not None else "",
            dataset_id=record.dataset_id if record is not None else "",
        )
        self._save_bound_case_result_state()
        descriptor = self.result_store.descriptor
        if descriptor is not None and descriptor.errors:
            self.message_log.append_message(
                "[Result] " + "; ".join(descriptor.errors))
        self.message_log.append_message(f"[Result] Active run: {run_id}")
        self._show_status(f"Active run: {run_id}")

    def _handle_run_result_selected(self, run_id, key, title, view):
        if self.project_state.active_run_record() is None or (
            self.project_state.active_run_record().run_id != run_id
        ):
            self._handle_run_selected(run_id)
        descriptor = self.results_tree.descriptor(run_id)
        if descriptor is None or descriptor.availability != RESULT_AVAILABLE:
            details = "; ".join(
                descriptor.errors if descriptor is not None else ())
            self.message_log.append_message(
                f"[Result] Run result unavailable: {run_id}"
                + (f"; {details}" if details else ""))
            self._show_status("Run result unavailable")
            return
        record = self.project_state.active_run_record()
        if (
            key == "history_matching"
            and record is not None
            and record.run_type == RUN_TYPE_HISTORY_MATCHING
        ):
            self.workspace.update_context(
                *self._result_context(key, title), view, key)
            self.workspace.load_history_matching_run(record)
            self.message_log.append_message(
                f"[HistoryMatching] Loaded run: {run_id}")
            self._show_status(f"History matching run: {run_id}")
            self._save_bound_case_result_state()
            return
        self._handle_result_selected(key, title, view)
        self._save_bound_case_result_state()

    def _handle_result_selected(self, key, title, view):
        context_title, detail = self._result_context(key, title)
        if view == "chart":
            self._load_chart_data(key, title)
            self.workspace.update_context(context_title, detail, view, key)
        elif view == "3d" and key in LAZY_SIMULATION_DATA_KEYS:
            self.workspace.update_context(context_title, detail, view, key)
            self._ensure_simulation_data_loaded()
        else:
            self.workspace.update_context(context_title, detail, view, key)
        prefix = "图表" if view == "chart" else "结果"
        self.message_log.append_message(f"[{prefix}] 已激活：{title}")
        self._show_status(f"当前查看{prefix}：{title}")

    def _ensure_simulation_data_loaded(self):
        if self.result_store.simulation_data is not None:
            return self.result_store.simulation_data
        if self._result_load_thread is not None:
            result_path = self.result_store.result_json_path or ""
            if result_path:
                self._start_initial_3d_result_load(
                    result_path,
                    self._active_result_load_context(result_path),
                )
            return None
        if self.result_store.simulation_data is not None:
            return self.result_store.simulation_data
        if self._result_load_thread is not None:
            self.message_log.append_message("[结果] 3D 结果正在自动加载，请稍候")
            self._show_status("3D 结果正在自动加载")
            return None
        result_path = self.result_store.result_json_path or ""
        if not result_path:
            return None
        if not os.path.exists(result_path):
            self.message_log.append_message(
                f"[结果] 模拟结果 JSON 不存在：{result_path}")
            return None
        self._start_initial_3d_result_load(
            result_path,
            self._active_result_load_context(result_path),
        )
        return None
        try:
            sim_data = SimulationData()
            sim_data.load_json(result_path)
        except Exception as exc:
            self.message_log.append_message(f"[结果] 按需加载模拟结果失败：{exc}")
            return None
        self._ensure_corner_point_grid_for_slice(sim_data)
        self._attach_parsed_wells_to_sim_data(sim_data)
        self._attach_static_property_preview_data(sim_data)
        self._attach_static_fracture_preview_data(sim_data)
        self._augment_corner_visual_layers(sim_data)
        self.result_store.simulation_data = sim_data
        self.result_store.load_status = "loaded"
        self.result_store.load_error = ""
        self._preview_data = sim_data
        self.workspace.set_simulation_data(sim_data)
        self.workspace.set_preview_data(sim_data)
        self._log_simulation_summary(sim_data)
        self.message_log.append_message(f"[结果] 已按需加载 3D 模拟结果：{result_path}")
        return sim_data

    def _result_context(self, key, title):
        contexts = {
            "pressure_field": (
                "当前结果：压力场",
                "三维窗口显示压力场结果。"),
            "water_saturation_field": (
                "当前结果：含水饱和度场",
                "三维窗口显示含水饱和度场结果。"),
            "porosity_field": (
                "当前结果：孔隙度场",
                "三维窗口显示孔隙度属性场结果。"),
            "permeability_x_field": (
                "当前结果：Kx 渗透率场",
                "三维窗口显示 X 方向渗透率属性场结果。"),
            "permeability_y_field": (
                "当前结果：Ky 渗透率场",
                "三维窗口显示 Y 方向渗透率属性场结果。"),
            "permeability_z_field": (
                "当前结果：Kz 渗透率场",
                "三维窗口显示 Z 方向渗透率属性场结果。"),
            "permeability_field": (
                "当前结果：Kx 渗透率场",
                "三维窗口显示 X 方向渗透率属性场结果。"),
            "production_curve": (
                "当前图表：生产曲线",
                "图表窗口显示生产曲线结果或占位曲线。"),
            "history_matching": (
                "当前结果：历史拟合",
                "图表窗口显示历史拟合参数、运行设置和结果摘要。"),
            "relative_permeability_curve": (
                "当前图表：相对渗透率曲线",
                "图表窗口根据当前输入参数显示相对渗透率曲线。"),
            "blasingame_curve": (
                "当前图表：Blasingame 曲线",
                "图表窗口显示 Blasingame 分析曲线占位结果。"),
            "pvt_curve": (
                "当前图表：PVT 表曲线",
                "图表窗口根据当前气相 PVT 参数显示 P-Z 曲线。"),
        }
        return contexts.get(
            key, (f"当前结果：{title}", "该结果节点后续接入真实模拟输出。"))

    def run_simulation_scan(self):
        if self.simulation_service.is_running():
            self.message_log.append_message(
                "[Run] A simulation is already running in this project")
            self._show_status("Simulation already running")
            return
        if not self.project_state.has_active_case():
            self.message_log.append_message("[算例] 请先新建或选择一个算例后再运行模拟。")
            self._show_status("请先新建或选择一个算例")
            return
        if not ensure_model_config_confirmed(self.project_state, self):
            self.message_log.append_message("[运行] 已取消：尚未确认模型方案")
            self._show_status("已取消运行：尚未确认模型方案")
            return
        self.input_tree.refresh_model_config_visibility()
        self.message_log.append_message(
            f"[模型方案] {model_config_summary(getattr(self.project_state, 'model_config', {}))}")
        self.message_log.append_message("[运行] 正在收集 Corner Grid LGR 输入参数")
        try:
            params = self.simulation_service.build_run_params(
                self.project_state)
            context = self.simulation_run_manager.prepare(params)
        except (ValueError, OSError, SimulationRunError) as exc:
            self.message_log.append_message(
                f"[Run] Failed to prepare simulation: {exc}")
            self._show_status("Simulation preparation failed")
            return
        self._last_simulation_context = context.to_dict()
        started = self.simulation_service.run(
            run_context=context.to_dict(),
            params=params,
        )
        if not started:
            self.simulation_run_manager.mark_failed(
                context,
                "Simulation service rejected the run",
            )

    def _handle_simulation_started(self, params, context):
        self._last_simulation_params = dict(params)
        self._last_simulation_context = dict(context or {})
        try:
            record = self.simulation_run_manager.mark_running(context)
        except SimulationRunError as exc:
            self.message_log.append_message(f"[Run] {exc}")
            return
        if record.case_id == self._bound_case_id:
            self.results_tree.refresh()
        if self.project_state.active_case_id == record.case_id:
            self.result_store.clear_run()
            self.result_store.case_id = record.case_id
            self.result_store.run_id = record.run_id
            self.result_store.dataset_id = record.dataset_id
            self.result_store.run_status = "running"
        self.message_log.append_message(
            f"[Run] case={record.case_id}, dataset={record.dataset_id or '-'}, "
            f"run={record.run_id}")
        self.message_log.append_message(
            f"[运行] 算法=corner_edfm，加密={params.get('corner_grid_refinement')}")
        if params.get("interface_source") == "case_dataset":
            self.message_log.append_message(
                f"[模型方案] type={params.get('model_type', 'normal')}，"
                f"WR={params.get('enable_dual_porosity')}，"
                f"LGR={params.get('enable_lgr')}，"
                f"DFN={params.get('enable_natural_fractures')}，"
                f"HF={params.get('enable_hydraulic_fractures')}，"
                f"PVT={params.get('enable_real_gas_pvt')}")
            self.message_log.append_message(
                f"[运行] Dataset={params.get('case_dataset_path', '')}")
            self.message_log.append_message(
                f"[运行] Grid={params.get('nx')} x {params.get('ny')} x {params.get('nz')}，"
                f"arrays={params.get('array_count')}，properties={params.get('property_count')}，"
                f"DFN={params.get('dfn_fracture_count')}")
            self._show_status("case_dataset 模拟运行中")
            return
        self.message_log.append_message(
            f"[运行] COORD={os.path.basename(params.get('coord_file', ''))}, "
            f"ZCORN={os.path.basename(params.get('zcorn_file', ''))}")
        self.message_log.append_message(
            f"[运行] HF count={params.get('hf_count')}, "
            f"center=({params.get('hf_center_x')}, {params.get('hf_center_y')}, {params.get('hf_center_z')})")
        self._show_status("Corner Grid LGR 模拟运行中")

    def _handle_simulation_finished(self, sim_data, result_path, context):
        run_context = SimulationRunContext.from_value(context)
        sim_data.result_context = run_context.to_dict()
        dataset_path = run_context.dataset_path
        self._ensure_corner_point_grid_for_slice(sim_data, dataset_path)
        self._attach_parsed_wells_to_sim_data(sim_data, dataset_path)
        self._attach_static_property_preview_data(sim_data, dataset_path)
        self._attach_static_fracture_preview_data(sim_data, dataset_path)
        self._augment_corner_visual_layers(sim_data)
        try:
            record = self.simulation_run_manager.mark_completed(
                run_context,
                result_path=result_path,
                exit_code=context.get("exit_code", 0),
                summary=self._simulation_data_summary(sim_data),
            )
        except SimulationRunError as exc:
            self.message_log.append_message(f"[Run] {exc}")
            return
        if record.case_id == self._bound_case_id:
            self.results_tree.refresh()
        if self.project_state.active_case_id != record.case_id:
            self.message_log.append_message(
                f"[Run] Background run completed for case={record.case_id}, "
                f"run={record.run_id}; current case was not changed")
            self._show_status("Background simulation completed")
            return
        self.result_store.run_status = "done"
        self.result_store.case_id = record.case_id
        self.result_store.run_id = record.run_id
        self.result_store.dataset_id = record.dataset_id
        self.result_store.load_status = "loaded"
        self.workspace.set_result_context(
            case_id=record.case_id,
            run_id=record.run_id,
            dataset_id=record.dataset_id,
        )
        self.result_store.simulation_data = sim_data
        self._preview_data = sim_data
        self.result_store.result_json_path = result_path
        self._refresh_result_file_paths(run_context.run_dir)
        self.workspace.set_simulation_data(sim_data)
        self.workspace.set_preview_data(sim_data)
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

        self.results_tree.select_key(
            "pressure_field", run_id=record.run_id)

    @staticmethod
    def _simulation_data_summary(sim_data):
        return {
            "pressure_field_count": len(
                getattr(sim_data, "pressure_field", None) or []),
            "water_saturation_field_count": len(
                getattr(sim_data, "water_saturation_field", None) or []),
            "fracture_count": len(getattr(sim_data, "fractures", None) or []),
        }

    def _ensure_corner_point_grid_for_slice(self, sim_data, dataset_path=None):
        if getattr(sim_data, "corner_point_grid", None) is not None:
            return
        dataset_path = (
            dataset_path
            or getattr(self.project_state, "case_dataset_path", "")
            or ""
        )
        if not dataset_path or not os.path.isdir(dataset_path):
            return
        try:
            dataset = load_case_dataset(dataset_path, strict=False)
            corner_grid = _corner_point_grid_from_dataset(dataset.grid)
        except (CaseDatasetReadError, ValueError, OSError) as exc:
            self.message_log.append_message(f"[切片] 从 Dataset 重建 Corner Point Grid 失败：{exc}")
            return
        if corner_grid is None:
            self.message_log.append_message("[切片] Dataset 网格数据不足，无法重建 Corner Point Grid")
            return
        sim_data.corner_point_grid = corner_grid
        self.message_log.append_message(
            f"[切片] 已从 Dataset 补齐 Corner Point Grid："
            f"{corner_grid.nx} x {corner_grid.ny} x {corner_grid.nz}"
        )

    def _attach_static_property_preview_data(self, sim_data, dataset_path=None):
        """
        给 sim_data 挂静态属性场预览数据。
        """
        if (
            getattr(sim_data, "static_grid_data", None) is not None
            and getattr(sim_data, "static_properties", None) is not None
        ):
            return
        dataset_path = dataset_path or (
            getattr(
                self.project_state,
                "case_dataset_path",
                "",
            )
            or ""
        )
        if not dataset_path or not os.path.isdir(dataset_path):
            self.message_log.append_message(
                "[静态属性预览] 当前没有有效的 CaseDataset 路径，无法加载静态属性。"
            )
            return
        try:
            dataset = load_case_dataset(
                dataset_path,
                strict=False,
            )
        except (
            CaseDatasetReadError,
            ValueError,
            OSError,
        ) as exc:
            self.message_log.append_message(
                f"[静态属性预览] 读取 CaseDataset 失败：{exc}"
            )
            return
        source_files = getattr(
            dataset,
            "source_files",
            None,
        )
        if not isinstance(source_files, dict):
            manifest = getattr(
                dataset,
                "manifest",
                None,
            )
            if isinstance(manifest, dict):
                source_files = manifest.get(
                    "source_files",
                    {},
                )
        if not isinstance(source_files, dict):
            self.message_log.append_message(
                "[静态属性预览] Dataset 中没有 source_files，无法定位属性文件。"
            )
            return

        def get_path(key):
            item = source_files.get(
                key,
                {},
            ) or {}

            if isinstance(item, dict):
                path = item.get(
                    "path",
                    "",
                ) or ""

                if path and os.path.exists(path):
                    return path

                copied_to = item.get(
                    "copied_to",
                    "",
                ) or ""

                if copied_to:
                    copied_path = os.path.join(
                        dataset_path,
                        copied_to,
                    )

                    if os.path.exists(copied_path):
                        return copied_path

                return path

            if isinstance(item, str):
                return item

            return ""

        grid_file = get_path("grid_file")

        property_files = {
            "MATRIX_PORO": get_path("matrix_phi_file"),
            "MATRIX_PERMX": get_path("matrix_kx_file"),
            "MATRIX_PERMY": get_path("matrix_ky_file"),
            "MATRIX_PERMZ": get_path("matrix_kz_file"),

            "DFN_PORO": get_path("fracture_phi_file"),
            "DFN_PERMX": get_path("fracture_kx_file"),
            "DFN_PERMY": get_path("fracture_ky_file"),
            "DFN_PERMZ": get_path("fracture_kz_file"),

            "SIGMA": get_path("sigma_file"),
        }

        if not grid_file:
            self.message_log.append_message(
                "[静态属性预览] 缺少 grid_file，无法构建角点网格预览。"
            )
            return

        try:
            attach_static_property_preview_data_from_files(
                sim_data=sim_data,
                grid_file=grid_file,
                property_files=property_files,
                null_value=99999.0,
                strict=False,
            )

        except Exception as exc:
            self.message_log.append_message(
                f"[静态属性预览] 静态属性数据挂载失败：{exc}"
            )
            return

        static_properties = (
            getattr(
                sim_data,
                "static_properties",
                {},
            )
            or {}
        )

        meta = (
            getattr(
                sim_data,
                "static_property_meta",
                {},
            )
            or {}
        )

        self.message_log.append_message(
            f"[静态属性预览] 已挂载静态属性预览数据："
            f"{len(meta)} 个属性文件，{len(static_properties)} 个属性键。"
        )

    def _attach_static_fracture_preview_data(self, sim_data, dataset_path=None):
        """
        给 sim_data 挂天然裂缝预览数据。
        """
        if getattr(sim_data, "static_dfn_data", None) is not None:
            return

        dataset_path = dataset_path or (
            getattr(
                self.project_state,
                "case_dataset_path",
                "",
            )
            or ""
        )

        if not dataset_path or not os.path.isdir(dataset_path):
            self.message_log.append_message(
                "[裂缝预览] 当前没有有效的 CaseDataset 路径，无法加载天然裂缝。"
            )
            return

        try:
            dataset = load_case_dataset(
                dataset_path,
                strict=False,
            )

        except (
            CaseDatasetReadError,
            ValueError,
            OSError,
        ) as exc:
            self.message_log.append_message(
                f"[裂缝预览] 读取 CaseDataset 失败：{exc}"
            )
            return

        dfn_data = getattr(
            dataset,
            "dfn",
            None,
        )

        if isinstance(dfn_data, dict) and dfn_data.get("fractures"):
            sim_data.static_dfn_data = dfn_data
            self.message_log.append_message(
                f"[裂缝预览] 已从 Dataset 挂载天然裂缝："
                f"{len(dfn_data.get('fractures', []))} 条。"
            )
            return

        source_files = getattr(
            dataset,
            "source_files",
            None,
        )

        if not isinstance(source_files, dict):
            manifest = getattr(
                dataset,
                "manifest",
                None,
            )

            if isinstance(manifest, dict):
                source_files = manifest.get(
                    "source_files",
                    {},
                )

        if not isinstance(source_files, dict):
            self.message_log.append_message(
                "[裂缝预览] Dataset 中没有 source_files，无法定位 dfn.txt。"
            )
            return

        item = source_files.get(
            "fracture_file",
            {},
        ) or {}

        dfn_file = ""

        if isinstance(item, dict):
            dfn_file = item.get(
                "path",
                "",
            ) or ""

            if not dfn_file or not os.path.exists(dfn_file):
                copied_to = item.get(
                    "copied_to",
                    "",
                ) or ""

                if copied_to:
                    copied_path = os.path.join(
                        dataset_path,
                        copied_to,
                    )

                    if os.path.exists(copied_path):
                        dfn_file = copied_path

        elif isinstance(item, str):
            dfn_file = item

        if not dfn_file or not os.path.exists(dfn_file):
            self.message_log.append_message(
                "[裂缝预览] 找不到 dfn.txt，无法加载天然裂缝预览。"
            )
            return

        try:
            dfn_data = parse_dfn(dfn_file)

        except Exception as exc:
            self.message_log.append_message(
                f"[裂缝预览] parse_dfn 失败：{exc}"
            )
            return

        sim_data.static_dfn_data = dfn_data

        self.message_log.append_message(
            f"[裂缝预览] 已解析并挂载天然裂缝："
            f"{len(dfn_data.get('fractures', []))} 条。"
        )

    def _attach_parsed_wells_to_sim_data(self, sim_data, dataset_path=None):
        dataset_path = dataset_path or (
            getattr(
                self.project_state,
                "case_dataset_path",
                "",
            )
            or ""
        )
        if not dataset_path or not os.path.isdir(dataset_path):
            self.message_log.append_message(
                "[井渲染] 当前没有有效的 CaseDataset 路径，无法加载井轨迹。"
            )
            return
        try:
            dataset = load_case_dataset(
                dataset_path,
                strict=False,
            )
        except (
            CaseDatasetReadError,
            ValueError,
            OSError,
        ) as exc:
            self.message_log.append_message(
                f"[井渲染] 读取 CaseDataset 失败：{exc}"
            )
            return
        well_data = getattr(
            dataset,
            "wells",
            None,
        )
        if not isinstance(well_data, dict):
            self.message_log.append_message(
                "[井渲染] 当前 Dataset 中没有解析后的井数据。"
            )
            return
        wells = well_data.get(
            "wells",
            [],
        )
        if not isinstance(wells, list) or not wells:
            self.message_log.append_message(
                "[井渲染] 当前 Dataset 中没有可渲染的井轨迹。"
            )
            return
        well_data = _normalize_parsed_wells_z_to_grid(
            well_data,
            dataset,
        )
        sim_data.parsed_well_data = well_data
        self.message_log.append_message(
            f"[井渲染] 已附加 {len(wells)} 口真实井轨迹到本次模拟结果。"
        )

    def _handle_simulation_failed(self, message, context=None):
        context = dict(context or {})
        record = None
        if context.get("case_id") and context.get("run_id"):
            try:
                record = self.simulation_run_manager.mark_failed(
                    context,
                    message,
                    exit_code=context.get("exit_code"),
                    cancelled=bool(context.get("cancelled")),
                )
            except SimulationRunError as exc:
                self.message_log.append_message(f"[Run] {exc}")
        if record is not None and record.case_id == self._bound_case_id:
            self.results_tree.refresh()
        if (
            record is None
            or self.project_state.active_case_id == record.case_id
        ):
            self.result_store.run_status = (
                "cancelled"
                if record is not None and record.status != "failed"
                else "failed"
            )
        self.message_log.append_message(f"[运行] {message}")
        self._show_status("Corner Grid LGR 模拟失败")

    def stop_simulation(self):
        return self.simulation_service.stop()

    def has_running_operations(self):
        return bool(
            self.simulation_service.is_running()
            or self.workspace.has_running_operations()
        )

    def shutdown(self):
        self.workspace.shutdown_operations(timeout_ms=5000)
        self._pending_result_load = None
        thread = self._result_load_thread
        if thread is not None and thread.isRunning():
            thread.quit()
            if not thread.wait(30000):
                thread.terminate()
                thread.wait(5000)
        context = dict(self.simulation_service.run_context or {})
        if not self.simulation_service.is_running():
            return
        self.simulation_service.stop()
        if context.get("case_id") and context.get("run_id"):
            try:
                self.simulation_run_manager.mark_failed(
                    context,
                    "Project closed while simulation was running",
                    cancelled=True,
                )
            except SimulationRunError:
                pass

    def closeEvent(self, event):
        self.shutdown()
        super().closeEvent(event)

    def _publish_loaded_charts(self):
        for key in ["production_curve", "pvt_curve"]:
            data = self.result_store.chart_data(key)
            if data:
                self.workspace.set_chart_data(key, data)

    def _augment_corner_visual_layers(self, sim_data):
        params = self._last_simulation_params or {}
        fractures = getattr(sim_data, "fractures", []) or []
        self._apply_corner_origin_offset(sim_data, fractures)
        parsed_well_data = getattr(sim_data, "parsed_well_data", None) or {}
        hydraulic_signatures = []

        def _normalize_points(points):
            normalized = []
            for point in points:
                normalized.append((
                    round(float(point[0]), 6),
                    round(float(point[1]), 6),
                    round(float(point[2]), 6),
                ))
            normalized.sort()
            return tuple(normalized)

        for well in parsed_well_data.get("wells", []) or []:
            for completion in well.get("completion_definitions", []) or []:
                if not completion.get("is_fractured", False):
                    continue

                fracture_data = completion.get("fracture")
                if not isinstance(fracture_data, dict):
                    continue

                if not fracture_data.get("geometry_available", False):
                    continue

                corners = fracture_data.get("corners", []) or []
                if len(corners) < 4:
                    continue

                try:
                    csv_points = [
                        (
                            float(corner["x_m"]),
                            float(corner["y_m"]),
                            float(corner["z_m"]),
                        )
                        for corner in corners[:4]
                    ]
                except (KeyError, TypeError, ValueError):
                    continue

                hydraulic_signatures.append(_normalize_points(csv_points))

        hydraulic_centers = []

        for index, frac in enumerate(fractures):
            try:
                frac_id = int(
                    frac.get(
                        "id",
                        frac.get("fracture_id", index),
                    )
                )
            except (TypeError, ValueError):
                frac_id = index

            points = frac.get("points", []) or []

            if len(points) < 4:
                frac["type"] = "natural"
                frac["is_hydraulic"] = 0
                frac["fracture_source"] = "dfn"
                continue

            try:
                final_signature = _normalize_points(points[:4])
            except (TypeError, ValueError, IndexError):
                frac["type"] = "natural"
                frac["is_hydraulic"] = 0
                frac["fracture_source"] = "dfn"
                continue

            is_hydraulic = final_signature in hydraulic_signatures

            if is_hydraulic:
                frac["type"] = "hydraulic"
                frac["is_hydraulic"] = 1
                frac["fracture_source"] = "well_completion_csv"

                if points:
                    hydraulic_centers.append(
                        tuple(
                            sum(float(point[axis]) for point in points) / len(points)
                            for axis in range(3)
                        )
                    )

            else:
                frac["type"] = "natural"
                frac["is_hydraulic"] = 0
                frac["fracture_source"] = "dfn"

    """
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
    """

    def _apply_corner_origin_offset(self, sim_data, fractures):
        if not fractures:
            return

        bounds = self._corner_grid_bounds(sim_data)
        if bounds is None:
            return
        min_x, max_x, min_y, max_y, min_z, max_z = bounds
        dx = max_x - min_x
        dy = max_y - min_y
        dz = max_z - min_z
        margin = max(dx, dy, dz, 1.0) * 1e-6
        local_z_margin = max(1.0, dz * 0.05)

        def in_range(value, lower, upper, tol=margin):
            return lower - tol <= value <= upper + tol

        def map_xy(value, lower, upper):
            if in_range(value, lower, upper):
                return value
            shifted = value + lower
            if in_range(shifted, lower, upper):
                return shifted
            return value

        def map_z(value):
            if in_range(value, min_z, max_z):
                return value
            flipped = -value
            if in_range(flipped, min_z, max_z, local_z_margin):
                return flipped
            shifted = value + min_z
            if -local_z_margin <= value <= dz + local_z_margin and in_range(shifted, min_z, max_z, local_z_margin):
                return shifted
            return value

        changed = 0
        total = 0
        for frac in fractures:
            normalized = []
            for point in frac.get("points", []) or []:
                x, y, z = (float(point[0]), float(point[1]), float(point[2]))
                mapped = (
                    map_xy(x, min_x, max_x),
                    map_xy(y, min_y, max_y),
                    map_z(z),
                )
                normalized.append(mapped)
                total += 1
                if any(abs(mapped[idx] - (x, y, z)[idx]) > margin for idx in range(3)):
                    changed += 1
            frac["points"] = normalized

        if changed:
            self.message_log.append_message(
                f"[裂缝坐标] 已按角点网格范围校正裂缝顶点：{changed}/{total}"
            )

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
                if len(row) > 28:
                    try:
                        pressures.append(float(row[28]))
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
        if key == "history_matching":
            self.message_log.append_message("[历史拟合] 已打开历史拟合工作页")
            return

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

    def _show_progress(self, task, percent=None, detail=""):
        window = self.window()
        if hasattr(window, "show_task_progress"):
            window.show_task_progress(task, percent, detail)

    def _finish_progress(self, message):
        window = self.window()
        if hasattr(window, "finish_task_progress"):
            window.finish_task_progress(message)

    def _fail_progress(self, message):
        window = self.window()
        if hasattr(window, "fail_task_progress"):
            window.fail_task_progress(message)
