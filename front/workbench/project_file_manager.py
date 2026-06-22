# -*- coding: utf-8 -*-
"""工程文件读写。

第二阶段起，保存的 .oilproj 是单文件 zip 工程包，内部包含 project.json
和可选的 case_dataset/。打开时仍兼容第一阶段的纯 JSON .oilproj。
算法侧不直接读取 .oilproj；UI 打开工程包后会解出 case_dataset 目录。
"""

import copy
import json
import os
import shutil
import zipfile
from datetime import datetime, timezone

from .case_dataset_reader import CaseDatasetReadError, load_case_dataset
from .case_data_parser import parse_case_data
from .project_state import ProjectState


PROJECT_SCHEMA_VERSION = "oil_project_v2"
LEGACY_PROJECT_SCHEMA_VERSION = "oil_project_v1"
PACKAGE_SCHEMA_VERSION = "oil_project_package_v1"
PROJECT_FILE_EXT = ".oilproj"
PACKAGE_PROJECT_FILE = "project.json"
PACKAGE_MANIFEST_FILE = "package_manifest.json"
PACKAGE_DATASET_DIR = "case_dataset"
PACKAGE_CACHE_DIR = os.path.join(".tmp", "project_cache")


class ProjectFileError(ValueError):
    """工程文件无法保存或读取时抛出。"""


def save_project_file(project_state, project_file_path):
    """把当前 ProjectState 保存为包式 .oilproj 文件。"""
    if project_state is None:
        raise ProjectFileError("当前没有可保存的工程")
    project_file_path = _ensure_project_suffix(project_file_path)
    project_file_path = os.path.abspath(project_file_path)
    project_dir = os.path.dirname(project_file_path)
    if not project_dir:
        raise ProjectFileError("工程文件目录为空")
    os.makedirs(project_dir, exist_ok=True)

    _save_project_package(project_state, project_file_path)

    project_state.project_file_path = project_file_path
    if not project_state.project_name:
        project_state.project_name = os.path.splitext(os.path.basename(project_file_path))[0]
    return project_file_path


def load_project_file(project_file_path):
    """读取 .oilproj 并恢复 ProjectState，同时返回校验信息。

    新格式 .oilproj 是 zip 工程包；旧格式 .oilproj 是第一阶段的 JSON 文件。
    """
    project_file_path = os.path.abspath(project_file_path or "")
    if not project_file_path:
        raise ProjectFileError("工程文件路径为空")
    if not os.path.exists(project_file_path):
        raise ProjectFileError(f"工程文件不存在: {project_file_path}")
    if zipfile.is_zipfile(project_file_path):
        return _load_project_package(project_file_path)
    return _load_legacy_project_file(project_file_path)


def _load_legacy_project_file(project_file_path):
    """读取第一阶段 JSON .oilproj。"""
    with open(project_file_path, "r", encoding="utf-8-sig") as file:
        payload = json.load(file)
    if payload.get("schema_version") not in {
        LEGACY_PROJECT_SCHEMA_VERSION, PROJECT_SCHEMA_VERSION,
    }:
        raise ProjectFileError(
            f"不支持的工程文件版本: {payload.get('schema_version')}")

    project_dir = os.path.dirname(project_file_path)
    state = _state_from_payload(payload, project_dir)
    state.project_file_path = project_file_path
    if not state.project_name:
        state.project_name = os.path.splitext(os.path.basename(project_file_path))[0]

    validation = validate_project_state(state)
    return state, validation


def _save_project_package(project_state, project_file_path):
    raw_dataset_path = getattr(project_state, "case_dataset_path", "") or ""
    dataset_path = os.path.abspath(raw_dataset_path) if raw_dataset_path else ""
    has_dataset = bool(dataset_path and os.path.isdir(dataset_path))
    payload = _build_package_payload(project_state, project_file_path, dataset_path)
    package_manifest = {
        "schema_version": PACKAGE_SCHEMA_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "project_file": PACKAGE_PROJECT_FILE,
        "has_case_dataset": has_dataset,
        "case_dataset_dir": PACKAGE_DATASET_DIR if has_dataset else "",
    }
    temp_path = f"{project_file_path}.tmp"
    try:
        with zipfile.ZipFile(
            temp_path, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=True
        ) as archive:
            _write_json_to_zip(archive, PACKAGE_PROJECT_FILE, payload)
            _write_json_to_zip(archive, PACKAGE_MANIFEST_FILE, package_manifest)
            if has_dataset:
                _write_directory_to_zip(archive, dataset_path, PACKAGE_DATASET_DIR)
        os.replace(temp_path, project_file_path)
    except Exception:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise


def _load_project_package(project_file_path):
    cache_dir = _extract_project_package(project_file_path)
    project_json = os.path.join(cache_dir, PACKAGE_PROJECT_FILE)
    if not os.path.exists(project_json):
        raise ProjectFileError(f"工程包缺少 {PACKAGE_PROJECT_FILE}")
    with open(project_json, "r", encoding="utf-8-sig") as file:
        payload = json.load(file)
    if payload.get("schema_version") not in {
        LEGACY_PROJECT_SCHEMA_VERSION, PROJECT_SCHEMA_VERSION,
    }:
        raise ProjectFileError(
            f"不支持的工程文件版本: {payload.get('schema_version')}")
    state = _state_from_payload(payload, cache_dir)
    state.project_file_path = project_file_path
    if not state.project_name:
        state.project_name = os.path.splitext(os.path.basename(project_file_path))[0]
    state.ui_state.setdefault("package_cache_dir", cache_dir)
    if state.case_data_sections:
        state.ui_state["case_data_source_mode"] = "snapshot"
    validation = validate_project_state(state, refresh_case_data=False)
    validation["package_cache_dir"] = cache_dir
    return state, validation


def validate_project_state(project_state, refresh_case_data=True):
    """检查工程引用的 CaseData 和 Dataset 是否仍可用。"""
    errors = []
    warnings = []
    dataset_summary = {}

    case_data_path = getattr(project_state, "case_data_path", "")
    if refresh_case_data and case_data_path and not os.path.exists(case_data_path):
        warnings.append(f"CaseData 文件不存在: {case_data_path}")
    elif refresh_case_data and case_data_path:
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


def _state_from_payload(payload, base_dir):
    state_payload = copy.deepcopy(payload.get("state", {}))
    path_records = payload.get("path_records") or {}
    for field_name in ("case_data_path", "case_dataset_path"):
        path_record = path_records.get(field_name)
        if path_record:
            state_payload[field_name] = _restore_path(path_record, base_dir)
            continue
        value = state_payload.get(field_name, "")
        if value and not os.path.isabs(value):
            state_payload[field_name] = os.path.abspath(os.path.join(base_dir, value))
    return ProjectState.from_dict(state_payload)


def _build_package_payload(project_state, project_file_path, dataset_path):
    payload = _build_payload(project_state, project_file_path)
    state = payload["state"]
    path_records = payload["path_records"]
    if state.get("case_data_sections"):
        state.setdefault("ui_state", {})["case_data_source_mode"] = "snapshot"
    if dataset_path and os.path.isdir(dataset_path):
        state["case_dataset_path"] = PACKAGE_DATASET_DIR
        path_records["case_dataset_path"] = {
            "stored_path": PACKAGE_DATASET_DIR,
            "absolute_path": dataset_path,
            "is_relative": True,
            "exists": True,
            "package_path": PACKAGE_DATASET_DIR,
        }
    return payload


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


def _write_json_to_zip(archive, arcname, payload):
    data = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    archive.writestr(arcname, data)


def _write_directory_to_zip(archive, source_dir, target_dir):
    source_dir = os.path.abspath(source_dir)
    for root, _, files in os.walk(source_dir):
        for filename in files:
            full_path = os.path.join(root, filename)
            rel_path = os.path.relpath(full_path, source_dir).replace("\\", "/")
            archive.write(full_path, f"{target_dir}/{rel_path}")


def _extract_project_package(project_file_path):
    cache_root = os.path.abspath(PACKAGE_CACHE_DIR)
    os.makedirs(cache_root, exist_ok=True)
    basename = os.path.splitext(os.path.basename(project_file_path))[0]
    cache_name = (
        f"{_safe_cache_name(basename)}_"
        f"{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
    )
    cache_dir = os.path.join(cache_root, cache_name)
    os.makedirs(cache_dir, exist_ok=False)
    try:
        with zipfile.ZipFile(project_file_path, "r") as archive:
            names = set(archive.namelist())
            if PACKAGE_PROJECT_FILE not in names:
                raise ProjectFileError(f"工程包缺少 {PACKAGE_PROJECT_FILE}")
            _safe_extract_zip(archive, cache_dir)
    except Exception:
        shutil.rmtree(cache_dir, ignore_errors=True)
        raise
    return cache_dir


def _safe_extract_zip(archive, target_dir):
    target_dir = os.path.abspath(target_dir)
    for member in archive.infolist():
        member_target = os.path.abspath(os.path.join(target_dir, member.filename))
        if member_target != target_dir and not member_target.startswith(target_dir + os.sep):
            raise ProjectFileError(f"工程包内存在非法路径: {member.filename}")
    archive.extractall(target_dir)


def _safe_cache_name(name):
    safe = "".join(ch if ch.isalnum() or ch in "_-" else "_" for ch in name)
    return safe or "project"


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
