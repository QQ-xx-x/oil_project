# -*- coding: utf-8 -*-
"""工程文件读写。

保存的 .oilproj 是单文件 zip 工程包。v2 工程包可以包含所有算例的
托管输入、Dataset 和已登记运行制品，同时继续兼容旧 JSON/v1 工程包。
"""

import copy
import json
import os
import shutil
import zipfile
from datetime import datetime, timedelta, timezone

from .case_dataset_reader import CaseDatasetReadError, load_case_dataset
from .case_data_parser import parse_case_data
from .legacy_module_migration import migrate_legacy_module_inputs
from .project_state import ProjectState


PROJECT_SCHEMA_VERSION = "oil_project_v3"
PREVIOUS_PROJECT_SCHEMA_VERSION = "oil_project_v2"
LEGACY_PROJECT_SCHEMA_VERSION = "oil_project_v1"
PACKAGE_SCHEMA_VERSION = "oil_project_package_v2"
PROJECT_FILE_EXT = ".oilproj"
PACKAGE_PROJECT_FILE = "project.json"
PACKAGE_MANIFEST_FILE = "package_manifest.json"
PACKAGE_DATASET_DIR = "case_dataset"
PACKAGE_RESULTS_DIR = "results"
PACKAGE_SIMULATION_RESULT_FILE = "simulation_result.json"
PACKAGE_CACHE_DIR = os.path.join(".tmp", "project_cache")
PROJECT_CACHE_MAX_AGE_DAYS = 7
PROJECT_CACHE_KEEP_RECENT = 10
PROJECT_CACHE_MAX_BYTES = 5 * 1024 ** 3
PROJECT_CACHE_TARGET_BYTES = 4 * 1024 ** 3

SUPPORTED_PROJECT_SCHEMA_VERSIONS = {
    LEGACY_PROJECT_SCHEMA_VERSION,
    PREVIOUS_PROJECT_SCHEMA_VERSION,
    PROJECT_SCHEMA_VERSION,
}


class ProjectFileError(ValueError):
    """工程文件无法保存或读取时抛出。"""


def save_project_file(
        project_state,
        project_file_path,
        simulation_result_path=None,
        result_files=None):
    """把当前 ProjectState 保存为包式 .oilproj 文件。"""
    if project_state is None:
        raise ProjectFileError("当前没有可保存的工程")
    unfinished = [
        (case.case_id, run.run_id)
        for case in (getattr(project_state, "cases", []) or [])
        for run in case.unfinished_runs()
    ]
    if unfinished:
        labels = ", ".join(
            f"{case_id}/{run_id}" for case_id, run_id in unfinished)
        raise ProjectFileError(
            "Cannot save a project while runs are preparing or running: "
            + labels)
    project_file_path = _ensure_project_suffix(project_file_path)
    project_file_path = os.path.abspath(project_file_path)
    project_dir = os.path.dirname(project_file_path)
    if not project_dir:
        raise ProjectFileError("工程文件目录为空")
    os.makedirs(project_dir, exist_ok=True)

    _save_project_package(
        project_state, project_file_path, simulation_result_path, result_files)

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
    if payload.get("schema_version") not in SUPPORTED_PROJECT_SCHEMA_VERSIONS:
        raise ProjectFileError(
            f"不支持的工程文件版本: {payload.get('schema_version')}")

    project_dir = os.path.dirname(project_file_path)
    state = _state_from_payload(payload, project_dir)
    state.project_file_path = project_file_path
    if not state.project_name:
        state.project_name = os.path.splitext(os.path.basename(project_file_path))[0]

    validation = validate_project_state(state)
    validation["module_migration"] = migrate_legacy_module_inputs(state)
    return state, validation


