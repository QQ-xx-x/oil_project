# -*- coding: utf-8 -*-
"""Standalone two-state window for the reservoir workflow UI."""

import os

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QMainWindow, QSplitter, QStackedWidget, QStatusBar, QVBoxLayout, QWidget,
)

from .message_log import MessageLogPanel
from .project_shell import ProjectShell
from .project_state import ProjectState
from .projects_panel import ProjectsPanel
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
        body = QSplitter(Qt.Horizontal)
        self.projects = ProjectsPanel()
        self.projects.open_requested.connect(lambda: self._handle_command("打开工程"))
        self.projects.new_requested.connect(lambda: self._handle_command("新建工程"))
        self.projects.project_requested.connect(self._open_project)
        body.addWidget(self.projects)
        body.addWidget(StartWorkspace())
        body.setSizes([380, 1420])
        body.setCollapsible(0, False)

        vertical = QSplitter(Qt.Vertical)
        vertical.addWidget(body)
        self.message_log = MessageLogPanel()
        vertical.addWidget(self.message_log)
        vertical.setSizes([760, 175])
        vertical.setCollapsible(0, False)
        vertical.setCollapsible(1, False)
        return vertical

    def _handle_command(self, command):
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

    def _open_project(self, name):
        project_state = ProjectState(project_name=name)
        shell = ProjectShell(name, project_state, project_root=os.getcwd())
        self.pages.addWidget(shell)
        self.pages.setCurrentWidget(shell)
        self.setWindowTitle("储层建模与模拟平台")
        self.ribbon.set_project_mode(True)
        message = f"[工程] 已打开 {name}，当前显示输入、结果和多窗口工作区。"
        shell.message_log.append_message(message)
        self.statusBar().showMessage("Action performed OK", 4500)

    def active_log(self):
        current = self.pages.currentWidget()
        if hasattr(current, "message_log"):
            return current.message_log
        if isinstance(current, ProjectShell):
            return current.message_log
        return self.message_log
