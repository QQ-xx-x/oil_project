# -*- coding: utf-8 -*-
"""Build a runnable Dataset from isolated business-module input states."""

import copy
import json
import math
import os
from dataclasses import dataclass, field

from .case_artifact_repository import CaseArtifactRepository
from .case_dataset_builder import build_case_dataset
from .case_models import new_dataset_id
from .input_keyword_registry import (
    KEYWORD_RULES,
    MODULE_FLUID_PVT,
    MODULE_FRACTURE_SYSTEM,
    MODULE_GRID_SPATIAL,
    MODULE_INITIAL_CONDITIONS,
    MODULE_MODEL_CONFIGURATION,
    MODULE_ROCK_PROPERTIES,
    MODULE_SOLVER_OUTPUT,
    MODULE_WELL_PRODUCTION,
    PARSER_LIST,
    PARSER_SCALAR,
)
from .project_state import MODEL_TYPE_WR, WR_INPUT_MODE_FILE, normalize_model_config


MODULE_TITLES = {
    MODULE_GRID_SPATIAL: "网格与空间数据",
    MODULE_ROCK_PROPERTIES: "储层岩石属性",
    MODULE_FRACTURE_SYSTEM: "裂缝系统",
    MODULE_FLUID_PVT: "流体与 PVT",
    MODULE_INITIAL_CONDITIONS: "初始状态",
    MODULE_WELL_PRODUCTION: "井与生产控制",
    MODULE_SOLVER_OUTPUT: "求解与输出控制",
}

BASE_REQUIRED_FIELDS = {
    MODULE_GRID_SPATIAL: (
        "grid", "matrix_phi", "matrix_kx", "matrix_ky", "matrix_kz",
    ),
    MODULE_ROCK_PROPERTIES: ("n",),
    MODULE_FLUID_PVT: (
        "mu_w", "mu_o", "cw", "co", "p_ref", "swi", "sor", "sgc",
    ),
    MODULE_INITIAL_CONDITIONS: ("pressure", "sw", "sg"),
    MODULE_WELL_PRODUCTION: ("wells",),
    MODULE_SOLVER_OUTPUT: ("total_time", "dt_init", "dt_min", "dt_max"),
}

GAS_REQUIRED_FIELDS = (
    "temperature_c", "mole_ch4", "mole_c2h6", "mole_c3h8", "mole_n2",
    "mole_co2", "mole_h2o", "mole_unknown", "gas_table_pmin_bar",
    "gas_table_pmax_bar", "gas_table_n",
)


@dataclass
class ModuleDatasetBuildResult:
    success: bool
    errors: tuple = ()
    warnings: tuple = ()
    output_dir: str = ""
    snapshot_path: str = ""
    dataset_id: str = ""
    manifest: dict = field(default_factory=dict)
    validation: dict = field(default_factory=dict)
    record: object = None