def _save_project_package(
        project_state,
        project_file_path,
        simulation_result_path=None,
        result_files=None):
    result_path = os.path.abspath(simulation_result_path or "") if simulation_result_path else ""
    has_result = bool(result_path and os.path.isfile(result_path))
    packaged_result_files = _existing_result_files(result_files)
    result_file_manifest = {
        key: f"{PACKAGE_RESULTS_DIR}/{os.path.basename(path)}"
        for key, path in packaged_result_files.items()
    }
    payload, package_plan, case_manifest, asset_manifest = _build_package_payload(
        project_state, project_file_path)
    active_dataset_dir = (
        (payload.get("state") or {}).get("case_dataset_path") or ""
    )
    has_dataset = bool(active_dataset_dir)
    package_manifest = {
        "schema_version": PACKAGE_SCHEMA_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "project_file": PACKAGE_PROJECT_FILE,
        "has_case_dataset": has_dataset,
        "case_dataset_dir": active_dataset_dir if has_dataset else "",
        "cases": case_manifest,
        "assets": asset_manifest,
        "has_results": has_result,
        "simulation_result_file": (
            f"{PACKAGE_RESULTS_DIR}/{PACKAGE_SIMULATION_RESULT_FILE}"
            if has_result else ""),
        "result_files": result_file_manifest,
        "result_summary": _build_result_summary(
            result_path if has_result else "",
            packaged_result_files,
            result_file_manifest,
        ),
    }
    temp_path = f"{project_file_path}.tmp"
    try:
        with zipfile.ZipFile(
            temp_path, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=True
        ) as archive:
            _write_json_to_zip(archive, PACKAGE_PROJECT_FILE, payload)
            _write_json_to_zip(archive, PACKAGE_MANIFEST_FILE, package_manifest)
            for entry in package_plan:
                if entry["kind"] == "directory":
                    _write_directory_to_zip(
                        archive, entry["source"], entry["target"])
                else:
                    archive.write(entry["source"], entry["target"])
            if has_result:
                archive.write(
                    result_path,
                    f"{PACKAGE_RESULTS_DIR}/{PACKAGE_SIMULATION_RESULT_FILE}")
            for path in packaged_result_files.values():
                archive.write(path, f"{PACKAGE_RESULTS_DIR}/{os.path.basename(path)}")
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
    manifest = _read_package_manifest(cache_dir)
    package_checks = _validate_package_contents(cache_dir, manifest)
    with open(project_json, "r", encoding="utf-8-sig") as file:
        payload = json.load(file)
    if payload.get("schema_version") not in SUPPORTED_PROJECT_SCHEMA_VERSIONS:
        raise ProjectFileError(
            f"不支持的工程文件版本: {payload.get('schema_version')}")
    state = _state_from_payload(payload, cache_dir)
    state.project_file_path = project_file_path
    if not state.project_name:
        state.project_name = os.path.splitext(os.path.basename(project_file_path))[0]
    state.ui_state.setdefault("package_cache_dir", cache_dir)
    results_dir = os.path.join(cache_dir, PACKAGE_RESULTS_DIR)
    result_json_path = os.path.join(
        results_dir, PACKAGE_SIMULATION_RESULT_FILE)
    if os.path.isdir(results_dir):
        state.ui_state["loaded_results_dir"] = results_dir
    if os.path.exists(result_json_path):
        state.ui_state["loaded_result_json_path"] = result_json_path
    if state.case_data_sections:
        state.ui_state["case_data_source_mode"] = "snapshot"
    validation = validate_project_state(state, refresh_case_data=False)
    validation["module_migration"] = migrate_legacy_module_inputs(state)
    validation["package_cache_dir"] = cache_dir
    validation["package_manifest"] = manifest
    validation["package_checks"] = package_checks
    validation["warnings"].extend(package_checks.get("warnings", []))
    validation["errors"].extend(package_checks.get("errors", []))
    validation["ok"] = not validation["errors"]
    return state, validation


