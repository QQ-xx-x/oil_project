# -*- coding: utf-8 -*-
"""Compact viewport toolbar used by placeholder windows."""

from PyQt5.QtCore import QSize
from PyQt5.QtWidgets import QComboBox, QFrame, QHBoxLayout, QLabel, QToolButton

from .icons import painted_icon


class ViewToolbar(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("viewToolbar")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(3)

        for tooltip, kind in [
                ("平移", "window"), ("选择", "generic"), ("缩放", "search"),
                ("旋转", "undo"), ("显示网格", "window"),
                ("显示属性", "database")]:
            button = QToolButton()
            button.setIcon(painted_icon(kind, 20))
            button.setIconSize(QSize(20, 20))
            button.setToolTip(tooltip)
            layout.addWidget(button)

        selector = QComboBox()
        selector.addItems(["任意", "压力", "孔隙度", "渗透率"])
        selector.setObjectName("viewSelector")
        layout.addWidget(selector)

        layout.addWidget(QLabel("比例"))
        scale = QComboBox()
        scale.addItems(["1", "0.5", "0.2"])
        scale.setCurrentText("1")
        scale.setObjectName("scaleSelector")
        layout.addWidget(scale)
        layout.addStretch()
