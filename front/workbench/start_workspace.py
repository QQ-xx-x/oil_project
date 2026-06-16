# -*- coding: utf-8 -*-
"""工程打开前显示的模块导航启动页。"""

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout,
    QWidget,
)

from .icons import painted_icon


class ModuleCard(QFrame):
    selected = pyqtSignal(str)

    def __init__(self, module_key, title, subtitle, icon_name, tone="steel",
                 featured=False, parent=None):
        super().__init__(parent)
        self.module_key = module_key
        self.setObjectName("moduleCard")
        self.setProperty("tone", tone)
        self.setProperty("featured", featured)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(138 if featured else 92)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 14)
        layout.setSpacing(8)

        icon = QLabel()
        icon.setObjectName("moduleCardIcon")
        icon.setPixmap(painted_icon(icon_name, 44 if featured else 34).pixmap(
            44 if featured else 34, 44 if featured else 34))
        layout.addWidget(icon, 0, Qt.AlignLeft)

        title_label = QLabel(title)
        title_label.setObjectName("moduleCardTitle")
        title_label.setWordWrap(True)
        layout.addWidget(title_label)

        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("moduleCardSubtitle")
        subtitle_label.setWordWrap(True)
        layout.addWidget(subtitle_label)
        layout.addStretch()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.selected.emit(self.module_key)
        super().mousePressEvent(event)


class StartWorkspace(QWidget):
    module_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("startWorkspace")

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        scroller = QScrollArea()
        scroller.setObjectName("moduleStartScroller")
        scroller.setWidgetResizable(True)
        scroller.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        content.setObjectName("moduleStartPage")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(46, 34, 46, 24)
        layout.setSpacing(22)

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(5)
        title = QLabel("储层建模与模拟平台")
        title.setObjectName("moduleStartTitle")
        subtitle = QLabel("选择一个功能模块进入对应工作区")
        subtitle.setObjectName("moduleStartSubtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header.addLayout(title_box)
        header.addStretch()
        version = QLabel("Workbench 2026")
        version.setObjectName("moduleStartVersion")
        header.addWidget(version, 0, Qt.AlignTop)
        layout.addLayout(header)

        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(16)
        cards = [
            ("reservoir_model", "储层建模", "角点网格、基质属性、初始状态与双重介质", "grid", "steel", True, 0, 0, 1, 1),
            ("fracture_modeling", "裂缝建模", "天然裂缝、人工裂缝与裂缝参数", "process", "steel", True, 0, 1, 1, 1),
            ("well_engineering", "井工程", "井位置、井底压力、井半径与井轨迹", "well", "steel", True, 0, 2, 1, 1),
            ("simulation", "数值模拟", "Corner Grid LGR 求解与运行控制", "monitor", "accent", True, 0, 3, 1, 1),
            ("results_visualization", "结果可视化", "压力场、饱和度、渗透率与三维视图", "chart", "accent", True, 0, 4, 1, 1),
            ("grid_import", "网格导入", "GRDECL、COORD、ZCORN 文件导入", "import", "steel", False, 1, 0, 1, 1),
            ("fluid_pvt", "流体与 PVT", "油水参数、真实气体 PVT 和表格", "database", "steel", False, 1, 1, 1, 1),
            ("relative_perm", "相渗设计", "相对渗透率参数与曲线", "chart", "steel", False, 1, 2, 1, 1),
            ("reservoir_analysis", "储层分析", "生产曲线、Blasingame 与结果分析", "search", "neutral", False, 1, 3, 1, 1),
            ("project_management", "工程管理", "最近工程、工程设置、导入导出", "folder", "neutral", False, 1, 4, 1, 1),
            ("help_license", "帮助与许可", "使用说明、许可证状态和日志", "warning", "support", False, 2, 0, 1, 1),
            ("ai_assistant", "AI 助手", "后续接入智能辅助建模与分析", "generic", "support", False, 2, 1, 1, 1),
        ]

        for module_key, title, subtitle, icon, tone, featured, row, col, row_span, col_span in cards:
            card = ModuleCard(module_key, title, subtitle, icon, tone, featured)
            card.selected.connect(self.module_requested)
            grid.addWidget(card, row, col, row_span, col_span)

        for col in range(5):
            grid.setColumnStretch(col, 1)
        layout.addLayout(grid)

        footer = QHBoxLayout()
        brand = QLabel("Oil Reservoir Workbench")
        brand.setObjectName("moduleStartBrand")
        footer.addWidget(brand)
        footer.addStretch()
        hint = QLabel("模块入口会打开工程并定位到对应工作区")
        hint.setObjectName("moduleStartHint")
        footer.addWidget(hint)
        layout.addLayout(footer)
        layout.addStretch()

        scroller.setWidget(content)
        root.addWidget(scroller)
