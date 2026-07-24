# -*- coding: utf-8 -*-
"""仿照 COMPASS 设计、根据现有 Corey 参数生成 SWGF 表的窗口。"""

import copy
import math

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.font_manager import FontProperties
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QDoubleValidator, QKeySequence
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QButtonGroup,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
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

from .input_keyword_registry import MODULE_ROCK_PROPERTIES, MODULE_SPEC_BY_KEY
from .module_import_service import validate_module_business_data
from .module_input_models import ModuleInputState, ModuleParsedData
from .relative_permeability_table_parser import (
    parse_relative_permeability_file,
)


NODE_SWGF = "swgf"
CURVE_POINT_COUNT = 21
MODE_TABLE = "table"
MODE_PARAMETERS = "parameters"


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


class _RelativePermeabilityTable(QTableWidget):
    """Spreadsheet-like table that accepts the Excel clipboard format."""

    paste_requested = pyqtSignal(str)

    def __init__(self, rows, columns, parent=None):
        super().__init__(rows, columns, parent)
        self._paste_enabled = False

    def set_paste_enabled(self, enabled):
        self._paste_enabled = bool(enabled)

    def keyPressEvent(self, event):
        if self._paste_enabled and event.matches(QKeySequence.Paste):
            self.paste_requested.emit(QApplication.clipboard().text())
            return
        if self._paste_enabled and event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            for item in self.selectedItems():
                item.setText("")
            return
        super().keyPressEvent(event)


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
        initial_curve = _initial_curve_state(self._working_values)
        self._active_mode = initial_curve["mode"]
        self._parameter_values = initial_curve["parameters"]
        self._table_payload = initial_curve["table_payload"]
        self._table_cells = _table_cells_from_rows(
            self._table_payload.get("rows") or [])
        self._rendering_table = False

        self.setObjectName("relativePermeabilityCompassDialog")
        self.setWindowTitle("相渗曲线")
        self.resize(1180, 720)

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

        self._refresh_inputs()
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
        self.import_button = QPushButton("粘贴 Excel 数据")
        self.import_button.setObjectName("importRelativePermeabilityDataButton")
        self.import_button.clicked.connect(self._paste_clipboard)
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

        mode_group = QGroupBox("输入模式")
        mode_layout = QHBoxLayout(mode_group)
        mode_layout.setContentsMargins(12, 8, 12, 8)
        self.mode_buttons = QButtonGroup(self)
        self.table_mode_button = QRadioButton("表格导入")
        self.parameter_mode_button = QRadioButton("参数计算")
        self.mode_buttons.addButton(self.table_mode_button)
        self.mode_buttons.addButton(self.parameter_mode_button)
        mode_layout.addWidget(self.table_mode_button)
        mode_layout.addWidget(self.parameter_mode_button)
        mode_layout.addStretch()
        layout.addWidget(mode_group)

        self.mode_stack = QStackedWidget()
        self.mode_stack.setObjectName("relativePermeabilityModeStack")
        self.mode_stack.addWidget(self._build_table_import_panel())
        self.mode_stack.addWidget(self._build_parameter_panel())
        layout.addWidget(self.mode_stack)

        self.table_mode_button.toggled.connect(self._mode_changed)
        self.parameter_mode_button.toggled.connect(self._mode_changed)

        self.curve_status = QLabel("等待相渗输入")
        self.curve_status.setObjectName("parameterDescription")
        layout.addWidget(self.curve_status)
        self.curve_table = _RelativePermeabilityTable(0, 3)
        self.curve_table.setObjectName("swgfCurveTable")
        self.curve_table.setHorizontalHeaderLabels((
            "水饱和度\nSw\n—",
            "水相相对渗透率\nKrw\n—",
            "气相相对渗透率\nKrg\n—",
        ))
        self.curve_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.curve_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch)
        self.curve_table.itemChanged.connect(self._table_item_changed)
        self.curve_table.paste_requested.connect(self._paste_text)

        preview_splitter = QSplitter(Qt.Horizontal)
        preview_splitter.setObjectName("relativePermeabilityPreviewSplitter")
        preview_splitter.setChildrenCollapsible(False)
        self.curve_table.setMinimumWidth(390)
        preview_splitter.addWidget(self.curve_table)
        preview_splitter.addWidget(self._build_curve_preview())
        preview_splitter.setStretchFactor(0, 1)
        preview_splitter.setStretchFactor(1, 1)
        preview_splitter.setSizes((455, 455))
        layout.addWidget(preview_splitter, 1)
        return page

    def _build_curve_preview(self):
        group = QGroupBox("相渗曲线预览")
        group.setObjectName("relativePermeabilityPreviewGroup")
        group.setMinimumWidth(390)
        layout = QVBoxLayout(group)
        layout.setContentsMargins(10, 12, 10, 10)

        self.preview_stack = QStackedWidget()
        self.preview_placeholder = QLabel(
            "输入至少两个有效数据点后显示 Krw / Krg 曲线")
        self.preview_placeholder.setObjectName(
            "relativePermeabilityPreviewPlaceholder")
        self.preview_placeholder.setAlignment(Qt.AlignCenter)
        self.preview_placeholder.setWordWrap(True)
        self.preview_stack.addWidget(self.preview_placeholder)

        self.preview_figure = Figure(facecolor="white")
        self.preview_canvas = FigureCanvas(self.preview_figure)
        self.preview_canvas.setObjectName(
            "relativePermeabilityPreviewCanvas")
        self.preview_canvas.setMinimumHeight(330)
        self.preview_stack.addWidget(self.preview_canvas)
        layout.addWidget(self.preview_stack, 1)
        return group

    def _build_table_import_panel(self):
        panel = QGroupBox("表格数据（可编辑）")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        action_row = QHBoxLayout()
        self.paste_button = QPushButton("粘贴")
        self.paste_button.setObjectName(
            "pasteRelativePermeabilityTableButton")
        self.paste_button.clicked.connect(self._paste_clipboard)
        action_row.addWidget(self.paste_button)
        self.add_row_button = QPushButton("添加行")
        self.add_row_button.setObjectName(
            "addRelativePermeabilityTableRowButton")
        self.add_row_button.clicked.connect(self._add_table_row)
        action_row.addWidget(self.add_row_button)
        self.delete_row_button = QPushButton("删除选中行")
        self.delete_row_button.setObjectName(
            "deleteRelativePermeabilityTableRowButton")
        self.delete_row_button.clicked.connect(self._delete_selected_rows)
        action_row.addWidget(self.delete_row_button)
        self.clear_table_button = QPushButton("清空表格")
        self.clear_table_button.setObjectName(
            "clearRelativePermeabilityTableButton")
        self.clear_table_button.clicked.connect(self._clear_table)
        action_row.addWidget(self.clear_table_button)
        action_row.addStretch()
        layout.addLayout(action_row)

        note = QLabel(
            "可从 Excel 复制 Sw、Krw、Krg 三列后，在下方表格选中起始单元格"
            "并按 Ctrl+V；也可直接双击单元格输入。若复制内容包含 "
            "Sw/Krw/Krg 表头，将自动跳过表头。")
        note.setObjectName("parameterDescription")
        note.setWordWrap(True)
        layout.addWidget(note)
        return panel

    def _build_parameter_panel(self):
        panel = QGroupBox("Corey 参数")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 10, 12, 10)

        parameter_rows = (
            ("水相相渗指数", "nw", "—", "nw", None),
            ("气相相渗指数", "ng", "—", "ng", None),
            ("水端点相渗", "Krw_end", "—", "krw_end", 1.0),
            ("气端点相渗", "Krg_end", "—", "krg_end", 1.0),
            ("束缚水饱和度", "Swi", "—", "swi", 1.0),
            ("残余气饱和度", "Sgr", "—", "sgc", 1.0),
        )
        self.parameter_table = QTableWidget(len(parameter_rows), 4)
        self.parameter_table.setObjectName("swgfParameterTable")
        self.parameter_table.setHorizontalHeaderLabels(
            ("参数", "标识", "单位", "参数值"))
        self.parameter_table.setVerticalHeaderLabels(tuple(
            str(index) for index in range(1, len(parameter_rows) + 1)))
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
        self.parameter_table.setMaximumHeight(275)
        layout.addWidget(self.parameter_table)
        return panel

    @staticmethod
    def _readonly_item(text):
        item = QTableWidgetItem(str(text))
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        item.setTextAlignment(Qt.AlignCenter)
        return item

    def _refresh_inputs(self):
        for key, editor in self._editors.items():
            editor.set_value(self._parameter_values.get(key))
        if self._active_mode == MODE_TABLE:
            self.table_mode_button.setChecked(True)
        else:
            self.parameter_mode_button.setChecked(True)
        self._apply_mode()

    def _mode_changed(self):
        if self.table_mode_button.isChecked():
            self._active_mode = MODE_TABLE
        elif self.parameter_mode_button.isChecked():
            self._active_mode = MODE_PARAMETERS
        self._apply_mode()

    def _apply_mode(self):
        table_mode = self._active_mode == MODE_TABLE
        self.mode_stack.setCurrentIndex(0 if table_mode else 1)
        self.import_button.setEnabled(table_mode)
        self.curve_table.set_paste_enabled(table_mode)
        self.curve_table.setEditTriggers(
            (
                QAbstractItemView.DoubleClicked
                | QAbstractItemView.EditKeyPressed
                | QAbstractItemView.AnyKeyPressed
            )
            if table_mode else QAbstractItemView.NoEditTriggers)
        self.curve_table.setSelectionBehavior(
            QAbstractItemView.SelectItems
            if table_mode else QAbstractItemView.SelectRows)
        self.import_button.setToolTip(
            "将剪贴板中的 Sw/Krw/Krg 数据粘贴到表格"
            if table_mode else "参数计算模式下请直接填写 Corey 参数")
        self._refresh_curve()

    def _read_parameters(self, require_complete=False):
        parameters = {}
        missing = []
        for key, editor in self._editors.items():
            value = editor.value()
            parameters[key] = value
            if value is None:
                missing.append(key)
        if require_complete and missing:
            raise ValueError(
                "请完整填写 nw、ng、Krw_end、Krg_end、Swi 和 Sgr。")
        return parameters

    def _collect_values(self):
        values = copy.deepcopy(self._working_values)
        if self._active_mode == MODE_TABLE:
            self._capture_table_cells()
            rows = self._read_table_rows(minimum_points=2)
            curve_state = {
                "mode": MODE_TABLE,
                "table": copy.deepcopy(rows),
            }
            for key in (
                    "n", "nw", "ng", "krw_end", "krg_end", "swi", "sgc"):
                values.pop(key, None)
        else:
            parameters = self._read_parameters(require_complete=True)
            rows = generate_corey_curve(parameters)
            curve_state = {
                "mode": MODE_PARAMETERS,
                "parameters": copy.deepcopy(parameters),
                "table": copy.deepcopy(rows),
            }
            values.update(parameters)
            if math.isclose(
                    parameters["nw"], parameters["ng"],
                    rel_tol=0.0, abs_tol=1e-12):
                values["n"] = parameters["nw"]
            else:
                values.pop("n", None)
        values["relative_permeability"] = curve_state
        return values

    def _refresh_curve(self):
        if self._active_mode == MODE_TABLE:
            self._render_table_editor()
            self._update_table_status()
            return

        try:
            self._parameter_values = self._read_parameters(
                require_complete=False)
            points = generate_corey_curve(self._parameter_values)
        except (TypeError, ValueError, OverflowError) as exc:
            self._render_curve(())
            message = str(exc) or "当前参数无法生成 SWGF 表。"
            self.curve_status.setText(message)
            self._show_preview_placeholder(message)
            return
        self._render_curve(points)
        self._render_curve_preview(points)
        self.curve_status.setText(
            f"已根据独立气水 Corey 指数和端点相渗生成 "
            f"{len(points)} 个数据点")

    def _render_curve(self, points):
        self._rendering_table = True
        self.curve_table.setUpdatesEnabled(False)
        try:
            self.curve_table.setRowCount(len(points))
            for row_index, point in enumerate(points):
                for column, key in enumerate(("sw", "krw", "krg")):
                    display = point.get(
                        f"{key}_text", f"{float(point[key]):.8g}")
                    self.curve_table.setItem(
                        row_index, column, self._readonly_item(display))
        finally:
            self.curve_table.setUpdatesEnabled(True)
            self._rendering_table = False

    def _render_table_editor(self):
        row_count = max(10, len(self._table_cells) + 1)
        self._rendering_table = True
        self.curve_table.setUpdatesEnabled(False)
        try:
            self.curve_table.clearContents()
            self.curve_table.setRowCount(row_count)
            for row_index in range(row_count):
                source_row = (
                    self._table_cells[row_index]
                    if row_index < len(self._table_cells) else ())
                for column in range(3):
                    text = (
                        source_row[column]
                        if column < len(source_row) else "")
                    item = QTableWidgetItem(str(text))
                    item.setTextAlignment(Qt.AlignCenter)
                    self.curve_table.setItem(row_index, column, item)
        finally:
            self.curve_table.setUpdatesEnabled(True)
            self._rendering_table = False

    def _table_item_changed(self, _item):
        if self._rendering_table or self._active_mode != MODE_TABLE:
            return
        self._capture_table_cells()
        self._ensure_trailing_blank_row()
        self._update_table_status()

    def _capture_table_cells(self):
        if self._active_mode != MODE_TABLE:
            return
        cells = []
        for row_index in range(self.curve_table.rowCount()):
            row = []
            for column in range(3):
                item = self.curve_table.item(row_index, column)
                row.append(item.text().strip() if item is not None else "")
            cells.append(row)
        while cells and not any(cells[-1]):
            cells.pop()
        self._table_cells = cells

    def _ensure_trailing_blank_row(self):
        self._rendering_table = True
        try:
            if self.curve_table.rowCount() < 10:
                self.curve_table.setRowCount(10)
            last_row = self.curve_table.rowCount() - 1
            if any(
                    (self.curve_table.item(last_row, column) is not None)
                    and self.curve_table.item(last_row, column).text().strip()
                    for column in range(3)):
                self.curve_table.insertRow(self.curve_table.rowCount())
                last_row += 1
            for column in range(3):
                if self.curve_table.item(last_row, column) is None:
                    self.curve_table.setItem(
                        last_row, column, QTableWidgetItem(""))
        finally:
            self._rendering_table = False

    def _read_table_rows(self, minimum_points=0):
        rows = []
        for row_index, cells in enumerate(self._table_cells, 1):
            texts = [str(value).strip() for value in cells[:3]]
            if not any(texts):
                continue
            if len(texts) < 3 or not all(texts):
                raise ValueError(
                    f"相渗表格第 {row_index} 行不完整，请填写 Sw、Krw、Krg。")
            try:
                numbers = [float(text) for text in texts]
            except ValueError as exc:
                raise ValueError(
                    f"相渗表格第 {row_index} 行包含非数字内容。") from exc
            if not all(math.isfinite(value) for value in numbers):
                raise ValueError(
                    f"相渗表格第 {row_index} 行必须填写有限数字。")
            if not all(0.0 <= value <= 1.0 for value in numbers):
                raise ValueError(
                    f"相渗表格第 {row_index} 行的 Sw、Krw、Krg "
                    "必须位于 0 到 1 之间。")
            if rows and numbers[0] <= rows[-1]["sw"]:
                raise ValueError(
                    f"相渗表格第 {row_index} 行的 Sw 必须严格大于上一行。")
            rows.append({
                "sw": numbers[0],
                "krw": numbers[1],
                "krg": numbers[2],
                "sw_text": texts[0],
                "krw_text": texts[1],
                "krg_text": texts[2],
            })
        if len(rows) < int(minimum_points):
            raise ValueError("相渗表格至少需要两行完整数据。")
        return rows

    def _update_table_status(self):
        try:
            rows = self._read_table_rows()
        except (TypeError, ValueError, OverflowError) as exc:
            message = str(exc)
            self.curve_status.setText(message)
            self._show_preview_placeholder(message)
            return []
        if not rows:
            message = (
                "请从 Excel 粘贴 Sw、Krw、Krg 三列数据，或直接填写表格")
            self.curve_status.setText(message)
            self._show_preview_placeholder(message)
        elif len(rows) == 1:
            message = "已有 1 个数据点；保存至少需要 2 个数据点"
            self.curve_status.setText(message)
            self._show_preview_placeholder(message)
        else:
            self.curve_status.setText(
                f"已有 {len(rows)} 个有效相渗数据点；数据按输入原值保存")
            self._render_curve_preview(rows)
        return rows

    def _render_curve_preview(self, points):
        rows = [
            point for point in points or []
            if isinstance(point, dict)
            and all(point.get(key) is not None for key in ("sw", "krw", "krg"))
        ]
        if len(rows) < 2:
            self._show_preview_placeholder(
                "输入至少两个有效数据点后显示 Krw / Krg 曲线")
            return

        sw_values = [float(point["sw"]) for point in rows]
        krw_values = [float(point["krw"]) for point in rows]
        krg_values = [float(point["krg"]) for point in rows]
        self.preview_figure.clear()
        axis = self.preview_figure.add_subplot(111)
        axis.set_facecolor("#ffffff")
        marker = "o" if len(rows) <= 60 else None
        axis.plot(
            sw_values,
            krw_values,
            color="#2f6fbd",
            linewidth=2.2,
            marker=marker,
            markersize=3.2,
            label="水相 Krw",
        )
        axis.plot(
            sw_values,
            krg_values,
            color="#e07a2d",
            linewidth=2.2,
            marker=marker,
            markersize=3.2,
            label="气相 Krg",
        )
        chinese_font = FontProperties(
            family=["Microsoft YaHei", "SimHei"])
        axis.set_xlim(0.0, 1.0)
        axis.set_ylim(0.0, 1.0)
        axis.set_xlabel("水饱和度 Sw", fontproperties=chinese_font)
        axis.set_ylabel("相对渗透率 Kr", fontproperties=chinese_font)
        axis.grid(True, linestyle="--", linewidth=0.8, alpha=0.38)
        axis.legend(loc="best", frameon=False, prop=chinese_font)
        axis.set_title("气–水相对渗透率", fontproperties=chinese_font)
        for spine in axis.spines.values():
            spine.set_color("#9ba8b8")
        self.preview_figure.tight_layout(pad=1.2)
        self.preview_canvas.draw_idle()
        self.preview_stack.setCurrentWidget(self.preview_canvas)

    def _show_preview_placeholder(self, message):
        self.preview_placeholder.setText(str(
            message or "输入有效数据后显示相渗曲线"))
        self.preview_stack.setCurrentWidget(self.preview_placeholder)

    def _paste_clipboard(self):
        self._paste_text(QApplication.clipboard().text())

    def _paste_text(self, text):
        try:
            matrix, had_header = _parse_clipboard_table(text)
        except ValueError as exc:
            QMessageBox.warning(self, "粘贴失败", str(exc))
            return
        start_row = max(0, self.curve_table.currentRow())
        start_column = max(0, self.curve_table.currentColumn())
        if had_header:
            start_column = 0
        widest = max(len(row) for row in matrix)
        if start_column + widest > 3:
            QMessageBox.warning(
                self,
                "粘贴失败",
                "粘贴数据超出 Sw、Krw、Krg 三列，请重新选择起始单元格。",
            )
            return

        required_rows = start_row + len(matrix)
        if self.curve_table.rowCount() <= required_rows:
            self.curve_table.setRowCount(required_rows + 1)
        self._rendering_table = True
        try:
            for row_offset, row in enumerate(matrix):
                for column_offset, value in enumerate(row):
                    row_index = start_row + row_offset
                    column = start_column + column_offset
                    item = self.curve_table.item(row_index, column)
                    if item is None:
                        item = QTableWidgetItem()
                        self.curve_table.setItem(row_index, column, item)
                    item.setText(value.strip())
                    item.setTextAlignment(Qt.AlignCenter)
        finally:
            self._rendering_table = False
        self._capture_table_cells()
        self._ensure_trailing_blank_row()
        self._update_table_status()
        self.import_status.setText(
            f"已粘贴 {len(matrix)} 行数据，等待确定")

    def _add_table_row(self):
        current = self.curve_table.currentRow()
        target = current + 1 if current >= 0 else self.curve_table.rowCount()
        self._rendering_table = True
        try:
            self.curve_table.insertRow(target)
            for column in range(3):
                self.curve_table.setItem(target, column, QTableWidgetItem(""))
        finally:
            self._rendering_table = False
        self._capture_table_cells()
        self.curve_table.setCurrentCell(target, 0)
        self.curve_table.editItem(self.curve_table.item(target, 0))

    def _delete_selected_rows(self):
        rows = sorted(
            {index.row() for index in self.curve_table.selectedIndexes()},
            reverse=True,
        )
        if not rows and self.curve_table.currentRow() >= 0:
            rows = [self.curve_table.currentRow()]
        for row_index in rows:
            self.curve_table.removeRow(row_index)
        self._capture_table_cells()
        self._ensure_trailing_blank_row()
        self._update_table_status()

    def _clear_table(self):
        self._table_cells = []
        self._render_table_editor()
        self._update_table_status()
        self.import_status.setText("表格已清空")

    def load_table_file(self, path):
        self._table_payload = parse_relative_permeability_file(path)
        self._table_cells = _table_cells_from_rows(
            self._table_payload.get("rows") or [])
        self._active_mode = MODE_TABLE
        self.table_mode_button.setChecked(True)
        self._apply_mode()
        count = len(self._table_payload.get("rows") or [])
        self.import_status.setText(f"已读取 {count} 个相渗数据点，等待确定")
        return copy.deepcopy(self._table_payload)

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


