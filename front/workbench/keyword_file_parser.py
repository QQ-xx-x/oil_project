# -*- coding: utf-8 -*-
"""扫描并解析用户所选输入文件中的关键字数据块。

扫描过程不依赖文件名、扩展名或 Qt。只有已注册关键字位于逻辑数据块开头时
才会被识别，随后持续读取数据，直至遇到 Eclipse 风格的 ``/`` 结束符。
"""

from dataclasses import dataclass
import math
import os
import re
from typing import Iterable, Optional, Tuple

from .input_source_registry import (
    normalize_content_keyword,
    registered_content_keywords,
)


_TOKEN_RE = re.compile(r"/|[^\s/]+")


class KeywordFileParseError(ValueError):
    """Structured, user-safe failure raised while reading a keyword file."""

    def __init__(self, code, message, *, path="", line_number=0,
                 expected_keywords=(), detected_keywords=()):
        super().__init__(str(message or code))
        self.code = str(code or "keyword_file_error")
        self.path = os.path.abspath(path) if path else ""
        self.line_number = max(0, int(line_number or 0))
        self.expected_keywords = _normalize_keywords(expected_keywords)
        self.detected_keywords = _normalize_keywords(detected_keywords)


@dataclass(frozen=True)
class KeywordBlock:
    keyword: str
    tokens: Tuple[str, ...]
    start_line: int
    end_line: int


@dataclass(frozen=True)
class KeywordFileScan:
    path: str
    blocks: Tuple[KeywordBlock, ...]

    @property
    def detected_keywords(self) -> Tuple[str, ...]:
        result = []
        for block in self.blocks:
            if block.keyword not in result:
                result.append(block.keyword)
        return tuple(result)

    def blocks_for(self, keywords: Iterable[str]) -> Tuple[KeywordBlock, ...]:
        expected = set(_normalize_keywords(keywords))
        return tuple(
            block for block in self.blocks if block.keyword in expected)


@dataclass(frozen=True)
class KeywordArrayData:
    path: str
    keyword: str
    values: Tuple[float, ...]
    block: KeywordBlock
    detected_keywords: Tuple[str, ...]


def scan_keyword_blocks(path: str, known_keywords: Optional[Iterable[str]] = None) \
        -> KeywordFileScan:
    """Return all recognized, slash-terminated blocks in one text file."""

    absolute_path = os.path.abspath(str(path or "").strip())
    if not absolute_path:
        raise KeywordFileParseError(
            "empty_path", "关键字文件路径为空。")

    known = set(_normalize_keywords(
        registered_content_keywords()
        if known_keywords is None else known_keywords))
    if not known:
        raise KeywordFileParseError(
            "empty_keyword_set", "没有可用于扫描的内容关键字。",
            path=absolute_path)

    try:
        with open(absolute_path, "r", encoding="utf-8-sig") as file:
            lines = file.readlines()
    except UnicodeError as exc:
        raise KeywordFileParseError(
            "invalid_encoding", "关键字文件不是有效的 UTF-8 文本。",
            path=absolute_path) from exc
    except OSError as exc:
        raise KeywordFileParseError(
            "unreadable_file", f"无法读取关键字文件：{exc}",
            path=absolute_path) from exc

    blocks = []
    active_keyword = ""
    active_tokens = []
    active_start_line = 0

    for line_number, raw_line in enumerate(lines, start=1):
        tokens = _TOKEN_RE.findall(_strip_comment(raw_line))
        index = 0
        while index < len(tokens):
            token = tokens[index]
            if not active_keyword:
                candidate = normalize_content_keyword(token)
                # A keyword must begin the remaining logical statement.  If
                # the first token is not registered, ignore the rest of that
                # line so comments/header prose cannot trigger a match.
                if candidate not in known:
                    break
                active_keyword = candidate
                active_tokens = []
                active_start_line = line_number
                index += 1
                continue

            if token == "/":
                blocks.append(KeywordBlock(
                    keyword=active_keyword,
                    tokens=tuple(active_tokens),
                    start_line=active_start_line,
                    end_line=line_number,
                ))
                active_keyword = ""
                active_tokens = []
                active_start_line = 0
                index += 1
                continue

            candidate = normalize_content_keyword(token)
            if candidate in known:
                raise KeywordFileParseError(
                    "unterminated_block",
                    f"关键字 {active_keyword} 的数据块在关键字 {candidate} 前缺少 / 结束符。",
                    path=absolute_path,
                    line_number=line_number,
                    detected_keywords=tuple(
                        block.keyword for block in blocks) + (active_keyword, candidate),
                )

            active_tokens.append(token)
            index += 1

    if active_keyword:
        raise KeywordFileParseError(
            "unterminated_block",
            f"关键字 {active_keyword} 的数据块缺少 / 结束符。",
            path=absolute_path,
            line_number=active_start_line,
            detected_keywords=tuple(
                block.keyword for block in blocks) + (active_keyword,),
        )

    return KeywordFileScan(
        path=absolute_path,
        blocks=tuple(blocks),
    )


