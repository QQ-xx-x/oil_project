# -*- coding: utf-8 -*-
"""工作台工程面板共享的轻量状态。"""

import os
from dataclasses import dataclass, field


@dataclass
class ProjectState:
    """Store UI-side project parameters without touching the legacy workflow."""

    project_name: str = ""
    algorithm: str = "corner_edfm"
    corner_grid_refinement: str = "加密"
    case_data_path: str = ""
    case_data_summary: dict = field(default_factory=dict)
    case_data_sections: list = field(default_factory=list)
    case_data_schema: dict = field(default_factory=dict)
    case_dataset_path: str = ""
    case_dataset_summary: dict = field(default_factory=dict)
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

    def set_case_data(self, case_data):
        if case_data is None:
            self.case_data_path = ""
            self.case_data_summary = {}
            self.case_data_sections = []
            self.case_data_schema = {}
            self.case_dataset_path = ""
            self.case_dataset_summary = {}
            return
        previous_path = self.case_data_path
        file_refs = case_data.file_refs()
        missing_refs = [item for item in file_refs if not item.file_exists]
        self.case_data_path = case_data.path
        if previous_path and os.path.abspath(previous_path) != os.path.abspath(self.case_data_path):
            self.case_dataset_path = ""
            self.case_dataset_summary = {}
        self.case_data_sections = [section.to_dict() for section in case_data.sections]
        self.case_data_schema = dict(case_data.schema or {})
        self.case_data_summary = {
            "section_count": len(case_data.sections),
            "keyword_count": case_data.keyword_count(),
            "file_ref_count": len(file_refs),
            "missing_file_ref_count": len(missing_refs),
            "error_count": len(case_data.errors),
        }

    def set_case_dataset(self, dataset_path, manifest=None, validation=None):
        """记录 CaseData 生成的标准数据包，供工程保存和模拟入口复用。"""
        self.case_dataset_path = os.path.abspath(dataset_path or "") if dataset_path else ""
        manifest = manifest or {}
        validation = validation or manifest.get("validation", {}) or {}
        self.case_dataset_summary = {
            "schema_version": manifest.get("schema_version", ""),
            "source_case_file": manifest.get("source_case_file", ""),
            "array_count": len(manifest.get("arrays", {}) or {}),
            "source_file_count": len(manifest.get("source_files", []) or []),
            "error_count": validation.get(
                "error_count", len(validation.get("errors", []) or [])),
            "warning_count": validation.get(
                "warning_count", len(validation.get("warnings", []) or [])),
            "manifest_path": os.path.join(self.case_dataset_path, "manifest.json")
            if self.case_dataset_path else "",
        }

    def mark_case_dataset_stale(self, reason="CaseData 已修改，请重新生成 Dataset"):
        """保留输出目录，但提示当前数据包已不再对应最新 CaseData。"""
        if not self.case_dataset_path:
            return
        self.case_dataset_summary["stale"] = True
        self.case_dataset_summary["stale_reason"] = reason
