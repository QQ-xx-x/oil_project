# -*- coding: utf-8 -*-
"""仿照 COMPASS 设计的流体与 PVT 模型编辑窗口。"""

import copy
import math

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QDoubleValidator, QIntValidator
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QStyle,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .chart_adapters import build_gas_pvt_curve_from_values
from .explicit_parameter_import_service import ExplicitParameterImportService
from .input_keyword_registry import MODULE_FLUID_PVT, MODULE_SPEC_BY_KEY
from .module_import_service import (
    normalize_module_business_data,
    validate_module_business_data,
)
from .module_input_models import ModuleInputState, ModuleParsedData
from .project_state import normalize_model_config


NODE_PVTW = "pvtw"
NODE_GASCOMP = "gascomp"
NODE_PVDG = "pvdg"


class _NumericEditor(QLineEdit):
    """A blank-aware numeric editor used directly inside parameter tables."""

    def __init__(self, *, integer=False, minimum=None, maximum=None,
                 decimals=10, parent=None):
        super().__init__(parent)
        self.integer = bool(integer)
        self.decimals = int(decimals)
        if self.integer:
            low = int(minimum if minimum is not None else -2147483647)
            high = int(maximum if maximum is not None else 2147483647)
            self.setValidator(QIntValidator(low, high, self))
        else:
            validator = QDoubleValidator(self)
            validator.setNotation(QDoubleValidator.ScientificNotation)
            if minimum is not None:
                validator.setBottom(float(minimum))
            if maximum is not None:
                validator.setTop(float(maximum))
            validator.setDecimals(max(0, self.decimals))
            self.setValidator(validator)
        self.setObjectName("fluidPvtTableEditor")

    def set_value(self, value):
        if value is None or value == "":
            self.clear()
            return
        if self.integer:
            self.setText(str(int(value)))
        else:
            self.setText(f"{float(value):.12g}")

    def value(self):
        text = self.text().strip()
        if not text:
            return None
        value = int(text) if self.integer else float(text)
        if not self.integer and not math.isfinite(value):
            raise ValueError("参数必须是有限数字。")
        return value


