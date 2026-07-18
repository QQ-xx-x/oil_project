# -*- coding: utf-8 -*-
"""普通业务输入模块使用的统一注册表驱动对话框。"""

import copy
import os

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QApplication, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QFrame,
    QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMessageBox, QPushButton,
    QScrollArea, QSplitter, QStackedWidget, QVBoxLayout, QWidget,
)

from .input_keyword_registry import (
    MODULE_FRACTURE_SYSTEM,
    MODULE_FLUID_PVT,
    MODULE_GRID_SPATIAL,
    MODULE_INITIAL_CONDITIONS,
    MODULE_ROCK_PROPERTIES,
    MODULE_SOLVER_OUTPUT,
    MODULE_WELL_PRODUCTION,
    MODULE_SPEC_BY_KEY,
    WIDGET_BOOLEAN,
    WIDGET_CHOICE,
    WIDGET_DERIVED,
    WIDGET_INTEGER,
    WIDGET_NUMBER,
    WIDGET_SUMMARY,
    WIDGET_SUMMARY_TABLE,
    WIDGET_TABLE,
    display_fields_for_module,
)
from .fluid_pvt_widgets import (
    BasicFluidParametersPage,
    GasCompositionPage,
    PVTTablePage,
)
from .fracture_system_widgets import (
    HydraulicFracturePage,
    NaturalFracturePage,
)
from .grid_spatial_widgets import (
    GridOverviewPage,
    GridPropertyStatisticsPage,
)
from .module_import_service import (
    ModuleImportService,
    natural_fracture_business_data,
    normalize_module_business_data,
    validate_module_business_data,
)
from .initial_state_widgets import (
    InitialPressurePage,
    InitialSaturationPage,
)
from .well_production_widgets import (
    CompletionControlPage,
    WellTrajectoryPage,
)
from .solver_time_widgets import SimulationTimeControlPage
from .module_input_models import ModuleInputState, ModuleParsedData
from .module_input_widgets import (
    BusinessScalarEditor,
    StatisticsTableWidget,
    StructuredDataTableWidget,
    SummaryCardWidget,
    ValidationPanel,
)
from .rock_physics_widgets import (
    RockEmptyStatePage,
    RockRelativePermeabilityPage,
)
from .fracture_data_adapter import derive_hydraulic_fractures
from ..uniform_parser import parse_dfn, parse_wells


SCALAR_WIDGETS = frozenset((
    WIDGET_NUMBER,
    WIDGET_INTEGER,
    WIDGET_BOOLEAN,
    WIDGET_CHOICE,
    WIDGET_DERIVED,
))

COMPACT_MODULES = frozenset((
    MODULE_GRID_SPATIAL,
    MODULE_ROCK_PROPERTIES,
    MODULE_FRACTURE_SYSTEM,
    MODULE_FLUID_PVT,
    MODULE_INITIAL_CONDITIONS,
    MODULE_SOLVER_OUTPUT,
    MODULE_WELL_PRODUCTION,
))

SINGLE_PAGE_MODULES = frozenset((MODULE_SOLVER_OUTPUT,))


