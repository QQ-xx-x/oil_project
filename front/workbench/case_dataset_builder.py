# -*- coding: utf-8 -*-
"""从 CaseData 输入文件构建标准 case_dataset 数据包。"""

import argparse
import copy
import hashlib
import json
import os
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone

import numpy as np

from front.uniform_parser import (
    parse_config,
    parse_dfn,
    parse_grid,
    parse_property,
    parse_wells,
)

from .case_data_parser import parse_case_data
from .keyword_file_parser import parse_keyword_array
from .case_dataset_schema import (
    ARRAYS_FILE,
    CASE_SECTIONS_FILE,
    CONFIG_FILE,
    DEFAULT_NULL_VALUE,
    DFN_FILE,
    FRACTURE_FILE_KEY,
    GRID_ARRAYS,
    GRID_FILE_KEY,
    MANIFEST_FILE,
    MASK_ACTIVE_KEY,
    MASK_PREFIX,
    PROPERTY_ARRAYS,
    RAW_DIR,
    REQUIRED_FILE_KEYS,
    SCHEMA_VERSION,
    VALIDATION_FILE,
    WELLS_FILE,
    WR_PROPERTY_FILE_KEYS,
)
from .project_state import (
    MODEL_TYPE_WR,
    WR_INPUT_MODE_CONSTANT,
    WR_INPUT_MODE_FILE,
    WR_INPUT_MODE_MIXED,
    normalize_model_config,
)


@dataclass
class CaseDatasetBuildResult:
    """构建完成后的轻量结果对象。"""

    output_dir: str
    manifest_path: str
    manifest: dict = field(default_factory=dict)
    validation: dict = field(default_factory=dict)

    def to_dict(self):
        return {
            "output_dir": self.output_dir,
            "manifest_path": self.manifest_path,
            "validation": dict(self.validation),
            "manifest": dict(self.manifest),
        }


class CaseDatasetBuildError(ValueError):
    """CaseData 标准数据包无法构建时抛出。"""


