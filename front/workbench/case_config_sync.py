# -*- coding: utf-8 -*-
"""Synchronize CaseData/config values with workbench module parameters."""

import json
import os


def sync_project_modules_from_dataset(project_state, dataset_path):
    config = _read_dataset_config(dataset_path)
    if config:
        sync_project_modules_from_config(project_state, config)


def sync_project_modules_from_config(project_state, config):
    if project_state is None or not isinstance(config, dict):
        return

    module_values = {
        "grid_basic": _grid_values(config),
        "initial_state": _initial_values(config),
        "oil_water_properties": _fluid_values(config),
        "gas_pvt": _gas_values(config),
        "well_parameters": _well_values(config),
        "hydraulic_fractures": _hydraulic_values(config),
        "simulation_control": _solver_values(config),
    }
    for module_key, values in module_values.items():
        _merge_module_values(project_state, module_key, values)


def sync_project_modules_from_case_data(project_state):
    if project_state is None:
        return
    config = _config_from_case_sections(
        getattr(project_state, "case_data_sections", []) or [])
    sync_project_modules_from_config(project_state, config)


def apply_module_values_to_case_data(project_state, module_key, values):
    if project_state is None or not isinstance(values, dict):
        return False
    mappings = _case_mappings(module_key, values)
    if not mappings:
        return False

    sections = list(getattr(project_state, "case_data_sections", []) or [])
    changed = False
    for section_name, keyword_key, value in mappings:
        if value is None:
            continue
        changed = _set_case_keyword(sections, section_name, keyword_key, value) or changed

    if changed:
        project_state.case_data_sections = sections
        _refresh_case_data_summary(project_state)
    return changed


def _read_dataset_config(dataset_path):
    if not dataset_path:
        return {}
    path = os.path.join(os.path.abspath(dataset_path), "config.json")
    try:
        with open(path, "r", encoding="utf-8") as file:
            payload = json.load(file)
    except (OSError, ValueError):
        return {}
    return payload.get("config", payload) if isinstance(payload, dict) else {}


def _merge_module_values(project_state, module_key, values):
    clean_values = {
        key: value for key, value in (values or {}).items()
        if value not in ("", None)
    }
    if not clean_values:
        return
    current = project_state.get_module_values(module_key)
    current.update(clean_values)
    project_state.set_module_values(module_key, current)


def _grid_values(config):
    lgr = config.get("lgr", {}) or {}
    return {
        "enable_lgr": lgr.get("enable_lgr"),
        "d_threshold": lgr.get("d_threshold"),
        "lgr_nrx": lgr.get("nrx"),
        "lgr_nry": lgr.get("nry"),
        "lgr_nrz": lgr.get("nrz"),
    }


def _initial_values(config):
    initial = config.get("initial", {}) or {}
    return {
        "initial_pressure": initial.get("pressure"),
        "initial_sw": initial.get("sw"),
        "initial_sg": initial.get("sg"),
    }


def _fluid_values(config):
    fluid = config.get("fluid", {}) or {}
    return {
        "mu_w": fluid.get("mu_w"),
        "mu_o": fluid.get("mu_o"),
        "cw": fluid.get("cw"),
        "co": fluid.get("co"),
        "p_ref": fluid.get("p_ref"),
        "swi": fluid.get("swi"),
        "sor": fluid.get("sor"),
        "sgc": fluid.get("sgc"),
    }


def _gas_values(config):
    gas = config.get("gas", {}) or {}
    return {
        "gas_t_C": gas.get("temperature_c"),
        "gas_table_Pmin_bar": gas.get("gas_table_pmin_bar"),
        "gas_table_Pmax_bar": gas.get("gas_table_pmax_bar"),
        "gas_table_n": gas.get("gas_table_n"),
    }


def _well_values(config):
    well = config.get("well", {}) or {}
    return {
        "pressure": well.get("producer_bhp"),
        "radius": well.get("well_radius"),
    }


def _hydraulic_values(config):
    hydraulic = config.get("hydraulic_fractures", {}) or {}
    length = hydraulic.get("length")
    return {
        "num_stages": hydraulic.get("count"),
        "spacing_x": hydraulic.get("spacing_x"),
        "length": length,
        "height": hydraulic.get("height"),
        "aperture": hydraulic.get("aperture"),
        "perm": hydraulic.get("perm"),
    }


