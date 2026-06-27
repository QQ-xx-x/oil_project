"""
子进程模拟运行器。
负责执行模拟、保留算法 stdout 输出，并将结果写入 JSON 供 UI 进程读取。
"""
import argparse
import csv
import importlib
import json
import math
import os
import sys

import numpy as np

from .data_models import CornerPointCell, CornerPointGridData, SimulationData
from .workbench.case_dataset_reader import load_case_dataset


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULE_SEARCH_DIRS = [
    os.path.join(PROJECT_ROOT, 'build', 'Release'),
    os.path.join(PROJECT_ROOT, 'build'),
    os.path.join(PROJECT_ROOT, 'build_nmake'),
    os.path.join(PROJECT_ROOT, 'build_nmake', 'Release'),
    os.path.join(PROJECT_ROOT, 'build_nmake', 'Debug'),
    os.path.join(PROJECT_ROOT, 'build_vs2022'),
    os.path.join(PROJECT_ROOT, 'build_vs2022', 'Release'),
    os.path.join(PROJECT_ROOT, 'build_vs2022', 'Debug'),
]
for module_dir in MODULE_SEARCH_DIRS:
    if os.path.isdir(module_dir) and module_dir not in sys.path:
        sys.path.append(module_dir)

_BLACK_OIL_MODULE = None
_BLACK_OIL_IMPORT_ERROR = None
_CORNER_EDFM_MODULE = None
_CORNER_EDFM_IMPORT_ERROR = None
_CORNER_EDFM_LGR_MODULE = None
_CORNER_EDFM_LGR_IMPORT_ERROR = None

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True, write_through=True)
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(line_buffering=True, write_through=True)


def run_simulation(params):
    """执行模拟并返回 SimulationData。"""
    if params.get('interface_source') == 'case_dataset':
        return run_case_dataset_simulation(params)
    if params.get('interface_source') == 'case_data':
        return run_case_data_simulation(params)
    algorithm = params.get('algorithm', 'black_oil')
    if algorithm == 'corner_edfm':
        return run_corner_edfm_simulation(params)
    return run_black_oil_simulation(params)


def load_black_oil_module():
    """按需加载 Black Oil C++ 模块，避免与其他 pybind 模块类型注册冲突。"""
    global _BLACK_OIL_MODULE, _BLACK_OIL_IMPORT_ERROR
    if _BLACK_OIL_MODULE is not None:
        return _BLACK_OIL_MODULE
    if _BLACK_OIL_IMPORT_ERROR is not None:
        raise RuntimeError(f"edfm_core module is not available: {_BLACK_OIL_IMPORT_ERROR}")

    try:
        _BLACK_OIL_MODULE = importlib.import_module('edfm_core')
        return _BLACK_OIL_MODULE
    except Exception as exc:
        _BLACK_OIL_IMPORT_ERROR = exc
        raise RuntimeError(f"edfm_core module is not available: {exc}") from exc


def load_corner_edfm_module():
    """按需加载 Corner EDFM C++ 模块，避免与 edfm_core 同时注册同名 pybind 类型。"""
    global _CORNER_EDFM_MODULE, _CORNER_EDFM_IMPORT_ERROR
    if _CORNER_EDFM_MODULE is not None:
        return _CORNER_EDFM_MODULE
    if _CORNER_EDFM_IMPORT_ERROR is not None:
        raise RuntimeError(f"edfm_core_corner module is not available: {_CORNER_EDFM_IMPORT_ERROR}")

    try:
        _CORNER_EDFM_MODULE = importlib.import_module('edfm_core_corner')
        return _CORNER_EDFM_MODULE
    except Exception as exc:
        _CORNER_EDFM_IMPORT_ERROR = exc
        raise RuntimeError(f"edfm_core_corner module is not available: {exc}") from exc


def load_corner_edfm_lgr_module():
    """按需加载 Corner EDFM LGR C++ 模块。"""
    global _CORNER_EDFM_LGR_MODULE, _CORNER_EDFM_LGR_IMPORT_ERROR
    if _CORNER_EDFM_LGR_MODULE is not None:
        return _CORNER_EDFM_LGR_MODULE
    if _CORNER_EDFM_LGR_IMPORT_ERROR is not None:
        raise RuntimeError(f"edfm_core_corner_lgr module is not available: {_CORNER_EDFM_LGR_IMPORT_ERROR}")

    try:
        _CORNER_EDFM_LGR_MODULE = importlib.import_module('edfm_core_corner_lgr')
        return _CORNER_EDFM_LGR_MODULE
    except Exception as exc:
        _CORNER_EDFM_LGR_IMPORT_ERROR = exc
        raise RuntimeError(f"edfm_core_corner_lgr module is not available: {exc}") from exc


