# -*- coding: utf-8 -*-
"""储层工作流界面的独立双状态窗口。"""

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

    def _new_project(self):
        index = self.pages.count()
        name = f"未命名工程{index}"
        self._open_project(name)
        self.statusBar().showMessage("已新建工程", 4500)
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

    def _open_project(self, name, module_key=None, project_state=None, project_root=None):
        project_state = project_state or ProjectState(project_name=name)
        if not project_state.project_name:
            project_state.project_name = name
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