def validate_project_state(project_state, refresh_case_data=True):
    """检查所有算例引用的 CaseData 和 Dataset 是否仍可用。"""
    errors = []
    warnings = []
    dataset_summary = {}
    case_summaries = {}
    run_summaries = {}

    cases = list(getattr(project_state, "cases", []) or [])
    if not cases:
        cases = [None]
    active_case_id = getattr(project_state, "active_case_id", "")

    for case in cases:
        case_id = getattr(case, "case_id", "") if case is not None else ""
        case_name = getattr(case, "case_name", "") if case is not None else "DefaultCase"
        input_state = getattr(case, "input_state", None) if case is not None else None
        case_data_path = (
            getattr(input_state, "case_data_path", "")
            if input_state is not None
            else getattr(project_state, "case_data_path", "")
        )
        if case_data_path and not os.path.exists(case_data_path):
            warnings.append(f"[{case_name}] CaseData 文件不存在: {case_data_path}")

        records = (
            list(getattr(case, "dataset_records", []) or [])
            if case is not None
            else []
        )
        if case is None and getattr(project_state, "case_dataset_path", ""):
            records = [type("LegacyDataset", (), {
                "path": project_state.case_dataset_path,
                "summary": project_state.case_dataset_summary,
                "dataset_id": "legacy",
            })()]

        summaries = []
        for record in records:
            dataset_path = getattr(record, "path", "") or ""
            if not dataset_path:
                continue
            if not os.path.isdir(dataset_path):
                warnings.append(f"[{case_name}] Dataset 目录不存在: {dataset_path}")
                continue
            try:
                dataset = load_case_dataset(dataset_path, strict=False)
                summary = dataset.summary()
                summaries.append(summary)
                record.summary.update({
                    "schema_version": summary.get("schema_version", ""),
                    "array_count": summary.get("array_count", 0),
                    "source_file_count": len(
                        dataset.manifest.get("source_files", {}) or {}),
                    "error_count": summary.get("error_count", 0),
                    "warning_count": summary.get("warning_count", 0),
                    "manifest_path": os.path.join(dataset_path, "manifest.json"),
                })
                if summary.get("error_count", 0):
                    errors.append(
                        f"[{case_name}] Dataset 校验存在 "
                        f"{summary.get('error_count')} 个错误")
                if case_id == active_case_id and (
                        getattr(case, "active_dataset_id", "") ==
                        getattr(record, "dataset_id", "")):
                    dataset_summary = summary
            except CaseDatasetReadError as exc:
                errors.append(f"[{case_name}] Dataset 读取失败: {exc}")
        case_summaries[case_id or "legacy"] = summaries
        dataset_ids = {
            str(getattr(record, "dataset_id", "") or "")
            for record in records
        }
        run_items = []
        for run in list(getattr(case, "run_records", []) or []):
            artifacts = dict(getattr(run, "artifacts", {}) or {})
            result_path = str(artifacts.get("result_json") or "")
            missing_artifacts = [
                key for key, path in artifacts.items()
                if isinstance(path, str) and path and not os.path.exists(path)
            ]
            item = {
                "run_id": getattr(run, "run_id", "") or "",
                "run_type": getattr(run, "run_type", "") or "",
                "status": getattr(run, "status", "") or "",
                "dataset_id": getattr(run, "dataset_id", "") or "",
                "result_json_path": result_path,
                "result_json_exists": bool(
                    result_path and os.path.isfile(result_path)),
                "artifact_count": len(artifacts),
                "missing_artifacts": missing_artifacts,
            }
            run_items.append(item)
            if case is not None and getattr(run, "case_id", "") != case_id:
                errors.append(
                    f"[{case_name}] Run {item['run_id']} ownership does not match its Case")
            if item["dataset_id"] and item["dataset_id"] not in dataset_ids:
                warnings.append(
                    f"[{case_name}] Run {item['run_id']} references an unknown Dataset "
                    f"{item['dataset_id']}")
            if item["status"] == "completed" and not item["result_json_exists"]:
                warnings.append(
                    f"[{case_name}] Run {item['run_id']} result JSON is missing")
            load_error = str(
                (getattr(run, "summary", {}) or {}).get(
                    "result_load_error") or "")
            if load_error:
                warnings.append(
                    f"[{case_name}] Run {item['run_id']} result is unreadable: "
                    f"{load_error}")
            if missing_artifacts:
                warnings.append(
                    f"[{case_name}] Run {item['run_id']} has missing artifacts: "
                    + ", ".join(sorted(missing_artifacts)))
        run_summaries[case_id or "legacy"] = run_items

    if refresh_case_data:
        case_data_path = getattr(project_state, "case_data_path", "")
        if case_data_path and os.path.exists(case_data_path):
            try:
                project_state.set_case_data(parse_case_data(case_data_path))
            except Exception as exc:
                errors.append(f"活动算例 CaseData 读取失败: {exc}")
    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "dataset_summary": dataset_summary,
        "case_summaries": case_summaries,
        "run_summaries": run_summaries,
    }


def _state_from_payload(payload, base_dir):
    state_payload = copy.deepcopy(payload.get("state", {}))
    _restore_case_paths_in_payload(state_payload, base_dir)
    for asset in (state_payload.get("input_assets") or {}).values():
        if isinstance(asset, dict):
            asset["managed_path"] = _restore_packaged_value(
                asset.get("managed_path"), base_dir)
    _restore_case_data_section_paths(
        state_payload.get("case_data_sections"), base_dir)
    _restore_module_input_paths(
        state_payload.get("module_inputs"), base_dir)
    path_records = payload.get("path_records") or {}
    for field_name in ("case_data_path", "case_dataset_path"):
        path_record = path_records.get(field_name)
        if path_record:
            state_payload[field_name] = _restore_path(path_record, base_dir)
            continue
        value = state_payload.get(field_name, "")
        if value and not os.path.isabs(value):
            state_payload[field_name] = os.path.abspath(os.path.join(base_dir, value))
    summary = state_payload.get("case_dataset_summary") or {}
    if summary.get("manifest_path") and not os.path.isabs(summary["manifest_path"]):
        summary["manifest_path"] = os.path.abspath(
            os.path.join(base_dir, summary["manifest_path"]))
    return ProjectState.from_dict(state_payload)


