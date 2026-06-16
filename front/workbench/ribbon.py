# -*- coding: utf-8 -*-
"""顶部快速访问区和中文功能区。"""

from PyQt5.QtCore import QSize, Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QSizePolicy, QTabWidget, QToolButton,
    QVBoxLayout, QWidget,
)

from .icon_registry import canonical_icon_kind
from .icons import painted_icon


def _action(text, kind="generic", size="medium", tooltip=None, command=None,
            enabled=True, requires_project=False, requires_results=False):
    return {
        "text": text,
        "kind": kind,
        "size": size,
        "tooltip": tooltip or text,
        "command": command or text,
        "enabled": enabled,
        "requires_project": requires_project,
        "requires_results": requires_results,
    }


def _semantic_icon_kind(kind, text="", tooltip="", command=""):
    content = f"{text} {tooltip} {command}".lower()
    if any(token in content for token in ("校验", "检查", "质控", "qc", "validate", "check")):
        return "validate"
    if any(token in content for token in ("运行", "模拟", "run simulation", "flow simulation")):
        return "run"
    if any(token in content for token in ("结果", "result")):
        return "result"
    if any(token in content for token in ("图层", "layer")):
        return "layer"
    if any(token in content for token in ("压力", "pressure")):
        return "pressure"
    if any(token in content for token in ("饱和度", "saturation")):
        return "saturation"
    if any(token in content for token in ("渗透率", "permeability")):
        return "permeability"
    if any(token in content for token in ("孔隙", "poro")):
        return "porosity"
    if any(token in content for token in ("裂缝", "fracture", "dfn")):
        return "fracture"
    if any(token in content for token in ("井", "well")):
        return "well"
    if any(token in content for token in ("流体", "pvt", "fluid")):
        return "fluid"
    if any(token in content for token in ("岩石", "rock", "petrophysical")):
        return "rock"
    if any(token in content for token in ("网格加密", "局部网格", "lgr")):
        return "lgr"
    if any(token in content for token in ("网格", "grid", "mesh")):
        return "grid"
    if any(token in content for token in ("曲线", "图表", "plot", "chart")):
        return "chart"
    return canonical_icon_kind(kind)


def _tool_button(action):
    size = action["size"]
    button = QToolButton()
    button.setText(action["text"])
    tooltip = action["tooltip"]
    if not action.get("enabled", True):
        reason = action.get("disabled_reason", "当前不可用")
        tooltip = f"{tooltip}\n当前不可用：{reason}"
    button.setToolTip(tooltip)
    button.setProperty("ribbonSize", size)
    button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    button.setEnabled(action.get("enabled", True))

    if size == "small":
        icon_size = 16
        button.setIconSize(QSize(icon_size, icon_size))
        button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        button.setFixedWidth(74)
        button.setFixedHeight(21)
    elif size == "medium":
        icon_size = 24
        button.setIconSize(QSize(icon_size, icon_size))
        button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        button.setFixedWidth(62)
        button.setFixedHeight(64)
    else:
        icon_size = 30
        button.setIconSize(QSize(icon_size, icon_size))
        button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        button.setFixedWidth(70)
        button.setFixedHeight(64)

    button.setIcon(painted_icon(_semantic_icon_kind(
        action["kind"], action["text"], action["tooltip"], action["command"]), icon_size))
    return button


class QuickAccessBar(QWidget):
    command_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("quickAccessBar")
        self.setFixedHeight(24)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 1, 8, 1)
        layout.setSpacing(1)

        groups = [
            [("新建", "new"), ("打开", "folder"), ("保存", "save")],
            [("撤销", "undo"), ("重做", "redo")],
            [("窗口", "window"), ("运行", "monitor"), ("校验", "import")],
        ]
        for group_index, group in enumerate(groups):
            if group_index:
                divider = QFrame()
                divider.setObjectName("quickAccessDivider")
                divider.setFrameShape(QFrame.VLine)
                layout.addWidget(divider)
            for text, kind in group:
                button = QToolButton()
                button.setObjectName("quickAccessButton")
                button.setIcon(painted_icon(_semantic_icon_kind(kind, text), 15))
                button.setIconSize(QSize(15, 15))
                button.setToolTip(text)
                button.setFixedSize(22, 21)
                button.clicked.connect(
                    lambda checked=False, command=text: self.command_requested.emit(command))
                layout.addWidget(button)

        layout.addStretch(1)


class RibbonGroup(QFrame):
    command_requested = pyqtSignal(str)

    def __init__(self, title, actions, parent=None):
        super().__init__(parent)
        self.setObjectName("ribbonGroup")
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        root = QVBoxLayout(self)
        root.setContentsMargins(5, 2, 5, 0)
        root.setSpacing(0)

        body = QHBoxLayout()
        body.setSpacing(2)
        body.setContentsMargins(0, 0, 0, 0)

        small_buffer = []
        for action in actions:
            if action["size"] == "small":
                small_buffer.append(action)
                if len(small_buffer) == 3:
                    body.addWidget(self._small_column(small_buffer))
                    small_buffer = []
                continue
            if small_buffer:
                body.addWidget(self._small_column(small_buffer))
                small_buffer = []
            body.addWidget(self._button(action))

        if small_buffer:
            body.addWidget(self._small_column(small_buffer))

        body.addStretch()
        root.addLayout(body)

        caption = QLabel(title)
        caption.setObjectName("ribbonGroupCaption")
        caption.setAlignment(Qt.AlignCenter)
        caption.setFixedHeight(16)
        root.addWidget(caption)

    def _button(self, action):
        button = _tool_button(action)
        button.clicked.connect(
            lambda checked=False, command=action["command"]:
            self.command_requested.emit(command))
        return button

    def _small_column(self, actions):
        column = QFrame()
        column.setObjectName("ribbonSmallColumn")
        column.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        layout = QVBoxLayout(column)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        for action in actions:
            layout.addWidget(self._button(action))
        layout.addStretch()
        return column


