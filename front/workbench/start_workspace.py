# -*- coding: utf-8 -*-
"""项目启动页面，左侧停靠区显示算例选项卡。"""

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QSplitter, QTabWidget, QVBoxLayout, QWidget,
)

from .case_manager_panel import CaseManagerPanel
from .icons import painted_icon


class StartWorkspace(QWidget):
    module_requested = pyqtSignal(str)
    command_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("startWorkspace")

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.case_manager = CaseManagerPanel(None)
        self.case_manager.command_requested.connect(self.command_requested.emit)

        left_container = QFrame()
        left_container.setObjectName("projectLeftDock")
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        header = QFrame()
        header.setObjectName("panelHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(8, 2, 5, 2)
        title = QLabel("算例")
        title.setObjectName("panelTitle")
        header_layout.addWidget(title)
        header_layout.addStretch()
        left_layout.addWidget(header)

        tabs = QTabWidget()
        tabs.setObjectName("leftDockTabs")
        tabs.setTabPosition(QTabWidget.South)
        tabs.setDocumentMode(True)
        tabs.addTab(self.case_manager, painted_icon("case", 16), "算例")
        left_layout.addWidget(tabs, 1)
        left_container.setMinimumWidth(380)
        left_container.setMaximumWidth(570)

        workspace = QFrame()
        workspace.setObjectName("moduleStartPage")

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_container)
        splitter.addWidget(workspace)
        splitter.setSizes([450, 1350])
        splitter.setCollapsible(0, False)
        root.addWidget(splitter, 1)
