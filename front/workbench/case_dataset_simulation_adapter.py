# -*- coding: utf-8 -*-
"""Build lightweight runner parameters from a standard case_dataset directory."""

import argparse
import json
import os
from dataclasses import dataclass, field

import numpy as np

from .case_dataset_reader import CaseDatasetReadError, load_case_dataset
from .project_state import (
    MODEL_TYPE_WR,
    WR_INPUT_MODE_CONSTANT,
    WR_INPUT_MODE_FILE,
    WR_INPUT_MODE_MIXED,
    normalize_model_config,
)


class CaseDatasetSimulationAdapterError(ValueError):
    """Raised when a case_dataset cannot be converted to runner parameters."""


@dataclass
class CaseDatasetSimulationInput:
    dataset_dir: str
    params: dict = field(default_factory=dict)
    summary: dict = field(default_factory=dict)
    validation: dict = field(default_factory=dict)

    def to_dict(self):
        return {
            "dataset_dir": self.dataset_dir,
            "params": dict(self.params),
            "summary": dict(self.summary),
            "validation": dict(self.validation),
        }


def build_case_dataset_simulation_input(dataset_dir, strict=True):
    """Load a case_dataset and return JSON-safe runner parameters.

    Large arrays stay in the dataset directory and are read by the runner
    subprocess. This keeps QProcess arguments small and avoids duplicating
    arrays.npz in memory.
    """
    dataset_dir = os.path.abspath(dataset_dir or "")
    if not dataset_dir:
        raise CaseDatasetSimulationAdapterError("case_dataset path is empty")
    try:
        dataset = load_case_dataset(dataset_dir, strict=strict)
    except CaseDatasetReadError as exc:
        raise CaseDatasetSimulationAdapterError(str(exc)) from exc

    summary = dataset.summary()
    validation = dict(dataset.validation or {})
    params = _build_runner_params(dataset, summary)
    return CaseDatasetSimulationInput(
        dataset_dir=dataset_dir,
        params=params,
        summary=summary,
        validation=validation,
    )


def build_case_dataset_params(dataset_dir, strict=True):
    """Return only the flat parameter dict used by front.simulation_runner."""
    return build_case_dataset_simulation_input(
        dataset_dir, strict=strict).params


def export_case_dataset_interface_json(dataset_dir, output_path, strict=True):
    """Export the lightweight case_dataset runner interface for inspection."""
    payload = build_case_dataset_simulation_input(
        dataset_dir, strict=strict).to_dict()
    output_path = os.path.abspath(output_path)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2, default=_json_default)
    return output_path


def _build_runner_params(dataset, summary):
    config = dataset.config or {}
    model_config = normalize_model_config(getattr(dataset, "model_config", None))
    model_params = _model_config_params(model_config)
    lgr = config.get("lgr", {}) or {}
    dual = config.get("dual_porosity", {}) or {}
    fluid = config.get("fluid", {}) or {}
    gas = config.get("gas", {}) or {}
    initial = config.get("initial", {}) or {}
    well = config.get("well", {}) or {}
    hydraulic = config.get("hydraulic_fractures", {}) or {}
    solver = config.get("solver", {}) or {}
    grid = dataset.grid
    hf_params = _hydraulic_fracture_params(dataset, hydraulic)
    hf_params["hf_enabled"] = bool(
        model_params["enable_hydraulic_fractures"] and hf_params.get("hf_enabled"))

    return {
        "algorithm": "corner_edfm",
        "interface_source": "case_dataset",
        "case_dataset_path": os.path.abspath(dataset.dataset_dir),
        "model_config": dict(model_config),
        "model_type": model_params["model_type"],
        "wr_input_mode": model_params["wr_input_mode"],
        "corner_grid_refinement": "加密" if bool(lgr.get("enable_lgr", False)) else "不加密",
        "grid_type": "corner_point",
        "nx": int(grid.nx),
        "ny": int(grid.ny),
        "nz": int(grid.nz),
        "active_cell_count": int(grid.active_cell_count),
        "inactive_cell_count": int(grid.inactive_cell_count),
        "array_count": int(summary.get("array_count", 0) or 0),
        "property_count": int(summary.get("property_count", 0) or 0),
        "dfn_fracture_count": int(summary.get("dfn_fracture_count", 0) or 0),
        "enable_lgr": bool(lgr.get("enable_lgr", False)),
        "corner_grid_refinement": "加密" if model_params["enable_lgr"] else "不加密",
        "enable_lgr": model_params["enable_lgr"],
        "enable_natural_fractures": model_params["enable_natural_fractures"],
        "enable_hydraulic_fractures": model_params["enable_hydraulic_fractures"],
        "enable_real_gas_pvt": model_params["enable_real_gas_pvt"],
        "enable_dual_porosity": model_params["enable_dual_porosity"],
        "corner_grid_refinement": "\u52a0\u5bc6" if model_params["enable_lgr"] else "\u4e0d\u52a0\u5bc6",
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
        **hf_params,
        **_dual_porosity_params(dual),
        "simulation_time": _float(solver, "total_time", 100.0),
        "time_step": _float(solver, "dt_init", 1.0),
        "dt_min": _float(solver, "dt_min", 1e-6),
        "dt_max": _float(solver, "dt_max", 30.0),
        "newton_max_iter": _int(solver, "newton_max_iter", 15),
        "newton_tol": _float(solver, "newton_tol", 1e-3),
        "linear_tol": _float(solver, "linear_tol", 1e-8),
        "linear_max_iter": _int(solver, "linear_max_iter", 1000),
        "null_value": float(dataset.manifest.get("null_value", 99999.0)),
        "valid_cell_rule": dataset.manifest.get(
            "valid_cell_rule", "grid_actnum == 1 and value != 99999"),
    }