def run_black_oil_simulation(params):
    """执行 Black Oil 模拟并返回 SimulationData。"""
    sim_data = SimulationData()

    nx = int(params['nx'])
    ny = int(params['ny'])
    nz = int(params['nz'])
    lx = float(params['lx'])
    ly = float(params['ly'])
    lz = float(params['lz'])
    num_fracs = int(params['num_fracs'])
    min_len = float(params['min_len'])
    max_len = float(params['max_len'])
    aperture = float(params['aperture'])
    well_x = float(params['well_x'])
    well_y = float(params['well_y'])
    well_z = float(params['well_z'])
    well_pressure = float(params['well_pressure'])
    region_num_fracs = int(params.get('region_num_fracs', 0))
    region_x_min = float(params.get('region_x_min', 0.0))
    region_x_max = float(params.get('region_x_max', 0.0))
    region_y_min = float(params.get('region_y_min', 0.0))
    region_y_max = float(params.get('region_y_max', 0.0))
    region_z_min = float(params.get('region_z_min', 0.0))
    region_z_max = float(params.get('region_z_max', 0.0))

    try:
        edfm_core = load_black_oil_module()
    except RuntimeError as exc:
        print(f"{exc}, using mock data")
        edfm_core = None

    if edfm_core is not None:
        sim = edfm_core.EDFMSimulator()
        sim.setGridParameters(nx, ny, nz, lx, ly, lz)
        sim.setFractureParameters(num_fracs, min_len, max_len, math.pi / 3.0, 0.0, math.pi, aperture, 10000.0)
        sim.setSimulationParameters(100.0, 1.0, 0.2, 0.001, 0.001, 0.0001)
        sim.setWellParameters(well_x, well_y, well_z, 0.05, well_pressure)
        if region_num_fracs > 0:
            if hasattr(sim, 'setRegionFractureParameters'):
                sim.setRegionFractureParameters(
                    region_num_fracs,
                    region_x_min, region_x_max,
                    region_y_min, region_y_max,
                    region_z_min, region_z_max,
                )
            else:
                print("WARNING: edfm_core missing setRegionFractureParameters(); region fractures disabled")
        result = sim.runSimulation()
        grid_lines = []
        interpolated_pressure = []
        if hasattr(sim, 'getGridLines'):
            grid_lines = sim.getGridLines()
        else:
            print("WARNING: edfm_core missing getGridLines(); using coarse grid visualization")
        if hasattr(sim, 'getInterpolatedPressureField'):
            interpolated_pressure = sim.getInterpolatedPressureField(50, 25, 10)
        else:
            print("WARNING: edfm_core missing getInterpolatedPressureField(); using Python fallback interpolation")
        sim_data.generate_from_cpp(
            result,
            nx,
            ny,
            nz,
            lx,
            ly,
            lz,
            grid_lines,
            interpolated_pressure,
        )
        if not sim_data.interpolated_pressure:
            sim_data.interpolated_pressure = build_interpolated_pressure_from_leaf_data(sim_data)
    else:
        sim_data.generate_mock_data(
            nx, ny, nz, lx, ly, lz,
            num_fracs, min_len, max_len,
            well_x, well_y, well_z, well_pressure
        )

    return sim_data


def load_corner_grid_info(coord_file, zcorn_file):
    """从 COORD/ZCORN CSV 中静默提取网格维度和范围。"""
    coord_points = []
    with open(coord_file, 'r', encoding='utf-8') as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            keys = list(row.keys())
            coord_points.append((
                float(row[keys[3]]),
                float(row[keys[4]]),
                float(row[keys[5]]),
            ))

    zcorn_dims = []
    with open(zcorn_file, 'r', encoding='utf-8') as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            keys = list(row.keys())
            zcorn_dims.append((
                int(row[keys[0]]),
                int(row[keys[1]]),
                int(row[keys[2]]),
            ))

    if zcorn_dims:
        nx = max(item[0] for item in zcorn_dims)
        ny = max(item[1] for item in zcorn_dims)
        nz = max(item[2] for item in zcorn_dims)
    else:
        nx = ny = nz = 0

    if coord_points:
        xs = [point[0] for point in coord_points]
        ys = [point[1] for point in coord_points]
        zs = [point[2] for point in coord_points]
        lx = max(xs) - min(xs)
        ly = max(ys) - min(ys)
        lz = max(zs) - min(zs)
    else:
        lx = ly = lz = 0.0

    return nx, ny, nz, lx, ly, lz


def apply_corner_fluid_properties(sim, params):
    """If supported by the loaded module, forward oil/water rock-fluid settings."""
    has_legacy_api = hasattr(sim, 'setOilWaterProperties')
    has_gw_api = hasattr(sim, 'setGasWaterProperties')
    if not has_legacy_api and not has_gw_api:
        return

    mu_w = float(params.get('mu_w', 1.0))
    mu_o = float(params.get('mu_o', 5.0))
    cw = float(params.get('cw', 1e-8))
    co = float(params.get('co', 1e-5))
    p_ref = float(params.get('p_ref', 100.0))
    swi = float(params.get('swi', 0.05))
    sor = float(params.get('sor', 0.01))
    sgc = float(params.get('sgc', 0.05))
    mu_g = float(params.get('mu_g', 0.2))
    cg = float(params.get('cg', 1e-3))

    if has_gw_api:
        sim.setGasWaterProperties(mu_w, cw, p_ref, swi, sgc, mu_g, cg)
        return

    sim.setOilWaterProperties(
        mu_w,
        mu_o,
        cw,
        co,
        p_ref,
        swi,
        sor,
        sgc,
        mu_g,
        cg,
    )


def apply_corner_gas_pvt_properties(sim, params):
    """If supported by the loaded module, forward real-gas PVT settings."""
    if not hasattr(sim, 'setGasPVTParameters'):
        return

    sim.setGasPVTParameters(
        float(params.get('gas_t_C', 140.0)),
        float(params.get('gas_Mg', 16.04)),
        float(params.get('gas_Tc', 190.58)),
        float(params.get('gas_Pc_bar', 45.44)),
        float(params.get('gas_table_Pmin_bar', 1.0)),
        float(params.get('gas_table_Pmax_bar', 1000.0)),
        int(params.get('gas_table_n', 2000)),
        float(params.get('gas_Psc_bar', 1.01325)),
    )


