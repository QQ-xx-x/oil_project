# -*- coding: utf-8 -*-
"""编辑算例输入前使用的算例管理树。"""

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFormLayout, QInputDialog,
    QLabel, QLineEdit, QMenu, QMessageBox, QTreeWidget, QTreeWidgetItem,
    QVBoxLayout,
)

from .icons import painted_icon
from .project_state import CASE_TYPE_GAS_WATER


KEY_ROLE = Qt.UserRole
KIND_ROLE = Qt.UserRole + 1


class NewCaseDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("newCaseDialog")
        self.setWindowTitle("创建模拟算例")
        self.resize(420, 150)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.case_type = QComboBox()
        self.case_type.addItem("气水模拟", CASE_TYPE_GAS_WATER)
        self.case_type.setEnabled(False)
        form.addRow("算例类型", self.case_type)

        self.case_name = QLineEdit("NewCase")
        self.case_name.selectAll()
        form.addRow("算例名称", self.case_name)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("确定")
        buttons.button(QDialogButtonBox.Cancel).setText("取消")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self):
        return {
            "case_type": self.case_type.currentData(),
            "case_name": self.case_name.text().strip() or "NewCase",
        }


class DuplicateCaseDialog(QDialog):
    """收集新名称，并明确仅复制配置的范围。"""

    def __init__(self, source_name, suggested_name, parent=None):
        super().__init__(parent)
        self.setObjectName("duplicateCaseDialog")
        self.setWindowTitle("复制算例")
        self.resize(460, 190)

        layout = QVBoxLayout(self)
        notice = QLabel(
            "将复制模型方案、CaseData 和各输入模块参数。"
            "\n模拟结果、历史拟合结果和运行记录不会被复制。"
        )
        notice.setObjectName("duplicateCaseNotice")
        notice.setWordWrap(True)
        layout.addWidget(notice)

        form = QFormLayout()
        source_label = QLabel(source_name)
        source_label.setObjectName("duplicateCaseSource")
        form.addRow("源算例", source_label)
        self.case_name = QLineEdit(suggested_name)
        self.case_name.selectAll()
        form.addRow("新算例名称", self.case_name)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("复制")
        buttons.button(QDialogButtonBox.Cancel).setText("取消")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def case_name_value(self):
        return self.case_name.text().strip()

    def accept(self):
        if not self.case_name_value():
            QMessageBox.warning(self, "复制算例", "请输入新算例名称。")
            self.case_name.setFocus()
            return
        super().accept()


