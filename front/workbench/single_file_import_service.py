# -*- coding: utf-8 -*-
"""为已选定的单个业务字段准备一次关键字文件导入。"""

from dataclasses import dataclass, field
import hashlib
import math
import os
from typing import Tuple

from .input_source_registry import (
    PARSER_KEYWORD_BUNDLE,
    PARSER_NUMERIC_ARRAY,
    SOURCE_MODE_KEYWORD_FILE,
    get_keyword_file_spec,
)
from .keyword_file_parser import (
    KeywordFileParseError,
    parse_keyword_array,
    parse_numeric_block,
    scan_keyword_blocks,
)


@dataclass(frozen=True)
class SingleFileImportResult:
    module_key: str
    value_key: str
    success: bool
    values: Tuple[float, ...] = ()
    data: object = None
    source: dict = field(default_factory=dict)
    errors: Tuple[str, ...] = ()
    error_code: str = ""


class SingleFileImportService:
    """Validate one file against the intrinsic keyword of one target field.

    The service never mutates ``ProjectState``.  Callers can normalize business
    units and atomically commit the returned draft only after ``success``.
    """

    def prepare(self, module_key, value_key, file_path, *, expected_len=None):
        module_key = str(module_key or "")
        value_key = str(value_key or "")
        spec = get_keyword_file_spec(module_key, value_key)
        if spec is None:
            return self._failure(
                module_key, value_key, "unsupported_field",
                "当前属性尚未注册关键字文件导入规则。")
        if spec.parser_kind == PARSER_KEYWORD_BUNDLE:
            return self._prepare_keyword_bundle(
                spec, module_key, value_key, file_path)
        if spec.parser_kind != PARSER_NUMERIC_ARRAY:
            return self._failure(
                module_key, value_key, "unsupported_parser",
                "当前属性的关键字文件解析方式尚未实现。")

        try:
            parsed = parse_keyword_array(
                file_path,
                spec.required_keywords,
                expected_len=expected_len,
            )
        except KeywordFileParseError as exc:
            return self._failure(
                module_key, value_key, exc.code, str(exc))

        source = self._source_record(
            parsed.path,
            module_key=module_key,
            value_key=value_key,
            expected_keywords=spec.required_keywords,
            detected_keyword=parsed.keyword,
            detected_keywords=parsed.detected_keywords,
        )
        return SingleFileImportResult(
            module_key=module_key,
            value_key=value_key,
            success=True,
            values=parsed.values,
            source=source,
        )

    def _prepare_keyword_bundle(self, spec, module_key, value_key, file_path):
        try:
            scan = scan_keyword_blocks(file_path)
            by_keyword = self._validate_bundle(scan, spec)
            grid = self._grid_from_blocks(scan, by_keyword, spec)
        except KeywordFileParseError as exc:
            return self._failure(
                module_key, value_key, exc.code, str(exc))

        source = self._source_record(
            scan.path,
            module_key=module_key,
            value_key=value_key,
            expected_keywords=spec.required_keywords,
            detected_keyword="",
            detected_keywords=scan.detected_keywords,
        )
        return SingleFileImportResult(
            module_key=module_key,
            value_key=value_key,
            success=True,
            data=grid,
            source=source,
        )

    @staticmethod
    def _validate_bundle(scan, spec):
        by_keyword = {}
        missing = []
        for keyword in spec.required_keywords:
            blocks = scan.blocks_for((keyword,))
            if not blocks:
                missing.append(keyword)
            elif len(blocks) > 1:
                raise KeywordFileParseError(
                    "duplicate_keyword",
                    f"角点网格文件中关键字 {keyword} 重复出现。",
                    path=scan.path,
                    line_number=blocks[1].start_line,
                    expected_keywords=spec.required_keywords,
                    detected_keywords=scan.detected_keywords,
                )
            else:
                by_keyword[keyword] = blocks[0]
        if missing:
            raise KeywordFileParseError(
                "missing_required_keywords",
                f"角点网格文件缺少关键字：{', '.join(missing)}。",
                path=scan.path,
                expected_keywords=spec.required_keywords,
                detected_keywords=scan.detected_keywords,
            )

        for keyword in spec.optional_keywords:
            blocks = scan.blocks_for((keyword,))
            if len(blocks) > 1:
                raise KeywordFileParseError(
                    "duplicate_keyword",
                    f"角点网格文件中关键字 {keyword} 重复出现。",
                    path=scan.path,
                    line_number=blocks[1].start_line,
                    expected_keywords=spec.required_keywords,
                    detected_keywords=scan.detected_keywords,
                )
            if blocks:
                by_keyword[keyword] = blocks[0]
        return by_keyword

    @staticmethod
    def _grid_from_blocks(scan, by_keyword, spec):
        specgrid = by_keyword["SPECGRID"]
        if len(specgrid.tokens) < 3:
            raise KeywordFileParseError(
                "invalid_specgrid",
                "SPECGRID 至少需要 Nx、Ny、Nz 三个维度值。",
                path=scan.path,
                line_number=specgrid.start_line,
                expected_keywords=spec.required_keywords,
                detected_keywords=scan.detected_keywords,
            )
        try:
            dimensions = []
            for token in specgrid.tokens[:3]:
                number = float(str(token).replace("D", "E").replace("d", "e"))
                integer = int(number)
                if not math.isfinite(number) or number != integer or integer <= 0:
                    raise ValueError
                dimensions.append(integer)
            nx, ny, nz = dimensions
        except (TypeError, ValueError, OverflowError) as exc:
            raise KeywordFileParseError(
                "invalid_specgrid",
                "SPECGRID 的 Nx、Ny、Nz 必须是大于零的整数。",
                path=scan.path,
                line_number=specgrid.start_line,
                expected_keywords=spec.required_keywords,
                detected_keywords=scan.detected_keywords,
            ) from exc

        coord = parse_numeric_block(
            by_keyword["COORD"],
            path=scan.path,
            expected_keywords=spec.required_keywords,
            detected_keywords=scan.detected_keywords,
        )
        zcorn = parse_numeric_block(
            by_keyword["ZCORN"],
            path=scan.path,
            expected_keywords=spec.required_keywords,
            detected_keywords=scan.detected_keywords,
        )
        actnum_values = ()
        if "ACTNUM" in by_keyword:
            actnum_values = parse_numeric_block(
                by_keyword["ACTNUM"],
                path=scan.path,
                expected_keywords=spec.required_keywords,
                detected_keywords=scan.detected_keywords,
            )
        actnum = [int(value) for value in actnum_values]
        total = nx * ny * nz
        active_count = sum(value == 1 for value in actnum)
        return {
            "nx": nx,
            "ny": ny,
            "nz": nz,
            "total_cell_count": total,
            "coord": list(coord),
            "zcorn": list(zcorn),
            "actnum": actnum,
            "active_cell_count": active_count,
            # Preserve the existing parse_grid summary semantics: omitted or
            # non-active ACTNUM entries count toward the inactive total.
            "inactive_cell_count": total - active_count,
            "active_cell_indices": [
                index for index, value in enumerate(actnum) if value == 1],
            "inactive_cell_indices": [
                index for index, value in enumerate(actnum) if value == 0],
        }

    @staticmethod
    def _source_record(path, *, module_key, value_key, expected_keywords,
                       detected_keyword, detected_keywords):
        absolute_path = os.path.abspath(path)
        try:
            stat = os.stat(absolute_path)
            source_size = int(stat.st_size)
            modified_ns = int(stat.st_mtime_ns)
            source_sha256 = _sha256_file(absolute_path)
        except OSError:
            source_size = 0
            modified_ns = 0
            source_sha256 = ""
        return {
            # Keep the legacy keys until the later state/Dataset migration.
            "raw_value": absolute_path,
            "resolved_path": absolute_path,
            "exists": os.path.isfile(absolute_path),
            # New provenance proves that the file was identified by content.
            "source_mode": SOURCE_MODE_KEYWORD_FILE,
            "module_key": module_key,
            "value_key": value_key,
            "expected_keywords": list(expected_keywords),
            "detected_keyword": detected_keyword,
            "detected_keywords": list(detected_keywords),
            "source_size": source_size,
            "modified_ns": modified_ns,
            "source_sha256": source_sha256,
        }

    @staticmethod
    def _failure(module_key, value_key, error_code, message):
        return SingleFileImportResult(
            module_key=module_key,
            value_key=value_key,
            success=False,
            errors=(str(message or "属性数据无法解析。"),),
            error_code=str(error_code or "single_file_import_error"),
        )


def _sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


__all__ = ["SingleFileImportResult", "SingleFileImportService"]