def _resolve_gas_water_initial_state(params):
    """Normalize the gas-water initial state for both new and legacy bindings."""
    pressure = float(params.get('pressure', 800.0))
    sw = float(params.get('sw', 0.05))

    sg_raw = params.get('sg')
    sg = None
    if sg_raw not in (None, ''):
        try:
            sg = float(sg_raw)
        except (TypeError, ValueError):
            sg = None

    if sg is not None:
        implied_sg = 1.0 - sw
        if abs(sg - implied_sg) > 1e-6:
            print(
                f"Initial gas saturation {sg:.6f} is ignored by the gas-water LGR model; "
                f"using Sg = 1 - Sw = {implied_sg:.6f}.",
                flush=True,
            )
        sg = implied_sg

    return pressure, sw, sg


def apply_corner_initial_state(sim, params):
    """Set the gas-water initial state while remaining compatible with old bindings."""
    if not hasattr(sim, 'setInitialStateParameters'):
        return

    pressure, sw, sg = _resolve_gas_water_initial_state(params)

    try:
        sim.setInitialStateParameters(pressure, sw)
        return
    except TypeError:
        pass

    if sg is None:
        sg = 1.0 - sw
    sim.setInitialStateParameters(pressure, sw, sg)


def run_case_dataset_simulation(params):
    """Run the solver from a standard case_dataset directory."""
    dataset_dir = os.path.abspath(params.get('case_dataset_path', '') or '')
    if not dataset_dir:
        raise ValueError("case_dataset_path is required for case_dataset simulation")

    strict = not bool(params.get('allow_invalid_case_dataset', False))
    dataset = load_case_dataset(dataset_dir, strict=strict)
    edfm_core_corner = load_corner_edfm_lgr_module()
    sim = edfm_core_corner.EDFMSimulator()

    _apply_case_dataset_grid(sim, dataset)
    _apply_case_dataset_properties(sim, dataset)
    _apply_case_dataset_dfn(sim, dataset)
    _apply_case_dataset_controls(sim, params)

    result = sim.runSimulation()
    result_params = _case_dataset_result_params(params, dataset)
    sim_data = _collect_case_data_simulation_result(sim, result, result_params)
    sim_data.corner_point_grid = _corner_point_grid_from_dataset(dataset.grid)
    return sim_data


def _apply_case_dataset_grid(sim, dataset):
    if not hasattr(sim, 'setCornerPointGrid'):
        raise RuntimeError("edfm_core_corner_lgr does not expose setCornerPointGrid")
    grid = dataset.grid
    sim.setCornerPointGrid(
        int(grid.nx),
        int(grid.ny),
        int(grid.nz),
        _array_float64(grid.coord),
        _array_float64(grid.zcorn),
        np.asarray(grid.actnum, dtype=np.int32),
    )


def _apply_case_dataset_properties(sim, dataset):
    properties = dataset.properties or {}
    matrix_keys = ('matrix_phi', 'matrix_kx', 'matrix_ky', 'matrix_kz')
    if all(key in properties for key in matrix_keys):
        if not hasattr(sim, 'setMatrixContinuumProperties'):
            raise RuntimeError("edfm_core_corner_lgr does not expose setMatrixContinuumProperties")
        sim.setMatrixContinuumProperties(*[
            _array_float64(properties[key]).tolist() for key in matrix_keys
        ])
    else:
        missing = [key for key in matrix_keys if key not in properties]
        print(f"WARNING: matrix continuum properties are incomplete: {missing}", flush=True)

    fracture_keys = ('fracture_phi', 'fracture_kx', 'fracture_ky', 'fracture_kz')
    if all(key in properties for key in fracture_keys):
        if not hasattr(sim, 'setDFNContinuumProperties'):
            raise RuntimeError("edfm_core_corner_lgr does not expose setDFNContinuumProperties")
        mask = _combined_valid_mask(dataset, fracture_keys)
        sim.setDFNContinuumProperties(
            int(dataset.grid.nx),
            int(dataset.grid.ny),
            int(dataset.grid.nz),
            *[_array_float64(properties[key]) for key in fracture_keys],
            mask,
        )
    else:
        missing = [key for key in fracture_keys if key not in properties]
        print(f"WARNING: fracture continuum properties are incomplete: {missing}", flush=True)

    sigma = properties.get('sigma')
    if sigma is not None:
        if not hasattr(sim, 'setSigmaArray'):
            raise RuntimeError("edfm_core_corner_lgr does not expose setSigmaArray")
        sim.setSigmaArray(_array_float64(sigma).tolist())


def _apply_case_dataset_dfn(sim, dataset):
    if not hasattr(sim, 'setDFNFractures'):
        raise RuntimeError("edfm_core_corner_lgr does not expose setDFNFractures")
    ids, offsets, vertices, apertures, permeabilities = _dfn_arrays(dataset.dfn)
    if len(ids) == 0:
        print("WARNING: case_dataset has no DFN fractures; solver will use generated fractures", flush=True)
        return
    sim.setDFNFractures(ids, offsets, vertices, apertures, permeabilities)