def build_case_dataset(case_data_path, output_dir, include_raw=True,
                       null_value=DEFAULT_NULL_VALUE, model_config=None,
                       business_overrides=None):
    """把 CaseData 和其引用文件保存为标准 case_dataset 目录。

    这个函数尽量生成完整诊断信息。除 CaseData 主文件不存在外，其余文件缺失或解析失败
    会写入 validation.json，并继续输出已经能生成的部分数据。
    """
    case_data_path = os.path.abspath(case_data_path or "")
    output_dir = os.path.abspath(output_dir or "")
    if not case_data_path:
        raise CaseDatasetBuildError("CaseData 路径为空")
    if not os.path.exists(case_data_path):
        raise CaseDatasetBuildError(f"CaseData 文件不存在: {case_data_path}")
    if not output_dir:
        raise CaseDatasetBuildError("输出目录为空")

    os.makedirs(output_dir, exist_ok=True)
    validation = _new_validation()
    model_config = normalize_model_config(model_config)
    business_overrides = copy.deepcopy(dict(business_overrides or {}))
    keyword_file_sources = dict(
        business_overrides.get("keyword_file_sources") or {})
    _record_model_config_validation(validation, model_config)

    case_data = parse_case_data(case_data_path)
    for error in case_data.errors:
        _add_warning(validation, f"CaseData UI 解析警告: {error}")

    files = _collect_file_paths(case_data)
    config = _parse_config(case_data_path, validation)
    hydraulic_override = business_overrides.get("hydraulic_fractures")
    if isinstance(hydraulic_override, dict):
        config["hydraulic_fractures"] = copy.deepcopy(hydraulic_override)
        _set_check(
            validation, "hydraulic_fracture_business_data", True,
            f"{int(hydraulic_override.get('count') or 0)} fractures")
    raw_copies = _copy_raw_files(
        case_data_path, files, output_dir, include_raw, validation)

    arrays = {}
    array_summary = {}
    property_edits = business_overrides.get("property_edits") or {}
    grid_summary = _parse_grid_arrays(
        files.get(GRID_FILE_KEY),
        arrays,
        validation,
        actnum_file=files.get("actnum_file"),
        actnum_edits=property_edits.get("actnum"),
        keyword_file_sources=keyword_file_sources,
    )
    active_mask = arrays.get(MASK_ACTIVE_KEY)

    _parse_property_arrays(
        files,
        arrays,
        array_summary,
        active_mask,
        grid_summary.get("total_cell_count"),
        null_value,
        validation,
        model_config,
        grid_shape=(
            grid_summary.get("nx"),
            grid_summary.get("ny"),
            grid_summary.get("nz"),
        ),
        property_edits=property_edits,
        keyword_file_sources=keyword_file_sources,
    )

    dfn_payload, dfn_summary = _parse_dfn_payload(files, validation)
    natural_override = business_overrides.get("natural_fractures")
    if isinstance(natural_override, dict):
        dfn_payload = copy.deepcopy(natural_override)
        fractures = [
            row for row in dfn_payload.get("fractures") or []
            if isinstance(row, dict)
        ]
        dfn_payload["fracture_count"] = len(fractures)
        dfn_summary = {
            **dict(dfn_summary or {}),
            "available": bool(fractures),
            "source_key": "business_override",
            "fracture_count": len(fractures),
            "parsed_fracture_count": len(fractures),
            "bbox_min": dfn_payload.get("bbox_min"),
            "bbox_max": dfn_payload.get("bbox_max"),
        }
        _set_check(
            validation, "dfn_business_data", bool(fractures),
            f"{len(fractures)} fractures")
    wells_override = business_overrides.get("wells")
    if isinstance(wells_override, dict):
        wells_payload = copy.deepcopy(wells_override)
        wells_summary = dict(wells_payload.get("summary") or {})
        wells_summary["available"] = bool(wells_payload.get("wells"))
        _set_check(
            validation, "wells_business_data", True,
            f"{int(wells_summary.get('well_count') or 0)} wells")
    else:
        wells_payload, wells_summary = _parse_wells_payload(
            case_data_path, config, files, validation)

    _write_json(os.path.join(output_dir, CONFIG_FILE), {
        "schema_version": SCHEMA_VERSION,
        "model_config": model_config,
        "config": config,
    })
    _write_json(os.path.join(output_dir, CASE_SECTIONS_FILE), {
        "schema_version": SCHEMA_VERSION,
        "source_case_file": case_data_path,
        "case_data": case_data.to_dict(),
    })
    _write_json(os.path.join(output_dir, DFN_FILE), {
        "schema_version": SCHEMA_VERSION,
        "dfn": dfn_payload,
    })
    _write_json(os.path.join(output_dir, WELLS_FILE), {
        "schema_version": SCHEMA_VERSION,
        "wells": wells_payload,
    })
    _write_json(os.path.join(output_dir, VALIDATION_FILE), validation)

    arrays_path = os.path.join(output_dir, ARRAYS_FILE)
    if arrays:
        np.savez_compressed(arrays_path, **arrays)
    else:
        np.savez_compressed(arrays_path)
        _add_warning(validation, "未写入任何数组，arrays.npz 为空")
        _write_json(os.path.join(output_dir, VALIDATION_FILE), validation)

    source_files = _build_source_file_records(case_data_path, files, raw_copies)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_case_file": case_data_path,
        "config_file": CONFIG_FILE,
        "case_sections_file": CASE_SECTIONS_FILE,
        "arrays_file": ARRAYS_FILE,
        "dfn_file": DFN_FILE,
        "wells_file": WELLS_FILE,
        "validation_file": VALIDATION_FILE,
        "raw_dir": RAW_DIR if include_raw else "",
        "null_value": float(null_value),
        "valid_cell_rule": "grid_actnum == 1 and value != 99999",
        "model_config": model_config,
        "grid": grid_summary,
        "arrays": array_summary,
        "dfn": dfn_summary,
        "wells": wells_summary,
        "source_files": source_files,
        "keyword_file_sources": _keyword_source_manifest(
            keyword_file_sources),
        "validation": {
            "ok": bool(validation.get("ok")),
            "error_count": len(validation.get("errors") or []),
            "warning_count": len(validation.get("warnings") or []),
        },
    }
    _write_json(os.path.join(output_dir, MANIFEST_FILE), manifest)
    return CaseDatasetBuildResult(
        output_dir=output_dir,
        manifest_path=os.path.join(output_dir, MANIFEST_FILE),
        manifest=manifest,
        validation=validation,
    )


