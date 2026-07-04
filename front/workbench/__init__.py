# -*- coding: utf-8 -*-
"""Workbench package exports."""

__all__ = ["WorkbenchWindow"]


def __getattr__(name):
    if name == "WorkbenchWindow":
        from .window import WorkbenchWindow

        return WorkbenchWindow
    raise AttributeError(name)
