# -*- coding: utf-8 -*-
"""网格属性节点专用弹窗：导入、方向复制和 BOX 编辑。"""

import copy
import math
import os
from dataclasses import dataclass

import numpy as np
from PyQt5.QtCore import QAbstractTableModel, QModelIndex, Qt, pyqtSignal
from PyQt5.QtGui import QBrush, QColor
from PyQt5.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFileDialog,
    QFormLayout, QFrame, QGridLayout, QGroupBox, QHBoxLayout, QHeaderView,
    QLabel, QListWidget, QMessageBox, QPushButton, QSpinBox, QSplitter,
    QTableView, QVBoxLayout, QWidget,
)

from ..uniform_parser import parse_grid, parse_property
from .configuration_status import (
    STATUS_CONFIGURED_COLOR,
    STATUS_MISSING_COLOR,
    property_is_configured,
)
from .input_keyword_registry import MODULE_GRID_SPATIAL
from .input_source_registry import SOURCE_MODE_KEYWORD_FILE
from .module_input_models import ModuleInputState, ModuleParsedData
from .project_state import normalize_model_config
from .single_file_import_service import SingleFileImportService


NULL_VALUE = 99999.0


@dataclass(frozen=True)
class PropertySpec:
    key: str
    title: str
    value_key: str
    source_identity: str
    permeability: bool = False
    binary: bool = False


PROPERTY_SPECS = (
    PropertySpec("PERMX", "X 向渗透率 (PERMX)", "matrix_kx", "ROCK.matrix_kx_file", True),
    PropertySpec("PERMY", "Y 向渗透率 (PERMY)", "matrix_ky", "ROCK.matrix_ky_file", True),
    PropertySpec("PERMZ", "Z 向渗透率 (PERMZ)", "matrix_kz", "ROCK.matrix_kz_file", True),
    PropertySpec("PORO", "孔隙度 (PORO)", "matrix_phi", "ROCK.matrix_phi_file"),
    PropertySpec("ACTNUM", "网格启用状态 (ACTNUM)", "actnum", "GRID.actnum_file", binary=True),
)


OPERATIONS = (
    ("set", "赋值"),
    ("add", "加"),
    ("subtract", "减"),
    ("multiply", "乘"),
    ("divide", "除"),
)


