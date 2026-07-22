# -*- coding: utf-8 -*-
"""兼容导入仍存放在 uniform_data 中的显式参数。

本服务会主动忽略所有文件定位参数。关键字文件由独立的内容关键字导入链路
负责；uniform_data 仅临时保留，用于尚无独立文件来源的标量和列表参数。
"""

import copy
import os

from .case_data_parser import parse_case_data
from .input_keyword_registry import (
    MODULE_SPEC_BY_KEY,
    PARSER_LIST,
    PARSER_SCALAR,
    STATE_SCOPE_MODULE_INPUT,
    keyword_rules_for_module,
)
from .input_source_registry import SOURCE_MODE_KEYWORD_FILE
from .module_import_service import validate_module_business_data
from .module_input_models import (
    ModuleImportResult,
    ModuleInputState,
    ModuleParsedData,
)


SOURCE_MODE_UNIFORM_EXPLICIT = "uniform_explicit"


def has_explicit_parameter_rules(module_key):
    """Return whether uniform_data still owns values for this module."""

    return any(
        rule.parser_kind in {PARSER_SCALAR, PARSER_LIST}
        and rule.value_type != "path"
        and rule.state_scope == STATE_SCOPE_MODULE_INPUT
        for rule in keyword_rules_for_module(
            str(module_key or ""), importable_only=True)
    )


class ExplicitParameterImportService:
    """Merge explicit CaseData values into one module without touching files."""

    def __init__(self, project_state=None):
        self.project_state = project_state

    def import_module(self, module_key, case_data_path):
        """Prepare, validate and atomically commit one module when possible."""

        prepared = self.prepare_module(module_key, case_data_path)
        if not prepared.success or prepared.state is None:
            return prepared
        if self.project_state is None:
            return prepared
        try:
            committed = self.project_state.replace_module_input_state(
                prepared.module_key, prepared.state)
        except (TypeError, ValueError):
            return ModuleImportResult(
                module_key=prepared.module_key,
                success=False,
                errors=("显式参数无法提交，原有数据已保留。",),
                warnings=prepared.warnings,
                replaced_revision=prepared.replaced_revision,
            )
        return ModuleImportResult(
            module_key=prepared.module_key,
            success=True,
            state=committed,
            warnings=prepared.warnings,
            replaced_revision=prepared.replaced_revision,
        )

    def prepare_module(self, module_key, case_data_path):
        """Build an isolated merged draft and never mutate ``ProjectState``."""

        module_key = str(module_key or "")
        previous = (
            self.project_state.get_module_input_state(module_key)
            if self.project_state is not None else None
        )
        replaced_revision = previous.revision if previous is not None else 0
        candidate, errors, warnings = self._build_candidate(
            module_key, case_data_path, previous)
        if candidate is None:
            return ModuleImportResult(
                module_key=module_key,
                success=False,
                errors=tuple(errors),
                warnings=tuple(warnings),
                replaced_revision=replaced_revision,
            )
        return ModuleImportResult(
            module_key=module_key,
            success=True,
            state=candidate,
            warnings=tuple(warnings),
            replaced_revision=replaced_revision,
        )

    def _build_candidate(self, module_key, case_data_path, previous):
        module = MODULE_SPEC_BY_KEY.get(module_key)
        if module is None or not module.accepts_case_keywords:
            return None, ["当前节点不支持显式参数导入。"], []

        source_path = os.path.abspath(str(case_data_path or "").strip())
        if not source_path or not os.path.isfile(source_path):
            return None, ["无法读取所选数据。"], []

        case_data = parse_case_data(source_path)
        if case_data.errors:
            return None, ["所选数据格式无效。"], []

        explicit_rules = tuple(
            rule for rule in keyword_rules_for_module(
                module_key, importable_only=True)
            if rule.parser_kind in {PARSER_SCALAR, PARSER_LIST}
            and rule.value_type != "path"
            and rule.state_scope == STATE_SCOPE_MODULE_INPUT
        )
        if not explicit_rules:
            return None, ["当前模块没有需要从 uniform_data 导入的显式参数。"], []

        keyword_index = _keyword_index(case_data)
        found = {
            rule: keyword_index[rule.identity]
            for rule in explicit_rules
            if rule.identity in keyword_index
        }
        if not found:
            return None, ["所选数据中没有当前模块可导入的显式参数。"], []

        imported_values = {}
        errors = []
        for rule, keyword in found.items():
            try:
                imported_values[rule.parsed_key] = _coerce_explicit_value(
                    keyword.value,
                    keyword.raw_value,
                    rule.value_type,
                    rule.parser_kind,
                )
            except (TypeError, ValueError, OverflowError):
                errors.append(f"{rule.title}的数值格式无效。")
        if errors:
            return None, errors, []

        candidate = (
            ModuleInputState.from_dict(previous, module_key)
            if previous is not None
            else ModuleInputState(module_key=module_key)
        )
        merged_values = copy.deepcopy(candidate.parsed_data.values)
        merged_values.update(copy.deepcopy(imported_values))

        business_validation = validate_module_business_data(
            module_key, merged_values)
        if not business_validation["ok"]:
            return None, list(business_validation["errors"]), list(
                business_validation["warnings"])

        merged_raw_values = copy.deepcopy(candidate.raw_values)
        # Old whole-CaseData imports stored locator values here.  They must no
        # longer be eligible input after this compatibility import.
        for rule in keyword_rules_for_module(
                module_key, importable_only=True):
            if (rule.value_type == "path"
                    or rule.parser_kind not in {PARSER_SCALAR, PARSER_LIST}):
                merged_raw_values.pop(rule.qualified_name, None)
        for rule, keyword in found.items():
            merged_raw_values[rule.qualified_name] = keyword.raw_value

        merged_source = copy.deepcopy(candidate.source)
        # Preserve only sources produced by the new content-keyword path.
        # Unmarked records are legacy uniform_data locators and would otherwise
        # still be consumed by Dataset assembly.
        keyword_sources = {
            name: copy.deepcopy(record)
            for name, record in (
                (merged_source.get("keywords") or {}).items())
            if isinstance(record, dict)
            and record.get("source_mode") == SOURCE_MODE_KEYWORD_FILE
        }
        if keyword_sources:
            merged_source["keywords"] = keyword_sources
        else:
            merged_source.pop("keywords", None)
        explicit_sources = dict(
            merged_source.get("explicit_parameters") or {})
        for rule, keyword in found.items():
            explicit_sources[rule.qualified_name] = {
                "source_mode": SOURCE_MODE_UNIFORM_EXPLICIT,
                "raw_value": keyword.raw_value,
                "source_path": source_path,
                "line_number": int(keyword.line_number or 0),
            }
        merged_source["explicit_parameters"] = explicit_sources
        merged_source["explicit_parameter_source"] = _source_record(
            source_path)

        current_validation = copy.deepcopy(candidate.validation)
        checks = dict(current_validation.get("checks") or {})
        checks.update(business_validation["checks"])
        warnings = list(dict.fromkeys(
            list(current_validation.get("warnings") or [])
            + list(business_validation["warnings"])
        ))
        current_validation.update({
            "ok": True,
            "errors": [],
            "warnings": warnings,
            "checks": checks,
            "imported_value_count": len(found),
            "explicit_imported_value_count": len(found),
        })

        candidate.raw_values = merged_raw_values
        candidate.parsed_data = ModuleParsedData(values=merged_values)
        candidate.validation = current_validation
        candidate.source = merged_source
        candidate.dirty = False
        return candidate, [], warnings


