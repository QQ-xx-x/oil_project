# -*- coding: utf-8 -*-
"""轻量 .oilproj 工程文件读写。

第一阶段工程文件只保存 UI 状态和数据目录引用，不打包 case_dataset 大文件。
算法仍然读取 case_dataset 目录，工程文件只负责让 UI 找回这个目录。
"""

import copy
import json
import os
from datetime import datetime, timezone

from .case_dataset_reader import CaseDatasetReadError, load_case_dataset
from .case_data_parser import parse_case_data
from .project_state import ProjectState


PROJECT_SCHEMA_VERSION = "oil_project_v1"
PROJECT_FILE_EXT = ".oilproj"


class ProjectFileError(ValueError):
    """工程文件无法保存或读取时抛出。"""


def save_project_file(project_state, project_file_path):
    """把当前 ProjectState 保存为 .oilproj 文件。"""
    if project_state is None:
        raise ProjectFileError("当前没有可保存的工程")
    project_file_path = _ensure_project_suffix(project_file_path)
    project_file_path = os.path.abspath(project_file_path)
    project_dir = os.path.dirname(project_file_path)
    if not project_dir:
        raise ProjectFileError("工程文件目录为空")
    os.makedirs(project_dir, exist_ok=True)

    payload = _build_payload(project_state, project_file_path)
    with open(project_file_path, "w", encoding="utf-8", newline="\n") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)
        file.write("\n")

    project_state.project_file_path = project_file_path
    if not project_state.project_name:
        project_state.project_name = os.path.splitext(os.path.basename(project_file_path))[0]
    return project_file_path


def load_project_file(project_file_path):
    """读取 .oilproj 并恢复 ProjectState，同时返回校验信息。"""
    project_file_path = os.path.abspath(project_file_path or "")
    if not project_file_path:
        raise ProjectFileError("工程文件路径为空")
    if not os.path.exists(project_file_path):
        raise ProjectFileError(f"工程文件不存在: {project_file_path}")
    with open(project_file_path, "r", encoding="utf-8-sig") as file:
        payload = json.load(file)
    if payload.get("schema_version") != PROJECT_SCHEMA_VERSION:
        raise ProjectFileError(
            f"不支持的工程文件版本: {payload.get('schema_version')}")

    project_dir = os.path.dirname(project_file_path)
    state_payload = copy.deepcopy(payload.get("state", {}))
    for field_name in ("case_data_path", "case_dataset_path"):
        path_record = (payload.get("path_records") or {}).get(field_name, {})
        state_payload[field_name] = _restore_path(path_record, project_dir)
    state = ProjectState.from_dict(state_payload)
    state.project_file_path = project_file_path
    if not state.project_name:
        state.project_name = os.path.splitext(os.path.basename(project_file_path))[0]

    validation = validate_project_state(state)
    return state, validation


def validate_project_state(project_state):
    """检查工程引用的 CaseData 和 Dataset 是否仍可用。"""
    errors = []
    warnings = []
    dataset_summary = {}

    case_data_path = getattr(project_state, "case_data_path", "")
    if case_data_path and not os.path.exists(case_data_path):
        warnings.append(f"CaseData 文件不存在: {case_data_path}")
    elif case_data_path:
        try:
            project_state.set_case_data(parse_case_data(case_data_path))
        except Exception as exc:
            errors.append(f"CaseData 读取失败: {exc}")

    dataset_path = getattr(project_state, "case_dataset_path", "")
    if dataset_path:
        if not os.path.isdir(dataset_path):
            warnings.append(f"Dataset 目录不存在: {dataset_path}")
        else:
            try:
                dataset = load_case_dataset(dataset_path, strict=False)
                dataset_summary = dataset.summary()
                project_state.case_dataset_summary.update({
                    "schema_version": dataset_summary.get("schema_version", ""),
                    "array_count": dataset_summary.get("array_count", 0),
                    "source_file_count": len(
                        dataset.manifest.get("source_files", {}) or {}),
                    "error_count": dataset_summary.get("error_count", 0),
                    "warning_count": dataset_summary.get("warning_count", 0),
                    "manifest_path": os.path.join(dataset_path, "manifest.json"),
                })
                if dataset_summary.get("error_count", 0):
                    errors.append(
                        f"Dataset 校验存在 {dataset_summary.get('error_count')} 个错误")
            except CaseDatasetReadError as exc:
                errors.append(f"Dataset 读取失败: {exc}")
    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "dataset_summary": dataset_summary,
    }


def _build_payload(project_state, project_file_path):
    now = datetime.now(timezone.utc).isoformat()
    state = project_state.to_dict()
    project_dir = os.path.dirname(os.path.abspath(project_file_path))
    path_records = {}
    for field_name in ("case_data_path", "case_dataset_path"):
        path_records[field_name] = _path_record(state.get(field_name, ""), project_dir)
        state[field_name] = path_records[field_name]["stored_path"]
    state["project_file_path"] = ""
    return {
        "schema_version": PROJECT_SCHEMA_VERSION,
        "project_name": state.get("project_name", ""),
        "created_at": now,
        "updated_at": now,
        "state": state,
        "path_records": path_records,
    }


def _path_record(path, base_dir):
    abs_path = os.path.abspath(path) if path else ""
    stored_path = ""
    is_relative = False
    if abs_path:
        rel_path = _safe_relpath(abs_path, base_dir)
        if rel_path is not None and not rel_path.startswith(".."):
            stored_path = rel_path.replace("\\", "/")
            is_relative = True
        else:
            stored_path = abs_path
    return {
        "stored_path": stored_path,
        "absolute_path": abs_path,
        "is_relative": is_relative,
        "exists": bool(abs_path and os.path.exists(abs_path)),
    }


def _restore_path(path_record, base_dir):
    stored_path = (path_record or {}).get("stored_path", "")
    absolute_path = (path_record or {}).get("absolute_path", "")
    if stored_path and not os.path.isabs(stored_path):
        candidate = os.path.abspath(os.path.join(base_dir, stored_path))
        if os.path.exists(candidate):
            return candidate
    if stored_path and os.path.isabs(stored_path):
        return os.path.abspath(stored_path)
    if absolute_path:
        return os.path.abspath(absolute_path)
    return ""


def _safe_relpath(path, base_dir):
    try:
        return os.path.relpath(path, base_dir)
    except ValueError:
        return None


def _ensure_project_suffix(path):
    if not path:
        raise ProjectFileError("工程文件路径为空")
    root, ext = os.path.splitext(path)
    if ext.lower() != PROJECT_FILE_EXT:
        return f"{path}{PROJECT_FILE_EXT}"
    return path
