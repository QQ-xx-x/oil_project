# -*- coding: utf-8 -*-
"""定义分阶段导入流程使用的关键字文件输入规范。

本注册表描述用户所选数据文件内部的关键字。它与
:mod:`input_keyword_registry` 相互独立；后者包含用于描述旧版
CaseData/uniform_data 清单的路径型规则。
"""

from dataclasses import dataclass
import re
from typing import Optional, Tuple

from .input_keyword_registry import MODULE_GRID_SPATIAL


SOURCE_MODE_KEYWORD_FILE = "keyword_file"

PARSER_NUMERIC_ARRAY = "numeric_array"
PARSER_KEYWORD_BUNDLE = "keyword_bundle"
VALID_FILE_PARSER_KINDS = frozenset((
    PARSER_NUMERIC_ARRAY,
    PARSER_KEYWORD_BUNDLE,
))

_KEYWORD_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")


def normalize_content_keyword(keyword: str) -> str:
    """Return the case-insensitive identity used for file-content keywords."""

    return str(keyword or "").strip().strip("'\"").upper()


@dataclass(frozen=True)
class KeywordFileSpec:
    """Contract for importing one business field from one selected file."""

    module_key: str
    value_key: str
    title: str
    parser_kind: str
    required_keywords: Tuple[str, ...]
    optional_keywords: Tuple[str, ...] = ()
    source_mode: str = SOURCE_MODE_KEYWORD_FILE

    def __post_init__(self):
        object.__setattr__(
            self,
            "required_keywords",
            _normalized_unique(self.required_keywords),
        )
        object.__setattr__(
            self,
            "optional_keywords",
            _normalized_unique(self.optional_keywords),
        )

    @property
    def identity(self) -> Tuple[str, str]:
        return str(self.module_key or ""), str(self.value_key or "")

    @property
    def accepted_keywords(self) -> Tuple[str, ...]:
        return self.required_keywords + tuple(
            keyword
            for keyword in self.optional_keywords
            if keyword not in self.required_keywords
        )


def _normalized_unique(keywords) -> Tuple[str, ...]:
    result = []
    for keyword in keywords or ():
        normalized = normalize_content_keyword(keyword)
        if normalized and normalized not in result:
            result.append(normalized)
    return tuple(result)


# The first milestone intentionally registers only the geometry and grid
# properties whose intrinsic file keywords have already been confirmed by the
# existing input fixtures.  No aliases (for example PORO/PERMX) are accepted
# until the external file contract explicitly confirms them.
KEYWORD_FILE_SPECS = (
    KeywordFileSpec(
        MODULE_GRID_SPATIAL,
        "grid",
        "角点网格",
        PARSER_KEYWORD_BUNDLE,
        ("SPECGRID", "COORD", "ZCORN"),
        ("ACTNUM",),
    ),
    KeywordFileSpec(
        MODULE_GRID_SPATIAL,
        "matrix_phi",
        "基质孔隙度",
        PARSER_NUMERIC_ARRAY,
        ("MATRIX_PORO",),
    ),
    KeywordFileSpec(
        MODULE_GRID_SPATIAL,
        "matrix_kx",
        "基质 X 向渗透率",
        PARSER_NUMERIC_ARRAY,
        ("MATRIX_PERMX",),
    ),
    KeywordFileSpec(
        MODULE_GRID_SPATIAL,
        "matrix_ky",
        "基质 Y 向渗透率",
        PARSER_NUMERIC_ARRAY,
        ("MATRIX_PERMY",),
    ),
    KeywordFileSpec(
        MODULE_GRID_SPATIAL,
        "matrix_kz",
        "基质 Z 向渗透率",
        PARSER_NUMERIC_ARRAY,
        ("MATRIX_PERMZ",),
    ),
    KeywordFileSpec(
        MODULE_GRID_SPATIAL,
        "actnum",
        "网格启用状态",
        PARSER_NUMERIC_ARRAY,
        ("ACTNUM",),
    ),
)

KEYWORD_FILE_SPEC_BY_IDENTITY = {
    spec.identity: spec for spec in KEYWORD_FILE_SPECS
}


def get_keyword_file_spec(module_key: str, value_key: str) \
        -> Optional[KeywordFileSpec]:
    return KEYWORD_FILE_SPEC_BY_IDENTITY.get((
        str(module_key or ""), str(value_key or "")))


def keyword_file_specs_for_module(module_key: str) -> Tuple[KeywordFileSpec, ...]:
    target = str(module_key or "")
    return tuple(
        spec for spec in KEYWORD_FILE_SPECS if spec.module_key == target)


def keyword_file_specs_for_content_keyword(keyword: str) \
        -> Tuple[KeywordFileSpec, ...]:
    target = normalize_content_keyword(keyword)
    return tuple(
        spec for spec in KEYWORD_FILE_SPECS
        if target in spec.accepted_keywords
    )


def registered_content_keywords() -> Tuple[str, ...]:
    result = []
    for spec in KEYWORD_FILE_SPECS:
        for keyword in spec.accepted_keywords:
            if keyword not in result:
                result.append(keyword)
    return tuple(result)


def keyword_file_registry_issues() -> Tuple[str, ...]:
    issues = []
    seen = set()
    for spec in KEYWORD_FILE_SPECS:
        if spec.identity in seen:
            issues.append(f"duplicate field identity: {spec.identity!r}")
        seen.add(spec.identity)
        if not spec.module_key or not spec.value_key or not spec.title:
            issues.append(f"incomplete file spec: {spec.identity!r}")
        if spec.source_mode != SOURCE_MODE_KEYWORD_FILE:
            issues.append(f"invalid source mode: {spec.identity!r}")
        if spec.parser_kind not in VALID_FILE_PARSER_KINDS:
            issues.append(f"invalid parser kind: {spec.identity!r}")
        if not spec.required_keywords:
            issues.append(f"missing required keywords: {spec.identity!r}")
        overlap = set(spec.required_keywords) & set(spec.optional_keywords)
        if overlap:
            issues.append(
                f"required/optional keyword overlap: {spec.identity!r} {sorted(overlap)!r}")
        for keyword in spec.accepted_keywords:
            if not _KEYWORD_RE.fullmatch(keyword):
                issues.append(
                    f"invalid content keyword: {spec.identity!r} {keyword!r}")
    return tuple(issues)


__all__ = [
    "KEYWORD_FILE_SPECS",
    "PARSER_KEYWORD_BUNDLE",
    "PARSER_NUMERIC_ARRAY",
    "SOURCE_MODE_KEYWORD_FILE",
    "KeywordFileSpec",
    "get_keyword_file_spec",
    "keyword_file_registry_issues",
    "keyword_file_specs_for_content_keyword",
    "keyword_file_specs_for_module",
    "normalize_content_keyword",
    "registered_content_keywords",
]
