# -*- coding: utf-8 -*-
"""显示启动、工程状态和流程消息的日志面板。"""

from html import escape

from PyQt5.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QLabel, QMenu, QTextEdit,
    QToolButton, QVBoxLayout, QWidget,
)

from .icons import painted_icon


class MessageLogPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("messageLogPanel")
        self._pinned = True
        self._collapsed = False

        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(0, 0, 0, 0)
        self.root_layout.setSpacing(0)

        self.header = QFrame()
        self.header.setObjectName("logHeader")
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(8, 2, 5, 2)
        self.title = QLabel("消息日志")
        self.title.setObjectName("panelTitle")
        header_layout.addWidget(self.title)
        header_layout.addStretch()
        self.menu_button = self._header_button("▾", "面板菜单")
        self.pin_button = self._header_button("⚑", "固定面板")
        self.close_button = self._header_button("×", "折叠面板")
        header_layout.addWidget(self.menu_button)
        header_layout.addWidget(self.pin_button)
        header_layout.addWidget(self.close_button)
        self.root_layout.addWidget(self.header)

        self.tools = QFrame()
        self.tools.setObjectName("logTools")
        tools_layout = QHBoxLayout(self.tools)
        tools_layout.setContentsMargins(6, 3, 6, 2)
        tools_layout.setSpacing(4)
        for tooltip, kind in [("清空日志", "new"), ("复制日志", "copy"),
                              ("保存日志", "save")]:
            button = QToolButton()
            button.setIcon(painted_icon(kind, 21))
            button.setToolTip(tooltip)
            if tooltip == "清空日志":
                button.clicked.connect(self.clear_messages)
            elif tooltip == "复制日志":
                button.clicked.connect(self.copy_messages)
            else:
                button.clicked.connect(
                    lambda: self.append_message("[面板] 保存日志功能后续接入"))
            tools_layout.addWidget(button)
        tools_layout.addStretch()
        self.root_layout.addWidget(self.tools)

        self.text = QTextEdit()
        self.text.setObjectName("messageLogText")
        self.text.setReadOnly(True)
        self.append_message("诊断信息采集已启用")
        self.append_message("[系统] 平台初始化完成，等待打开工程。")
        self.root_layout.addWidget(self.text, 1)

        self._setup_menu()

    def append_message(self, message):
        color = self._message_color(message)
        safe_message = escape(str(message)).replace("\n", "<br>")
        self.text.append(
            f'<span style="color:{color};">{safe_message}</span>')

    def clear_messages(self):
        self.text.clear()
        self.append_message("[面板] 消息日志已清空")

    def copy_messages(self):
        QApplication.clipboard().setText(self.text.toPlainText())
        self.append_message("[面板] 消息日志已复制到剪贴板")

    def _message_color(self, message):
        text = str(message).lower()
        if any(token in text for token in ("error", "错误", "失败", "runner error", "traceback")):
            return "#b42318"
        if any(token in text for token in ("warning", "警告", "缺失")):
            return "#9a6700"
        if any(token in text for token in ("[运行]", "运行", "simulation")):
            return "#245c8a"
        if any(token in text for token in ("[casedata]", "casedata")):
            return "#2f6f78"
        if any(token in text for token in ("[结果]", "result")):
            return "#257253"
        if any(token in text for token in ("[系统]", "[面板]")):
            return "#59636f"
        return "#30343a"

    def _header_button(self, text, tooltip):
        button = QToolButton()
        button.setObjectName("panelHeaderButton")
        button.setText(text)
        button.setToolTip(tooltip)
        button.setAutoRaise(True)
        return button

    def _setup_menu(self):
        menu = QMenu(self)
        menu.addAction("清空日志", self.clear_messages)
        menu.addAction("复制日志", self.copy_messages)
        menu.addAction("刷新", lambda: self.append_message("[面板] 消息日志已刷新"))
        menu.addSeparator()
        menu.addAction("重置面板布局", self.reset_panel)
        self.menu_button.setMenu(menu)
        self.menu_button.setPopupMode(QToolButton.InstantPopup)
        self.pin_button.clicked.connect(self.toggle_pin)
        self.close_button.clicked.connect(self.toggle_collapsed)

    def toggle_pin(self):
        self._pinned = not self._pinned
        self.pin_button.setText("⚑" if self._pinned else "◇")
        state = "固定" if self._pinned else "自动隐藏"
        self.append_message(f"[面板] 消息日志已切换为{state}")

    def toggle_collapsed(self):
        self.set_collapsed(not self._collapsed)

    def set_collapsed(self, collapsed):
        self._collapsed = bool(collapsed)
        self.tools.setVisible(not self._collapsed)
        self.text.setVisible(not self._collapsed)
        self.close_button.setText("□" if self._collapsed else "×")
        self.close_button.setToolTip("展开面板" if self._collapsed else "折叠面板")
        self.setMaximumHeight(self.header.sizeHint().height() + 2 if self._collapsed else 16777215)
        if not self._collapsed:
            self.append_message("[面板] 消息日志已展开")

    def reset_panel(self):
        self._pinned = True
        self.pin_button.setText("⚑")
        self.set_collapsed(False)
        self.append_message("[面板] 消息日志布局已重置")