def _build_package_payload(project_state, project_file_path):
    payload = _build_payload(project_state, project_file_path)
    state = payload["state"]
    path_records = payload["path_records"]
    package_plan = []
    plan_targets = set()
    asset_manifest = []
    asset_targets = {}
    case_manifest = []

    cases_by_id = {
        getattr(case, "case_id", ""): case
        for case in (getattr(project_state, "cases", []) or [])
    }
    for case_payload in state.get("cases", []) or []:
        if not isinstance(case_payload, dict):
            continue
        case_id = str(case_payload.get("case_id") or "")
        case = cases_by_id.get(case_id)
        if case is None:
            continue
        packaged_case = {
            "case_id": case_id,
            "case_name": case_payload.get("case_name", ""),
            "datasets": [],
            "runs": [],
        }
        dataset_package_paths = {}
        input_payload = case_payload.get("input_state") or {}
        assets = input_payload.get("input_assets") or {}
        for key, asset in assets.items():
            if not isinstance(asset, dict):
                continue
            source = asset.get("managed_path") or ""
            if not source or not os.path.isfile(source):
                continue
            digest = asset.get("sha256") or ""
            if not digest:
                digest = _file_sha256(source)
                asset["sha256"] = digest
                asset["asset_id"] = digest
            target = asset_targets.get(digest)
            if not target:
                target = (
                    f"assets/{_safe_package_component(digest)}/"
                    f"{_safe_package_filename(os.path.basename(source))}"
                )
                asset_targets[digest] = target
                _add_package_entry(
                    package_plan, plan_targets, source, target, "file")
                asset_manifest.append({
                    "asset_id": digest,
                    "package_path": target,
                    "size": _file_size(source),
                })
            asset["managed_path"] = target
            if key == "case_data":
                input_payload["case_data_path"] = target
            for section in input_payload.get("case_data_sections", []) or []:
                if not isinstance(section, dict):
                    continue
                for keyword in section.get("keywords", []) or []:
                    if not isinstance(keyword, dict) or keyword.get("key") != key:
                        continue
                    keyword["file_path"] = target
                    keyword["file_exists"] = True

        _rebind_module_sources_to_assets(input_payload)

        for record_payload in case_payload.get("dataset_records", []) or []:
            if not isinstance(record_payload, dict):
                continue
            source = record_payload.get("path") or ""
            if not source or not os.path.isdir(source):
                continue
            dataset_id = _safe_package_component(
                record_payload.get("dataset_id") or "dataset")
            target = f"cases/{_safe_package_component(case_id)}/datasets/{dataset_id}"
            _add_package_entry(
                package_plan, plan_targets, source, target, "directory")
            record_payload["path"] = target
            dataset_package_paths[record_payload.get("dataset_id", "")] = target
            summary = record_payload.get("summary") or {}
            summary["manifest_path"] = f"{target}/manifest.json"
            packaged_case["datasets"].append({
                "dataset_id": record_payload.get("dataset_id", ""),
                "path": target,
                "status": record_payload.get("status", ""),
            })

        for run_payload in case_payload.get("run_records", []) or []:
            if not isinstance(run_payload, dict):
                continue
            run_dataset_id = run_payload.get("dataset_id", "") or ""
            if run_dataset_id in dataset_package_paths:
                run_payload["dataset_path"] = dataset_package_paths[run_dataset_id]
            run_id = _safe_package_component(run_payload.get("run_id") or "run")
            run_type = _safe_package_component(
                run_payload.get("run_type") or "simulation")
            artifacts = run_payload.get("artifacts") or {}
            packaged_artifacts = {}
            run_target = (
                f"cases/{_safe_package_component(case_id)}/runs/"
                f"{run_type}/{run_id}"
            )
            run_dir_source = artifacts.get("run_dir") or ""
            if run_dir_source and os.path.isdir(run_dir_source):
                run_dir_source = os.path.abspath(run_dir_source)
                _add_package_entry(
                    package_plan,
                    plan_targets,
                    run_dir_source,
                    run_target,
                    "directory",
                )
                artifacts["run_dir"] = run_target
                packaged_artifacts["run_dir"] = run_target
            elif run_dir_source:
                artifacts.pop("run_dir", None)
            for key, source in list(artifacts.items()):
                if key == "run_dir":
                    continue
                if not isinstance(source, str) or not source:
                    artifacts.pop(key, None)
                    continue
                if not os.path.exists(source):
                    artifacts.pop(key, None)
                    continue
                relative = _path_within(source, run_dir_source)
                if relative:
                    target = f"{run_target}/{relative.replace(os.sep, '/')}"
                else:
                    target = (
                        f"{run_target}/artifacts/{_safe_package_component(key)}/"
                        f"{_safe_package_filename(os.path.basename(source))}"
                    )
                    kind = "directory" if os.path.isdir(source) else "file"
                    _add_package_entry(
                        package_plan, plan_targets, source, target, kind)
                artifacts[key] = target
                packaged_artifacts[key] = target
            packaged_case["runs"].append({
                "run_id": run_payload.get("run_id", ""),
                "run_type": run_payload.get("run_type", ""),
                "status": run_payload.get("status", ""),
                "artifacts": packaged_artifacts,
            })
        case_manifest.append(packaged_case)

    active_case_payload = next((
        item for item in state.get("cases", []) or []
        if isinstance(item, dict)
        and item.get("case_id") == state.get("active_case_id")
    ), None)
    if active_case_payload:
        input_payload = active_case_payload.get("input_state") or {}
        state["case_data_path"] = input_payload.get("case_data_path", "")
        state["case_data_summary"] = copy.deepcopy(
            input_payload.get("case_data_summary") or {})
        state["case_data_sections"] = copy.deepcopy(
            input_payload.get("case_data_sections") or [])
        state["case_data_schema"] = copy.deepcopy(
            input_payload.get("case_data_schema") or {})
        state["model_config"] = copy.deepcopy(input_payload.get("model_config") or {})
        state["module_values"] = copy.deepcopy(input_payload.get("module_values") or {})
        state["module_inputs"] = copy.deepcopy(input_payload.get("module_inputs") or {})
        state["checked_items"] = copy.deepcopy(input_payload.get("checked_items") or {})
        state["input_assets"] = copy.deepcopy(input_payload.get("input_assets") or {})
        active_dataset_id = active_case_payload.get("active_dataset_id") or ""
        active_dataset = next((
            item for item in active_case_payload.get("dataset_records", []) or []
            if isinstance(item, dict) and item.get("dataset_id") == active_dataset_id
        ), None)
        state["case_dataset_path"] = (
            active_dataset.get("path", "") if active_dataset else "")
        state["case_dataset_summary"] = copy.deepcopy(
            active_dataset.get("summary") or {}) if active_dataset else {}

    if state.get("case_data_sections"):
        state.setdefault("ui_state", {})["case_data_source_mode"] = "snapshot"
    for field_name in ("case_data_path", "case_dataset_path"):
        stored_path = state.get(field_name, "") or ""
        path_records[field_name] = {
            "stored_path": stored_path,
            "absolute_path": "",
            "is_relative": bool(stored_path),
            "exists": bool(stored_path),
            "package_path": stored_path,
        }
    return payload, package_plan, case_manifest, asset_manifest


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