class ModuleInputDialog(QDialog):
    """所有普通输入模块共享的事务式外壳。"""

    values_applied = pyqtSignal(str, str, dict)

    def __init__(self, module_key, project_state, initial_group_key=None,
                 parent=None):
        super().__init__(parent)
        self.module_key = str(module_key or "")
        self.project_state = project_state
        self.module_spec = MODULE_SPEC_BY_KEY.get(self.module_key)
        if self.module_spec is None:
            raise ValueError(f"Unknown module: {self.module_key}")
        self.values_were_applied = False
        self._pages = []
        self._working_state = (
            project_state.get_module_input_state(self.module_key)
            or ModuleInputState(
                module_key=self.module_key,
                parsed_data=ModuleParsedData(),
                validation={
                    "ok": None,
                    "status": "empty",
                    "errors": [],
                    "warnings": [],
                },
            )
        )
        self._working_values = copy.deepcopy(
            self._working_state.parsed_data.values)

        self.setObjectName("moduleInputDialog")
        self.setWindowTitle(f"{self.module_spec.title} - 参数设置")
        if self.module_key == MODULE_SOLVER_OUTPUT:
            screen = QApplication.primaryScreen()
            available = screen.availableGeometry() if screen is not None else None
            preferred_width, preferred_height = 900, 600
            width = min(preferred_width, available.width() - 50) if available else preferred_width
            height = min(preferred_height, available.height() - 60) if available else preferred_height
            self.resize(max(760, width), max(520, height))
        elif self.module_key in {
                MODULE_FRACTURE_SYSTEM,
                MODULE_FLUID_PVT,
                MODULE_WELL_PRODUCTION}:
            screen = QApplication.primaryScreen()
            available = screen.availableGeometry() if screen is not None else None
            preferred_sizes = {
                MODULE_FRACTURE_SYSTEM: (1180, 980),
                MODULE_FLUID_PVT: (1080, 820),
                MODULE_WELL_PRODUCTION: (1120, 800),
            }
            preferred_width, preferred_height = preferred_sizes[self.module_key]
            width = min(preferred_width, available.width() - 50) if available else preferred_width
            height = min(preferred_height, available.height() - 60) if available else preferred_height
            self.resize(max(760, width), max(720, height))
        else:
            self.resize(980, 680)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)
        root.addWidget(self._header())

        splitter = QSplitter(Qt.Horizontal)
        self.nav = QListWidget()
        self.nav.setObjectName("moduleInputNav")
        if self.module_key in COMPACT_MODULES:
            self.nav.setMinimumWidth(112)
            self.nav.setMaximumWidth(140)
        else:
            self.nav.setMinimumWidth(175)
            self.nav.setMaximumWidth(230)
        self.nav.currentRowChanged.connect(self._show_page)
        splitter.addWidget(self.nav)
        if self.module_key in SINGLE_PAGE_MODULES:
            self.nav.hide()

        self.stack = QStackedWidget()
        splitter.addWidget(self.stack)
        splitter.setSizes(
            [0, 950]
            if self.module_key in SINGLE_PAGE_MODULES
            else [125, 825]
            if self.module_key in COMPACT_MODULES
            else [190, 760])
        root.addWidget(splitter, 1)

        self._build_pages(initial_group_key)
        self.validation_panel = ValidationPanel()
        root.addWidget(self.validation_panel)
        self._refresh_from_working_state()

        buttons = QDialogButtonBox()
        self.apply_button = QPushButton("应用")
        self.ok_button = QPushButton("确定")
        self.cancel_button = QPushButton("取消")
        buttons.addButton(self.apply_button, QDialogButtonBox.ApplyRole)
        buttons.addButton(self.ok_button, QDialogButtonBox.AcceptRole)
        buttons.addButton(self.cancel_button, QDialogButtonBox.RejectRole)
        self.apply_button.clicked.connect(self.apply_values)
        self.ok_button.clicked.connect(self._accept_with_apply)
        self.cancel_button.clicked.connect(self.reject)
        root.addWidget(buttons)

    def _header(self):
        frame = QFrame()
        frame.setObjectName("parameterIntro")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 8, 12, 8)
        title = QLabel(self.module_spec.title)
        title.setObjectName("parameterTitle")
        toolbar = QHBoxLayout()
        self.import_button = QPushButton(
            "导入"
            if self.module_key in COMPACT_MODULES
            else "导入模块数据")
        self.import_button.setObjectName("importModuleDataButton")
        self.import_status = QLabel("")
        self.import_status.setObjectName("parameterDescription")
        self.import_button.clicked.connect(self._import_module_data)
        if self.module_key in COMPACT_MODULES:
            toolbar.addWidget(title)
            toolbar.addStretch()
            toolbar.addWidget(self.import_status)
            toolbar.addWidget(self.import_button)
            layout.addLayout(toolbar)
        else:
            description = QLabel(
                "导入或编辑当前模块的业务参数。窗口仅展示解析后的参数、统计和结构化数据。")
            description.setObjectName("parameterDescription")
            description.setWordWrap(True)
            toolbar.addWidget(self.import_button)
            toolbar.addWidget(self.import_status, 1)
            layout.addWidget(title)
            layout.addWidget(description)
            layout.addLayout(toolbar)
        return frame

    def _build_pages(self, initial_group_key):
        fields = display_fields_for_module(self.module_key)
        initial_row = 0
        for index, group in enumerate(self.module_spec.groups):
            item = QListWidgetItem(group.title)
            item.setData(Qt.UserRole, group.key)
            self.nav.addItem(item)
            page_fields = tuple(field for field in fields if field.group == group.title)
            if (self.module_key == MODULE_GRID_SPATIAL
                    and group.key == "grid_properties"):
                page = GridOverviewPage(group.title, page_fields, self)
            elif (self.module_key == MODULE_GRID_SPATIAL
                    and group.key == "porosity_permeability"):
                page = GridPropertyStatisticsPage(
                    group.title, page_fields, self)
            elif (self.module_key == MODULE_ROCK_PROPERTIES
                    and group.key == "relative_permeability"):
                page = RockRelativePermeabilityPage(
                    group.title, page_fields, self)
            elif (self.module_key == MODULE_ROCK_PROPERTIES
                    and group.key in {"fine_analysis", "sensitivity"}):
                page = RockEmptyStatePage(
                    group.title, page_fields, self)
            elif (self.module_key == MODULE_FRACTURE_SYSTEM
                    and group.key == "natural_fractures"):
                page = NaturalFracturePage(
                    group.title, page_fields, self)
            elif (self.module_key == MODULE_FRACTURE_SYSTEM
                    and group.key == "hydraulic_fractures"):
                page = HydraulicFracturePage(
                    group.title, page_fields,
                    project_state=self.project_state, parent=self)
            elif (self.module_key == MODULE_FLUID_PVT
                    and group.key == "base_fluid_parameters"):
                page = BasicFluidParametersPage(
                    group.title, page_fields, self)
            elif (self.module_key == MODULE_FLUID_PVT
                    and group.key == "gas_components"):
                page = GasCompositionPage(
                    group.title, page_fields, self)
            elif (self.module_key == MODULE_FLUID_PVT
                    and group.key == "pvt_table"):
                page = PVTTablePage(
                    group.title, page_fields, self)
            elif (self.module_key == MODULE_INITIAL_CONDITIONS
                    and group.key == "initial_pressure"):
                page = InitialPressurePage(
                    group.title, page_fields, self)
            elif (self.module_key == MODULE_INITIAL_CONDITIONS
                    and group.key == "initial_saturation"):
                page = InitialSaturationPage(
                    group.title, page_fields, self)
            elif (self.module_key == MODULE_WELL_PRODUCTION
                    and group.key == "well_trajectory"):
                page = WellTrajectoryPage(
                    group.title, page_fields, self)
            elif (self.module_key == MODULE_WELL_PRODUCTION
                    and group.key == "completion_control"):
                page = CompletionControlPage(
                    group.title, page_fields, self)
            elif (self.module_key == MODULE_SOLVER_OUTPUT
                    and group.key == "time_control"):
                page = SimulationTimeControlPage(
                    group.title, page_fields, self)
            else:
                page = ModuleGroupPage(group.title, page_fields, self)
            page.values_changed.connect(self._mark_draft_changed)
            self._pages.append(page)
            self.stack.addWidget(page)
            if initial_group_key == group.key:
                initial_row = index
        if self.nav.count():
            self.nav.setCurrentRow(initial_row)

    def _show_page(self, index):
        if 0 <= index < self.stack.count():
            self.stack.setCurrentIndex(index)
            page = self.stack.widget(index)
            if isinstance(page, HydraulicFracturePage):
                page.refresh_from_project_state()

    def _mark_draft_changed(self):
        self.import_status.setText("存在尚未应用的修改")
        preview = copy.deepcopy(self._working_values)
        try:
            for page in self._pages:
                page.collect_values(preview)
        except (TypeError, ValueError):
            return
        for page in self._pages:
            page.refresh_derived(preview, self.module_key)

    def _import_module_data(self):
        current_group = self._current_group_key()
        if (self.module_key == MODULE_FRACTURE_SYSTEM
                and current_group == "natural_fractures"):
            self._import_natural_fractures()
            return
        if (self.module_key == MODULE_FRACTURE_SYSTEM
                and current_group == "hydraulic_fractures"):
            self._import_hydraulic_fractures()
            return

        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择模块数据",
            "",
            "输入数据 (*.txt *.data);;所有文件 (*)",
        )
        if not path:
            return
        result = ModuleImportService(self.project_state).prepare_module(
            self.module_key, path)
        if not result.success or result.state is None:
            message = "\n".join(result.errors or ("模块数据导入失败。",))
            QMessageBox.warning(self, "导入失败", message)
            return
        self._working_state = result.state
        self._working_values = copy.deepcopy(
            result.state.parsed_data.values)
        self._refresh_from_working_state()
        count = result.state.validation.get("imported_value_count", 0)
        self.import_status.setText(f"已读取 {count} 项业务输入，等待应用")

    def _current_group_key(self):
        item = self.nav.currentItem()
        return str(item.data(Qt.UserRole) or "") if item is not None else ""

    def _import_natural_fractures(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择天然裂缝 DFN 数据",
            "",
            "DFN 数据 (*.txt *.dfn);;所有文件 (*)",
        )
        if not path:
            return
        try:
            natural = natural_fracture_business_data(parse_dfn(path))
        except (OSError, TypeError, ValueError):
            QMessageBox.warning(
                self, "导入失败", "天然裂缝数据解析失败，请检查 DFN 文件内容。")
            return
        if not (natural.get("fractures") or []):
            QMessageBox.warning(
                self, "导入失败", "所选文件中没有解析到天然裂缝数据。")
            return
        self._set_direct_import_value(
            "natural_fractures", natural,
            {"dfn_file": os.path.abspath(path)},
        )
        self.import_status.setText(
            f"已读取 {len(natural.get('fractures') or [])} 条天然裂缝，等待应用")

    def _import_hydraulic_fractures(self):
        completion_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择人工裂缝完井数据",
            "",
            "完井数据 (*.csv);;所有文件 (*)",
        )
        if not completion_path:
            return

        track_path = os.path.join(
            os.path.dirname(os.path.abspath(completion_path)),
            "well_tracks.csv",
        )
        if not os.path.isfile(track_path):
            track_path, _ = QFileDialog.getOpenFileName(
                self,
                "选择配套井轨迹数据",
                os.path.dirname(os.path.abspath(completion_path)),
                "井轨迹数据 (*.csv);;所有文件 (*)",
            )
        if not track_path:
            return

        try:
            parsed_wells = parse_wells(track_path, completion_path)
            records = derive_hydraulic_fractures(parsed_wells)
        except (OSError, TypeError, ValueError):
            QMessageBox.warning(
                self, "导入失败",
                "人工裂缝数据解析失败，请检查完井文件及配套井轨迹文件。")
            return
        if not records:
            QMessageBox.warning(
                self, "导入失败",
                "完井数据中没有带完整几何信息的人工裂缝 PERF 记录。")
            return

        self._set_direct_import_value(
            "hydraulic_fractures", records,
            {
                "well_completions": os.path.abspath(completion_path),
                "well_tracks": os.path.abspath(track_path),
            },
        )
        self.import_status.setText(
            f"已读取 {len(records)} 条人工裂缝，等待应用")

    def _set_direct_import_value(self, key, value, source):
        self._working_values[key] = copy.deepcopy(value)
        validation = validate_module_business_data(
            self.module_key, self._working_values)
        current_validation = dict(self._working_state.validation or {})
        current_validation.update(validation)
        self._working_state.validation = current_validation
        current_source = dict(self._working_state.source or {})
        direct_imports = dict(current_source.get("direct_imports") or {})
        direct_imports[key] = copy.deepcopy(source)
        current_source["direct_imports"] = direct_imports
        self._working_state.source = current_source
        self._refresh_from_working_state()

    def _refresh_from_working_state(self):
        for page in self._pages:
            page.set_values(self._working_values, self.module_key)
        self.validation_panel.set_validation(
            self._working_state.validation,
            has_data=bool(self._working_values),
        )

    def apply_values(self):
        values = copy.deepcopy(self._working_values)
        try:
            for page in self._pages:
                page.collect_values(values)
        except (TypeError, ValueError):
            validation = {
                "ok": False,
                "errors": ["存在无法保存的参数值，请检查输入。"],
                "warnings": [],
            }
            self.validation_panel.set_validation(
                validation, has_data=bool(values))
            QMessageBox.warning(
                self, "参数无效", "存在无法保存的参数值，请检查输入。")
            return False

        values = normalize_module_business_data(self.module_key, values)
        business_validation = validate_module_business_data(
            self.module_key, values)
        if not business_validation["ok"]:
            self.validation_panel.set_validation(
                business_validation, has_data=bool(values))
            QMessageBox.warning(
                self, "参数校验未通过",
                "\n".join(business_validation["errors"]))
            return False

        draft = ModuleInputState.from_dict(self._working_state)
        draft.parsed_data = ModuleParsedData(values=values)
        draft.validation = dict(draft.validation or {})
        checks = dict(draft.validation.get("checks") or {})
        checks.update(business_validation["checks"])
        warnings = list(dict.fromkeys(
            list(draft.validation.get("warnings") or [])
            + list(business_validation["warnings"])
        ))
        draft.validation.update({
            "ok": True,
            "errors": [],
            "warnings": warnings,
            "checks": checks,
        })
        draft.dirty = True

        current = self.project_state.get_module_input_state(self.module_key)
        if current is not None and _state_content(current) == _state_content(draft):
            self._working_state = current
            self._working_values = copy.deepcopy(values)
            self.import_status.setText("当前数据没有变化")
            return True

        try:
            committed = self.project_state.replace_module_input_state(
                self.module_key, draft)
        except (TypeError, ValueError):
            QMessageBox.warning(self, "保存失败", "当前模块数据未能保存。")
            return False

        self._working_state = committed
        self._working_values = copy.deepcopy(values)
        self.values_were_applied = True
        self.import_status.setText(f"已应用，数据修订号 {committed.revision}")
        self.values_applied.emit(
            self.module_key, self.module_spec.title,
            _compact_business_values(values))
        self.validation_panel.set_validation(
            committed.validation, has_data=bool(values))
        return True

    def _accept_with_apply(self):
        if self.apply_values():
            self.accept()