class ModuleDatasetService:
    """Validate, compose, build and register the active case Dataset."""

    def __init__(self, project_state, repository=None, project_root=None):
        if project_state is None:
            raise ValueError("project_state is required")
        self.project_state = project_state
        self.repository = (
            repository
            or getattr(project_state, "artifact_repository", None)
            or CaseArtifactRepository(
                project_state, project_root=project_root or os.getcwd())
        )

    def validate_inputs(self):
        errors = []
        warnings = []
        if not self.project_state.has_active_case():
            return ["请先新建或选择一个算例。"], warnings

        config = normalize_model_config(self.project_state.model_config)
        if not config.get("confirmed"):
            errors.append("模型配置尚未确认。")

        required_fields = dict(BASE_REQUIRED_FIELDS)
        if config.get("enable_real_gas_pvt"):
            required_fields[MODULE_FLUID_PVT] = (
                required_fields[MODULE_FLUID_PVT] + GAS_REQUIRED_FIELDS)
        if (config.get("enable_natural_fractures")
                or config.get("enable_hydraulic_fractures")
                or config.get("model_type") == MODEL_TYPE_WR):
            required_fields[MODULE_FRACTURE_SYSTEM] = ()
        if (config.get("model_type") == MODEL_TYPE_WR
                and config.get("wr_input_mode") == WR_INPUT_MODE_FILE):
            required_fields[MODULE_ROCK_PROPERTIES] = (
                required_fields[MODULE_ROCK_PROPERTIES] + ("shape_factor",))
            required_fields[MODULE_FRACTURE_SYSTEM] = (
                "fracture_phi", "fracture_kx", "fracture_ky", "fracture_kz")

        states = {}
        for module_key, fields in required_fields.items():
            state = self.project_state.get_module_input_state(module_key)
            states[module_key] = state
            title = MODULE_TITLES[module_key]
            if state is None:
                errors.append(f"{title}尚未导入或设置。")
                continue
            if not (state.validation or {}).get("ok", False):
                errors.append(f"{title}校验未通过。")
                continue
            values = state.parsed_data.values
            missing = [field for field in fields if not _has_business_value(values, field)]
            if missing:
                errors.append(f"{title}缺少 {len(missing)} 项必要业务数据。")

        fracture_state = states.get(MODULE_FRACTURE_SYSTEM)
        fracture_values = (
            fracture_state.parsed_data.values
            if fracture_state is not None else {})
        if (config.get("enable_natural_fractures")
                and not _has_business_value(
                    fracture_values, "natural_fractures")):
            errors.append("裂缝系统缺少天然裂缝数据。")
        if (config.get("enable_hydraulic_fractures")
                and not (fracture_values.get("hydraulic_fractures") or [])):
            errors.append("裂缝系统缺少人工裂缝参数。")

        for module_key, state in states.items():
            if state is None:
                continue
            for record in ((state.source or {}).get("keywords") or {}).values():
                path = str((record or {}).get("resolved_path") or "").strip()
                if path and not os.path.isfile(path):
                    errors.append(
                        f"{MODULE_TITLES[module_key]}的一项数据内容已不可用。")
                    break
        return _unique(errors), _unique(warnings)

    def build(self):
        errors, warnings = self.validate_inputs()
        if errors:
            return ModuleDatasetBuildResult(
                success=False,
                errors=tuple(errors),
                warnings=tuple(warnings),
            )

        case = self.project_state.active_case()
        dataset_id = new_dataset_id()
        try:
            dataset_id, output_dir = self.repository.allocate_dataset_dir(
                case.case_id, dataset_id)
            snapshot_path = self.repository.snapshot_path(
                case.case_id, case.input_state.input_revision)
            sections = self._compose_sections()
            _write_case_snapshot(snapshot_path, sections)
            overrides = self._business_overrides()
            result = build_case_dataset(
                snapshot_path,
                output_dir,
                model_config=self.project_state.model_config,
                business_overrides=overrides,
            )
        except (OSError, TypeError, ValueError) as exc:
            return ModuleDatasetBuildResult(
                success=False,
                errors=("Dataset 生成过程未完成，请检查当前模块数据。",),
                warnings=tuple(warnings),
                dataset_id=dataset_id,
                validation={"internal_error": str(exc)},
            )

        build_errors = list(result.validation.get("errors") or [])
        build_warnings = list(result.validation.get("warnings") or [])
        if build_errors:
            return ModuleDatasetBuildResult(
                success=False,
                errors=(
                    f"Dataset 底层校验未通过（{len(build_errors)} 项），"
                    "请检查网格、属性和模块参数。",
                ),
                warnings=tuple(warnings),
                output_dir=result.output_dir,
                snapshot_path=snapshot_path,
                dataset_id=dataset_id,
                manifest=result.manifest,
                validation=result.validation,
            )

        result.manifest.update({
            "case_id": case.case_id,
            "dataset_id": dataset_id,
            "business_input_revision": case.input_state.input_revision,
            "module_revisions": {
                module_key: state.revision
                for module_key, state in case.input_state.module_inputs.items()
            },
            "ui_case_data_source": {
                "mode": "business_module_snapshot",
            },
        })
        try:
            with open(result.manifest_path, "w", encoding="utf-8") as file:
                json.dump(result.manifest, file, ensure_ascii=False, indent=2)
            record = self.project_state.set_case_dataset(
                result.output_dir,
                result.manifest,
                result.validation,
                dataset_id=dataset_id,
            )
        except (OSError, TypeError, ValueError) as exc:
            return ModuleDatasetBuildResult(
                success=False,
                errors=("Dataset 已完成计算，但未能登记到当前算例。",),
                warnings=tuple(warnings),
                output_dir=result.output_dir,
                snapshot_path=snapshot_path,
                dataset_id=dataset_id,
                manifest=result.manifest,
                validation={
                    **dict(result.validation or {}),
                    "internal_registration_error": str(exc),
                },
            )
        safe_warnings = list(warnings)
        if build_warnings:
            safe_warnings.append(
                f"Dataset 生成完成，包含 {len(build_warnings)} 项校验提示。")
        return ModuleDatasetBuildResult(
            success=True,
            warnings=tuple(_unique(safe_warnings)),
            output_dir=result.output_dir,
            snapshot_path=snapshot_path,
            dataset_id=dataset_id,
            manifest=result.manifest,
            validation=result.validation,
            record=record,
        )

    def _compose_sections(self):
        config = normalize_model_config(self.project_state.model_config)
        sections = {
            "LGR": {
                "enable_lgr": config.get("enable_lgr"),
                "d_threshold": config.get("lgr_d_threshold"),
                "nrx": config.get("lgr_nrx"),
                "nry": config.get("lgr_nry"),
                "nrz": config.get("lgr_nrz"),
            },
        }
        for rule in KEYWORD_RULES:
            if rule.module_key == MODULE_MODEL_CONFIGURATION:
                continue
            state = self.project_state.get_module_input_state(rule.module_key)
            if state is None:
                continue
            value = _rule_snapshot_value(rule, state)
            if value is None:
                continue
            sections.setdefault(rule.section, {})[rule.keyword] = value

        hydraulic = self._hydraulic_override()
        if hydraulic:
            fracture = sections.setdefault("FRACTURE", {})
            fracture.update({
                "hydraulic_fracture_count": hydraulic.get("count"),
                "hydraulic_fracture_spacing": hydraulic.get("spacing_x"),
                "hydraulic_fracture_length": hydraulic.get("length"),
                "hydraulic_fracture_height": hydraulic.get("height"),
                "hydraulic_fracture_aperture": hydraulic.get("aperture"),
                "hydraulic_fracture_permeability": hydraulic.get("perm"),
                "hydraulic_fracture_center_x": hydraulic.get("center_x"),
                "hydraulic_fracture_center_y": hydraulic.get("center_y"),
                "hydraulic_fracture_center_z": hydraulic.get("center_z"),
            })
        return sections

    def _business_overrides(self):
        overrides = {}
        hydraulic = self._hydraulic_override()
        if hydraulic:
            overrides["hydraulic_fractures"] = hydraulic
        well_state = self.project_state.get_module_input_state(
            MODULE_WELL_PRODUCTION)
        if well_state is not None:
            wells = (well_state.parsed_data.values.get("wells") or {})
            overrides["wells"] = _dataset_wells_from_business(wells)
        return overrides

    def _hydraulic_override(self):
        state = self.project_state.get_module_input_state(
            MODULE_FRACTURE_SYSTEM)
        rows = (
            state.parsed_data.values.get("hydraulic_fractures") or []
            if state is not None else [])
        if not rows:
            return {}
        numeric = {
            key: [_finite_float(row.get(key)) for row in rows]
            for key in (
                "center_x", "center_y", "center_z", "length", "height",
                "aperture", "perm", "conductivity")
        }
        center_x_values = sorted(
            value for value in numeric["center_x"] if value is not None)
        spacing = 0.0
        if len(center_x_values) > 1:
            spacing = sum(
                center_x_values[index] - center_x_values[index - 1]
                for index in range(1, len(center_x_values))
            ) / (len(center_x_values) - 1)
        return {
            "count": len(rows),
            "spacing_x": spacing,
            "length": _mean(numeric["length"], 0.0),
            "height": _mean(numeric["height"], 0.0),
            "aperture": _mean(numeric["aperture"], 0.0),
            "perm": _mean(numeric["perm"], 0.0),
            "conductivity": _mean(numeric["conductivity"], 0.0),
            "center_x": _mean(numeric["center_x"], -1.0),
            "center_y": _mean(numeric["center_y"], -1.0),
            "center_z": _mean(numeric["center_z"], -1.0),
            "records": copy.deepcopy(rows),
        }