def _restore_case_paths_in_payload(state_payload, base_dir):
    for case_payload in state_payload.get("cases", []) or []:
        if not isinstance(case_payload, dict):
            continue
        input_payload = case_payload.get("input_state") or {}
        input_payload["case_data_path"] = _restore_packaged_value(
            input_payload.get("case_data_path"), base_dir)
        for asset in (input_payload.get("input_assets") or {}).values():
            if isinstance(asset, dict):
                asset["managed_path"] = _restore_packaged_value(
                    asset.get("managed_path"), base_dir)
        _restore_case_data_section_paths(
            input_payload.get("case_data_sections"), base_dir)
        _restore_module_input_paths(
            input_payload.get("module_inputs"), base_dir)
        for record in case_payload.get("dataset_records", []) or []:
            if not isinstance(record, dict):
                continue
            record["path"] = _restore_packaged_value(record.get("path"), base_dir)
            summary = record.get("summary") or {}
            summary["manifest_path"] = _restore_packaged_value(
                summary.get("manifest_path"), base_dir)
        for run in case_payload.get("run_records", []) or []:
            if not isinstance(run, dict):
                continue
            run["dataset_path"] = _restore_packaged_value(
                run.get("dataset_path"), base_dir)
            artifacts = run.get("artifacts") or {}
            for key, value in list(artifacts.items()):
                if isinstance(value, str):
                    artifacts[key] = _restore_packaged_value(value, base_dir)


