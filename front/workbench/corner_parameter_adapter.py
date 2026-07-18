# -*- coding: utf-8 -*-
"""将工作台工程状态转换为角点网格求解器参数。"""

import math
import os

from ..grdecl_parser import convert_grdecl_to_temp_csv


class CornerParameterError(ValueError):
    """工作台状态无法供角点网格求解器运行时抛出。"""


def build_corner_grid_params(project_state):
    """使用已导入的角点网格文件为 `front.simulation_runner` 构建参数。"""
    modules = getattr(project_state, "module_values", {}) or {}

    grid = _module(modules, "grid_basic")
    initial = _module(modules, "initial_state")
    matrix = _module(modules, "matrix_properties")
    dual = _module(modules, "dual_porosity")
    oil_water = _module(modules, "oil_water_properties")
    gas_pvt = _module(modules, "gas_pvt")
    well = _module(modules, "well_parameters")
    natural = _module(modules, "natural_fractures")
    hydraulic = _module(modules, "hydraulic_fractures")
    simulation = _module(modules, "simulation_control")

    coord_file, zcorn_file = _resolve_grid_files(grid)
    _validate_files(coord_file, zcorn_file)
    _validate_saturations(initial, oil_water)
    _validate_gas_pvt(gas_pvt)

    hf_length = _float(
        hydraulic,
        "length",
        _float(hydraulic, "half_len", 60.0) * 2.0,
    )
    well_x = _float(well, "x", 500.0)
    well_y = _float(well, "y", 250.0)
    well_z = _float(well, "z", 50.0)

    params = {
        "algorithm": "corner_edfm",
        "corner_grid_refinement": "加密",
        "grid_type": "corner_point",
        "coord_file": coord_file,
        "zcorn_file": zcorn_file,
        "nx": _int(grid, "nx", 20),
        "ny": _int(grid, "ny", 10),
        "nz": _int(grid, "nz", 5),
        "lx": _float(grid, "lx", 1000.0),
        "ly": _float(grid, "ly", 500.0),
        "lz": _float(grid, "lz", 100.0),
        "enable_lgr": bool(grid.get("enable_lgr", True)),
        "d_threshold": _float(grid, "d_threshold", 5.05),
        "lgr_nrx": _int(grid, "lgr_nrx", 2),
        "lgr_nry": _int(grid, "lgr_nry", 2),
        "lgr_nrz": _int(grid, "lgr_nrz", 2),
        "pressure": _float(initial, "initial_pressure", 800.0),
        "sw": _float(initial, "initial_sw", 0.05),
        "sg": _float(initial, "initial_sg", 0.9),
        "phi_matrix": _float(matrix, "porosity", 0.04),
        "porosity": _float(matrix, "porosity", 0.04),
        "k_matrix_x": _float(matrix, "perm_x", 0.005),
        "k_matrix_y": _float(matrix, "perm_y", 0.005),
        "k_matrix_z": _float(matrix, "perm_z", 0.005),
        "perm_x": _float(matrix, "perm_x", 0.005),
        "perm_y": _float(matrix, "perm_y", 0.005),
        "perm_z": _float(matrix, "perm_z", 0.005),
        "enable_dual_porosity": bool(dual.get("enable_dual_porosity", False)),
        "phi_fracture": _float(dual, "phi_fracture", 0.4),
        "k_fracture_x": _float(dual, "k_fracture_x", 1.0),
        "k_fracture_y": _float(dual, "k_fracture_y", 1.0),
        "k_fracture_z": _float(dual, "k_fracture_z", 0.1),
        "matrix_volume_fraction": _float(dual, "matrix_volume_fraction", 0.98),
        "fracture_volume_fraction": _float(dual, "fracture_volume_fraction", 0.02),
        "wr_shape_factor": _float(dual, "wr_shape_factor", 0.12),
        "mu_w": _float(oil_water, "mu_w", 1.0),
        "mu_o": _float(oil_water, "mu_o", 5.0),
        "mu_g": _float(oil_water, "mu_g", 0.2),
        "cw": _float(oil_water, "cw", 1e-8),
        "co": _float(oil_water, "co", 1e-5),
        "cg": _float(oil_water, "cg", 1e-3),
        "p_ref": _float(oil_water, "p_ref", 100.0),
        "swi": _float(oil_water, "swi", 0.05),
        "sor": _float(oil_water, "sor", 0.01),
        "sgc": _float(oil_water, "sgc", 0.05),
        "gas_t_C": _float(gas_pvt, "gas_t_C", 140.0),
        "gas_Mg": _float(gas_pvt, "gas_Mg", 16.04),
        "gas_Tc": _float(gas_pvt, "gas_Tc", 190.58),
        "gas_Pc_bar": _float(gas_pvt, "gas_Pc_bar", 45.44),
        "gas_table_Pmin_bar": _float(gas_pvt, "gas_table_Pmin_bar", 1.0),
        "gas_table_Pmax_bar": _float(gas_pvt, "gas_table_Pmax_bar", 1000.0),
        "gas_table_n": _int(gas_pvt, "gas_table_n", 2000),
        "well_x": well_x,
        "well_y": well_y,
        "well_z": well_z,
        "well_radius": _float(well, "radius", 0.05),
        "well_pressure": _float(well, "pressure", 50.0),
        "num_fracs": _int(natural, "num_fracs", 100),
        "min_len": _float(natural, "min_len", 10.0),
        "max_len": _float(natural, "max_len", 20.0),
        "max_dip": math.pi / 3.0,
        "min_strike": 0.0,
        "max_strike": math.pi,
        "aperture": _float(natural, "aperture", 0.1),
        "frac_perm": _float(natural, "perm", 100.0),
        "hf_enabled": bool(hydraulic.get("num_stages", 20) > 0),
        "hf_count": _int(hydraulic, "num_stages", 20),
        "hf_spacing_x": _float(hydraulic, "spacing_x", 31.58),
        "hf_length": hf_length,
        "hf_height": _float(hydraulic, "height", 30.0),
        "hf_aperture": _float(hydraulic, "aperture", 0.1),
        "hf_perm": _float(hydraulic, "perm", 1000.0),
        "hf_center_x": -1.0,
        "hf_center_y": -1.0,
        "hf_center_z": -1.0,
        "simulation_time": _float(simulation, "simulation_time", 100.0),
        "time_step": _float(simulation, "time_step", 1.0),
        "region_num_fracs": 0,
        "region_x_min": 0.0,
        "region_x_max": 0.0,
        "region_y_min": 0.0,
        "region_y_max": 0.0,
        "region_z_min": 0.0,
        "region_z_max": 0.0,
    }
    return params