def _has_business_value(values, key):
    if key not in values:
        return False
    value = values.get(key)
    if value is None or value == "":
        return False
    if isinstance(value, dict) and not value:
        return False
    if isinstance(value, (list, tuple)) and not value:
        return False
    return True


def _rule_snapshot_value(rule, state):
    if rule.parser_kind in {PARSER_SCALAR, PARSER_LIST}:
        return state.parsed_data.values.get(rule.parsed_key)
    record = ((state.source or {}).get("keywords") or {}).get(
        rule.qualified_name) or {}
    return str(record.get("resolved_path") or "").strip() or None


def _write_case_snapshot(path, sections):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    lines = ["// 由业务模块状态合成，仅供 Dataset 生成使用。", ""]
    for section, values in sections.items():
        clean = [(key, value) for key, value in values.items() if value is not None]
        if not clean:
            continue
        lines.append(f"[{section}]")
        for key, value in clean:
            lines.append(f"{key} = {_format_case_value(value)}")
        lines.append("")
    with open(path, "w", encoding="utf-8") as file:
        file.write("\n".join(lines).rstrip() + "\n")


def _format_case_value(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, tuple)):
        return ", ".join(_format_case_value(item) for item in value)
    if isinstance(value, float):
        return f"{value:.15g}"
    return str(value)