def _restore_case_data_section_paths(sections, base_dir):
    for section in sections or []:
        if not isinstance(section, dict):
            continue
        for keyword in section.get("keywords", []) or []:
            if not isinstance(keyword, dict) or not keyword.get("is_file_ref"):
                continue
            keyword["file_path"] = _restore_packaged_value(
                keyword.get("file_path"), base_dir)
            keyword["file_exists"] = bool(
                keyword.get("file_path")
                and os.path.exists(keyword["file_path"])
            )


def _rebind_module_sources_to_assets(input_payload):
    """将打包后的模块定位信息指向按内容寻址的资源。"""

    assets = input_payload.get("input_assets") or {}
    lookup = {}
    for asset_key, asset in assets.items():
        if not isinstance(asset, dict):
            continue
        path = str(asset.get("managed_path") or "")
        if not path:
            continue
        source_key = str(asset.get("source_key") or asset_key)
        lookup[source_key.lower()] = path
        lookup[str(asset_key).removeprefix("module:").lower()] = path

    for module_state in (input_payload.get("module_inputs") or {}).values():
        if not isinstance(module_state, dict):
            continue
        source = module_state.get("source") or {}
        case_data_path = str(input_payload.get("case_data_path") or "")
        if case_data_path:
            source["case_data_path"] = case_data_path
            source["base_dir"] = os.path.dirname(case_data_path)
        for qualified_name, record in (source.get("keywords") or {}).items():
            if not isinstance(record, dict):
                continue
            keyword = str(qualified_name).split(".", 1)[-1].lower()
            resolved = lookup.get(str(qualified_name).lower()) or lookup.get(keyword)
            if resolved:
                record["resolved_path"] = resolved
                record["exists"] = True
        module_state["source"] = source


def _restore_module_input_paths(module_inputs, base_dir):
    for module_state in (module_inputs or {}).values():
        if not isinstance(module_state, dict):
            continue
        source = module_state.get("source") or {}
        source["case_data_path"] = _restore_packaged_value(
            source.get("case_data_path"), base_dir)
        source["base_dir"] = _restore_packaged_value(
            source.get("base_dir"), base_dir)
        for record in (source.get("keywords") or {}).values():
            if not isinstance(record, dict) or not record.get("resolved_path"):
                continue
            record["resolved_path"] = _restore_packaged_value(
                record.get("resolved_path"), base_dir)
            record["exists"] = bool(os.path.isfile(record["resolved_path"]))


def _restore_packaged_value(value, base_dir):
    value = str(value or "")
    if not value or os.path.isabs(value):
        return value
    return os.path.abspath(os.path.join(base_dir, value))


def _add_package_entry(plan, targets, source, target, kind):
    source = os.path.abspath(source)
    target = str(target or "").replace("\\", "/").strip("/")
    if not target or target in targets:
        return
    targets.add(target)
    plan.append({"source": source, "target": target, "kind": kind})


def _safe_package_component(value):
    value = str(value or "")
    safe = "".join(
        ch if ch.isalnum() or ch in "_-" else "_"
        for ch in value
    ).strip("_")
    return safe or "item"


def _safe_package_filename(value):
    value = os.path.basename(str(value or "artifact"))
    safe = "".join(
        ch if ch.isalnum() or ch in "._-" else "_"
        for ch in value
    )
    return safe or "artifact"


def _path_within(path, root):
    if not path or not root:
        return ""
    path = os.path.abspath(path)
    root = os.path.abspath(root)
    try:
        if os.path.commonpath([path, root]) != root or path == root:
            return ""
    except ValueError:
        return ""
    return os.path.relpath(path, root)


def _file_sha256(path):
    import hashlib

    digest = hashlib.sha256()
    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def _existing_result_files(result_files):
    if not result_files:
        return {}
    existing = {}
    for key, path in dict(result_files).items():
        if not path:
            continue
        abs_path = os.path.abspath(path)
        if os.path.isfile(abs_path):
            existing[str(key)] = abs_path
    return existing