def load_case_dataset_manifest(dataset_dir):
    """读取 case_dataset 的 manifest.json。"""
    manifest_path = os.path.join(os.path.abspath(dataset_dir), MANIFEST_FILE)
    with open(manifest_path, "r", encoding="utf-8") as file:
        return json.load(file)


def _new_validation():
    return {
        "schema_version": SCHEMA_VERSION,
        "ok": True,
        "errors": [],
        "warnings": [],
        "checks": {},
    }


def _add_error(validation, message):
    validation["ok"] = False
    validation["errors"].append(str(message))


def _add_warning(validation, message):
    validation["warnings"].append(str(message))


def _set_check(validation, name, ok, detail=None):
    validation["checks"][name] = {
        "ok": bool(ok),
        "detail": detail or "",
    }


def _parse_config(case_data_path, validation):
    try:
        config = parse_config(case_data_path)
    except Exception as exc:
        _add_error(validation, f"config 解析失败: {exc}")
        return {}
    _set_check(validation, "config_parse_ok", True)
    return config


def _collect_file_paths(case_data):
    files = {}
    for section in case_data.sections:
        for keyword in section.keywords:
            if keyword.is_file_ref:
                files[keyword.key] = os.path.abspath(keyword.file_path or "")
    return files


def _replay_property_edits(values, records, grid_shape, property_key,
                           null_value, validation):
    """Replay persisted UI edits on one I-fast property array."""
    records = list(records or [])
    if not records:
        return values
    try:
        nx, ny, nz = (int(value or 0) for value in (grid_shape or (0, 0, 0)))
    except (TypeError, ValueError):
        nx = ny = nz = 0
    expected = nx * ny * nz
    if not expected or len(values) != expected:
        _add_error(
            validation,
            f"{property_key} 编辑无法应用：属性数量 {len(values)} 与网格维度不一致",
        )
        return values

    result = values.copy()
    allowed = {"set", "add", "subtract", "multiply", "divide"}
    for index, record in enumerate(records, 1):
        try:
            if not isinstance(record, dict):
                raise ValueError("编辑记录格式无效")
            operation = str(record.get("operation") or "set")
            if operation not in allowed:
                raise ValueError(f"不支持的操作 {operation}")
            if property_key == "actnum" and operation != "set":
                raise ValueError("ACTNUM 只支持赋值")
            value = float(record.get("value", 0.0))
            if not np.isfinite(value):
                raise ValueError("操作数不是有效数字")
            if operation == "divide" and value == 0.0:
                raise ValueError("除数不能为 0")

            scope = str(record.get("scope") or "all")
            if scope == "all":
                bounds = (1, nx, 1, ny, 1, nz)
            elif scope in {"layer", "box"}:
                bounds = (
                    int(record.get("x1", 1)), int(record.get("x2", nx)),
                    int(record.get("y1", 1)), int(record.get("y2", ny)),
                    int(record.get("z1", 1)), int(record.get("z2", nz)),
                )
            else:
                raise ValueError(f"不支持的作用范围 {scope}")
            x1, x2, y1, y2, z1, z2 = bounds
            if not (1 <= x1 <= x2 <= nx and 1 <= y1 <= y2 <= ny
                    and 1 <= z1 <= z2 <= nz):
                raise ValueError("BOX 范围超出网格维度")

            candidate = result.copy()
            view = candidate.reshape((nz, ny, nx))[
                z1 - 1:z2, y1 - 1:y2, x1 - 1:x2]
            source = view.astype(np.float64, copy=True)
            editable = ~np.isclose(source, float(null_value))
            if operation == "set":
                source[editable] = value
            elif operation == "add":
                source[editable] += value
            elif operation == "subtract":
                source[editable] -= value
            elif operation == "multiply":
                source[editable] *= value
            elif operation == "divide":
                source[editable] /= value

            changed = source[editable]
            if not np.all(np.isfinite(changed)):
                raise ValueError("运算结果包含无效数字")
            if property_key == "actnum" and not np.all(
                    np.isin(changed, (0.0, 1.0))):
                raise ValueError("ACTNUM 只能设置为 0 或 1")
            if property_key in {"matrix_kx", "matrix_ky", "matrix_kz"} \
                    and np.any(changed < 0.0):
                raise ValueError("渗透率不能小于 0")
            if property_key == "matrix_phi" and (
                    np.any(changed < 0.0) or np.any(changed > 1.0)):
                raise ValueError("孔隙度必须位于 0 到 1 之间")
            view[...] = source.astype(view.dtype, copy=False)
            result = candidate
        except (TypeError, ValueError, OverflowError) as exc:
            _add_error(
                validation,
                f"{property_key} 第 {index} 条编辑无法应用: {exc}",
            )
            return result

    _set_check(
        validation,
        f"{property_key}_property_edits_replayed",
        True,
        f"{len(records)} edits",
    )
    return result


