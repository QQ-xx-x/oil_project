# -*- coding: utf-8 -*-
"""将 CaseData 输入文件转换为 pybind C++ 求解器参数。

这个模块是 UI 侧 CaseData 模型和 ``front.simulation_runner`` 之间的接口边界。
UI 控件不直接调用 C++ 模块，而是在这里生成参数字典，再交给现有运行层处理。
"""

import json
import os
from dataclasses import dataclass, field

from front.uniform_parser import parse_config, parse_grid, parse_property

from .case_data_parser import parse_case_data


class CaseDataSimulationAdapterError(ValueError):
    """CaseData 无法转换为求解器参数时抛出。"""


@dataclass
class CaseDataSimulationInput:
    case_data_path: str
    params: dict = field(default_factory=dict)
    config: dict = field(default_factory=dict)
    files: dict = field(default_factory=dict)
    grid_summary: dict = field(default_factory=dict)
    property_summary: dict = field(default_factory=dict)
    validation: dict = field(default_factory=dict)

    def to_dict(self):
        return {
            "case_data_path": self.case_data_path,
            "params": dict(self.params),
            "config": dict(self.config),
            "files": dict(self.files),
            "grid_summary": dict(self.grid_summary),
            "property_summary": dict(self.property_summary),
            "validation": dict(self.validation),
        }


FILE_KEYS = {
    "grid_file",
    "matrix_phi_file",
    "matrix_kx_file",
    "matrix_ky_file",
    "matrix_kz_file",
    "fracture_phi_file",
    "fracture_kx_file",
    "fracture_ky_file",
    "fracture_kz_file",
    "fracture_file",
    "sigma_file",
}

PROPERTY_FILE_KEYS = {
    "matrix_phi_file",
    "matrix_kx_file",
    "matrix_ky_file",
    "matrix_kz_file",
    "fracture_phi_file",
    "fracture_kx_file",
    "fracture_ky_file",
    "fracture_kz_file",
    "sigma_file",
}


def build_case_data_simulation_input(case_data_path, validate_arrays=True):
    """从 CaseData 输入文件构建结构化的求解器接口对象。"""
    case_data_path = os.path.abspath(case_data_path or "")
    if not case_data_path:
        raise CaseDataSimulationAdapterError("CaseData 路径为空")
    if not os.path.exists(case_data_path):
        raise CaseDataSimulationAdapterError(f"CaseData 文件不存在: {case_data_path}")

    case_data = parse_case_data(case_data_path)
    config = parse_config(case_data_path)
    files = _collect_file_paths(case_data)
    validation = {"ok": True, "errors": [], "warnings": []}

    _validate_required_files(files, validation)
    grid_summary = _build_grid_summary(files.get("grid_file"), validation)
    property_summary = {}
    if validate_arrays:
        property_summary = _build_property_summary(
            files, grid_summary.get("total_cell_count"), validation)

    params = _build_runner_params(case_data_path, config, files, grid_summary)
    if files.get("grid_file") and not files.get("coord_file") and not files.get("zcorn_file"):
        validation["warnings"].append(
            "当前 CaseData 提供 grid_file，现有 simulation_runner 仍使用 coord_file/zcorn_file；"
            "需要后续让 runner 或 C++ pybind 接收 grid.inc。"
        )
    return CaseDataSimulationInput(
        case_data_path=case_data_path,
        params=params,
        config=config,
        files=files,
        grid_summary=grid_summary,
        property_summary=property_summary,
        validation=validation,
    )


def build_case_data_params(case_data_path, validate_arrays=True):
    """只返回 ``front.simulation_runner`` 使用的扁平参数字典。"""
    return build_case_data_simulation_input(
        case_data_path, validate_arrays=validate_arrays).params


def export_case_data_interface_json(case_data_path, output_path, validate_arrays=True):
    """将接口内容导出为 JSON，方便算法侧检查字段和取值。"""
    payload = build_case_data_simulation_input(
        case_data_path, validate_arrays=validate_arrays).to_dict()
    output_path = os.path.abspath(output_path)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)
    return output_path


def _collect_file_paths(case_data):
    files = {}
    for section in case_data.sections:
        for keyword in section.keywords:
            key = keyword.key
            if key in FILE_KEYS or keyword.is_file_ref:
                files[key] = os.path.abspath(keyword.file_path or "")
    return files


def _validate_required_files(files, validation):
    required = [
        "grid_file",
        "matrix_phi_file",
        "matrix_kx_file",
        "matrix_ky_file",
        "matrix_kz_file",
    ]
    for key in required:
        path = files.get(key, "")
        if not path:
            _add_error(validation, f"缺少必需文件关键字: {key}")
        elif not os.path.exists(path):
            _add_error(validation, f"{key} 文件不存在: {path}")
    for key, path in files.items():
        if path and not os.path.exists(path):
            _add_error(validation, f"{key} 文件不存在: {path}")


def _build_grid_summary(grid_file, validation):
    if not grid_file or not os.path.exists(grid_file):
        return {}
    try:
        grid = parse_grid(grid_file)
    except Exception as exc:
        _add_error(validation, f"grid_file 解析失败: {exc}")
        return {}
    return {
        "nx": grid.get("nx"),
        "ny": grid.get("ny"),
        "nz": grid.get("nz"),
        "total_cell_count": grid.get("total_cell_count"),
        "coord_value_count": len(grid.get("coord") or []),
        "zcorn_value_count": len(grid.get("zcorn") or []),
        "actnum_value_count": len(grid.get("actnum") or []),
        "active_cell_count": grid.get("active_cell_count"),
        "inactive_cell_count": grid.get("inactive_cell_count"),
    }


