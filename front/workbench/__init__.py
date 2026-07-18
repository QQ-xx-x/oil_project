# -*- coding: utf-8 -*-
"""工作台包导出项。"""

__all__ = ["WorkbenchWindow"]


def __getattr__(name):
    if name == "WorkbenchWindow":
        from .window import WorkbenchWindow

        return WorkbenchWindow
    raise AttributeError(name)