class ModuleGroupPage(QWidget):
    """通用对话框外壳中的一个注册表业务分组。"""

    values_changed = pyqtSignal()

    def __init__(self, title, fields, parent=None):
        super().__init__(parent)
        self.group_title = title
        self.fields = tuple(fields or ())
        self.bindings = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        holder = QWidget()
        self.content = QVBoxLayout(holder)
        self.content.setContentsMargins(14, 12, 14, 12)
        self.content.setSpacing(10)
        scroll.setWidget(holder)
        outer.addWidget(scroll)

        title_label = QLabel(title)
        title_label.setObjectName("parameterTitle")
        self.content.addWidget(title_label)
        if not self.fields:
            note = QLabel("当前分类尚未注册可展示的业务字段。")
            note.setObjectName("parameterDescription")
            self.content.addWidget(note)
        self._build_controls()
        self.content.addStretch()

    def _build_controls(self):
        scalar_group = None
        scalar_form = None
        for field in self.fields:
            if field.widget_kind in SCALAR_WIDGETS:
                if scalar_group is None:
                    scalar_group = QFrame()
                    scalar_form = QFormLayout(scalar_group)
                    self.content.addWidget(scalar_group)
                control = BusinessScalarEditor(field)
                control.value_changed.connect(self.values_changed.emit)
                scalar_form.addRow(field.title, control)
            elif field.widget_kind == WIDGET_SUMMARY_TABLE:
                control = StatisticsTableWidget(
                    field.title, field.columns)
                self.content.addWidget(control)
            elif field.widget_kind == WIDGET_TABLE:
                control = StructuredDataTableWidget(
                    field.title, field.columns, editable=field.editable)
                control.value_changed.connect(self.values_changed.emit)
                self.content.addWidget(control)
            elif field.widget_kind == WIDGET_SUMMARY:
                control = SummaryCardWidget(field.title)
                self.content.addWidget(control)
            else:
                control = SummaryCardWidget(field.title)
                self.content.addWidget(control)
            self.bindings.append((field, control))

    def set_values(self, values, module_key):
        for field, control in self.bindings:
            value = _display_value(values, field.source_path, module_key)
            control.set_value(value)

    def collect_values(self, values):
        for field, control in self.bindings:
            if not field.editable:
                continue
            if isinstance(control, BusinessScalarEditor):
                value = control.value()
            elif isinstance(control, StructuredDataTableWidget):
                value = control.value()
            else:
                continue
            if value is None:
                _remove_value(values, field.source_path)
            else:
                _set_value(values, field.source_path, value)

    def refresh_derived(self, values, module_key):
        for field, control in self.bindings:
            if field.widget_kind != WIDGET_DERIVED:
                continue
            control.set_value(_display_value(
                values, field.source_path, module_key))


