# -*- coding: utf-8 -*-
"""CaseData 输入文件参数面板。"""

import os

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMessageBox, QPlainTextEdit, QPushButton, QSplitter,
    QTableWidget, QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget,
)

from .case_file_analyzer import (
    analyze_case_file, analyze_property_against_grid,
    read_expanded_array_preview, read_text_preview,
)
from .case_data_parser import parse_case_data, save_case_data, update_keyword_value


class CaseDataPanel(QWidget):
    """显示并编辑 CaseData 关键字，不在主表格中加载大数组内容。"""

    case_data_saved = pyqtSignal()

    HEADERS = ["关键字", "值", "类型", "状态"]

    def __init__(self, project_state=None, initial_section=None,
                 section_locked=False, parent=None):
        super().__init__(parent)
        self.project_state = project_state
        self.initial_section = initial_section
        self.section_locked = bool(section_locked and initial_section)
        self.case_data = None
        self.current_section = None
        self._syncing_table = False
        self.values_were_saved = False
        self.setObjectName("caseDataPanel")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)
        root.addWidget(self._build_header())

        splitter = QSplitter(Qt.Horizontal)
        self.section_list = QListWidget()
        self.section_list.setObjectName("caseDataSectionList")
        self.section_list.currentItemChanged.connect(self._handle_section_changed)
        splitter.addWidget(self.section_list)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(6)

        self.summary_label = QLabel("尚未加载 CaseData 文件")
        self.summary_label.setObjectName("caseDataSummary")
        self.summary_label.setWordWrap(True)
        right_layout.addWidget(self.summary_label)

        self.table = QTableWidget(0, len(self.HEADERS))
        self.table.setObjectName("caseDataKeywordTable")
        self.table.setHorizontalHeaderLabels(self.HEADERS)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.itemSelectionChanged.connect(self._sync_detail)
        self.table.itemChanged.connect(self._handle_item_changed)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 165)
        self.table.setColumnWidth(1, 210)
        self.table.setColumnWidth(2, 72)
        right_layout.addWidget(self.table, 1)

        self.detail = QPlainTextEdit()
        self.detail.setObjectName("caseDataDetail")
        self.detail.setReadOnly(True)
        self.detail.setMaximumHeight(118)
        right_layout.addWidget(self.detail)

        splitter.addWidget(right)
        if self.section_locked:
            self.section_list.setVisible(False)
            splitter.setSizes([0, 775])
        else:
            splitter.setSizes([155, 620])
        root.addWidget(splitter, 1)

        self._load_saved_path()

    def _build_header(self):
        frame = QFrame()
        frame.setObjectName("parameterIntro")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        title_text = (
            f"{self.initial_section} 参数"
            if self.section_locked else "CaseData 输入"
        )
        title = QLabel(title_text)
        title.setObjectName("parameterTitle")
        if self.section_locked:
            desc_text = (
                "当前窗口只显示所选 CaseData section 的关键字、参数和文件引用状态。"
            )
        else:
            desc_text = (
                "加载 casedata manifest 后按 section 显示关键字、参数和文件引用状态；"
                "大数组只显示文件引用，不在界面中展开。"
            )
        desc = QLabel(desc_text)
        desc.setObjectName("parameterDescription")
        desc.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(desc)

        row = QHBoxLayout()
        row.setSpacing(6)
        self.path_edit = QLineEdit()
        self.path_edit.setObjectName("parameterPathEdit")
        self.path_edit.setPlaceholderText("选择 casedata txt 文件")
        browse = QPushButton("选择")
        browse.setObjectName("parameterBrowseButton")
        browse.clicked.connect(self._choose_file)
        reload_button = QPushButton("重载")
        reload_button.setObjectName("parameterBrowseButton")
        reload_button.clicked.connect(self.reload)
        self.save_button = QPushButton("保存")
        self.save_button.setObjectName("parameterBrowseButton")
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self.save)
        row.addWidget(self.path_edit, 1)
        row.addWidget(browse)
        row.addWidget(reload_button)
        row.addWidget(self.save_button)
        layout.addLayout(row)
        return frame

    def _load_saved_path(self):
        path = getattr(self.project_state, "case_data_path", "") if self.project_state else ""
        if path:
            self.path_edit.setText(path)
            self.load_path(path)

    def _choose_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择 CaseData 文件",
            "",
            "CaseData Files (*.txt *.data *.inc);;All Files (*)",
        )
        if path:
            self.path_edit.setText(path)
            self.load_path(path)

    def reload(self):
        path = self.path_edit.text().strip()
        if path:
            self.load_path(path)

    def save(self):
        if self.case_data is None:
            QMessageBox.warning(self, "保存 CaseData", "尚未加载 CaseData 文件。")
            return False
        try:
            saved_path = save_case_data(self.case_data)
        except Exception as exc:
            QMessageBox.critical(self, "保存 CaseData 失败", str(exc))
            return False
        self.path_edit.setText(saved_path)
        self.values_were_saved = True
        if self.project_state is not None:
            self.project_state.set_case_data(self.case_data)
        self.case_data_saved.emit()
        self._populate_keywords()
        self._update_summary()
        QMessageBox.information(self, "保存 CaseData", "CaseData 参数已保存。")
        return True

    def load_path(self, path):
        self.case_data = parse_case_data(path)
        self.values_were_saved = False
        if self.project_state is not None:
            self.project_state.set_case_data(self.case_data)
        self._populate_sections()
        self._update_summary()

    def _populate_sections(self):
        self.section_list.clear()
        self.table.setRowCount(0)
        self.detail.clear()
        if self.case_data is None:
            return
        if self.section_locked:
            self.current_section = self.case_data.section(self.initial_section)
            self._populate_keywords()
            return
        target_row = 0
        for row, section in enumerate(self.case_data.sections):
            item = QListWidgetItem(section.name)
            item.setData(Qt.UserRole, section.name)
            self.section_list.addItem(item)
            if self.initial_section and section.name.upper() == self.initial_section.upper():
                target_row = row
        if self.section_list.count():
            self.section_list.setCurrentRow(target_row)

    def _handle_section_changed(self, current, previous):
        if current is None or self.case_data is None:
            return
        section_name = current.data(Qt.UserRole)
        self.current_section = self.case_data.section(section_name)
        self._populate_keywords()

    def _populate_keywords(self):
        self._syncing_table = True
        self.table.setRowCount(0)
        if self.current_section is None:
            self._syncing_table = False
            return
        self.table.setRowCount(len(self.current_section.keywords))
        for row, keyword in enumerate(self.current_section.keywords):
            key_item = self._readonly_item(keyword.key)
            value_item = QTableWidgetItem(keyword.raw_value)
            value_item.setData(Qt.UserRole, keyword)
            type_item = self._readonly_item(keyword.value_type)
            status_item = self._readonly_item(self._keyword_status(keyword))
            self.table.setItem(row, 0, key_item)
            self.table.setItem(row, 1, value_item)
            self.table.setItem(row, 2, type_item)
            self.table.setItem(row, 3, status_item)
        self._syncing_table = False
        if self.table.rowCount():
            self.table.selectRow(0)
        else:
            self._sync_detail()

    def _readonly_item(self, text):
        item = QTableWidgetItem(str(text))
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        return item

    def _keyword_status(self, keyword):
        if keyword.is_file_ref:
            return "文件已找到" if keyword.file_exists else "文件缺失"
        return "可编辑"

    def _handle_item_changed(self, item):
        if self._syncing_table or item.column() != 1:
            return
        keyword = item.data(Qt.UserRole)
        if keyword is None:
            return
        update_keyword_value(self.case_data, keyword, item.text())
        self.table.item(item.row(), 2).setText(keyword.value_type)
        self.table.item(item.row(), 3).setText(self._keyword_status(keyword))
        self._sync_detail()
        self._update_summary()

    def _sync_detail(self):
        selected = self.table.selectedItems()
        if not selected:
            if self.current_section is None:
                self.detail.setPlainText("")
            else:
                self.detail.setPlainText(self.current_section.comment)
            return
        row = selected[0].row()
        value_item = self.table.item(row, 1)
        keyword = value_item.data(Qt.UserRole) if value_item is not None else None
        if keyword is None:
            self.detail.clear()
            return
        lines = [
            f"[{self.current_section.name}] {keyword.key}",
            f"值: {keyword.raw_value}",
            f"行号: {keyword.line_number}",
        ]
        if keyword.is_file_ref:
            lines.append(f"文件: {keyword.file_path}")
            lines.append(f"状态: {'已找到' if keyword.file_exists else '缺失'}")
        if keyword.comment:
            lines.extend(["", keyword.comment])
        self.detail.setPlainText("\n".join(lines))

    def _update_summary(self):
        if self.case_data is None:
            self.summary_label.setText("尚未加载 CaseData 文件")
            return
        refs = self.case_data.file_refs()
        missing = [item for item in refs if not item.file_exists]
        schema_state = "已读取" if self.case_data.schema else "未发现"
        basename = os.path.basename(self.case_data.path)
        dirty_text = "；已修改，未保存" if self.case_data.dirty else "；已保存"
        text = (
            f"{basename} | section {len(self.case_data.sections)} 个，"
            f"关键字 {self.case_data.keyword_count()} 个，文件引用 {len(refs)} 个，"
            f"缺失 {len(missing)} 个，schema {schema_state}{dirty_text}"
        )
        if self.section_locked:
            section_name = self.initial_section or ""
            section = self.case_data.section(section_name)
            if section is None:
                text += f"；当前 section {section_name} 未找到"
            else:
                text += f"；当前 {section.name} 参数 {len(section.keywords)} 个"
        if self.case_data.errors:
            text += f"；错误 {len(self.case_data.errors)} 个"
        self.summary_label.setText(text)
        if hasattr(self, "save_button"):
            self.save_button.setEnabled(bool(self.case_data.dirty))

    def get_values(self):
        if self.case_data is None:
            return {}
        return self.case_data.to_dict()