def _keyword_index(case_data):
    index = {}
    for section in case_data.sections:
        section_name = str(section.name or "").strip().upper()
        for keyword in section.keywords:
            identity = (section_name, str(keyword.key or "").strip().lower())
            index[identity] = keyword
    return index


def _coerce_explicit_value(value, raw_value, value_type, parser_kind):
    if parser_kind == PARSER_LIST:
        if isinstance(value, list):
            return list(value)
        text = str(raw_value or "").replace(",", " ")
        return [float(token) for token in text.split() if token]
    if value_type == "bool":
        if isinstance(value, bool):
            return value
        text = str(value).strip().lower()
        if text in {"true", "1", "yes", "on"}:
            return True
        if text in {"false", "0", "no", "off"}:
            return False
        raise ValueError("invalid bool")
    if value_type == "int":
        if isinstance(value, bool):
            raise ValueError("invalid int")
        number = float(value)
        if not number.is_integer():
            raise ValueError("invalid int")
        return int(number)
    if value_type == "float":
        if isinstance(value, bool):
            raise ValueError("invalid float")
        return float(value)
    return value


def _source_record(source_path):
    try:
        stat = os.stat(source_path)
        source_size = int(stat.st_size)
        modified_ns = int(stat.st_mtime_ns)
    except OSError:
        source_size = 0
        modified_ns = 0
    return {
        "source_mode": SOURCE_MODE_UNIFORM_EXPLICIT,
        "source_path": source_path,
        "source_size": source_size,
        "modified_ns": modified_ns,
    }


__all__ = [
    "ExplicitParameterImportService",
    "SOURCE_MODE_UNIFORM_EXPLICIT",
    "has_explicit_parameter_rules",
]