def _apply_case_dataset_controls(sim, params):
    if hasattr(sim, 'setHydraulicFractureParameters'):
        hf_enabled = bool(params.get('hf_enabled', False))
        hf_count = int(params.get('hf_count', 0)) if hf_enabled else 0
        sim.setHydraulicFractureParameters(
            hf_count,
            float(params.get('hf_spacing_x', 0.0)),
            float(params.get('hf_length', 120.0)),
            float(params.get('hf_height', 30.0)),
            float(params.get('hf_aperture', 0.1)),
            float(params.get('hf_perm', 1000.0)),
            float(params.get('hf_center_x', -1.0)),
            float(params.get('hf_center_y', -1.0)),
            float(params.get('hf_center_z', -1.0)),
        )
    if hasattr(sim, 'setWellParameters'):
        sim.setWellParameters(
            float(params.get('well_radius', 0.05)),
            float(params.get('well_pressure', 100.0)),
        )
    apply_corner_fluid_properties(sim, params)
    apply_corner_gas_pvt_properties(sim, params)
    apply_corner_initial_state(sim, params)

    if hasattr(sim, 'setLGRParameters'):
        sim.setLGRParameters(
            bool(params.get('enable_lgr', True)),
            float(params.get('d_threshold', 5.05)),
            int(params.get('lgr_nrx', 2)),
            int(params.get('lgr_nry', 2)),
            int(params.get('lgr_nrz', 2)),
        )
    if hasattr(sim, 'setDualPorosityParameters') and params.get('enable_dual_porosity') is not None:
        sim.setDualPorosityParameters(
            bool(params.get('enable_dual_porosity', False)),
            float(params.get('phi_matrix', 0.04)),
            float(params.get('phi_fracture', 0.4)),
            float(params.get('k_matrix_x', 0.005)),
            float(params.get('k_matrix_y', 0.005)),
            float(params.get('k_matrix_z', 0.005)),
            float(params.get('k_fracture_x', 1.0)),
            float(params.get('k_fracture_y', 1.0)),
            float(params.get('k_fracture_z', 0.1)),
            float(params.get('matrix_volume_fraction', 0.98)),
            float(params.get('fracture_volume_fraction', 0.02)),
            float(params.get('wr_shape_factor', 0.12)),
        )
    _apply_case_data_solver_parameters(sim, params)


def _case_dataset_result_params(params, dataset):
    result_params = dict(params)
    lx, ly, lz = _grid_extents(dataset.grid.coord)
    result_params.update({
        'nx': int(dataset.grid.nx),
        'ny': int(dataset.grid.ny),
        'nz': int(dataset.grid.nz),
        'lx': lx,
        'ly': ly,
        'lz': lz,
    })
    return result_params


def _corner_point_grid_from_dataset(grid):
    """Build the renderer-facing coarse corner grid from case_dataset arrays."""
    nx = int(getattr(grid, 'nx', 0) or 0)
    ny = int(getattr(grid, 'ny', 0) or 0)
    nz = int(getattr(grid, 'nz', 0) or 0)
    if nx <= 0 or ny <= 0 or nz <= 0:
        return None

    coord = _array_float64(getattr(grid, 'coord', []))
    zcorn = _array_float64(getattr(grid, 'zcorn', []))
    expected_pillars = (nx + 1) * (ny + 1)
    expected_zcorn = nx * ny * nz * 8
    if coord.size < expected_pillars * 6 or zcorn.size < expected_zcorn:
        print(
            "WARNING: case_dataset grid arrays are incomplete; "
            "corner_point_grid not attached to result",
            flush=True,
        )
        return None

    coord = coord[:expected_pillars * 6].reshape(expected_pillars, 6)
    zcorn = zcorn[:expected_zcorn].reshape(nx * ny * nz, 8)

    corner_grid = CornerPointGridData()
    corner_grid.nx = nx
    corner_grid.ny = ny
    corner_grid.nz = nz

    xs = np.concatenate([coord[:, 0], coord[:, 3]])
    ys = np.concatenate([coord[:, 1], coord[:, 4]])
    zs = zcorn.reshape(-1)
    corner_grid.origin_x = float(np.nanmin(xs)) if xs.size else 0.0
    corner_grid.origin_y = float(np.nanmin(ys)) if ys.size else 0.0
    corner_grid.origin_z = float(np.nanmin(zs)) if zs.size else 0.0
    corner_grid.lx = float(np.nanmax(xs) - np.nanmin(xs)) if xs.size else 0.0
    corner_grid.ly = float(np.nanmax(ys) - np.nanmin(ys)) if ys.size else 0.0
    corner_grid.lz = float(np.nanmax(zs) - np.nanmin(zs)) if zs.size else 0.0

    def pillar(i, j):
        return coord[j * (nx + 1) + i]

    def top_xy(i, j):
        p = pillar(i, j)
        return float(p[0]), float(p[1])

    def bottom_xy(i, j):
        p = pillar(i, j)
        return float(p[3]), float(p[4])

    cells = []
    cell_id = 0
    for iz in range(nz):
        for iy in range(ny):
            for ix in range(nx):
                values = zcorn[cell_id]
                cell = CornerPointCell(cell_id)
                cell.ix = ix
                cell.iy = iy
                cell.iz = iz

                b0 = bottom_xy(ix, iy)
                b1 = bottom_xy(ix + 1, iy)
                b2 = bottom_xy(ix + 1, iy + 1)
                b3 = bottom_xy(ix, iy + 1)
                t0 = top_xy(ix, iy)
                t1 = top_xy(ix + 1, iy)
                t2 = top_xy(ix + 1, iy + 1)
                t3 = top_xy(ix, iy + 1)

                cell.corners = [
                    (b0[0], b0[1], float(values[4])),
                    (b1[0], b1[1], float(values[5])),
                    (b2[0], b2[1], float(values[6])),
                    (b3[0], b3[1], float(values[7])),
                    (t0[0], t0[1], float(values[0])),
                    (t1[0], t1[1], float(values[1])),
                    (t2[0], t2[1], float(values[2])),
                    (t3[0], t3[1], float(values[3])),
                ]
                cells.append(cell)
                cell_id += 1

    corner_grid.cells = cells
    return corner_grid