class FileMenuPopup(QFrame):
    command_requested = pyqtSignal(str)
    _project_commands = {"保存工程", "工程另存为", "工程设置", "工程工具", "打印"}

    def __init__(self, parent=None):
        super().__init__(parent, Qt.Popup | Qt.FramelessWindowHint)
        self.setObjectName("fileMenuPopup")
        self.setFixedSize(690, 520)
        self._command_buttons = {}

        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        menu_panel = QFrame()
        menu_panel.setObjectName("fileMenuSide")
        menu_panel.setFixedWidth(278)
        menu_column = QVBoxLayout(menu_panel)
        menu_column.setContentsMargins(18, 14, 14, 14)
        menu_column.setSpacing(3)

        menu_column.addWidget(self._title("文件"))

        for text, kind, command, tooltip, has_submenu in [
            ("保存工程", "save", "保存工程", "保存当前工程文件", False),
            ("工程另存为...", "save", "工程另存为", "将当前工程保存为新的工程文件", False),
            ("打开工程...", "folder", "打开工程", "打开已有工程文件", False),
        ]:
            menu_column.addWidget(self._command_button(text, kind, command, tooltip, has_submenu))
        menu_column.addWidget(self._separator())

        for text, kind, command, tooltip, has_submenu in [
            ("新建工程", "new", "新建工程", "创建一个新的工程", False),
            ("工程设置", "window", "工程设置", "坐标、单位、工程路径等设置", True),
            ("工程工具", "process", "工程工具", "工程清理、检查和维护工具", True),
            ("选项", "generic", "选项", "界面显示和默认参数选项", True),
            ("系统", "monitor", "系统", "运行环境、缓存和系统状态", True),
        ]:
            menu_column.addWidget(self._command_button(text, kind, command, tooltip, has_submenu))
        menu_column.addWidget(self._separator())

        for text, kind, command, tooltip, has_submenu in [
            ("打印...", "window", "打印", "打印当前视图或报告", False),
            ("许可模块", "case", "许可模块", "查看许可模块和授权状态", False),
            ("帮助", "generic", "帮助", "打开帮助说明", True),
            ("链接", "import", "链接", "打开相关资源链接", True),
        ]:
            menu_column.addWidget(self._command_button(text, kind, command, tooltip, has_submenu))
        menu_column.addStretch()

        exit_line = self._separator()
        exit_line.setObjectName("fileMenuExitSeparator")
        menu_column.addWidget(exit_line)
        menu_column.addWidget(self._command_button("退出", "warning", "退出", "退出软件", False))

        content_panel = QFrame()
        content_panel.setObjectName("fileMenuContent")
        recent_column = QVBoxLayout(content_panel)
        recent_column.setContentsMargins(24, 18, 24, 18)
        recent_column.setSpacing(10)
        recent_column.addWidget(self._title("最近工程"))
        for idx, (name, path) in enumerate([
            ("3.18.pet", r"E:\...\3.18.pet"),
            ("400jingju", r"D:\petrelobject\400jingju"),
            ("4501200.pet", r"D:\petrelobject\4501200.pet"),
        ], start=1):
            recent_column.addWidget(self._recent_card(idx, name, path))
        recent_column.addStretch()

        root.addWidget(menu_panel)
        root.addWidget(content_panel, 1)

    def _title(self, text):
        label = QLabel(text)
        label.setObjectName("fileMenuTitle")
        return label

    def _separator(self):
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setObjectName("fileMenuSeparator")
        return line

    def _command_button(self, text, kind, command, tooltip, has_submenu):
        button = QToolButton()
        button.setObjectName("fileMenuCommand")
        button.setText(f"{text}  ›" if has_submenu else text)
        button.setIcon(painted_icon(_semantic_icon_kind(kind, text, tooltip, command), 24))
        button.setIconSize(QSize(24, 24))
        button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        button.setToolTip(tooltip)
        button.setProperty("baseTooltip", tooltip)
        button.setFixedSize(246, 38)
        button.clicked.connect(lambda checked=False, value=command: self._emit_command(value))
        self._command_buttons.setdefault(command, []).append(button)
        return button

    def _recent_card(self, index, name, path):
        card = QFrame()
        card.setObjectName("fileMenuRecentCard")
        card.setToolTip(f"最近打开的工程：{path}")
        layout = QHBoxLayout(card)
        layout.setContentsMargins(10, 7, 10, 7)
        layout.setSpacing(9)

        number = QLabel(str(index))
        number.setObjectName("fileMenuRecentIndex")
        layout.addWidget(number)

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(1)
        title = QLabel(name)
        title.setObjectName("fileMenuRecentName")
        path_label = QLabel(path)
        path_label.setObjectName("fileMenuRecentPath")
        text_layout.addWidget(title)
        text_layout.addWidget(path_label)
        layout.addLayout(text_layout, 1)
        return card

    def set_project_mode(self, enabled):
        for command in self._project_commands:
            for button in self._command_buttons.get(command, []):
                button.setEnabled(enabled)
                if enabled:
                    button.setToolTip(button.property("baseTooltip") or button.toolTip())
                else:
                    base_tooltip = button.property("baseTooltip") or button.toolTip()
                    button.setToolTip(f"{base_tooltip}\n当前不可用：请先打开工程")

    def _emit_command(self, command):
        self.hide()
        self.command_requested.emit(command)


