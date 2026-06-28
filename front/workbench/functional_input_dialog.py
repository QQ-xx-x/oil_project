# -*- coding: utf-8 -*-
"""Functional input module editor dialog."""

from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFrame, QGridLayout, QHeaderView, QHBoxLayout,
    QLabel, QListWidget, QListWidgetItem, QPlainTextEdit, QPushButton,
    QScrollArea, QSplitter, QStackedWidget, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from .case_data_panel import CaseDataPanel
from .chart_adapters import build_gas_pvt_curve_data, build_relative_permeability_data
from .case_config_sync import apply_module_values_to_case_data
from .input_data_model import InputDataModel
from .parameter_panels import (
    WorkbenchDualPorosityPanel, WorkbenchGasPvtPanel, WorkbenchGridPanel,
    WorkbenchHydraulicFracturesPanel, WorkbenchInitialStatePanel,
    WorkbenchMatrixPanel, WorkbenchNaturalFracturesPanel,
    WorkbenchOilWaterPanel, WorkbenchSimulationPanel, WorkbenchWellPanel,
)
from .production_curve_panel import ProductionCurvePanel
from .viewport_placeholders import ChartViewport


PANEL_FACTORIES = {
    "grid_basic": WorkbenchGridPanel,
    "initial_state": WorkbenchInitialStatePanel,
    "matrix_properties": WorkbenchMatrixPanel,
    "dual_porosity": WorkbenchDualPorosityPanel,
    "simulation_control": WorkbenchSimulationPanel,
    "oil_water_properties": WorkbenchOilWaterPanel,
    "gas_pvt": WorkbenchGasPvtPanel,
    "well_parameters": WorkbenchWellPanel,
    "natural_fractures": WorkbenchNaturalFracturesPanel,
    "hydraulic_fractures": WorkbenchHydraulicFracturesPanel,
}


class FunctionalInputDialog(QDialog):
    """A Harmony-style functional editor for one input module."""

    values_applied = pyqtSignal(str, str, dict)
    case_data_saved = pyqtSignal()
    case_dataset_built = pyqtSignal(str, dict)
    result_requested = pyqtSignal(str)

    def __init__(self, module_schema, project_state, initial_child_key=None, parent=None):
        super().__init__(parent)
        self.module_schema = module_schema
        self.project_state = project_state
        self.data_model = InputDataModel(project_state)
        self.values_were_applied = False
        self._pages = []
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(120)
        self._preview_timer.timeout.connect(self._refresh_preview)

        self.setObjectName("functionalInputDialog")
        self.setWindowTitle(f"{module_schema.get('title', '输入')} 参数设置")
        self.resize(1280, 720)

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        splitter = QSplitter(Qt.Horizontal)
        self.nav = QListWidget()
        self.nav.setObjectName("functionalInputNav")
        self.nav.currentRowChanged.connect(self._show_page)
        splitter.addWidget(self.nav)

        self.stack = QStackedWidget()
        splitter.addWidget(self.stack)

        self.preview_panel = ModulePreviewPanel(module_schema, project_state, self)
        self.preview_panel.result_requested.connect(self.result_requested.emit)
        splitter.addWidget(self.preview_panel)
        splitter.setSizes([190, 650, 440])
        root.addWidget(splitter, 1)

        self._build_pages(initial_child_key)
        for page in self._pages:
            page.values_changed.connect(self._schedule_preview_refresh)
        self._refresh_preview()

        buttons = QDialogButtonBox()
        apply_button = QPushButton("应用")
        ok_button = QPushButton("确定")
        cancel_button = QPushButton("取消")
        buttons.addButton(apply_button, QDialogButtonBox.ApplyRole)
        buttons.addButton(ok_button, QDialogButtonBox.AcceptRole)
        buttons.addButton(cancel_button, QDialogButtonBox.RejectRole)
        apply_button.clicked.connect(self.apply_values)
        ok_button.clicked.connect(self._accept_with_apply)
        cancel_button.clicked.connect(self.reject)
        root.addWidget(buttons)

    def _build_pages(self, initial_child_key):
        children = self.module_schema.get("children", []) or []
        if self.module_schema.get("special") == "case_data":
            children = [{
                "key": "case_data_manifest",
                "title": "CaseData 文件与 Dataset",
                "items": [],
                "page": "case_manifest",
            }] + children

        initial_row = 0
        for index, child in enumerate(children):
            item = QListWidgetItem(child.get("title", child.get("key", "")))
            item.setData(Qt.UserRole, child.get("key", ""))
            self.nav.addItem(item)
            page = FunctionalGroupPage(
                self.module_schema, child, self.project_state, self.data_model, self)
            self._pages.append(page)
            self.stack.addWidget(page)
            if initial_child_key and child.get("key") == initial_child_key:
                initial_row = index
        if self.nav.count():
            self.nav.setCurrentRow(initial_row)

    def _show_page(self, index):
        if 0 <= index < self.stack.count():
            self.stack.setCurrentIndex(index)

    def apply_values(self):
        changed = {}
        for page in self._pages:
            for module_key, values in page.collect_values().items():
                self.project_state.set_module_values(module_key, values)
                if apply_module_values_to_case_data(self.project_state, module_key, values):
                    self.project_state.mark_case_dataset_stale()
                changed[module_key] = values
                self.values_applied.emit(module_key, page.title(), dict(values))
        if changed:
            self.values_were_applied = True

    def _accept_with_apply(self):
        self.apply_values()
        self.accept()

    def _schedule_preview_refresh(self):
        self._preview_timer.start()

    def _refresh_preview(self):
        overrides = {}
        for page in self._pages:
            for module_key, values in page.collect_values().items():
                overrides[module_key] = dict(values)
        self.preview_panel.update_preview(overrides)


