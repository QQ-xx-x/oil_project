# -*- coding: utf-8 -*-
"""仿照 COMPASS 设计、根据现有 Corey 参数生成 SWGF 表的窗口。"""

import copy
import math

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QDoubleValidator
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
    QStyle,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .explicit_parameter_import_service import ExplicitParameterImportService
from .input_keyword_registry import MODULE_ROCK_PROPERTIES, MODULE_SPEC_BY_KEY
from .module_import_service import validate_module_business_data
from .module_input_models import ModuleInputState, ModuleParsedData


NODE_SWGF = "swgf"
CURVE_POINT_COUNT = 21


class _CurveNumberEditor(QLineEdit):
    def __init__(self, *, minimum=0.0, maximum=None, parent=None):
        super().__init__(parent)
        validator = QDoubleValidator(self)
        validator.setNotation(QDoubleValidator.ScientificNotation)
        validator.setDecimals(10)
        validator.setBottom(float(minimum))
        if maximum is not None:
            validator.setTop(float(maximum))
        self.setValidator(validator)
        self.setObjectName("relativePermeabilityParameterEditor")

    def set_value(self, value):
        self.setText("" if value in (None, "") else f"{float(value):.12g}")

    def value(self):
        text = self.text().strip()
        if not text:
            return None
        value = float(text)
        if not math.isfinite(value):
            raise ValueError("相渗参数必须是有限数字。")
        return value