def _normalize_actnum_values(values):
    """Normalize ACTNUM to int8, treating the project null sentinel as inactive."""
    numbers = np.asarray(values, dtype=np.float64)
    if not np.all(np.isfinite(numbers)):
        raise ValueError("ACTNUM 数据中存在无效数值")
    numbers = numbers.copy()
    null_mask = np.isclose(numbers, 99999.0)
    numbers[null_mask] = 0.0
    if not np.all(np.isin(numbers, (0.0, 1.0))):
        raise ValueError("ACTNUM 只能包含 0、1 或空值 99999")
    return numbers.astype(np.int8), int(np.sum(null_mask))


def _parse_grid_arrays(grid_file, arrays, validation, actnum_file=None,
                       actnum_edits=None, keyword_file_sources=None):
    if not grid_file:
        _add_error(validation, "缺少 grid_file")
        _set_check(validation, "grid_file_exists", False, "缺少 grid_file")
        return {}
    if not os.path.exists(grid_file):
        _add_error(validation, f"grid_file 文件不存在: {grid_file}")
        _set_check(validation, "grid_file_exists", False, grid_file)
        return {}
    _set_check(validation, "grid_file_exists", True, grid_file)

    try:
        grid = parse_grid(grid_file)
    except Exception as exc:
        _add_error(validation, f"grid_file 解析失败: {exc}")
        _set_check(validation, "grid_parse_ok", False, str(exc))
        return {}
    _set_check(validation, "grid_parse_ok", True)

    coord = np.asarray(grid.get("coord") or [], dtype=np.float64)
    zcorn = np.asarray(grid.get("zcorn") or [], dtype=np.float64)
    try:
        actnum, grid_null_count = _normalize_actnum_values(
            grid.get("actnum") or [])
        if grid_null_count:
            _add_warning(
                validation,
                f"grid_file 的 ACTNUM 中 {grid_null_count} 个 99999 已按非活跃网格处理",
            )
    except (TypeError, ValueError, OverflowError) as exc:
        _add_error(validation, f"grid_file 的 ACTNUM 无效: {exc}")
        actnum = np.asarray([], dtype=np.int8)
    if actnum_file:
        if not os.path.exists(actnum_file):
            _add_error(validation, f"actnum_file 文件不存在: {actnum_file}")
        else:
            try:
                override, null_count = _normalize_actnum_values(
                    _parse_property_source(
                        actnum_file,
                        "actnum_file",
                        keyword_file_sources,
                    ))
                actnum = override
                _set_check(validation, "actnum_override_parse_ok", True, actnum_file)
                _record_selected_keyword_check(
                    validation, "actnum_file", keyword_file_sources)
                if null_count:
                    _add_warning(
                        validation,
                        f"actnum_file 中 {null_count} 个 99999 已按非活跃网格处理",
                    )
            except Exception as exc:
                _add_error(validation, f"actnum_file 解析失败: {exc}")
                _set_check(validation, "actnum_override_parse_ok", False, str(exc))
                _record_selected_keyword_check(
                    validation, "actnum_file", keyword_file_sources,
                    ok=False, detail=str(exc))

    nx = int(grid.get("nx") or 0)
    ny = int(grid.get("ny") or 0)
    nz = int(grid.get("nz") or 0)
    actnum = _replay_property_edits(
        actnum,
        actnum_edits,
        (nx, ny, nz),
        "actnum",
        99999.0,
        validation,
    )
    arrays[GRID_ARRAYS["coord"]] = coord
    arrays[GRID_ARRAYS["zcorn"]] = zcorn
    arrays[GRID_ARRAYS["actnum"]] = actnum
    arrays[MASK_ACTIVE_KEY] = actnum == 1

    total = int(grid.get("total_cell_count") or 0)
    if total and len(actnum) != total:
        _add_error(
            validation,
            f"grid_actnum 数量 {len(actnum)} 与 nx*ny*nz {total} 不一致",
        )
    _set_check(
        validation,
        "grid_actnum_length_match_total",
        not total or len(actnum) == total,
        f"{len(actnum)} / {total}",
    )
    return {
        "nx": nx,
        "ny": ny,
        "nz": nz,
        "total_cell_count": total,
        "coord_value_count": int(len(coord)),
        "zcorn_value_count": int(len(zcorn)),
        "actnum_value_count": int(len(actnum)),
        "active_cell_count": int(np.sum(actnum == 1)),
        "inactive_cell_count": int(np.sum(actnum == 0)),
    }