def _solver_values(config):
    solver = config.get("solver", {}) or {}
    return {
        "simulation_time": solver.get("total_time"),
        "time_step": solver.get("dt_init"),
    }


def _config_from_case_sections(sections):
    return {
        "lgr": {
            "enable_lgr": _case_value(sections, "LGR", "enable_lgr"),
            "d_threshold": _case_value(sections, "LGR", "d_threshold"),
            "nrx": _case_value(sections, "LGR", "nrx"),
            "nry": _case_value(sections, "LGR", "nry"),
            "nrz": _case_value(sections, "LGR", "nrz"),
        },
        "fluid": {
            "mu_w": _case_value(sections, "FLUID", "mu_w"),
            "mu_o": _case_value(sections, "FLUID", "mu_o"),
            "cw": _case_value(sections, "FLUID", "cw"),
            "co": _case_value(sections, "FLUID", "co"),
            "p_ref": _case_value(sections, "FLUID", "p_ref"),
            "swi": _case_value(sections, "FLUID", "Swi"),
            "sor": _case_value(sections, "FLUID", "Sor"),
            "sgc": _case_value(sections, "FLUID", "Sgc"),
        },
        "gas": {
            "temperature_c": _case_value(sections, "GAS", "temperature_C"),
            "gas_table_pmin_bar": _case_value(sections, "GAS", "gas_table_Pmin_bar"),
            "gas_table_pmax_bar": _case_value(sections, "GAS", "gas_table_Pmax_bar"),
            "gas_table_n": _case_value(sections, "GAS", "gas_table_n"),
        },
        "initial": {
            "pressure": _case_value(sections, "INITIAL", "pressure"),
            "sw": _case_value(sections, "INITIAL", "Sw"),
            "sg": _case_value(sections, "INITIAL", "Sg"),
        },
        "well": {
            "producer_bhp": _case_value(sections, "WELL", "producer_bhp"),
            "well_radius": _case_value(sections, "WELL", "well_radius"),
        },
        "hydraulic_fractures": {
            "count": _case_value(sections, "FRACTURE", "hydraulic_fracture_count"),
            "spacing_x": _case_value(sections, "FRACTURE", "hydraulic_fracture_spacing"),
            "length": _case_value(sections, "FRACTURE", "hydraulic_fracture_length"),
            "height": _case_value(sections, "FRACTURE", "hydraulic_fracture_height"),
            "aperture": _case_value(sections, "FRACTURE", "hydraulic_fracture_aperture"),
            "perm": _case_value(sections, "FRACTURE", "hydraulic_fracture_permeability"),
        },
        "solver": {
            "total_time": _case_value(sections, "SOLVER", "total_time"),
            "dt_init": _case_value(sections, "SOLVER", "dt_init"),
        },
    }


def _case_mappings(module_key, values):
    if module_key == "grid_basic":
        return [
            ("LGR", "enable_lgr", values.get("enable_lgr")),
            ("LGR", "d_threshold", values.get("d_threshold")),
            ("LGR", "nrx", values.get("lgr_nrx")),
            ("LGR", "nry", values.get("lgr_nry")),
            ("LGR", "nrz", values.get("lgr_nrz")),
        ]
    if module_key == "initial_state":
        return [
            ("INITIAL", "pressure", values.get("initial_pressure")),
            ("INITIAL", "Sw", values.get("initial_sw")),
            ("INITIAL", "Sg", values.get("initial_sg")),
        ]
    if module_key == "oil_water_properties":
        return [
            ("FLUID", "mu_w", values.get("mu_w")),
            ("FLUID", "mu_o", values.get("mu_o")),
            ("FLUID", "cw", values.get("cw")),
            ("FLUID", "co", values.get("co")),
            ("FLUID", "p_ref", values.get("p_ref")),
            ("FLUID", "Swi", values.get("swi")),
            ("FLUID", "Sor", values.get("sor")),
            ("FLUID", "Sgc", values.get("sgc")),
        ]
    if module_key == "gas_pvt":
        return [
            ("GAS", "temperature_C", values.get("gas_t_C")),
            ("GAS", "gas_table_Pmin_bar", values.get("gas_table_Pmin_bar")),
            ("GAS", "gas_table_Pmax_bar", values.get("gas_table_Pmax_bar")),
            ("GAS", "gas_table_n", values.get("gas_table_n")),
        ]
    if module_key == "well_parameters":
        return [
            ("WELL", "producer_bhp", values.get("pressure")),
            ("WELL", "well_radius", values.get("radius")),
        ]
    if module_key == "hydraulic_fractures":
        length = values.get("length")
        if length is None and values.get("half_len") is not None:
            length = float(values.get("half_len")) * 2.0
        return [
            ("FRACTURE", "hydraulic_fracture_count", values.get("num_stages")),
            ("FRACTURE", "hydraulic_fracture_spacing", values.get("spacing_x")),
            ("FRACTURE", "hydraulic_fracture_length", length),
            ("FRACTURE", "hydraulic_fracture_height", values.get("height")),
            ("FRACTURE", "hydraulic_fracture_aperture", values.get("aperture")),
            ("FRACTURE", "hydraulic_fracture_permeability", values.get("perm")),
        ]
    if module_key == "simulation_control":
        return [
            ("SOLVER", "total_time", values.get("simulation_time")),
            ("SOLVER", "dt_init", values.get("time_step")),
        ]
    return []


