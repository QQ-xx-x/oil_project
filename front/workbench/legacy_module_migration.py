# -*- coding: utf-8 -*-
"""从整份 CaseData 项目迁移到模块输入的兼容逻辑。"""

import copy
import os
import tempfile
import uuid

from .case_data_parser import case_data_from_dict, export_case_data_snapshot
from .input_keyword_registry import (
    MODULE_HISTORY_MATCHING,
    MODULE_MODEL_CONFIGURATION,
    MODULE_SPECS,
)
from .module_import_service import ModuleImportService
from .project_state import ProjectState


MODULE_INPUT_SCHEMA_VERSION = 1


def migrate_legacy_module_inputs(project_state):
    """根据每个算例的历史 CaseData 补齐缺失模块状态。迁移不会改变修订号：它只解释已保存输入，因此不能让原本可用的 Dataset 变为过期。已有模块状态始终优先于旧版快照。"""

    report = {
        "schema_version": MODULE_INPUT_SCHEMA_VERSION,
        "migrated_case_count": 0,
        "migrated_module_count": 0,
        "cases": {},
    }
    if project_state is None:
        return report

    module_keys = tuple(
        spec.key for spec in MODULE_SPECS
        if spec.accepts_case_keywords
        and spec.key not in {
            MODULE_MODEL_CONFIGURATION,
            MODULE_HISTORY_MATCHING,
        }
    )

    snapshots = []
    try:
        for case in list(getattr(project_state, "cases", []) or []):
            input_state = case.input_state
            missing = tuple(
                key for key in module_keys
                if key not in input_state.module_inputs
            )
            if not missing:
                continue

            source_path = _legacy_case_data_source(
                input_state, case.case_id)
            if not source_path:
                continue
            if source_path != os.path.abspath(input_state.case_data_path or ""):
                snapshots.append(source_path)

            staging = ProjectState(project_name="legacy-module-migration")
            staging_case = staging.add_case(
                case_name=case.case_name,
                input_state=copy.deepcopy(input_state),
            )
            # 解析器建立预期网格单元数等跨模块事实时，
            # 只修改分离的暂存状态。
            service = ModuleImportService(staging)
            migrated = []
            skipped = []
            for module_key in missing:
                result = service.import_module(module_key, source_path)
                if result.success and result.state is not None:
                    migrated.append(module_key)
                else:
                    skipped.append(module_key)

            if not migrated:
                continue
            merged = dict(input_state.module_inputs)
            for module_key in migrated:
                merged[module_key] = copy.deepcopy(
                    staging_case.input_state.module_inputs[module_key])
            input_state.module_inputs = merged

            report["migrated_case_count"] += 1
            report["migrated_module_count"] += len(migrated)
            report["cases"][case.case_id] = {
                "migrated_modules": migrated,
                "skipped_modules": skipped,
            }
    finally:
        for path in snapshots:
            try:
                os.remove(path)
            except OSError:
                pass
    return report


def _legacy_case_data_source(input_state, case_id):
    source_path = os.path.abspath(input_state.case_data_path or "") \
        if input_state.case_data_path else ""
    if not input_state.case_data_sections:
        return source_path if source_path and os.path.isfile(source_path) else ""

    case_data = case_data_from_dict({
        "path": source_path,
        "base_dir": os.path.dirname(source_path) if source_path else "",
        "sections": copy.deepcopy(input_state.case_data_sections),
        "schema": copy.deepcopy(input_state.case_data_schema),
    })
    target = os.path.join(
        tempfile.gettempdir(),
        f"oil_module_migration_{case_id or 'legacy'}_{uuid.uuid4().hex}.txt",
    )
    try:
        return export_case_data_snapshot(case_data, target)
    except (OSError, ValueError):
        try:
            os.remove(target)
        except OSError:
            pass
        return source_path if source_path and os.path.isfile(source_path) else ""


__all__ = ["MODULE_INPUT_SCHEMA_VERSION", "migrate_legacy_module_inputs"]