class FluidPvtCompassDialog(QDialog):
    """A new table-oriented fluid/PVT window independent of legacy pages."""

    values_applied = pyqtSignal(str, str, dict)

    EDITABLE_SPECS = {
        "p_ref": {"minimum": 0.0},
        "cw": {"minimum": 0.0},
        "mu_w": {"minimum": 0.0},
        "temperature_c": {"minimum": -273.14},
        "mole_ch4": {"minimum": 0.0, "maximum": 1.0},
        "mole_c2h6": {"minimum": 0.0, "maximum": 1.0},
        "mole_c3h8": {"minimum": 0.0, "maximum": 1.0},
        "mole_n2": {"minimum": 0.0, "maximum": 1.0},
        "mole_co2": {"minimum": 0.0, "maximum": 1.0},
        "mole_h2o": {"minimum": 0.0, "maximum": 1.0},
        "mole_unknown": {"minimum": 0.0, "maximum": 1.0},
        "gas_table_pmin_bar": {"minimum": 0.0},
        "gas_table_pmax_bar": {"minimum": 0.0},
        "gas_table_n": {"integer": True, "minimum": 2, "maximum": 100000},
    }

    def __init__(self, project_state, parent=None):
        super().__init__(parent)
        if project_state is None:
            raise ValueError("project_state is required")
        self.project_state = project_state
        self.module_spec = MODULE_SPEC_BY_KEY[MODULE_FLUID_PVT]
        self.values_were_applied = False
        self._working_state = (
            project_state.get_module_input_state(MODULE_FLUID_PVT)
            or ModuleInputState(
                module_key=MODULE_FLUID_PVT,
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
        self._editors = {}
        self._tree_items = {}
        self._page_index = {}

        self.setObjectName("fluidPvtCompassDialog")
        self.setWindowTitle("流体与 PVT")
        self.resize(980, 700)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(9)
        root.addWidget(self._build_header())

        splitter = QSplitter(Qt.Horizontal)
        splitter.setObjectName("fluidPvtCompassSplitter")
        splitter.addWidget(self._build_navigation())
        self.stack = QStackedWidget()
        self.stack.setObjectName("fluidPvtCompassStack")
        self._add_page(NODE_PVTW, self._build_pvtw_page())
        self._add_page(NODE_GASCOMP, self._build_gascomp_page())
        self._add_page(NODE_PVDG, self._build_pvdg_page())
        splitter.addWidget(self.stack)
        splitter.setSizes([205, 750])
        root.addWidget(splitter, 1)

        buttons = QDialogButtonBox()
        self.ok_button = QPushButton("确定")
        self.cancel_button = QPushButton("取消")
        buttons.addButton(self.ok_button, QDialogButtonBox.AcceptRole)
        buttons.addButton(self.cancel_button, QDialogButtonBox.RejectRole)
        self.ok_button.clicked.connect(self._accept_values)
        self.cancel_button.clicked.connect(self.reject)
        root.addWidget(buttons)

        self._apply_model_availability()
        self._refresh_editors()
        self._select_node(NODE_PVTW)

    def _build_header(self):
        frame = QFrame()
        frame.setObjectName("fluidPvtCompassHeader")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(12, 8, 12, 8)
        title = QLabel("流体与 PVT")
        title.setObjectName("parameterTitle")
        layout.addWidget(title)
        layout.addStretch()
        self.import_status = QLabel("")
        self.import_status.setObjectName("parameterDescription")
        layout.addWidget(self.import_status)
        self.import_button = QPushButton("导入")
        self.import_button.setObjectName("importFluidPvtDataButton")
        self.import_button.clicked.connect(self._import_values)
        layout.addWidget(self.import_button)
        return frame

    def _build_navigation(self):
        self.nav = QTreeWidget()
        self.nav.setObjectName("fluidPvtCompassNavigation")
        self.nav.setHeaderHidden(True)
        self.nav.setMinimumWidth(180)
        self.nav.setMaximumWidth(245)
        self.nav.setRootIsDecorated(True)
        root = QTreeWidgetItem(["Reg-1"])
        root.setData(0, Qt.UserRole, "region")
        root.setIcon(0, self.style().standardIcon(QStyle.SP_DirOpenIcon))
        root.setFlags(root.flags() & ~Qt.ItemIsSelectable)
        self.nav.addTopLevelItem(root)
        for key, text in (
                (NODE_PVTW, "PVTW"),
                (NODE_GASCOMP, "GASCOMP"),
                (NODE_PVDG, "PVDG")):
            item = QTreeWidgetItem([text])
            item.setData(0, Qt.UserRole, key)
            item.setToolTip(0, {
                NODE_PVTW: "水相 PVT 参数",
                NODE_GASCOMP: "气体组分",
                NODE_PVDG: "计算生成的气体 PVT 表",
            }[key])
            item.setIcon(0, self.style().standardIcon(QStyle.SP_FileIcon))
            root.addChild(item)
            self._tree_items[key] = item
        root.setExpanded(True)
        self.nav.currentItemChanged.connect(self._navigation_changed)
        return self.nav

    def _add_page(self, key, page):
        self._page_index[key] = self.stack.addWidget(page)

    def _page_frame(self, title):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(14, 10, 14, 14)
        layout.setSpacing(10)
        title_label = QLabel(title)
        title_label.setObjectName("parameterTitle")
        layout.addWidget(title_label)
        return page, layout

    def _editor(self, key):
        spec = dict(self.EDITABLE_SPECS[key])
        editor = _NumericEditor(**spec)
        editor.editingFinished.connect(self._editor_finished)
        self._editors[key] = editor
        return editor

    def _build_pvtw_page(self):
        page, layout = self._page_frame("水相 PVT 属性（PVTW）")
        self.pvtw_table = QTableWidget(1, 4)
        self.pvtw_table.setObjectName("pvtwParameterTable")
        self.pvtw_table.setHorizontalHeaderLabels((
            "参考压力\nPref\nbar",
            "体积系数\nBw\n—",
            "压缩系数\nCw\n1/bar",
            "黏度\nVis\ncP",
        ))
        self.pvtw_table.verticalHeader().setVisible(True)
        self.pvtw_table.setVerticalHeaderLabels(["1"])
        self.pvtw_table.setCellWidget(0, 0, self._editor("p_ref"))
        self.pvtw_table.setItem(
            0, 1, self._readonly_item(
                "1", "当前模型在参考压力下取 Bw=1"))
        self.pvtw_table.setCellWidget(0, 2, self._editor("cw"))
        self.pvtw_table.setCellWidget(0, 3, self._editor("mu_w"))
        self.pvtw_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch)
        self.pvtw_table.verticalHeader().setDefaultSectionSize(36)
        self.pvtw_table.setMinimumHeight(150)
        self.pvtw_table.setMaximumHeight(190)
        layout.addWidget(self.pvtw_table)
        layout.addStretch()
        return page

    def _build_gascomp_page(self):
        page, layout = self._page_frame("气体组分（GASCOMP）")
        rows = (
            ("气藏温度", "temperature_C", "°C", "temperature_c"),
            ("甲烷摩尔分数", "mole_CH4", "—", "mole_ch4"),
            ("乙烷摩尔分数", "mole_C2H6", "—", "mole_c2h6"),
            ("丙烷摩尔分数", "mole_C3H8", "—", "mole_c3h8"),
            ("氮气摩尔分数", "mole_N2", "—", "mole_n2"),
            ("二氧化碳摩尔分数", "mole_CO2", "—", "mole_co2"),
            ("水蒸气摩尔分数", "mole_H2O", "—", "mole_h2o"),
            ("其他组分摩尔分数", "mole_unknown", "—", "mole_unknown"),
        )
        table = self._vertical_parameter_table("gasCompositionTable", rows)
        layout.addWidget(table)
        self.composition_status = QLabel("")
        self.composition_status.setObjectName("gasCompositionStatus")
        layout.addWidget(self.composition_status)
        layout.addStretch()
        return page

    def _build_pvdg_page(self):
        page, layout = self._page_frame("气体 PVT 计算表（PVDG）")
        settings = (
            ("最小压力", "Pmin", "bar", "gas_table_pmin_bar"),
            ("最大压力", "Pmax", "bar", "gas_table_pmax_bar"),
            ("采样点数", "n", "—", "gas_table_n"),
        )
        settings_table = self._vertical_parameter_table(
            "pvdgSettingsTable", settings)
        settings_table.setMaximumHeight(185)
        layout.addWidget(settings_table)
        self.pvdg_status = QLabel("等待完整参数")
        self.pvdg_status.setObjectName("parameterDescription")
        layout.addWidget(self.pvdg_status)
        self.pvdg_table = QTableWidget(0, 3)
        self.pvdg_table.setObjectName("pvdgDataTable")
        self.pvdg_table.setHorizontalHeaderLabels((
            "压力\nP\nbar",
            "体积系数\nBg\nrm³/sm³",
            "黏度\nVis\ncP",
        ))
        self.pvdg_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.pvdg_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.pvdg_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.pvdg_table, 1)
        return page

    def _vertical_parameter_table(self, object_name, rows):
        table = QTableWidget(len(rows), 4)
        table.setObjectName(object_name)
        table.setHorizontalHeaderLabels(("参数", "标识", "单位", "参数值"))
        table.verticalHeader().setVisible(True)
        table.setVerticalHeaderLabels(
            [str(index) for index in range(1, len(rows) + 1)])
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        for row_index, (title, symbol, unit, key) in enumerate(rows):
            table.setItem(row_index, 0, self._readonly_item(title))
            table.setItem(row_index, 1, self._readonly_item(symbol))
            table.setItem(row_index, 2, self._readonly_item(unit))
            table.setCellWidget(row_index, 3, self._editor(key))
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        table.verticalHeader().setDefaultSectionSize(34)
        table.setMinimumHeight(min(370, 70 + len(rows) * 35))
        return table

    @staticmethod
    def _readonly_item(text, tooltip=""):
        item = QTableWidgetItem(str(text))
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        item.setTextAlignment(Qt.AlignCenter)
        if tooltip:
            item.setToolTip(tooltip)
        return item

    def _apply_model_availability(self):
        config = normalize_model_config(self.project_state.model_config)
        enabled = bool(config.get("enable_real_gas_pvt"))
        for key in (NODE_GASCOMP, NODE_PVDG):
            item = self._tree_items[key]
            item.setDisabled(not enabled)
            if not enabled:
                item.setToolTip(0, "请先在模型配置中启用真实气体 PVT")

    def _navigation_changed(self, current, previous):
        if current is None or current.isDisabled():
            return
        key = str(current.data(0, Qt.UserRole) or "")
        if key in self._page_index:
            self.stack.setCurrentIndex(self._page_index[key])
            if key == NODE_PVDG:
                self._refresh_pvdg_table()

    def _select_node(self, key):
        item = self._tree_items.get(key)
        if item is not None and not item.isDisabled():
            self.nav.setCurrentItem(item)

    def _refresh_editors(self):
        for key, editor in self._editors.items():
            editor.set_value(self._working_values.get(key))
        self._refresh_composition_status()
        self._refresh_pvdg_table()

    def _editor_finished(self):
        self._refresh_composition_status()
        self._refresh_pvdg_table()

    def _collect_values(self):
        values = copy.deepcopy(self._working_values)
        for key, editor in self._editors.items():
            value = editor.value()
            if value is None:
                values.pop(key, None)
            else:
                values[key] = value
        return normalize_module_business_data(MODULE_FLUID_PVT, values)

    def _refresh_composition_status(self):
        keys = (
            "mole_ch4", "mole_c2h6", "mole_c3h8", "mole_n2",
            "mole_co2", "mole_h2o", "mole_unknown",
        )
        try:
            values = [
                self._editors[key].value()
                for key in keys if self._editors[key].value() is not None
            ]
        except (TypeError, ValueError):
            self.composition_status.setText("组分中存在无效数值")
            return
        if not values:
            self.composition_status.setText("尚未输入气体组分")
            return
        total = sum(float(value) for value in values)
        if math.isclose(total, 1.0, rel_tol=1e-6, abs_tol=1e-6):
            self.composition_status.setText(f"组分总和：{total:.6g}（校验通过）")
        else:
            self.composition_status.setText(f"组分总和：{total:.6g}（应为 1）")

    def _refresh_pvdg_table(self):
        if not hasattr(self, "pvdg_table"):
            return
        try:
            values = self._collect_values()
            required = (
                "temperature_c", "gas_table_pmin_bar",
                "gas_table_pmax_bar", "gas_table_n",
            )
            if any(values.get(key) is None for key in required):
                raise ValueError("请先填写温度、压力范围和采样点数。")
            curve = build_gas_pvt_curve_from_values(values)
            points = list(curve.get("pvdg_rows") or [])
        except (TypeError, ValueError, OverflowError) as exc:
            self.pvdg_table.setRowCount(0)
            self.pvdg_status.setText(str(exc) or "当前参数无法生成 PVDG 表。")
            return
        self.pvdg_table.setUpdatesEnabled(False)
        try:
            self.pvdg_table.setRowCount(len(points))
            for row, point in enumerate(points):
                for column, value in enumerate(point):
                    self.pvdg_table.setItem(
                        row, column,
                        self._readonly_item(f"{float(value):.8g}"))
        finally:
            self.pvdg_table.setUpdatesEnabled(True)
        self.pvdg_status.setText(f"已生成 {len(points)} 个压力点")

    def _import_values(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择流体与 PVT 参数数据",
            "",
            "输入数据 (*.txt *.data);;所有文件 (*)",
        )
        if not path:
            return
        result = ExplicitParameterImportService(
            self.project_state).prepare_module(MODULE_FLUID_PVT, path)
        if not result.success or result.state is None:
            QMessageBox.warning(
                self,
                "导入失败",
                "\n".join(result.errors or ("流体与 PVT 参数导入失败。",)),
            )
            return
        self._working_state = result.state
        self._working_values = copy.deepcopy(result.state.parsed_data.values)
        self._refresh_editors()
        count = result.state.validation.get("imported_value_count", 0)
        self.import_status.setText(f"已读取 {count} 项参数，等待确定")

    def _accept_values(self):
        try:
            values = self._collect_values()
        except (TypeError, ValueError, OverflowError) as exc:
            QMessageBox.warning(self, "参数无效", str(exc) or "存在无效参数。")
            return
        validation = validate_module_business_data(MODULE_FLUID_PVT, values)
        if not validation["ok"]:
            QMessageBox.warning(
                self, "参数校验未通过", "\n".join(validation["errors"]))
            return

        draft = ModuleInputState.from_dict(self._working_state)
        draft.parsed_data = ModuleParsedData(values=values)
        current_validation = dict(draft.validation or {})
        checks = dict(current_validation.get("checks") or {})
        checks.update(validation["checks"])
        warnings = list(dict.fromkeys(
            list(current_validation.get("warnings") or [])
            + list(validation["warnings"])
        ))
        current_validation.update({
            "ok": True,
            "errors": [],
            "warnings": warnings,
            "checks": checks,
        })
        draft.validation = current_validation
        draft.dirty = True

        current = self.project_state.get_module_input_state(MODULE_FLUID_PVT)
        if current is not None and _state_content(current) == _state_content(draft):
            self._working_state = current
            self._working_values = copy.deepcopy(values)
            self.accept()
            return
        try:
            committed = self.project_state.replace_module_input_state(
                MODULE_FLUID_PVT, draft)
        except (TypeError, ValueError):
            QMessageBox.warning(self, "保存失败", "流体与 PVT 参数未能保存。")
            return

        self._working_state = committed
        self._working_values = copy.deepcopy(values)
        self.values_were_applied = True
        self.values_applied.emit(
            MODULE_FLUID_PVT,
            self.module_spec.title,
            _compact_values(values),
        )
        self.accept()


def _state_content(state):
    return {
        "raw_values": copy.deepcopy(state.raw_values),
        "parsed_data": state.parsed_data.to_dict(),
        "validation": copy.deepcopy(state.validation),
        "source": copy.deepcopy(state.source),
    }


def _compact_values(values):
    result = {}
    for key, value in (values or {}).items():
        if isinstance(value, dict):
            result[key] = f"{len(value)} 项业务属性"
        elif isinstance(value, (list, tuple)):
            result[key] = f"{len(value)} 条业务记录"
        else:
            result[key] = value
    return result


__all__ = [
    "FluidPvtCompassDialog",
    "NODE_GASCOMP",
    "NODE_PVDG",
    "NODE_PVTW",
]