def _grid_extents(coord):
    coord = _array_float64(coord)
    if coord.size == 0 or coord.size % 6 != 0:
        return 0.0, 0.0, 0.0
    pillars = coord.reshape((-1, 6))
    xs = np.concatenate([pillars[:, 0], pillars[:, 3]])
    ys = np.concatenate([pillars[:, 1], pillars[:, 4]])
    zs = np.concatenate([pillars[:, 2], pillars[:, 5]])
    return (
        float(np.max(xs) - np.min(xs)),
        float(np.max(ys) - np.min(ys)),
        float(np.max(zs) - np.min(zs)),
    )


def _combined_valid_mask(dataset, property_keys):
    masks = []
    for key in property_keys:
        mask = dataset.valid_masks.get(key)
        if mask is not None:
            masks.append(np.asarray(mask, dtype=np.bool_))
    if not masks:
        return np.asarray(dataset.grid.active_mask, dtype=np.bool_)
    combined = masks[0].copy()
    for mask in masks[1:]:
        n = min(combined.size, mask.size)
        combined[:n] = combined[:n] & mask[:n]
        if mask.size < combined.size:
            combined[mask.size:] = False
    return np.asarray(combined, dtype=np.bool_)


def _dfn_arrays(dfn_payload):
    dfn_payload = dfn_payload or {}
    fractures = dfn_payload.get('fractures') or [] if isinstance(dfn_payload, dict) else []
    ids = []
    offsets = [0]
    vertices = []
    apertures = []
    permeabilities = []
    for index, fracture in enumerate(fractures):
        points = fracture.get('vertices') or fracture.get('points') or []
        if len(points) < 3:
            continue
        try:
            clean_points = [
                (float(point[0]), float(point[1]), float(point[2]))
                for point in points
            ]
        except (TypeError, ValueError, IndexError):
            continue
        frac_id = fracture.get('fracture_id', fracture.get('id', index))
        aperture = fracture.get('aperture', 0.01)
        permeability = fracture.get('permeability', fracture.get('perm', 10000.0))
        ids.append(int(frac_id))
        vertices.extend(clean_points)
        offsets.append(len(vertices))
        apertures.append(max(float(aperture), 1e-12))
        permeabilities.append(max(float(permeability), 0.0))
    return (
        np.asarray(ids, dtype=np.int32),
        np.asarray(offsets, dtype=np.int32),
        np.asarray(vertices, dtype=np.float64).reshape((-1, 3)),
        np.asarray(apertures, dtype=np.float64),
        np.asarray(permeabilities, dtype=np.float64),
    )


def _array_float64(values):
    return np.ascontiguousarray(values, dtype=np.float64)


def run_case_data_simulation(params):
    """执行 CaseData 接入流程的模拟。

    这个分支面向新的 CaseData 输入链路。当前算法 pybind 还没有最终确认，
    因此 grid.inc 和属性文件使用显式接口探测：接口存在就调用，不存在就给出
    清晰错误或警告，避免误走旧的 coord_file/zcorn_file 流程。
    """
    refinement_mode = params.get('corner_grid_refinement', '不加密')
    use_lgr_module = refinement_mode == '加密'
    edfm_core_corner = load_corner_edfm_lgr_module() if use_lgr_module else load_corner_edfm_module()
    sim = edfm_core_corner.EDFMSimulator()

    _apply_case_data_grid_file(sim, params)
    _apply_case_data_property_files(sim, params)
    _apply_case_data_fracture_file(sim, params)

    if hasattr(sim, 'setWellParameters'):
        sim.setWellParameters(
            float(params.get('well_radius', 0.05)),
            float(params.get('well_pressure', 100.0)),
        )
    apply_corner_fluid_properties(sim, params)
    apply_corner_gas_pvt_properties(sim, params)
    apply_corner_initial_state(sim, params)

    if hasattr(sim, 'setLGRParameters'):
        sim.setLGRParameters(
            bool(params.get('enable_lgr', True)),
            float(params.get('d_threshold', 5.05)),
            int(params.get('lgr_nrx', 2)),
            int(params.get('lgr_nry', 2)),
            int(params.get('lgr_nrz', 2)),
        )
    _apply_case_data_solver_parameters(sim, params)

    result = sim.runSimulation()
    return _collect_case_data_simulation_result(sim, result, params)


def _apply_case_data_grid_file(sim, params):
    grid_file = params.get('grid_file', '')
    if not grid_file:
        raise ValueError("CaseData 缺少 grid_file，无法运行模拟")
    if hasattr(sim, 'setGridFile'):
        sim.setGridFile(grid_file)
        return
    if hasattr(sim, 'setGridIncFile'):
        sim.setGridIncFile(grid_file)
        return
    raise RuntimeError(
        "当前算法 pybind 尚未提供 grid.inc 接口。"
        "请在 C++ 侧新增 setGridFile(grid_file) 或 setGridIncFile(grid_file)。"
    )


