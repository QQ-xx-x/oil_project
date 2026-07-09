# -*- coding: utf-8 -*-
"""工作台工程面板共享的轻量状态。"""

import copy
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .case_config_sync import (
    sync_project_modules_from_case_data,
    sync_project_modules_from_dataset,
)

MODEL_TYPE_NORMAL = "normal"
MODEL_TYPE_WR = "wr"
GRID_TYPE_CORNER_POINT = "corner_point"
WR_INPUT_MODE_FILE = "file"
WR_INPUT_MODE_CONSTANT = "constant"
WR_INPUT_MODE_MIXED = "mixed"
CASE_TYPE_GAS_WATER = "gas_water"


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _new_case_id():
    return f"case_{uuid.uuid4().hex[:12]}"


@dataclass
class CaseInfo:
    """Lightweight case metadata. Inputs remain project-level in this phase."""

    case_id: str = ""
    case_name: str = "NewCase"
    case_type: str = CASE_TYPE_GAS_WATER
    description: str = ""
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        if not self.case_id:
            self.case_id = _new_case_id()
        if not self.case_name:
            self.case_name = "NewCase"
        if self.case_type != CASE_TYPE_GAS_WATER:
            self.case_type = CASE_TYPE_GAS_WATER
        now = _utc_now()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = self.created_at

    def to_dict(self):
        return {
            "case_id": self.case_id,
            "case_name": self.case_name,
            "case_type": self.case_type,
            "description": self.description,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, payload):
        payload = payload or {}
        return cls(
            case_id=payload.get("case_id", ""),
            case_name=payload.get("case_name", "NewCase"),
            case_type=payload.get("case_type", CASE_TYPE_GAS_WATER),
            description=payload.get("description", ""),
            created_at=payload.get("created_at", ""),
            updated_at=payload.get("updated_at", ""),
        )


def default_model_config():
    return {
        "schema_version": 1,
        "model_type": MODEL_TYPE_NORMAL,
        "grid_type": GRID_TYPE_CORNER_POINT,
        "enable_lgr": True,
        "enable_natural_fractures": True,
        "enable_hydraulic_fractures": False,
        "enable_real_gas_pvt": True,
        "wr_input_mode": WR_INPUT_MODE_FILE,
        "confirmed": False,
    }


def normalize_model_config(config=None, legacy_refinement=None):
    normalized = default_model_config()
    if legacy_refinement is not None and not config:
        normalized["enable_lgr"] = str(legacy_refinement).strip() not in {
            "", "0", "false", "False", "不加密",
        }

    if isinstance(config, dict):
        normalized.update({
            key: value
            for key, value in config.items()
            if key in normalized
        })

    if normalized["model_type"] not in {MODEL_TYPE_NORMAL, MODEL_TYPE_WR}:
        normalized["model_type"] = MODEL_TYPE_NORMAL
    if normalized["grid_type"] not in {GRID_TYPE_CORNER_POINT}:
        normalized["grid_type"] = GRID_TYPE_CORNER_POINT
    if normalized["wr_input_mode"] not in {
        WR_INPUT_MODE_FILE,
        WR_INPUT_MODE_CONSTANT,
        WR_INPUT_MODE_MIXED,
    }:
        normalized["wr_input_mode"] = WR_INPUT_MODE_FILE

    for key in (
        "enable_lgr",
        "enable_natural_fractures",
        "enable_hydraulic_fractures",
        "enable_real_gas_pvt",
        "confirmed",
    ):
        normalized[key] = bool(normalized.get(key))
    normalized["schema_version"] = int(normalized.get("schema_version") or 1)
    return normalized