def _parse_property_arrays(files, arrays, array_summary, active_mask,
                           expected_count, null_value, validation,
                           model_config=None, grid_shape=None,
                           property_edits=None,
                           keyword_file_sources=None):
    required_file_keys = _required_file_keys(model_config)
    for file_key in required_file_keys:
        if file_key not in files:
            _add_error(validation, f"缺少必要文件关键字: {file_key}")

    all_lengths_match = True
    for file_key, array_key in PROPERTY_ARRAYS.items():
        # ACTNUM is resolved together with the grid so the active mask always
        # reflects imported and BOX-edited values.
        if file_key == "actnum_file":
            continue
        if not _should_parse_property_file(file_key, model_config):
            continue
        path = files.get(file_key)
        if not path:
            if file_key not in required_file_keys and _warn_missing_optional_file(
                    file_key, model_config):
                _add_warning(validation, f"未提供可选属性文件: {file_key}")
            continue
        if not os.path.exists(path):
            _add_error(validation, f"{file_key} 文件不存在: {path}")
            continue
        try:
            values = _parse_property_source(
                path,
                file_key,
                keyword_file_sources,
                expected_len=expected_count,
            )
            _record_selected_keyword_check(
                validation, file_key, keyword_file_sources)
        except Exception as exc:
            _add_error(validation, f"{file_key} 解析失败: {exc}")
            continue

        dtype = np.int8 if file_key == "actnum_file" else np.float64
        values_array = np.asarray(values, dtype=dtype)
        transform = None
        if dtype == np.float64:
            values_array, transform = _apply_property_transform(
                file_key, values_array, null_value)
        values_array = _replay_property_edits(
            values_array,
            (property_edits or {}).get(array_key),
            grid_shape,
            array_key,
            null_value,
            validation,
        )
        arrays[array_key] = values_array
        mask_key = f"{MASK_PREFIX}{array_key}_valid"
        valid_mask = _build_valid_mask(values_array, active_mask, null_value)
        arrays[mask_key] = valid_mask

        length_match = expected_count is None or len(values_array) == expected_count
        if not length_match:
            all_lengths_match = False
            _add_error(
                validation,
                f"{file_key} 数量 {len(values_array)} 与网格总数 {expected_count} 不一致",
            )
        array_summary[array_key] = _array_summary(
            file_key,
            path,
            values_array,
            valid_mask,
            null_value,
            expected_count,
            mask_key,
            transform,
        )

    _set_check(
        validation,
        "property_lengths_match_grid",
        all_lengths_match,
        f"expected={expected_count}",
    )


