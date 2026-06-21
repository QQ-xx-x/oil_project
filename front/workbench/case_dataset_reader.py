# -*- coding: utf-8 -*-
"""读取标准 case_dataset 数据目录。

这个模块是 UI 侧提供给算法同学参考的读取接口。算法入口只需要拿到
case_dataset 目录，内部 JSON/NPZ 文件都按该目录下的相对路径读取，不依赖
原始 CaseData 文件的绝对路径。
"""

import argparse
import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Mapping, Optional

import numpy as np

from .case_dataset_schema import (
    ARRAYS_FILE,
    CASE_SECTIONS_FILE,
    CONFIG_FILE,
    DFN_FILE,
    GRID_ARRAYS,
    MASK_ACTIVE_KEY,
    MASK_PREFIX,
    MANIFEST_FILE,
    PROPERTY_ARRAYS,
    VALIDATION_FILE,
)


class CaseDatasetReadError(ValueError):
    """case_dataset 缺失、损坏或校验失败时抛出。"""


@dataclass(frozen=True)
class CaseDatasetGrid:
    """算法侧需要的角点网格数组。"""

    nx: int
    ny: int
    nz: int
    coord: np.ndarray
    zcorn: np.ndarray
    actnum: np.ndarray
    active_mask: np.ndarray

    @property
    def total_cell_count(self):
        total = int(self.nx) * int(self.ny) * int(self.nz)
        return total if total > 0 else int(len(self.actnum))

    @property
    def active_cell_count(self):
        return int(np.sum(self.active_mask))

    @property
    def inactive_cell_count(self):
        if len(self.actnum):
            return int(np.sum(self.actnum == 0))
        return max(0, self.total_cell_count - self.active_cell_count)


@dataclass
class CaseDataset:
    """已经读入内存的 case_dataset。"""

    dataset_dir: str
    manifest: Dict[str, Any]
    config: Dict[str, Any]
    case_sections: Dict[str, Any]
    validation: Dict[str, Any]
    dfn: Dict[str, Any]
    arrays: Dict[str, np.ndarray] = field(default_factory=dict)
    grid: CaseDatasetGrid = None
    properties: Dict[str, np.ndarray] = field(default_factory=dict)
    valid_masks: Dict[str, np.ndarray] = field(default_factory=dict)

    def array(self, key, required=True):
        """按 arrays.npz 内部键名读取数组。"""
        if key in self.arrays:
            return self.arrays[key]
        if required:
            raise CaseDatasetReadError(f"数组不存在: {key}")
        return None

    def property_array(self, key, required=True):
        """按标准属性名或 CaseData 文件关键字读取属性数组。"""
        normalized = self._normalize_property_key(key)
        if normalized in self.properties:
            return self.properties[normalized]
        if required:
            raise CaseDatasetReadError(f"属性数组不存在: {key}")
        return None

    def valid_mask(self, key, required=True):
        """读取属性数组对应的有效值掩码。"""
        normalized = self._normalize_property_key(key)
        if normalized in self.valid_masks:
            return self.valid_masks[normalized]
        if required:
            raise CaseDatasetReadError(f"有效值掩码不存在: {key}")
        return None

    def valid_values(self, key):
        """返回跳过 ACTNUM=0 和 value=99999 后的有效属性值。"""
        values = self.property_array(key)
        mask = self.valid_mask(key)
        n = min(len(values), len(mask))
        return values[:n][mask[:n]]

    def to_algorithm_inputs(self):
        """返回一份面向 pybind 调用的结构化输入对象。"""
        return {
            "dataset_dir": self.dataset_dir,
            "config": self.config,
            "grid": {
                "nx": self.grid.nx,
                "ny": self.grid.ny,
                "nz": self.grid.nz,
                "coord": self.grid.coord,
                "zcorn": self.grid.zcorn,
                "actnum": self.grid.actnum,
                "active_mask": self.grid.active_mask,
            },
            "properties": self.properties,
            "valid_masks": self.valid_masks,
            "dfn": self.dfn,
        }

    def summary(self):
        """返回适合日志或调试打印的轻量摘要。"""
        validation_block = self.manifest.get("validation", {}) or {}
        return {
            "dataset_dir": self.dataset_dir,
            "schema_version": self.manifest.get("schema_version", ""),
            "validation_ok": bool(self.validation.get("ok")),
            "error_count": len(self.validation.get("errors") or []),
            "warning_count": len(self.validation.get("warnings") or []),
            "manifest_error_count": validation_block.get("error_count"),
            "manifest_warning_count": validation_block.get("warning_count"),
            "grid": {
                "nx": self.grid.nx,
                "ny": self.grid.ny,
                "nz": self.grid.nz,
                "total_cell_count": self.grid.total_cell_count,
                "active_cell_count": self.grid.active_cell_count,
                "inactive_cell_count": self.grid.inactive_cell_count,
                "coord_value_count": int(len(self.grid.coord)),
                "zcorn_value_count": int(len(self.grid.zcorn)),
                "actnum_value_count": int(len(self.grid.actnum)),
            },
            "array_count": len(self.arrays),
            "property_count": len(self.properties),
            "properties": {
                key: {
                    "count": int(len(value)),
                    "valid_count": int(np.sum(self.valid_masks[key]))
                    if key in self.valid_masks else None,
                }
                for key, value in sorted(self.properties.items())
            },
            "dfn_fracture_count": _dfn_fracture_count(self.dfn),
        }

    def _normalize_property_key(self, key):
        return PROPERTY_ARRAYS.get(key, key)


