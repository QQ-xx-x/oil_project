#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Independent entry point for the reservoir workbench start page."""

import os
import sys

from PyQt5.QtWidgets import QApplication


ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT_DIR)

from front.workbench.window import WorkbenchWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("储层建模与模拟平台")
    app.setStyle("Fusion")

    style_path = os.path.join(
        ROOT_DIR, "front", "workbench", "resources", "workbench.qss")
    with open(style_path, "r", encoding="utf-8") as style_file:
        app.setStyleSheet(style_file.read())

    window = WorkbenchWindow()
    window.showMaximized()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