def _parse_property_source(path, file_key, keyword_file_sources=None,
                           expected_len=None):
    """Read the content keyword verified by the UI, with legacy fallback."""

    record = dict((keyword_file_sources or {}).get(file_key) or {})
    keyword = str(record.get("detected_keyword") or "").strip()
    if not keyword:
        expected = list(record.get("expected_keywords") or [])
        keyword = str(expected[0] if expected else "").strip()
    if not keyword:
        return parse_property(path, expected_len=expected_len)
    parsed = parse_keyword_array(
        path,
        (keyword,),
        expected_len=expected_len,
    )
    return list(parsed.values)


def _record_selected_keyword_check(validation, file_key,
                                   keyword_file_sources=None, *, ok=True,
                                   detail=""):
    record = dict((keyword_file_sources or {}).get(file_key) or {})
    keyword = str(record.get("detected_keyword") or "").strip()
    if keyword:
        _set_check(
            validation,
            f"{file_key}_content_keyword",
            ok,
            detail or keyword,
        )


def _keyword_source_manifest(keyword_file_sources):
    result = {}
    for file_key, source in (keyword_file_sources or {}).items():
        if not isinstance(source, dict):
            continue
        result[str(file_key)] = {
            key: copy.deepcopy(source.get(key))
            for key in (
                "source_mode",
                "value_key",
                "detected_keyword",
                "expected_keywords",
                "copied_from",
                "source_sha256",
            )
            if source.get(key) not in (None, "", [])
        }
    return result


def _record_model_config_validation(validation, model_config):
    model_type = model_config.get("model_type", "")
    wr_input_mode = model_config.get("wr_input_mode", "")
    _set_check(
        validation,
        "model_config",
        True,
        f"model_type={model_type}, wr_input_mode={wr_input_mode}",
    )
    validation["model_config"] = dict(model_config)
    if model_type == MODEL_TYPE_WR and not model_config.get("confirmed"):
        _add_warning(validation, "WR 模型方案尚未标记为已确认，请核对输入数据")


def _required_file_keys(model_config=None):
    config = normalize_model_config(model_config)
    required = list(REQUIRED_FILE_KEYS)
    if (config.get("model_type") == MODEL_TYPE_WR and
            config.get("wr_input_mode") == WR_INPUT_MODE_FILE):
        required.extend(WR_PROPERTY_FILE_KEYS)
    return tuple(required)


def _warn_missing_optional_file(file_key, model_config=None):
    config = normalize_model_config(model_config)
    if file_key not in WR_PROPERTY_FILE_KEYS:
        return True
    if config.get("model_type") != MODEL_TYPE_WR:
        return False
    return config.get("wr_input_mode") in {
        WR_INPUT_MODE_CONSTANT,
        WR_INPUT_MODE_MIXED,
    }


def _should_parse_property_file(file_key, model_config=None):
    config = normalize_model_config(model_config)
    if file_key in WR_PROPERTY_FILE_KEYS:
        return config.get("model_type") == MODEL_TYPE_WR
    return True