def _table_cells_from_rows(rows):
    cells = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        cells.append([
            _stored_table_cell_text(row, "sw"),
            _stored_table_cell_text(row, "krw"),
            _stored_table_cell_text(row, "krg"),
        ])
    return cells


def _stored_table_cell_text(row, key):
    display = row.get(f"{key}_text")
    if display not in (None, ""):
        return str(display)
    value = row.get(key)
    return "" if value is None else f"{float(value):.12g}"


def _parse_clipboard_table(text):
    raw_lines = str(text or "").replace("\r\n", "\n").replace(
        "\r", "\n").split("\n")
    while raw_lines and not raw_lines[-1].strip():
        raw_lines.pop()
    while raw_lines and not raw_lines[0].strip():
        raw_lines.pop(0)
    if not raw_lines:
        raise ValueError("剪贴板中没有可粘贴的数据。")

    matrix = []
    for line in raw_lines:
        if "\t" in line:
            row = line.split("\t")
        elif "," in line:
            row = line.split(",")
        else:
            row = [line]
        matrix.append([cell.strip() for cell in row])

    normalized_header = [
        cell.strip().lower().replace(" ", "")
        for cell in matrix[0]
    ]
    had_header = (
        len(normalized_header) >= 3
        and normalized_header[:3] == ["sw", "krw", "krg"]
    )
    if had_header:
        matrix.pop(0)
    if not matrix or not any(any(cell for cell in row) for row in matrix):
        raise ValueError("剪贴板中只有表头，没有相渗数据。")
    if any(len(row) > 3 for row in matrix):
        raise ValueError("每行最多只能粘贴 Sw、Krw、Krg 三列数据。")
    return matrix, had_header