def _format_property_value(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "—"
    if not math.isfinite(number):
        return "—"
    return f"{number:.10g}"


class PropertyLayerTableModel(QAbstractTableModel):
    """将一维 I-fast 属性数组按当前 K 层展示为 Ny × Nx 表格。"""

    def __init__(self, values=None, nx=0, ny=0, nz=0, layer=1, parent=None):
        super().__init__(parent)
        self.values = values
        self.nx = max(0, int(nx or 0))
        self.ny = max(0, int(ny or 0))
        self.nz = max(0, int(nz or 0))
        self.layer = max(1, min(int(layer or 1), max(1, self.nz)))

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() or self.values is None else self.ny

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() or self.values is None else self.nx

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or role not in {Qt.DisplayRole, Qt.TextAlignmentRole}:
            return None
        if role == Qt.TextAlignmentRole:
            return int(Qt.AlignCenter)
        offset = (self.layer - 1) * self.nx * self.ny
        value = self.values[offset + index.row() * self.nx + index.column()]
        return _format_property_value(value)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        return f"X{section + 1}" if orientation == Qt.Horizontal else f"Y{section + 1}"


class CopyPropertyDialog(QDialog):
    """为一个空的渗透率方向选择已有属性作为复制来源。"""

    def __init__(self, target_spec, source_specs, parent=None):
        super().__init__(parent)
        self.target_spec = target_spec
        self.source_specs = tuple(source_specs or ())
        self.setWindowTitle(f"复制到 {target_spec.key}")
        self.resize(430, 210)
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(12)

        title = QLabel(f"为 {target_spec.key} 选择数据来源")
        title.setObjectName("parameterTitle")
        description = QLabel(
            "复制后目标属性将成为独立副本，后续修改不会影响来源属性。")
        description.setObjectName("parameterDescription")
        description.setWordWrap(True)
        root.addWidget(title)
        root.addWidget(description)

        form = QFormLayout()
        self.source_combo = QComboBox()
        for source in self.source_specs:
            self.source_combo.addItem(source.title, source.value_key)
        form.addRow("已有属性", self.source_combo)
        root.addLayout(form)
        root.addStretch()

        buttons = QDialogButtonBox()
        buttons.addButton(QPushButton("确定复制"), QDialogButtonBox.AcceptRole)
        buttons.addButton(QPushButton("取消"), QDialogButtonBox.RejectRole)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def source_value_key(self):
        return self.source_combo.currentData()


class BoxEditDialog(QDialog):
    """在指定 I/J/K 范围执行赋值或算术运算。"""

    def __init__(self, spec, nx, ny, nz, parent=None):
        super().__init__(parent)
        self.spec = spec
        self.setObjectName("boxEditDialog")
        self.setWindowTitle(f"{spec.key} - BOX 区域编辑")
        self.resize(660, 440)
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(14)

        intro = QFrame()
        intro.setObjectName("parameterIntro")
        intro_layout = QVBoxLayout(intro)
        intro_layout.setContentsMargins(12, 9, 12, 9)
        intro_layout.setSpacing(3)
        title = QLabel("BOX 分区编辑")
        title.setObjectName("parameterTitle")
        intro_layout.addWidget(title)
        root.addWidget(intro)

        range_group = QGroupBox("网格范围")
        grid = QGridLayout(range_group)
        grid.setContentsMargins(14, 16, 14, 12)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(10)
        grid.addWidget(QLabel("方向"), 0, 0)
        grid.addWidget(QLabel("最小索引"), 0, 1)
        grid.addWidget(QLabel(""), 0, 2)
        grid.addWidget(QLabel("最大索引"), 0, 3)
        self.bounds = {}
        definitions = (
            ("X (I)", "x1", "x2", nx),
            ("Y (J)", "y1", "y2", ny),
            ("Z (K)", "z1", "z2", nz),
        )
        for row, (axis, lower_key, upper_key, maximum) in enumerate(
                definitions, 1):
            axis_label = QLabel(axis)
            axis_label.setObjectName("boxAxisLabel")
            lower = QSpinBox()
            upper = QSpinBox()
            for editor in (lower, upper):
                editor.setRange(1, max(1, int(maximum)))
                editor.setMinimumWidth(150)
            lower.setValue(1)
            upper.setValue(max(1, int(maximum)))
            self.bounds[lower_key] = lower
            self.bounds[upper_key] = upper
            separator = QLabel("—")
            separator.setAlignment(Qt.AlignCenter)
            grid.addWidget(axis_label, row, 0)
            grid.addWidget(lower, row, 1)
            grid.addWidget(separator, row, 2)
            grid.addWidget(upper, row, 3)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)
        root.addWidget(range_group)

        operation_group = QGroupBox("属性操作")
        operation_layout = QGridLayout(operation_group)
        operation_layout.setContentsMargins(14, 16, 14, 12)
        operation_layout.setHorizontalSpacing(12)
        self.operation = QComboBox()
        for key, title in OPERATIONS:
            if spec.binary and key != "set":
                continue
            self.operation.addItem(title, key)
        self.value = QDoubleSpinBox()
        self.value.setRange(-1.0e12, 1.0e12)
        self.value.setDecimals(6)
        self.value.setValue(1.0)
        if spec.binary:
            self.value.setRange(0.0, 1.0)
            self.value.setDecimals(0)
        operation_layout.addWidget(QLabel("操作方式"), 0, 0)
        operation_layout.addWidget(self.operation, 0, 1)
        operation_layout.addWidget(QLabel("编辑数值"), 0, 2)
        operation_layout.addWidget(self.value, 0, 3)
        operation_layout.setColumnStretch(1, 1)
        operation_layout.setColumnStretch(3, 1)
        root.addWidget(operation_group)

        self.range_label = QLabel()
        self.range_label.setObjectName("boxRangeSummary")
        self.range_label.setMinimumHeight(42)
        self.range_label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        root.addWidget(self.range_label)
        for editor in self.bounds.values():
            editor.valueChanged.connect(self._refresh_range)
        self._refresh_range()
        root.addStretch()

        buttons = QDialogButtonBox()
        buttons.addButton(QPushButton("确定"), QDialogButtonBox.AcceptRole)
        buttons.addButton(QPushButton("取消"), QDialogButtonBox.RejectRole)
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)
        self.setStyleSheet("""
            QDialog#boxEditDialog QGroupBox {
                font-weight: 600;
                border: 1px solid #cfd7e3;
                border-radius: 5px;
                margin-top: 8px;
                padding-top: 7px;
            }
            QDialog#boxEditDialog QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QLabel#boxAxisLabel {
                color: #24527a;
                font-weight: 600;
                min-width: 52px;
            }
            QLabel#boxRangeSummary {
                color: #36536d;
                background: #eef4fa;
                border: 1px solid #d2dfeb;
                border-radius: 4px;
                padding: 7px 11px;
            }
        """)

    def _refresh_range(self):
        self.range_label.setText(
            f"范围：X({self.bounds['x1'].value()}-{self.bounds['x2'].value()})；"
            f"Y({self.bounds['y1'].value()}-{self.bounds['y2'].value()})；"
            f"Z({self.bounds['z1'].value()}-{self.bounds['z2'].value()})")

    def _validate_and_accept(self):
        for lower, upper, title in (
                ("x1", "x2", "X"), ("y1", "y2", "Y"), ("z1", "z2", "Z")):
            if self.bounds[lower].value() > self.bounds[upper].value():
                QMessageBox.warning(self, "范围无效", f"{title} 方向最小值不能大于最大值。")
                return
        self.accept()

    def record(self):
        return {
            "scope": "box",
            **{key: editor.value() for key, editor in self.bounds.items()},
            "operation": self.operation.currentData(),
            "value": self.value.value(),
        }