def _apply_property_transform(file_key, values, null_value):
    # Property files are persisted exactly as imported.  Unit conversion, if
    # needed by a downstream consumer, must not change the front-end dataset.
    return values, None


def _build_valid_mask(values, active_mask, null_value):
    valid = ~np.isclose(values.astype(np.float64), float(null_value))
    if active_mask is None:
        return valid
    combined = np.zeros(len(values), dtype=bool)
    n = min(len(values), len(active_mask))
    combined[:n] = valid[:n] & active_mask[:n]
    return combined


def _array_summary(file_key, path, values, valid_mask, null_value,
                   expected_count, mask_key, transform=None):
    float_values = values.astype(np.float64)
    null_mask = np.isclose(float_values, float(null_value))
    valid_values = float_values[valid_mask]
    summary = {
        "source_key": file_key,
        "source_path": os.path.abspath(path),
        "saved_key": PROPERTY_ARRAYS[file_key],
        "mask_key": mask_key,
        "dtype": str(values.dtype),
        "count": int(len(values)),
        "expected_count": int(expected_count or 0),
        "length_match_grid": bool(expected_count is None or len(values) == expected_count),
        "null_count": int(np.sum(null_mask)),
        "valid_count": int(np.sum(valid_mask)),
        "min_valid": _safe_float(np.min(valid_values)) if len(valid_values) else None,
        "max_valid": _safe_float(np.max(valid_values)) if len(valid_values) else None,
    }
    if transform:
        summary["transform"] = transform
    return summary


def _parse_dfn_payload(files, validation):
    dfn_key = FRACTURE_FILE_KEY if files.get(FRACTURE_FILE_KEY) else "dfn_file"
    dfn_path = files.get(dfn_key)
    if not dfn_path:
        _add_warning(validation, "未提供 fracture_file，dfn.json 将写入空值")
        return None, {"available": False}
    if not os.path.exists(dfn_path):
        _add_error(validation, f"{dfn_key} 文件不存在: {dfn_path}")
        return None, {"available": False, "source_key": dfn_key, "source_path": dfn_path}
    try:
        dfn = parse_dfn(dfn_path)
    except Exception as exc:
        _add_error(validation, f"{dfn_key} 解析失败: {exc}")
        return None, {"available": False, "source_key": dfn_key, "source_path": dfn_path}

    declared_count = int(dfn.get("fracture_count") or 0)
    parsed_count = len(dfn.get("fractures") or [])
    if declared_count and declared_count != parsed_count:
        _add_warning(
            validation,
            f"dfn 声明裂缝数 {declared_count} 与解析数量 {parsed_count} 不一致",
        )
    _set_check(validation, "dfn_parse_ok", True, dfn_path)
    return dfn, {
        "available": True,
        "source_key": dfn_key,
        "source_path": os.path.abspath(dfn_path),
        "fracture_count": declared_count,
        "parsed_fracture_count": parsed_count,
        "bbox_min": dfn.get("bbox_min"),
        "bbox_max": dfn.get("bbox_max"),
    }


def _parse_wells_payload(case_data_path, config, files, validation):
    well_config = (config.get("well", {}) if isinstance(config, dict) else {}) or {}
    track_file = _resolve_well_file(
        case_data_path, files, well_config, "well_track_file")
    completion_file = _resolve_well_file(
        case_data_path, files, well_config, "well_completion_file")

    if not track_file and not completion_file:
        _set_check(validation, "wells_parse_ok", True, "no well files provided")
        return None, {"available": False}

    if not track_file or not os.path.exists(track_file):
        _add_error(validation, f"well_track_file missing or does not exist: {track_file}")
        _set_check(validation, "well_track_file_exists", False, track_file)
        return None, {"available": False, "well_track_file": track_file}
    _set_check(validation, "well_track_file_exists", True, track_file)

    if not completion_file or not os.path.exists(completion_file):
        _add_error(validation, f"well_completion_file missing or does not exist: {completion_file}")
        _set_check(validation, "well_completion_file_exists", False, completion_file)
        return None, {"available": False, "well_completion_file": completion_file}
    _set_check(validation, "well_completion_file_exists", True, completion_file)

    try:
        wells = parse_wells(track_file, completion_file)
    except Exception as exc:
        _add_error(validation, f"wells parse failed: {exc}")
        _set_check(validation, "wells_parse_ok", False, str(exc))
        return None, {
            "available": False,
            "well_track_file": os.path.abspath(track_file),
            "well_completion_file": os.path.abspath(completion_file),
        }

    for warning in ((wells.get("validation") or {}).get("warnings") or []):
        _add_warning(validation, f"wells: {warning}")
    _set_check(validation, "wells_parse_ok", True)
    summary = dict(wells.get("summary") or {})
    summary.update({
        "available": True,
        "well_track_file": os.path.abspath(track_file),
        "well_completion_file": os.path.abspath(completion_file),
    })
    return wells, summary