def load_case_dataset(dataset_dir, strict=True):
    """读取 case_dataset 目录。

    strict=True 时，如果 validation.json 已记录错误，会直接抛出异常；警告不阻断读取。
    """
    dataset_dir = os.path.abspath(dataset_dir or "")
    if not dataset_dir:
        raise CaseDatasetReadError("case_dataset 目录为空")
    if not os.path.isdir(dataset_dir):
        raise CaseDatasetReadError(f"case_dataset 目录不存在: {dataset_dir}")

    manifest_path = os.path.join(dataset_dir, MANIFEST_FILE)
    manifest = _read_json(manifest_path)

    config_payload = _read_json(_dataset_file_path(
        dataset_dir, manifest, "config_file", CONFIG_FILE))
    case_sections_payload = _read_json(_dataset_file_path(
        dataset_dir, manifest, "case_sections_file", CASE_SECTIONS_FILE))
    dfn_payload = _read_json(_dataset_file_path(
        dataset_dir, manifest, "dfn_file", DFN_FILE))
    validation = _read_json(_dataset_file_path(
        dataset_dir, manifest, "validation_file", VALIDATION_FILE))
    if strict and validation.get("errors"):
        raise CaseDatasetReadError(
            "case_dataset 校验存在错误: " + "; ".join(validation.get("errors") or []))

    arrays_path = _dataset_file_path(dataset_dir, manifest, "arrays_file", ARRAYS_FILE)
    arrays = _read_npz_arrays(arrays_path)
    grid = _build_grid(manifest, arrays)
    properties, valid_masks = _split_property_arrays(arrays)

    return CaseDataset(
        dataset_dir=dataset_dir,
        manifest=manifest,
        config=config_payload.get("config", config_payload),
        case_sections=case_sections_payload,
        validation=validation,
        dfn=dfn_payload.get("dfn", dfn_payload),
        arrays=arrays,
        grid=grid,
        properties=properties,
        valid_masks=valid_masks,
    )


def load_case_dataset_manifest(dataset_dir):
    """只读取 manifest.json，用于快速查看数据包元信息。"""
    dataset_dir = os.path.abspath(dataset_dir or "")
    return _read_json(os.path.join(dataset_dir, MANIFEST_FILE))


def _dataset_file_path(dataset_dir, manifest, field_name, fallback_name):
    value = manifest.get(field_name) or fallback_name
    if os.path.isabs(value):
        return value
    return os.path.join(dataset_dir, value)


def _read_json(path):
    if not os.path.exists(path):
        raise CaseDatasetReadError(f"文件不存在: {path}")
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def _read_npz_arrays(path):
    if not os.path.exists(path):
        raise CaseDatasetReadError(f"数组文件不存在: {path}")
    with np.load(path, allow_pickle=False) as npz_file:
        return {name: np.asarray(npz_file[name]) for name in npz_file.files}


def _build_grid(manifest, arrays):
    missing = [
        key for key in (
            GRID_ARRAYS["coord"],
            GRID_ARRAYS["zcorn"],
            GRID_ARRAYS["actnum"],
            MASK_ACTIVE_KEY,
        )
        if key not in arrays
    ]
    if missing:
        raise CaseDatasetReadError(f"网格数组缺失: {', '.join(missing)}")
    grid_summary = manifest.get("grid", {}) or {}
    return CaseDatasetGrid(
        nx=int(grid_summary.get("nx") or 0),
        ny=int(grid_summary.get("ny") or 0),
        nz=int(grid_summary.get("nz") or 0),
        coord=arrays[GRID_ARRAYS["coord"]],
        zcorn=arrays[GRID_ARRAYS["zcorn"]],
        actnum=arrays[GRID_ARRAYS["actnum"]],
        active_mask=arrays[MASK_ACTIVE_KEY].astype(bool),
    )


def _split_property_arrays(arrays):
    properties = {}
    valid_masks = {}
    property_keys = set(PROPERTY_ARRAYS.values())
    for key in property_keys:
        if key in arrays:
            properties[key] = arrays[key]
        mask_key = f"{MASK_PREFIX}{key}_valid"
        if mask_key in arrays:
            valid_masks[key] = arrays[mask_key].astype(bool)
    return properties, valid_masks


def _dfn_fracture_count(dfn_payload):
    if not isinstance(dfn_payload, Mapping):
        return 0
    if dfn_payload.get("fracture_count") is not None:
        return int(dfn_payload.get("fracture_count") or 0)
    return len(dfn_payload.get("fractures") or [])


def _json_default(value):
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    raise TypeError(f"{type(value).__name__} 不能序列化为 JSON")


def main(argv: Optional[Iterable[str]] = None):
    parser = argparse.ArgumentParser(description="读取并检查 case_dataset 数据目录")
    parser.add_argument("dataset_dir", help="case_dataset 目录")
    parser.add_argument(
        "--allow-invalid",
        action="store_true",
        help="validation.json 存在错误时仍尝试读取",
    )
    args = parser.parse_args(argv)
    dataset = load_case_dataset(args.dataset_dir, strict=not args.allow_invalid)
    print(json.dumps(dataset.summary(), ensure_ascii=False, indent=2, default=_json_default))


if __name__ == "__main__":
    main()