class RelativePermeabilityCompassDialog(QDialog):
    """Independent tree-and-table editor for the existing SWGF capability."""

    values_applied = pyqtSignal(str, str, dict)

    def __init__(self, project_state, parent=None):
        super().__init__(parent)
        if project_state is None:
            raise ValueError("project_state is required")
        self.project_state = project_state
        self.module_spec = MODULE_SPEC_BY_KEY[MODULE_ROCK_PROPERTIES]
        self.values_were_applied = False
        self._working_state = (
            project_state.get_module_input_state(MODULE_ROCK_PROPERTIES)
            or ModuleInputState(
                module_key=MODULE_ROCK_PROPERTIES,
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

        self.setObjectName("relativePermeabilityCompassDialog")
        self.setWindowTitle("相渗曲线")
        self.resize(900, 700)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(9)
        root.addWidget(self._build_header())

        splitter = QSplitter(Qt.Horizontal)
        splitter.setObjectName("relativePermeabilityCompassSplitter")
        splitter.addWidget(self._build_navigation())
        splitter.addWidget(self._build_swgf_page())
        splitter.setSizes([195, 680])
        root.addWidget(splitter, 1)

        buttons = QDialogButtonBox()
        self.ok_button = QPushButton("确定")
        self.cancel_button = QPushButton("取消")
        buttons.addButton(self.ok_button, QDialogButtonBox.AcceptRole)
        buttons.addButton(self.cancel_button, QDialogButtonBox.RejectRole)
        self.ok_button.clicked.connect(self._accept_values)
        self.cancel_button.clicked.connect(self.reject)
        root.addWidget(buttons)

        self._refresh_editors()
        self.nav.setCurrentItem(self.swgf_item)

    def _build_header(self):
        frame = QFrame()
        frame.setObjectName("relativePermeabilityCompassHeader")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(12, 8, 12, 8)
        title = QLabel("相渗曲线")
        title.setObjectName("parameterTitle")
        layout.addWidget(title)
        layout.addStretch()
        self.import_status = QLabel("")
        self.import_status.setObjectName("parameterDescription")
        layout.addWidget(self.import_status)
        self.import_button = QPushButton("导入")
        self.import_button.setObjectName("importRelativePermeabilityDataButton")
        self.import_button.clicked.connect(self._import_values)
        layout.addWidget(self.import_button)
        return frame

    def _build_navigation(self):
        self.nav = QTreeWidget()
        self.nav.setObjectName("relativePermeabilityCompassNavigation")
        self.nav.setHeaderHidden(True)
        self.nav.setMinimumWidth(170)
        self.nav.setMaximumWidth(230)
        region = QTreeWidgetItem(["Reg-1"])
        region.setIcon(0, self.style().standardIcon(QStyle.SP_DirOpenIcon))
        region.setFlags(region.flags() & ~Qt.ItemIsSelectable)
        self.nav.addTopLevelItem(region)
        self.swgf_item = QTreeWidgetItem(["SWGF"])
        self.swgf_item.setData(0, Qt.UserRole, NODE_SWGF)
        self.swgf_item.setToolTip(0, "气—水相对渗透率函数")
        self.swgf_item.setIcon(
            0, self.style().standardIcon(QStyle.SP_FileIcon))
        region.addChild(self.swgf_item)
        region.setExpanded(True)
        return self.nav

    def _build_swgf_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(14, 10, 14, 14)
        layout.setSpacing(10)
        title = QLabel("气水相对渗透率函数（SWGF）")
        title.setObjectName("parameterTitle")
        layout.addWidget(title)

        parameter_rows = (
            ("相渗指数", "n", "—", "n", None),
            ("束缚水饱和度", "Swi", "—", "swi", 1.0),
            ("残余气饱和度", "Sgr", "—", "sgc", 1.0),
        )
        self.parameter_table = QTableWidget(len(parameter_rows), 4)
        self.parameter_table.setObjectName("swgfParameterTable")
        self.parameter_table.setHorizontalHeaderLabels(
            ("参数", "标识", "单位", "参数值"))
        self.parameter_table.setVerticalHeaderLabels(("1", "2", "3"))
        for row, (name, symbol, unit, key, maximum) in enumerate(parameter_rows):
            self.parameter_table.setItem(row, 0, self._readonly_item(name))
            self.parameter_table.setItem(row, 1, self._readonly_item(symbol))
            self.parameter_table.setItem(row, 2, self._readonly_item(unit))
            editor = _CurveNumberEditor(
                minimum=0.0, maximum=maximum, parent=self.parameter_table)
            editor.editingFinished.connect(self._refresh_curve)
            self.parameter_table.setCellWidget(row, 3, editor)
            self._editors[key] = editor
        header = self.parameter_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        self.parameter_table.verticalHeader().setDefaultSectionSize(34)
        self.parameter_table.setMaximumHeight(185)
        layout.addWidget(self.parameter_table)

        self.curve_status = QLabel("等待完整的 n、Swi、Sgr 参数")
        self.curve_status.setObjectName("parameterDescription")
        layout.addWidget(self.curve_status)
        self.curve_table = QTableWidget(0, 3)
        self.curve_table.setObjectName("swgfCurveTable")
        self.curve_table.setHorizontalHeaderLabels((
            "水饱和度\nSw\n—",
            "水相相对渗透率\nkrw\n—",
            "气相相对渗透率\nkrg\n—",
        ))
        self.curve_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.curve_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.curve_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch)
        layout.addWidget(self.curve_table, 1)
        return page

    @staticmethod
    def _readonly_item(text):
        item = QTableWidgetItem(str(text))
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        item.setTextAlignment(Qt.AlignCenter)
        return item

    def _refresh_editors(self):
        for key, editor in self._editors.items():
            editor.set_value(self._working_values.get(key))
        self._refresh_curve()

    def _collect_values(self):
        values = copy.deepcopy(self._working_values)
        for key, editor in self._editors.items():
            value = editor.value()
            if value is None:
                values.pop(key, None)
            else:
                values[key] = value
        return values

    def _refresh_curve(self):
        try:
            values = self._collect_values()
            exponent = values.get("n")
            swi = values.get("swi")
            sgr = values.get("sgc")
            if None in (exponent, swi, sgr):
                raise ValueError("请先填写 n、Swi 和 Sgr。")
            exponent = float(exponent)
            swi = float(swi)
            sgr = float(sgr)
            if exponent <= 0.0:
                raise ValueError("相渗指数 n 必须大于 0。")
            if not (0.0 <= swi <= 1.0 and 0.0 <= sgr <= 1.0):
                raise ValueError("Swi 和 Sgr 必须位于 0 到 1 之间。")
            denominator = 1.0 - swi - sgr
            if denominator <= 0.0:
                raise ValueError("Swi + Sgr 必须小于 1。")
            points = []
            for index in range(CURVE_POINT_COUNT):
                effective = index / (CURVE_POINT_COUNT - 1)
                sw = swi + denominator * effective
                krw = effective ** exponent
                krg = (1.0 - effective) ** exponent
                points.append((sw, krw, krg))
        except (TypeError, ValueError, OverflowError) as exc:
            self.curve_table.setRowCount(0)
            self.curve_status.setText(str(exc) or "当前参数无法生成 SWGF 表。")
            return

        self.curve_table.setUpdatesEnabled(False)
        try:
            self.curve_table.setRowCount(len(points))
            for row, point in enumerate(points):
                for column, value in enumerate(point):
                    self.curve_table.setItem(
                        row, column,
                        self._readonly_item(f"{float(value):.8g}"))
        finally:
            self.curve_table.setUpdatesEnabled(True)
        self.curve_status.setText(
            f"已根据 Corey 指数 n={exponent:.6g} 生成 {len(points)} 个数据点")

    def _import_values(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择相渗参数数据",
            "",
            "输入数据 (*.txt *.data);;所有文件 (*)",
        )
        if not path:
            return
        result = ExplicitParameterImportService(
            self.project_state).prepare_module(MODULE_ROCK_PROPERTIES, path)
        if not result.success or result.state is None:
            QMessageBox.warning(
                self,
                "导入失败",
                "\n".join(result.errors or ("相渗参数导入失败。",)),
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
        validation = validate_module_business_data(
            MODULE_ROCK_PROPERTIES, values)
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

        current = self.project_state.get_module_input_state(
            MODULE_ROCK_PROPERTIES)
        if current is not None and _state_content(current) == _state_content(draft):
            self.accept()
            return
        try:
            committed = self.project_state.replace_module_input_state(
                MODULE_ROCK_PROPERTIES, draft)
        except (TypeError, ValueError):
            QMessageBox.warning(self, "保存失败", "相渗参数未能保存。")
            return
        self._working_state = committed
        self._working_values = copy.deepcopy(values)
        self.values_were_applied = True
        self.values_applied.emit(
            MODULE_ROCK_PROPERTIES,
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
    "CURVE_POINT_COUNT",
    "NODE_SWGF",
    "RelativePermeabilityCompassDialog",
]