def parse_keyword_array(path: str, expected_keywords: Iterable[str], *,
                        expected_len: Optional[int] = None) -> KeywordArrayData:
    """Parse exactly one numeric block matching ``expected_keywords``."""

    if isinstance(expected_keywords, str):
        expected_keywords = (expected_keywords,)
    expected = _normalize_keywords(expected_keywords)
    if not expected:
        raise KeywordFileParseError(
            "empty_expected_keywords", "没有指定期望的数据关键字。",
            path=str(path or ""))

    known = tuple(dict.fromkeys(
        registered_content_keywords() + expected))
    scan = scan_keyword_blocks(path, known)
    matches = scan.blocks_for(expected)
    if not matches:
        detected = scan.detected_keywords
        code = "keyword_mismatch" if detected else "missing_keyword"
        detail = (
            f"，实际检测到：{', '.join(detected)}" if detected else "")
        raise KeywordFileParseError(
            code,
            f"文件中没有找到期望关键字：{', '.join(expected)}{detail}。",
            path=scan.path,
            expected_keywords=expected,
            detected_keywords=detected,
        )
    if len(matches) > 1:
        raise KeywordFileParseError(
            "duplicate_keyword",
            f"文件中出现了多个期望属性数据块：{', '.join(block.keyword for block in matches)}。",
            path=scan.path,
            line_number=matches[1].start_line,
            expected_keywords=expected,
            detected_keywords=scan.detected_keywords,
        )

    block = matches[0]
    values = parse_numeric_block(
        block,
        path=scan.path,
        expected_keywords=expected,
        detected_keywords=scan.detected_keywords,
    )

    if expected_len is not None:
        expected_count = int(expected_len)
        if len(values) != expected_count:
            raise KeywordFileParseError(
                "length_mismatch",
                f"关键字 {block.keyword} 的数值数量 {len(values)} 与预期 {expected_count} 不一致。",
                path=scan.path,
                line_number=block.start_line,
                expected_keywords=expected,
                detected_keywords=scan.detected_keywords,
            )

    return KeywordArrayData(
        path=scan.path,
        keyword=block.keyword,
        values=values,
        block=block,
        detected_keywords=scan.detected_keywords,
    )


def parse_numeric_block(block: KeywordBlock, *, path="",
                        expected_keywords=(), detected_keywords=()) \
        -> Tuple[float, ...]:
    """Expand one already-scanned numeric block without reading the file again."""

    if not block.tokens:
        raise KeywordFileParseError(
            "empty_block",
            f"关键字 {block.keyword} 的数据块为空。",
            path=path,
            line_number=block.start_line,
            expected_keywords=expected_keywords,
            detected_keywords=detected_keywords,
        )

    values = []
    for token in block.tokens:
        values.extend(_expand_numeric_token(
            token,
            path=path,
            line_number=block.start_line,
            keyword=block.keyword,
            expected_keywords=expected_keywords,
            detected_keywords=detected_keywords,
        ))
    return tuple(values)


def _strip_comment(line: str) -> str:
    cut_positions = [
        position for marker in ("--", "//")
        if (position := line.find(marker)) >= 0
    ]
    if cut_positions:
        return line[:min(cut_positions)]
    return line


def _normalize_keywords(keywords: Iterable[str]) -> Tuple[str, ...]:
    result = []
    for keyword in keywords or ():
        normalized = normalize_content_keyword(keyword)
        if normalized and normalized not in result:
            result.append(normalized)
    return tuple(result)


def _expand_numeric_token(token, *, path, line_number, keyword,
                          expected_keywords, detected_keywords):
    text = str(token or "").strip().rstrip(",")
    try:
        if "*" in text:
            count_text, value_text = text.split("*", 1)
            count = int(count_text)
            if count < 0 or not value_text:
                raise ValueError
            value = _finite_float(value_text)
            return [value] * count
        return [_finite_float(text)]
    except (TypeError, ValueError, OverflowError) as exc:
        raise KeywordFileParseError(
            "invalid_numeric_token",
            f"关键字 {keyword} 中存在无效数值：{token}。",
            path=path,
            line_number=line_number,
            expected_keywords=expected_keywords,
            detected_keywords=detected_keywords,
        ) from exc


def _finite_float(text):
    # Eclipse-style files sometimes use Fortran D exponents.
    value = float(str(text).replace("D", "E").replace("d", "e"))
    if not math.isfinite(value):
        raise ValueError("non-finite value")
    return value


__all__ = [
    "KeywordArrayData",
    "KeywordBlock",
    "KeywordFileParseError",
    "KeywordFileScan",
    "parse_keyword_array",
    "parse_numeric_block",
    "scan_keyword_blocks",
]