def _operation_view(array, record, nx, ny, nz):
    shaped = array.reshape((nz, ny, nx))
    scope = record.get("scope", "all")
    if scope == "all":
        return shaped
    x1 = int(record.get("x1", 1))
    x2 = int(record.get("x2", nx))
    y1 = int(record.get("y1", 1))
    y2 = int(record.get("y2", ny))
    z1 = int(record.get("z1", 1))
    z2 = int(record.get("z2", nz))
    return shaped[z1 - 1:z2, y1 - 1:y2, x1 - 1:x2]


def apply_property_operation(array, record, nx, ny, nz, spec):
    """原子应用一个属性运算；非法结果不会写回数组。"""

    view = _operation_view(array, record, nx, ny, nz)
    value = float(record.get("value", 0.0))
    operation = str(record.get("operation") or "set")
    if operation == "divide" and value == 0.0:
        raise ValueError("除数不能为 0。")
    source = view.astype(np.float64, copy=True)
    editable = ~np.isclose(source, NULL_VALUE)
    if operation == "set":
        source[editable] = value
    elif operation == "add":
        source[editable] += value
    elif operation == "subtract":
        source[editable] -= value
    elif operation == "multiply":
        source[editable] *= value
    elif operation == "divide":
        source[editable] /= value
    else:
        raise ValueError("不支持的属性运算。")
    changed = source[editable]
    if not np.all(np.isfinite(changed)):
        raise ValueError("运算结果中存在无效数值。")
    if spec.binary and not np.all(np.isin(changed, (0.0, 1.0))):
        raise ValueError("ACTNUM 只能设置为 0 或 1。")
    if spec.permeability and np.any(changed < 0.0):
        raise ValueError("渗透率运算结果不能小于 0。")
    if spec.value_key == "matrix_phi" and (
            np.any(changed < 0.0) or np.any(changed > 1.0)):
        raise ValueError("孔隙度运算结果必须位于 0 到 1 之间。")
    view[...] = source.astype(view.dtype, copy=False)
    return array