class CaseManagerPanel(QTreeWidget):
    command_requested = pyqtSignal(str)
    case_selected = pyqtSignal(str)
    case_created = pyqtSignal(str)
    cases_changed = pyqtSignal()

    def __init__(self, project_state=None, parent=None):
        super().__init__(parent)
        self.project_state = project_state
        self.setObjectName("caseManagerTree")
        self.setHeaderHidden(True)
        self.setExpandsOnDoubleClick(False)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.itemActivated.connect(self._activate_item)
        self.itemClicked.connect(self._select_case_item)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self.refresh()

    def set_project_state(self, project_state):
        self.project_state = project_state
        self.refresh()

    def refresh(self):
        current_case_id = (
            getattr(self.project_state, "active_case_id", "")
            if self.project_state is not None else ""
        )
        self.clear()
        if self.project_state is None:
            project_group = self._group("工程")
            project_group.addChild(
                self._action_item("新建工程(NEW PROJECT)", "new_project", "new"))
            project_group.addChild(
                self._action_item("打开工程(OPEN PROJECT)", "open_project", "folder"))
            self.addTopLevelItem(project_group)
            project_group.setExpanded(True)
            return

        project_group = self._group("工程")
        project_group.addChild(
            self._action_item("保存工程(SAVE PROJECT)", "save_project", "save"))
        project_group.addChild(
            self._action_item("关闭工程(CLOSE PROJECT)", "close_project", "folder"))
        self.addTopLevelItem(project_group)
        project_group.setExpanded(True)

        case_actions = self._group("算例操作")
        case_actions.addChild(
            self._action_item("新建算例(NEW CASE)", "new_case", "new"))
        self.addTopLevelItem(case_actions)
        case_actions.setExpanded(True)

        project_name = getattr(self.project_state, "project_name", "") or "未命名工程"
        project_item = self._item(project_name, "project", "folder")
        project_item.setToolTip(0, "当前工程")
        self.addTopLevelItem(project_item)

        cases = list(getattr(self.project_state, "cases", []) or [])
        if not cases:
            empty = self._item("尚未创建算例", "empty", "warning")
            empty.setFlags(empty.flags() & ~Qt.ItemIsSelectable)
            project_item.addChild(empty)
        for case in cases:
            item = self._item(case.case_name, "case", "case")
            item.setData(0, KEY_ROLE, case.case_id)
            item.setToolTip(0, f"算例类型: 气水模拟\ncase_id: {case.case_id}")
            project_item.addChild(item)
            if case.case_id == current_case_id:
                self.setCurrentItem(item)
        project_item.setExpanded(True)

    def _add_action(self, text, action_key, icon_name):
        item = self._action_item(text, action_key, icon_name)
        self.addTopLevelItem(item)
        return item

    def _action_item(self, text, action_key, icon_name):
        item = self._item(text, "action", icon_name)
        item.setData(0, KEY_ROLE, action_key)
        return item

    def _group(self, text):
        item = self._item(text, "group", "folder")
        item.setFlags(item.flags() & ~Qt.ItemIsSelectable)
        return item

    def _item(self, text, kind, icon_name):
        item = QTreeWidgetItem([text])
        item.setData(0, KIND_ROLE, kind)
        item.setIcon(0, painted_icon(icon_name, 16))
        return item

    def _activate_item(self, item, column):
        kind = item.data(0, KIND_ROLE)
        key = item.data(0, KEY_ROLE)
        if kind == "case" and self.project_state is not None:
            self._select_case(key)

    def _select_case_item(self, item, column):
        kind = item.data(0, KIND_ROLE)
        if kind == "action":
            self._handle_action(item.data(0, KEY_ROLE))
        elif kind == "case":
            self._select_case(item.data(0, KEY_ROLE))

    def _select_case(self, case_id):
        if self.project_state is None:
            return
        if self.project_state.select_case(case_id):
            self.case_selected.emit(case_id)
            self.refresh()

    def _handle_action(self, action_key):
        if action_key == "new_project":
            self.command_requested.emit("新建工程")
        elif action_key == "open_project":
            self.command_requested.emit("打开工程")
        elif action_key == "save_project":
            self.command_requested.emit("保存工程")
        elif action_key == "close_project":
            self.command_requested.emit("关闭工程")
        elif action_key == "new_case":
            self._create_case()
        elif action_key in {"import_eclipse_case", "import_case"}:
            self.command_requested.emit("导入算例")

    def _create_case(self):
        if self.project_state is None:
            self.command_requested.emit("新建工程")
            return
        dialog = NewCaseDialog(self)
        if dialog.exec_() != QDialog.Accepted:
            return
        values = dialog.values()
        case = self.project_state.add_case(
            case_name=values["case_name"],
            case_type=values["case_type"],
            activate=True,
        )
        self.refresh()
        self.case_created.emit(case.case_id)
        self.cases_changed.emit()

    def _show_context_menu(self, pos):
        item = self.itemAt(pos)
        if item is None or item.data(0, KIND_ROLE) != "case":
            return
        case_id = item.data(0, KEY_ROLE)
        menu = QMenu(self)
        menu.addAction("重命名算例", lambda: self._rename_case(case_id))
        menu.addAction("复制算例", lambda: self._duplicate_case(case_id))
        menu.addSeparator()
        menu.addAction("删除算例", lambda: self._delete_case(case_id))
        menu.exec_(self.viewport().mapToGlobal(pos))

    def _rename_case(self, case_id):
        case = self.project_state.case_by_id(case_id) if self.project_state else None
        if case is None:
            return
        name, ok = QInputDialog.getText(
            self, "重命名算例", "算例名称", text=case.case_name)
        if not ok or not name.strip():
            return
        if self.project_state.rename_case(case_id, name.strip()):
            self.refresh()
            self.cases_changed.emit()

    def _duplicate_case(self, case_id):
        if self.project_state is None:
            return
        source = self.project_state.case_by_id(case_id)
        if source is None:
            return
        dialog = DuplicateCaseDialog(
            source.case_name,
            self.project_state.suggest_duplicate_case_name(source.case_name),
            self,
        )
        if dialog.exec_() != QDialog.Accepted:
            return
        case = self.project_state.duplicate_case(
            case_id, case_name=dialog.case_name_value())
        if case is None:
            return
        self.refresh()
        self.case_created.emit(case.case_id)
        self.cases_changed.emit()

    def _delete_case(self, case_id):
        case = self.project_state.case_by_id(case_id) if self.project_state else None
        if case is None:
            return
        if case.has_unfinished_runs():
            QMessageBox.warning(
                self,
                "算例正在运行",
                "该算例仍有仿真或历史拟合任务正在运行，请先停止任务再删除。",
            )
            return
        result = QMessageBox.question(
            self,
            "删除算例",
            f"确定删除算例“{case.case_name}”吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if result != QMessageBox.Yes:
            return
        if self.project_state.delete_case(case_id):
            self.refresh()
            self.cases_changed.emit()