def _apply_case_data_property_files(sim, params):
    property_args = (
        params.get('matrix_phi_file', ''),
        params.get('matrix_kx_file', ''),
        params.get('matrix_ky_file', ''),
        params.get('matrix_kz_file', ''),
        params.get('fracture_phi_file', ''),
        params.get('fracture_kx_file', ''),
        params.get('fracture_ky_file', ''),
        params.get('fracture_kz_file', ''),
        params.get('sigma_file', ''),
    )
    if hasattr(sim, 'setPropertyFiles'):
        sim.setPropertyFiles(*property_args)
        return
    if any(property_args):
        print(
            "WARNING: 当前算法 pybind 尚未提供 setPropertyFiles(...); "
            "CaseData 属性文件路径已生成，但本次运行不会传入 C++。",
            flush=True,
        )


def _apply_case_data_fracture_file(sim, params):
    fracture_file = params.get('fracture_file', '')
    if not fracture_file:
        return
    if hasattr(sim, 'setFractureFile'):
        sim.setFractureFile(fracture_file)
        return
    print(
        "WARNING: 当前算法 pybind 尚未提供 setFractureFile(fracture_file); "
        "CaseData 裂缝几何文件路径已生成，但本次运行不会传入 C++。",
        flush=True,
    )


def _apply_case_data_solver_parameters(sim, params):
    if hasattr(sim, 'setSolverParameters'):
        sim.setSolverParameters(
            float(params.get('simulation_time', 100.0)),
            float(params.get('time_step', 1.0)),
            float(params.get('dt_min', 1e-6)),
            float(params.get('dt_max', 30.0)),
            int(params.get('newton_max_iter', 15)),
            float(params.get('newton_tol', 1e-3)),
            float(params.get('linear_tol', 1e-8)),
            int(params.get('linear_max_iter', 1000)),
        )
        return
    if hasattr(sim, 'setSimulationParameters'):
        sim.setSimulationParameters(float(params.get('simulation_time', 100.0)))


def _collect_case_data_simulation_result(sim, result, params):
    nx = int(params.get('nx', 0))
    ny = int(params.get('ny', 0))
    nz = int(params.get('nz', 0))
    lx = float(params.get('lx', 0.0))
    ly = float(params.get('ly', 0.0))
    lz = float(params.get('lz', 0.0))

    sim_data = SimulationData()
    sim_data.generate_from_cpp(result, nx, ny, nz, lx, ly, lz, [], [])
    if hasattr(sim, 'getCellGeometryWithPressure'):
        try:
            sim_data.cell_geometry_with_pressure = sim.getCellGeometryWithPressure()
        except Exception as exc:
            print(f"WARNING: getCellGeometryWithPressure failed: {exc}", flush=True)
    if hasattr(sim, 'getLGRGridGeometry'):
        try:
            sim_data.corner_lgr_grid_geometry = sim.getLGRGridGeometry()
        except Exception as exc:
            print(f"WARNING: getLGRGridGeometry failed: {exc}", flush=True)
    if hasattr(sim, 'getParentGridGeometry'):
        try:
            sim_data.corner_lgr_parent_grid_geometry = sim.getParentGridGeometry()
        except Exception as exc:
            print(f"WARNING: getParentGridGeometry failed: {exc}", flush=True)
    if hasattr(sim, 'getRefinedGridGeometry'):
        try:
            sim_data.corner_lgr_refined_grid_geometry = sim.getRefinedGridGeometry()
        except Exception as exc:
            print(f"WARNING: getRefinedGridGeometry failed: {exc}", flush=True)
    if hasattr(sim, 'getDualPorosityPressureData'):
        try:
            sim_data.dual_porosity_pressure_field = sim.getDualPorosityPressureData()
        except Exception as exc:
            print(f"WARNING: getDualPorosityPressureData failed: {exc}", flush=True)
    if hasattr(sim, 'getTimeSteps'):
        try:
            sim_data.time_steps = _array_float64(sim.getTimeSteps()).tolist()
        except Exception as exc:
            print(f"WARNING: getTimeSteps failed: {exc}", flush=True)
    if hasattr(sim, 'getPressureSteps'):
        try:
            sim_data.pressure_steps = _array_float64(sim.getPressureSteps()).tolist()
        except Exception as exc:
            print(f"WARNING: getPressureSteps failed: {exc}", flush=True)
    if hasattr(sim, 'getSwSteps'):
        try:
            sim_data.sw_steps = _array_float64(sim.getSwSteps()).tolist()
        except Exception as exc:
            print(f"WARNING: getSwSteps failed: {exc}", flush=True)
    if hasattr(sim, 'getPorositySteps'):
        try:
            sim_data.porosity_steps = _array_float64(sim.getPorositySteps()).tolist()
        except Exception as exc:
            print(f"WARNING: getPorositySteps failed: {exc}", flush=True)
    if hasattr(sim, 'getPermeabilityXSteps'):
        try:
            sim_data.permeability_x_steps = _array_float64(sim.getPermeabilityXSteps()).tolist()
        except Exception as exc:
            print(f"WARNING: getPermeabilityXSteps failed: {exc}", flush=True)
    if hasattr(sim, 'getPermeabilityYSteps'):
        try:
            sim_data.permeability_y_steps = _array_float64(sim.getPermeabilityYSteps()).tolist()
        except Exception as exc:
            print(f"WARNING: getPermeabilityYSteps failed: {exc}", flush=True)
    if hasattr(sim, 'getPermeabilityZSteps'):
        try:
            sim_data.permeability_z_steps = _array_float64(sim.getPermeabilityZSteps()).tolist()
        except Exception as exc:
            print(f"WARNING: getPermeabilityZSteps failed: {exc}", flush=True)
    sim_data.has_dual_porosity = bool(params.get('enable_dual_porosity', False))
    return sim_data


