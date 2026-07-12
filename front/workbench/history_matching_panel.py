# -*- coding: utf-8 -*-
"""History matching workspace page."""

import copy
import csv
import json
import math
import re
import sys
import time
import zipfile
from datetime import datetime
from pathlib import Path

from PyQt5.QtCore import QProcess, QTimer, QUrl, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QDesktopServices, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QFormLayout, QFrame, QGridLayout,
    QGroupBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QPushButton,
    QMessageBox, QProgressBar,
    QScrollArea, QSpinBox, QTableWidget, QTableWidgetItem, QTabWidget,
    QTextEdit, QVBoxLayout, QWidget,
)


DEFAULT_CONFIG_NAME = "enkf_config.json"

PARAMETER_LABELS = {
    "initial_sw": "初始含水饱和度",
    "well_bhp": "井底流压",
    "hf_perm": "人工裂缝渗透率",
    "frac_perm": "天然裂缝渗透率",
    "wr_shape_factor": "基质-裂缝交换系数",
}

PARAMETER_RECOMMENDED_RANGES = {
    "initial_sw": "0.10 ～ 0.60",
    "well_bhp": "30 ～ 100 bar",
    "hf_perm": "200 ～ 2500 mD",
    "frac_perm": "30 ～ 600 mD",
    "wr_shape_factor": "0.02 ～ 0.25",
}

CHANNEL_LABELS = {
    "gas_rate": "日产气量",
    "gas_cum": "累计产气量",
    "water_rate": "日产水量",
    "water_cum": "累计产水量",
    "bhp": "井底流压",
}

WELL_CONTROL_OPTIONS = [
    ("自由井控", "free"),
    ("固定井底流压", "fixed_bhp"),
    ("固定产气量", "fixed_gas_rate"),
    ("固定产水量", "fixed_water_rate"),
]

TRANSFORM_OPTIONS = [("线性", "linear"), ("对数", "log")]

FIT_QUALITY_THRESHOLDS = {
    "good": 1.0,
    "acceptable": 2.0,
}

from .case_models import RUN_TYPE_HISTORY_MATCHING
from .history_matching_run_manager import (
    HistoryMatchingRunError,
    HistoryMatchingRunManager,
    context_from_record,
)


