# -*- coding: utf-8 -*-
"""仿照 COMPASS 设计的独立井与生产控制输入窗口。"""

import copy
import hashlib
import math
import os
from dataclasses import dataclass

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
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

from ..uniform_parser import parse_wells
from .input_keyword_registry import MODULE_WELL_PRODUCTION
from .module_import_service import (
    validate_module_business_data,
    well_business_data,
)
from .module_input_models import ModuleInputState, ModuleParsedData
from .well_file_classifier import identify_well_file_roles


WELL_NAME_ROLE = Qt.UserRole
COMPLETION_RECORD_ROLE = Qt.UserRole + 1

CONNECTION_LABELS = {
    "matrix": "基质 (matrix)",
    "fracture": "裂缝 (fracture)",
    "matrix_and_fracture": "基质与裂缝 (matrix + fracture)",
    "none": "未连接 (none)",
}

@dataclass(frozen=True)
class WellPropertySpec:
    source_index: int
    key: str
    title: str
    symbol: str
    unit: str = "NA"


# Keep only COMPASS rows 1-8 and 13. The current project does not yet provide
# genuine grid indices or a well index, so those values remain blank until the
# later data-mapping steps rather than receiving synthetic defaults.
WELL_PROPERTY_SPECS = (
    WellPropertySpec(1, "completion_name", "名称", "Name"),
    WellPropertySpec(2, "grid_i", "X方向网格", "I"),
    WellPropertySpec(3, "grid_j", "Y方向网格", "J"),
    WellPropertySpec(4, "grid_k1", "Z方向起始网格", "K1"),
    WellPropertySpec(5, "grid_k2", "Z方向结束网格", "K2"),
    WellPropertySpec(6, "status", "开关标志", "Status"),
    WellPropertySpec(7, "perforation_type", "射孔类型", "Perforation"),
    WellPropertySpec(8, "well_index", "井指数", "WI", "m·mD"),
    WellPropertySpec(13, "well_radius", "井半径", "Rw", "m"),
)