class CaseKeywordPanel(QWidget):
    """显示单个 CaseData 关键字，并提供文件预览和校验结果。"""

    def __init__(self, project_state=None, section_name="", keyword_key="", parent=None):
        super().__init__(parent)
        self.project_state = project_state
        self.section_name = section_name
        self.keyword_key = keyword_key
        self.case_data = None
        self.keyword = None
        self.analysis = None
        self.setObjectName("caseDataKeywordPanel")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        header = QFrame()
        header.setObjectName("parameterIntro")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(12, 10, 12, 10)
        header_layout.setSpacing(6)

        self.title_label = QLabel("CaseData 参数")
        self.title_label.setObjectName("parameterTitle")
        self.desc_label = QLabel("显示单个关键字的值、说明和文件预览。")
        self.desc_label.setObjectName("parameterDescription")
        self.desc_label.setWordWrap(True)
        header_layout.addWidget(self.title_label)
        header_layout.addWidget(self.desc_label)
        root.addWidget(header)

        self.info = QPlainTextEdit()
        self.info.setObjectName("caseDataDetail")
        self.info.setReadOnly(True)
        self.info.setMaximumHeight(150)
        root.addWidget(self.info)

        self.tabs = QTabWidget()
        self.raw_preview = self._read_only_text("caseDataFilePreview")
        self.summary_view = self._read_only_text("caseDataFileSummary")
        self.validation_view = self._read_only_text("caseDataFileValidation")
        self.tabs.addTab(self.raw_preview, "预览")
        self.tabs.addTab(self.summary_view, "解析摘要")
        self.tabs.addTab(self.validation_view, "校验结果")
        root.addWidget(self.tabs, 1)

        self._load_keyword()

    def _read_only_text(self, object_name):
        widget = QPlainTextEdit()
        widget.setObjectName(object_name)
        widget.setReadOnly(True)
        return widget

    def _load_keyword(self):
        path = getattr(self.project_state, "case_data_path", "") if self.project_state else ""
        if not path:
            self.info.setPlainText("尚未加载 CaseData 文件。请先双击 CaseData 输入并选择文件。")
            self._clear_tabs()
            return
        self.case_data = parse_case_data(path)
        section = self.case_data.section(self.section_name)
        if section is None:
            self.info.setPlainText(f"未找到 section: {self.section_name}")
            self._clear_tabs()
            return
        for keyword in section.keywords:
            if keyword.key == self.keyword_key:
                self.keyword = keyword
                break
        if self.keyword is None:
            self.info.setPlainText(f"[{section.name}] 中未找到关键字: {self.keyword_key}")
            self._clear_tabs()
            return
        self._render_keyword(section.name, self.keyword)

    def _render_keyword(self, section_name, keyword):
        title = f"[{section_name}] {keyword.key}"
        self.title_label.setText(title)
        self.desc_label.setText(
            "文件关键字显示文件路径、状态和前 200 行预览；普通关键字显示参数值和说明。"
            if keyword.is_file_ref else
            "普通关键字显示参数值、类型、行号和原始说明。"
        )

        lines = [
            title,
            f"值: {keyword.raw_value}",
            f"类型: {keyword.value_type}",
            f"行号: {keyword.line_number}",
        ]
        if keyword.is_file_ref:
            lines.append(f"文件: {keyword.file_path}")
            lines.append(f"状态: {'已找到' if keyword.file_exists else '缺失'}")
            if keyword.file_exists:
                lines.append(f"大小: {os.path.getsize(keyword.file_path)} bytes")
        if keyword.comment:
            lines.extend(["", keyword.comment])
        self.info.setPlainText("\n".join(lines))

        if keyword.is_file_ref:
            self.analysis = analyze_case_file(keyword.file_path, keyword.key)
            self.raw_preview.setPlainText(self._preview_text_for_file(keyword))
            self.summary_view.setPlainText(self.analysis.summary_text())
            self.validation_view.setPlainText(self._validation_text_with_grid_check())
        else:
            self.analysis = None
            text = (
                "参数值\n"
                "------\n"
                f"{keyword.key} = {keyword.raw_value}\n\n"
                "该节点不是文件引用，因此不显示文件内容。"
            )
            self.raw_preview.setPlainText(text)
            self.summary_view.setPlainText(text)
            self.validation_view.setPlainText("普通参数暂不需要文件校验。")

    def _preview_text_for_file(self, keyword):
        if self.analysis is not None and self.analysis.file_type == "property_array":
            grid_keyword = self._find_grid_keyword()
            grid_path = grid_keyword.file_path if grid_keyword is not None and grid_keyword.file_exists else None
            return read_expanded_array_preview(keyword.file_path, grid_path=grid_path)
        return read_text_preview(keyword.file_path)

    def _validation_text_with_grid_check(self):
        text = self.analysis.validation_text() if self.analysis is not None else ""
        if self.analysis is None or self.analysis.file_type != "property_array":
            return text
        grid_keyword = self._find_grid_keyword()
        if grid_keyword is None or not grid_keyword.file_exists:
            return f"{text}\n\n联合校验:\n未找到可读取的 grid_file，无法与 ACTNUM 对齐校验。"
        grid_analysis = analyze_case_file(grid_keyword.file_path, grid_keyword.key)
        grid_total = grid_analysis.summary.get("total_cell_count")
        actnum_count = grid_analysis.summary.get("actnum_value_count")
        array_count = self.analysis.summary.get("总值数量")
        lines = ["", "联合校验:"]
        if grid_analysis.errors:
            lines.append(f"grid_file 解析失败: {'; '.join(grid_analysis.errors)}")
        else:
            state_total = "通过" if array_count == grid_total else "不匹配"
            state_actnum = "通过" if array_count == actnum_count else "不匹配"
            lines.append(f"属性数组数量 vs nx*ny*nz: {array_count} / {grid_total} ({state_total})")
            lines.append(f"属性数组数量 vs ACTNUM 数量: {array_count} / {actnum_count} ({state_actnum})")
            lines.append(
                "ACTNUM 活跃/非活跃: "
                f"{grid_analysis.summary.get('active_cell_count')} / "
                f"{grid_analysis.summary.get('inactive_cell_count')}"
            )
            try:
                active_stats = analyze_property_against_grid(
                    self.keyword.file_path,
                    grid_keyword.file_path,
                )
                lines.append("前端展示过滤规则: ACTNUM=0 跳过，value=99999 跳过")
                lines.append(f"ACTNUM=0 跳过数量: {active_stats.get('inactive_skipped_count')}")
                lines.append(f"活跃网格中 99999 跳过数量: {active_stats.get('active_null_count')}")
                lines.append(f"最终显示有效数量: {active_stats.get('display_value_count')}")
                lines.append(
                    "最终显示值范围: "
                    f"{active_stats.get('display_min')} ~ {active_stats.get('display_max')}"
                )
                if active_stats.get("length_mismatch"):
                    lines.append("警告: 属性数组数量与 ACTNUM 数量不一致，过滤时按较短长度处理。")
            except Exception as exc:
                lines.append(f"ACTNUM 联合过滤统计失败: {exc}")
        return f"{text}\n" + "\n".join(lines)

    def _find_grid_keyword(self):
        if self.case_data is None:
            return None
        section = self.case_data.section("GRID")
        if section is None:
            return None
        for keyword in section.keywords:
            if keyword.key == "grid_file":
                return keyword
        return None

    def _clear_tabs(self):
        self.raw_preview.clear()
        self.summary_view.clear()
        self.validation_view.clear()

    def get_values(self):
        if self.keyword is None:
            return {}
        return {
            "section": self.section_name,
            "key": self.keyword.key,
            "value": self.keyword.value,
            "raw_value": self.keyword.raw_value,
            "is_file_ref": self.keyword.is_file_ref,
            "file_path": self.keyword.file_path,
            "file_exists": self.keyword.file_exists,
        }