class RibbonWidget(QTabWidget):
    command_requested = pyqtSignal(str)

    _startup_allowed = {
        "透视图", "工具箱", "检查器", "播放器", "视觉过滤", "窗口布局", "全屏",
        "面板", "重置布局", "恢复位置", "订阅", "自动刷新", "健康监视", "演示导出",
    }
    _result_keywords = (
        "结果", "历史拟合", "RFT", "PLT", "目标函数", "代理图", "聚类", "旋风",
        "Tornado", "VFP", "导出3D",
    )
    _unavailable_keywords = ("不可用", "未授权", "许可")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("mainRibbon")
        self.setDocumentMode(True)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(118)
        self._project_mode = False
        self._last_content_index = 1
        self._suppress_tab_handler = False
        self.file_menu = None

        self.base_tabs = [
            "文件", "首页", "地层学", "地震解释", "构造建模", "属性建模",
            "裂缝建模", "油藏工程", "井工程", "模拟", "碳封存",
            "地质力学",
        ]
        self._rebuild_tabs()
        self.currentChanged.connect(self._handle_tab_changed)

    def set_project_mode(self, enabled):
        if self._project_mode == enabled:
            return
        self._project_mode = enabled
        self._rebuild_tabs()

    def _rebuild_tabs(self):
        self._suppress_tab_handler = True
        self.clear()
        tabs = list(self.base_tabs)
        if self._project_mode:
            tabs.extend(["三维"])
        for tab in tabs:
            self._building_tab = tab
            if tab == "文件":
                page = QWidget()
                page.setObjectName("fileRibbonPlaceholder")
            elif tab == "首页":
                page = self._home_page()
            elif tab == "地层学":
                page = self._stratigraphy_page()
            elif tab == "地震解释":
                page = self._seismic_page()
            elif tab == "构造建模":
                page = self._structural_modeling_page()
            elif tab == "属性建模":
                page = self._property_modeling_page()
            elif tab == "裂缝建模":
                page = self._fracture_modeling_page()
            elif tab == "油藏工程":
                page = self._reservoir_engineering_page()
            elif tab == "井工程":
                page = self._well_engineering_page()
            elif tab == "碳封存":
                page = self._carbon_storage_page()
            elif tab == "地质力学":
                page = self._geomechanics_page()
            elif tab == "三维":
                page = self._three_d_page()
            elif tab == "模拟":
                page = self._simulation_page()
            else:
                page = self._placeholder_page(tab)
            self.addTab(page, tab)
            if tab == "三维":
                self.tabBar().setTabTextColor(self.count() - 1, Qt.darkRed)
        self._building_tab = None
        target_index = min(max(self._last_content_index, 1), self.count() - 1)
        self.setCurrentIndex(target_index)
        self._last_content_index = target_index
        self._suppress_tab_handler = False

    def _handle_tab_changed(self, index):
        if self._suppress_tab_handler or index < 0:
            return
        if self.tabText(index) == "文件":
            self._show_file_menu()
            self._suppress_tab_handler = True
            self.setCurrentIndex(self._last_content_index)
            self._suppress_tab_handler = False
            return
        self._last_content_index = index

    def _show_file_menu(self):
        if self.file_menu is None:
            self.file_menu = FileMenuPopup(self)
            self.file_menu.command_requested.connect(self.command_requested)
        self.file_menu.set_project_mode(self._project_mode)
        tab_bar = self.tabBar()
        menu_pos = tab_bar.mapToGlobal(tab_bar.rect().bottomLeft())
        self.file_menu.move(menu_pos)
        self.file_menu.show()
        self.file_menu.raise_()

    def _add_groups(self, page, groups):
        layout = QHBoxLayout(page)
        layout.setContentsMargins(3, 1, 3, 1)
        layout.setSpacing(0)
        for title, actions in groups:
            group = RibbonGroup(title, self._prepare_group_actions(actions))
            group.command_requested.connect(self.command_requested)
            layout.addWidget(group)
        layout.addStretch()

    def _prepare_group_actions(self, actions):
        balanced = []
        prominent_count = 0
        for action in actions:
            action = dict(action)
            if action["size"] != "small":
                prominent_count += 1
                if prominent_count > 3:
                    action["size"] = "small"
            balanced.append(self._apply_action_state(action))
        return balanced

    def _apply_action_state(self, action):
        enabled = action.get("enabled", True)
        reason = ""
        tab = getattr(self, "_building_tab", "")
        text = action["text"]
        tooltip = action.get("tooltip", "")

        if enabled and not self._project_mode and tab not in {"文件", "首页"}:
            enabled = False
            reason = "请先打开工程"
        if enabled and not self._project_mode and tab == "首页" and text not in self._startup_allowed:
            enabled = False
            reason = "请先打开工程"
        if enabled and action.get("requires_project") and not self._project_mode:
            enabled = False
            reason = "请先打开工程"
        if enabled and (action.get("requires_results") or self._looks_like_result_action(text, tooltip)):
            enabled = False
            reason = "需要生成结果后可用"
        if enabled and self._looks_like_unavailable_action(text, tooltip):
            enabled = False
            reason = "当前阶段仅展示界面"

        action["enabled"] = enabled
        if reason:
            action["disabled_reason"] = reason
        return action

    def _looks_like_result_action(self, text, tooltip):
        value = f"{text} {tooltip}"
        return any(keyword in value for keyword in self._result_keywords)

    def _looks_like_unavailable_action(self, text, tooltip):
        value = f"{text} {tooltip}"
        return any(keyword in value for keyword in self._unavailable_keywords)

    def _file_page(self):
        page = QWidget()
        page.setObjectName("fileRibbonPage")
        self._add_groups(page, [
            ("工程", [
                _action("保存", "save", "large", "保存当前工程", command="保存工程"),
                _action("另存为", "save", "large", "将当前工程另存为新文件", command="工程另存为"),
                _action("打开", "folder", "large", "打开已有工程", command="打开工程"),
                _action("新建", "new", "large", "新建工程", command="新建工程"),
            ]),
            ("设置", [
                _action("项目设置", "window", "small", "工程坐标、单位、路径等设置"),
                _action("项目工具", "process", "small", "工程维护、清理和检查工具"),
                _action("选项", "generic", "small", "用户界面和默认参数选项"),
                _action("系统", "monitor", "small", "系统环境和运行状态"),
            ]),
            ("输出", [
                _action("打印", "window", "large", "打印当前视图或报告"),
                _action("许可", "case", "large", "查看许可模块状态", command="许可模块"),
                _action("帮助", "generic", "large", "打开帮助文档"),
                _action("链接", "import", "medium", "打开相关链接"),
                _action("退出", "warning", "medium", "退出软件"),
            ]),
            ("最近工程", [
                _action("3.18.pet", "folder", "small", "最近打开的工程：E:\\...\\3.18.pet"),
                _action("400jingju", "folder", "small", "最近打开的工程目录"),
                _action("教学算例", "folder", "small", "最近打开的教学算例"),
            ]),
        ])
        return page

    def _home_page(self):
        page = QWidget()
        self._add_groups(page, [
            ("透视图", [_action("透视图", "window", "large", "切换工程透视图和工作视角")]),
            ("视图", [
                _action("工具箱", "case", "large", "打开工具面板"),
                _action("检查器", "search", "medium", "显示对象检查器"),
                _action("播放器", "monitor", "medium", "显示动画播放器"),
                _action("视觉过滤", "process", "medium", "配置视觉过滤条件"),
                _action("克隆窗口", "window", "medium", "复制当前窗口"),
                _action("窗口布局", "window", "medium", "选择或保存窗口布局"),
                _action("全屏", "window", "medium", "切换全屏显示"),
            ]),
            ("布局", [
                _action("面板", "window", "small", "显示或隐藏停靠面板"),
                _action("重置布局", "undo", "small", "重置当前窗口布局"),
                _action("恢复位置", "redo", "small", "恢复工具位置"),
            ]),
            ("插入", [
                _action("窗口", "window", "small", "插入新的 2D/3D/图表窗口"),
                _action("对象", "generic", "small", "插入工程对象"),
                _action("文件夹", "folder", "small", "新建工程文件夹"),
            ]),
            ("搜索", [
                _action("工程", "search", "large", "在当前工程中搜索"),
                _action("全部资源", "search", "large", "搜索全部工程资源"),
            ]),
            ("数据管理", [
                _action("工作室", "database", "large", "打开数据工作室"),
                _action("导入文件", "import", "small", "导入外部数据文件"),
                _action("导出文件", "import", "small", "导出当前工程数据"),
                _action("管理器", "window", "small", "打开数据管理器"),
            ]),
            ("传输", [
                _action("传输工具", "process", "large", "打开工程传输工具"),
                _action("参考工程", "folder", "small", "选择参考工程"),
                _action("数据释放", "database", "small", "释放或迁移数据"),
                _action("同步", "import", "small", "同步工程数据"),
            ]),
            ("通知", [
                _action("订阅", "generic", "large", "订阅工程消息"),
                _action("自动刷新", "monitor", "large", "切换自动刷新状态"),
            ]),
            ("剪贴板", [
                _action("粘贴", "generic", "medium", "粘贴剪贴板内容"),
                _action("剪切", "generic", "small", "剪切选中对象"),
                _action("复制", "generic", "small", "复制选中对象"),
                _action("位图", "window", "small", "复制或保存位图"),
                _action("复制外观", "window", "small", "复制对象显示样式"),
                _action("绘制", "chart", "small", "打开绘制选项"),
            ]),
            ("监视", [_action("健康监视", "monitor", "large", "查看运行与资源健康状态")]),
            ("捕获", [_action("演示导出", "generic", "large", "导出演示或截图材料")]),
        ])
        return page

    def _stratigraphy_page(self):
        page = QWidget()
        self._add_groups(page, [
            ("井", [
                _action("新井", "well", "large", "Create new well，新建井对象"),
                _action("保存搜索", "import", "small", "Create saved search，创建已保存搜索"),
                _action("井过滤", "process", "small", "New well filter，新建井过滤器"),
                _action("井管理", "database", "small", "Well data managers，打开井数据管理器"),
            ]),
            ("剖面", [
                _action("剖面编辑", "process", "large", "X-section editing，编辑井剖面"),
                _action("井剖面", "window", "large", "New well section window，新建井剖面窗口"),
            ]),
            ("地层图表", [
                _action("地层窗口", "window", "small", "New stratigraphic window，新建地层窗口"),
                _action("图表编辑", "chart", "small", "Chart editing，编辑地层图表"),
                _action("列数据", "database", "small", "Columns spreadsheet，打开列数据表"),
                _action("新文件夹", "folder", "small", "New folder，新建文件夹"),
                _action("新图表", "chart", "small", "New chart，新建图表"),
                _action("新列", "database", "small", "New column，新建列"),
            ]),
            ("人工测井", [
                _action("离散测井", "database", "small", "New discrete log，新建离散测井"),
                _action("备注测井", "window", "small", "New comment log，新建备注测井"),
                _action("测井校正", "process", "small", "Log conditioning，测井条件校正"),
            ]),
            ("自动测井", [
                _action("测井计算", "database", "large", "Log calculator，测井计算器"),
                _action("神经网络", "process", "small", "Neural net，神经网络预测"),
                _action("网络测井", "database", "small", "Logs from neural net，网络生成测井"),
                _action("测井估计", "chart", "small", "Log estimator，测井估计器"),
            ]),
            ("井对比", [
                _action("井顶文件夹", "folder", "large", "New well tops folder，新建井顶文件夹"),
                _action("编辑井顶", "well", "large", "Edit well tops，编辑井顶"),
                _action("分层测井", "database", "small", "Insert/update zone log，插入或更新分层测井"),
                _action("分层表", "window", "small", "Zone spreadsheet，分层数据表"),
                _action("井顶表", "window", "small", "Well tops spreadsheet，井顶数据表"),
            ]),
            ("工具", [
                _action("生成面", "grid", "large", "Make surface，由井数据生成面"),
                _action("多边形", "process", "large", "Polygon editing，多边形编辑"),
            ]),
            ("高级", [
                _action("专家", "process", "large", "Guru，专家工具"),
                _action("井对置", "chart", "large", "Analyze well juxtaposition，分析井对置关系"),
                _action("栅格测井", "chart", "large", "Raster Digitization，栅格测井数字化"),
                _action("沉积模拟", "monitor", "large", "Run sedimentary simulation，运行沉积模拟"),
                _action("流程播放器", "monitor", "large", "Simulation process player，模拟流程播放器"),
            ]),
        ])
        return page

    def _seismic_page(self):
        page = QWidget()
        self._add_groups(page, [
            ("设置", [
                _action("管理器", "window", "large", "Managers，打开地震解释管理器"),
                _action("数据体", "database", "small", "选择地震数据体"),
                _action("解释集", "folder", "small", "选择解释数据集"),
                _action("属性集", "database", "small", "选择属性集合"),
            ]),
            ("井震标定", [
                _action("井震联结", "chart", "large", "Seismic well tie，井震联结"),
                _action("子波工具", "chart", "small", "Wavelet toolbox，子波工具箱"),
                _action("测井校正", "process", "small", "Log conditioning，测井条件校正"),
                _action("联结编辑", "well", "small", "Well tie editing，井震联结编辑"),
            ]),
            ("辅助解释", [
                _action("机器学习", "process", "large", "Machine learning，机器学习解释"),
                _action("层位提取", "chart", "small", "Horizon extraction，层位提取"),
                _action("层位工具", "process", "small", "Horizon extraction tools，层位提取工具"),
                _action("断层提取", "chart", "small", "Fault extraction，断层提取"),
                _action("断层工具", "process", "small", "Fault extraction tools，断层提取工具"),
                _action("断点集", "database", "small", "Fault point set editing，断点集编辑"),
            ]),
            ("2D/3D 解释", [
                _action("插入", "window", "large", "Insert，插入解释对象"),
                _action("地震解释", "chart", "large", "Seismic interpretation，打开地震解释"),
            ]),
            ("网格", [_action("网格编辑", "grid", "large", "Mesh editing，网格编辑")]),
            ("属性", [
                _action("体属性", "database", "large", "Volume attributes，体属性"),
                _action("混合器", "window", "large", "Mixer，属性混合器"),
                _action("面属性", "database", "small", "Surface attributes，面属性"),
                _action("计算器", "process", "small", "Calculator，属性计算器"),
                _action("神经网络", "process", "small", "Neural net，神经网络属性"),
            ]),
            ("体解释", [
                _action("插入", "window", "large", "Insert，插入体解释对象"),
                _action("地质解释", "chart", "large", "Geo interpretation，地质解释"),
            ]),
            ("构造", [_action("构造工具", "process", "large", "Structure tools，构造工具")]),
            ("构造框架", [
                _action("构造框架", "grid", "small", "Structural framework，构造框架"),
                _action("断层框架", "process", "small", "Fault framework，断层框架"),
                _action("QC 管理", "search", "small", "QC Manager，质量控制管理器"),
            ]),
            ("深度", [
                _action("时深", "chart", "small", "TWT/Depth，时深转换"),
                _action("Z 转换", "chart", "small", "Z conversion，Z 向转换"),
                _action("深度模型", "grid", "small", "Depth model，深度模型"),
            ]),
            ("工具", [
                _action("生成面", "grid", "large", "Make surface，生成面"),
                _action("多边形", "process", "large", "Polygon editing，多边形编辑"),
                _action("专家", "process", "large", "Guru，专家工具"),
            ]),
        ])
        return page

    def _structural_modeling_page(self):
        page = QWidget()
        self._add_groups(page, [
            ("构造框架", [
                _action("构造框架", "grid", "large", "Structural framework，构造框架"),
                _action("断层框架", "process", "large", "Fault framework，断层框架"),
                _action("构造工具", "process", "small", "Structure tools，构造工具"),
                _action("层位清理", "chart", "small", "Horizon clean-up，层位清理"),
                _action("模型边界", "window", "small", "Model boundary，模型边界"),
                _action("模型构建", "grid", "small", "Model construction，模型构建"),
                _action("模型细化", "grid", "small", "Model refinement，模型细化"),
                _action("沉积计算", "process", "small", "Depospace calculation，沉积空间计算"),
                _action("构造网格", "grid", "small", "Structural gridding，构造网格化"),
                _action("QC 管理", "search", "small", "QC Manager，质量控制管理"),
                _action("框架对象", "grid", "small", "Structural framework，框架对象"),
            ]),
            ("角点网格", [
                _action("定义模型", "database", "small", "Define model，定义模型"),
                _action("简单网格", "grid", "small", "Simple grid，简单网格"),
                _action("断层网格", "grid", "small", "SF to fault model，转断层模型"),
                _action("断层对象", "process", "small", "Fault model object，断层模型对象"),
                _action("断层操作", "process", "small", "Fault model operations，断层模型操作"),
                _action("编辑断层", "process", "small", "Edit fault model，编辑断层模型"),
                _action("柱网格", "grid", "medium", "Pillar gridding，柱网格化"),
            ]),
            ("层位与分层", [
                _action("层位", "chart", "small", "Horizons，层位"),
                _action("分区", "database", "small", "Zones，分区"),
                _action("层化", "database", "small", "Layering，层化"),
                _action("层位清理", "chart", "small", "Horizon clean-up，层位清理"),
                _action("网格细化", "grid", "small", "Grid refinement，网格细化"),
                _action("域转换", "process", "small", "Domain conversion，域转换"),
            ]),
            ("网格编辑", [
                _action("放大构造", "grid", "large", "Scale up structure，构造升尺度"),
                _action("局部更新", "process", "large", "Local model update，局部模型更新"),
                _action("编辑3D网格", "grid", "small", "Edit 3D grid，编辑三维网格"),
                _action("局部网格", "grid", "small", "Make local grids，创建局部网格"),
            ]),
            ("网格 QC", [_action("几何QC", "grid", "large", "Geometrical grid QC，几何网格质控")]),
            ("工具", [
                _action("构造工具", "process", "medium", "Structure tools，构造工具"),
                _action("生成面", "grid", "large", "Make surface，生成面"),
                _action("多边形", "process", "large", "Polygon editing，多边形编辑"),
                _action("点编辑", "process", "small", "Point editing，点编辑"),
                _action("制多边形", "process", "small", "Make polygons，生成多边形"),
                _action("面编辑", "grid", "small", "Surface editing，面编辑"),
                _action("专家", "process", "large", "Guru，专家工具"),
            ]),
        ])
        return page

    def _property_modeling_page(self):
        page = QWidget()
        self._add_groups(page, [
            ("数据准备", [
                _action("测井升尺度", "well", "large", "Well log upscaling，测井曲线升尺度"),
                _action("数据分析", "chart", "large", "Data analysis，数据分析"),
                _action("趋势建模", "grid", "large", "Trend modeling，趋势建模"),
                _action("自定义对象", "new", "small", "User-defined object，用户自定义对象"),
                _action("训练图像", "chart", "small", "Training image，训练图像"),
                _action("几何趋势", "process", "small", "Geometrical trend，几何趋势"),
            ]),
            ("属性建模", [
                _action("几何", "grid", "large", "Geometrical，几何建模"),
                _action("相建模", "grid", "large", "Facies，相建模"),
                _action("岩石物理", "database", "large", "Petrophysical，岩石物理建模"),
                _action("计算器", "database", "large", "Calculator，属性计算器"),
            ]),
            ("机器学习", [
                _action("EMBER", "process", "large", "EMBER，机器学习建模"),
                _action("神经网络", "process", "large", "Neural net，神经网络"),
            ]),
            ("体积计算", [
                _action("段", "grid", "large", "Segments，段对象"),
                _action("接触面", "grid", "large", "Contacts，接触面"),
                _action("体积", "database", "large", "Volume，体积对象"),
            ]),
            ("流动诊断", [_action("流动模拟", "monitor", "large", "Flow simulation，流动模拟")]),
            ("工作流", [
                _action("不确定优化", "process", "large", "Uncertainty and optimization，不确定性优化"),
                _action("新工作流", "window", "large", "New workflow，新工作流"),
            ]),
            ("构造", [
                _action("属性分析", "grid", "large", "Property analysis，属性分析"),
                _action("断层属性", "process", "large", "Fault property editing，断层属性编辑"),
            ]),
            ("网格升尺度", [
                _action("构造", "grid", "large", "Structure，构造升尺度"),
                _action("属性", "database", "large", "Property，属性升尺度"),
            ]),
            ("工具", [
                _action("生成面", "grid", "large", "Make surface，生成面"),
                _action("多边形", "process", "large", "Polygon editing，多边形编辑"),
                _action("点编辑", "process", "small", "Point editing，点编辑"),
                _action("制多边形", "process", "small", "Make polygons，生成多边形"),
                _action("面编辑", "grid", "small", "Surface editing，面编辑"),
                _action("专家", "process", "large", "Guru，专家工具"),
            ]),
        ])
        return page

    def _fracture_modeling_page(self):
        page = QWidget()
        self._add_groups(page, [
            ("数据准备与分析", [
                _action("井剖面", "window", "large", "Well section window，井剖面窗口"),
                _action("测井升尺度", "well", "small", "Scale up well logs，测井升尺度"),
                _action("密度裂缝", "chart", "small", "Fracture density，裂缝密度"),
                _action("赤平投影", "chart", "small", "Stereonet window，赤平投影窗口"),
                _action("分配裂缝", "process", "large", "Assign fractures，分配裂缝"),
            ]),
            ("天然裂缝预测", [
                _action("褶皱驱动", "chart", "large", "Folding driver，褶皱驱动"),
                _action("断层驱动", "chart", "large", "Faulting driver，断层驱动"),
                _action("生成属性", "grid", "large", "Generate fracture properties，生成裂缝属性"),
                _action("应力窗口", "window", "small", "Tectonic stress window，构造应力窗口"),
                _action("调整截断", "process", "small", "Adjust fit cut off，调整拟合截断"),
                _action("采集方位", "process", "small", "Gather orientations，采集裂缝方位"),
            ]),
            ("其他驱动", [
                _action("体属性", "database", "large", "Volume attributes，体属性"),
                _action("断层提取", "process", "large", "Fault extraction，断层提取"),
                _action("生成面", "grid", "large", "Make surface，生成面"),
                _action("几何模型", "grid", "large", "Geometrical modeling，几何建模"),
            ]),
            ("裂缝建模", [
                _action("裂缝网络", "process", "large", "Fracture network，裂缝网络"),
                _action("升尺度属性", "grid", "large", "Scale up fracture properties，升尺度裂缝属性"),
                _action("复合网络", "grid", "large", "Composite fracture network，复合裂缝网络"),
            ]),
            ("高级", [_action("专家", "process", "large", "Guru，专家工具")]),
        ])
        return page

    def _reservoir_engineering_page(self):
        page = QWidget()
        self._add_groups(page, [
            ("模型", [
                _action("导入", "import", "large", "Import，导入油藏工程数据"),
                _action("简单网格", "grid", "large", "Simple grid，简单网格"),
            ]),
            ("简单网格", [
                _action("层位", "chart", "small", "Horizons，层位"),
                _action("分区", "database", "small", "Zones，分区"),
                _action("层化", "database", "small", "Layering，层化"),
                _action("局部网格", "grid", "small", "Make local grids，创建局部网格"),
                _action("全局细化", "grid", "small", "Global refinement，全局细化"),
                _action("全局粗化", "grid", "small", "Global coarsening，全局粗化"),
            ]),
            ("裂缝建模", [_action("复合网络", "grid", "large", "Composite fracture network，复合裂缝网络")]),
            ("三维与断层属性", [
                _action("几何模型", "grid", "large", "Geometrical modeling，几何建模"),
                _action("三维属性", "grid", "small", "3D properties，三维属性"),
                _action("升尺度属性", "grid", "small", "Scale up properties，升尺度属性"),
                _action("局部更新", "process", "small", "Local model update，局部模型更新"),
                _action("分配倍数", "database", "small", "Assign multiplier，分配倍数"),
                _action("断层分析", "chart", "small", "Fault analysis，断层分析"),
            ]),
            ("流体", [
                _action("段", "grid", "small", "Segments，段对象"),
                _action("接触面", "grid", "small", "Make contacts，生成接触面"),
                _action("流体模型", "database", "small", "Fluid model，流体模型"),
                _action("流体图", "chart", "large", "Fluid plots，流体图"),
            ]),
            ("初始化", [
                _action("初始条件", "database", "large", "Initial conditions，初始条件"),
                _action("按图初始化", "chart", "large", "Initialize from maps，根据图件初始化"),
            ]),
            ("岩石物理", [
                _action("岩石物理", "database", "large", "Rock physics，岩石物理"),
                _action("饱和度图", "chart", "large", "Saturation plots，饱和度图"),
            ]),
            ("边界", [
                _action("含水层", "database", "large", "Aquifers，含水层"),
                _action("热边界", "database", "large", "Thermal boundary，热边界"),
            ]),
            ("储量", [_action("体积计算", "database", "large", "Volume calculation，体积储量计算")]),
            ("工具", [
                _action("生成面", "grid", "small", "Make surface，生成面"),
                _action("多边形", "process", "small", "Polygon editing，多边形编辑"),
                _action("网格过滤", "process", "small", "Create grid filter，创建网格过滤器"),
                _action("专家", "process", "large", "Guru，专家工具"),
                _action("构造工具", "process", "medium", "Structure tools，构造工具"),
                _action("STT 管理", "window", "large", "STT Manager，STT 管理器"),
            ]),
        ])
        return page

    def _well_engineering_page(self):
        page = QWidget()
        self._add_groups(page, [
            ("井数据", [
                _action("导入", "import", "large", "Import，导入井数据"),
                _action("新井", "well", "large", "New well，新建井"),
                _action("井模板", "window", "large", "Well templates，井模板"),
            ]),
            ("井轨迹", [
                _action("自动设计", "process", "large", "Automated design，自动设计井轨迹"),
                _action("数字化井", "process", "small", "Digitize well，井轨迹数字化"),
                _action("加侧钻", "well", "small", "Add lateral，添加侧钻"),
                _action("井管理", "database", "small", "Well manager，井管理器"),
            ]),
            ("完井", [
                _action("自动设计", "process", "large", "Automated design，自动完井设计"),
                _action("手动设计", "well", "large", "Manual design，手动完井设计"),
                _action("分段", "process", "small", "Segmentation，完井分段"),
                _action("全局属性", "database", "small", "Global properties，全局完井属性"),
                _action("完井管理", "window", "small", "Completions manager，完井管理器"),
            ]),
            ("产能", [
                _action("PIPESIM", "import", "large", "PIPESIM import，导入 PIPESIM 数据"),
                _action("流体模型", "database", "large", "New well fluid model，新建井流体模型"),
                _action("IPR 管理", "window", "large", "IPR-outflow manager，IPR/流出管理器"),
                _action("流程不可用", "warning", "small", "Process unavailable，流程不可用"),
                _action("VFP 结果", "chart", "small", "VFP results，VFP 结果"),
                _action("结果不可用", "warning", "small", "Process unavailable，结果流程不可用"),
            ]),
            ("开发方案", [
                _action("分离器", "process", "large", "Separator modeling，分离器建模"),
                _action("开发策略", "chart", "large", "Development strategy，开发策略"),
                _action("流程不可用", "warning", "small", "Process unavailable，流程不可用"),
                _action("修井候选", "well", "small", "Workover candidates，修井候选井"),
            ]),
            ("钻井模拟", [
                _action("救援井", "well", "large", "Relief well，救援井设计"),
            ]),
            ("高级", [
                _action("专家", "process", "large", "Guru，专家工具"),
            ]),
        ])
        return page

    def _geomechanics_page(self):
        page = QWidget()
        self._add_groups(page, [
            ("网格化", [
                _action("力学网格", "grid", "large", "Geomechanical grid，地质力学网格"),
                _action("简单网格", "grid", "large", "Simple grid，简单网格"),
                _action("层位", "chart", "small", "Horizons，层位"),
                _action("分区", "database", "small", "Zones，分区"),
                _action("层化", "database", "small", "Layering，层化"),
                _action("局部网格", "grid", "large", "Make local grids，创建局部网格"),
            ]),
            ("数据准备", [
                _action("几何建模", "grid", "small", "Geometrical modeling，几何建模"),
                _action("测井升尺度", "well", "small", "Well log upscaling，测井升尺度"),
                _action("岩石物理", "database", "small", "Petrophysical，岩石物理"),
            ]),
            ("属性", [
                _action("材料建模", "database", "large", "Material modeling，材料建模"),
                _action("函数图", "chart", "large", "Function plots，函数图"),
                _action("Quick MEM", "grid", "large", "Quick MEM，快速力学模型"),
                _action("填充属性", "database", "large", "Populate properties，填充属性"),
                _action("不连续体", "process", "large", "Discontinuity modeling，不连续体建模"),
            ]),
            ("加载条件", [
                _action("压温饱", "process", "large", "Pressure, temperature, saturation，压力/温度/饱和度"),
                _action("边界条件", "grid", "large", "Boundary conditions，边界条件"),
            ]),
            ("模拟", [
                _action("定义算例", "case", "large", "Define case，定义模拟算例"),
                _action("不确定优化", "process", "large", "Uncertainty and optimization，不确定性与优化"),
            ]),
            ("结果", [
                _action("应力计算", "database", "large", "Stress calculator，应力计算器"),
                _action("应力图表", "chart", "large", "Stress charting，应力图表"),
                _action("点拾取", "search", "small", "Point picker，点拾取"),
                _action("多值探针", "search", "small", "Multi-value probe，多值探针"),
                _action("导出3D", "import", "small", "Export 3D results，导出三维结果"),
                _action("结果图表", "chart", "large", "Results charting，结果图表"),
            ]),
            ("钻井", [
                _action("泥浆密度", "database", "large", "Mud weight，泥浆密度"),
                _action("钻井集成", "process", "large", "Subsurface to drilling integration，地下到钻井集成"),
                _action("数据释放", "import", "large", "Data liberation，数据释放"),
            ]),
            ("高级", [
                _action("专家", "process", "large", "Guru，专家工具"),
            ]),
        ])
        return page

    def _carbon_storage_page(self):
        page = QWidget()
        self._add_groups(page, [
            ("模拟", [
                _action("碳封存", "database", "large", "Carbon storage，碳封存模拟"),
            ]),
            ("不确定与优化", [
                _action("网格修改", "grid", "large", "Grid property modification，网格属性修改"),
                _action("不确定优化", "process", "large", "Uncertainty and optimization，不确定性与优化"),
            ]),
            ("汇总结果", [
                _action("存储图", "chart", "large", "Storage plots，碳封存图"),
                _action("结果图表", "chart", "small", "Results charting，结果图表"),
                _action("汇总计算", "database", "small", "Summary calculator，汇总计算器"),
            ]),
            ("3D 结果", [
                _action("3D存储", "grid", "large", "3D storage results，三维封存结果"),
                _action("3D分析", "chart", "small", "3D results analysis，三维结果分析"),
                _action("多值探针", "search", "small", "Multi-value probe，多值探针"),
                _action("3D计算器", "database", "small", "3D results calculator，三维结果计算器"),
                _action("播放器", "monitor", "small", "Players，结果播放器"),
            ]),
            ("高级", [
                _action("专家", "process", "large", "Guru，专家工具"),
            ]),
        ])
        return page

    def _three_d_page(self):
        page = QWidget()
        self._add_groups(page, [
            ("窗口", [
                _action("设置", "window", "small", "Settings，三维窗口设置"),
                _action("视图全部", "search", "large", "View all，查看全部对象"),
                _action("设为首页", "window", "small", "Set home，设置当前视角为主页"),
                _action("回首页", "window", "small", "Go home，回到主页视角"),
                _action("上方视图", "grid", "large", "View from above，从上方查看"),
                _action("正交相机", "window", "small", "Orthographic camera，正交相机"),
                _action("防翻滚", "monitor", "small", "Anti roll，防止视角翻滚"),
            ]),
            ("联动", [
                _action("跟踪光标", "process", "large", "Track this cursor，跟踪当前光标"),
                _action("联动相机", "search", "large", "Link this camera，联动当前相机"),
            ]),
            ("可视化", [
                _action("隐藏解释", "monitor", "large", "Hide/redisplay interpretations，隐藏或重新显示解释对象"),
                _action("交会显示", "window", "large", "Visualize on intersection，在交会面上显示"),
                _action("限制", "generic", "large", "Restrict，限制显示范围"),
                _action("清除显示", "warning", "large", "Clear display，清除显示"),
                _action("灯光", "process", "medium", "Light tool，灯光工具"),
            ]),
            ("显示元素", [
                _action("自动图例", "chart", "large", "Auto legend，自动图例"),
                _action("切换背景", "window", "large", "Toggle background，切换背景"),
                _action("指南针", "process", "small", "Compass，指南针"),
                _action("坐标轴", "chart", "small", "Axis，坐标轴"),
                _action("人工层位", "chart", "small", "Artificial horizon，人工层位"),
                _action("性能指标", "monitor", "small", "Performance indicator，性能指标"),
                _action("粘滞光标", "search", "small", "Sticky cursor，粘滞光标"),
                _action("解释窗口", "window", "small", "Interpretation window，解释窗口"),
            ]),
            ("注释", [
                _action("插入", "import", "small", "Insert，插入注释"),
                _action("显示注释", "window", "small", "Show annotations，显示注释"),
                _action("注释管理", "window", "small", "Annotate manager，注释管理器"),
            ]),
            ("捕获", [
                _action("插入位图", "window", "large", "Insert bitmap，插入位图"),
                _action("复制位图", "window", "large", "Copy bitmap，复制位图"),
                _action("导出图形", "import", "small", "Export graphic，导出图形"),
                _action("导入图形", "import", "small", "Import graphic，导入图形"),
                _action("发送到", "import", "small", "Send to，发送到"),
                _action("场景制作", "monitor", "large", "Scene maker，场景制作器"),
                _action("捕获工具", "monitor", "large", "Capture tools，捕获工具"),
            ]),
        ])
        return page

    def _simulation_page(self):
        page = QWidget()
        self._add_groups(page, [
            ("模拟", [
                _action("导入", "import", "small", "导入模拟相关数据"),
                _action("定义算例", "case", "small", "创建或编辑模拟算例"),
                _action("常规模拟", "monitor", "large", "运行常规模拟流程"),
            ]),
            ("算例管理", [
                _action("导出运行", "import", "small", "导出运行文件"),
                _action("报告", "window", "small", "生成模拟报告"),
                _action("关键字", "process", "small", "编辑模拟关键字", command="关键字编辑"),
            ]),
            ("用户编辑", [
                _action("场图", "chart", "large", "查看或编辑场图"),
                _action("结果图表", "chart", "small", "显示结果图表"),
                _action("流程不可用", "warning", "small", "标记不可用流程"),
                _action("汇总计算", "process", "small", "执行汇总计算"),
            ]),
            ("三维结果", [
                _action("三维属性", "grid", "large", "打开三维属性显示"),
                _action("分析结果", "chart", "small", "显示三维分析结果"),
                _action("显示井", "well", "small", "显示或隐藏井"),
                _action("三维结果", "grid", "small", "显示三维结果"),
                _action("流线", "process", "small", "显示流线结果"),
                _action("分配", "database", "small", "分配结果对象"),
                _action("多值探针", "search", "small", "使用多值探针"),
            ]),
            ("历史拟合与优化", [
                _action("三维属性", "grid", "large", "查看历史拟合三维属性"),
                _action("网格修改", "grid", "large", "修改网格属性"),
                _action("不匹配", "chart", "small", "RFT/PLT 不匹配分析"),
                _action("目标函数", "chart", "small", "查看目标函数"),
                _action("不确定优化", "process", "small", "不确定性和优化分析"),
            ]),
            ("算例分析", [
                _action("数据中心", "database", "large", "打开 U&O 数据中心"),
                _action("旋风图", "chart", "large", "显示 Tornado 分析图"),
                _action("分析", "chart", "small", "打开分析菜单"),
                _action("代理图", "chart", "small", "查看代理模型图"),
                _action("表格", "window", "small", "查看分析表格"),
                _action("应用目标", "import", "small", "应用目标设置"),
                _action("聚类分析", "process", "small", "执行聚类分析"),
                _action("RFT/PLT", "chart", "small", "执行 RFT/PLT 分析"),
            ]),
            ("派生算例", [
                _action("转换", "process", "small", "转换算例"),
                _action("重启", "undo", "small", "创建重启算例"),
                _action("扇区", "window", "small", "创建扇区算例"),
            ]),
            ("高级", [
                _action("历史工具", "generic", "large", "历史拟合工具"),
                _action("专家工具", "process", "large", "专家工具设置"),
                _action("快速更新", "monitor", "large", "快速更新模型"),
            ]),
            ("运行", [
                _action("运行模拟", "monitor", "large", "运行当前模拟算例"),
                _action("扫描结果", "search", "small", "扫描已有模拟结果"),
                _action("刷新结果", "import", "small", "刷新结果图表和数据"),
            ]),
        ])
        return page

    def _placeholder_page(self, tab):
        page = QWidget()
        layout = QHBoxLayout(page)
        label = QLabel(f"{tab} 功能区后续按截图继续补齐")
        label.setObjectName("ribbonPlaceholder")
        layout.addWidget(label)
        layout.addStretch()
        return page
