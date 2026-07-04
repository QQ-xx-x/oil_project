# -*- coding: utf-8 -*-
"""History matching workspace page."""

import copy
import json
import re
import sys
from datetime import datetime
from pathlib import Path

from PyQt5.QtCore import QProcess, Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QFrame, QGridLayout,
    QGroupBox, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QPushButton,
    QScrollArea, QSpinBox, QTableWidget, QTableWidgetItem, QTabWidget,
    QTextEdit, QVBoxLayout, QWidget,
)


DEFAULT_CONFIG_NAME = "enkf_config.json"


class HistoryMatchingViewport(QWidget):
    """Workspace viewport for history matching setup and results."""

    FIT_COLUMNS = [
        "启用", "参数名", "参数路径", "初值", "下限", "上限", "变换", "扰动",
    ]
    OBS_COLUMNS = [
        "启用", "通道", "历史列", "模型键", "变换", "epsilon",
        "相对误差", "绝对误差", "权重",
    ]

    def __init__(self, project_state=None, result_store=None, parent=None):
        super().__init__(parent)
        self.project_state = project_state
        self.result_store = result_store
        self.context_title = "当前结果：历史拟合"
        self.context_detail = "编辑历史拟合参数、运行拟合流程，并查看拟合结果。"
        self.display_key = "history_matching"
        self.project_root = Path(__file__).resolve().parents[2]
        self.history_root = self.project_root / "history_matching"
        self.default_config_path = self.history_root / DEFAULT_CONFIG_NAME
        self.default_config = self._load_default_config()
        self.last_collected_config = None
        self.last_runtime_dir = None
        self.last_runtime_config_path = None
        self.process = None
        self.result_payload = None
        self._stdout_buffer = ""
        self._stderr_buffer = ""
        self._stop_requested = False
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
        self.tabs.addTab(self._scroll_page(self._result_placeholder_page()), "结果")
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

        group = QGroupBox("运行设置")
        group.setObjectName("parameterSection")
        form = QFormLayout(group)
        form.setLabelAlignment(Qt.AlignRight)

        self.history_file_edit = QLineEdit()
        self.history_file_edit.setObjectName("parameterPathEdit")
        self.simulation_days_spin = self._double_spin(0.0, 100000.0, 730.0, 2)
        self.ensemble_size_spin = self._spin(2, 10000, 24)
        self.alphas_edit = QLineEdit("4.0, 4.0, 4.0, 4.0")
        self.random_seed_spin = self._spin(0, 2147483647, 20260521)
        self.max_workers_spin = self._spin(1, 256, 1)
        self.reuse_outputs_check = QCheckBox("复用已有 member 输出")
        self.quiet_logs_check = QCheckBox("静默 member 日志")

        form.addRow("历史数据 CSV:", self.history_file_edit)
        form.addRow("模拟天数:", self.simulation_days_spin)
        form.addRow("集合规模:", self.ensemble_size_spin)
        form.addRow("Alpha 列表:", self.alphas_edit)
        form.addRow("随机种子:", self.random_seed_spin)
        form.addRow("最大并行数:", self.max_workers_spin)
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
        self.status_label = QLabel("已从默认历史拟合模板加载参数。")
        self.status_label.setObjectName("modulePreviewDescription")
        self.status_label.setWordWrap(True)
        action_layout.addWidget(self.collect_button)
        action_layout.addWidget(self.generate_config_button)
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
        self.well_mode_combo = QComboBox()
        self.well_mode_combo.addItems(["free", "fixed_bhp", "fixed_gas_rate", "fixed_water_rate"])
        self.well_bhp_spin = self._double_spin(0.0, 100000.0, 42.0, 4)
        self.fixed_rate_spin = self._double_spin(0.0, 1.0e12, 0.0, 4)
        self.rate_column_edit = QLineEdit()
        self.well_mode_combo.currentTextChanged.connect(self._sync_well_control_fields)
        grid.addWidget(QLabel("井控模式:"), 0, 0)
        grid.addWidget(self.well_mode_combo, 0, 1)
        grid.addWidget(QLabel("固定 BHP:"), 1, 0)
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
        note = QLabel("第一版支持编辑默认拟合参数。固定 BHP 模式下 well_bhp 自动不参与拟合。")
        note.setObjectName("modulePreviewDescription")
        note.setWordWrap(True)
        group_layout.addWidget(note)
        self.fit_table = QTableWidget(0, len(self.FIT_COLUMNS))
        self._setup_table(self.fit_table, self.FIT_COLUMNS)
        group_layout.addWidget(self.fit_table)
        layout.addWidget(group, 1)
        return page

    def _legacy_result_placeholder_page(self):
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
        controls_layout.addWidget(self.run_button)
        controls_layout.addWidget(self.stop_button)
        controls_layout.addStretch()
        layout.addWidget(controls)

        card = QFrame()
        card.setObjectName("modulePreviewCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        title = QLabel("运行状态")
        title.setObjectName("modulePreviewSubtitle")
        self.run_state_label = QLabel("未运行")
        self.run_state_label.setObjectName("modulePreviewDescription")
        self.progress_label = QLabel("iteration: -, member: -, objective: -")
        self.progress_label.setObjectName("modulePreviewDescription")
        self.runtime_config_label = QLabel("运行配置: -")
        self.runtime_config_label.setObjectName("modulePreviewDescription")
        self.runtime_config_label.setWordWrap(True)
        card_layout.addWidget(title)
        card_layout.addWidget(self.run_state_label)
        card_layout.addWidget(self.progress_label)
        card_layout.addWidget(self.runtime_config_label)
        layout.addWidget(card)

        log_group = QGroupBox("运行日志")
        log_group.setObjectName("parameterSection")
        log_layout = QVBoxLayout(log_group)
        self.run_log = QTextEdit()
        self.run_log.setReadOnly(True)
        self.run_log.setMinimumHeight(260)
        log_layout.addWidget(self.run_log)
        layout.addWidget(log_group, 1)
        return page

    def _result_placeholder_page(self):
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
        controls_layout.addWidget(self.run_button)
        controls_layout.addWidget(self.stop_button)
        controls_layout.addWidget(self.refresh_results_button)
        controls_layout.addStretch()
        layout.addWidget(controls)

        overview = QGroupBox("运行概览")
        overview.setObjectName("parameterSection")
        overview_layout = QGridLayout(overview)
        overview_layout.setColumnStretch(1, 1)
        overview_layout.setColumnStretch(3, 1)
        self.run_state_label = QLabel("未运行")
        self.run_state_label.setObjectName("modulePreviewDescription")
        self.progress_label = QLabel("iteration: -, member: -, objective: -")
        self.progress_label.setObjectName("modulePreviewDescription")
        self.result_objective_label = QLabel("-")
        self.result_objective_label.setObjectName("modulePreviewDescription")
        self.result_source_label = QLabel("-")
        self.result_source_label.setObjectName("modulePreviewDescription")
        self.result_mode_label = QLabel("-")
        self.result_mode_label.setObjectName("modulePreviewDescription")
        self.results_dir_label = QLabel("结果目录: -")
        self.results_dir_label.setObjectName("modulePreviewDescription")
        self.results_dir_label.setWordWrap(True)
        self.runtime_config_label = QLabel("运行配置: -")
        self.runtime_config_label.setObjectName("modulePreviewDescription")
        self.runtime_config_label.setWordWrap(True)
        overview_layout.addWidget(QLabel("运行状态:"), 0, 0)
        overview_layout.addWidget(self.run_state_label, 0, 1)
        overview_layout.addWidget(QLabel("最终 objective:"), 0, 2)
        overview_layout.addWidget(self.result_objective_label, 0, 3)
        overview_layout.addWidget(QLabel("当前进度:"), 1, 0)
        overview_layout.addWidget(self.progress_label, 1, 1)
        overview_layout.addWidget(QLabel("选择来源:"), 1, 2)
        overview_layout.addWidget(self.result_source_label, 1, 3)
        overview_layout.addWidget(QLabel("拟合模式:"), 2, 0)
        overview_layout.addWidget(self.result_mode_label, 2, 1)
        overview_layout.addWidget(self.results_dir_label, 3, 0, 1, 4)
        overview_layout.addWidget(self.runtime_config_label, 4, 0, 1, 4)
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
        self._setup_table(self.best_params_table, ["参数名", "拟合值", "物理值/显示值", "说明"])
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
        self.run_log = QTextEdit()
        self.run_log.setReadOnly(True)
        self.run_log.setMinimumHeight(220)
        log_layout.addWidget(self.run_log)
        layout.addWidget(log_group, 1)
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

    def _load_config_to_ui(self, config):
        enkf = config.get("enkf") or {}
        observation = config.get("observation") or {}
        well_control = config.get("well_control") or {}

        self.history_file_edit.setText(str(config.get("history_file", "")))
        self.simulation_days_spin.setValue(float(config.get("simulation_days", 0.0) or 0.0))
        self.ensemble_size_spin.setValue(int(enkf.get("ensemble_size", 24) or 24))
        self.alphas_edit.setText(", ".join(str(value) for value in enkf.get("alphas", [4.0, 4.0, 4.0, 4.0])))
        self.random_seed_spin.setValue(int(config.get("random_seed", 20260521) or 0))
        self.max_workers_spin.setValue(int(enkf.get("max_workers", 1) or 1))
        self.reuse_outputs_check.setChecked(bool(enkf.get("reuse_existing_outputs", True)))
        self.quiet_logs_check.setChecked(bool(enkf.get("quiet_member_logs", True)))

        self.well_mode_combo.setCurrentText(str(well_control.get("mode") or "free"))
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
            self.fit_table.setItem(row, 1, QTableWidgetItem(str(spec.get("name", ""))))
            self.fit_table.setItem(row, 2, QTableWidgetItem(".".join(spec.get("path", []))))
            self.fit_table.setItem(row, 3, QTableWidgetItem(self._format_number(spec.get("initial"))))
            self.fit_table.setItem(row, 4, QTableWidgetItem(self._format_number(spec.get("lower"))))
            self.fit_table.setItem(row, 5, QTableWidgetItem(self._format_number(spec.get("upper"))))
            self.fit_table.setCellWidget(row, 6, self._combo(["linear", "log"], spec.get("transform", "linear")))
            self.fit_table.setItem(row, 7, QTableWidgetItem(self._format_number(spec.get("perturb", 0.0))))
            self.fit_table.item(row, 1).setData(Qt.UserRole, copy.deepcopy(spec))
        self.fit_table.resizeRowsToContents()

    def _populate_observation_table(self, channels):
        self.observation_table.setRowCount(0)
        for channel in channels:
            row = self.observation_table.rowCount()
            self.observation_table.insertRow(row)
            self.observation_table.setItem(row, 0, self._check_item(True))
            self.observation_table.setItem(row, 1, QTableWidgetItem(str(channel.get("name", ""))))
            self.observation_table.setItem(row, 2, QTableWidgetItem(str(channel.get("column", ""))))
            self.observation_table.setItem(row, 3, QTableWidgetItem(str(channel.get("model_key", ""))))
            self.observation_table.setCellWidget(row, 4, self._combo(["linear", "log"], channel.get("transform", "linear")))
            self.observation_table.setItem(row, 5, QTableWidgetItem(self._format_number(channel.get("epsilon", 0.0))))
            self.observation_table.setItem(row, 6, QTableWidgetItem(self._format_number(channel.get("relative_error", 0.0))))
            self.observation_table.setItem(row, 7, QTableWidgetItem(self._format_number(channel.get("absolute_error", 0.0))))
            self.observation_table.setItem(row, 8, QTableWidgetItem(self._format_number(channel.get("weight", 1.0))))
        self.observation_table.resizeRowsToContents()

    def _sync_well_control_fields(self):
        mode = self.well_mode_combo.currentText()
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
            if name_item.text() != "well_bhp":
                continue
            if mode == "fixed_bhp":
                enabled_item.setCheckState(Qt.Unchecked)
                enabled_item.setFlags(enabled_item.flags() & ~Qt.ItemIsEnabled)
            else:
                enabled_item.setFlags(enabled_item.flags() | Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)

    def collect_runtime_config(self):
        config = copy.deepcopy(self.default_config)
        config["history_file"] = self.history_file_edit.text().strip()
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
        self.last_collected_config = config
        return config

    def _collect_well_control(self):
        mode = self.well_mode_combo.currentText()
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
                "name": self._table_text(self.observation_table, row, 1),
                "column": self._table_text(self.observation_table, row, 2),
                "model_key": self._table_text(self.observation_table, row, 3),
                "transform": self._combo_text(self.observation_table, row, 4),
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
            name = self._table_text(self.fit_table, row, 1)
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
                "transform": self._combo_text(self.fit_table, row, 6),
                "perturb": self._table_float(self.fit_table, row, 7, 0.0),
            }
            if original.get("dependent"):
                spec["dependent"] = copy.deepcopy(original["dependent"])
            parameters.append(spec)
        return parameters

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
            config_path = self.generate_runtime_config_file()
        except (OSError, ValueError) as exc:
            self.status_label.setText(f"生成运行配置失败：{exc}")
            return
        self.status_label.setText(f"运行配置已生成：{config_path}")

    def generate_runtime_config_file(self):
        config = self.collect_runtime_config()
        run_dir = self._new_runtime_dir()
        run_dir.mkdir(parents=True, exist_ok=False)
        config = self._prepare_runtime_config(config, run_dir)
        config_path = run_dir / "enkf_runtime_config.json"
        config_path.write_text(
            json.dumps(config, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self.last_runtime_dir = run_dir
        self.last_runtime_config_path = config_path
        self.last_collected_config = config
        return config_path

    def start_history_matching(self):
        if self.process is not None and self.process.state() != QProcess.NotRunning:
            self._append_run_log("历史拟合已经在运行。")
            return

        try:
            config_path = self.generate_runtime_config_file()
        except (OSError, ValueError) as exc:
            self.run_state_label.setText(f"启动失败：{exc}")
            self._append_run_log(f"启动失败：{exc}")
            return

        self.result_payload = None
        self._stdout_buffer = ""
        self._stderr_buffer = ""
        self._stop_requested = False
        self.run_log.clear()
        self._reset_result_view()
        self.run_state_label.setText("运行中")
        self.progress_label.setText("iteration: -, member: -, objective: -")
        self.runtime_config_label.setText(f"运行配置: {config_path}")

        script_path = self.history_root / "run_enkf_history_match.py"
        self.process = QProcess(self)
        self.process.setProgram(sys.executable)
        self.process.setArguments([str(script_path), "--config", str(config_path)])
        self.process.setWorkingDirectory(str(self.history_root))
        self.process.readyReadStandardOutput.connect(self._handle_process_stdout)
        self.process.readyReadStandardError.connect(self._handle_process_stderr)
        self.process.errorOccurred.connect(self._handle_process_error)
        self.process.finished.connect(self._handle_process_finished)
        self._set_process_running(True)
        self._append_run_log(f"启动命令: {sys.executable} {script_path} --config {config_path}")
        self.process.start()

    def stop_history_matching(self):
        if self.process is None or self.process.state() == QProcess.NotRunning:
            return
        self._append_run_log("请求停止历史拟合进程。")
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
        member_match = re.search(
            r"iteration=(\d+)\s+member=(\d+)\s+objective=([0-9.eE+-]+)",
            line,
        )
        if member_match:
            iteration, member, objective = member_match.groups()
            self.progress_label.setText(
                f"iteration: {iteration}, member: {member}, objective: {objective}"
            )
            return

        summary_match = re.search(
            r"iteration=(\d+)\s+objective_min=([0-9.eE+-]+)\s+"
            r"objective_mean=([0-9.eE+-]+)\s+objective_max=([0-9.eE+-]+)",
            line,
        )
        if summary_match:
            iteration, minimum, mean, maximum = summary_match.groups()
            self.progress_label.setText(
                f"iteration: {iteration}, objective min/mean/max: {minimum} / {mean} / {maximum}"
            )
            return

        if line.startswith("best_fit_objective="):
            value = line.split("=", 1)[1].strip()
            self.progress_label.setText(f"best objective: {value}")
            return

        if line.startswith("best_fit_selected_source="):
            source = line.split("=", 1)[1].strip()
            self.run_state_label.setText(f"已选择拟合结果: {source}")
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
            f"mode: {mode}, source: {selected_source}, objective: {objective}"
        )
        self._update_result_view(payload)

    def _handle_process_error(self, error):
        self.run_state_label.setText(f"进程错误: {error}")
        self._append_run_log(f"进程错误: {error}")
        if self.process is None or self.process.state() == QProcess.NotRunning:
            self._set_process_running(False)
            self.process = None

    def _handle_process_finished(self, exit_code, exit_status):
        self._flush_process_buffers()
        if self._stop_requested:
            self.run_state_label.setText("已停止")
        elif exit_code == 0:
            if self.result_payload:
                self.run_state_label.setText("运行完成，结果已解析")
            else:
                self.run_state_label.setText("运行完成")
        else:
            self.run_state_label.setText(f"运行失败，退出码: {exit_code}")
        self._append_run_log(f"进程结束: exit_code={exit_code}, exit_status={exit_status}")
        self._set_process_running(False)
        self.process = None

    def _set_process_running(self, running):
        self.run_button.setEnabled(not running)
        self.stop_button.setEnabled(running)
        self.generate_config_button.setEnabled(not running)
        self.collect_button.setEnabled(not running)

    def _append_run_log(self, text):
        if not hasattr(self, "run_log"):
            return
        self.run_log.append(str(text))
        self.run_log.ensureCursorVisible()

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
        self.result_objective_label.setText("-")
        self.result_source_label.setText("-")
        self.result_mode_label.setText("-")
        self.results_dir_label.setText("结果目录: -")
        self.runtime_config_label.setText("运行配置: -")
        self._set_result_plot(None)
        self._populate_best_params({})
        self._populate_result_files({})

    def _update_result_view(self, payload):
        if not isinstance(payload, dict):
            payload = {}
        self.result_objective_label.setText(str(payload.get("objective", "-")))
        self.result_source_label.setText(str(payload.get("selected_source", "-")))
        self.result_mode_label.setText(str(payload.get("mode", "-")))

        files = dict(payload.get("files") or {})
        if not files:
            files = self._expected_result_files()
        results_dir = self._infer_results_dir(files)
        self.results_dir_label.setText(f"结果目录: {results_dir or '-'}")
        self._set_result_plot(files.get("plot"))
        self._populate_best_params(payload)
        self._populate_result_files(files)

    def _load_latest_result_payload(self):
        candidates = []
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
            return {}
        results_dir = Path(self.last_runtime_dir) / "results"
        return {
            "plot": str(results_dir / "history_fit_gas_water.png"),
            "best_fit_params": str(results_dir / "best_fit_params.json"),
            "best_fit_output": str(results_dir / "best_fit_output.csv"),
            "summary": str(results_dir / "best_fit_summary.json"),
            "assimilation_summary": str(results_dir / "assimilation_summary.csv"),
        }

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
                    key,
                    self._format_result_value(fitted.get(key, "-")),
                    self._format_result_value(physical.get(key, "-")),
                    "",
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

    def _new_runtime_dir(self):
        base_dir = self.history_root / "ui_runs"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        candidate = base_dir / f"run_{timestamp}"
        suffix = 1
        while candidate.exists():
            candidate = base_dir / f"run_{timestamp}_{suffix:02d}"
            suffix += 1
        return candidate

    def _prepare_runtime_config(self, config, run_dir):
        runtime = copy.deepcopy(config)
        runtime["results_dir"] = "results"
        runtime["runs_dir"] = "members"
        runtime["history_file"] = str(self._resolve_history_path(runtime.get("history_file", "")))
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
            raise ValueError("Alpha 列表不能为空。")
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

    def _combo_text(self, table, row, column):
        widget = table.cellWidget(row, column)
        if isinstance(widget, QComboBox):
            return widget.currentText()
        return self._table_text(table, row, column)

    def _check_item(self, checked):
        item = QTableWidgetItem("")
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
        item.setCheckState(Qt.Checked if checked else Qt.Unchecked)
        return item

    def _combo(self, values, current):
        combo = QComboBox()
        combo.addItems(values)
        if current in values:
            combo.setCurrentText(current)
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