def _build_property_summary(files, expected_count, validation):
    summary = {}
    for key in sorted(PROPERTY_FILE_KEYS):
        path = files.get(key)
        if not path or not os.path.exists(path):
            continue
        try:
            values = parse_property(path)
        except Exception as exc:
            _add_error(validation, f"{key} 解析失败: {exc}")
            continue
        null_count = sum(1 for value in values if float(value) == 99999.0)
        item = {
            "path": path,
            "value_count": len(values),
            "null_value_count": null_count,
        }
        if expected_count is not None and len(values) != expected_count:
            item["length_match_grid"] = False
            _add_error(
                validation,
                f"{key} 数量 {len(values)} 与网格总数 {expected_count} 不一致",
            )
        else:
            item["length_match_grid"] = True
        summary[key] = item
    return summary


def _build_runner_params(case_data_path, config, files, grid_summary):
    lgr = config.get("lgr", {}) or {}
    fluid = config.get("fluid", {}) or {}
    gas = config.get("gas", {}) or {}
    initial = config.get("initial", {}) or {}
    well = config.get("well", {}) or {}
    solver = config.get("solver", {}) or {}

    # 这些字段名与 front.simulation_runner.py 保持一致。部分文件字段当前的
    # pybind 绑定还没有使用，但先放进接口，方便算法侧后续接入。
    params = {
        "algorithm": "corner_edfm",
        "interface_source": "case_data",
        "case_data_path": os.path.abspath(case_data_path),
        "corner_grid_refinement": "加密" if bool(lgr.get("enable_lgr", False)) else "不加密",
        "grid_type": "corner_point",
        "grid_file": files.get("grid_file", ""),
        "coord_file": files.get("coord_file", ""),
        "zcorn_file": files.get("zcorn_file", ""),
        "matrix_phi_file": files.get("matrix_phi_file", ""),
        "matrix_kx_file": files.get("matrix_kx_file", ""),
        "matrix_ky_file": files.get("matrix_ky_file", ""),
        "matrix_kz_file": files.get("matrix_kz_file", ""),
        "fracture_phi_file": files.get("fracture_phi_file", ""),
        "fracture_kx_file": files.get("fracture_kx_file", ""),
        "fracture_ky_file": files.get("fracture_ky_file", ""),
        "fracture_kz_file": files.get("fracture_kz_file", ""),
        "fracture_file": files.get("fracture_file", ""),
        "sigma_file": files.get("sigma_file", ""),
        "nx": _int(grid_summary, "nx", 0),
        "ny": _int(grid_summary, "ny", 0),
        "nz": _int(grid_summary, "nz", 0),
        "active_cell_count": _int(grid_summary, "active_cell_count", 0),
        "inactive_cell_count": _int(grid_summary, "inactive_cell_count", 0),
        "enable_lgr": bool(lgr.get("enable_lgr", False)),
        "d_threshold": _float(lgr, "d_threshold", 5.05),
        "lgr_nrx": _int(lgr, "nrx", 2),
        "lgr_nry": _int(lgr, "nry", 2),
        "lgr_nrz": _int(lgr, "nrz", 2),
        "mu_w": _float(fluid, "mu_w", 1.0),
        "mu_o": _float(fluid, "mu_o", 5.0),
        "cw": _float(fluid, "cw", 1e-8),
        "co": _float(fluid, "co", 1e-5),
        "p_ref": _float(fluid, "p_ref", 100.0),
        "swi": _float(fluid, "swi", 0.05),
        "sor": _float(fluid, "sor", 0.01),
        "sgc": _float(fluid, "sgc", 0.05),
        "gas_t_C": _float(gas, "temperature_c", 140.0),
        "gas_table_Pmin_bar": _float(gas, "gas_table_pmin_bar", 1.0),
        "gas_table_Pmax_bar": _float(gas, "gas_table_pmax_bar", 1000.0),
        "gas_table_n": _int(gas, "gas_table_n", 2000),
        "pressure": _float(initial, "pressure", 800.0),
        "sw": _float(initial, "sw", 0.05),
        "sg": _float(initial, "sg", 0.9),
        "so": _float(initial, "so", 0.05),
        "well_pressure": _float(well, "producer_bhp", 100.0),
        "well_radius": _float(well, "well_radius", 0.05),
        "simulation_time": _float(solver, "total_time", 100.0),
        "time_step": _float(solver, "dt_init", 1.0),
        "dt_min": _float(solver, "dt_min", 1e-6),
        "dt_max": _float(solver, "dt_max", 30.0),
        "newton_max_iter": _int(solver, "newton_max_iter", 15),
        "newton_tol": _float(solver, "newton_tol", 1e-3),
        "linear_tol": _float(solver, "linear_tol", 1e-8),
        "linear_max_iter": _int(solver, "linear_max_iter", 1000),
        "null_value": 99999.0,
        "valid_cell_rule": "ACTNUM == 1 and value != 99999",
    }
    return params


def _add_error(validation, message):
    validation["errors"].append(message)
    validation["ok"] = False


def _float(values, key, default):
    try:
        return float(values.get(key, default))
    except (TypeError, ValueError) as exc:
        raise CaseDataSimulationAdapterError(f"{key} 必须是数字") from exc


def _int(values, key, default):
    try:
        return int(values.get(key, default))
    except (TypeError, ValueError) as exc:
        raise CaseDataSimulationAdapterError(f"{key} 必须是整数") from exc