class WellProductionCompassDialog(QDialog):
    """Three-pane editor for imported well and production-control data."""

    import_requested = pyqtSignal()
    values_applied = pyqtSignal(str, str, dict)

    def __init__(self, project_state, parent=None):
        super().__init__(parent)
        if project_state is None:
            raise ValueError("project_state is required")
        self.project_state = project_state
        self.values_were_applied = False
        existing = project_state.get_module_input_state(
            MODULE_WELL_PRODUCTION)
        self._working_state = (
            ModuleInputState.from_dict(existing)
            if existing is not None else ModuleInputState(
                module_key=MODULE_WELL_PRODUCTION,
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
        self._working_source = copy.deepcopy(self._working_state.source)
        self._refreshing_ui = False
        self._visible_completions = []
        self._current_completion = None
        self._shown_property_texts = {}

        self.setObjectName("wellProductionCompassDialog")
        self.setWindowTitle("井与生产控制")
        self.resize(1120, 730)

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(9)
        root.addWidget(self._build_header())

        splitter = QSplitter(Qt.Horizontal)
        splitter.setObjectName("wellProductionCompassSplitter")
        splitter.addWidget(self._build_well_panel())
        splitter.addWidget(self._build_completion_panel())
        splitter.addWidget(self._build_property_panel())
        splitter.setSizes([205, 220, 695])
        root.addWidget(splitter, 1)

        buttons = QDialogButtonBox()
        self.ok_button = QPushButton("确定")
        self.cancel_button = QPushButton("取消")
        buttons.addButton(self.ok_button, QDialogButtonBox.AcceptRole)
        buttons.addButton(self.cancel_button, QDialogButtonBox.RejectRole)
        self.ok_button.clicked.connect(self._accept_values)
        self.cancel_button.clicked.connect(self.reject)
        root.addWidget(buttons)

        self._refresh_well_list(select_first=True)

    def _build_header(self):
        frame = QFrame()
        frame.setObjectName("wellProductionCompassHeader")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(12, 8, 12, 8)
        title = QLabel("井与生产控制")
        title.setObjectName("parameterTitle")
        layout.addWidget(title)
        layout.addStretch()
        self.import_status = QLabel("等待导入井数据")
        self.import_status.setObjectName("parameterDescription")
        layout.addWidget(self.import_status)
        self.import_button = QPushButton("导入")
        self.import_button.setObjectName("importWellProductionDataButton")
        self.import_button.clicked.connect(self._request_import)
        layout.addWidget(self.import_button)
        return frame

    def _build_well_panel(self):
        panel, layout = self._panel("井名称")
        self.well_tree = QTreeWidget()
        self.well_tree.setObjectName("wellNameTree")
        self.well_tree.setHeaderHidden(True)
        self.well_tree.setSelectionMode(QAbstractItemView.SingleSelection)
        self.well_tree.currentItemChanged.connect(
            self._well_selection_changed)
        layout.addWidget(self.well_tree, 1)
        return panel

    def _build_completion_panel(self):
        panel, layout = self._panel("射孔名称")
        self.completion_table = QTableWidget(0, 1)
        self.completion_table.setObjectName("wellCompletionNameTable")
        self.completion_table.setHorizontalHeaderLabels(("射孔名称",))
        self.completion_table.setEditTriggers(
            QAbstractItemView.NoEditTriggers)
        self.completion_table.setSelectionBehavior(
            QAbstractItemView.SelectRows)
        self.completion_table.setSelectionMode(
            QAbstractItemView.SingleSelection)
        self.completion_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch)
        self.completion_table.currentCellChanged.connect(
            self._completion_selection_changed)
        layout.addWidget(self.completion_table, 1)
        return panel

    def _build_property_panel(self):
        panel, layout = self._panel("射孔属性")
        self.property_table = QTableWidget(
            len(WELL_PROPERTY_SPECS), 4)
        self.property_table.setObjectName("wellCompletionPropertyTable")
        self.property_table.setHorizontalHeaderLabels(
            ("参数", "标识", "单位", "参数值"))
        self.property_table.setVerticalHeaderLabels(tuple(
            str(index) for index in range(1, len(WELL_PROPERTY_SPECS) + 1)))
        self.property_table.setEditTriggers(
            QAbstractItemView.DoubleClicked
            | QAbstractItemView.EditKeyPressed
            | QAbstractItemView.SelectedClicked)
        for row, spec in enumerate(WELL_PROPERTY_SPECS):
            self.property_table.setItem(
                row, 0, self._readonly_item(spec.title))
            self.property_table.setItem(
                row, 1, self._readonly_item(spec.symbol))
            self.property_table.setItem(
                row, 2, self._readonly_item(spec.unit))
            self.property_table.setItem(
                row, 3, QTableWidgetItem(""))
        header = self.property_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        self.property_table.verticalHeader().setDefaultSectionSize(36)
        layout.addWidget(self.property_table, 1)
        return panel

    @staticmethod
    def _panel(title):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(7)
        label = QLabel(title)
        label.setObjectName("parameterTitle")
        layout.addWidget(label)
        return panel, layout

    @staticmethod
    def _readonly_item(text, center=True):
        item = QTableWidgetItem(str(text))
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        if center:
            item.setTextAlignment(Qt.AlignCenter)
        return item

    def _request_import(self):
        if not self._commit_visible_property_edits():
            return
        self.import_requested.emit()
        first_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择第一个井数据文件",
            "",
            "井数据 (*.csv);;所有文件 (*)",
        )
        if not first_path:
            return
        second_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择第二个井数据文件",
            os.path.dirname(os.path.abspath(first_path)),
            "井数据 (*.csv);;所有文件 (*)",
        )
        if not second_path:
            return

        try:
            track_path, completion_path = identify_well_file_roles(
                first_path, second_path)
        except (OSError, UnicodeError, ValueError) as exc:
            QMessageBox.warning(
                self,
                "文件识别失败",
                str(exc) or "无法根据CSV表头识别井数据文件。",
            )
            return
        try:
            wells = well_business_data(
                parse_wells(track_path, completion_path))
        except (OSError, TypeError, ValueError, UnicodeError):
            QMessageBox.warning(
                self,
                "导入失败",
                "井数据联合解析失败，请检查井轨迹文件和完井与井控文件。",
            )
            return
        well_rows = [
            row for row in wells.get("well_list") or []
            if isinstance(row, dict)
            and str(row.get("well_name") or "").strip()
        ]
        if not well_rows:
            QMessageBox.warning(
                self, "导入失败", "所选文件中没有解析到有效井数据。")
            return

        absolute_track = os.path.abspath(track_path)
        absolute_completion = os.path.abspath(completion_path)
        working_values = copy.deepcopy(self._working_values)
        working_values["wells"] = copy.deepcopy(wells)
        working_source = copy.deepcopy(self._working_source)
        keywords = dict(working_source.get("keywords") or {})
        keywords["WELL.well_track_file"] = _direct_source_record(
            absolute_track, "well_tracks")
        keywords["WELL.well_completion_file"] = _direct_source_record(
            absolute_completion, "well_completions")
        working_source["keywords"] = keywords
        direct_imports = dict(working_source.get("direct_imports") or {})
        direct_imports["wells"] = {
            "well_tracks": absolute_track,
            "well_completions": absolute_completion,
        }
        working_source["direct_imports"] = direct_imports

        self._working_values = working_values
        self._working_source = working_source
        self._refresh_well_list(select_first=True)
        completion_count = int(
            (wells.get("summary") or {}).get(
                "completion_definition_count") or 0)
        self.import_status.setText(
            f"已预览 {len(well_rows)} 口井、{completion_count} 个射孔；点击确定后保存")

    def _refresh_well_list(self, select_first=False):
        wells = self._working_values.get("wells") or {}
        rows = [
            row for row in wells.get("well_list") or []
            if isinstance(row, dict)
            and str(row.get("well_name") or "").strip()
        ]
        rows.sort(key=lambda row: str(row.get("well_name") or ""))
        target_name = ""
        prior_refresh = self._refreshing_ui
        self._refreshing_ui = True
        self.well_tree.blockSignals(True)
        try:
            self.well_tree.clear()
            for row in rows:
                well_name = str(row.get("well_name") or "").strip()
                item = QTreeWidgetItem([well_name])
                item.setData(0, WELL_NAME_ROLE, well_name)
                item.setIcon(
                    0, self.style().standardIcon(QStyle.SP_FileIcon))
                self.well_tree.addTopLevelItem(item)
            if select_first and self.well_tree.topLevelItemCount():
                item = self.well_tree.topLevelItem(0)
                self.well_tree.setCurrentItem(item)
                target_name = str(item.data(0, WELL_NAME_ROLE) or "")
        finally:
            self.well_tree.blockSignals(False)
            self._refreshing_ui = prior_refresh
        if target_name and not prior_refresh:
            self._populate_completion_names(target_name)
        elif not rows:
            self._populate_completion_names("")
        if rows:
            completion_count = int(
                (wells.get("summary") or {}).get(
                    "completion_definition_count") or 0)
            self.import_status.setText(
                f"已加载 {len(rows)} 口井、{completion_count} 个射孔")

    def _well_selection_changed(self, current, previous):
        if self._refreshing_ui:
            return
        if not self._commit_visible_property_edits():
            if previous is not None:
                self._refreshing_ui = True
                try:
                    self.well_tree.setCurrentItem(previous)
                finally:
                    self._refreshing_ui = False
            return
        well_name = (
            str(current.data(0, WELL_NAME_ROLE) or "")
            if current is not None else ""
        )
        self._populate_completion_names(well_name)

    def _populate_completion_names(self, well_name):
        wells = self._working_values.get("wells") or {}
        records = [
            row for row in wells.get("completions") or []
            if isinstance(row, dict)
            and str(row.get("well_name") or "").strip() == well_name
            and str(row.get("event") or "").strip().upper() == "PERF"
            and str(row.get("comp_id") or "").strip()
        ]
        unique = {}
        for row in records:
            unique.setdefault(str(row.get("comp_id") or "").strip(), row)
        self._visible_completions = [
            unique[key] for key in sorted(unique)
        ]

        prior_refresh = self._refreshing_ui
        self._refreshing_ui = True
        self._current_completion = None
        self.completion_table.blockSignals(True)
        try:
            self.completion_table.setRowCount(len(self._visible_completions))
            for row_index, completion in enumerate(
                    self._visible_completions):
                item = self._readonly_item(
                    completion.get("comp_id", ""), center=False)
                item.setData(COMPLETION_RECORD_ROLE, completion)
                self.completion_table.setItem(row_index, 0, item)
            if self._visible_completions:
                self.completion_table.setCurrentCell(0, 0)
        finally:
            self.completion_table.blockSignals(False)
            self._refreshing_ui = prior_refresh
        if self._visible_completions:
            self._show_completion_properties(self._visible_completions[0])
        else:
            self._show_completion_properties({})

    def _completion_selection_changed(
            self, current_row, current_column, previous_row,
            previous_column):
        del current_column, previous_column
        if self._refreshing_ui:
            return
        if not self._commit_visible_property_edits():
            if previous_row >= 0:
                self._refreshing_ui = True
                try:
                    self.completion_table.setCurrentCell(previous_row, 0)
                finally:
                    self._refreshing_ui = False
            return
        if 0 <= current_row < len(self._visible_completions):
            self._show_completion_properties(
                self._visible_completions[current_row])
        else:
            self._show_completion_properties({})

    def _show_completion_properties(self, completion):
        self._current_completion = completion if completion else None
        values = {
            "completion_name": completion.get("comp_id"),
            "grid_i": completion.get("grid_i"),
            "grid_j": completion.get("grid_j"),
            "grid_k1": completion.get("grid_k1"),
            "grid_k2": completion.get("grid_k2"),
            "status": (
                _status_label(completion.get("status"))
                or self._derived_completion_status(completion)
            ),
            "perforation_type": (
                _connection_label(
                    completion.get("perforation_type")
                    or completion.get("connection_target"))
            ),
            "well_index": completion.get("well_index"),
            "well_radius": completion.get(
                "rw_m", completion.get("well_radius")),
        }
        for row, spec in enumerate(WELL_PROPERTY_SPECS):
            text = _display_value(values.get(spec.key))
            self.property_table.item(row, 3).setText(text)
            self._shown_property_texts[spec.key] = text

    def _derived_completion_status(self, completion):
        if not completion:
            return ""
        well_name = str(completion.get("well_name") or "").strip()
        comp_id = str(completion.get("comp_id") or "").strip()
        wells = self._working_values.get("wells") or {}
        events = [
            row for row in wells.get("completions") or []
            if isinstance(row, dict)
            and str(row.get("well_name") or "").strip() == well_name
            and str(row.get("comp_id") or "").strip() == comp_id
            and str(row.get("event") or "").strip().upper()
            in {"OPEN", "SHUT"}
        ]
        if not events:
            return ""
        events.sort(key=lambda row: (
            _sortable_number(row.get("date", row.get("date_day"))),
            int(row.get("source_row") or 0),
        ))
        event = str(events[-1].get("event") or "").strip().upper()
        return "开启 (OPEN)" if event == "OPEN" else "关闭 (SHUT)"

    def _commit_visible_property_edits(self):
        if self._refreshing_ui or self._current_completion is None:
            return True
        candidate = {}
        entered_texts = {}
        for row, spec in enumerate(WELL_PROPERTY_SPECS):
            text = self.property_table.item(row, 3).text().strip()
            entered_texts[spec.key] = text
            try:
                candidate[spec.key] = _coerce_property_value(spec.key, text)
            except ValueError as exc:
                self.property_table.setCurrentCell(row, 3)
                QMessageBox.warning(
                    self, "参数无效", str(exc) or f"{spec.title}填写无效。")
                return False

        changed = {
            key for key, text in entered_texts.items()
            if text != self._shown_property_texts.get(key, "")
        }
        if not changed:
            return True

        record = self._current_completion
        old_name = str(record.get("comp_id") or "").strip()
        well_name = str(record.get("well_name") or "").strip()
        new_name = (
            str(candidate["completion_name"] or "").strip()
            if "completion_name" in changed else old_name
        )
        if not new_name:
            QMessageBox.warning(self, "参数无效", "射孔名称不能为空。")
            return False

        related = [
            row for row in (
                (self._working_values.get("wells") or {}).get(
                    "completions") or [])
            if isinstance(row, dict)
            and str(row.get("well_name") or "").strip() == well_name
            and str(row.get("comp_id") or "").strip() == old_name
        ]
        target = (
            _internal_connection(candidate["perforation_type"])
            if "perforation_type" in changed else None
        )
        for row in related:
            if "completion_name" in changed:
                row["comp_id"] = new_name
                if str(row.get("referenced_completion") or "").strip() == old_name:
                    row["referenced_completion"] = new_name
            if "well_radius" in changed:
                if candidate["well_radius"] is None:
                    row.pop("rw_m", None)
                else:
                    row["rw_m"] = candidate["well_radius"]
            if "perforation_type" in changed:
                _apply_connection_target(row, target)

        if "status" in changed:
            status = _internal_status(candidate["status"])
            if status:
                record["status"] = status
            else:
                record.pop("status", None)
        for key in ("grid_i", "grid_j", "grid_k1", "grid_k2", "well_index"):
            if key not in changed:
                continue
            value = candidate[key]
            if value is None:
                record.pop(key, None)
            else:
                record[key] = value

        for row_index, visible in enumerate(self._visible_completions):
            if visible is record:
                item = self.completion_table.item(row_index, 0)
                if item is not None:
                    item.setText(new_name)
                break
        self._shown_property_texts = dict(entered_texts)
        return True

    def _accept_values(self):
        if not self._commit_visible_property_edits():
            return
        errors = _validate_well_records(self._working_values)
        business_validation = validate_module_business_data(
            MODULE_WELL_PRODUCTION, self._working_values)
        errors.extend(business_validation.get("errors") or [])
        if errors:
            QMessageBox.warning(
                self,
                "井属性校验未通过",
                "\n".join(dict.fromkeys(errors)),
            )
            return

        draft = ModuleInputState.from_dict(self._working_state)
        draft.parsed_data = ModuleParsedData(
            values=copy.deepcopy(self._working_values))
        draft.source = copy.deepcopy(self._working_source)
        current_validation = copy.deepcopy(draft.validation or {})
        checks = dict(current_validation.get("checks") or {})
        checks.update(business_validation.get("checks") or {})
        warnings = list(dict.fromkeys(
            list(current_validation.get("warnings") or [])
            + list(business_validation.get("warnings") or [])
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
            MODULE_WELL_PRODUCTION)
        if current is not None and _state_content(current) == _state_content(draft):
            self.accept()
            return
        if current is None and not self._working_values:
            self.accept()
            return
        try:
            committed = self.project_state.replace_module_input_state(
                MODULE_WELL_PRODUCTION, draft)
        except (TypeError, ValueError):
            QMessageBox.warning(
                self, "保存失败", "井与生产控制数据未能保存。")
            return

        self._working_state = committed
        self._working_values = copy.deepcopy(
            committed.parsed_data.values)
        self._working_source = copy.deepcopy(committed.source)
        self.values_were_applied = True
        self.values_applied.emit(
            MODULE_WELL_PRODUCTION,
            "井与生产控制",
            _compact_values(self._working_values),
        )
        self.accept()


def _direct_source_record(path, value_key):
    absolute_path = os.path.abspath(path)
    try:
        stat = os.stat(absolute_path)
        digest = hashlib.sha256()
        with open(absolute_path, "rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
        source_size = int(stat.st_size)
        modified_ns = int(stat.st_mtime_ns)
        source_sha256 = digest.hexdigest()
    except OSError:
        source_size = 0
        modified_ns = 0
        source_sha256 = ""
    return {
        "raw_value": absolute_path,
        "resolved_path": absolute_path,
        "exists": os.path.isfile(absolute_path),
        "source_mode": "paired_well_files",
        "module_key": MODULE_WELL_PRODUCTION,
        "value_key": value_key,
        "source_size": source_size,
        "modified_ns": modified_ns,
        "source_sha256": source_sha256,
    }


def _connection_label(value):
    key = str(value or "").strip()
    return CONNECTION_LABELS.get(key, key)


def _display_value(value):
    if value in (None, ""):
        return ""
    if isinstance(value, float):
        return f"{value:.12g}"
    return str(value)


def _sortable_number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _coerce_property_value(key, text):
    value = str(text or "").strip()
    if key == "completion_name":
        return value
    if key == "status":
        if not value:
            return None
        if _internal_status(value) is None:
            raise ValueError("开关标志只能填写 OPEN/开启 或 SHUT/关闭。")
        return value
    if key == "perforation_type":
        if not value:
            return None
        if _internal_connection(value) is None:
            raise ValueError(
                "射孔类型只能填写基质、裂缝、基质与裂缝或未连接。")
        return value
    if not value:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("该参数必须填写有效数字。") from exc
    if not math.isfinite(number):
        raise ValueError("该参数必须填写有限数字。")
    if key in {"grid_i", "grid_j", "grid_k1", "grid_k2"}:
        if not number.is_integer() or number < 1:
            raise ValueError("网格编号必须是大于或等于 1 的整数。")
        return int(number)
    if key == "well_index" and number < 0:
        raise ValueError("井指数不能小于 0。")
    if key == "well_radius" and number <= 0:
        raise ValueError("井半径必须大于 0。")
    return number


def _internal_status(value):
    text = str(value or "").strip().upper()
    if not text:
        return None
    if "OPEN" in text or "开启" in text or text == "开":
        return "OPEN"
    if "SHUT" in text or "关闭" in text or text == "关":
        return "SHUT"
    return None


def _status_label(value):
    status = _internal_status(value)
    if status == "OPEN":
        return "开启 (OPEN)"
    if status == "SHUT":
        return "关闭 (SHUT)"
    return ""


def _internal_connection(value):
    text = str(value or "").strip().lower()
    if not text:
        return None
    if ("matrix_and_fracture" in text
            or ("matrix" in text and "fracture" in text)
            or ("基质" in text and "裂缝" in text)):
        return "matrix_and_fracture"
    if "matrix" in text or "基质" in text:
        return "matrix"
    if "fracture" in text or "裂缝" in text:
        return "fracture"
    if "none" in text or "未连接" in text:
        return "none"
    return None


def _apply_connection_target(record, target):
    if not target:
        for key in (
                "connection_target", "connect_matrix",
                "connect_fracture", "is_fractured",
                "perforation_type"):
            record.pop(key, None)
        return
    record["connection_target"] = target
    record.pop("perforation_type", None)
    record["connect_matrix"] = int(
        target in {"matrix", "matrix_and_fracture"})
    record["connect_fracture"] = int(
        target in {"fracture", "matrix_and_fracture"})
    record["is_fractured"] = int(
        target in {"fracture", "matrix_and_fracture"})


def _validate_well_records(values):
    errors = []
    wells = values.get("wells") or {}
    definitions = [
        row for row in wells.get("completions") or []
        if isinstance(row, dict)
        and str(row.get("event") or "").strip().upper() == "PERF"
    ]
    identifiers = [
        (
            str(row.get("well_name") or "").strip(),
            str(row.get("comp_id") or "").strip(),
        )
        for row in definitions
    ]
    if any(not well_name or not comp_id for well_name, comp_id in identifiers):
        errors.append("井名称和射孔名称不能为空。")
    available = [item for item in identifiers if all(item)]
    if len(available) != len(set(available)):
        errors.append("同一口井中的射孔名称不能重复。")
    for record in definitions:
        radius = _finite_number(record.get("rw_m"))
        if radius is None or radius <= 0:
            errors.append("井半径必须大于 0。")
        for key in ("grid_i", "grid_j", "grid_k1", "grid_k2"):
            value = record.get(key)
            number = _finite_number(value)
            if value is not None and (
                    number is None or not number.is_integer() or number < 1):
                errors.append("网格编号必须是大于或等于 1 的整数。")
        k1 = _finite_number(record.get("grid_k1"))
        k2 = _finite_number(record.get("grid_k2"))
        if (k1 is None) != (k2 is None):
            errors.append("K1 和 K2 必须同时填写或同时留空。")
        elif k1 is not None and k1 > k2:
            errors.append("Z方向起始网格 K1 不能大于 K2。")
        well_index = record.get("well_index")
        numeric_wi = _finite_number(well_index)
        if well_index is not None and (
                numeric_wi is None or numeric_wi < 0):
            errors.append("井指数不能小于 0。")
        target = str(record.get("connection_target") or "").strip()
        if target and target not in CONNECTION_LABELS:
            errors.append("射孔类型不是受支持的连接类型。")
        if target in {"fracture", "matrix_and_fracture"}:
            fracture = record.get("fracture") or {}
            if not isinstance(fracture, dict) or not fracture.get(
                    "geometry_available"):
                errors.append(
                    "连接裂缝的射孔缺少真实裂缝几何数据，不能直接改为裂缝类型。")
        status = record.get("status")
        if status not in (None, "") and _internal_status(status) is None:
            errors.append("开关标志只能为 OPEN/开启 或 SHUT/关闭。")
    return list(dict.fromkeys(errors))


def _finite_number(value):
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None


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
    "MODULE_WELL_PRODUCTION",
    "COMPLETION_RECORD_ROLE",
    "WELL_NAME_ROLE",
    "WELL_PROPERTY_SPECS",
    "WellProductionCompassDialog",
    "WellPropertySpec",
]
