# -*- coding: utf-8 -*-
"""Targeted CaseData import used by the model-configuration window."""

import os

from .case_data_parser import parse_case_data
from .input_keyword_registry import (
    MODULE_MODEL_CONFIGURATION,
    keyword_rules_for_module,
)


class ModelConfigImportError(ValueError):
    """The selected data cannot provide valid model-configuration values."""


def load_lgr_model_config_values(path):
    """Read only registered ``LGR.*`` values from one CaseData source.

    Other sections—including WR property locators—are deliberately ignored.
    The returned mapping uses persistent model-config keys and contains no
    source filename, path, section name, or raw keyword record.
    """

    source = os.path.abspath(str(path or "").strip())
    if not source or not os.path.isfile(source):
        raise ModelConfigImportError("无法读取所选数据。")

    case_data = parse_case_data(source)
    if case_data.errors:
        raise ModelConfigImportError("所选数据格式无效。")

    lgr_rules = tuple(
        rule for rule in keyword_rules_for_module(
            MODULE_MODEL_CONFIGURATION, importable_only=True)
        if rule.section.upper() == "LGR"
    )
    section = case_data.section("LGR")
    if section is None:
        raise ModelConfigImportError("所选数据中没有可导入的 LGR 参数。")

    available = {
        str(keyword.key or "").strip().lower(): keyword.value
        for keyword in section.keywords
    }
    values = {}
    for rule in lgr_rules:
        lookup_key = rule.keyword.lower()
        if lookup_key not in available:
            continue
        try:
            values[rule.state_key] = _coerce_value(
                available[lookup_key], rule.value_type)
        except (TypeError, ValueError) as exc:
            raise ModelConfigImportError(
                "LGR 参数中存在无法识别的数值。") from exc

    if not values:
        raise ModelConfigImportError("所选数据中没有可导入的 LGR 参数。")
    return values


def _coerce_value(value, value_type):
    if value_type == "bool":
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)) and value in (0, 1):
            return bool(value)
        text = str(value).strip().lower()
        if text in {"true", "1", "yes", "on"}:
            return True
        if text in {"false", "0", "no", "off"}:
            return False
        raise ValueError("invalid bool")
    if value_type == "float":
        if isinstance(value, bool):
            raise ValueError("invalid float")
        number = float(value)
        if number < 0:
            raise ValueError("negative value")
        return number
    if value_type == "int":
        if isinstance(value, bool):
            raise ValueError("invalid int")
        number = float(value)
        if not number.is_integer() or number < 1:
            raise ValueError("invalid positive int")
        return int(number)
    return value