class GridPropertyDialog(QDialog):
    """网格属性节点专用弹窗，左侧只展示属性关键字。"""

    values_applied = pyqtSignal(str, str, dict)

    def __init__(self, project_state, parent=None):
        super().__init__(parent)
        self.project_state = project_state
        config = normalize_model_config(getattr(project_state, "model_config", None))
        self.config = config
        self.nx = int(config.get("grid_nx", 50))
        self.ny = int(config.get("grid_ny", 25))
        self.nz = int(config.get("grid_nz", 3))
        current = project_state.get_module_input_state(MODULE_GRID_SPATIAL)
        self._working_state = current or ModuleInputState(
            module_key=MODULE_GRID_SPATIAL,
            parsed_data=ModuleParsedData(),
            validation={"ok": True, "errors": [], "warnings": [], "checks": {}},
        )
        self._working_values = copy.deepcopy(self._working_state.parsed_data.values)
        self._working_source = copy.deepcopy(self._working_state.source or {})
        self._arrays = {}
        self._changed_keys = set()
        self._selected_spec = PROPERTY_SPECS[0]

        self.setObjectName("gridPropertyDialog")
        self.setWindowTitle("网格属性 (PROPERTY)")
        self.resize(1080, 760)
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)
        root.addWidget(self._header())
        splitter = QSplitter(Qt.Horizontal)
        self.nav = QListWidget()
        self.nav.setObjectName("propertyLogicNav")
        self.nav.setMinimumWidth(150)
        self.nav.setMaximumWidth(190)
        for spec in PROPERTY_SPECS:
            self.nav.addItem(spec.key)
        splitter.addWidget(self.nav)
        splitter.addWidget(self._content())
        splitter.setSizes([165, 895])
        root.addWidget(splitter, 1)
        self.status_label = QLabel("")
        self.status_label.setObjectName("parameterDescription")
        root.addWidget(self.status_label)
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
        self.nav.currentRowChanged.connect(self._select_property)
        self.layer_spin.valueChanged.connect(self._refresh_table)
        self.nav.setCurrentRow(0)

    def _header(self):
        frame = QFrame()
        frame.setObjectName("parameterIntro")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(12, 8, 12, 8)
        title = QLabel("网格属性")
        title.setObjectName("parameterTitle")
        layout.addWidget(title)
        layout.addStretch()
        dimensions = QLabel(f"网格维度：{self.nx} × {self.ny} × {self.nz}")
        dimensions.setObjectName("parameterDescription")
        layout.addWidget(dimensions)
        return frame

    def _content(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(14, 12, 14, 12)
        toolbar = QHBoxLayout()
        self.property_title = QLabel()
        self.property_title.setObjectName("parameterTitle")
        toolbar.addWidget(self.property_title)
        toolbar.addStretch()
        layer_label = QLabel("显示层 K")
        layer_label.setToolTip("切换当前表格显示的垂向网格层")
        toolbar.addWidget(layer_label)
        self.layer_spin = QSpinBox()
        self.layer_spin.setRange(1, max(1, self.nz))
        self.layer_spin.setSuffix(f" / {self.nz}")
        self.layer_spin.setToolTip("切换当前表格显示的垂向网格层")
        toolbar.addWidget(self.layer_spin)
        self.import_button = QPushButton("导入")
        self.copy_button = QPushButton("复制")
        self.copy_button.setToolTip("从已有的其他方向渗透率复制数据")
        self.box_button = QPushButton("BOX")
        self.import_button.clicked.connect(self._import_property)
        self.copy_button.clicked.connect(self._open_copy)
        self.box_button.clicked.connect(self._open_box)
        toolbar.addWidget(self.import_button)
        toolbar.addWidget(self.copy_button)
        toolbar.addWidget(self.box_button)
        layout.addLayout(toolbar)
        self.statistics = QLabel("尚未导入数据")
        self.statistics.setObjectName("parameterDescription")
        layout.addWidget(self.statistics)
        self.table = QTableView()
        self.table.setObjectName("propertyLayerTable")
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableView.NoEditTriggers)
        self.table.setSelectionBehavior(QTableView.SelectItems)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setDefaultSectionSize(80)
        layout.addWidget(self.table, 1)
        return page

    def _select_property(self, index):
        if not 0 <= index < len(PROPERTY_SPECS):
            return
        self._selected_spec = PROPERTY_SPECS[index]
        self.property_title.setText(self._selected_spec.title)
        self._ensure_loaded(self._selected_spec)
        self._refresh_table()

    def _update_nav_status(self):
        for index, spec in enumerate(PROPERTY_SPECS):
            configured = property_is_configured(
                self.config,
                self._working_values,
                self._working_source,
                spec.value_key,
                spec.source_identity,
                spec.binary,
                self._arrays,
            )
            item = self.nav.item(index)
            if item is None:
                continue
            color = (
                STATUS_CONFIGURED_COLOR
                if configured else STATUS_MISSING_COLOR)
            item.setForeground(QBrush(QColor(color)))
            font = item.font()
            font.setBold(True)
            item.setFont(font)
            item.setToolTip(
                "配置状态：已配置"
                if configured else "配置状态：尚未配置或数据无效")

    def _source_path(self, spec):
        keywords = self._working_source.get("keywords") or {}
        record = keywords.get(spec.source_identity) or {}
        path = str(record.get("resolved_path") or "").strip()
        if path:
            return path
        if spec.binary:
            grid_record = keywords.get("GRID.grid_file") or {}
            return str(grid_record.get("resolved_path") or "").strip()
        return ""

    def _ensure_loaded(self, spec):
        if spec.value_key in self._arrays:
            return self._arrays[spec.value_key]
        path = self._source_path(spec)
        if not path or not os.path.isfile(path):
            return None
        try:
            if spec.binary and spec.source_identity not in (
                    self._working_source.get("keywords") or {}):
                values = parse_grid(path).get("actnum") or []
            else:
                record = (
                    (self._working_source.get("keywords") or {}).get(
                        spec.source_identity) or {})
                if record.get("source_mode") == SOURCE_MODE_KEYWORD_FILE:
                    # A copied permeability direction deliberately keeps the
                    # original imported file/keyword as its persistent source.
                    imported_value_key = str(
                        record.get("value_key") or spec.value_key)
                    result = SingleFileImportService().prepare(
                        MODULE_GRID_SPATIAL,
                        imported_value_key,
                        path,
                        expected_len=self.nx * self.ny * self.nz,
                    )
                    if not result.success:
                        raise ValueError("\n".join(result.errors))
                    values = result.values
                else:
                    # Existing projects may still contain a legacy CaseData
                    # locator without intrinsic-keyword provenance.
                    values = parse_property(path)
            array = self._normalize_imported_array(spec, values)
            for record in self._property_edits().get(spec.value_key, []):
                apply_property_operation(array, record, self.nx, self.ny, self.nz, spec)
        except (OSError, TypeError, ValueError, OverflowError):
            self.status_label.setText(f"{spec.key} 数据无法加载，请重新导入。")
            return None
        self._arrays[spec.value_key] = array
        return array

    def _normalize_imported_array(self, spec, values):
        expected = self.nx * self.ny * self.nz
        if len(values) != expected:
            raise ValueError(f"数值数量 {len(values)} 与网格总数 {expected} 不一致。")
        if spec.binary:
            numbers = np.asarray(values, dtype=np.float64)
            if not np.all(np.isfinite(numbers)):
                raise ValueError("ACTNUM 数据中存在无效数值。")
            numbers = numbers.copy()
            numbers[np.isclose(numbers, NULL_VALUE)] = 0.0
            if not np.all(np.isin(numbers, (0.0, 1.0))):
                raise ValueError("ACTNUM 只能包含 0、1 或空值 99999。")
            array = numbers.astype(np.int8)
        else:
            # Grid-property files are already expressed in the units chosen by
            # the user.  Keep the imported values unchanged in the UI instead
            # of applying an implicit permeability conversion.
            array = np.asarray(values, dtype=np.float64).copy()
        self._validate_array(spec, array)
        return array

    @staticmethod
    def _validate_array(spec, array):
        values = array.astype(np.float64)
        valid = values[~np.isclose(values, NULL_VALUE)]
        if not np.all(np.isfinite(valid)):
            raise ValueError("属性数据中存在无效数值。")
        if spec.binary and not np.all(np.isin(valid, (0.0, 1.0))):
            raise ValueError("ACTNUM 只能包含 0 或 1。")
        if spec.permeability and np.any(valid < 0.0):
            raise ValueError("渗透率不能小于 0。")
        if spec.value_key == "matrix_phi" and (
                np.any(valid < 0.0) or np.any(valid > 1.0)):
            raise ValueError("孔隙度必须位于 0 到 1 之间。")

    def _import_property(self):
        spec = self._selected_spec
        path, _ = QFileDialog.getOpenFileName(
            self, f"导入 {spec.key}", "",
            "属性数据 (*.inc *.txt *.dat *.data *.csv);;所有文件 (*)")
        if not path:
            return
        try:
            result = SingleFileImportService().prepare(
                MODULE_GRID_SPATIAL,
                spec.value_key,
                path,
                expected_len=self.nx * self.ny * self.nz,
            )
            if not result.success:
                raise ValueError("\n".join(result.errors))
            array = self._normalize_imported_array(spec, result.values)
        except (OSError, TypeError, ValueError, OverflowError) as exc:
            QMessageBox.warning(self, "导入失败", str(exc) or "属性数据无法解析。")
            return
        edits = self._property_edits()
        edits[spec.value_key] = []
        self._working_values["property_edits"] = edits
        keywords = copy.deepcopy(self._working_source.get("keywords") or {})
        keywords[spec.source_identity] = copy.deepcopy(result.source)
        self._working_source["keywords"] = keywords
        self._arrays[spec.value_key] = array
        self._changed_keys.add(spec.value_key)
        self.status_label.setText(f"已读取 {os.path.basename(path)}，等待应用。")
        self._refresh_table()

    def _property_edits(self):
        return copy.deepcopy(self._working_values.get("property_edits") or {})

    def _has_property_data(self, spec):
        if spec.value_key in self._arrays:
            return True
        path = self._source_path(spec)
        return bool(path and os.path.isfile(path))

    def _available_copy_sources(self, target_spec):
        if not target_spec.permeability:
            return ()
        return tuple(
            source for source in PROPERTY_SPECS
            if (source.permeability
                and source.value_key != target_spec.value_key
                and self._has_property_data(source))
        )

    def _open_copy(self):
        target = self._selected_spec
        if not target.permeability or self._ensure_loaded(target) is not None:
            return
        sources = self._available_copy_sources(target)
        if not sources:
            QMessageBox.information(
                self, "暂无可复制数据", "请先导入其他方向的渗透率属性。")
            return
        dialog = CopyPropertyDialog(target, sources, self)
        if dialog.exec_() != QDialog.Accepted:
            return
        source_by_value = {spec.value_key: spec for spec in sources}
        source = source_by_value.get(dialog.source_value_key())
        if source is not None:
            self._copy_property(source, [target.value_key])

    def _open_box(self):
        spec = self._selected_spec
        if self._ensure_loaded(spec) is None:
            QMessageBox.warning(self, "缺少属性数据", "请先导入当前属性数据。")
            return
        dialog = BoxEditDialog(spec, self.nx, self.ny, self.nz, self)
        if dialog.exec_() == QDialog.Accepted:
            self._apply_edit_record(spec, dialog.record())

    def _apply_edit_record(self, spec, record):
        array = self._ensure_loaded(spec)
        try:
            apply_property_operation(array, record, self.nx, self.ny, self.nz, spec)
        except ValueError as exc:
            QMessageBox.warning(self, "运算无效", str(exc))
            return False
        edits = self._property_edits()
        edits.setdefault(spec.value_key, []).append(copy.deepcopy(record))
        self._working_values["property_edits"] = edits
        self._changed_keys.add(spec.value_key)
        self.status_label.setText("存在尚未应用的属性修改。")
        self._refresh_table()
        return True

    def _copy_property(self, source_spec, target_value_keys):
        source_array = self._ensure_loaded(source_spec)
        keywords = copy.deepcopy(self._working_source.get("keywords") or {})
        source_record = keywords.get(source_spec.source_identity) or {}
        if source_array is None or not source_record.get("resolved_path"):
            QMessageBox.warning(
                self, "无法复制", "当前方向没有可持久化的导入数据。")
            return False

        spec_by_value = {spec.value_key: spec for spec in PROPERTY_SPECS}
        edits = self._property_edits()
        copied = []
        for value_key in target_value_keys:
            target = spec_by_value.get(value_key)
            if target is None or not target.permeability:
                continue
            if self._ensure_loaded(target) is not None:
                continue
            target_record = copy.deepcopy(source_record)
            target_record["copied_from"] = source_spec.key
            keywords[target.source_identity] = target_record
            self._arrays[target.value_key] = source_array.copy()
            edits[target.value_key] = copy.deepcopy(
                edits.get(source_spec.value_key) or [])
            self._changed_keys.add(target.value_key)
            copied.append(target.key)

        if not copied:
            QMessageBox.information(
                self, "无需复制", "所选方向已经存在属性数据。")
            return False
        self._working_source["keywords"] = keywords
        self._working_values["property_edits"] = edits
        self.status_label.setText(
            f"已将 {source_spec.key} 复制到 {'、'.join(copied)}，等待应用。")
        self._refresh_table()
        return True

    def _refresh_table(self):
        spec = self._selected_spec
        array = self._ensure_loaded(spec)
        self.table.setModel(PropertyLayerTableModel(
            array, self.nx, self.ny, self.nz,
            self.layer_spin.value(), self.table))
        enabled = array is not None
        self.box_button.setEnabled(enabled)
        copy_sources = self._available_copy_sources(spec) if not enabled else ()
        self.copy_button.setEnabled(
            not enabled and spec.permeability and bool(copy_sources))
        if not spec.permeability:
            self.copy_button.setToolTip("仅 PERMX、PERMY、PERMZ 支持方向复制")
        elif enabled:
            self.copy_button.setToolTip("当前属性已有数据，无需复制")
        elif copy_sources:
            names = "、".join(source.key for source in copy_sources)
            self.copy_button.setToolTip(f"可从 {names} 复制到当前属性")
        else:
            self.copy_button.setToolTip("暂无可用的其他方向渗透率属性")
        self._update_nav_status()
        if not enabled:
            self.statistics.setText("尚未导入数据")
            return
        values = array.astype(np.float64)
        valid = values[~np.isclose(values, NULL_VALUE)]
        if not len(valid):
            self.statistics.setText("当前属性没有有效数值")
            return
        self.statistics.setText(
            f"最小值：{_format_property_value(np.min(valid))}    "
            f"最大值：{_format_property_value(np.max(valid))}    "
            f"平均值：{_format_property_value(np.mean(valid))}")

    @staticmethod
    def _summary(array):
        values = array.astype(np.float64)
        null_mask = np.isclose(values, NULL_VALUE)
        valid = values[~null_mask]
        return {
            "count": int(len(values)),
            "expected_count": int(len(values)),
            "length_match_grid": True,
            "valid_count": int(len(valid)),
            "null_count": int(np.sum(null_mask)),
            "min": float(np.min(valid)) if len(valid) else None,
            "max": float(np.max(valid)) if len(valid) else None,
            "mean": float(np.mean(valid)) if len(valid) else None,
        }

    def apply_values(self):
        for spec in PROPERTY_SPECS:
            if spec.value_key not in self._arrays:
                continue
            summary_key = "actnum_property" if spec.binary else spec.value_key
            self._working_values[summary_key] = {
                "summary": self._summary(self._arrays[spec.value_key])}
        current = self.project_state.get_module_input_state(MODULE_GRID_SPATIAL)
        if (current is not None
                and current.parsed_data.values == self._working_values
                and (current.source or {}) == self._working_source):
            self.status_label.setText("当前属性数据没有变化。")
            return True
        draft = ModuleInputState.from_dict(self._working_state, MODULE_GRID_SPATIAL)
        draft.parsed_data = ModuleParsedData(values=self._working_values)
        draft.source = copy.deepcopy(self._working_source)
        checks = dict((draft.validation or {}).get("checks") or {})
        checks["网格属性"] = {
            "ok": True,
            "detail": f"已配置 {len(self._arrays)} 项属性",
        }
        draft.validation = {
            **dict(draft.validation or {}),
            "ok": True,
            "errors": [],
            "checks": checks,
        }
        draft.dirty = True
        try:
            committed = self.project_state.replace_module_input_state(
                MODULE_GRID_SPATIAL, draft)
        except (TypeError, ValueError):
            QMessageBox.warning(self, "保存失败", "网格属性未能保存。")
            return False
        self._working_state = committed
        self._working_values = copy.deepcopy(committed.parsed_data.values)
        self._working_source = copy.deepcopy(committed.source or {})
        self._changed_keys.clear()
        self._update_nav_status()
        self.status_label.setText(f"已应用，数据修订号 {committed.revision}")
        self.values_applied.emit(
            MODULE_GRID_SPATIAL, "网格属性",
            copy.deepcopy(self._working_values.get("property_edits") or {}),
        )
        return True

    def _accept_with_apply(self):
        if self.apply_values():
            self.accept()