def run_corner_edfm_simulation(params):
    """执行 Corner EDFM 模拟并返回 SimulationData。"""
    refinement_mode = params.get('corner_grid_refinement', '不加密')
    use_lgr_module = refinement_mode == '加密'
    edfm_core_corner = load_corner_edfm_lgr_module() if use_lgr_module else load_corner_edfm_module()

    coord_file = params.get('coord_file', '')
    zcorn_file = params.get('zcorn_file', '')
    if not coord_file or not zcorn_file:
        raise ValueError("Corner EDFM requires both COORD and ZCORN files")
    
    # 注意：不再在子进程中加载corner_point_grid，主进程中已经加载了

    sim = edfm_core_corner.EDFMSimulator()
    sim.setCornerPointFiles(coord_file, zcorn_file)
    sim.setFractureParameters(
        int(params.get('num_fracs', 100)),
        float(params.get('min_len', 10.0)),
        float(params.get('max_len', 20.0)),
        float(params.get('max_dip', math.pi / 3.0)),
        float(params.get('min_strike', 0.0)),
        float(params.get('max_strike', math.pi)),
        float(params.get('aperture', 0.1)),
        float(params.get('frac_perm', 100.0)),
    )
    region_num_fracs = int(params.get('region_num_fracs', 0))
    if region_num_fracs > 0:
        region_args = (
            region_num_fracs,
            float(params.get('region_x_min', 0.0)),
            float(params.get('region_x_max', 0.0)),
            float(params.get('region_y_min', 0.0)),
            float(params.get('region_y_max', 0.0)),
            float(params.get('region_z_min', 0.0)),
            float(params.get('region_z_max', 0.0)),
        )
        if hasattr(sim, 'setRegionFractureParameters'):
            print(
                "Setting region fracture parameters: "
                f"N={region_args[0]}, "
                f"X[{region_args[1]}, {region_args[2]}], "
                f"Y[{region_args[3]}, {region_args[4]}], "
                f"Z[{region_args[5]}, {region_args[6]}]",
                flush=True,
            )
            sim.setRegionFractureParameters(*region_args)
        else:
            print(
                "WARNING: corner EDFM module missing setRegionFractureParameters(); "
                "region fractures disabled",
                flush=True,
            )
    hf_count = int(params.get('hf_count', 20)) if params.get('hf_enabled', True) else 0
    hf_spacing = float(params.get('hf_spacing_x', 0.0))
    sim.setHydraulicFractureParameters(
        hf_count,
        hf_spacing,
        float(params.get('hf_length', 120.0)),
        float(params.get('hf_height', 30.0)),
        float(params.get('hf_aperture', 0.1)),
        float(params.get('hf_perm', 1000.0)),
        float(params.get('hf_center_x', -1.0)),
        float(params.get('hf_center_y', -1.0)),
        float(params.get('hf_center_z', -1.0)),
    )
    sim.setWellParameters(
        float(params.get('well_radius', 0.05)),
        float(params.get('well_pressure', 50.0)),
    )
    apply_corner_fluid_properties(sim, params)
    apply_corner_gas_pvt_properties(sim, params)
    if use_lgr_module and hasattr(sim, 'setInitialStateParameters'):
        apply_corner_initial_state(sim, params)
    if use_lgr_module and hasattr(sim, 'setLGRParameters'):
        sim.setLGRParameters(
            bool(params.get('enable_lgr', True)),
            float(params.get('d_threshold', 5.05)),
            int(params.get('lgr_nrx', 2)),
            int(params.get('lgr_nry', 2)),
            int(params.get('lgr_nrz', 2)),
        )
    if use_lgr_module and hasattr(sim, 'setDualPorosityParameters'):
        enable_dp = bool(params.get('enable_dual_porosity', False))
        if enable_dp:
            print("Setting dual porosity parameters (Warren-Root)...", flush=True)
        sim.setDualPorosityParameters(
            enable_dp,
            float(params.get('phi_matrix', 0.04)),
            float(params.get('phi_fracture', 0.4)),
            float(params.get('k_matrix_x', 0.005)),
            float(params.get('k_matrix_y', 0.005)),
            float(params.get('k_matrix_z', 0.005)),
            float(params.get('k_fracture_x', 1.0)),
            float(params.get('k_fracture_y', 1.0)),
            float(params.get('k_fracture_z', 0.1)),
            float(params.get('matrix_volume_fraction', 0.98)),
            float(params.get('fracture_volume_fraction', 0.02)),
            float(params.get('wr_shape_factor', 0.12)),
        )
    elif use_lgr_module and not hasattr(sim, 'setDualPorosityParameters'):
        print("Note: loaded module does not expose setDualPorosityParameters; dual porosity skipped.", flush=True)

    sim.setSimulationParameters(float(params.get('simulation_time', 100.0)))

    result = sim.runSimulation()

    time_steps = None
    pressure_steps = None
    sw_steps = None
    porosity_steps = None
    permeability_x_steps = None
    permeability_y_steps = None
    permeability_z_steps = None
    if hasattr(sim, 'getTimeSteps'):
        try:
            time_steps = _array_float64(sim.getTimeSteps()).tolist()
        except Exception as exc:
            print(f"WARNING: getTimeSteps failed: {exc}", flush=True)
    if hasattr(sim, 'getPressureSteps'):
        try:
            pressure_steps = _array_float64(sim.getPressureSteps()).tolist()
        except Exception as exc:
            print(f"WARNING: getPressureSteps failed: {exc}", flush=True)
    if hasattr(sim, 'getSwSteps'):
        try:
            sw_steps = _array_float64(sim.getSwSteps()).tolist()
        except Exception as exc:
            print(f"WARNING: getSwSteps failed: {exc}", flush=True)
    if hasattr(sim, 'getPorositySteps'):
        try:
            porosity_steps = _array_float64(sim.getPorositySteps()).tolist()
        except Exception as exc:
            print(f"WARNING: getPorositySteps failed: {exc}", flush=True)
    if hasattr(sim, 'getPermeabilityXSteps'):
        try:
            permeability_x_steps = _array_float64(sim.getPermeabilityXSteps()).tolist()
        except Exception as exc:
            print(f"WARNING: getPermeabilityXSteps failed: {exc}", flush=True)
    if hasattr(sim, 'getPermeabilityYSteps'):
        try:
            permeability_y_steps = _array_float64(sim.getPermeabilityYSteps()).tolist()
        except Exception as exc:
            print(f"WARNING: getPermeabilityYSteps failed: {exc}", flush=True)
    if hasattr(sim, 'getPermeabilityZSteps'):
        try:
            permeability_z_steps = _array_float64(sim.getPermeabilityZSteps()).tolist()
        except Exception as exc:
            print(f"WARNING: getPermeabilityZSteps failed: {exc}", flush=True)
    
    print("Getting cell geometry with pressure...")
    cell_geometry = sim.getCellGeometryWithPressure()
    
    print("Getting fracture vertices...")
    try:
        fracture_vertices = sim.getFractureVertices()
    except:
        fracture_vertices = None
    
    # 如果是LGR加密模式，获取加密网格几何
    corner_lgr_grid_geometry = None
    corner_lgr_parent_grid_geometry = None
    corner_lgr_refined_grid_geometry = None
    if use_lgr_module:
        try:
            corner_lgr_grid_geometry = sim.getLGRGridGeometry()
            corner_lgr_parent_grid_geometry = sim.getParentGridGeometry()
            corner_lgr_refined_grid_geometry = sim.getRefinedGridGeometry()
        except Exception as e:
            print(f"Warning: could not get LGR grid geometry: {e}", flush=True)
    
    nx, ny, nz, lx, ly, lz = load_corner_grid_info(coord_file, zcorn_file)

    sim_data = SimulationData()
    sim_data.generate_from_cpp(result, nx, ny, nz, lx, ly, lz, [], [])
    sim_data.cell_geometry_with_pressure = cell_geometry
    sim_data.corner_lgr_grid_geometry = corner_lgr_grid_geometry
    sim_data.corner_lgr_parent_grid_geometry = corner_lgr_parent_grid_geometry
    sim_data.corner_lgr_refined_grid_geometry = corner_lgr_refined_grid_geometry
    sim_data.time_steps = time_steps
    sim_data.pressure_steps = pressure_steps
    sim_data.sw_steps = sw_steps
    sim_data.porosity_steps = porosity_steps
    sim_data.permeability_x_steps = permeability_x_steps
    sim_data.permeability_y_steps = permeability_y_steps
    sim_data.permeability_z_steps = permeability_z_steps

    dual_porosity_pressure = None
    if use_lgr_module and hasattr(sim, 'getDualPorosityPressureData'):
        try:
            dual_porosity_pressure = sim.getDualPorosityPressureData()
            if dual_porosity_pressure is not None and hasattr(dual_porosity_pressure, '__len__'):
                print(f"Got dual porosity pressure data: {len(dual_porosity_pressure)} entries", flush=True)
            else:
                print("Dual porosity pressure data is empty or None.", flush=True)
        except Exception as e:
            print(f"Warning: getDualPorosityPressureData failed: {e}", flush=True)
    if dual_porosity_pressure is not None:
        sim_data.dual_porosity_pressure_field = dual_porosity_pressure
    sim_data.has_dual_porosity = bool(params.get('enable_dual_porosity', False))
    
    # 插值由C++算法完成，不再在Python中做插值
    return sim_data