def _case_value(sections, section_name, keyword_key):
    keyword = _find_case_keyword(sections, section_name, keyword_key)
    if not keyword:
        return None
    if "value" in keyword:
        return keyword.get("value")
    return _parse_raw_value(keyword.get("raw_value", ""))


def _set_case_keyword(sections, section_name, keyword_key, value):
    section = _find_or_create_section(sections, section_name)
    keyword = _find_keyword_in_section(section, keyword_key)
    raw_value = _format_raw_value(value)
    parsed_value, value_type = _parse_value_and_type(raw_value)
    if keyword is None:
        section.setdefault("keywords", []).append({
            "key": keyword_key,
            "value": parsed_value,
            "raw_value": raw_value,
            "original_raw_value": "",
            "value_type": value_type,
            "comment": "",
            "line_number": 0,
            "is_file_ref": False,
            "file_path": "",
            "file_exists": False,
            "dirty": True,
        })
        return True
    if str(keyword.get("raw_value", "")) == raw_value:
        return False
    keyword["raw_value"] = raw_value
    keyword["value"] = parsed_value
    keyword["value_type"] = value_type
    keyword["dirty"] = raw_value != str(keyword.get("original_raw_value", ""))
    return True


def _find_case_keyword(sections, section_name, keyword_key):
    section = _find_section(sections, section_name)
    return _find_keyword_in_section(section, keyword_key) if section else None


def _find_section(sections, section_name):
    target = str(section_name or "").upper()
    for section in sections:
        if str(section.get("name", "")).upper() == target:
            return section
    return None


def _find_or_create_section(sections, section_name):
    section = _find_section(sections, section_name)
    if section is not None:
        return section
    section = {
        "name": section_name,
        "line_number": 0,
        "comment": "",
        "keywords": [],
        "loose_items": [],
    }
    sections.append(section)
    return section


def _find_keyword_in_section(section, keyword_key):
    if not section:
        return None
    target = str(keyword_key or "").lower()
    for keyword in section.get("keywords", []) or []:
        if str(keyword.get("key", "")).lower() == target:
            return keyword
    return None


def _format_raw_value(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return f"{value:.12g}"
    return str(value)


def _parse_raw_value(raw_value):
    return _parse_value_and_type(str(raw_value))[0]


def _parse_value_and_type(raw_value):
    text = str(raw_value).strip()
    lowered = text.lower()
    if lowered in {"true", "false"}:
        return lowered == "true", "bool"
    try:
        if text and all(char not in text for char in ".eE"):
            return int(text), "int"
    except ValueError:
        pass
    try:
        return float(text), "float"
    except ValueError:
        return text, "string"


def _refresh_case_data_summary(project_state):
    sections = getattr(project_state, "case_data_sections", []) or []
    file_refs = [
        keyword
        for section in sections
        for keyword in section.get("keywords", []) or []
        if keyword.get("is_file_ref")
    ]
    missing = [keyword for keyword in file_refs if not keyword.get("file_exists")]
    project_state.case_data_summary = {
        "section_count": len(sections),
        "keyword_count": sum(len(section.get("keywords", []) or []) for section in sections),
        "file_ref_count": len(file_refs),
        "missing_file_ref_count": len(missing),
        "error_count": (getattr(project_state, "case_data_summary", {}) or {}).get("error_count", 0),
    }