def generate_corey_curve(parameters, point_count=CURVE_POINT_COUNT):
    """按现有气水 Corey 公式的独立指数、端点扩展生成曲线。"""

    required = ("nw", "ng", "krw_end", "krg_end", "swi", "sgc")
    if any(parameters.get(key) is None for key in required):
        raise ValueError(
            "请完整填写 nw、ng、Krw_end、Krg_end、Swi 和 Sgr。")

    values = {key: float(parameters[key]) for key in required}
    if not all(math.isfinite(value) for value in values.values()):
        raise ValueError("相渗参数必须是有限数字。")
    if values["nw"] <= 0.0 or values["ng"] <= 0.0:
        raise ValueError("气相和水相相渗指数必须大于 0。")
    for key, title in (
            ("krw_end", "水端点相渗"),
            ("krg_end", "气端点相渗"),
            ("swi", "Swi"),
            ("sgc", "Sgr")):
        if not 0.0 <= values[key] <= 1.0:
            raise ValueError(f"{title}必须位于 0 到 1 之间。")
    denominator = 1.0 - values["swi"] - values["sgc"]
    if denominator <= 0.0:
        raise ValueError("Swi + Sgr 必须小于 1。")

    count = int(point_count)
    if count < 2:
        raise ValueError("相渗曲线至少需要两个数据点。")
    points = []
    for index in range(count):
        effective = index / (count - 1)
        sw = values["swi"] + denominator * effective
        krw = values["krw_end"] * effective ** values["nw"]
        krg = values["krg_end"] * (1.0 - effective) ** values["ng"]
        points.append({
            "sw": sw,
            "krw": krw,
            "krg": krg,
        })
    return points