def build_interpolated_pressure_from_leaf_data(sim_data, nx=50, ny=25, nz=10):
    """旧版 edfm_core 缺少插值接口时，使用最近邻生成规则压力场。"""
    field_data = sim_data.pressure_field
    if not field_data:
        return []

    xs = [point[0] for point in field_data]
    ys = [point[1] for point in field_data]
    zs = [point[2] for point in field_data]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    min_z, max_z = min(zs), max(zs)

    interpolated = []
    for k in range(nz):
        z = min_z + (max_z - min_z) * k / (nz - 1) if nz > 1 else min_z
        for j in range(ny):
            y = min_y + (max_y - min_y) * j / (ny - 1) if ny > 1 else min_y
            for i in range(nx):
                x = min_x + (max_x - min_x) * i / (nx - 1) if nx > 1 else min_x
                nearest = min(
                    field_data,
                    key=lambda point: (
                        (point[0] - x) * (point[0] - x)
                        + (point[1] - y) * (point[1] - y)
                        + (point[2] - z) * (point[2] - z)
                    ),
                )
                interpolated.append((x, y, z, nearest[3]))
    return interpolated


def main():
    parser = argparse.ArgumentParser(description="Run EDFM simulation in a child process.")
    parser.add_argument("--output", required=True, help="Path to the JSON result file.")
    parser.add_argument("--params", required=True, help="JSON-encoded simulation parameters.")
    args = parser.parse_args()

    try:
        params = json.loads(args.params)
        sim_data = run_simulation(params)
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        sim_data.save_json(args.output)
        return 0
    except Exception as exc:
        print(f"RUNNER ERROR: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