def _build_result_summary(result_path, result_files, result_file_manifest):
    summary = {
        "has_3d_json": bool(result_path),
        "simulation_result_size_bytes": _file_size(result_path),
        "pressure_points": 0,
        "corner_cell_count": 0,
        "corner_grid_cell_count": 0,
        "fracture_count": 0,
        "well_count": 0,
        "time_step_count": 0,
        "pressure_step_count": 0,
        "has_dual_porosity": False,
        "result_files": _result_file_summaries(result_files, result_file_manifest),
    }
    if not result_path:
        return summary
    try:
        with open(result_path, "r", encoding="utf-8-sig") as file:
            payload = json.load(file)
    except Exception as exc:
        summary["summary_error"] = str(exc)
        return summary

    summary.update({
        "pressure_points": _sequence_length(payload.get("pressure_field")),
        "corner_cell_count": _sequence_length(
            payload.get("cell_geometry_with_pressure")),
        "corner_grid_cell_count": _corner_grid_cell_count(
            payload.get("corner_point_grid")),
        "fracture_count": _sequence_length(payload.get("fractures")),
        "well_count": _sequence_length(payload.get("wells")),
        "time_step_count": _sequence_length(payload.get("time_steps")),
        "pressure_step_count": _sequence_length(payload.get("pressure_steps")),
        "has_dual_porosity": bool(payload.get("has_dual_porosity", False)),
    })
    return summary


def _result_file_summaries(result_files, result_file_manifest):
    summaries = {}
    for key, path in dict(result_files or {}).items():
        summaries[key] = {
            "package_path": result_file_manifest.get(key, ""),
            "source_basename": os.path.basename(path),
            "size_bytes": _file_size(path),
        }
    return summaries


def _read_package_manifest(cache_dir):
    manifest_path = os.path.join(cache_dir, PACKAGE_MANIFEST_FILE)
    if not os.path.exists(manifest_path):
        return {}
    try:
        with open(manifest_path, "r", encoding="utf-8-sig") as file:
            manifest = json.load(file)
    except Exception as exc:
        return {"_read_error": str(exc)}
    return manifest if isinstance(manifest, dict) else {}


def _validate_package_contents(cache_dir, manifest):
    checks = {
        "ok": True,
        "errors": [],
        "warnings": [],
        "info": [],
        "result_summary": dict((manifest or {}).get("result_summary") or {}),
    }
    if not manifest:
        checks["warnings"].append("工程包缺少 package_manifest.json，已按旧包格式兼容打开")
    elif manifest.get("_read_error"):
        checks["warnings"].append(
            f"工程包 package_manifest.json 读取失败：{manifest.get('_read_error')}")

    _require_package_file(cache_dir, PACKAGE_PROJECT_FILE, checks, "工程状态 project.json")

    dataset_dir = (manifest or {}).get("case_dataset_dir") or ""
    if (manifest or {}).get("has_case_dataset"):
        if dataset_dir:
            _require_package_dir(cache_dir, dataset_dir, checks, "CaseDataset")
        else:
            checks["errors"].append("工程包声明包含 CaseDataset，但 manifest 未记录目录")

    result_file = (manifest or {}).get("simulation_result_file") or ""
    if (manifest or {}).get("has_results"):
        if result_file:
            _require_package_file(cache_dir, result_file, checks, "模拟结果 JSON")
        else:
            checks["errors"].append("工程包声明包含模拟结果，但 manifest 未记录结果 JSON")
    elif _package_file_exists(cache_dir, f"{PACKAGE_RESULTS_DIR}/{PACKAGE_SIMULATION_RESULT_FILE}"):
        checks["info"].append("工程包包含模拟结果 JSON，但 manifest 未声明 has_results")

    for key, package_path in dict((manifest or {}).get("result_files") or {}).items():
        label = f"结果文件 {key}"
        _require_package_file(cache_dir, package_path, checks, label)

    for asset in (manifest or {}).get("assets", []) or []:
        if not isinstance(asset, dict):
            continue
        _require_package_file(
            cache_dir,
            asset.get("package_path", ""),
            checks,
            f"输入资产 {asset.get('asset_id', '')}",
        )

    for case in (manifest or {}).get("cases", []) or []:
        if not isinstance(case, dict):
            continue
        case_label = case.get("case_name") or case.get("case_id") or "case"
        for dataset in case.get("datasets", []) or []:
            if isinstance(dataset, dict):
                _require_package_dir(
                    cache_dir,
                    dataset.get("path", ""),
                    checks,
                    f"[{case_label}] Dataset {dataset.get('dataset_id', '')}",
                )
        for run in case.get("runs", []) or []:
            if not isinstance(run, dict):
                continue
            for key, package_path in (run.get("artifacts") or {}).items():
                abs_path = _package_abs_path(cache_dir, package_path)
                label = f"[{case_label}] Run {run.get('run_id', '')} 制品 {key}"
                if abs_path and os.path.isdir(abs_path):
                    _require_package_dir(cache_dir, package_path, checks, label)
                else:
                    _require_package_file(cache_dir, package_path, checks, label)

    checks["ok"] = not checks["errors"]
    return checks