def _resolve_well_file(case_data_path, files, well_config, key):
    path = files.get(key) or well_config.get(key, "")
    if not path:
        return ""
    path = str(path).strip().strip("\"'")
    if os.path.isabs(path):
        return os.path.abspath(path)
    return os.path.abspath(os.path.join(os.path.dirname(case_data_path), path))


def _copy_raw_files(case_data_path, files, output_dir, include_raw, validation):
    if not include_raw:
        return {}
    raw_dir = os.path.join(output_dir, RAW_DIR)
    os.makedirs(raw_dir, exist_ok=True)
    raw_sources = {"case_data": case_data_path}
    raw_sources.update(files)
    copied = {}
    for key, path in raw_sources.items():
        if not path or not os.path.exists(path):
            continue
        target_name = _raw_copy_name(key, path)
        target_path = os.path.join(raw_dir, target_name)
        try:
            shutil.copy2(path, target_path)
        except OSError as exc:
            _add_warning(validation, f"{key} 原始文件备份失败: {exc}")
            continue
        copied[key] = os.path.join(RAW_DIR, target_name).replace("\\", "/")
    return copied


def _raw_copy_name(key, path):
    basename = os.path.basename(path)
    safe_key = "".join(ch if ch.isalnum() or ch in "_-" else "_" for ch in key)
    return f"{safe_key}__{basename}"


def _build_source_file_records(case_data_path, files, raw_copies):
    records = {
        "case_data": _source_file_record(case_data_path, raw_copies.get("case_data", "")),
    }
    for key, path in sorted(files.items()):
        records[key] = _source_file_record(path, raw_copies.get(key, ""))
    return records


def _source_file_record(path, copied_to=""):
    record = {
        "path": os.path.abspath(path or ""),
        "exists": bool(path and os.path.exists(path)),
        "copied_to": copied_to,
    }
    if record["exists"]:
        stat = os.stat(path)
        record.update({
            "size": int(stat.st_size),
            "mtime": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
            "sha256": _sha256(path),
        })
    return record


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _json_default(value):
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    raise TypeError(f"{type(value).__name__} 不能序列化为 JSON")


def _write_json(path, payload):
    with open(path, "w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2, default=_json_default)


def main(argv=None):
    parser = argparse.ArgumentParser(description="构建 CaseData 标准数据包")
    parser.add_argument("case_data_path", help="CaseData/uniform_data.txt 路径")
    parser.add_argument("output_dir", help="case_dataset 输出目录")
    parser.add_argument(
        "--no-raw",
        action="store_true",
        help="不复制原始输入文件到 raw 目录",
    )
    args = parser.parse_args(argv)
    result = build_case_dataset(
        args.case_data_path,
        args.output_dir,
        include_raw=not args.no_raw,
    )
    print(json.dumps({
        "output_dir": result.output_dir,
        "manifest_path": result.manifest_path,
        "ok": result.validation.get("ok"),
        "error_count": len(result.validation.get("errors") or []),
        "warning_count": len(result.validation.get("warnings") or []),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
