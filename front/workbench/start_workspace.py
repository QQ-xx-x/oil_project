# -*- coding: utf-8 -*-
"""Empty workspace displayed until a project is opened."""

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QLabel, QVBoxLayout, QWidget


class StartWorkspace(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("startWorkspace")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        watermark = QLabel("储层模拟")
        watermark.setObjectName("workspaceWatermark")
        watermark.setAlignment(Qt.AlignCenter)
        layout.addWidget(watermark)