def _initial_curve_state(values):
    stored = copy.deepcopy(
        (values or {}).get("relative_permeability") or {})
    mode = str(stored.get("mode") or MODE_PARAMETERS)
    if mode not in {MODE_TABLE, MODE_PARAMETERS}:
        mode = MODE_PARAMETERS

    stored_parameters = dict(stored.get("parameters") or {})
    legacy_exponent = (values or {}).get("n")
    parameters = {
        "nw": stored_parameters.get(
            "nw", (values or {}).get("nw", legacy_exponent)),
        "ng": stored_parameters.get(
            "ng", (values or {}).get("ng", legacy_exponent)),
        "krw_end": stored_parameters.get(
            "krw_end", (values or {}).get("krw_end", 1.0)),
        "krg_end": stored_parameters.get(
            "krg_end", (values or {}).get("krg_end", 1.0)),
        "swi": stored_parameters.get("swi", (values or {}).get("swi")),
        "sgc": stored_parameters.get("sgc", (values or {}).get("sgc")),
    }

    table_payload = {}
    if mode == MODE_TABLE:
        rows = copy.deepcopy(stored.get("table") or [])
        table_payload = {
            "source_path": str(stored.get("source_path") or ""),
            "file_name": str(stored.get("file_name") or ""),
            "columns": ["SW", "KRW", "KRG"],
            "rows": rows,
            "summary": {
                "point_count": len(rows),
                "sw_min": rows[0].get("sw") if rows else None,
                "sw_max": rows[-1].get("sw") if rows else None,
            },
        }
    return {
        "mode": mode,
        "parameters": parameters,
        "table_payload": table_payload,
    }


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
    "MODE_PARAMETERS",
    "MODE_TABLE",
    "NODE_SWGF",
    "RelativePermeabilityCompassDialog",
    "generate_corey_curve",
]