def _require_package_file(cache_dir, package_path, checks, label):
    if not package_path:
        checks["warnings"].append(f"{label} 未记录包内路径")
        return
    if _package_file_exists(cache_dir, package_path):
        checks["info"].append(f"{label} 可用：{package_path}")
    else:
        checks["errors"].append(f"{label} 缺失：{package_path}")


def _require_package_dir(cache_dir, package_path, checks, label):
    abs_path = _package_abs_path(cache_dir, package_path)
    if abs_path and os.path.isdir(abs_path):
        checks["info"].append(f"{label} 可用：{package_path}")
    else:
        checks["errors"].append(f"{label} 缺失：{package_path}")


def _package_file_exists(cache_dir, package_path):
    abs_path = _package_abs_path(cache_dir, package_path)
    return bool(abs_path and os.path.isfile(abs_path))


def _package_abs_path(cache_dir, package_path):
    parts = str(package_path or "").replace("\\", "/").split("/")
    parts = [part for part in parts if part and part not in {".", ".."}]
    if not parts:
        return ""
    abs_path = os.path.abspath(os.path.join(cache_dir, *parts))
    cache_dir = os.path.abspath(cache_dir)
    if abs_path != cache_dir and abs_path.startswith(cache_dir + os.sep):
        return abs_path
    return ""


def _sequence_length(value):
    return len(value) if isinstance(value, (list, tuple)) else 0


def _corner_grid_cell_count(corner_point_grid):
    if not isinstance(corner_point_grid, dict):
        return 0
    return _sequence_length(corner_point_grid.get("cells"))


def _file_size(path):
    try:
        return os.path.getsize(path) if path else 0
    except OSError:
        return 0

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
    _cleanup_project_cache(cache_root)
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


def _cleanup_project_cache(cache_root):
    entries = _list_project_cache_entries(cache_root)
    if not entries:
        return

    keep_paths = {entry["path"] for entry in entries[:PROJECT_CACHE_KEEP_RECENT]}
    cutoff = datetime.now(timezone.utc) - timedelta(days=PROJECT_CACHE_MAX_AGE_DAYS)
    for entry in reversed(entries):
        if entry["path"] in keep_paths:
            continue
        if entry["modified_at"] < cutoff:
            _remove_cache_dir(entry["path"])

    entries = _list_project_cache_entries(cache_root)
    total_size = sum(entry["size"] for entry in entries)
    if total_size <= PROJECT_CACHE_MAX_BYTES:
        return

    keep_paths = {entry["path"] for entry in entries[:PROJECT_CACHE_KEEP_RECENT]}
    for entry in reversed(entries):
        if total_size <= PROJECT_CACHE_TARGET_BYTES:
            break
        if entry["path"] in keep_paths:
            continue
        if _remove_cache_dir(entry["path"]):
            total_size -= entry["size"]


def _list_project_cache_entries(cache_root):
    entries = []
    try:
        names = os.listdir(cache_root)
    except OSError:
        return entries
    for name in names:
        path = os.path.abspath(os.path.join(cache_root, name))
        if not _is_direct_child_dir(cache_root, path):
            continue
        try:
            stat = os.stat(path)
        except OSError:
            continue
        entries.append({
            "path": path,
            "modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc),
            "size": _cache_dir_size(path),
        })
    entries.sort(key=lambda entry: entry["modified_at"], reverse=True)
    return entries


def _is_direct_child_dir(parent, path):
    parent = os.path.abspath(parent)
    path = os.path.abspath(path)
    if os.path.dirname(path) != parent:
        return False
    return os.path.isdir(path)


def _cache_dir_size(path):
    total = 0
    for root, _, files in os.walk(path):
        for filename in files:
            file_path = os.path.join(root, filename)
            try:
                total += os.path.getsize(file_path)
            except OSError:
                pass
    return total


def _remove_cache_dir(path):
    try:
        shutil.rmtree(path)
        return True
    except OSError:
        return False


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
