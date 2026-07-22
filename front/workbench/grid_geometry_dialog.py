# -*- coding: utf-8 -*-
"""根据模型网格类型编辑或预览几何信息的专用对话框。"""

import copy
import math
import os

import numpy as np
from PyQt5.QtCore import QAbstractTableModel, QModelIndex, Qt, pyqtSignal
from PyQt5.QtGui import QBrush, QColor
from PyQt5.QtWidgets import (
    QDialog, QDialogButtonBox, QDoubleSpinBox, QFileDialog, QFormLayout,
    QFrame, QGridLayout, QGroupBox, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPushButton,
    QSplitter, QStackedWidget, QTableView, QVBoxLayout, QWidget,
)

from ..uniform_parser import parse_grid
from .configuration_status import (
    STATUS_CONFIGURED_COLOR,
    STATUS_MISSING_COLOR,
)
from .input_keyword_registry import MODULE_GRID_SPATIAL
from .input_source_registry import SOURCE_MODE_KEYWORD_FILE
from .module_input_models import ModuleInputState, ModuleParsedData
from .project_state import (
    GRID_TYPE_CARTESIAN,
    GRID_TYPE_CORNER_POINT,
    normalize_model_config,
)
from .single_file_import_service import SingleFileImportService


def _display_number(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "—"
    if not math.isfinite(number):
        return "—"
    return f"{number:.2f}"


def _display_source_number(value):
    """显示导入数组的实际数值精度，不对角点网格数据做两位截断。"""

    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not math.isfinite(number):
        return "—"
    return f"{number:.15g}"


class CoordTableModel(QAbstractTableModel):
    """按柱线顶底端点惰性展示 COORD 数组。"""

    HEADERS = ("I", "J", "端点", "X", "Y", "Z")

    def __init__(self, values=(), nx=0, ny=0, parent=None):
        super().__init__(parent)
        self.values = values or ()
        self.nx = max(0, int(nx or 0))
        self.ny = max(0, int(ny or 0))
        self.pillar_count = min(
            len(self.values) // 6,
            (self.nx + 1) * (self.ny + 1)
            if self.nx >= 0 and self.ny >= 0 else 0,
        )

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else self.pillar_count * 2

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.HEADERS)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or role not in {Qt.DisplayRole, Qt.TextAlignmentRole}:
            return None
        if role == Qt.TextAlignmentRole:
            return int(Qt.AlignCenter)
        pillar = index.row() // 2
        endpoint = index.row() % 2
        stride = self.nx + 1
        values = (
            pillar % stride + 1,
            pillar // stride + 1,
            "顶" if endpoint == 0 else "底",
            self.values[pillar * 6 + endpoint * 3],
            self.values[pillar * 6 + endpoint * 3 + 1],
            self.values[pillar * 6 + endpoint * 3 + 2],
        )
        value = values[index.column()]
        return str(value) if index.column() < 3 else _display_source_number(value)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal and 0 <= section < len(self.HEADERS):
            return self.HEADERS[section]
        return section + 1 if orientation == Qt.Vertical else None


