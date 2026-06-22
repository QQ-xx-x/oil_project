# -*- coding: utf-8 -*-
"""储层工作流界面的独立双状态窗口。"""

import json
import os

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QFileDialog, QMainWindow, QMessageBox, QSplitter, QStackedWidget,
    QStatusBar, QVBoxLayout, QWidget,
)

from .message_log import MessageLogPanel
from .project_file_manager import (
    PROJECT_FILE_EXT, ProjectFileError, load_project_file, save_project_file,
)
from .project_shell import ProjectShell
from .project_state import ProjectState
from .recent_projects import add_recent_project
from .ribbon import QuickAccessBar, RibbonWidget
from .start_workspace import StartWorkspace


class WorkbenchWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._child_windows = []
        self.setWindowTitle("储层建模与模拟平台")
        self.resize(1800, 1000)
        self.setMinimumSize(1160, 720)

        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        self.setCentralWidget(root)

        self.quick_access = QuickAccessBar()
        self.quick_access.command_requested.connect(self._handle_command)
        root_layout.addWidget(self.quick_access)

        self.ribbon = RibbonWidget()
        self.ribbon.command_requested.connect(self._handle_command)
        root_layout.addWidget(self.ribbon)

        self.pages = QStackedWidget()
        self.start_page = self._create_start_page()
        self.pages.addWidget(self.start_page)
        root_layout.addWidget(self.pages, 1)

        status = QStatusBar()
        status.showMessage("平台初始化完成，等待打开工程")
        self.setStatusBar(status)

    def _create_start_page(self):
        vertical = QSplitter(Qt.Vertical)
        self.start_workspace = StartWorkspace()
        self.start_workspace.module_requested.connect(self._open_module_workspace)
        vertical.addWidget(self.start_workspace)
        self.message_log = MessageLogPanel()
        vertical.addWidget(self.message_log)
        vertical.setSizes([760, 175])
        vertical.setCollapsible(0, False)
        vertical.setCollapsible(1, False)
        return vertical

    def _handle_command(self, command):
        recent_path = self._recent_project_path(command)
        if recent_path:
            self._open_project_file(recent_path)
            return
        if self._is_save_as_command(command):
            self._save_project_as()
            return
        if self._is_save_command(command):
            self._save_project()
            return
        if self._is_open_command(command):
            self._open_project_file_dialog()
            return
        if self._is_new_command(command):
            self._new_project()
            return
        if command in {"运行模拟", "扫描结果", "刷新结果"}:
            current = self.pages.currentWidget()
            if isinstance(current, ProjectShell):
                current.run_simulation_scan()
                self.statusBar().showMessage("运行模拟扫描完成", 4500)
            else:
                message = "[运行] 请先打开工程"
                self.active_log().append_message(message)
                self.statusBar().showMessage(message, 4500)
            return
        message = f"[操作] {command} 功能将在后续阶段接入。"
        self.active_log().append_message(message)
        self.statusBar().showMessage(message, 4500)

    def _current_project_shell(self):
        current = self.pages.currentWidget()
        return current if isinstance(current, ProjectShell) else None

    def _save_project(self):
        shell = self._current_project_shell()
        if shell is None:
            self._show_project_message("[工程] 请先新建或打开工程后再保存。")
            return False
        path = getattr(shell.project_state, "project_file_path", "")
        if not path:
            return self._save_project_as()
        return self._write_project_file(shell, path)

    def _save_project_as(self):
        shell = self._current_project_shell()
        if shell is None:
            self._show_project_message("[工程] 请先新建或打开工程后再另存为。")
            return False
        default_name = shell.project_state.project_name or "untitled"
        if default_name.lower().endswith((".pet", ".oilproj")):
            default_name = os.path.splitext(default_name)[0]
        start_path = shell.project_state.project_file_path or os.path.join(
            os.getcwd(), f"{default_name}{PROJECT_FILE_EXT}")
        path, _ = QFileDialog.getSaveFileName(
            self,
            "保存工程",
            start_path,
            "Oil Project Files (*.oilproj);;All Files (*)",
        )
        if not path:
            return False
        return self._write_project_file(shell, path)

    def _write_project_file(self, shell, path):
        try:
            shell.collect_ui_state()
            saved_path = save_project_file(shell.project_state, path)
        except ProjectFileError as exc:
            QMessageBox.critical(self, "保存工程失败", str(exc))
            return False
        self._mark_project_clean(shell)
        add_recent_project(saved_path, shell.project_state.project_name)
        self.ribbon.refresh_recent_projects()
        shell.message_log.append_message(f"[工程] 已保存工程文件：{saved_path}")
        self.statusBar().showMessage(f"工程已保存：{saved_path}", 4500)
        return True

    def _open_project_file_dialog(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "打开工程",
            os.getcwd(),
            "Oil Project Files (*.oilproj);;All Files (*)",
        )
        if not path:
            return False
        return self._open_project_file(path)

    def _open_project_file(self, path):
        target = self._choose_project_target("打开工程")
        if target is None:
            return False
        if target == "new_window":
            return self._open_project_file_in_new_window(path)
        if not self._confirm_close_current_project():
            return False
        return self._open_project_file_current(path, replace_current=True)

    def _open_project_file_current(self, path, replace_current=False):
        try:
            project_state, validation = load_project_file(path)
        except ProjectFileError as exc:
            QMessageBox.critical(self, "打开工程失败", str(exc))
            return False
        project_root = os.path.dirname(os.path.abspath(path))
        shell = self._open_project(
            project_state.project_name or os.path.basename(path),
            project_state=project_state,
            project_root=project_root,
            replace_current=replace_current,
        )
        shell.message_log.append_message(f"[工程] 已加载工程文件：{path}")
        shell.log_project_references(validation)
        add_recent_project(path, project_state.project_name)
        self.ribbon.refresh_recent_projects()
        if validation.get("ok"):
            self.statusBar().showMessage("工程文件加载完成", 4500)
        else:
            self.statusBar().showMessage("工程文件已加载，但存在需要处理的问题", 6500)
        return True

    def _open_project_file_in_new_window(self, path):
        window = WorkbenchWindow()
        if not window._open_project_file_current(path, replace_current=True):
            window.deleteLater()
            return False
        self._register_child_window(window)
        window.resize(self.size())
        window.move(self.x() + 40, self.y() + 40)
        window.show()
        return True

    def _new_project(self):
        target = self._choose_project_target("新建工程")
        if target is None:
            return False
        if target == "new_window":
            return self._new_project_in_new_window()
        if not self._confirm_close_current_project():
            return False
        return self._new_project_current(replace_current=True)

    def _new_project_current(self, replace_current=False):
        index = self.pages.count()
        name = f"未命名工程{index}"
        self._open_project(name, replace_current=replace_current)
        self.statusBar().showMessage("已新建工程", 4500)
        return True

    def _new_project_in_new_window(self):
        window = WorkbenchWindow()
        window._new_project_current(replace_current=True)
        self._register_child_window(window)
        window.resize(self.size())
        window.move(self.x() + 40, self.y() + 40)
        window.show()
        return True

    def _show_project_message(self, message):
        self.active_log().append_message(message)
        self.statusBar().showMessage(message, 4500)

    def _recent_project_path(self, command):
        text = str(command or "")
        prefix = "open_recent_project::"
        if text.startswith(prefix):
            return text[len(prefix):]
        return ""

    def _is_save_as_command(self, command):
        text = str(command or "")
        return "另存" in text

    def _is_save_command(self, command):
        text = str(command or "")
        return "保存" in text and not self._is_save_as_command(text)

    def _is_open_command(self, command):
        text = str(command or "")
        return "打开" in text

    def _is_new_command(self, command):
        text = str(command or "")
        return "新建" in text

    def _open_project(self, name, module_key=None, project_state=None,
                      project_root=None, replace_current=False):
        project_state = project_state or ProjectState(project_name=name)
        if not project_state.project_name:
            project_state.project_name = name
        if replace_current:
            self._close_current_project_page()
        shell = ProjectShell(
            project_state.project_name,
            project_state,
            project_root=project_root or os.getcwd(),
        )
        self.pages.addWidget(shell)
        self.pages.setCurrentWidget(shell)
        self.setWindowTitle("储层建模与模拟平台")
        self.ribbon.set_project_mode(True)
        message = f"[工程] 已打开 {name}，当前显示输入、结果和多窗口工作区。"
        shell.message_log.append_message(message)
        if module_key:
            shell.activate_module(module_key)
        self._mark_project_clean(shell)
        self.statusBar().showMessage("Action performed OK", 4500)
        return shell

    def _open_module_workspace(self, module_key):
        if module_key in {"help_license", "ai_assistant"}:
            labels = {
                "help_license": "帮助与许可",
                "ai_assistant": "AI 助手",
            }
            message = f"[启动] {labels[module_key]} 模块将在后续阶段接入。"
            self.active_log().append_message(message)
            self.statusBar().showMessage(message, 4500)
            return
        self._open_project("默认工程.pet", module_key)

    def active_log(self):
        current = self.pages.currentWidget()
        if hasattr(current, "message_log"):
            return current.message_log
        if isinstance(current, ProjectShell):
            return current.message_log
        return self.message_log

    def _choose_project_target(self, action_title):
        if self._current_project_shell() is None:
            return "current_window"
        dialog = QMessageBox(self)
        dialog.setWindowTitle(action_title)
        dialog.setIcon(QMessageBox.Question)
        dialog.setText(f"{action_title}方式")
        dialog.setInformativeText(
            "请选择在当前窗口切换工程，还是新建一个窗口打开工程。")
        current_button = dialog.addButton("当前窗口", QMessageBox.AcceptRole)
        new_window_button = dialog.addButton("新建窗口", QMessageBox.ActionRole)
        cancel_button = dialog.addButton("取消", QMessageBox.RejectRole)
        dialog.setDefaultButton(new_window_button)
        dialog.exec_()
        clicked = dialog.clickedButton()
        if clicked == current_button:
            return "current_window"
        if clicked == new_window_button:
            return "new_window"
        if clicked == cancel_button:
            return None
        return None

    def _confirm_close_current_project(self):
        shell = self._current_project_shell()
        if shell is None or not self._is_project_dirty(shell):
            return True
        name = shell.project_state.project_name or shell.project_name or "未命名工程"
        dialog = QMessageBox(self)
        dialog.setWindowTitle("工程未保存")
        dialog.setIcon(QMessageBox.Warning)
        dialog.setText(f"当前工程“{name}”有未保存修改。")
        dialog.setInformativeText("切换到其他工程前，请选择是否先保存当前工程。")
        save_button = dialog.addButton("保存工程", QMessageBox.AcceptRole)
        discard_button = dialog.addButton("不保存", QMessageBox.DestructiveRole)
        cancel_button = dialog.addButton("取消", QMessageBox.RejectRole)
        dialog.setDefaultButton(save_button)
        dialog.exec_()
        clicked = dialog.clickedButton()
        if clicked == save_button:
            return self._save_project()
        if clicked == discard_button:
            return True
        if clicked == cancel_button:
            return False
        return False

    def _project_data_signature(self, shell):
        shell.collect_ui_state()
        state = shell.project_state.to_dict()
        state.pop("project_file_path", None)
        state.pop("ui_state", None)
        return json.dumps(state, ensure_ascii=False, sort_keys=True, default=str)

    def _mark_project_clean(self, shell):
        if shell is not None:
            shell._saved_project_signature = self._project_data_signature(shell)

    def _is_project_dirty(self, shell):
        if shell is None:
            return False
        baseline = getattr(shell, "_saved_project_signature", None)
        if baseline is None:
            self._mark_project_clean(shell)
            return False
        return baseline != self._project_data_signature(shell)

    def _close_current_project_page(self):
        shell = self._current_project_shell()
        if shell is None:
            return
        self.pages.removeWidget(shell)
        shell.deleteLater()
        self.pages.setCurrentWidget(self.start_page)
        self.ribbon.set_project_mode(bool(self._project_shells()))

    def _project_shells(self):
        shells = []
        for index in range(self.pages.count()):
            widget = self.pages.widget(index)
            if isinstance(widget, ProjectShell):
                shells.append(widget)
        return shells

    def _register_child_window(self, window):
        self._child_windows.append(window)
        window.destroyed.connect(
            lambda _=None, child=window: self._forget_child_window(child))

    def _forget_child_window(self, window):
        if window in self._child_windows:
            self._child_windows.remove(window)

    def closeEvent(self, event):
        for shell in list(self._project_shells()):
            self.pages.setCurrentWidget(shell)
            if not self._confirm_close_current_project():
                event.ignore()
                return
        super().closeEvent(event)
