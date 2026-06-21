# -*- coding: utf-8 -*-
"""视图窗口使用的紧凑工具栏。"""

from PyQt5.QtCore import QSize, pyqtSignal
from PyQt5.QtWidgets import QComboBox, QFrame, QHBoxLayout, QLabel, QToolButton

from .icon_registry import semantic_icon_kind
from .icons import painted_icon


class ViewToolbar(QFrame):
    new_window_requested = pyqtSignal()
    clone_window_requested = pyqtSignal()
    close_window_requested = pyqtSignal()

    TOOLSETS = {
        "3d": [
            ("选择对象", "select"), ("旋转视图", "undo"), ("平移视图", "pan"),
            ("缩放视图", "search"), ("适配全部", "fit_view"), ("显示图例", "chart"),
            ("切换背景", "background"), ("截图", "camera"),
        ],
        "2d": [
            ("选择对象", "select"), ("平移视图", "pan"), ("缩放视图", "search"),
            ("适配全部", "fit_view"), ("比例尺", "measure"), ("显示网格", "grid"),
            ("测量", "measure"), ("截图", "camera"),
        ],
        "chart": [
            ("刷新图表", "refresh"), ("框选缩放", "search"), ("重置视图", "undo"),
            ("保存图像", "save"), ("显示图例", "chart"), ("曲线设置", "settings"),
            ("导出数据", "export"),
        ],
    }

    def __init__(self, view_type="3d", parent=None):
        super().__init__(parent)
        self.setObjectName("viewToolbar")
        self.setProperty("viewType", view_type)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 5, 2)
        layout.setSpacing(2)

        for tooltip, kind, signal in [
            ("新建窗口", "new", self.new_window_requested),
            ("复制当前窗口", "copy", self.clone_window_requested),
            ("关闭当前窗口", "warning", self.close_window_requested),
        ]:
            button = self._button(tooltip, kind)
            button.setProperty("windowTool", True)
            button.clicked.connect(signal.emit)
            layout.addWidget(button)

        divider = QFrame()
        divider.setObjectName("viewToolbarDivider")
        divider.setFrameShape(QFrame.VLine)
        layout.addWidget(divider)

        for tooltip, kind in self.TOOLSETS.get(view_type, self.TOOLSETS["3d"]):
            layout.addWidget(self._button(tooltip, kind))

        selector = QComboBox()
        if view_type == "chart":
            selector.addItems(["曲线类型", "相渗", "生产", "PVT"])
        elif view_type == "2d":
            selector.addItems(["图层", "井位", "网格", "裂缝"])
        else:
            selector.addItems(["属性", "压力", "孔隙度", "渗透率"])
        selector.setObjectName("viewSelector")
        layout.addWidget(selector)

        if view_type != "chart":
            layout.addWidget(QLabel("比例"))
            scale = QComboBox()
            scale.addItems(["1", "0.5", "0.2"])
            scale.setCurrentText("1")
            scale.setObjectName("scaleSelector")
            layout.addWidget(scale)
        layout.addStretch()

    def _button(self, tooltip, kind):
        button = QToolButton()
        button.setObjectName("viewToolbarButton")
        button.setIcon(painted_icon(semantic_icon_kind(kind, tooltip), 18))
        button.setIconSize(QSize(18, 18))
        button.setToolTip(tooltip)
        button.setFixedSize(24, 23)
        button.setAutoRaise(True)
        return button