def _model_config_params(model_config):
    config = normalize_model_config(model_config)
    is_wr = config.get("model_type") == MODEL_TYPE_WR
    wr_input_mode = config.get("wr_input_mode", WR_INPUT_MODE_FILE)
    if wr_input_mode not in {
        WR_INPUT_MODE_FILE,
        WR_INPUT_MODE_CONSTANT,
        WR_INPUT_MODE_MIXED,
    }:
        wr_input_mode = WR_INPUT_MODE_FILE
    return {
        "model_type": config.get("model_type"),
        "wr_input_mode": wr_input_mode,
        "enable_lgr": bool(config.get("enable_lgr", True)),
        "enable_natural_fractures": bool(config.get("enable_natural_fractures", True)),
        "enable_hydraulic_fractures": bool(config.get("enable_hydraulic_fractures", False)),
        "enable_real_gas_pvt": bool(config.get("enable_real_gas_pvt", True)),
        "enable_dual_porosity": bool(is_wr),
    }


def _dual_porosity_params(dual):
    return {
        "phi_matrix": _float(dual, "phi_matrix", 0.04),
        "phi_fracture": _float(dual, "phi_fracture", 0.4),
        "k_matrix_x": _float(dual, "k_matrix_x", 0.005),
        "k_matrix_y": _float(dual, "k_matrix_y", 0.005),
        "k_matrix_z": _float(dual, "k_matrix_z", 0.005),
        "k_fracture_x": _float(dual, "k_fracture_x", 1.0),
        "k_fracture_y": _float(dual, "k_fracture_y", 1.0),
        "k_fracture_z": _float(dual, "k_fracture_z", 0.1),
        "matrix_volume_fraction": _float(dual, "matrix_volume_fraction", 0.98),
        "fracture_volume_fraction": _float(dual, "fracture_volume_fraction", 0.02),
        "wr_shape_factor": _float(dual, "wr_shape_factor", 0.12),
    }


def _hydraulic_fracture_params(dataset, hydraulic):
    if not hydraulic:
        # Temporary fallback for older case_dataset inputs: wells are attached
        # to hydraulic fracture segments, while early case_dataset files had no
        # hydraulic fracture block.
        return _temporary_hf_defaults(dataset)

    hf_count = _int(hydraulic, "count", 0)
    return {
        "hf_enabled": hf_count > 0,
        "hf_count": hf_count,
        "hf_spacing_x": _float(hydraulic, "spacing_x", 0.0),
        "hf_length": _float(hydraulic, "length", 120.0),
        "hf_height": _float(hydraulic, "height", 30.0),
        "hf_aperture": _float(hydraulic, "aperture", 0.1),
        "hf_perm": _float(hydraulic, "perm", 1000.0),
        "hf_center_x": _float(hydraulic, "center_x", -1.0),
        "hf_center_y": _float(hydraulic, "center_y", -1.0),
        "hf_center_z": _float(hydraulic, "center_z", -1.0),
    }


def _temporary_hf_defaults(dataset):
    center = _first_dfn_center(dataset.dfn)
    return {
        "hf_enabled": True,
        "hf_count": 1,
        "hf_spacing_x": 0.0,
        "hf_length": 10.0,
        "hf_height": 10.0,
        "hf_aperture": 0.1,
        "hf_perm": 1000.0,
        "hf_center_x": center[0],
        "hf_center_y": center[1],
        "hf_center_z": center[2],
    }


def _first_dfn_center(dfn_payload):
    fractures = (dfn_payload or {}).get("fractures") or []
    for fracture in fractures:
        points = fracture.get("vertices") or fracture.get("points") or []
        if not points:
            continue
        try:
            arr = np.asarray(points, dtype=np.float64)
        except (TypeError, ValueError):
            continue
        if arr.ndim == 2 and arr.shape[0] > 0 and arr.shape[1] >= 3:
            center = np.mean(arr[:, :3], axis=0)
            return (float(center[0]), float(center[1]), float(center[2]))
    return (-1.0, -1.0, -1.0)

def _float(values, key, default):
    try:
        return float(values.get(key, default))
    except (TypeError, ValueError) as exc:
        raise CaseDatasetSimulationAdapterError(f"{key} must be numeric") from exc


def _int(values, key, default):
    try:
        return int(values.get(key, default))
    except (TypeError, ValueError) as exc:
        raise CaseDatasetSimulationAdapterError(f"{key} must be an integer") from exc


def _json_default(value):
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    raise TypeError(f"{type(value).__name__} is not JSON serializable")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Build runner parameters from a case_dataset directory")
    parser.add_argument("dataset_dir", help="case_dataset directory")
    parser.add_argument(
        "--allow-invalid",
        action="store_true",
        help="load the dataset even when validation.json contains errors",
    )
    parser.add_argument(
        "--output",
        default="",
        help="optional JSON file to write the full interface payload",
    )
    args = parser.parse_args(argv)

    payload = build_case_dataset_simulation_input(
        args.dataset_dir, strict=not args.allow_invalid).to_dict()
    if args.output:
        output_path = os.path.abspath(args.output)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, indent=2, default=_json_default)
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default))


if __name__ == "__main__":
    main()