class HistoryMatchingViewport(QWidget):
    """Workspace viewport for history matching setup and results."""

    run_state_changed = pyqtSignal(str, str)
    derived_case_created = pyqtSignal(str)

    FIT_COLUMNS = [
        "启用", "参数", "参数路径", "初值", "下限", "上限", "变换", "扰动",
        "推荐范围", "校验状态",
    ]
    OBS_COLUMNS = [
        "启用", "观测通道", "历史数据列", "模型输出键", "变换", "最小正值",
        "相对误差", "绝对误差", "权重",
    ]

    def __init__(self, project_state=None, result_store=None, parent=None):
        super().__init__(parent)
        self.project_state = project_state
        self.result_store = result_store
        self.context_title = "历史拟合"
        self.context_detail = "确认模型和历史数据，设置观测与拟合参数，然后运行历史拟合。"
        self.display_key = "history_matching"
        self.project_root = Path(__file__).resolve().parents[2]
        self.history_root = self.project_root / "history_matching"
        self.default_config_path = self.history_root / DEFAULT_CONFIG_NAME
        self.default_config = self._load_default_config()
        self.last_collected_config = None
        self.last_runtime_dir = None
        self.last_runtime_config_path = None
        self.process = None
        self.target_process = None
        self.result_payload = None
        self._stdout_buffer = ""
        self._stderr_buffer = ""
        self._target_stdout_buffer = ""
        self._target_stderr_buffer = ""
        self._stop_requested = False
        self._structured_events_seen = False
        self._run_started_at = None
        self._completed_durations = []
        self._best_objective_value = None
        self._progress_total = 0
        self._progress_completed = 0
        self._progress_timer = QTimer(self)
        self._progress_timer.setInterval(1000)
        self._progress_timer.timeout.connect(self._refresh_runtime_clock)
        self._active_run_context = None
        self._viewing_run_context = None
        self._build_ui()
        self._load_config_to_ui(self.default_config)

    def _load_default_config(self):
        try:
            with self.default_config_path.open("r", encoding="utf-8") as file:
                return json.load(file)
        except (OSError, json.JSONDecodeError):
            return self._fallback_config()

    def _fallback_config(self):
        return {
            "history_file": "history_fit_target.csv",
            "results_dir": "results_ui",
            "runs_dir": "runs_ui",
            "case_dataset_path": "",
            "build_release": "../build/Release",
            "random_seed": 20260521,
            "simulation_days": 730.0,
            "well_control": {"mode": "free"},
            "enkf": {
                "ensemble_size": 24,
                "alphas": [4.0, 4.0, 4.0, 4.0],
                "max_workers": 1,
                "reuse_existing_outputs": True,
                "quiet_member_logs": True,
            },
            "observation": {
                "start_day": 0.0,
                "end_day": 730.0,
                "stride_days": 14.0,
                "channels": [],
            },
            "base_params": {},
            "fit_parameters": [],
        }

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)

        header = QFrame()
        header.setObjectName("modulePreviewPanel")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(14, 12, 14, 12)
        header_layout.setSpacing(5)
        self.title_label = QLabel(self.context_title)
        self.title_label.setObjectName("modulePreviewTitle")
        self.detail_label = QLabel(self.context_detail)
        self.detail_label.setObjectName("modulePreviewDescription")
        self.detail_label.setWordWrap(True)
        header_layout.addWidget(self.title_label)
        header_layout.addWidget(self.detail_label)
        root.addWidget(header)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._scroll_page(self._run_settings_page()), "运行设置")
        self.tabs.addTab(self._scroll_page(self._well_observation_page()), "井控与观测")
        self.tabs.addTab(self._scroll_page(self._fit_parameters_page()), "拟合参数")
        self.tabs.addTab(self._scroll_page(self._run_page()), "运行")
        root.addWidget(self.tabs, 1)

    def _scroll_page(self, page):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(page)
        return scroll

    def _run_settings_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)

        model_group = QGroupBox("当前模型")
        model_group.setObjectName("parameterSection")
        model_layout = QVBoxLayout(model_group)
        self.case_dataset_path_edit = QLineEdit()
        self.case_dataset_path_edit.setObjectName("parameterPathEdit")
        dataset_row = QWidget()
        dataset_layout = QHBoxLayout(dataset_row)
        dataset_layout.setContentsMargins(0, 0, 0, 0)
        dataset_layout.setSpacing(6)
        self.refresh_dataset_button = QPushButton("从工程刷新")
        self.refresh_dataset_button.setObjectName("modulePreviewResultButton")
        self.refresh_dataset_button.clicked.connect(self._refresh_case_dataset_from_project)
        self.choose_dataset_button = QPushButton("选择目录")
        self.choose_dataset_button.setObjectName("modulePreviewResultButton")
        self.choose_dataset_button.clicked.connect(self._select_case_dataset_directory)
        self.case_dataset_path_edit.textChanged.connect(self._update_case_dataset_status)
        dataset_layout.addWidget(self.case_dataset_path_edit, 1)
        dataset_layout.addWidget(self.refresh_dataset_button)
        dataset_layout.addWidget(self.choose_dataset_button)

        self.case_dataset_status_label = QLabel("")
        self.case_dataset_status_label.setObjectName("modulePreviewDescription")
        self.case_dataset_status_label.setWordWrap(True)
        self.model_summary_label = QLabel("等待读取模型摘要。")
        self.model_summary_label.setObjectName("modulePreviewDescription")
        self.model_summary_label.setWordWrap(True)
        model_layout.addWidget(dataset_row)
        model_layout.addWidget(self.case_dataset_status_label)
        model_layout.addWidget(self.model_summary_label)
        layout.addWidget(model_group)

        history_group = QGroupBox("历史数据")
        history_group.setObjectName("parameterSection")
        history_layout = QVBoxLayout(history_group)
        history_row = QWidget()
        history_row_layout = QHBoxLayout(history_row)
        history_row_layout.setContentsMargins(0, 0, 0, 0)
        history_row_layout.setSpacing(6)
        self.history_file_edit = QLineEdit()
        self.history_file_edit.setObjectName("parameterPathEdit")
        self.choose_history_button = QPushButton("选择 CSV")
        self.choose_history_button.setObjectName("modulePreviewResultButton")
        self.choose_history_button.clicked.connect(self._select_history_file)
        self.history_file_edit.textChanged.connect(self._update_history_preview)
        history_row_layout.addWidget(self.history_file_edit, 1)
        history_row_layout.addWidget(self.choose_history_button)
        self.history_status_label = QLabel("尚未选择历史数据。")
        self.history_status_label.setObjectName("modulePreviewDescription")
        self.history_status_label.setWordWrap(True)
        self.history_preview_label = QLabel("选择历史数据后将在这里显示气、水生产曲线预览。")
        self.history_preview_label.setAlignment(Qt.AlignCenter)
        self.history_preview_label.setMinimumHeight(240)
        self.history_preview_label.setObjectName("modulePreviewDescription")
        self.history_preview_label.setWordWrap(True)
        history_layout.addWidget(history_row)
        history_layout.addWidget(self.history_status_label)
        history_layout.addWidget(self.history_preview_label)
        layout.addWidget(history_group)

        group = QGroupBox("算法设置")
        group.setObjectName("parameterSection")
        form = QFormLayout(group)
        form.setLabelAlignment(Qt.AlignRight)
        self.simulation_days_spin = self._double_spin(0.0, 100000.0, 730.0, 2)
        self.ensemble_size_spin = self._spin(2, 10000, 24)
        self.alphas_edit = QLineEdit("4.0, 4.0, 4.0, 4.0")
        self.random_seed_spin = self._spin(0, 2147483647, 20260521)
        self.max_workers_spin = self._spin(1, 256, 1)
        self.max_workers_spin.setValue(1)
        self.max_workers_spin.setEnabled(False)
        self.max_workers_spin.setToolTip("当前历史拟合算法按成员串行执行，并行计算将在后续阶段实现。")
        self.reuse_outputs_check = QCheckBox("复用已有成员计算结果")
        self.quiet_logs_check = QCheckBox("隐藏成员详细日志")

        form.addRow("模拟天数:", self.simulation_days_spin)
        form.addRow("集合规模:", self.ensemble_size_spin)
        form.addRow("ES-MDA 膨胀系数:", self.alphas_edit)
        form.addRow("随机种子:", self.random_seed_spin)
        form.addRow("最大并行数（当前仅串行）:", self.max_workers_spin)
        form.addRow("", self.reuse_outputs_check)
        form.addRow("", self.quiet_logs_check)
        layout.addWidget(group)

        actions = QFrame()
        actions.setObjectName("modulePreviewCard")
        action_layout = QHBoxLayout(actions)
        action_layout.setContentsMargins(10, 8, 10, 8)
        self.collect_button = QPushButton("检查当前参数")
        self.collect_button.setObjectName("modulePreviewResultButton")
        self.collect_button.clicked.connect(self._handle_collect_clicked)
        self.generate_config_button = QPushButton("生成运行配置")
        self.generate_config_button.setObjectName("modulePreviewResultButton")
        self.generate_config_button.clicked.connect(self._handle_generate_config_clicked)
        self.generate_target_button = QPushButton("生成测试目标数据")
        self.generate_target_button.setObjectName("modulePreviewResultButton")
        self.generate_target_button.clicked.connect(self.start_generate_history_target)
        self.status_label = QLabel("已从默认历史拟合模板加载参数。")
        self.status_label.setObjectName("modulePreviewDescription")
        self.status_label.setWordWrap(True)
        action_layout.addWidget(self.collect_button)
        action_layout.addWidget(self.generate_config_button)
        self.generate_target_button.setToolTip("仅用于测试和演示，真实历史拟合通常不需要生成目标数据。")
        action_layout.addWidget(self.generate_target_button)
        action_layout.addWidget(self.status_label, 1)
        layout.addWidget(actions)
        layout.addStretch()
        return page

    def _well_observation_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)

        well_group = QGroupBox("井控设置")
        well_group.setObjectName("parameterSection")
        grid = QGridLayout(well_group)
        grid.setColumnStretch(1, 1)
        self.well_mode_combo = self._coded_combo(WELL_CONTROL_OPTIONS, "free")
        self.well_bhp_spin = self._double_spin(0.0, 100000.0, 42.0, 4)
        self.fixed_rate_spin = self._double_spin(0.0, 1.0e12, 0.0, 4)
        self.rate_column_edit = QLineEdit()
        self.well_mode_combo.currentTextChanged.connect(self._sync_well_control_fields)
        grid.addWidget(QLabel("井控模式:"), 0, 0)
        grid.addWidget(self.well_mode_combo, 0, 1)
        grid.addWidget(QLabel("固定井底流压 (bar):"), 1, 0)
        grid.addWidget(self.well_bhp_spin, 1, 1)
        grid.addWidget(QLabel("固定产量:"), 2, 0)
        grid.addWidget(self.fixed_rate_spin, 2, 1)
        grid.addWidget(QLabel("历史列名:"), 3, 0)
        grid.addWidget(self.rate_column_edit, 3, 1)
        layout.addWidget(well_group)

        obs_group = QGroupBox("观测设置")
        obs_group.setObjectName("parameterSection")
        obs_layout = QVBoxLayout(obs_group)
        timing = QHBoxLayout()
        self.obs_start_spin = self._double_spin(0.0, 1.0e9, 0.0, 3)
        self.obs_end_spin = self._double_spin(0.0, 1.0e9, 730.0, 3)
        self.obs_stride_spin = self._double_spin(1.0e-9, 1.0e9, 14.0, 3)
        timing.addWidget(QLabel("起始天数"))
        timing.addWidget(self.obs_start_spin)
        timing.addWidget(QLabel("结束天数"))
        timing.addWidget(self.obs_end_spin)
        timing.addWidget(QLabel("步长"))
        timing.addWidget(self.obs_stride_spin)
        timing.addStretch()
        obs_layout.addLayout(timing)

        self.observation_table = QTableWidget(0, len(self.OBS_COLUMNS))
        self._setup_table(self.observation_table, self.OBS_COLUMNS)
        obs_layout.addWidget(self.observation_table)
        layout.addWidget(obs_group, 1)
        return page

    def _fit_parameters_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)

        group = QGroupBox("拟合参数")
        group.setObjectName("parameterSection")
        group_layout = QVBoxLayout(group)
        note = QLabel("界面使用中文参数名，运行配置仍保留兼容算法的英文键。固定井底流压模式下，井底流压自动不参与拟合。")
        note.setObjectName("modulePreviewDescription")
        note.setWordWrap(True)
        group_layout.addWidget(note)
        self.fit_table = QTableWidget(0, len(self.FIT_COLUMNS))
        self._setup_table(self.fit_table, self.FIT_COLUMNS)
        self.fit_table.itemChanged.connect(self._on_fit_table_item_changed)
        group_layout.addWidget(self.fit_table)
        layout.addWidget(group, 1)
        return page

    def _run_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(12)

        controls = QFrame()
        controls.setObjectName("modulePreviewCard")
        controls_layout = QHBoxLayout(controls)
        controls_layout.setContentsMargins(10, 8, 10, 8)
        self.run_button = QPushButton("运行历史拟合")
        self.run_button.setObjectName("modulePreviewResultButton")
        self.run_button.clicked.connect(self.start_history_matching)
        self.stop_button = QPushButton("停止运行")
        self.stop_button.setObjectName("modulePreviewResultButton")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_history_matching)
        self.refresh_results_button = QPushButton("刷新结果")
        self.refresh_results_button.setObjectName("modulePreviewResultButton")
        self.refresh_results_button.clicked.connect(self.refresh_result_view)
        self.derive_case_button = QPushButton("最优参数生成派生算例")
        self.derive_case_button.setObjectName("modulePreviewResultButton")
        self.derive_case_button.setEnabled(False)
        self.derive_case_button.clicked.connect(self.create_derived_case_from_best)
        self.export_results_button = QPushButton("导出拟合结果")
        self.export_results_button.setObjectName("modulePreviewResultButton")
        self.export_results_button.setEnabled(False)
        self.export_results_button.clicked.connect(self.export_result_package)
        self.open_results_button = QPushButton("打开结果目录")
        self.open_results_button.setObjectName("modulePreviewResultButton")
        self.open_results_button.setEnabled(False)
        self.open_results_button.clicked.connect(self._open_results_directory)
        controls_layout.addWidget(self.run_button)
        controls_layout.addWidget(self.stop_button)
        controls_layout.addWidget(self.refresh_results_button)
        controls_layout.addWidget(self.derive_case_button)
        controls_layout.addWidget(self.export_results_button)
        controls_layout.addWidget(self.open_results_button)
        controls_layout.addStretch()
        layout.addWidget(controls)

        progress_group = QGroupBox("运行进度")
        progress_group.setObjectName("parameterSection")
        progress_layout = QGridLayout(progress_group)
        progress_layout.setColumnStretch(1, 1)
        progress_layout.setColumnStretch(3, 1)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setTextVisible(True)
        self.round_member_label = QLabel("轮次：- / -，成员：- / -")
        self.completed_runs_label = QLabel("已完成计算：0 / 0")
        self.current_objective_label = QLabel("当前误差：-")
        self.best_objective_label = QLabel("当前全局最优误差：-")
        self.elapsed_time_label = QLabel("已运行：00:00")
        self.remaining_time_label = QLabel("预计剩余：等待首个成员完成")
        self.error_guidance_label = QLabel("")
        self.error_guidance_label.setObjectName("modulePreviewDescription")
        self.error_guidance_label.setWordWrap(True)
        self.error_guidance_label.setStyleSheet(
            "color: #b42318; background: #fff2f0; border: 1px solid #f3b5ad; "
            "padding: 8px; border-radius: 3px;")
        self.error_guidance_label.setVisible(False)
        for label in (
            self.round_member_label, self.completed_runs_label,
            self.current_objective_label, self.best_objective_label,
            self.elapsed_time_label, self.remaining_time_label,
        ):
            label.setObjectName("modulePreviewDescription")
        progress_layout.addWidget(self.round_member_label, 0, 0, 1, 2)
        progress_layout.addWidget(self.completed_runs_label, 0, 2, 1, 2)
        progress_layout.addWidget(self.progress_bar, 1, 0, 1, 4)
        progress_layout.addWidget(self.current_objective_label, 2, 0, 1, 2)
        progress_layout.addWidget(self.best_objective_label, 2, 2, 1, 2)
        progress_layout.addWidget(self.elapsed_time_label, 3, 0, 1, 2)
        progress_layout.addWidget(self.remaining_time_label, 3, 2, 1, 2)
        progress_layout.addWidget(self.error_guidance_label, 4, 0, 1, 4)
        layout.addWidget(progress_group)

        overview = QGroupBox("运行状态与完成摘要")
        overview.setObjectName("parameterSection")
        overview_layout = QGridLayout(overview)
        overview_layout.setColumnStretch(1, 1)
        overview_layout.setColumnStretch(3, 1)
        self.run_state_label = QLabel("未运行")
        self.run_state_label.setObjectName("modulePreviewDescription")
        self.progress_label = QLabel("轮次：-，成员：-，误差：-")
        self.progress_label.setObjectName("modulePreviewDescription")
        self.result_objective_label = QLabel("-")
        self.result_objective_label.setObjectName("modulePreviewDescription")
        self.result_source_label = QLabel("-")
        self.result_source_label.setObjectName("modulePreviewDescription")
        self.result_mode_label = QLabel("-")
        self.result_mode_label.setObjectName("modulePreviewDescription")
        self.fit_quality_label = QLabel("-")
        self.fit_quality_label.setObjectName("modulePreviewDescription")
        self.fit_quality_detail_label = QLabel(
            "评价依据：归一化误差 ≤1 为好，1～2 为一般，>2 为差。")
        self.fit_quality_detail_label.setObjectName("modulePreviewDescription")
        self.fit_quality_detail_label.setWordWrap(True)
        self.results_dir_label = QLabel("结果目录: -")
        self.results_dir_label.setObjectName("modulePreviewDescription")
        self.results_dir_label.setWordWrap(True)
        self.runtime_config_label = QLabel("运行配置: -")
        self.runtime_config_label.setObjectName("modulePreviewDescription")
        self.runtime_config_label.setWordWrap(True)
        overview_layout.addWidget(QLabel("运行状态:"), 0, 0)
        overview_layout.addWidget(self.run_state_label, 0, 1)
        overview_layout.addWidget(QLabel("最终误差:"), 0, 2)
        overview_layout.addWidget(self.result_objective_label, 0, 3)
        overview_layout.addWidget(QLabel("当前进度:"), 1, 0)
        overview_layout.addWidget(self.progress_label, 1, 1)
        overview_layout.addWidget(QLabel("选择来源:"), 1, 2)
        overview_layout.addWidget(self.result_source_label, 1, 3)
        overview_layout.addWidget(QLabel("拟合模式:"), 2, 0)
        overview_layout.addWidget(self.result_mode_label, 2, 1)
        overview_layout.addWidget(QLabel("拟合评价:"), 2, 2)
        overview_layout.addWidget(self.fit_quality_label, 2, 3)
        overview_layout.addWidget(self.fit_quality_detail_label, 3, 0, 1, 4)
        overview_layout.addWidget(self.results_dir_label, 4, 0, 1, 4)
        overview_layout.addWidget(self.runtime_config_label, 5, 0, 1, 4)
        layout.addWidget(overview)

        plot_group = QGroupBox("拟合曲线")
        plot_group.setObjectName("parameterSection")
        plot_layout = QVBoxLayout(plot_group)
        self.result_plot_label = QLabel("等待历史拟合输出曲线图")
        self.result_plot_label.setAlignment(Qt.AlignCenter)
        self.result_plot_label.setMinimumHeight(260)
        self.result_plot_label.setObjectName("modulePreviewDescription")
        self.result_plot_label.setWordWrap(True)
        self.result_plot_path_label = QLabel("图片路径: -")
        self.result_plot_path_label.setObjectName("modulePreviewDescription")
        self.result_plot_path_label.setWordWrap(True)
        plot_layout.addWidget(self.result_plot_label)
        plot_layout.addWidget(self.result_plot_path_label)
        layout.addWidget(plot_group)

        params_group = QGroupBox("最佳拟合参数")
        params_group.setObjectName("parameterSection")
        params_layout = QVBoxLayout(params_group)
        self.best_params_table = QTableWidget(0, 4)
        self._setup_table(self.best_params_table, ["参数", "拟合值", "物理值/显示值", "推荐范围"])
        self.best_params_table.setMinimumHeight(140)
        params_layout.addWidget(self.best_params_table)
        layout.addWidget(params_group)

        files_group = QGroupBox("结果文件")
        files_group.setObjectName("parameterSection")
        files_layout = QVBoxLayout(files_group)
        self.result_files_table = QTableWidget(0, 3)
        self._setup_table(self.result_files_table, ["文件类型", "路径", "状态"])
        self.result_files_table.setMinimumHeight(130)
        files_layout.addWidget(self.result_files_table)
        layout.addWidget(files_group)

        log_group = QGroupBox("运行日志")
        log_group.setObjectName("parameterSection")
        log_layout = QVBoxLayout(log_group)
        self.business_log = QTextEdit()
        self.business_log.setReadOnly(True)
        self.business_log.setMinimumHeight(150)
        self.business_log.setPlaceholderText("运行后将在这里显示关键业务步骤。")
        self.detailed_log_check = QCheckBox("显示详细技术日志")
        self.detailed_log_check.setChecked(False)
        self.run_log = QTextEdit()
        self.run_log.setReadOnly(True)
        self.run_log.setMinimumHeight(220)
        self.run_log.setVisible(False)
        self.detailed_log_check.toggled.connect(self.run_log.setVisible)
        log_layout.addWidget(self.business_log)
        log_layout.addWidget(self.detailed_log_check)
        log_layout.addWidget(self.run_log)
        layout.insertWidget(3, log_group, 1)
        self._reset_progress_view()
        self._reset_result_view()
        return page

    def _setup_table(self, table, headers):
        table.setObjectName("modulePreviewTable")
        table.setHorizontalHeaderLabels(headers)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        table.horizontalHeader().setStretchLastSection(True)
        table.verticalHeader().setVisible(False)

    def _initial_case_dataset_path(self, config=None):
        project_path = self._project_case_dataset_path()
        if project_path:
            return project_path
        if isinstance(config, dict):
            return str(config.get("case_dataset_path", "") or "")
        return ""

    def _project_case_dataset_path(self):
        return str(getattr(self.project_state, "case_dataset_path", "") or "").strip()

    def _refresh_case_dataset_from_project(self):
        project_path = self._project_case_dataset_path()
        if project_path:
            self.case_dataset_path_edit.setText(project_path)
        self._update_case_dataset_status()

    def _select_case_dataset_directory(self):
        current = self.case_dataset_path_edit.text().strip() or self._project_case_dataset_path()
        if current:
            current_path = Path(current).expanduser()
            if not current_path.is_absolute():
                current_path = self._resolve_existing_or_template_path(current)
            current = str(current_path)
        selected = QFileDialog.getExistingDirectory(self, "选择 case_dataset 目录", current)
        if selected:
            self.case_dataset_path_edit.setText(selected)
        self._update_case_dataset_status()

    def _select_history_file(self):
        current = self.history_file_edit.text().strip()
        start_dir = str(self.history_root)
        if current:
            current_path = self._resolve_history_path(current)
            start_dir = str(current_path.parent if current_path.suffix else current_path)
        selected, _ = QFileDialog.getOpenFileName(
            self,
            "选择历史生产数据",
            start_dir,
            "CSV 文件 (*.csv);;所有文件 (*)",
        )
        if selected:
            self.history_file_edit.setText(selected)

    def _update_case_dataset_status(self):
        if not hasattr(self, "case_dataset_status_label"):
            return
        raw_path = self.case_dataset_path_edit.text().strip() if hasattr(self, "case_dataset_path_edit") else ""
        if not raw_path:
            self.case_dataset_status_label.setText("未设置 case_dataset。请先在 CaseData 页面生成 Dataset，或手动选择目录。")
            self.model_summary_label.setText("等待读取模型摘要。")
            return
        path = Path(raw_path).expanduser()
        if not path.is_absolute():
            path = self._resolve_existing_or_template_path(raw_path)
        if not path.exists():
            self.case_dataset_status_label.setText(f"case_dataset 不存在: {path}")
            self.model_summary_label.setText("无法读取模型摘要：目录不存在。")
            return
        if not path.is_dir():
            self.case_dataset_status_label.setText(f"case_dataset 路径不是目录: {path}")
            self.model_summary_label.setText("无法读取模型摘要：所选路径不是目录。")
            return
        manifest = path / "manifest.json"
        if manifest.exists():
            self.case_dataset_status_label.setText(f"case_dataset 已就绪: {path}")
            self._update_model_summary(manifest)
        else:
            self.case_dataset_status_label.setText(f"目录存在，但未发现 manifest.json: {path}")
            self.model_summary_label.setText("无法读取模型摘要：缺少 manifest.json。")

    def _update_model_summary(self, manifest_path):
        try:
            manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            self.model_summary_label.setText(f"模型摘要读取失败：{exc}")
            return

        grid = dict(manifest.get("grid") or {})
        dfn = dict(manifest.get("dfn") or {})
        wells = dict(manifest.get("wells") or {})
        validation = dict(manifest.get("validation") or {})
        case = (
            self.project_state.active_case()
            if self.project_state is not None
            and hasattr(self.project_state, "active_case") else None
        )
        case_name = str(getattr(case, "case_name", "") or "当前活动算例")
        nx, ny, nz = grid.get("nx", "-"), grid.get("ny", "-"), grid.get("nz", "-")
        validation_text = (
            "通过" if validation.get("ok") is True else
            "存在问题" if validation else "未提供"
        )
        self.model_summary_label.setText(
            f"算例：{case_name}\n"
            f"网格维度：{nx} × {ny} × {nz}    "
            f"总网格数：{grid.get('total_cell_count', '-')}    "
            f"活跃/非活跃：{grid.get('active_cell_count', '-')} / "
            f"{grid.get('inactive_cell_count', '-')}\n"
            f"天然裂缝数：{dfn.get('fracture_count', '-')}    "
            f"井数：{wells.get('well_count', '-')}    "
            f"数据校验：{validation_text}"
        )

    def _update_history_preview(self):
        if not hasattr(self, "history_status_label"):
            return
        raw_path = self.history_file_edit.text().strip()
        if not raw_path:
            self.history_status_label.setText("尚未选择历史数据。")
            self.history_preview_label.clear()
            self.history_preview_label.setText("选择历史数据后将在这里显示气、水生产曲线预览。")
            return
        path = self._resolve_history_path(raw_path)
        if not path.is_file():
            self.history_status_label.setText(f"历史数据不存在：{path}")
            self.history_preview_label.clear()
            self.history_preview_label.setText("无法生成预览。")
            return
        try:
            summary = self._read_history_summary(path)
        except (OSError, ValueError) as exc:
            self.history_status_label.setText(f"历史数据检查失败：{exc}")
            self.history_preview_label.clear()
            self.history_preview_label.setText("历史数据格式不正确，无法生成预览。")
            return

        fields = "、".join(summary["fields"])
        self.history_status_label.setText(
            f"已读取 {summary['row_count']} 行，时间范围 "
            f"{summary['start_day']:g} ～ {summary['end_day']:g} 天；"
            f"字段：{fields}"
        )
        pixmap = self._history_preview_pixmap(summary)
        if pixmap is None:
            self.history_preview_label.clear()
            self.history_preview_label.setText("已读取历史数据，但未找到可绘制的气、水产量列。")
        else:
            self.history_preview_label.setPixmap(pixmap)

    def _read_history_summary(self, path, required_columns=None):
        with Path(path).open("r", newline="", encoding="utf-8-sig") as file:
            reader = csv.DictReader(file)
            fields = list(reader.fieldnames or [])
            if not fields:
                raise ValueError("CSV 没有表头")
            if "day" not in fields:
                raise ValueError("缺少时间列 day")
            missing = [name for name in (required_columns or []) if name not in fields]
            if missing:
                raise ValueError(f"缺少观测列：{'、'.join(missing)}")
            rows = list(reader)
        if not rows:
            raise ValueError("CSV 没有数据行")

        try:
            days = [float(row["day"]) for row in rows]
        except (TypeError, ValueError, KeyError):
            raise ValueError("day 列包含非数字内容") from None
        if any(not math.isfinite(value) for value in days):
            raise ValueError("day 列包含无效数值")
        if any(right < left for left, right in zip(days[:-1], days[1:])):
            raise ValueError("day 列必须按时间升序排列")

        series = {}
        for field in fields:
            if field == "day":
                continue
            values = []
            numeric = True
            for row in rows:
                try:
                    value = float(row.get(field, ""))
                except (TypeError, ValueError):
                    numeric = False
                    break
                if not math.isfinite(value):
                    numeric = False
                    break
                values.append(value)
            if numeric:
                series[field] = values
        non_numeric_required = [name for name in (required_columns or []) if name not in series]
        if non_numeric_required:
            raise ValueError(f"观测列包含非数字或空值：{'、'.join(non_numeric_required)}")
        return {
            "path": str(path),
            "fields": fields,
            "row_count": len(rows),
            "start_day": min(days),
            "end_day": max(days),
            "days": days,
            "series": series,
        }

    def _history_preview_pixmap(self, summary):
        series = summary.get("series") or {}
        channels = list((self.default_config.get("observation") or {}).get("channels") or [])
        preferred = []
        for model_key in ("gas_rate", "water_rate"):
            channel = next((item for item in channels if item.get("model_key") == model_key), None)
            column = str((channel or {}).get("column") or "")
            if column in series:
                preferred.append((CHANNEL_LABELS.get(model_key, model_key), column, series[column]))
        if not preferred:
            for field, values in series.items():
                lower = field.lower()
                if "rate" in lower and ("gas" in lower or "water" in lower):
                    preferred.append((field, field, values))
                if len(preferred) == 2:
                    break
        if not preferred:
            return None

        width, height = 900, 250
        pixmap = QPixmap(width, height)
        pixmap.fill(QColor("#ffffff"))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing, True)
        try:
            panel_width = width // len(preferred)
            for index, (label, column, values) in enumerate(preferred):
                self._draw_preview_series(
                    painter,
                    index * panel_width,
                    0,
                    panel_width,
                    height,
                    summary["days"],
                    values,
                    f"{label}（{column}）",
                    QColor("#1f77b4") if index == 0 else QColor("#2ca02c"),
                )
        finally:
            painter.end()
        return pixmap

    @staticmethod
    def _draw_preview_series(painter, x, y, width, height, days, values, title, color):
        left, top, right, bottom = x + 58, y + 34, x + width - 18, y + height - 36
        painter.setPen(QPen(QColor("#666666"), 1))
        painter.drawLine(left, bottom, right, bottom)
        painter.drawLine(left, top, left, bottom)
        painter.drawText(x + 12, y + 22, title)
        if not days or not values:
            return
        x_min, x_max = min(days), max(days)
        y_min, y_max = min(values), max(values)
        x_span = max(x_max - x_min, 1.0)
        y_span = max(y_max - y_min, 1.0e-12)
        painter.setPen(QPen(color, 2))
        previous = None
        step = max(1, len(days) // 500)
        for day, value in zip(days[::step], values[::step]):
            px = left + int((day - x_min) / x_span * (right - left))
            py = bottom - int((value - y_min) / y_span * (bottom - top))
            if previous is not None:
                painter.drawLine(previous[0], previous[1], px, py)
            previous = (px, py)
        painter.setPen(QPen(QColor("#666666"), 1))
        painter.drawText(left, bottom + 20, f"{x_min:g} 天")
        painter.drawText(right - 60, bottom + 20, f"{x_max:g} 天")
        painter.drawText(x + 4, top + 5, f"{y_max:.4g}")
        painter.drawText(x + 4, bottom, f"{y_min:.4g}")

    def _load_config_to_ui(self, config):
        enkf = config.get("enkf") or {}
        observation = config.get("observation") or {}
        well_control = config.get("well_control") or {}

        self.history_file_edit.setText(str(config.get("history_file", "")))
        self.case_dataset_path_edit.setText(self._initial_case_dataset_path(config))
        self._update_case_dataset_status()
        self.simulation_days_spin.setValue(float(config.get("simulation_days", 0.0) or 0.0))
        self.ensemble_size_spin.setValue(int(enkf.get("ensemble_size", 24) or 24))
        self.alphas_edit.setText(", ".join(str(value) for value in enkf.get("alphas", [4.0, 4.0, 4.0, 4.0])))
        self.random_seed_spin.setValue(int(config.get("random_seed", 20260521) or 0))
        self.max_workers_spin.setValue(1)
        self.reuse_outputs_check.setChecked(bool(enkf.get("reuse_existing_outputs", True)))
        self.quiet_logs_check.setChecked(bool(enkf.get("quiet_member_logs", True)))

        self._set_combo_value(self.well_mode_combo, str(well_control.get("mode") or "free"))
        self.well_bhp_spin.setValue(float(well_control.get("bhp", self._base_well_bhp(config))))
        self.fixed_rate_spin.setValue(float(well_control.get("rate", 0.0) or 0.0))
        self.rate_column_edit.setText(str(well_control.get("column") or well_control.get("rate_column") or ""))

        self.obs_start_spin.setValue(float(observation.get("start_day", 0.0) or 0.0))
        self.obs_end_spin.setValue(float(observation.get("end_day", self.simulation_days_spin.value()) or 0.0))
        self.obs_stride_spin.setValue(float(observation.get("stride_days", 1.0) or 1.0))
        self._populate_observation_table(observation.get("channels", []))
        self._populate_fit_table(config.get("fit_parameters", []))
        self._sync_well_control_fields()

    def _base_well_bhp(self, config):
        return ((config.get("base_params") or {}).get("well") or {}).get("bhp", 42.0)

    def _populate_fit_table(self, fit_parameters):
        self.fit_table.setRowCount(0)
        for spec in fit_parameters:
            row = self.fit_table.rowCount()
            self.fit_table.insertRow(row)
            enabled = self._check_item(True)
            self.fit_table.setItem(row, 0, enabled)
            key = str(spec.get("name", ""))
            name_item = QTableWidgetItem(PARAMETER_LABELS.get(key, key))
            name_item.setData(Qt.UserRole, copy.deepcopy(spec))
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self.fit_table.setItem(row, 1, name_item)
            self.fit_table.setItem(row, 2, QTableWidgetItem(".".join(spec.get("path", []))))
            self.fit_table.setItem(row, 3, QTableWidgetItem(self._format_number(spec.get("initial"))))
            self.fit_table.setItem(row, 4, QTableWidgetItem(self._format_number(spec.get("lower"))))
            self.fit_table.setItem(row, 5, QTableWidgetItem(self._format_number(spec.get("upper"))))
            transform_combo = self._coded_combo(
                TRANSFORM_OPTIONS, spec.get("transform", "linear"))
            transform_combo.currentIndexChanged.connect(
                lambda _index, target_row=row: self._refresh_fit_row_status(target_row))
            self.fit_table.setCellWidget(row, 6, transform_combo)
            self.fit_table.setItem(row, 7, QTableWidgetItem(self._format_number(spec.get("perturb", 0.0))))
            recommended = QTableWidgetItem(PARAMETER_RECOMMENDED_RANGES.get(key, "-"))
            recommended.setFlags(recommended.flags() & ~Qt.ItemIsEditable)
            self.fit_table.setItem(row, 8, recommended)
            status = QTableWidgetItem("待检查")
            status.setFlags(status.flags() & ~Qt.ItemIsEditable)
            self.fit_table.setItem(row, 9, status)
        self._update_fit_validation_states()
        self.fit_table.resizeRowsToContents()

    def _populate_observation_table(self, channels):
        self.observation_table.setRowCount(0)
        for channel in channels:
            row = self.observation_table.rowCount()
            self.observation_table.insertRow(row)
            self.observation_table.setItem(row, 0, self._check_item(True))
            key = str(channel.get("name", ""))
            name_item = QTableWidgetItem(CHANNEL_LABELS.get(key, key))
            name_item.setData(Qt.UserRole, copy.deepcopy(channel))
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self.observation_table.setItem(row, 1, name_item)
            self.observation_table.setItem(row, 2, QTableWidgetItem(str(channel.get("column", ""))))
            self.observation_table.setItem(row, 3, QTableWidgetItem(str(channel.get("model_key", ""))))
            self.observation_table.setCellWidget(
                row, 4, self._coded_combo(TRANSFORM_OPTIONS, channel.get("transform", "linear")))
            self.observation_table.setItem(row, 5, QTableWidgetItem(self._format_number(channel.get("epsilon", 0.0))))
            self.observation_table.setItem(row, 6, QTableWidgetItem(self._format_number(channel.get("relative_error", 0.0))))
            self.observation_table.setItem(row, 7, QTableWidgetItem(self._format_number(channel.get("absolute_error", 0.0))))
            self.observation_table.setItem(row, 8, QTableWidgetItem(self._format_number(channel.get("weight", 1.0))))
        self.observation_table.resizeRowsToContents()

    def _sync_well_control_fields(self):
        mode = self._combo_value(self.well_mode_combo)
        self.well_bhp_spin.setEnabled(mode == "fixed_bhp")
        self.fixed_rate_spin.setEnabled(mode in {"fixed_gas_rate", "fixed_water_rate"})
        self.rate_column_edit.setEnabled(mode in {"fixed_gas_rate", "fixed_water_rate"})
        self._sync_well_bhp_fit_row(mode)

    def _sync_well_bhp_fit_row(self, mode):
        for row in range(self.fit_table.rowCount()):
            name_item = self.fit_table.item(row, 1)
            enabled_item = self.fit_table.item(row, 0)
            if name_item is None or enabled_item is None:
                continue
            if self._fit_parameter_key(row) != "well_bhp":
                continue
            if mode == "fixed_bhp":
                enabled_item.setCheckState(Qt.Unchecked)
                enabled_item.setFlags(enabled_item.flags() & ~Qt.ItemIsEnabled)
            else:
                enabled_item.setFlags(enabled_item.flags() | Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)

    def collect_runtime_config(self):
        config = copy.deepcopy(self.default_config)
        active_case = (
            self.project_state.active_case()
            if self.project_state is not None
            and hasattr(self.project_state, "active_case") else None
        )
        if active_case is not None:
            derived_base = (active_case.input_state.module_values or {}).get(
                "history_matching_base_params")
            if isinstance(derived_base, dict) and derived_base:
                config["base_params"] = copy.deepcopy(derived_base)
        config["history_file"] = self.history_file_edit.text().strip()
        config["case_dataset_path"] = self.case_dataset_path_edit.text().strip()
        config["simulation_days"] = float(self.simulation_days_spin.value())
        config["random_seed"] = int(self.random_seed_spin.value())
        config["enkf"] = dict(config.get("enkf") or {})
        config["enkf"]["ensemble_size"] = int(self.ensemble_size_spin.value())
        config["enkf"]["alphas"] = self._parse_alphas()
        config["enkf"]["max_workers"] = int(self.max_workers_spin.value())
        config["enkf"]["reuse_existing_outputs"] = bool(self.reuse_outputs_check.isChecked())
        config["enkf"]["quiet_member_logs"] = bool(self.quiet_logs_check.isChecked())
        config["well_control"] = self._collect_well_control()
        config["observation"] = self._collect_observation()
        config["fit_parameters"] = self._collect_fit_parameters(config["well_control"].get("mode"))
        if "base_params" in config:
            config["base_params"]["simulation_days"] = float(self.simulation_days_spin.value())
        self._validate_runtime_config(config)
        self.last_collected_config = config
        return config

    def _collect_well_control(self):
        mode = self._combo_value(self.well_mode_combo)
        if mode == "free":
            return {"mode": "free"}
        if mode == "fixed_bhp":
            return {"mode": "fixed_bhp", "bhp": float(self.well_bhp_spin.value())}
        payload = {"mode": mode}
        if self.fixed_rate_spin.value() > 0:
            payload["rate"] = float(self.fixed_rate_spin.value())
        column = self.rate_column_edit.text().strip()
        if column:
            payload["column"] = column
        return payload

    def _collect_observation(self):
        channels = []
        for row in range(self.observation_table.rowCount()):
            if not self._row_checked(self.observation_table, row):
                continue
            channel = {
                "name": self._observation_channel_key(row),
                "column": self._table_text(self.observation_table, row, 2),
                "model_key": self._table_text(self.observation_table, row, 3),
                "transform": self._combo_value(self.observation_table.cellWidget(row, 4)),
                "epsilon": self._table_float(self.observation_table, row, 5, 0.0),
                "relative_error": self._table_float(self.observation_table, row, 6, 0.0),
                "absolute_error": self._table_float(self.observation_table, row, 7, 0.0),
                "weight": self._table_float(self.observation_table, row, 8, 1.0),
            }
            channels.append(channel)
        return {
            "start_day": float(self.obs_start_spin.value()),
            "end_day": float(self.obs_end_spin.value()),
            "stride_days": float(self.obs_stride_spin.value()),
            "channels": channels,
        }

    def _collect_fit_parameters(self, well_control_mode):
        parameters = []
        for row in range(self.fit_table.rowCount()):
            name = self._fit_parameter_key(row)
            if well_control_mode == "fixed_bhp" and name == "well_bhp":
                continue
            if not self._row_checked(self.fit_table, row):
                continue
            original = self.fit_table.item(row, 1).data(Qt.UserRole) or {}
            spec = {
                "name": name,
                "path": self._parse_path(self._table_text(self.fit_table, row, 2)),
                "initial": self._table_float(self.fit_table, row, 3, 0.0),
                "lower": self._table_float(self.fit_table, row, 4, 0.0),
                "upper": self._table_float(self.fit_table, row, 5, 0.0),
                "transform": self._combo_value(self.fit_table.cellWidget(row, 6)),
                "perturb": self._table_float(self.fit_table, row, 7, 0.0),
            }
            if original.get("dependent"):
                spec["dependent"] = copy.deepcopy(original["dependent"])
            parameters.append(spec)
        return parameters

    def _fit_parameter_key(self, row):
        item = self.fit_table.item(row, 1)
        original = item.data(Qt.UserRole) if item is not None else None
        if isinstance(original, dict) and original.get("name"):
            return str(original["name"])
        return self._table_text(self.fit_table, row, 1)

    def _observation_channel_key(self, row):
        item = self.observation_table.item(row, 1)
        original = item.data(Qt.UserRole) if item is not None else None
        if isinstance(original, dict) and original.get("name"):
            return str(original["name"])
        return self._table_text(self.observation_table, row, 1)

    def _validate_runtime_config(self, config):
        alphas = list((config.get("enkf") or {}).get("alphas") or [])
        if any(float(value) <= 0 for value in alphas):
            raise ValueError("ES-MDA 膨胀系数必须全部大于 0")
        observation = config.get("observation") or {}
        if float(observation.get("end_day", 0.0)) < float(observation.get("start_day", 0.0)):
            raise ValueError("观测结束天数不能小于起始天数")
        if not observation.get("channels"):
            raise ValueError("至少启用一个观测通道")
        parameters = list(config.get("fit_parameters") or [])
        if not parameters:
            raise ValueError("至少启用一个拟合参数")
        errors = []
        for spec in parameters:
            name = str(spec.get("name") or "")
            label = PARAMETER_LABELS.get(name, name)
            initial = float(spec.get("initial", 0.0))
            lower = float(spec.get("lower", 0.0))
            upper = float(spec.get("upper", 0.0))
            perturb = float(spec.get("perturb", 0.0))
            if not lower < upper:
                errors.append(f"{label}的下限必须小于上限")
            elif not lower <= initial <= upper:
                errors.append(f"{label}的初值必须位于上下限之间")
            if spec.get("transform") == "log" and min(lower, initial, upper) <= 0:
                errors.append(f"{label}使用对数变换时数值必须大于 0")
            if perturb < 0:
                errors.append(f"{label}的扰动不能为负数")
            if not spec.get("path"):
                errors.append(f"{label}缺少参数路径")
        self._update_fit_validation_states(errors)
        if errors:
            raise ValueError("；".join(errors))

    def _update_fit_validation_states(self, errors=None):
        errors = list(errors or [])
        for row in range(self.fit_table.rowCount()):
            item = self.fit_table.item(row, 9)
            if item is None:
                continue
            label = PARAMETER_LABELS.get(self._fit_parameter_key(row), self._fit_parameter_key(row))
            row_errors = [error for error in errors if error.startswith(label)]
            item.setText("；".join(row_errors) if row_errors else "通过")
            item.setForeground(QColor("#b42318") if row_errors else QColor("#1b6e3c"))

    def _on_fit_table_item_changed(self, item):
        if item is None or item.column() == 9:
            return
        self._refresh_fit_row_status(item.row())

    def _refresh_fit_row_status(self, row):
        status_item = self.fit_table.item(row, 9)
        if status_item is None:
            return
        error = ""
        try:
            path = self._parse_path(self._table_text(self.fit_table, row, 2))
            initial = self._table_float(self.fit_table, row, 3, 0.0)
            lower = self._table_float(self.fit_table, row, 4, 0.0)
            upper = self._table_float(self.fit_table, row, 5, 0.0)
            perturb = self._table_float(self.fit_table, row, 7, 0.0)
            transform = self._combo_value(self.fit_table.cellWidget(row, 6))
            if not path:
                error = "缺少参数路径"
            elif not lower < upper:
                error = "下限必须小于上限"
            elif not lower <= initial <= upper:
                error = "初值必须位于上下限之间"
            elif transform == "log" and min(lower, initial, upper) <= 0:
                error = "对数变换要求数值大于 0"
            elif perturb < 0:
                error = "扰动不能为负数"
        except ValueError:
            error = "请输入有效数字"
        self.fit_table.blockSignals(True)
        try:
            status_item.setText(error or "通过")
            status_item.setForeground(QColor("#b42318") if error else QColor("#1b6e3c"))
        finally:
            self.fit_table.blockSignals(False)

    def _handle_collect_clicked(self):
        try:
            config = self.collect_runtime_config()
            channel_count = len(config.get("observation", {}).get("channels", []))
            parameter_count = len(config.get("fit_parameters", []))
            self.status_label.setText(
                f"参数检查完成：{parameter_count} 个拟合参数，{channel_count} 个观测通道。"
            )
        except ValueError as exc:
            self.status_label.setText(f"参数检查失败：{exc}")

    def _handle_generate_config_clicked(self):
        try:
            config = self.collect_runtime_config()
            history_path = self._validated_history_path()
            case_dataset_path = self._validated_case_dataset_path()
            manager = self._history_run_manager()
            runtime = self._prepare_runtime_config(
                config, self.history_root, history_path, case_dataset_path)
            context = manager.prepare(runtime, history_path)
            config_path = Path(context.config_path)
            self._active_run_context = context
            self._viewing_run_context = context
            self.last_runtime_dir = Path(context.run_dir)
            self.last_runtime_config_path = config_path
            self.last_collected_config = json.loads(
                config_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, HistoryMatchingRunError) as exc:
            self.status_label.setText(f"生成运行配置失败：{exc}")
            return
        self.status_label.setText(f"运行配置已生成：{config_path}")

    def generate_runtime_config_file(self):
        config = self.collect_runtime_config()
        history_path = self._validated_history_path()
        case_dataset_path = self._validated_case_dataset_path()
        manager = self._history_run_manager()
        runtime = self._prepare_runtime_config(
            config, self.history_root, history_path, case_dataset_path)
        context = manager.prepare(runtime, history_path)
        config_path = Path(context.config_path)
        self._active_run_context = context
        self._viewing_run_context = context
        self.last_runtime_dir = Path(context.run_dir)
        self.last_runtime_config_path = config_path
        self.last_collected_config = json.loads(config_path.read_text(encoding="utf-8"))
        return config_path

    def _build_preflight_report(self):
        config = self.collect_runtime_config()
        dataset_path = self._validated_case_dataset_path()
        history_path = self._validated_history_path()

        manifest_path = dataset_path / "manifest.json"
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"模型清单读取失败：{exc}") from exc
        grid = dict(manifest.get("grid") or {})
        validation = dict(manifest.get("validation") or {})
        if validation and validation.get("ok") is not True:
            raise ValueError(
                f"模型数据校验未通过：{validation.get('error_count', '-')} 个错误，"
                f"{validation.get('warning_count', '-')} 个警告"
            )

        active_case = (
            self.project_state.active_case()
            if self.project_state is not None
            and hasattr(self.project_state, "active_case") else None
        )
        active_dataset = active_case.active_dataset() if active_case is not None else None
        active_dataset_path = str(getattr(active_dataset, "path", "") or "")
        if active_dataset_path:
            if Path(active_dataset_path).resolve() != dataset_path.resolve():
                raise ValueError("所选模型不是当前算例的活动 Dataset，请先在工程中激活对应 Dataset")

        channels = list((config.get("observation") or {}).get("channels") or [])
        required_columns = sorted({str(item.get("column") or "") for item in channels if item.get("column")})
        history = self._read_history_summary(history_path, required_columns=required_columns)
        start_day = float((config.get("observation") or {}).get("start_day", 0.0))
        end_day = float((config.get("observation") or {}).get("end_day", 0.0))
        if start_day < history["start_day"] or end_day > history["end_day"]:
            raise ValueError(
                f"观测时间 {start_day:g}～{end_day:g} 天超出历史数据范围 "
                f"{history['start_day']:g}～{history['end_day']:g} 天"
            )

        alphas = list((config.get("enkf") or {}).get("alphas") or [])
        ensemble_size = int((config.get("enkf") or {}).get("ensemble_size", 0))
        forward_runs = ensemble_size * len(alphas) + 1
        return {
            "config": config,
            "dataset_path": dataset_path,
            "history_path": history_path,
            "history": history,
            "grid": grid,
            "parameter_count": len(config.get("fit_parameters") or []),
            "channel_count": len(channels),
            "iteration_count": len(alphas),
            "ensemble_size": ensemble_size,
            "forward_runs": forward_runs,
        }

    def _confirm_preflight(self, report):
        grid = report["grid"]
        text = (
            "即将开始历史拟合\n\n"
            f"✓ 模型数据有效：{grid.get('nx', '-')} × {grid.get('ny', '-')} × {grid.get('nz', '-')}，"
            f"活跃网格 {grid.get('active_cell_count', '-')}\n"
            f"✓ 历史数据有效：{report['history']['row_count']} 行，"
            f"{report['history']['start_day']:g}～{report['history']['end_day']:g} 天\n"
            f"✓ 拟合参数：{report['parameter_count']} 个\n"
            f"✓ 观测通道：{report['channel_count']} 个\n"
            f"✓ ES-MDA 轮次：{report['iteration_count']} 轮\n\n"
            f"预计执行 {report['forward_runs']} 次前向模拟（当前串行执行）。\n\n"
            "是否确认开始？"
        )
        answer = QMessageBox.question(
            self,
            "运行前检查",
            text,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        return answer == QMessageBox.Yes

    def start_generate_history_target(self):
        if self.process is not None and self.process.state() != QProcess.NotRunning:
            self._append_run_log("历史拟合正在运行，不能同时生成目标数据。")
            return
        if self.target_process is not None and self.target_process.state() != QProcess.NotRunning:
            self._append_run_log("目标历史数据正在生成。")
            return

        try:
            case_dataset_path = self._validated_case_dataset_path()
        except ValueError as exc:
            self.status_label.setText(f"生成目标数据失败：{exc}")
            self._append_run_log(f"生成目标数据失败：{exc}")
            return

        script_path = self.history_root / "generate_history_fit_target_direct.py"
        output_path = self.history_root / "history_fit_target.csv"
        truth_params_path = self.history_root / "history_fit_truth_params.json"
        log_path = self.history_root / "history_fit_truth_run.log"

        self._target_stdout_buffer = ""
        self._target_stderr_buffer = ""
        self.run_log.clear()
        self._append_run_log(
            "启动目标数据生成: "
            f"{sys.executable} {script_path} --case-dataset-path {case_dataset_path} "
            f"--output {output_path}"
        )
        self.status_label.setText("正在生成目标历史数据...")
        self.target_process = QProcess(self)
        self.target_process.setProgram(sys.executable)
        self.target_process.setArguments([
            str(script_path),
            "--case-dataset-path",
            str(case_dataset_path),
            "--output",
            str(output_path),
            "--truth-params-output",
            str(truth_params_path),
            "--log",
            str(log_path),
        ])
        self.target_process.setWorkingDirectory(str(self.history_root))
        self.target_process.readyReadStandardOutput.connect(self._handle_target_stdout)
        self.target_process.readyReadStandardError.connect(self._handle_target_stderr)
        self.target_process.errorOccurred.connect(self._handle_target_error)
        self.target_process.finished.connect(self._handle_target_finished)
        self._set_target_process_running(True)
        self.target_process.start()

    def _validated_case_dataset_path(self):
        raw_path = self.case_dataset_path_edit.text().strip()
        if not raw_path:
            raise ValueError("未设置 case_dataset 目录")
        path = Path(raw_path).expanduser()
        if not path.is_absolute():
            path = self._resolve_existing_or_template_path(raw_path)
        path = path.resolve()
        if not path.exists():
            raise ValueError(f"case_dataset 不存在: {path}")
        if not path.is_dir():
            raise ValueError(f"case_dataset 路径不是目录: {path}")
        if not (path / "manifest.json").exists():
            raise ValueError(f"case_dataset 缺少 manifest.json: {path}")
        return path

    def _validated_history_path(self):
        raw_path = self.history_file_edit.text().strip()
        if not raw_path:
            raise ValueError("未设置历史数据 CSV")
        path = Path(raw_path).expanduser()
        if not path.is_absolute():
            path = self._resolve_history_path(raw_path)
        path = path.resolve()
        if not path.exists():
            raise ValueError(f"历史数据 CSV 不存在: {path}")
        if not path.is_file():
            raise ValueError(f"历史数据 CSV 路径不是文件: {path}")
        return path

    def _handle_target_stdout(self):
        if self.target_process is None:
            return
        text = bytes(self.target_process.readAllStandardOutput()).decode("utf-8", errors="replace")
        self._consume_target_text(text, stderr=False)

    def _handle_target_stderr(self):
        if self.target_process is None:
            return
        text = bytes(self.target_process.readAllStandardError()).decode("utf-8", errors="replace")
        self._consume_target_text(text, stderr=True)

    def _consume_target_text(self, text, stderr=False):
        if not text:
            return
        buffer_name = "_target_stderr_buffer" if stderr else "_target_stdout_buffer"
        data = getattr(self, buffer_name) + text
        lines = data.splitlines(keepends=True)
        if lines and not lines[-1].endswith(("\n", "\r")):
            setattr(self, buffer_name, lines.pop())
        else:
            setattr(self, buffer_name, "")

        for raw_line in lines:
            line = raw_line.rstrip("\r\n")
            if not line:
                continue
            self._append_run_log(f"[target stderr] {line}" if stderr else f"[target] {line}")
            if not stderr and line.startswith("target="):
                self.history_file_edit.setText(line.split("=", 1)[1].strip())

    def _flush_target_buffers(self):
        for buffer_name, stderr in (("_target_stdout_buffer", False), ("_target_stderr_buffer", True)):
            line = getattr(self, buffer_name)
            if not line:
                continue
            setattr(self, buffer_name, "")
            self._append_run_log(f"[target stderr] {line}" if stderr else f"[target] {line}")

    def _handle_target_error(self, error):
        self._append_run_log(f"目标数据生成进程错误: {error}")
        if self.target_process is None or self.target_process.state() == QProcess.NotRunning:
            self._set_target_process_running(False)
            self.target_process = None

    def _handle_target_finished(self, exit_code, exit_status):
        self._flush_target_buffers()
        output_path = self.history_root / "history_fit_target.csv"
        if exit_code == 0 and output_path.exists():
            self.history_file_edit.setText(str(output_path))
            self.status_label.setText(f"目标历史数据已生成：{output_path}")
            self._append_run_log(f"目标历史数据已生成: {output_path}")
        else:
            self.status_label.setText(f"目标历史数据生成失败，退出码：{exit_code}")
            self._append_run_log(f"目标历史数据生成失败: exit_code={exit_code}, exit_status={exit_status}")
        self._set_target_process_running(False)
        self.target_process = None

    def _set_target_process_running(self, running):
        if hasattr(self, "generate_target_button"):
            self.generate_target_button.setEnabled(not running)
        if hasattr(self, "generate_config_button"):
            self.generate_config_button.setEnabled(not running)
        if hasattr(self, "run_button"):
            self.run_button.setEnabled(not running)

    def start_history_matching(self):
        if self.process is not None and self.process.state() != QProcess.NotRunning:
            self._append_run_log("历史拟合已经在运行。")
            return

        try:
            report = self._build_preflight_report()
        except (OSError, ValueError, HistoryMatchingRunError) as exc:
            self.run_state_label.setText(f"运行前检查失败：{exc}")
            self.status_label.setText(f"运行前检查失败：{exc}")
            QMessageBox.warning(self, "运行前检查失败", str(exc))
            return
        if not self._confirm_preflight(report):
            self.status_label.setText("已取消历史拟合运行。")
            return

        try:
            config_path = self.generate_runtime_config_file()
        except (OSError, ValueError, HistoryMatchingRunError) as exc:
            self.run_state_label.setText(f"启动失败：{exc}")
            self._append_run_log(f"启动失败：{exc}")
            self._append_business_log(f"启动失败：{exc}")
            self._progress_timer.stop()
            return

        self.result_payload = None
        self._stdout_buffer = ""
        self._stderr_buffer = ""
        self._stop_requested = False
        self._structured_events_seen = False
        self.run_log.clear()
        self.business_log.clear()
        self._reset_progress_view(report["forward_runs"])
        self._run_started_at = time.monotonic()
        self._progress_timer.start()
        self._append_business_log(
            f"运行准备完成：{report['iteration_count']} 轮，"
            f"每轮 {report['ensemble_size']} 个成员，共 {report['forward_runs']} 次前向模拟。"
        )
        self._reset_result_view()
        self.run_state_label.setText("运行中")
        self.progress_label.setText(
            f"等待计算：共 {report['iteration_count']} 轮、"
            f"{report['ensemble_size']} 个成员、{report['forward_runs']} 次前向模拟"
        )
        self.runtime_config_label.setText(f"运行配置: {config_path}")
        self.tabs.setCurrentIndex(3)

        script_path = self.history_root / "run_enkf_history_match.py"
        self.process = QProcess(self)
        self.process.setProgram(sys.executable)
        self.process.setArguments([str(script_path), "--config", str(config_path)])
        self.process.setWorkingDirectory(str(self.last_runtime_dir))
        self.process.readyReadStandardOutput.connect(self._handle_process_stdout)
        self.process.readyReadStandardError.connect(self._handle_process_stderr)
        self.process.errorOccurred.connect(self._handle_process_error)
        self.process.finished.connect(self._handle_process_finished)
        self._set_process_running(True)
        self._append_run_log(f"启动命令: {sys.executable} {script_path} --config {config_path}")
        manager = self._history_run_manager()
        manager.mark_running(self._active_run_context)
        self.run_state_changed.emit(
            self._active_run_context.case_id, self._active_run_context.run_id)
        self.process.start()

    def stop_history_matching(self):
        if self.process is None or self.process.state() == QProcess.NotRunning:
            return
        self._append_run_log("请求停止历史拟合进程。")
        self._append_business_log("正在停止历史拟合，请稍候。")
        self.run_state_label.setText("正在停止")
        self._stop_requested = True
        self.process.terminate()

    def _handle_process_stdout(self):
        if self.process is None:
            return
        text = bytes(self.process.readAllStandardOutput()).decode("utf-8", errors="replace")
        self._consume_process_text(text, stderr=False)

    def _handle_process_stderr(self):
        if self.process is None:
            return
        text = bytes(self.process.readAllStandardError()).decode("utf-8", errors="replace")
        self._consume_process_text(text, stderr=True)

    def _consume_process_text(self, text, stderr=False):
        if not text:
            return
        buffer_name = "_stderr_buffer" if stderr else "_stdout_buffer"
        data = getattr(self, buffer_name) + text
        lines = data.splitlines(keepends=True)
        if lines and not lines[-1].endswith(("\n", "\r")):
            setattr(self, buffer_name, lines.pop())
        else:
            setattr(self, buffer_name, "")

        for raw_line in lines:
            line = raw_line.rstrip("\r\n")
            if not line:
                continue
            display_line = f"[stderr] {line}" if stderr else line
            self._append_run_log(display_line)
            if not stderr:
                self._parse_process_line(line)

    def _flush_process_buffers(self):
        for buffer_name, stderr in (("_stdout_buffer", False), ("_stderr_buffer", True)):
            line = getattr(self, buffer_name)
            if not line:
                continue
            setattr(self, buffer_name, "")
            display_line = f"[stderr] {line}" if stderr else line
            self._append_run_log(display_line)
            if not stderr:
                self._parse_process_line(line)

    def _parse_process_line(self, line):
        if line.startswith("HM_EVENT="):
            try:
                event = json.loads(line.split("=", 1)[1])
            except json.JSONDecodeError as exc:
                self._append_business_log(f"运行事件解析失败：{exc}")
                return
            self._structured_events_seen = True
            self._handle_progress_event(event)
            return

        member_match = re.search(
            r"iteration=(\d+)\s+member=(\d+)\s+objective=([0-9.eE+-]+)",
            line,
        )
        if member_match:
            if self._structured_events_seen:
                return
            iteration, member, objective = member_match.groups()
            if self._active_run_context is not None:
                self._history_run_manager().record_member(
                    self._active_run_context, iteration, member, objective)
            self.progress_label.setText(
                f"第 {int(iteration) + 1} 轮，成员 {int(member) + 1}，当前误差：{objective}"
            )
            self._progress_completed = min(
                self._progress_total, self._progress_completed + 1)
            self._best_objective_value = (
                float(objective) if self._best_objective_value is None
                else min(self._best_objective_value, float(objective))
            )
            self._update_progress_counts()
            self.current_objective_label.setText(f"当前误差：{float(objective):.6g}")
            self.best_objective_label.setText(
                f"当前全局最优误差：{self._best_objective_value:.6g}")
            return

        summary_match = re.search(
            r"iteration=(\d+)\s+objective_min=([0-9.eE+-]+)\s+"
            r"objective_mean=([0-9.eE+-]+)\s+objective_max=([0-9.eE+-]+)",
            line,
        )
        if summary_match:
            if self._structured_events_seen:
                return
            iteration, minimum, mean, maximum = summary_match.groups()
            if self._active_run_context is not None:
                self._history_run_manager().record_iteration(
                    self._active_run_context,
                    iteration, minimum, mean, maximum,
                )
            self.progress_label.setText(
                f"第 {int(iteration) + 1} 轮完成，误差最小/平均/最大："
                f"{minimum} / {mean} / {maximum}"
            )
            self._append_business_log(
                f"第 {int(iteration) + 1} 轮完成：最小误差 {minimum}，平均误差 {mean}。")
            return

        if line.startswith("best_fit_objective="):
            value = line.split("=", 1)[1].strip()
            self.progress_label.setText(f"最终最佳误差：{value}")
            return

        if line.startswith("best_fit_selected_source="):
            source = line.split("=", 1)[1].strip()
            self.run_state_label.setText(f"已选择拟合结果：{self._source_label(source)}")
            return

        if line.startswith("best_fit_output="):
            output_path = line.split("=", 1)[1].strip()
            self.runtime_config_label.setText(f"最佳拟合输出: {output_path}")
            return

        if not line.startswith("RESULT_JSON="):
            return

        try:
            payload = json.loads(line.split("=", 1)[1])
        except json.JSONDecodeError as exc:
            self._append_run_log(f"RESULT_JSON 解析失败: {exc}")
            return

        self.result_payload = payload
        objective = payload.get("objective", "-")
        mode = payload.get("mode", "-")
        selected_source = payload.get("selected_source", "-")
        self.run_state_label.setText("结果已解析")
        self.progress_label.setText(
            f"井控模式：{self._well_mode_label(mode)}，结果来源："
            f"{self._source_label(selected_source)}，误差：{objective}"
        )
        self._update_result_view(payload)

    def _handle_progress_event(self, event):
        if not isinstance(event, dict):
            return
        event_type = str(event.get("type") or "")
        total_runs = int(event.get("total_forward_runs") or self._progress_total or 0)
        if total_runs > 0:
            self._progress_total = total_runs

        if event_type == "run_started":
            if self._run_started_at is None:
                self._run_started_at = time.monotonic()
            self._progress_completed = 0
            self._best_objective_value = None
            self._completed_durations = []
            self._progress_timer.start()
            self.run_state_label.setText("运行中")
            self.round_member_label.setText(
                f"轮次：0 / {event.get('total_iterations', '-')}，"
                f"成员：0 / {event.get('total_members', '-')}")
            self._update_progress_counts()
            self._append_business_log("历史拟合已启动，正在准备第一轮计算。")
            return

        if event_type == "iteration_started":
            iteration = int(event.get("iteration") or 0)
            total_iterations = event.get("total_iterations", "-")
            total_members = event.get("total_members", "-")
            self.round_member_label.setText(
                f"轮次：{iteration} / {total_iterations}，成员：0 / {total_members}")
            self.progress_label.setText(f"第 {iteration} 轮正在运行")
            self._append_business_log(
                f"第 {iteration}/{total_iterations} 轮开始，膨胀系数 {event.get('alpha', '-')}。")
            return

        if event_type == "member_started":
            iteration = int(event.get("iteration") or 0)
            member = int(event.get("member") or 0)
            self.round_member_label.setText(
                f"轮次：{iteration} / {event.get('total_iterations', '-')}，"
                f"成员：{member} / {event.get('total_members', '-')}")
            self.progress_label.setText(f"第 {iteration} 轮，第 {member} 个成员正在计算")
            self.current_objective_label.setText("当前误差：计算中")
            return

        if event_type in {"member_completed", "final_mean_completed"}:
            self._progress_completed = int(
                event.get("completed_runs") or self._progress_completed)
            objective = float(event.get("objective"))
            best_objective = float(event.get("best_objective", objective))
            improved = bool(event.get("best_improved", False))
            self._best_objective_value = best_objective
            elapsed = float(event.get("elapsed_seconds") or 0.0)
            reused = bool(event.get("reused", False))
            if elapsed > 0 and not reused:
                self._completed_durations.append(elapsed)
                self._completed_durations = self._completed_durations[-20:]
            self.current_objective_label.setText(f"当前误差：{objective:.6g}")
            self.best_objective_label.setText(
                f"当前全局最优误差：{best_objective:.6g}")
            self._update_progress_counts()
            self._refresh_runtime_clock()

            if event_type == "member_completed":
                iteration_index = int(event.get("iteration_index", int(event.get("iteration", 1)) - 1))
                member_index = int(event.get("member_index", int(event.get("member", 1)) - 1))
                if self._active_run_context is not None:
                    self._history_run_manager().record_member(
                        self._active_run_context,
                        iteration_index,
                        member_index,
                        objective,
                    )
                suffix = "（复用已有结果）" if reused else ""
                if improved:
                    self._append_business_log(
                        f"发现新的全局最优误差 {best_objective:.6g}{suffix}。")
            else:
                self.progress_label.setText("最终集合均值计算完成")
                self._append_business_log(
                    f"最终集合均值计算完成，误差 {objective:.6g}。")
            return

        if event_type == "iteration_completed":
            iteration = int(event.get("iteration") or 0)
            minimum = float(event.get("objective_min"))
            mean = float(event.get("objective_mean"))
            maximum = float(event.get("objective_max"))
            if self._active_run_context is not None:
                self._history_run_manager().record_iteration(
                    self._active_run_context,
                    int(event.get("iteration_index", iteration - 1)),
                    minimum,
                    mean,
                    maximum,
                )
            self.progress_label.setText(
                f"第 {iteration} 轮完成，误差最小/平均/最大："
                f"{minimum:.6g} / {mean:.6g} / {maximum:.6g}")
            self._append_business_log(
                f"第 {iteration}/{event.get('total_iterations', '-')} 轮完成："
                f"最小误差 {minimum:.6g}，平均误差 {mean:.6g}。")
            return

        if event_type == "final_mean_started":
            self.round_member_label.setText("正在计算最终集合均值")
            self.progress_label.setText("正在执行最后一次前向模拟")
            self._append_business_log("所有同化轮次已完成，正在计算最终集合均值。")
            return

        if event_type == "run_completed":
            self._progress_completed = int(
                event.get("completed_runs") or self._progress_total)
            self._update_progress_counts()
            self._progress_timer.stop()
            self._refresh_runtime_clock()
            self.remaining_time_label.setText("预计剩余：已完成")
            self._append_business_log(
                f"历史拟合完成，最终选择误差 {float(event.get('objective')):.6g}。")
            return

        if event_type == "run_failed":
            self._progress_timer.stop()
            message = str(event.get("message") or "未知错误")
            self.run_state_label.setText("运行失败")
            self._show_error_guidance(message)

    def _reset_progress_view(self, total_runs=0):
        self._progress_total = max(0, int(total_runs or 0))
        self._progress_completed = 0
        self._best_objective_value = None
        self._completed_durations = []
        self._run_started_at = None
        if not hasattr(self, "progress_bar"):
            return
        self.progress_bar.setValue(0)
        self.round_member_label.setText("轮次：- / -，成员：- / -")
        self.completed_runs_label.setText(
            f"已完成计算：0 / {self._progress_total}")
        self.current_objective_label.setText("当前误差：-")
        self.best_objective_label.setText("当前全局最优误差：-")
        self.elapsed_time_label.setText("已运行：00:00")
        self.remaining_time_label.setText("预计剩余：等待首个成员完成")
        self.error_guidance_label.clear()
        self.error_guidance_label.setVisible(False)

    def _update_progress_counts(self):
        if not hasattr(self, "progress_bar"):
            return
        total = max(0, int(self._progress_total))
        completed = max(0, min(int(self._progress_completed), total)) if total else 0
        percent = int(round(100.0 * completed / total)) if total else 0
        self.progress_bar.setValue(percent)
        self.completed_runs_label.setText(f"已完成计算：{completed} / {total}")

    def _refresh_runtime_clock(self):
        if not hasattr(self, "elapsed_time_label") or self._run_started_at is None:
            return
        elapsed = max(0.0, time.monotonic() - self._run_started_at)
        self.elapsed_time_label.setText(f"已运行：{self._format_duration(elapsed)}")
        remaining_runs = max(0, self._progress_total - self._progress_completed)
        if remaining_runs == 0 and self._progress_total > 0:
            self.remaining_time_label.setText("预计剩余：已完成")
        elif self._completed_durations:
            average = sum(self._completed_durations) / len(self._completed_durations)
            self.remaining_time_label.setText(
                f"预计剩余：约 {self._format_duration(average * remaining_runs)}")
        else:
            self.remaining_time_label.setText("预计剩余：等待首个成员完成")

    @staticmethod
    def _format_duration(seconds):
        total_seconds = max(0, int(round(float(seconds or 0.0))))
        hours, remainder = divmod(total_seconds, 3600)
        minutes, secs = divmod(remainder, 60)
        if hours:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"

    def _append_business_log(self, text):
        if not hasattr(self, "business_log") or not text:
            return
        self.business_log.append(str(text))
        self.business_log.ensureCursorVisible()

    @staticmethod
    def _friendly_error_message(raw_text):
        text = str(raw_text or "").strip()
        lower = text.lower()
        mappings = [
            (
                ("case_dataset" in lower and (
                    "does not exist" in lower or "missing" in lower or "required" in lower
                )) or "manifest.json" in lower,
                "模型数据目录无效或缺少模型清单。请返回“运行设置”，重新选择当前算例的有效 Dataset。",
            ),
            (
                "history file is empty" in lower or "csv 没有数据" in text,
                "历史数据文件为空。请检查 CSV 是否包含表头和至少一行有效生产数据。",
            ),
            (
                "rate control column does not exist" in lower
                or "缺少观测列" in text
                or "keyerror" in lower
                or ("column" in lower and "does not exist" in lower),
                "历史数据字段与观测配置不一致。请检查 day 列以及已启用观测通道对应的 CSV 列名。",
            ),
            (
                "module is not available" in lower
                or "modulenotfounderror" in lower
                or "dll load failed" in lower
                or "cannot open shared object" in lower,
                "计算模块未正确加载。请确认 C++ 模块已经编译，并且运行环境包含所需 DLL 和 Python 扩展。",
            ),
            (
                "simulation output not found" in lower
                or "simulation output is empty" in lower,
                "前向模拟没有生成有效结果。请检查模型参数、井控设置和求解器详细日志。",
            ),
            (
                "memoryerror" in lower or "out of memory" in lower,
                "运行内存不足。建议减小集合规模、降低模型规模或关闭其他占用内存的程序后重试。",
            ),
            (
                "singular matrix" in lower
                or "linalgerror" in lower
                or "not positive definite" in lower,
                "同化矩阵计算失败。建议增加观测误差、减少高度相关的观测点或缩小拟合参数数量。",
            ),
            (
                "converg" in lower or "不收敛" in text,
                "前向求解未收敛。建议检查参数上下限、初始状态、井控条件和时间步设置。",
            ),
        ]
        for matched, message in mappings:
            if matched:
                return message
        chinese_lines = [
            line.strip() for line in text.splitlines()
            if re.search(r"[\u4e00-\u9fff]", line)
            and not line.lstrip().startswith(("File ", "Traceback"))
        ]
        if chinese_lines:
            return f"运行失败：{chinese_lines[-1]} 请展开详细技术日志查看完整信息。"
        return "历史拟合运行发生异常。请展开详细技术日志查看具体原因，并检查模型、历史数据和参数配置。"

    def _show_error_guidance(self, raw_text):
        message = self._friendly_error_message(raw_text)
        self.error_guidance_label.setText(f"错误诊断：{message}")
        self.error_guidance_label.setVisible(True)
        self._append_business_log(f"错误诊断：{message}")
        return message

    def _handle_process_error(self, error):
        self.run_state_label.setText(f"进程错误: {error}")
        self._append_run_log(f"进程错误: {error}")
        self._show_error_guidance(f"Process error: {error}")
        if self.process is None or self.process.state() == QProcess.NotRunning:
            self._progress_timer.stop()
            if self._active_run_context is not None:
                context = self._active_run_context
                self._history_run_manager().mark_failed(
                    context, f"Process error: {error}")
                self.run_state_changed.emit(context.case_id, context.run_id)
                self._active_run_context = None
            self._set_process_running(False)
            self.process = None

    def _handle_process_finished(self, exit_code, exit_status):
        self._flush_process_buffers()
        self._progress_timer.stop()
        self._refresh_runtime_clock()
        context = self._active_run_context
        if self._stop_requested:
            self.run_state_label.setText("已停止")
            self.remaining_time_label.setText("预计剩余：已停止")
            self._append_business_log("历史拟合已由用户停止。")
        elif exit_code == 0:
            if not self._structured_events_seen:
                self._progress_completed = self._progress_total
                self._update_progress_counts()
                self.remaining_time_label.setText("预计剩余：已完成")
            if self.result_payload:
                self.run_state_label.setText("运行完成，结果已解析")
            else:
                self.run_state_label.setText("运行完成")
            if not self._structured_events_seen:
                self._append_business_log("历史拟合运行完成。")
        else:
            self.run_state_label.setText(f"运行失败，退出码: {exit_code}")
            self.remaining_time_label.setText("预计剩余：运行失败")
            if self.error_guidance_label.isHidden():
                self._show_error_guidance(self.run_log.toPlainText())
        self._append_run_log(f"进程结束: exit_code={exit_code}, exit_status={exit_status}")
        if context is not None:
            manager = self._history_run_manager()
            if self._stop_requested:
                manager.mark_failed(
                    context, "History matching cancelled by user",
                    exit_code=exit_code, cancelled=True)
            elif exit_code == 0:
                manager.mark_completed(
                    context, payload=self.result_payload, exit_code=exit_code)
            else:
                manager.mark_failed(
                    context, f"History matching exited with code {exit_code}",
                    exit_code=exit_code)
            self.run_state_changed.emit(context.case_id, context.run_id)
            self._active_run_context = None
            self.derive_case_button.setEnabled(exit_code == 0)
        self._set_process_running(False)
        self.process = None

    def _set_process_running(self, running):
        self.run_button.setEnabled(not running)
        self.stop_button.setEnabled(running)
        self.generate_config_button.setEnabled(not running)
        if hasattr(self, "generate_target_button"):
            self.generate_target_button.setEnabled(not running)
        self.collect_button.setEnabled(not running)

    def _append_run_log(self, text):
        if not hasattr(self, "run_log"):
            return
        self.run_log.append(str(text))
        self.run_log.ensureCursorVisible()
        if self._active_run_context is not None:
            try:
                self._history_run_manager().append_log(
                    self._active_run_context, text)
            except (OSError, HistoryMatchingRunError):
                pass

    def refresh_result_view(self):
        payload = self.result_payload or self._load_latest_result_payload()
        if payload:
            self.result_payload = payload
            self._update_result_view(payload)
            self._append_run_log("结果视图已刷新。")
            return
        self._reset_result_view()
        self._append_run_log("未找到可刷新的历史拟合结果。")

    def _reset_result_view(self):
        if not hasattr(self, "result_objective_label"):
            return
        if hasattr(self, "derive_case_button"):
            self.derive_case_button.setEnabled(False)
        if hasattr(self, "export_results_button"):
            self.export_results_button.setEnabled(False)
        if hasattr(self, "open_results_button"):
            self.open_results_button.setEnabled(False)
        self.result_objective_label.setText("-")
        self.result_source_label.setText("-")
        self.result_mode_label.setText("-")
        self.fit_quality_label.setText("-")
        self.fit_quality_label.setStyleSheet("")
        self.fit_quality_detail_label.setText(
            "评价依据：归一化误差 ≤1 为好，1～2 为一般，>2 为差。")
        self.results_dir_label.setText("结果目录: -")
        self.runtime_config_label.setText("运行配置: -")
        self._set_result_plot(None)
        self._populate_best_params({})
        self._populate_result_files(self._target_context_files())

    def _update_result_view(self, payload):
        if not isinstance(payload, dict):
            payload = {}
        self.result_objective_label.setText(str(payload.get("objective", "-")))
        self.result_source_label.setText(self._source_label(payload.get("selected_source", "-")))
        self.result_mode_label.setText(self._well_mode_label(payload.get("mode", "-")))
        quality = self._fit_quality(payload.get("objective"))
        self.fit_quality_label.setText(quality["label"])
        self.fit_quality_label.setStyleSheet(
            f"color: {quality['color']}; font-weight: 600;")
        self.fit_quality_detail_label.setText(quality["detail"])

        files = dict(payload.get("files") or {})
        if not files:
            files = self._expected_result_files()
        files = self._with_target_context_files(files)
        results_dir = self._infer_results_dir(files)
        self.results_dir_label.setText(f"结果目录: {results_dir or '-'}")
        self.export_results_button.setEnabled(bool(payload))
        self.open_results_button.setEnabled(
            bool(results_dir) and Path(results_dir).is_dir())
        self._set_result_plot(files.get("plot"))
        self._populate_best_params(payload)
        self._populate_result_files(files)

    @staticmethod
    def _fit_quality(objective):
        try:
            value = float(objective)
        except (TypeError, ValueError):
            return {
                "code": "unknown",
                "label": "无法评价",
                "color": "#667085",
                "detail": "没有可用的归一化误差，暂时无法判断拟合质量。",
            }
        if not math.isfinite(value):
            return {
                "code": "unknown",
                "label": "无法评价",
                "color": "#667085",
                "detail": "归一化误差不是有限数值，请检查运行结果和详细技术日志。",
            }
        good = FIT_QUALITY_THRESHOLDS["good"]
        acceptable = FIT_QUALITY_THRESHOLDS["acceptable"]
        if value <= good:
            code, label, color = "good", "好", "#1b6e3c"
            reason = "整体残差处于观测误差范围内"
        elif value <= acceptable:
            code, label, color = "acceptable", "一般", "#9a6700"
            reason = "整体趋势基本匹配，但部分时段或通道仍有明显偏差"
        else:
            code, label, color = "poor", "差", "#b42318"
            reason = "残差明显高于设定的观测误差，建议检查参数范围、通道权重和历史数据"
        return {
            "code": code,
            "label": f"{label}（归一化误差 {value:.6g}）",
            "color": color,
            "detail": (
                f"评价：{reason}。阈值：≤{good:g} 为好，"
                f"{good:g}～{acceptable:g} 为一般，>{acceptable:g} 为差。"
            ),
        }

    def export_result_package(self, destination=None):
        interactive = destination is None or isinstance(destination, bool)
        payload = self.result_payload or self._load_latest_result_payload()
        if not isinstance(payload, dict) or not payload:
            message = "没有可导出的历史拟合结果。"
            self.status_label.setText(message)
            if interactive:
                QMessageBox.warning(self, "导出失败", message)
            return None

        if interactive:
            default_name = "历史拟合结果.zip"
            if self._viewing_run_context is not None:
                run_id = str(self._viewing_run_context.run_id or "").strip()
                if run_id:
                    default_name = f"历史拟合结果_{run_id}.zip"
            selected, _ = QFileDialog.getSaveFileName(
                self,
                "导出历史拟合结果",
                str(Path.home() / default_name),
                "ZIP 压缩包 (*.zip)",
            )
            if not selected:
                return None
            destination = selected

        archive_path = Path(str(destination)).expanduser()
        if archive_path.suffix.lower() != ".zip":
            archive_path = archive_path.with_suffix(".zip")
        archive_path.parent.mkdir(parents=True, exist_ok=True)

        quality = self._fit_quality(payload.get("objective"))
        files = dict(payload.get("files") or {})
        if not files:
            files = self._expected_result_files()
        result_entries = {
            "plot": "results/history_fit_gas_water.png",
            "best_fit_params": "results/best_fit_params.json",
            "best_fit_output": "results/best_fit_output.csv",
            "summary": "results/best_fit_summary.json",
            "assimilation_summary": "results/assimilation_summary.csv",
        }
        included = []
        missing = []
        with zipfile.ZipFile(
            archive_path, "w", compression=zipfile.ZIP_DEFLATED
        ) as archive:
            archive.writestr(
                "run_result.json",
                json.dumps(payload, ensure_ascii=False, indent=2),
            )
            for key, arcname in result_entries.items():
                resolved = self._resolve_result_path(files.get(key))
                if resolved is not None and resolved.is_file():
                    archive.write(resolved, arcname)
                    included.append(arcname)
                else:
                    missing.append(key)

            config_path = self.last_runtime_config_path
            if config_path is None and self._viewing_run_context is not None:
                config_path = Path(self._viewing_run_context.config_path)
            if config_path is not None and Path(config_path).is_file():
                archive.write(Path(config_path), "runtime/enkf_runtime_config.json")
                included.append("runtime/enkf_runtime_config.json")
            else:
                missing.append("runtime_config")

            context = self._viewing_run_context
            if context is not None:
                if context.log_path and Path(context.log_path).is_file():
                    archive.write(Path(context.log_path), "runtime/run.log")
                    included.append("runtime/run.log")
                else:
                    missing.append("run_log")
                if context.observation_path and Path(context.observation_path).is_file():
                    suffix = Path(context.observation_path).suffix or ".csv"
                    archive.write(
                        Path(context.observation_path),
                        f"observation/history{suffix}",
                    )
                    included.append(f"observation/history{suffix}")
                else:
                    missing.append("observation_csv")

            manifest = {
                "schema_version": "history_matching_export_v1",
                "exported_at": datetime.now().isoformat(timespec="seconds"),
                "objective": payload.get("objective"),
                "quality": quality,
                "mode": payload.get("mode"),
                "selected_source": payload.get("selected_source"),
                "included_files": sorted(included),
                "missing_optional_files": sorted(set(missing)),
            }
            archive.writestr(
                "export_manifest.json",
                json.dumps(manifest, ensure_ascii=False, indent=2),
            )
            archive.writestr(
                "结果说明.txt",
                (
                    f"历史拟合评价：{quality['label']}\n"
                    f"{quality['detail']}\n"
                    f"结果来源：{self._source_label(payload.get('selected_source', '-'))}\n"
                    f"井控模式：{self._well_mode_label(payload.get('mode', '-'))}\n"
                ),
            )

        self.status_label.setText(f"历史拟合结果已导出：{archive_path}")
        self._append_business_log(f"结果包已导出：{archive_path}")
        if interactive:
            QMessageBox.information(self, "导出完成", f"结果已导出到：\n{archive_path}")
        return archive_path

    def _open_results_directory(self):
        payload = self.result_payload or {}
        files = dict(payload.get("files") or {})
        if not files:
            files = self._expected_result_files()
        results_dir = self._infer_results_dir(files)
        if not results_dir or not Path(results_dir).is_dir():
            QMessageBox.warning(self, "打开失败", "没有可用的历史拟合结果目录。")
            return False
        return bool(QDesktopServices.openUrl(QUrl.fromLocalFile(results_dir)))

    def _load_latest_result_payload(self):
        candidates = []
        if self._viewing_run_context is not None:
            candidates.append(
                Path(self._viewing_run_context.results_dir) / "run_result.json")
        active_case = (
            self.project_state.active_case()
            if self.project_state is not None
            and hasattr(self.project_state, "active_case") else None
        )
        if active_case is not None:
            for record in reversed(active_case.run_records or []):
                if record.run_type != RUN_TYPE_HISTORY_MATCHING:
                    continue
                result_path = str((record.artifacts or {}).get("result_json") or "")
                if result_path:
                    candidates.append(Path(result_path))
        if self.last_runtime_dir:
            candidates.append(Path(self.last_runtime_dir) / "results" / "run_result.json")
        ui_runs = self.history_root / "ui_runs"
        if ui_runs.exists():
            candidates.extend(sorted(
                ui_runs.glob("run_*/results/run_result.json"),
                key=lambda path: path.stat().st_mtime if path.exists() else 0,
                reverse=True,
            ))
        for result_dir in ("results_ui", "results_fit_target", "results_free_full", "results_fixed_bhp_full"):
            candidates.append(self.history_root / result_dir / "run_result.json")

        seen = set()
        for path in candidates:
            path = Path(path)
            key = str(path.resolve()) if path.exists() else str(path)
            if key in seen:
                continue
            seen.add(key)
            if not path.exists():
                continue
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                self._append_run_log(f"读取结果文件失败: {path} ({exc})")
        return None

    def _expected_result_files(self):
        if not self.last_runtime_dir:
            return self._target_context_files()
        results_dir = Path(self.last_runtime_dir) / "results"
        return self._with_target_context_files({
            "plot": str(results_dir / "history_fit_gas_water.png"),
            "best_fit_params": str(results_dir / "best_fit_params.json"),
            "best_fit_output": str(results_dir / "best_fit_output.csv"),
            "summary": str(results_dir / "best_fit_summary.json"),
            "assimilation_summary": str(results_dir / "assimilation_summary.csv"),
        })

    def _target_context_files(self):
        files = {
            "history_target_csv": str(self.history_root / "history_fit_target.csv"),
            "truth_params": str(self.history_root / "history_fit_truth_params.json"),
            "target_generation_log": str(self.history_root / "history_fit_truth_run.log"),
        }
        history_text = self.history_file_edit.text().strip() if hasattr(self, "history_file_edit") else ""
        if history_text:
            files["current_history_csv"] = str(self._resolve_history_path(history_text))
        dataset_text = self.case_dataset_path_edit.text().strip() if hasattr(self, "case_dataset_path_edit") else ""
        if dataset_text:
            dataset_path = Path(dataset_text).expanduser()
            if not dataset_path.is_absolute():
                dataset_path = self._resolve_existing_or_template_path(dataset_text)
            files["case_dataset"] = str(dataset_path)
        return files

    def _with_target_context_files(self, files):
        merged = dict(files or {})
        for key, value in self._target_context_files().items():
            merged.setdefault(key, value)
        return merged

    def _infer_results_dir(self, files):
        for raw_path in (files or {}).values():
            resolved = self._resolve_result_path(raw_path)
            if resolved:
                return str(resolved.parent)
        return ""

    def _set_result_plot(self, raw_path):
        if not hasattr(self, "result_plot_label"):
            return
        resolved = self._resolve_result_path(raw_path)
        if not resolved:
            self.result_plot_label.clear()
            self.result_plot_label.setText("等待历史拟合输出曲线图")
            self.result_plot_path_label.setText("图片路径: -")
            return
        self.result_plot_path_label.setText(f"图片路径: {resolved}")
        if not resolved.exists():
            self.result_plot_label.clear()
            self.result_plot_label.setText("曲线图文件尚未生成")
            return
        pixmap = QPixmap(str(resolved))
        if pixmap.isNull():
            self.result_plot_label.clear()
            self.result_plot_label.setText("曲线图文件读取失败")
            return
        scaled = pixmap.scaled(900, 320, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.result_plot_label.setPixmap(scaled)

    def _populate_best_params(self, payload):
        if not hasattr(self, "best_params_table"):
            return
        fitted = payload.get("best_fit_parameters") if isinstance(payload, dict) else None
        physical = payload.get("physical_fit_parameters") if isinstance(payload, dict) else None
        fitted = fitted if isinstance(fitted, dict) else {}
        physical = physical if isinstance(physical, dict) else {}
        keys = sorted(set(fitted) | set(physical))
        self.best_params_table.setRowCount(0)
        if not keys:
            self._append_table_row(self.best_params_table, ["等待拟合结果", "-", "-", "-"])
            return
        for key in keys:
            self._append_table_row(
                self.best_params_table,
                [
                    PARAMETER_LABELS.get(key, key),
                    self._format_result_value(fitted.get(key, "-")),
                    self._format_result_value(physical.get(key, "-")),
                    PARAMETER_RECOMMENDED_RANGES.get(key, ""),
                ],
            )
        self.best_params_table.resizeRowsToContents()

    def _populate_result_files(self, files):
        if not hasattr(self, "result_files_table"):
            return
        self.result_files_table.setRowCount(0)
        if not files:
            self._append_table_row(self.result_files_table, ["等待拟合结果", "-", "-"])
            return
        for file_type, raw_path in files.items():
            resolved = self._resolve_result_path(raw_path)
            path_text = str(resolved or raw_path or "")
            status = "存在" if resolved and resolved.exists() else "缺失"
            self._append_table_row(self.result_files_table, [str(file_type), path_text, status])
        self.result_files_table.resizeRowsToContents()

    def _resolve_result_path(self, raw_path):
        if not raw_path:
            return None
        path = Path(str(raw_path)).expanduser()
        if path.is_absolute():
            return path
        candidates = []
        if self.last_runtime_dir:
            candidates.append((Path(self.last_runtime_dir) / path).resolve())
        candidates.extend([
            (self.project_root / path).resolve(),
            (self.history_root / path).resolve(),
        ])
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return candidates[0] if candidates else path

    def _append_table_row(self, table, values):
        row = table.rowCount()
        table.insertRow(row)
        for column, value in enumerate(values):
            table.setItem(row, column, QTableWidgetItem(str(value)))

    def _format_result_value(self, value):
        if value == "-":
            return "-"
        if isinstance(value, float):
            return f"{value:.12g}"
        if isinstance(value, (int, bool)):
            return str(value)
        return str(value)

    @staticmethod
    def _source_label(source):
        return {
            "final_ensemble_mean": "最终集合均值",
            "best_seen_member": "历史最优成员",
            "-": "-",
        }.get(str(source), str(source))

    @staticmethod
    def _well_mode_label(mode):
        labels = {value: label for label, value in WELL_CONTROL_OPTIONS}
        return labels.get(str(mode), str(mode))

    def _prepare_runtime_config(self, config, run_dir, history_path=None, case_dataset_path=None):
        runtime = copy.deepcopy(config)
        runtime["results_dir"] = "results"
        runtime["runs_dir"] = "members"
        if history_path is None:
            history_path = self._resolve_history_path(runtime.get("history_file", ""))
        runtime["history_file"] = str(Path(history_path).resolve())
        if case_dataset_path is None:
            raw_dataset_path = runtime.get("case_dataset_path", "")
            if raw_dataset_path:
                case_dataset_path = self._resolve_existing_or_template_path(raw_dataset_path)
        if case_dataset_path is not None:
            runtime["case_dataset_path"] = str(Path(case_dataset_path).resolve())
        runtime["build_release"] = str(self._resolve_template_path(runtime.get("build_release", "")))

        base_params = runtime.get("base_params") or {}
        for key in ("coord_file", "zcorn_file"):
            if base_params.get(key):
                base_params[key] = str(self._resolve_template_path(base_params[key]))
        runtime["base_params"] = base_params
        runtime["_ui_runtime"] = {
            "run_dir": str(run_dir),
            "generated_from": str(self.default_config_path),
            "generated_at": datetime.now().isoformat(timespec="seconds"),
        }
        return runtime

    def _resolve_history_path(self, raw_path):
        return self._resolve_existing_or_template_path(raw_path)

    def _resolve_template_path(self, raw_path):
        return self._resolve_existing_or_template_path(raw_path)

    def _resolve_existing_or_template_path(self, raw_path):
        path = Path(str(raw_path or "")).expanduser()
        if path.is_absolute():
            return path
        history_candidate = (self.history_root / path).resolve()
        if history_candidate.exists():
            return history_candidate
        project_candidate = (self.project_root / path).resolve()
        if project_candidate.exists():
            return project_candidate
        return history_candidate

    def _parse_alphas(self):
        raw = self.alphas_edit.text().replace(";", ",").split(",")
        values = []
        for item in raw:
            text = item.strip()
            if not text:
                continue
            values.append(float(text))
        if not values:
            raise ValueError("ES-MDA 膨胀系数不能为空。")
        return values

    def _parse_path(self, text):
        return [part.strip() for part in str(text).split(".") if part.strip()]

    def _row_checked(self, table, row):
        item = table.item(row, 0)
        return item is not None and item.checkState() == Qt.Checked

    def _table_text(self, table, row, column):
        item = table.item(row, column)
        return item.text().strip() if item is not None else ""

    def _table_float(self, table, row, column, default):
        text = self._table_text(table, row, column)
        if not text:
            return float(default)
        return float(text)

    @staticmethod
    def _combo_value(combo):
        if not isinstance(combo, QComboBox):
            return ""
        value = combo.currentData()
        return str(value if value is not None else combo.currentText())

    @staticmethod
    def _set_combo_value(combo, value):
        if not isinstance(combo, QComboBox):
            return
        index = combo.findData(value)
        if index < 0:
            index = combo.findText(str(value))
        if index >= 0:
            combo.setCurrentIndex(index)

    def _check_item(self, checked):
        item = QTableWidgetItem("")
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
        item.setCheckState(Qt.Checked if checked else Qt.Unchecked)
        return item

    def _coded_combo(self, options, current):
        combo = QComboBox()
        for label, value in options:
            combo.addItem(label, value)
        self._set_combo_value(combo, current)
        return combo

    def _spin(self, minimum, maximum, value):
        spin = QSpinBox()
        spin.setObjectName("parameterSpinBox")
        spin.setRange(int(minimum), int(maximum))
        spin.setValue(int(value))
        return spin

    def _double_spin(self, minimum, maximum, value, decimals):
        spin = QDoubleSpinBox()
        spin.setObjectName("parameterSpinBox")
        spin.setDecimals(decimals)
        spin.setRange(float(minimum), float(maximum))
        spin.setValue(float(value))
        spin.setSingleStep(1.0)
        return spin

    def _format_number(self, value):
        try:
            return f"{float(value):.12g}"
        except (TypeError, ValueError):
            return ""

    def set_project_context(self, project_state=None, result_store=None):
        if project_state is not None:
            self.project_state = project_state
        if result_store is not None:
            self.result_store = result_store
        if hasattr(self, "case_dataset_path_edit") and self._project_case_dataset_path():
            self._refresh_case_dataset_from_project()
        self._apply_active_case_best_parameters()

    def _apply_active_case_best_parameters(self):
        if not hasattr(self, "fit_table"):
            return
        case = (
            self.project_state.active_case()
            if self.project_state is not None
            and hasattr(self.project_state, "active_case") else None
        )
        if case is None:
            return
        default_values = {
            str(spec.get("name") or ""): spec.get("initial")
            for spec in (self.default_config.get("fit_parameters") or [])
        }
        overlay = (case.input_state.module_values or {}).get(
            "history_matching_best_parameters") or {}
        values = default_values
        values.update(dict(overlay.get("physical_fit_parameters") or {}))
        for row in range(self.fit_table.rowCount()):
            name = self._fit_parameter_key(row)
            if name in values:
                self.fit_table.setItem(
                    row, 3, QTableWidgetItem(
                        self._format_number(values[name])))

    def _history_run_manager(self):
        repository = (
            getattr(self.project_state, "artifact_repository", None)
            if self.project_state is not None else None
        )
        if repository is None:
            raise HistoryMatchingRunError(
                "The project artifact repository is not available")
        return HistoryMatchingRunManager(self.project_state, repository)

    def load_run_record(self, run_record):
        """Load one persisted history-matching Run without using global latest."""
        if run_record is None or run_record.run_type != RUN_TYPE_HISTORY_MATCHING:
            return False
        context = context_from_record(
            getattr(self.project_state, "project_id", ""), run_record)
        self._viewing_run_context = context
        self.last_runtime_dir = Path(context.run_dir) if context.run_dir else None
        self.last_runtime_config_path = (
            Path(context.config_path) if context.config_path else None)
        payload = None
        result_path = str((run_record.artifacts or {}).get("result_json") or "")
        if result_path and Path(result_path).is_file():
            try:
                payload = json.loads(Path(result_path).read_text(encoding="utf-8"))
                payload = self._payload_with_record_artifacts(
                    payload, run_record)
            except (OSError, json.JSONDecodeError) as exc:
                self._append_run_log(f"Failed to load history-matching result: {exc}")
        self.result_payload = payload
        status = str(run_record.status or "-")
        self.run_state_label.setText({
            "pending": "等待运行",
            "running": "运行中",
            "completed": "运行完成",
            "failed": "运行失败",
            "cancelled": "已停止",
        }.get(status, status))
        self.runtime_config_label.setText(
            f"运行配置: {context.config_path or '-'}")
        summary = dict(run_record.summary or {})
        ensemble_size = int(summary.get("ensemble_size") or 0)
        iteration_count = int(summary.get("iteration_count") or 0)
        total_runs = ensemble_size * iteration_count + 1 if ensemble_size and iteration_count else 0
        self._reset_progress_view(total_runs)
        progress = dict((run_record.summary or {}).get("progress") or {})
        if progress:
            iteration_index = int(progress.get("iteration", 0))
            member_index = int(progress.get("member", -1))
            self.round_member_label.setText(
                f"轮次：{iteration_index + 1} / {iteration_count or '-'}，"
                f"成员：{member_index + 1 if member_index >= 0 else '-'} / "
                f"{ensemble_size or '-'}")
            if member_index >= 0 and ensemble_size:
                self._progress_completed = min(
                    total_runs, iteration_index * ensemble_size + member_index + 1)
                self._update_progress_counts()
            if "objective" in progress:
                self.current_objective_label.setText(
                    f"当前误差：{float(progress['objective']):.6g}")
        if status == "completed" and total_runs:
            self._progress_completed = total_runs
            self._update_progress_counts()
            self.remaining_time_label.setText("预计剩余：已完成")
            if isinstance(payload, dict) and payload.get("objective") is not None:
                objective = float(payload["objective"])
                self.best_objective_label.setText(
                    f"当前全局最优误差：{objective:.6g}")
        self.business_log.clear()
        self._append_business_log(f"已加载历史拟合记录，状态：{self.run_state_label.text()}。")
        if payload:
            self._update_result_view(payload)
        else:
            self._reset_result_view()
        log_path = str((run_record.artifacts or {}).get("run_log") or "")
        if log_path and Path(log_path).is_file():
            try:
                self.run_log.setPlainText(
                    Path(log_path).read_text(encoding="utf-8", errors="replace"))
            except OSError:
                pass
        self.derive_case_button.setEnabled(
            run_record.status == "completed" and bool(payload))
        self.tabs.setCurrentIndex(3)
        return bool(payload)

    @staticmethod
    def _payload_with_record_artifacts(payload, run_record):
        payload = copy.deepcopy(payload or {})
        files = dict(payload.get("files") or {})
        artifacts = dict(getattr(run_record, "artifacts", {}) or {})
        for payload_key, artifact_key in (
            ("plot", "history_fit_plot"),
            ("best_fit_params", "best_fit_params"),
            ("best_fit_output", "best_fit_output"),
            ("summary", "best_fit_summary"),
            ("assimilation_summary", "assimilation_summary"),
        ):
            path = str(artifacts.get(artifact_key) or "")
            if path:
                files[payload_key] = path
        payload["files"] = files
        return payload

    def create_derived_case_from_best(self):
        context = self._viewing_run_context
        if context is None:
            self.status_label.setText("请先选择一个已完成的历史拟合 Run")
            return None
        try:
            derived = self._history_run_manager().create_derived_case(context)
        except (OSError, ValueError, HistoryMatchingRunError) as exc:
            self.status_label.setText(f"派生算例创建失败: {exc}")
            self._append_run_log(f"派生算例创建失败: {exc}")
            return None
        self.status_label.setText(
            f"已创建派生算例: {derived.case_name} ({derived.case_id})")
        self._append_run_log(
            f"Derived case created: {derived.case_name} ({derived.case_id})")
        self.derived_case_created.emit(derived.case_id)
        return derived

    def has_running_operation(self):
        for process in (self.process, self.target_process):
            if process is not None and process.state() != QProcess.NotRunning:
                return True
        return False

    def shutdown_operations(self, timeout_ms=5000):
        """Stop child processes and finalize their persistent Run state."""
        timeout_ms = max(0, int(timeout_ms or 0))
        context = self._active_run_context
        process = self.process
        if process is not None and process.state() != QProcess.NotRunning:
            self._stop_requested = True
            process.terminate()
            if not process.waitForFinished(timeout_ms):
                process.kill()
                process.waitForFinished(2000)
        if context is not None and self._active_run_context is not None:
            try:
                self._history_run_manager().mark_failed(
                    context,
                    "Project or workspace closed while history matching was running",
                    cancelled=True,
                )
                self.run_state_changed.emit(context.case_id, context.run_id)
            except (OSError, ValueError, HistoryMatchingRunError):
                pass
            self._active_run_context = None
        self.process = None

        target = self.target_process
        if target is not None and target.state() != QProcess.NotRunning:
            target.terminate()
            if not target.waitForFinished(timeout_ms):
                target.kill()
                target.waitForFinished(2000)
        self.target_process = None
        self._progress_timer.stop()
        self._set_process_running(False)
        self._set_target_process_running(False)
        return not self.has_running_operation()

    def set_context(self, title, detail, display_key=None):
        self.context_title = title or self.context_title
        self.context_detail = detail or self.context_detail
        if display_key:
            self.display_key = display_key
        self.title_label.setText(self.context_title)
        self.detail_label.setText(self.context_detail)

    def set_chart_data(self, chart_key, data):
        return

    def export_ui_state(self):
        return {
            "context_title": self.context_title,
            "context_detail": self.context_detail,
            "display_key": self.display_key,
        }

    def restore_ui_state(self, state):
        if not isinstance(state, dict):
            return
        self.set_context(
            state.get("context_title") or self.context_title,
            state.get("context_detail") or self.context_detail,
            state.get("display_key") or self.display_key,
        )
