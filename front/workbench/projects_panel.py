# -*- coding: utf-8 -*-
"""Recent-project panel shown before a reservoir project is opened."""

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QScrollArea, QToolButton, QVBoxLayout, QWidget,
)

from .icons import painted_icon, project_thumbnail


class ProjectCard(QFrame):
    selected = pyqtSignal(str)

    def __init__(self, name, path, accent, parent=None):
        super().__init__(parent)
        self.name = name
        self.setObjectName("projectCard")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 5, 6, 5)
        layout.setSpacing(9)

        preview = QLabel()
        preview.setObjectName("projectPreview")
        preview.setPixmap(project_thumbnail(accent).scaled(
            66, 42, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        layout.addWidget(preview)

        labels = QVBoxLayout()
        labels.setSpacing(3)
        project_name = QLabel(name)
        project_name.setObjectName("projectName")
        location = QLabel(path)
        location.setObjectName("projectPath")
        labels.addWidget(project_name)
        labels.addWidget(location)
        labels.addStretch()
        layout.addLayout(labels, 1)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.selected.emit(self.name)
        super().mouseDoubleClickEvent(event)


class ProjectsPanel(QWidget):
    open_requested = pyqtSignal()
    new_requested = pyqtSignal()
    project_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("projectsPanel")
        self.setMinimumWidth(360)
        self.setMaximumWidth(430)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QFrame()
        header.setObjectName("panelHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(8, 2, 5, 2)
        title = QLabel("项目")
        title.setObjectName("panelTitle")
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(QLabel("▾   ⚑  ×"))
        layout.addWidget(header)

        commands = QFrame()
        commands.setObjectName("panelCommands")
        command_layout = QHBoxLayout(commands)
        command_layout.setContentsMargins(6, 4, 6, 4)
        command_layout.setSpacing(4)
        open_button = QToolButton()
        open_button.setIcon(painted_icon("folder"))
        open_button.setToolTip("打开工程")
        open_button.clicked.connect(self.open_requested)
        new_button = QToolButton()
        new_button.setIcon(painted_icon("new"))
        new_button.setToolTip("新建工程")
        new_button.clicked.connect(self.new_requested)
        command_layout.addWidget(open_button)
        command_layout.addWidget(new_button)
        command_layout.addStretch()
        layout.addWidget(commands)

        scroller = QScrollArea()
        scroller.setWidgetResizable(True)
        scroller.setFrameShape(QFrame.NoFrame)
        list_widget = QWidget()
        list_layout = QVBoxLayout(list_widget)
        list_layout.setContentsMargins(5, 5, 5, 5)
        list_layout.setSpacing(3)
        projects = [
            ("3.18.pet", r"E:\EdgeDownload\400jingju1200\400jingju1200", "#23b777"),
            ("裂缝油藏示例.pet", r"D:\reservoir\projects\fracture_demo", "#dc9b22"),
            ("三维网格对比.pet", r"D:\reservoir\projects\grid_compare", "#6694be"),
            ("水平井开发.pet", r"D:\reservoir\projects\horizontal_well", "#5eab84"),
            ("压力场分析.pet", r"D:\reservoir\projects\pressure_case", "#cf765a"),
        ]
        for name, path, accent in projects:
            card = ProjectCard(name, path, accent)
            card.selected.connect(self.project_requested)
            list_layout.addWidget(card)
        list_layout.addStretch()
        scroller.setWidget(list_widget)
        layout.addWidget(scroller, 1)