@dataclass
class ProjectState:
    """Store UI-side project parameters without touching the legacy workflow."""

    project_name: str = ""
    project_file_path: str = ""
    algorithm: str = "corner_edfm"
    corner_grid_refinement: str = "加密"
    model_config: dict = field(default_factory=default_model_config)
    case_data_path: str = ""
    case_data_summary: dict = field(default_factory=dict)
    case_data_sections: list = field(default_factory=list)
    case_data_schema: dict = field(default_factory=dict)
    case_dataset_path: str = ""
    case_dataset_summary: dict = field(default_factory=dict)
    checked_items: dict = field(default_factory=dict)
    module_values: dict = field(default_factory=dict)
    ui_state: dict = field(default_factory=dict)
    cases: list = field(default_factory=list)
    active_case_id: str = ""

    def __post_init__(self):
        self.model_config = normalize_model_config(
            self.model_config, self.corner_grid_refinement)
        self.cases = self._normalize_cases(self.cases)
        if self.active_case_id and not self.case_by_id(self.active_case_id):
            self.active_case_id = ""
        if not self.active_case_id and self.cases:
            self.active_case_id = self.cases[0].case_id

    def _normalize_cases(self, cases):
        normalized = []
        seen = set()
        for item in cases or []:
            case = item if isinstance(item, CaseInfo) else CaseInfo.from_dict(item)
            if case.case_id in seen:
                case.case_id = _new_case_id()
            seen.add(case.case_id)
            normalized.append(case)
        return normalized

    def case_by_id(self, case_id):
        for case in self.cases:
            if case.case_id == case_id:
                return case
        return None

    def active_case(self):
        return self.case_by_id(self.active_case_id)

    def has_active_case(self):
        return self.active_case() is not None

    def add_case(self, case_name="NewCase", case_type=CASE_TYPE_GAS_WATER,
                 description="", activate=True):
        existing_names = {case.case_name for case in self.cases}
        name = case_name or "NewCase"
        if name in existing_names:
            base = name
            index = 1
            while f"{base}{index}" in existing_names:
                index += 1
            name = f"{base}{index}"
        case = CaseInfo(
            case_name=name,
            case_type=case_type,
            description=description,
        )
        self.cases.append(case)
        if activate:
            self.active_case_id = case.case_id
        return case

    def select_case(self, case_id):
        if not self.case_by_id(case_id):
            return False
        self.active_case_id = case_id
        return True

    def rename_case(self, case_id, case_name):
        case = self.case_by_id(case_id)
        if not case or not case_name:
            return False
        case.case_name = case_name
        case.updated_at = _utc_now()
        return True

    def delete_case(self, case_id):
        before = len(self.cases)
        self.cases = [case for case in self.cases if case.case_id != case_id]
        if len(self.cases) == before:
            return False
        if self.active_case_id == case_id:
            self.active_case_id = self.cases[0].case_id if self.cases else ""
        return True

    def duplicate_case(self, case_id):
        source = self.case_by_id(case_id)
        if not source:
            return None
        return self.add_case(
            case_name=f"{source.case_name}_copy",
            case_type=source.case_type,
            description=source.description,
            activate=True,
        )

    def ensure_legacy_case(self):
        if self.cases:
            return self.active_case()
        has_legacy_input = any([
            self.case_data_path,
            self.case_dataset_path,
            self.case_data_sections,
            self.module_values,
        ])
        if not has_legacy_input:
            return None
        return self.add_case(case_name=self.project_name or "DefaultCase")

    def set_model_config(self, config):
        self.model_config = normalize_model_config(
            config, self.corner_grid_refinement)
        self.corner_grid_refinement = (
            "加密" if self.model_config.get("enable_lgr") else "不加密"
        )

    def update_model_config(self, **updates):
        config = dict(self.model_config or {})
        config.update(updates)
        self.set_model_config(config)

    def is_wr_model(self):
        return self.model_config.get("model_type") == MODEL_TYPE_WR

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
        sync_project_modules_from_case_data(self)

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
        sync_project_modules_from_dataset(self, self.case_dataset_path)

    def mark_case_dataset_stale(self, reason="CaseData 已修改，请重新生成 Dataset"):
        """保留输出目录，但提示当前数据包已不再对应最新 CaseData。"""
        if not self.case_dataset_path:
            return
        self.case_dataset_summary["stale"] = True
        self.case_dataset_summary["stale_reason"] = reason

    def to_dict(self):
        """导出轻量工程状态，用于写入 .oilproj。"""
        return {
            "project_name": self.project_name,
            "project_file_path": self.project_file_path,
            "algorithm": self.algorithm,
            "corner_grid_refinement": self.corner_grid_refinement,
            "model_config": copy.deepcopy(self.model_config),
            "case_data_path": self.case_data_path,
            "case_data_summary": copy.deepcopy(self.case_data_summary),
            "case_data_sections": copy.deepcopy(self.case_data_sections),
            "case_data_schema": copy.deepcopy(self.case_data_schema),
            "case_dataset_path": self.case_dataset_path,
            "case_dataset_summary": copy.deepcopy(self.case_dataset_summary),
            "checked_items": copy.deepcopy(self.checked_items),
            "module_values": copy.deepcopy(self.module_values),
            "ui_state": copy.deepcopy(self.ui_state),
            "cases": [case.to_dict() for case in self.cases],
            "active_case_id": self.active_case_id,
        }

    @classmethod
    def from_dict(cls, payload):
        """从 .oilproj 载入轻量工程状态。"""
        payload = payload or {}
        state = cls(project_name=payload.get("project_name", ""))
        for field_name in (
            "project_file_path",
            "algorithm",
            "corner_grid_refinement",
            "model_config",
            "case_data_path",
            "case_data_summary",
            "case_data_sections",
            "case_data_schema",
            "case_dataset_path",
            "case_dataset_summary",
            "checked_items",
            "module_values",
            "ui_state",
            "cases",
            "active_case_id",
        ):
            if field_name in payload:
                setattr(state, field_name, copy.deepcopy(payload.get(field_name)))
        state.model_config = normalize_model_config(
            payload.get("model_config"), state.corner_grid_refinement)
        state.corner_grid_refinement = (
            "加密" if state.model_config.get("enable_lgr") else "不加密"
        )
        state.cases = state._normalize_cases(getattr(state, "cases", []) or [])
        if state.active_case_id and not state.case_by_id(state.active_case_id):
            state.active_case_id = ""
        if not state.active_case_id and state.cases:
            state.active_case_id = state.cases[0].case_id
        state.ensure_legacy_case()
        if state.case_data_sections:
            sync_project_modules_from_case_data(state)
        if state.case_dataset_path:
            sync_project_modules_from_dataset(state, state.case_dataset_path)
        return state