class FunctionalGroupPage(QWidget):
    values_changed = pyqtSignal()

    def __init__(self, module_schema, child_schema, project_state, data_model,
                 dialog, parent=None):
        super().__init__(parent)
        self.module_schema = module_schema
        self.child_schema = child_schema
        self.project_state = project_state
        self.data_model = data_model
        self.dialog = dialog
        self._panels = {}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        holder = QWidget()
        self.layout = QVBoxLayout(holder)
        self.layout.setContentsMargins(14, 12, 14, 12)
        self.layout.setSpacing(10)
        scroll.setWidget(holder)
        outer.addWidget(scroll)

        self._build()
        self.layout.addStretch()

    def title(self):
        return self.child_schema.get("title", self.child_schema.get("key", ""))

    def collect_values(self):
        values = {}
        for module_key, panel in self._panels.items():
            if hasattr(panel, "get_values"):
                values[module_key] = panel.get_values()
        return values

    def _build(self):
        self.layout.addWidget(self._intro())
        page_type = self.child_schema.get("page", "summary")
        if page_type == "case_manifest":
            self._add_case_data_panel()
            return
        self._add_source_table()
        self._add_edit_panels()
        if page_type == "overview":
            self._add_overview()
        elif page_type == "files":
            self._add_file_table()
        elif page_type == "arrays":
            self._add_array_tables()
        elif page_type == "dfn":
            self._add_dfn_tables()
        elif page_type == "case":
            self._add_case_table()
        self._add_validation_notes()

    def _intro(self):
        box = QFrame()
        box.setObjectName("parameterIntro")
        layout = QVBoxLayout(box)
        layout.setContentsMargins(12, 10, 12, 10)
        title = QLabel(self.title())
        title.setObjectName("parameterTitle")
        desc = QLabel(
            f"{self.module_schema.get('title', '')} / {self.title()}。"
            "本页按功能展示当前工程已有输入、CaseData 引用和派生数据摘要。")
        desc.setObjectName("parameterDescription")
        desc.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(desc)
        return box

    def _add_case_data_panel(self):
        panel = CaseDataPanel(self.project_state)
        panel.case_data_saved.connect(self.dialog.case_data_saved.emit)
        panel.case_dataset_built.connect(self.dialog.case_dataset_built.emit)
        self.layout.addWidget(panel)

    def _add_source_table(self):
        items = self.child_schema.get("items", []) or []
        if not items:
            return
        table = self._table(["名称", "来源", "值 / 摘要", "状态"], len(items))
        for row, item in enumerate(items):
            table.setItem(row, 0, self._cell(item.get("title", item.get("key", ""))))
            table.setItem(row, 1, self._cell(self._source_label(item)))
            table.setItem(row, 2, self._cell(self._format_value(self.data_model.item_value(item))))
            table.setItem(row, 3, self._cell(self.data_model.item_status(item)))
        self.layout.addWidget(self._section("字段来源", table))

    def _add_edit_panels(self):
        modules = []
        for item in self.child_schema.get("items", []) or []:
            if item.get("source") == "ui":
                module_key = item.get("module")
                if module_key and module_key not in modules and module_key in PANEL_FACTORIES:
                    modules.append(module_key)
        for module_key in modules:
            panel = PANEL_FACTORIES[module_key]()
            self._restore_panel_values(panel, module_key)
            self._connect_panel_change_signals(panel)
            self._panels[module_key] = panel
            self.layout.addWidget(self._section(f"可编辑参数：{module_key}", panel))

    def _connect_panel_change_signals(self, panel):
        for widget in panel.findChildren(QWidget):
            for signal_name in (
                "valueChanged", "textChanged", "toggled", "stateChanged",
                "currentIndexChanged",
            ):
                signal = getattr(widget, signal_name, None)
                if signal is None:
                    continue
                try:
                    signal.connect(lambda *args: self.values_changed.emit())
                except (TypeError, RuntimeError):
                    pass

    def _add_overview(self):
        summary = [
            ("CaseData 文件", self.data_model.project_value("case_data_path")),
            ("Dataset 目录", self.data_model.dataset_dir()),
            ("Dataset 状态", "已生成" if self.data_model.dataset_exists() else "未生成"),
            ("CaseData section 数", len(self.data_model.case_sections())),
            ("文件引用数", len(self.data_model.file_records())),
        ]
        table = self._table(["项目", "值"], len(summary))
        for row, (name, value) in enumerate(summary):
            table.setItem(row, 0, self._cell(name))
            table.setItem(row, 1, self._cell(self._format_value(value)))
        self.layout.addWidget(self._section("输入总览", table))

    def _add_file_table(self):
        records = self.data_model.file_records()
        table = self._table(["Section", "Key", "路径", "状态", "行号"], len(records))
        for row, record in enumerate(records):
            table.setItem(row, 0, self._cell(record["section"]))
            table.setItem(row, 1, self._cell(record["key"]))
            table.setItem(row, 2, self._cell(record["path"]))
            table.setItem(row, 3, self._cell("存在" if record["exists"] else "缺失"))
            table.setItem(row, 4, self._cell(record["line"]))
        self.layout.addWidget(self._section("CaseData 文件引用", table))

    def _add_array_tables(self):
        array_items = [
            item for item in self.child_schema.get("items", []) or []
            if item.get("source") == "array"
        ]
        table = self._table(["数组", "状态", "形状", "类型", "数量", "最小值", "最大值", "均值"],
                            len(array_items))
        for row, item in enumerate(array_items):
            summary = self.data_model.array_summary(item.get("key", ""))
            table.setItem(row, 0, self._cell(item.get("title", item.get("key", ""))))
            table.setItem(row, 1, self._cell(summary.get("status", "")))
            table.setItem(row, 2, self._cell(summary.get("shape", "")))
            table.setItem(row, 3, self._cell(summary.get("dtype", "")))
            table.setItem(row, 4, self._cell(summary.get("count", "")))
            table.setItem(row, 5, self._cell(summary.get("min", "")))
            table.setItem(row, 6, self._cell(summary.get("max", "")))
            table.setItem(row, 7, self._cell(summary.get("mean", "")))
        self.layout.addWidget(self._section("数组摘要", table))

        preview = QPlainTextEdit()
        preview.setReadOnly(True)
        lines = []
        for item in array_items:
            key = item.get("key", "")
            values = self.data_model.array_preview(key, limit=24)
            if values:
                lines.append(f"[{key}] 前 {len(values)} 个值:")
                lines.append(", ".join(str(value) for value in values))
                lines.append("")
        preview.setPlainText("\n".join(lines) if lines else "当前没有可预览数组。")
        preview.setMinimumHeight(150)
        self.layout.addWidget(self._section("数组预览", preview))

    def _add_dfn_tables(self):
        summary = self.data_model.dfn_summary()
        rows = list(summary.items())
        table = self._table(["项目", "值"], len(rows))
        for row, (key, value) in enumerate(rows):
            table.setItem(row, 0, self._cell(key))
            table.setItem(row, 1, self._cell(self._format_value(value)))
        self.layout.addWidget(self._section("DFN 摘要", table))

        fractures = self.data_model.dfn_fractures(limit=200)
        frac_table = self._table(
            ["ID", "顶点数", "Set", "渗透率", "压缩系数", "开度"], len(fractures))
        for row, frac in enumerate(fractures):
            frac_table.setItem(row, 0, self._cell(frac.get("fracture_id", "")))
            frac_table.setItem(row, 1, self._cell(frac.get("vertex_count", "")))
            frac_table.setItem(row, 2, self._cell(frac.get("set_id", "")))
            frac_table.setItem(row, 3, self._cell(frac.get("permeability", "")))
            frac_table.setItem(row, 4, self._cell(frac.get("compressibility", "")))
            frac_table.setItem(row, 5, self._cell(frac.get("aperture", "")))
        self.layout.addWidget(self._section("裂缝表（前 200 条）", frac_table))

    def _add_case_table(self):
        rows = []
        for item in self.child_schema.get("items", []) or []:
            if item.get("source") != "case":
                continue
            keyword = self.data_model.case_keyword(item.get("section", ""), item.get("key", ""))
            rows.append((item, keyword))
        table = self._table(["Section", "Key", "Value", "类型", "状态"], len(rows))
        for row, (item, keyword) in enumerate(rows):
            table.setItem(row, 0, self._cell(item.get("section", "")))
            table.setItem(row, 1, self._cell(item.get("key", "")))
            table.setItem(row, 2, self._cell(keyword.get("raw_value", "") if keyword else ""))
            table.setItem(row, 3, self._cell(keyword.get("value_type", "") if keyword else ""))
            table.setItem(row, 4, self._cell(self.data_model.item_status(item)))
        self.layout.addWidget(self._section("CaseData 参数", table))

    def _add_validation_notes(self):
        items = self.data_model.validation_items()
        errors = self.data_model.load_errors()
        if not items and not errors:
            return
        text = QPlainTextEdit()
        text.setReadOnly(True)
        lines = []
        for item in items:
            lines.append(f"[{item['level']}] {item['message']}")
        for name, message in errors.items():
            lines.append(f"[load] {name}: {message}")
        text.setPlainText("\n".join(lines))
        text.setMinimumHeight(120)
        self.layout.addWidget(self._section("校验与读取信息", text))

    def _section(self, title, widget):
        frame = QFrame()
        frame.setObjectName("parameterSectionFrame")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        label = QLabel(title)
        label.setObjectName("parameterTitle")
        label.setStyleSheet("font-size: 13px;")
        layout.addWidget(label)
        layout.addWidget(widget)
        return frame

    def _table(self, headers, rows):
        table = QTableWidget(rows, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        table.horizontalHeader().setStretchLastSection(True)
        table.setMinimumHeight(min(300, max(120, 34 + rows * 26)))
        return table

    def _cell(self, value):
        item = QTableWidgetItem(self._format_value(value))
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        return item

    def _source_label(self, item):
        source = item.get("source", "")
        if source == "ui":
            return f"UI:{item.get('module', '')}.{item.get('key', '')}"
        if source == "case":
            return f"CaseData:[{item.get('section', '')}].{item.get('key', '')}"
        if source == "config":
            return f"config:{item.get('group', '')}.{item.get('key', '')}"
        if source == "array":
            return f"arrays.npz:{item.get('key', '')}"
        if source == "dfn":
            return f"dfn.json:{item.get('key', '')}"
        if source == "validation":
            return f"validation.json:{item.get('key', '')}"
        if source == "project":
            return f"project_state:{item.get('key', '')}"
        return source

    def _format_value(self, value):
        if value is None:
            return ""
        if isinstance(value, float):
            return f"{value:.6g}"
        if isinstance(value, (list, tuple)):
            return ", ".join(str(part) for part in value)
        return str(value)

    def _restore_panel_values(self, panel, module_key):
        values = self.project_state.get_module_values(module_key)
        if not values:
            return
        attr_overrides = {
            "enable_dual_porosity": "check_enable",
            "k_fracture_x": "spin_k_fx",
            "k_fracture_y": "spin_k_fy",
            "k_fracture_z": "spin_k_fz",
            "matrix_volume_fraction": "spin_matrix_vol_frac",
            "fracture_volume_fraction": "spin_fracture_vol_frac",
            "wr_shape_factor": "spin_wr_shape_factor",
            "gas_Mg": "spin_gas_mg",
            "gas_Tc": "spin_gas_tc",
            "gas_Pc_bar": "spin_gas_pc_bar",
            "gas_table_Pmin_bar": "spin_gas_table_pmin_bar",
            "gas_table_Pmax_bar": "spin_gas_table_pmax_bar",
            "x": "spin_well_x",
            "y": "spin_well_y",
            "z": "spin_well_z",
            "pressure": "spin_well_pressure",
            "radius": "spin_well_radius",
            "WI": "spin_well_WI",
            "grdecl_file": "edit_grdecl_file",
            "coord_file": "edit_coord_file",
            "zcorn_file": "edit_zcorn_file",
            "enable_lgr": "check_enable_lgr",
            "d_threshold": "spin_d_threshold",
        }
        lower_attrs = {name.lower(): name for name in dir(panel)}
        for key, value in values.items():
            candidates = [attr_overrides.get(key), f"spin_{key}", f"check_{key}", key]
            target = None
            for candidate in candidates:
                if not candidate:
                    continue
                attr_name = lower_attrs.get(candidate.lower())
                if attr_name:
                    target = getattr(panel, attr_name)
                    break
            if target is None:
                continue
            if isinstance(value, bool) and hasattr(target, "setChecked"):
                target.setChecked(value)
            elif hasattr(target, "setValue"):
                target.setValue(value)
            elif hasattr(target, "setText"):
                target.setText(str(value))


class PreviewProjectState:
    def __init__(self, base_state, overrides):
        self._base_state = base_state
        self._overrides = overrides or {}

    def get_module_values(self, module_key):
        values = {}
        if self._base_state is not None:
            values.update(self._base_state.get_module_values(module_key) or {})
        values.update(self._overrides.get(module_key, {}) or {})
        return values

    def __getattr__(self, name):
        return getattr(self._base_state, name)


class ModulePreviewPanel(QFrame):
    result_requested = pyqtSignal(str)

    def __init__(self, module_schema, project_state, parent=None):
        super().__init__(parent)
        self.module_schema = module_schema
        self.project_state = project_state
        self.data_model = InputDataModel(project_state)
        self.setObjectName("modulePreviewPanel")
        self.setMinimumWidth(400)
        self.setMaximumWidth(520)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        title = QLabel("预览")
        title.setObjectName("modulePreviewTitle")
        layout.addWidget(title)

        desc = QLabel("参数修改后，右侧曲线或摘要会自动刷新；3D 场仍在主工作区查看。")
        desc.setObjectName("modulePreviewDescription")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        self.content = QFrame()
        self.content.setObjectName("modulePreviewContent")
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(8)
        layout.addWidget(self.content, 1)

        self.actions = QFrame()
        self.actions.setObjectName("modulePreviewActions")
        self.actions_layout = QVBoxLayout(self.actions)
        self.actions_layout.setContentsMargins(0, 0, 0, 0)
        self.actions_layout.setSpacing(5)
        layout.addWidget(self.actions)
        layout.addStretch()

    def update_preview(self, overrides):
        self._clear_layout(self.content_layout)
        self._clear_layout(self.actions_layout)
        proxy = PreviewProjectState(self.project_state, overrides)
        module_key = self.module_schema.get("key", "")
        if module_key == "fluid_pvt_inputs":
            self._add_fluid_preview(proxy)
        elif module_key == "well_production":
            self._add_well_production_preview(proxy)
        elif module_key == "rock_properties":
            self._add_rock_summary(proxy)
        elif module_key == "grid_spatial":
            self._add_grid_summary(proxy)
        elif module_key == "fracture_system_inputs":
            self._add_fracture_summary(proxy)
        elif module_key == "solver_output":
            self._add_solver_summary(proxy)
        elif module_key == "initial_conditions":
            self._add_initial_summary(proxy)
        else:
            self._add_overview_summary()
        self._add_result_actions()

    def _add_fluid_preview(self, proxy):
        charts = []
        try:
            charts.append((
                "relative_permeability_curve",
                build_relative_permeability_data(proxy),
                "相对渗透率",
            ))
        except Exception as exc:
            self._add_message("相对渗透率预览不可用", str(exc))
        try:
            charts.append(("pvt_curve", build_gas_pvt_curve_data(proxy), "PVT 曲线"))
        except Exception as exc:
            self._add_message("PVT 预览不可用", str(exc))
        if charts:
            self._add_chart_switcher(charts)

    def _add_well_production_preview(self, proxy):
        production_panel = ProductionCurvePanel(compact=True)
        production_panel.setMinimumHeight(430)
        production_panel.load_from_project(proxy, self._nearest_result_store())
        blasingame = self._chart_widget(
            "blasingame_curve", None, "Blasingame 预览")
        self._add_widget_switcher([
            ("production_curve", production_panel, "生产曲线预览"),
            ("blasingame_curve", blasingame, "Blasingame 预览"),
        ])

    def _add_widget_switcher(self, widgets):
        frame = QFrame()
        frame.setObjectName("modulePreviewChartFrame")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(6)
        label = QLabel("曲线预览")
        label.setObjectName("modulePreviewSubtitle")
        header.addWidget(label)
        header.addStretch()

        stack = QStackedWidget()
        if len(widgets) > 1:
            selector = QComboBox()
            selector.setObjectName("modulePreviewChartSelector")
            for key, widget, title in widgets:
                selector.addItem(title, key)
            selector.currentIndexChanged.connect(stack.setCurrentIndex)
            header.addWidget(selector)
        layout.addLayout(header)

        for key, widget, title in widgets:
            stack.addWidget(widget)
        layout.addWidget(stack, 1)
        self.content_layout.addWidget(frame, 1)

    def _add_chart_switcher(self, charts):
        frame = QFrame()
        frame.setObjectName("modulePreviewChartFrame")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(6)
        label = QLabel("曲线预览")
        label.setObjectName("modulePreviewSubtitle")
        header.addWidget(label)
        header.addStretch()

        stack = QStackedWidget()
        if len(charts) > 1:
            selector = QComboBox()
            selector.setObjectName("modulePreviewChartSelector")
            for key, data, title in charts:
                selector.addItem(title, key)
            selector.currentIndexChanged.connect(stack.setCurrentIndex)
            header.addWidget(selector)
        layout.addLayout(header)

        for key, data, title in charts:
            stack.addWidget(self._chart_widget(key, data, title))
        layout.addWidget(stack, 1)
        self.content_layout.addWidget(frame, 1)

    def _add_chart(self, key, data, title):
        frame = QFrame()
        frame.setObjectName("modulePreviewChartFrame")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(4)
        label = QLabel(title)
        label.setObjectName("modulePreviewSubtitle")
        layout.addWidget(label)
        layout.addWidget(self._chart_widget(key, data, title), 1)
        self.content_layout.addWidget(frame)

    def _chart_widget(self, key, data, title):
        chart = ChartViewport()
        chart.setMinimumHeight(430)
        chart.set_context(title, "", key)
        if data:
            chart.set_chart_data(key, data)
        return chart

    def _add_rock_summary(self, proxy):
        values = proxy.get_module_values("matrix_properties")
        self._add_cards([
            ("孔隙度", values.get("porosity", "")),
            ("Kx", values.get("perm_x", "")),
            ("Ky", values.get("perm_y", "")),
            ("Kz", values.get("perm_z", "")),
        ])
        self._add_array_summary(["matrix_phi", "matrix_kx", "matrix_ky", "matrix_kz"])

    def _add_grid_summary(self, proxy):
        values = proxy.get_module_values("grid_basic")
        self._add_cards([
            ("Nx", values.get("nx", "")),
            ("Ny", values.get("ny", "")),
            ("Nz", values.get("nz", "")),
            ("LGR", "开启" if values.get("enable_lgr") else "关闭"),
        ])
        self._add_array_summary(["grid_coord", "grid_zcorn", "grid_actnum", "mask_active"])

    def _add_fracture_summary(self, proxy):
        natural = proxy.get_module_values("natural_fractures")
        hydraulic = proxy.get_module_values("hydraulic_fractures")
        dfn = self.data_model.dfn_summary()
        dfn_fracture_count = dfn.get("fracture_count", "")
        natural_count = dfn_fracture_count if dfn_fracture_count not in ("", None) else natural.get("num_fracs", "")
        self._add_cards([
            ("天然裂缝", natural_count),
            ("压裂段数", hydraulic.get("num_stages", "")),
            ("DFN 裂缝数", dfn.get("fracture_count", "")),
            ("DFN 节点数", dfn.get("node_count", "")),
        ])

    def _add_solver_summary(self, proxy):
        values = proxy.get_module_values("simulation_control")
        total_time = self._float_or_none(values.get("simulation_time"))
        dt = self._float_or_none(values.get("time_step"))
        steps = ""
        if total_time is not None and dt and dt > 0:
            steps = int(total_time / dt)
        self._add_cards([
            ("模拟时间", values.get("simulation_time", "")),
            ("时间步长", values.get("time_step", "")),
            ("估算步数", steps),
            ("结果状态", "等待运行/加载"),
        ])

    def _add_initial_summary(self, proxy):
        values = proxy.get_module_values("initial_state")
        self._add_cards([
            ("初始压力", values.get("initial_pressure", "")),
            ("Sw", values.get("initial_sw", "")),
            ("Sg", values.get("initial_sg", "")),
            ("So", self._phase_oil(values)),
        ])

    def _add_overview_summary(self):
        self._add_cards([
            ("CaseData", self.data_model.project_value("case_data_path") or "未设置"),
            ("Dataset", "已生成" if self.data_model.dataset_exists() else "未生成"),
            ("Section", len(self.data_model.case_sections())),
            ("文件引用", len(self.data_model.file_records())),
        ])

    def _add_cards(self, rows):
        frame = QFrame()
        frame.setObjectName("modulePreviewCards")
        grid = QGridLayout(frame)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(6)
        grid.setVerticalSpacing(6)
        for index, (name, value) in enumerate(rows):
            card = QFrame()
            card.setObjectName("modulePreviewCard")
            layout = QVBoxLayout(card)
            layout.setContentsMargins(8, 6, 8, 6)
            title = QLabel(str(name))
            title.setObjectName("modulePreviewCardTitle")
            data = QLabel(self._format_value(value))
            data.setObjectName("modulePreviewCardValue")
            data.setWordWrap(True)
            layout.addWidget(title)
            layout.addWidget(data)
            grid.addWidget(card, index // 2, index % 2)
        self.content_layout.addWidget(frame)

    def _add_array_summary(self, keys):
        rows = []
        for key in keys:
            summary = self.data_model.array_summary(key)
            rows.append((key, summary.get("status", ""), summary.get("shape", "")))
        table = QTableWidget(len(rows), 3)
        table.setObjectName("modulePreviewTable")
        table.setHorizontalHeaderLabels(["数组", "状态", "形状"])
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        table.horizontalHeader().setStretchLastSection(True)
        table.setMaximumHeight(150)
        for row, (key, status, shape) in enumerate(rows):
            table.setItem(row, 0, QTableWidgetItem(str(key)))
            table.setItem(row, 1, QTableWidgetItem(str(status)))
            table.setItem(row, 2, QTableWidgetItem(str(shape)))
        self.content_layout.addWidget(table)

    def _add_message(self, title, text):
        frame = QFrame()
        frame.setObjectName("modulePreviewMessage")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(8, 8, 8, 8)
        title_label = QLabel(title)
        title_label.setObjectName("modulePreviewSubtitle")
        text_label = QLabel(text)
        text_label.setObjectName("modulePreviewDescription")
        text_label.setWordWrap(True)
        layout.addWidget(title_label)
        layout.addWidget(text_label)
        self.content_layout.addWidget(frame)

    def _add_result_actions(self):
        results = self.module_schema.get("related_results", []) or []
        if not results:
            return
        label = QLabel("主工作区")
        label.setObjectName("modulePreviewSubtitle")
        self.actions_layout.addWidget(label)
        for result in results:
            self.actions_layout.addWidget(self._result_button(result))

    def _result_button(self, result):
        button = QPushButton(result.get("title", result.get("key", "")))
        button.setObjectName("modulePreviewResultButton")
        button.setToolTip(self._tooltip(result))
        button.clicked.connect(
            lambda checked=False, key=result.get("key", ""):
                self._emit_result_request(key))
        return button

    def _emit_result_request(self, key):
        if key:
            self.result_requested.emit(key)

    def _nearest_result_store(self):
        parent = self.parent()
        while parent is not None:
            result_store = getattr(parent, "result_store", None)
            if result_store is not None:
                return result_store
            parent = parent.parent()
        return None

    def _tooltip(self, result):
        parts = [
            f"key: {result.get('key', '')}",
            f"type: {result.get('view', '')}",
        ]
        if result.get("note"):
            parts.append(result.get("note"))
        return "\n".join(parts)

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _format_value(self, value):
        if value is None:
            return ""
        if isinstance(value, float):
            return f"{value:.6g}"
        return str(value)

    def _float_or_none(self, value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _phase_oil(self, values):
        sw = self._float_or_none(values.get("initial_sw"))
        sg = self._float_or_none(values.get("initial_sg"))
        if sw is None or sg is None:
            return ""
        return max(0.0, 1.0 - sw - sg)