def _module(modules, key):
    return dict(modules.get(key, {}) or {})


def _resolve_grid_files(grid):
    coord_file = str(grid.get("coord_file", "") or "").strip()
    zcorn_file = str(grid.get("zcorn_file", "") or "").strip()
    grdecl_file = str(grid.get("grdecl_file", "") or "").strip()

    if (not coord_file or not zcorn_file) and grdecl_file:
        if not os.path.exists(grdecl_file):
            raise CornerParameterError(f"GRDECL 文件不存在: {grdecl_file}")
        coord_file, zcorn_file = convert_grdecl_to_temp_csv(grdecl_file)

    if not coord_file or not zcorn_file:
        raise CornerParameterError("Corner Grid 运行必须先导入 GRDECL，或选择 COORD/ZCORN CSV 文件。")
    return coord_file, zcorn_file


def _validate_files(coord_file, zcorn_file):
    if not os.path.exists(coord_file):
        raise CornerParameterError(f"COORD 文件不存在: {coord_file}")
    if not os.path.exists(zcorn_file):
        raise CornerParameterError(f"ZCORN 文件不存在: {zcorn_file}")


def _validate_saturations(initial, oil_water):
    sw = _float(initial, "initial_sw", 0.05)
    sg = _float(initial, "initial_sg", 0.9)
    if sw + sg > 1.0 + 1e-8:
        raise CornerParameterError("初始饱和度必须满足 Sw + Sg <= 1.0。")

    swi = _float(oil_water, "swi", 0.05)
    sor = _float(oil_water, "sor", 0.01)
    sgc = _float(oil_water, "sgc", 0.05)
    if swi + sor >= 1.0:
        raise CornerParameterError("油水参数必须满足 Swi + Sor < 1.0。")
    if sgc + swi + sor >= 1.0:
        raise CornerParameterError("油水参数必须满足 Sgc + Swi + Sor < 1.0。")


def _validate_gas_pvt(gas_pvt):
    pmin = _float(gas_pvt, "gas_table_Pmin_bar", 1.0)
    pmax = _float(gas_pvt, "gas_table_Pmax_bar", 1000.0)
    if pmin <= 0.0 or pmax <= pmin:
        raise CornerParameterError("Gas PVT 表压力范围必须满足 0 < Pmin < Pmax。")
    if _int(gas_pvt, "gas_table_n", 2000) < 2:
        raise CornerParameterError("Gas PVT 表采样点数必须至少为 2。")
    if _float(gas_pvt, "gas_t_C", 140.0) + 273.15 <= 0.0:
        raise CornerParameterError("气体温度换算到 K 后必须大于 0。")


def _float(values, key, default):
    try:
        return float(values.get(key, default))
    except (TypeError, ValueError) as exc:
        raise CornerParameterError(f"{key} 必须是数字。") from exc


def _int(values, key, default):
    try:
        return int(values.get(key, default))
    except (TypeError, ValueError) as exc:
        raise CornerParameterError(f"{key} 必须是整数。") from exc