def _dataset_wells_from_business(wells):
    wells = wells or {}
    well_list = list(wells.get("well_list") or [])
    lookup = {
        str(row.get("well_name") or ""): {
            "well_name": str(row.get("well_name") or ""),
            "well_type": row.get("well_type", ""),
            "track": [],
            "completion_definitions": [],
            "events": [],
            "md_min_m": row.get("md_min"),
            "md_max_m": row.get("md_max"),
        }
        for row in well_list if isinstance(row, dict)
    }
    for row in wells.get("tracks") or []:
        if not isinstance(row, dict):
            continue
        name = str(row.get("well_name") or "")
        well = lookup.setdefault(name, _empty_dataset_well(name))
        point = copy.deepcopy(row)
        point.pop("well_name", None)
        well["track"].append(point)
    for row in wells.get("completions") or []:
        if not isinstance(row, dict):
            continue
        name = str(row.get("well_name") or "")
        well = lookup.setdefault(name, _empty_dataset_well(name))
        payload = copy.deepcopy(row)
        payload["date_day"] = payload.get("date_day", payload.get("date"))
        payload.pop("date", None)
        event = str(payload.get("event") or "").upper()
        if event == "PERF":
            payload.pop("event", None)
            well["completion_definitions"].append(payload)
        else:
            well["events"].append(payload)
    for well in lookup.values():
        well["track"].sort(key=lambda row: _finite_float(row.get("md_m")) or 0.0)
        if well["track"]:
            md_values = [
                _finite_float(row.get("md_m")) for row in well["track"]
            ]
            md_values = [value for value in md_values if value is not None]
            if md_values:
                well["md_min_m"] = min(md_values)
                well["md_max_m"] = max(md_values)
    return {
        "schema_version": wells.get(
            "schema_version", "wells_v2_event_comp_id"),
        "summary": copy.deepcopy(wells.get("summary") or {}),
        "validation": {"error_count": 0, "warning_count": 0, "warnings": []},
        "wells": list(lookup.values()),
    }


def _empty_dataset_well(name):
    return {
        "well_name": name,
        "well_type": "",
        "track": [],
        "completion_definitions": [],
        "events": [],
        "md_min_m": None,
        "md_max_m": None,
    }


def _finite_float(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _mean(values, default):
    clean = [value for value in values if value is not None]
    return sum(clean) / len(clean) if clean else default


def _unique(items):
    return list(dict.fromkeys(str(item) for item in items if str(item).strip()))