def _display_value(values, source_path, module_key):
    if source_path == "derived.mole_fraction_sum":
        keys = (
            "mole_ch4", "mole_c2h6", "mole_c3h8", "mole_n2",
            "mole_co2", "mole_h2o", "mole_unknown",
        )
        available = [values.get(key) for key in keys if values.get(key) is not None]
        return sum(float(value) for value in available) if available else None
    if source_path == "derived.so":
        sw = values.get("sw")
        sg = values.get("sg")
        if sw is None or sg is None:
            return None
        return 1.0 - float(sw) - float(sg)
    return _get_value(values, source_path)


def _get_value(values, path):
    current = values
    for part in str(path or "").split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _set_value(values, path, value):
    parts = str(path or "").split(".")
    current = values
    for part in parts[:-1]:
        child = current.get(part)
        if not isinstance(child, dict):
            child = {}
            current[part] = child
        current = child
    if parts and parts[-1] != "derived":
        current[parts[-1]] = copy.deepcopy(value)


def _remove_value(values, path):
    parts = str(path or "").split(".")
    current = values
    for part in parts[:-1]:
        if not isinstance(current, dict) or part not in current:
            return
        current = current[part]
    if isinstance(current, dict) and parts:
        current.pop(parts[-1], None)


def _state_content(state):
    return {
        "raw_values": copy.deepcopy(state.raw_values),
        "parsed_data": state.parsed_data.to_dict(),
        "validation": copy.deepcopy(state.validation),
        "source": copy.deepcopy(state.source),
    }


def _compact_business_values(values):
    compact = {}
    for key, value in (values or {}).items():
        if isinstance(value, dict):
            compact[key] = f"{len(value)} 项业务属性"
        elif isinstance(value, (list, tuple)):
            compact[key] = f"{len(value)} 条业务记录"
        else:
            compact[key] = value
    return compact
