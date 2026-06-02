# -*- coding: utf-8 -*-
"""Lightweight state shared by the workbench project panels."""

from dataclasses import dataclass, field


@dataclass
class ProjectState:
    """Store UI-side project parameters without touching the legacy workflow."""

    project_name: str = ""
    checked_items: dict = field(default_factory=dict)
    module_values: dict = field(default_factory=dict)

    def set_checked(self, key, checked):
        if key:
            self.checked_items[key] = bool(checked)

    def is_checked(self, key, default=False):
        return self.checked_items.get(key, default)

    def set_module_values(self, key, values):
        if key:
            self.module_values[key] = dict(values or {})

    def get_module_values(self, key):
        return dict(self.module_values.get(key, {}))