class ZcornTableModel(QAbstractTableModel):
    """按单元惰性展示八个 ZCORN 值。"""

    HEADERS = ("I", "J", "K", "Z1", "Z2", "Z3", "Z4", "Z5", "Z6", "Z7", "Z8")

    def __init__(self, values=(), nx=0, ny=0, nz=0, parent=None):
        super().__init__(parent)
        self.values = values or ()
        self.nx = max(0, int(nx or 0))
        self.ny = max(0, int(ny or 0))
        self.nz = max(0, int(nz or 0))
        expected = self.nx * self.ny * self.nz
        self.cell_count = min(len(self.values) // 8, expected)

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else self.cell_count

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.HEADERS)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or role not in {Qt.DisplayRole, Qt.TextAlignmentRole}:
            return None
        if role == Qt.TextAlignmentRole:
            return int(Qt.AlignCenter)
        cell = index.row()
        layer_size = self.nx * self.ny
        values = (
            cell % self.nx + 1,
            (cell // self.nx) % self.ny + 1,
            cell // layer_size + 1,
            *self.values[cell * 8:cell * 8 + 8],
        )
        value = values[index.column()]
        return str(value) if index.column() < 3 else _display_source_number(value)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal and 0 <= section < len(self.HEADERS):
            return self.HEADERS[section]
        return section + 1 if orientation == Qt.Vertical else None


class GridGeometryDialog(QDialog):
    """几何信息节点专用弹窗，左侧只展示当前网格内部逻辑。"""

    values_applied = pyqtSignal(str, str, dict)

    def __init__(self, project_state, parent=None):
        super().__init__(parent)
        self.project_state = project_state
        self.config = normalize_model_config(
            getattr(project_state, "model_config", None))
        self.grid_type = self.config.get(
            "grid_type", GRID_TYPE_CORNER_POINT)
        self.nx = int(self.config.get("grid_nx", 50))
        self.ny = int(self.config.get("grid_ny", 25))
        self.nz = int(self.config.get("grid_nz", 3))
        self._pending_grid_dimensions = None
        self._corner_grid = None

        current = project_state.get_module_input_state(MODULE_GRID_SPATIAL)
        self._working_state = current or ModuleInputState(
            module_key=MODULE_GRID_SPATIAL,
            parsed_data=ModuleParsedData(),
            validation={"ok": True, "errors": [], "warnings": [], "checks": {}},
        )
        self._working_values = copy.deepcopy(
            self._working_state.parsed_data.values)
        self._working_source = copy.deepcopy(self._working_state.source or {})

        self.setObjectName("gridGeometryDialog")
        self.setWindowTitle("几何信息 (GEOMETRY)")
        self.resize(1080, 760)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)
        root.addWidget(self._header())

        splitter = QSplitter(Qt.Horizontal)
        self.nav = QListWidget()
        self.nav.setObjectName("geometryLogicNav")
        self.nav.setMinimumWidth(150)
        self.nav.setMaximumWidth(190)
        splitter.addWidget(self.nav)
        self.stack = QStackedWidget()
        splitter.addWidget(self.stack)
        splitter.setSizes([165, 895])
        root.addWidget(splitter, 1)

        self.status_label = QLabel("")
        self.status_label.setObjectName("parameterDescription")

        if self.grid_type == GRID_TYPE_CARTESIAN:
            self._build_cartesian_pages()
        else:
            self._build_corner_point_pages()
        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex)
        if self.nav.count():
            self.nav.setCurrentRow(0)

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

    def _header(self):
        frame = QFrame()
        frame.setObjectName("parameterIntro")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(12, 8, 12, 8)
        title = QLabel("几何信息")
        title.setObjectName("parameterTitle")
        layout.addWidget(title)
        layout.addStretch()
        self.type_label = QLabel()
        self.type_label.setObjectName("parameterDescription")
        layout.addWidget(self.type_label)
        self._refresh_header_text()
        return frame

    def _refresh_header_text(self):
        type_name = (
            "笛卡尔网格 (CARTESIAN)"
            if self.grid_type == GRID_TYPE_CARTESIAN
            else "角点网格 (CPG)"
        )
        self.type_label.setText(
            f"当前类型：{type_name}    网格维度：{self.nx} × {self.ny} × {self.nz}")

    def _add_page(self, label, page):
        item = QListWidgetItem(label)
        item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.nav.addItem(item)
        self.stack.addWidget(page)

    def _set_nav_status(self, index, configured):
        item = self.nav.item(index)
        if item is None:
            return
        color = STATUS_CONFIGURED_COLOR if configured else STATUS_MISSING_COLOR
        item.setForeground(QBrush(QColor(color)))
        font = item.font()
        font.setBold(True)
        item.setFont(font)
        item.setToolTip(
            "配置状态：已配置" if configured else "配置状态：尚未配置或数据无效")

    def _update_nav_status(self):
        if self.grid_type == GRID_TYPE_CARTESIAN:
            cartesian = ((self._working_values.get("geometry") or {}).get(
                "cartesian") or {})
            try:
                size_ok = bool(cartesian) and all(
                    key in cartesian and float(cartesian[key]) > 0.0
                    for key in ("lx", "ly", "lz"))
                location_ok = bool(cartesian) and all(
                    key in cartesian
                    and math.isfinite(float(cartesian[key]))
                    for key in (
                        "origin_x", "origin_y", "origin_z", "rotation_deg"))
            except (TypeError, ValueError):
                size_ok = location_ok = False
            self._set_nav_status(0, size_ok)
            self._set_nav_status(1, location_ok)
            return

        grid = self._corner_grid or {}
        dimensions = self._corner_dimensions(grid)
        dimensions_ok = dimensions == (self.nx, self.ny, self.nz)
        coord = np.asarray(grid.get("coord") or [], dtype=np.float64)
        zcorn = np.asarray(grid.get("zcorn") or [], dtype=np.float64)
        coord_ok = bool(
            dimensions_ok
            and len(coord) == 6 * (self.nx + 1) * (self.ny + 1)
            and np.all(np.isfinite(coord)))
        zcorn_ok = bool(
            dimensions_ok
            and len(zcorn) == 8 * self.nx * self.ny * self.nz
            and np.all(np.isfinite(zcorn)))
        self._set_nav_status(0, coord_ok)
        self._set_nav_status(1, zcorn_ok)

    def _build_corner_point_pages(self):
        coord_page, self.coord_summary, self.coord_table = self._corner_page(
            "COORD", "网格柱线坐标 (COORD)")
        zcorn_page, self.zcorn_summary, self.zcorn_table = self._corner_page(
            "ZCORN", "网格角点深度 (ZCORN)")
        self._add_page("COORD", coord_page)
        self._add_page("ZCORN", zcorn_page)
        self._load_existing_corner_grid()

    def _corner_page(self, key, title):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(14, 12, 14, 12)
        toolbar = QHBoxLayout()
        heading = QLabel(title)
        heading.setObjectName("parameterTitle")
        import_button = QPushButton("导入")
        import_button.setObjectName(f"import{key.title()}Button")
        import_button.clicked.connect(self._import_corner_grid)
        toolbar.addWidget(heading)
        toolbar.addStretch()
        toolbar.addWidget(import_button)
        layout.addLayout(toolbar)
        summary = QLabel("尚未导入数据")
        summary.setObjectName("parameterDescription")
        layout.addWidget(summary)
        table = QTableView()
        table.setObjectName(f"{key.lower()}GeometryTable")
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableView.SelectRows)
        table.setEditTriggers(QTableView.NoEditTriggers)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(table, 1)
        return page, summary, table

    def _load_existing_corner_grid(self):
        path = self._corner_source_path()
        if not path or not os.path.isfile(path):
            self._set_corner_models({})
            return
        try:
            record = ((self._working_source.get("keywords") or {}).get(
                "GRID.grid_file") or {})
            if record.get("source_mode") == SOURCE_MODE_KEYWORD_FILE:
                result = SingleFileImportService().prepare(
                    MODULE_GRID_SPATIAL, "grid", path)
                if not result.success:
                    raise ValueError("\n".join(result.errors))
                self._corner_grid = result.data
            else:
                # Existing projects without content-keyword provenance keep
                # their legacy parser path until the later migration step.
                self._corner_grid = parse_grid(path)
        except (OSError, TypeError, ValueError, OverflowError):
            self.status_label.setText("已保存的角点网格源文件无法解析，请重新导入。")
            self._set_corner_models({})
            return
        self._set_corner_models(self._corner_grid)
        dimensions = self._corner_dimensions(self._corner_grid)
        if dimensions != (self.nx, self.ny, self.nz):
            self.status_label.setText(
                "已加载角点网格，但文件维度 "
                f"{dimensions[0]} × {dimensions[1]} × {dimensions[2]} "
                "与模型配置不一致。")
        else:
            self.status_label.setText(f"已加载角点网格：{os.path.basename(path)}")

    def _corner_source_path(self):
        keywords = self._working_source.get("keywords") or {}
        record = keywords.get("GRID.grid_file") or {}
        return str(record.get("resolved_path") or "").strip()

    def _import_corner_grid(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "导入角点网格",
            "",
            "角点网格 (*.grdecl *.GRDECL *.data *.DATA *.inc *.txt);;所有文件 (*)",
        )
        if not path:
            return
        try:
            result = SingleFileImportService().prepare(
                MODULE_GRID_SPATIAL, "grid", path)
            if not result.success:
                raise ValueError("\n".join(result.errors))
            grid = result.data
        except (OSError, TypeError, ValueError, OverflowError) as exc:
            QMessageBox.warning(
                self, "导入失败",
                str(exc) or "所选文件无法解析为包含 SPECGRID、COORD 和 ZCORN 的角点网格。")
            return
        grid_error = self._corner_grid_error(grid)
        if grid_error:
            QMessageBox.warning(self, "导入失败", grid_error)
            return

        dimensions = self._corner_dimensions(grid)
        if dimensions != (self.nx, self.ny, self.nz):
            answer = QMessageBox.question(
                self,
                "网格维度不一致",
                "导入文件的网格维度为 "
                f"{dimensions[0]} × {dimensions[1]} × {dimensions[2]}，"
                "与模型配置不一致。\n是否在应用时同步更新模型配置？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return
            self._pending_grid_dimensions = dimensions
            self.nx, self.ny, self.nz = dimensions
            self._refresh_header_text()

        self._corner_grid = grid
        keywords = copy.deepcopy(self._working_source.get("keywords") or {})
        keywords["GRID.grid_file"] = copy.deepcopy(result.source)
        self._working_source["keywords"] = keywords
        summary = self._corner_grid_summary(grid)
        geometry = copy.deepcopy(self._working_values.get("geometry") or {})
        geometry["corner_point"] = {
            "source_name": os.path.basename(path),
            "coord_value_count": summary["coord_value_count"],
            "zcorn_value_count": summary["zcorn_value_count"],
        }
        self._working_values["geometry"] = geometry
        self._working_values["grid"] = summary
        self._set_corner_models(grid)
        self.status_label.setText(
            f"已读取 {os.path.basename(path)}，等待应用。")

    @staticmethod
    def _corner_dimensions(grid):
        return (
            int(grid.get("nx") or 0),
            int(grid.get("ny") or 0),
            int(grid.get("nz") or 0),
        )

    @staticmethod
    def _corner_grid_error(grid):
        nx, ny, nz = GridGeometryDialog._corner_dimensions(grid)
        if nx <= 0 or ny <= 0 or nz <= 0:
            return "角点网格缺少有效的 SPECGRID 维度。"
        coord = np.asarray(grid.get("coord") or [], dtype=np.float64)
        zcorn = np.asarray(grid.get("zcorn") or [], dtype=np.float64)
        expected_coord = 6 * (nx + 1) * (ny + 1)
        expected_zcorn = 8 * nx * ny * nz
        if len(coord) != expected_coord:
            return f"COORD 数值数量不正确：{len(coord)}，预期 {expected_coord}。"
        if len(zcorn) != expected_zcorn:
            return f"ZCORN 数值数量不正确：{len(zcorn)}，预期 {expected_zcorn}。"
        if not np.all(np.isfinite(coord)) or not np.all(np.isfinite(zcorn)):
            return "COORD 或 ZCORN 中存在无效数值。"
        return ""

    def _set_corner_models(self, grid):
        coord = grid.get("coord") or []
        zcorn = grid.get("zcorn") or []
        nx = int(grid.get("nx") or self.nx)
        ny = int(grid.get("ny") or self.ny)
        nz = int(grid.get("nz") or self.nz)
        self.coord_table.setModel(CoordTableModel(coord, nx, ny, self.coord_table))
        self.zcorn_table.setModel(
            ZcornTableModel(zcorn, nx, ny, nz, self.zcorn_table))
        expected_coord = 6 * (nx + 1) * (ny + 1)
        expected_zcorn = 8 * nx * ny * nz
        self.coord_summary.setText(
            f"数值数量：{len(coord)}    预期：{expected_coord}")
        self.zcorn_summary.setText(
            f"数值数量：{len(zcorn)}    预期：{expected_zcorn}")
        self._update_nav_status()

    @staticmethod
    def _corner_grid_summary(grid):
        nx = int(grid.get("nx") or 0)
        ny = int(grid.get("ny") or 0)
        nz = int(grid.get("nz") or 0)
        coord = np.asarray(grid.get("coord") or [], dtype=np.float64)
        zcorn = np.asarray(grid.get("zcorn") or [], dtype=np.float64)
        actnum = np.asarray(grid.get("actnum") or [], dtype=np.int8)
        bbox_min, bbox_max = GridGeometryDialog._corner_bbox(coord, zcorn)
        return {
            "nx": nx,
            "ny": ny,
            "nz": nz,
            "total_cell_count": nx * ny * nz,
            "active_cell_count": int(np.sum(actnum == 1)),
            "inactive_cell_count": int(np.sum(actnum == 0)),
            "coord_value_count": int(len(coord)),
            "zcorn_value_count": int(len(zcorn)),
            "actnum_value_count": int(len(actnum)),
            "bbox_min": bbox_min,
            "bbox_max": bbox_max,
        }

    @staticmethod
    def _corner_bbox(coord, zcorn):
        if len(coord) >= 6:
            pillars = coord[:len(coord) - len(coord) % 6].reshape((-1, 6))
            x_values = pillars[:, (0, 3)].reshape(-1)
            y_values = pillars[:, (1, 4)].reshape(-1)
            x_min, x_max = float(np.min(x_values)), float(np.max(x_values))
            y_min, y_max = float(np.min(y_values)), float(np.max(y_values))
        else:
            x_min = x_max = y_min = y_max = 0.0
        if len(zcorn):
            z_min, z_max = float(np.min(zcorn)), float(np.max(zcorn))
        else:
            z_min = z_max = 0.0
        return [x_min, y_min, z_min], [x_max, y_max, z_max]

    def _build_cartesian_pages(self):
        geometry = self._working_values.get("geometry") or {}
        values = geometry.get("cartesian") or {}
        self.cartesian_editors = {}
        self.cell_size_fields = {}

        size_page = QWidget()
        size_layout = QVBoxLayout(size_page)
        size_layout.setContentsMargins(14, 12, 14, 12)
        title = QLabel("笛卡尔网格尺寸 (LXYZ)")
        title.setObjectName("parameterTitle")
        size_layout.addWidget(title)

        dimensions = QGroupBox("模型尺寸")
        form = QFormLayout(dimensions)
        for key, label, default in (
                ("lx", "X 方向长度 Lx (m)", 1000.0),
                ("ly", "Y 方向长度 Ly (m)", 500.0),
                ("lz", "Z 方向长度 Lz (m)", 100.0)):
            editor = self._double_editor(values.get(key, default), 0.000001, 1.0e12)
            editor.setObjectName(f"geometry{key.upper()}SpinBox")
            editor.valueChanged.connect(self._refresh_cell_sizes)
            self.cartesian_editors[key] = editor
            form.addRow(label, editor)
        size_layout.addWidget(dimensions)

        derived = QGroupBox("单元尺寸（自动计算）")
        grid = QGridLayout(derived)
        for column, (key, label) in enumerate((
                ("dx", "Dx = Lx / Nx"),
                ("dy", "Dy = Ly / Ny"),
                ("dz", "Dz = Lz / Nz"))):
            field = QLineEdit()
            field.setReadOnly(True)
            field.setObjectName(f"geometry{key.upper()}LineEdit")
            self.cell_size_fields[key] = field
            grid.addWidget(QLabel(label), 0, column)
            grid.addWidget(field, 1, column)
            grid.setColumnStretch(column, 1)
        size_layout.addWidget(derived)
        size_layout.addStretch()

        location_page = QWidget()
        location_layout = QVBoxLayout(location_page)
        location_layout.setContentsMargins(14, 12, 14, 12)
        title = QLabel("空间定位")
        title.setObjectName("parameterTitle")
        location_layout.addWidget(title)
        location = QGroupBox("网格原点与旋转")
        location_form = QFormLayout(location)
        for key, label, default, minimum, maximum in (
                ("origin_x", "网格原点 X (m)", 0.0, -1.0e12, 1.0e12),
                ("origin_y", "网格原点 Y (m)", 0.0, -1.0e12, 1.0e12),
                ("origin_z", "网格原点 Z (m)", 0.0, -1.0e12, 1.0e12),
                ("rotation_deg", "网格旋转角 (°)", 0.0, -360.0, 360.0)):
            editor = self._double_editor(values.get(key, default), minimum, maximum)
            editor.setObjectName(f"geometry{''.join(part.title() for part in key.split('_'))}SpinBox")
            self.cartesian_editors[key] = editor
            location_form.addRow(label, editor)
        location_layout.addWidget(location)
        location_layout.addStretch()

        self._add_page("网格尺寸", size_page)
        self._add_page("空间定位", location_page)
        self._refresh_cell_sizes()
        self._update_nav_status()

    @staticmethod
    def _double_editor(value, minimum, maximum):
        editor = QDoubleSpinBox()
        editor.setRange(float(minimum), float(maximum))
        editor.setDecimals(2)
        editor.setSingleStep(1.0)
        editor.setValue(float(value))
        return editor

    def _refresh_cell_sizes(self, *_args):
        if not hasattr(self, "cell_size_fields"):
            return
        values = {
            "dx": self.cartesian_editors["lx"].value() / self.nx,
            "dy": self.cartesian_editors["ly"].value() / self.ny,
            "dz": self.cartesian_editors["lz"].value() / self.nz,
        }
        for key, value in values.items():
            self.cell_size_fields[key].setText(_display_number(value))

    def _collect_cartesian(self):
        values = {
            key: editor.value()
            for key, editor in self.cartesian_editors.items()
        }
        values.update({
            "dx": values["lx"] / self.nx,
            "dy": values["ly"] / self.ny,
            "dz": values["lz"] / self.nz,
        })
        geometry = copy.deepcopy(self._working_values.get("geometry") or {})
        geometry["cartesian"] = values
        self._working_values["geometry"] = geometry

    def apply_values(self):
        if self.grid_type == GRID_TYPE_CARTESIAN:
            self._collect_cartesian()
        elif self._corner_grid is None:
            QMessageBox.warning(
                self, "几何信息不完整", "请先导入包含 COORD 和 ZCORN 的角点网格文件。")
            return False
        elif self._corner_grid_error(self._corner_grid):
            QMessageBox.warning(
                self, "几何信息不完整",
                self._corner_grid_error(self._corner_grid))
            return False
        elif self._corner_dimensions(self._corner_grid) != (self.nx, self.ny, self.nz):
            dimensions = self._corner_dimensions(self._corner_grid)
            answer = QMessageBox.question(
                self,
                "网格维度不一致",
                "当前角点网格维度与模型配置不一致。\n"
                "是否同步更新模型配置后继续应用？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return False
            self._pending_grid_dimensions = dimensions
            self.nx, self.ny, self.nz = dimensions
            self._refresh_header_text()

        if self._pending_grid_dimensions is not None:
            nx, ny, nz = self._pending_grid_dimensions
            self.project_state.update_model_config(
                grid_nx=nx, grid_ny=ny, grid_nz=nz)
            self._pending_grid_dimensions = None

        current = self.project_state.get_module_input_state(MODULE_GRID_SPATIAL)
        if (current is not None
                and current.parsed_data.values == self._working_values
                and (current.source or {}) == self._working_source):
            self.status_label.setText("当前几何信息没有变化。")
            return True

        draft = ModuleInputState.from_dict(
            self._working_state, MODULE_GRID_SPATIAL)
        draft.parsed_data = ModuleParsedData(values=self._working_values)
        draft.source = copy.deepcopy(self._working_source)
        checks = dict((draft.validation or {}).get("checks") or {})
        checks["几何信息"] = {
            "ok": True,
            "detail": (
                "笛卡尔网格尺寸已设置"
                if self.grid_type == GRID_TYPE_CARTESIAN
                else "COORD/ZCORN 已导入"
            ),
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
            QMessageBox.warning(self, "保存失败", "几何信息未能保存。")
            return False

        self._working_state = committed
        self._working_values = copy.deepcopy(committed.parsed_data.values)
        self._working_source = copy.deepcopy(committed.source or {})
        self._update_nav_status()
        self.status_label.setText(f"已应用，数据修订号 {committed.revision}")
        self.values_applied.emit(
            MODULE_GRID_SPATIAL, "几何信息",
            copy.deepcopy(self._working_values.get("geometry") or {}),
        )
        return True

    def _accept_with_apply(self):
        if self.apply_values():
            self.accept()
