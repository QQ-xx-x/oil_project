# -*- coding: utf-8 -*-
"""
静态属性场预览渲染器。
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pyvista as pv

from front.uniform_parser import parse_grid, parse_property


def get_bright_jet_cmap():
    from matplotlib.colors import LinearSegmentedColormap

    bright_jet_colors = [
        (0.00, (0.00, 1.00, 1.00)),
        (0.04, (0.00, 1.00, 0.95)),
        (0.08, (0.00, 1.00, 0.88)),
        (0.12, (0.00, 1.00, 0.78)),
        (0.16, (0.00, 1.00, 0.65)),
        (0.20, (0.00, 1.00, 0.52)),
        (0.24, (0.00, 1.00, 0.40)),
        (0.26, (0.00, 1.00, 0.35)),
        (0.30, (0.08, 1.00, 0.22)),
        (0.34, (0.18, 1.00, 0.10)),
        (0.38, (0.32, 1.00, 0.02)),
        (0.42, (0.48, 1.00, 0.00)),
        (0.46, (0.62, 1.00, 0.00)),
        (0.50, (0.78, 1.00, 0.00)),
        (0.54, (0.92, 1.00, 0.00)),
        (0.58, (1.00, 1.00, 0.00)),
        (0.63, (1.00, 0.94, 0.00)),
        (0.68, (1.00, 0.86, 0.00)),
        (0.73, (1.00, 0.76, 0.00)),
        (0.78, (1.00, 0.64, 0.00)),
        (0.84, (1.00, 0.48, 0.00)),
        (0.90, (1.00, 0.34, 0.00)),
        (0.95, (1.00, 0.18, 0.00)),
        (1.00, (1.00, 0.00, 0.00)),
    ]

    return LinearSegmentedColormap.from_list(
        "bright_jet",
        bright_jet_colors,
        N=4096,
    )


STATIC_PROPERTY_OPACITY = 0.95
STATIC_PROPERTY_SHOW_EDGES = False
STATIC_PROPERTY_EDGE_COLOR = (0.18, 0.18, 0.18)
STATIC_PROPERTY_EDGE_LINE_WIDTH = 0.3
STATIC_PROPERTY_LIGHTING = False
STATIC_PROPERTY_SMOOTH_SHADING = False
STATIC_PROPERTY_AMBIENT = 1.0
STATIC_PROPERTY_DIFFUSE = 0.0
STATIC_PROPERTY_SPECULAR = 0.0
STATIC_PROPERTY_INTERPOLATE_BEFORE_MAP = False

STATIC_PROPERTY_SCALAR_BAR_ARGS = {
    "position_x": 0.02,
    "position_y": 0.55,
    "width": 0.08,
    "height": 0.40,
    "label_font_size": 14,
    "title_font_size": 16,
    "color": "#2f3640",
    "vertical": True,
}


STATIC_PROPERTY_SPECS = {
    "MATRIX_PORO": {
        "aliases": ["matrix_phi", "MATRIX_PORO", "matrix_poro"],
        "label": "Matrix Porosity",
        "internal_key": "matrix_phi",
        "scale": 1.0,
        "unit": "",
    },
    "MATRIX_PERMX": {
        "aliases": ["matrix_kx", "MATRIX_PERMX", "matrix_permx"],
        "label": "Matrix Kx",
        "internal_key": "matrix_kx",
        "scale": 0.001,
        "unit": "",
    },
    "MATRIX_PERMY": {
        "aliases": ["matrix_ky", "MATRIX_PERMY", "matrix_permy"],
        "label": "Matrix Ky",
        "internal_key": "matrix_ky",
        "scale": 0.001,
        "unit": "",
    },
    "MATRIX_PERMZ": {
        "aliases": ["matrix_kz", "MATRIX_PERMZ", "matrix_permz"],
        "label": "Matrix Kz",
        "internal_key": "matrix_kz",
        "scale": 0.001,
        "unit": "",
    },
    "DFN_PORO": {
        "aliases": ["fracture_phi", "DFN_PORO", "dfn_poro"],
        "label": "DFN Porosity",
        "internal_key": "fracture_phi",
        "scale": 1.0,
        "unit": "",
    },
    "DFN_PERMX": {
        "aliases": ["fracture_kx", "DFN_PERMX", "dfn_permx"],
        "label": "DFN Kx",
        "internal_key": "fracture_kx",
        "scale": 1.0,
        "unit": "",
    },
    "DFN_PERMY": {
        "aliases": ["fracture_ky", "DFN_PERMY", "dfn_permy"],
        "label": "DFN Ky",
        "internal_key": "fracture_ky",
        "scale": 1.0,
        "unit": "",
    },
    "DFN_PERMZ": {
        "aliases": ["fracture_kz", "DFN_PERMZ", "dfn_permz"],
        "label": "DFN Kz",
        "internal_key": "fracture_kz",
        "scale": 1.0,
        "unit": "",
    },
    "SIGMA": {
        "aliases": ["sigma", "SIGMA"],
        "label": "Sigma",
        "internal_key": "sigma",
        "scale": 1.0,
        "unit": "",
    },
}


PROPERTY_ALIAS_TO_CANONICAL = {}

for canonical_key, spec in STATIC_PROPERTY_SPECS.items():
    PROPERTY_ALIAS_TO_CANONICAL[canonical_key] = canonical_key
    PROPERTY_ALIAS_TO_CANONICAL[canonical_key.lower()] = canonical_key

    for alias in spec.get("aliases", []):
        PROPERTY_ALIAS_TO_CANONICAL[alias] = canonical_key
        PROPERTY_ALIAS_TO_CANONICAL[alias.lower()] = canonical_key


def normalize_static_property_key(property_key: str) -> str:
    if property_key is None:
        raise ValueError("property_key 不能为空")

    key = str(property_key).strip()

    if key in PROPERTY_ALIAS_TO_CANONICAL:
        return PROPERTY_ALIAS_TO_CANONICAL[key]

    lower_key = key.lower()

    if lower_key in PROPERTY_ALIAS_TO_CANONICAL:
        return PROPERTY_ALIAS_TO_CANONICAL[lower_key]

    raise KeyError(
        f"未知静态属性: {property_key!r}, "
        f"可用属性: {list(STATIC_PROPERTY_SPECS.keys())}"
    )


def _is_valid_path(path: Optional[str]) -> bool:
    return bool(path) and os.path.exists(str(path))


def _scale_static_property_values(
    values,
    property_key: str,
    null_value: float = 99999.0,
) -> np.ndarray:
    canonical_key = normalize_static_property_key(property_key)
    spec = STATIC_PROPERTY_SPECS[canonical_key]

    array = np.asarray(
        values,
        dtype=np.float64,
    ).copy()

    scale = float(spec.get("scale", 1.0))

    if abs(scale - 1.0) < 1e-15:
        return array

    valid_mask = (
        np.isfinite(array)
        & (np.abs(array - float(null_value)) > 1e-12)
    )

    array[valid_mask] = array[valid_mask] * scale

    return array


def property_files_from_case_dataset(case_dataset: Dict[str, Any]) -> Dict[str, str]:
    source_files = case_dataset.get(
        "source_files",
        {},
    ) or {}

    def _path(key: str) -> str:
        item = source_files.get(
            key,
            {},
        ) or {}

        return item.get(
            "path",
            "",
        ) or ""

    return {
        "MATRIX_PORO": _path("matrix_phi_file"),
        "MATRIX_PERMX": _path("matrix_kx_file"),
        "MATRIX_PERMY": _path("matrix_ky_file"),
        "MATRIX_PERMZ": _path("matrix_kz_file"),
        "DFN_PORO": _path("fracture_phi_file"),
        "DFN_PERMX": _path("fracture_kx_file"),
        "DFN_PERMY": _path("fracture_ky_file"),
        "DFN_PERMZ": _path("fracture_kz_file"),
        "SIGMA": _path("sigma_file"),
    }


def attach_static_property_preview_data_from_files(
    sim_data,
    grid_file: str,
    property_files: Dict[str, str],
    null_value: float = 99999.0,
    strict: bool = False,
):
    if not _is_valid_path(grid_file):
        raise FileNotFoundError(f"grid_file 不存在: {grid_file}")

    grid_data = parse_grid(grid_file)

    total = int(
        grid_data.get(
            "total_cell_count",
            int(grid_data["nx"]) * int(grid_data["ny"]) * int(grid_data["nz"]),
        )
    )

    static_properties: Dict[str, np.ndarray] = {}
    static_property_meta: Dict[str, Dict[str, Any]] = {}

    for raw_key, file_path in property_files.items():
        if not file_path:
            if strict:
                raise FileNotFoundError(f"{raw_key} 的属性路径为空")
            continue

        if not os.path.exists(str(file_path)):
            if strict:
                raise FileNotFoundError(f"{raw_key} 属性文件不存在: {file_path}")
            continue

        canonical_key = normalize_static_property_key(raw_key)
        spec = STATIC_PROPERTY_SPECS[canonical_key]

        values = parse_property(
            str(file_path),
            expected_len=total,
        )

        values = _scale_static_property_values(
            values,
            property_key=canonical_key,
            null_value=null_value,
        )

        internal_key = spec["internal_key"]

        static_properties[canonical_key] = values
        static_properties[internal_key] = values

        static_property_meta[canonical_key] = {
            "file_path": str(file_path),
            "label": spec["label"],
            "internal_key": internal_key,
            "scale": spec["scale"],
            "unit": spec.get("unit", ""),
            "null_value": float(null_value),
            "count": int(values.size),
        }

    sim_data.static_grid_data = grid_data
    sim_data.static_properties = static_properties
    sim_data.static_property_meta = static_property_meta
    sim_data.static_property_null_value = float(null_value)

    return sim_data


class StaticPropertyPreviewRenderer:
    def __init__(self, host):
        self.host = host
        self.plotter = host.plotter

        self.actor = None
        self.edge_actor = None
        self.scalar_bar_actor = None
        self.scalar_bar_title = None

        self.current_grid = None
        self.current_property_key = None
        self.current_axis = None
        self.current_layer_index = None

    def clear(self, render_now: bool = True):
        self._remove_actor(self.actor)
        self._remove_actor(self.edge_actor)

        self.actor = None
        self.edge_actor = None

        self.current_grid = None
        self.current_property_key = None
        self.current_axis = None
        self.current_layer_index = None

        self._remove_scalar_bar()

        if render_now:
            self._render()

    def render_property(
        self,
        sim_data,
        property_key: str,
        render_now: bool = True,
        **_ignored_style_kwargs,
    ):
        canonical_key = normalize_static_property_key(property_key)

        grid_data = self._get_static_grid_data(sim_data)

        values = self._get_static_property_values(
            sim_data,
            canonical_key,
        )

        mask = self._build_valid_property_mask(
            grid_data=grid_data,
            values=values,
            axis=None,
            layer_index0=None,
            null_value=self._get_null_value(sim_data),
        )

        scalar_name = self._scalar_name(canonical_key)

        grid = self._build_corner_point_property_grid(
            grid_data=grid_data,
            values=values,
            mask=mask,
            scalar_name=scalar_name,
        )

        return self._render_grid(
            grid=grid,
            property_key=canonical_key,
            scalar_name=scalar_name,
            title=self._scalar_bar_title(canonical_key),
            axis=None,
            layer_index0=None,
            render_now=render_now,
        )

    def render_property_layer(
        self,
        sim_data,
        property_key: str,
        axis: str = "k",
        layer_index: int = 1,
        index_base: int = 1,
        render_now: bool = True,
        **_ignored_style_kwargs,
    ):
        canonical_key = normalize_static_property_key(property_key)

        axis = str(axis).strip().lower()

        if axis not in ("i", "j", "k"):
            raise ValueError("axis 只能是 'i'、'j' 或 'k'")

        layer_index0 = int(layer_index)

        if int(index_base) == 1:
            layer_index0 -= 1

        grid_data = self._get_static_grid_data(sim_data)

        nx = int(grid_data["nx"])
        ny = int(grid_data["ny"])
        nz = int(grid_data["nz"])

        if axis == "i":
            max_layer = nx
        elif axis == "j":
            max_layer = ny
        else:
            max_layer = nz

        if layer_index0 < 0 or layer_index0 >= max_layer:
            raise IndexError(
                f"{axis.upper()} 层号越界: 当前={layer_index}, "
                f"有效范围={1 if index_base == 1 else 0} ~ "
                f"{max_layer if index_base == 1 else max_layer - 1}"
            )

        values = self._get_static_property_values(
            sim_data,
            canonical_key,
        )

        mask = self._build_valid_property_mask(
            grid_data=grid_data,
            values=values,
            axis=axis,
            layer_index0=layer_index0,
            null_value=self._get_null_value(sim_data),
        )

        scalar_name = self._scalar_name(canonical_key)

        grid = self._build_corner_point_property_grid(
            grid_data=grid_data,
            values=values,
            mask=mask,
            scalar_name=scalar_name,
        )

        title = (
            f"{self._scalar_bar_title(canonical_key)} "
            f"{axis.upper()}={layer_index0 + 1}"
        )

        return self._render_grid(
            grid=grid,
            property_key=canonical_key,
            scalar_name=scalar_name,
            title=title,
            axis=axis,
            layer_index0=layer_index0,
            render_now=render_now,
        )

    def _get_static_grid_data(self, sim_data) -> Dict[str, Any]:
        grid_data = getattr(
            sim_data,
            "static_grid_data",
            None,
        )

        if not isinstance(grid_data, dict):
            raise ValueError(
                "sim_data.static_grid_data 不存在。"
                "请先调用 attach_static_property_preview_data_from_files() "
                "或者手动执行 sim_data.static_grid_data = parse_grid(grid_file)。"
            )

        required = ["nx", "ny", "nz", "coord", "zcorn", "actnum"]

        missing = [
            key for key in required
            if key not in grid_data
        ]

        if missing:
            raise ValueError(
                f"sim_data.static_grid_data 缺少字段: {missing}"
            )

        return grid_data

    def _get_static_property_values(
        self,
        sim_data,
        property_key: str,
    ) -> np.ndarray:
        canonical_key = normalize_static_property_key(property_key)
        spec = STATIC_PROPERTY_SPECS[canonical_key]

        static_properties = getattr(
            sim_data,
            "static_properties",
            None,
        )

        if not isinstance(static_properties, dict):
            raise ValueError(
                "sim_data.static_properties 不存在。"
                "请先调用 attach_static_property_preview_data_from_files() "
                "或者手动执行 sim_data.static_properties = {...}。"
            )

        candidates = [
            canonical_key,
            spec["internal_key"],
            canonical_key.lower(),
            spec["internal_key"].lower(),
        ]

        values = None

        for key in candidates:
            if key in static_properties:
                values = static_properties[key]
                break

        if values is None:
            raise KeyError(
                f"静态属性 {property_key!r} 不存在。"
                f"当前已有属性: {list(static_properties.keys())}"
            )

        values = np.asarray(
            values,
            dtype=np.float64,
        )

        return values

    @staticmethod
    def _get_null_value(sim_data) -> float:
        return float(
            getattr(
                sim_data,
                "static_property_null_value",
                99999.0,
            )
        )

    def _build_valid_property_mask(
        self,
        grid_data: Dict[str, Any],
        values: np.ndarray,
        axis: Optional[str],
        layer_index0: Optional[int],
        null_value: float,
    ) -> np.ndarray:
        nx = int(grid_data["nx"])
        ny = int(grid_data["ny"])
        nz = int(grid_data["nz"])
        total = nx * ny * nz

        if values.size != total:
            raise ValueError(
                f"属性数组长度不匹配: values={values.size}, grid={total}"
            )

        actnum = np.asarray(
            grid_data.get(
                "actnum",
                np.ones(total, dtype=np.int32),
            ),
            dtype=np.int32,
        )

        if actnum.size != total:
            actnum = np.ones(
                total,
                dtype=np.int32,
            )

        mask = (
            (actnum == 1)
            & np.isfinite(values)
            & (np.abs(values - float(null_value)) > 1e-12)
        )

        if axis is None:
            return mask

        axis = axis.lower()

        layer_mask = np.zeros(
            total,
            dtype=bool,
        )

        for k in range(nz):
            for j in range(ny):
                for i in range(nx):
                    cell_index = self._cell_index(
                        i=i,
                        j=j,
                        k=k,
                        nx=nx,
                        ny=ny,
                    )

                    if axis == "i":
                        inside = i == layer_index0
                    elif axis == "j":
                        inside = j == layer_index0
                    else:
                        inside = k == layer_index0

                    if inside:
                        layer_mask[cell_index] = True

        return mask & layer_mask

    def _build_corner_point_property_grid(
        self,
        grid_data: Dict[str, Any],
        values: np.ndarray,
        mask: np.ndarray,
        scalar_name: str,
    ) -> Optional[pv.UnstructuredGrid]:
        nx = int(grid_data["nx"])
        ny = int(grid_data["ny"])
        nz = int(grid_data["nz"])

        total = nx * ny * nz

        coord = np.asarray(
            grid_data["coord"],
            dtype=np.float64,
        )

        zcorn = np.asarray(
            grid_data["zcorn"],
            dtype=np.float64,
        )

        if coord.size != 6 * (nx + 1) * (ny + 1):
            raise ValueError(
                f"COORD 数量不匹配: 当前={coord.size}, "
                f"期望={6 * (nx + 1) * (ny + 1)}"
            )

        if zcorn.size != 8 * total:
            raise ValueError(
                f"ZCORN 数量不匹配: 当前={zcorn.size}, "
                f"期望={8 * total}"
            )

        if mask.size != total:
            raise ValueError(
                f"mask 长度不匹配: 当前={mask.size}, 期望={total}"
            )

        selected_cell_indices = np.flatnonzero(mask)

        if selected_cell_indices.size == 0:
            return None

        points = []
        cells = []
        cell_values = []

        for cell_index in selected_cell_indices:
            k = int(cell_index // (nx * ny))
            rem = int(cell_index % (nx * ny))
            j = int(rem // nx)
            i = int(rem % nx)

            cell_points = self._corner_point_cell_points(
                coord=coord,
                zcorn=zcorn,
                nx=nx,
                ny=ny,
                i=i,
                j=j,
                k=k,
            )

            if cell_points is None:
                continue

            base = len(points)

            points.extend(cell_points)

            cells.extend(
                [
                    8,
                    base + 0,
                    base + 1,
                    base + 2,
                    base + 3,
                    base + 4,
                    base + 5,
                    base + 6,
                    base + 7,
                ]
            )

            cell_values.append(
                float(values[cell_index])
            )

        if not points or not cell_values:
            return None

        points_array = np.asarray(
            points,
            dtype=np.float64,
        )

        cells_array = np.asarray(
            cells,
            dtype=np.int64,
        )

        cell_types = np.full(
            len(cell_values),
            pv.CellType.HEXAHEDRON,
            dtype=np.uint8,
        )

        grid = pv.UnstructuredGrid(
            cells_array,
            cell_types,
            points_array,
        )

        grid.cell_data[scalar_name] = np.asarray(
            cell_values,
            dtype=np.float64,
        )

        return grid

    def _corner_point_cell_points(
        self,
        coord: np.ndarray,
        zcorn: np.ndarray,
        nx: int,
        ny: int,
        i: int,
        j: int,
        k: int,
    ):
        try:
            z000 = self._zcorn_value(zcorn, nx, ny, i, j, k, 0, 0, 0)
            z100 = self._zcorn_value(zcorn, nx, ny, i, j, k, 1, 0, 0)
            z110 = self._zcorn_value(zcorn, nx, ny, i, j, k, 1, 1, 0)
            z010 = self._zcorn_value(zcorn, nx, ny, i, j, k, 0, 1, 0)

            z001 = self._zcorn_value(zcorn, nx, ny, i, j, k, 0, 0, 1)
            z101 = self._zcorn_value(zcorn, nx, ny, i, j, k, 1, 0, 1)
            z111 = self._zcorn_value(zcorn, nx, ny, i, j, k, 1, 1, 1)
            z011 = self._zcorn_value(zcorn, nx, ny, i, j, k, 0, 1, 1)

            p000 = self._pillar_point_at_z(coord, nx, i,     j,     z000)
            p100 = self._pillar_point_at_z(coord, nx, i + 1, j,     z100)
            p110 = self._pillar_point_at_z(coord, nx, i + 1, j + 1, z110)
            p010 = self._pillar_point_at_z(coord, nx, i,     j + 1, z010)

            p001 = self._pillar_point_at_z(coord, nx, i,     j,     z001)
            p101 = self._pillar_point_at_z(coord, nx, i + 1, j,     z101)
            p111 = self._pillar_point_at_z(coord, nx, i + 1, j + 1, z111)
            p011 = self._pillar_point_at_z(coord, nx, i,     j + 1, z011)

            cell_points = [
                p000,
                p100,
                p110,
                p010,
                p001,
                p101,
                p111,
                p011,
            ]

            if not np.isfinite(
                np.asarray(
                    cell_points,
                    dtype=np.float64,
                )
            ).all():
                return None

            return cell_points

        except Exception:
            return None

    @staticmethod
    def _pillar_point_at_z(
        coord: np.ndarray,
        nx: int,
        i_pillar: int,
        j_pillar: int,
        z: float,
    ) -> Tuple[float, float, float]:
        pillar_index = j_pillar * (nx + 1) + i_pillar
        base = pillar_index * 6

        x0 = float(coord[base + 0])
        y0 = float(coord[base + 1])
        z0 = float(coord[base + 2])

        x1 = float(coord[base + 3])
        y1 = float(coord[base + 4])
        z1 = float(coord[base + 5])

        z = float(z)

        dz = z1 - z0

        if abs(dz) < 1e-12:
            return (
                x0,
                y0,
                z,
            )

        t = (z - z0) / dz

        x = x0 + t * (x1 - x0)
        y = y0 + t * (y1 - y0)

        return (
            float(x),
            float(y),
            float(z),
        )

    @staticmethod
    def _zcorn_value(
        zcorn: np.ndarray,
        nx: int,
        ny: int,
        i: int,
        j: int,
        k: int,
        ii: int,
        jj: int,
        kk: int,
    ) -> float:
        index = (
            ((2 * k + kk) * (2 * ny) + (2 * j + jj))
            * (2 * nx)
            + (2 * i + ii)
        )

        return float(zcorn[index])

    @staticmethod
    def _cell_index(
        i: int,
        j: int,
        k: int,
        nx: int,
        ny: int,
    ) -> int:
        return int(k * nx * ny + j * nx + i)

    def _render_grid(
        self,
        grid: Optional[pv.UnstructuredGrid],
        property_key: str,
        scalar_name: str,
        title: str,
        axis: Optional[str],
        layer_index0: Optional[int],
        render_now: bool,
    ):
        self.clear(render_now=False)

        if grid is None or grid.n_cells == 0:
            if render_now:
                self._render()
            return None

        values = np.asarray(
            grid.cell_data[scalar_name],
            dtype=np.float64,
        )

        clim = self._safe_clim(values)

        surface = grid.extract_surface()

        try:
            surface = surface.compute_normals(
                consistent_normals=True,
                auto_orient_normals=True,
            )
        except Exception:
            pass

        self.actor = self.plotter.add_mesh(
            surface,
            scalars=scalar_name,
            cmap=get_bright_jet_cmap(),
            clim=clim,
            opacity=STATIC_PROPERTY_OPACITY,
            show_edges=STATIC_PROPERTY_SHOW_EDGES,
            edge_color=STATIC_PROPERTY_EDGE_COLOR,
            line_width=STATIC_PROPERTY_EDGE_LINE_WIDTH,
            show_scalar_bar=False,
            lighting=STATIC_PROPERTY_LIGHTING,
            smooth_shading=STATIC_PROPERTY_SMOOTH_SHADING,
            ambient=STATIC_PROPERTY_AMBIENT,
            diffuse=STATIC_PROPERTY_DIFFUSE,
            specular=STATIC_PROPERTY_SPECULAR,
            interpolate_before_map=STATIC_PROPERTY_INTERPOLATE_BEFORE_MAP,
            render=False,
        )

        self._force_actor_unlit(self.actor)

        self.scalar_bar_actor = self._replace_scalar_bar(
            title=title,
            render=False,
        )

        self.scalar_bar_title = title

        self.current_grid = grid
        self.current_property_key = property_key
        self.current_axis = axis
        self.current_layer_index = layer_index0

        self._reset_camera_to_grid(surface)

        if render_now:
            self._render()

        return self.actor

    @staticmethod
    def _safe_clim(values: np.ndarray) -> Tuple[float, float]:
        finite_values = values[
            np.isfinite(values)
        ]

        if finite_values.size == 0:
            return (
                0.0,
                1.0,
            )

        vmin = float(
            np.min(finite_values)
        )

        vmax = float(
            np.max(finite_values)
        )

        if abs(vmax - vmin) < 1e-12:
            delta = max(
                abs(vmin) * 0.05,
                1e-6,
            )

            return (
                vmin - delta,
                vmax + delta,
            )

        return (
            vmin,
            vmax,
        )

    def _reset_camera_to_grid(self, grid):
        try:
            self.plotter.reset_camera()
            self.plotter.reset_camera_clipping_range()
        except Exception:
            pass

    @staticmethod
    def _scalar_name(property_key: str) -> str:
        canonical_key = normalize_static_property_key(property_key)
        return f"Static_{canonical_key}"

    @staticmethod
    def _scalar_bar_title(property_key: str) -> str:
        canonical_key = normalize_static_property_key(property_key)
        spec = STATIC_PROPERTY_SPECS[canonical_key]

        return spec.get(
            "label",
            canonical_key,
        )

    def _force_actor_unlit(self, actor):
        if actor is None:
            return

        try:
            prop = actor.GetProperty()

            if prop is not None:
                prop.LightingOff()
                prop.SetAmbient(1.0)
                prop.SetDiffuse(0.0)
                prop.SetSpecular(0.0)
                prop.SetInterpolationToFlat()

        except Exception:
            pass

    def _replace_scalar_bar(
        self,
        title: str,
        render: bool = False,
    ):
        self._remove_scalar_bar()

        kwargs = dict(
            title=title,
            position_x=STATIC_PROPERTY_SCALAR_BAR_ARGS["position_x"],
            position_y=STATIC_PROPERTY_SCALAR_BAR_ARGS["position_y"],
            width=STATIC_PROPERTY_SCALAR_BAR_ARGS["width"],
            height=STATIC_PROPERTY_SCALAR_BAR_ARGS["height"],
            label_font_size=STATIC_PROPERTY_SCALAR_BAR_ARGS["label_font_size"],
            title_font_size=STATIC_PROPERTY_SCALAR_BAR_ARGS["title_font_size"],
            color=STATIC_PROPERTY_SCALAR_BAR_ARGS["color"],
            vertical=STATIC_PROPERTY_SCALAR_BAR_ARGS["vertical"],
        )

        try:
            scalar_bar = self.plotter.add_scalar_bar(
                **kwargs,
                render=render,
            )

        except TypeError:
            scalar_bar = self.plotter.add_scalar_bar(
                **kwargs,
            )

        self.scalar_bar_title = title
        self.scalar_bar_actor = scalar_bar

        return scalar_bar

    def _remove_scalar_bar(self):
        if not self.scalar_bar_title:
            self.scalar_bar_actor = None
            return

        try:
            self.plotter.remove_scalar_bar(
                self.scalar_bar_title,
                render=False,
            )

        except Exception:
            try:
                self.plotter.remove_scalar_bar(
                    title=self.scalar_bar_title,
                    render=False,
                )

            except Exception:
                try:
                    self.plotter.remove_scalar_bar(
                        render=False,
                    )

                except Exception:
                    pass

        self.scalar_bar_title = None
        self.scalar_bar_actor = None

    def _remove_actor(self, actor):
        if actor is None:
            return

        if hasattr(self.host, "_remove_actor"):
            try:
                self.host._remove_actor(actor)
                return
            except Exception:
                pass

        try:
            self.plotter.remove_actor(
                actor,
                render=False,
            )
        except Exception:
            pass

    def _render(self):
        if hasattr(self.host, "_render"):
            self.host._render()
        else:
            self.plotter.render()