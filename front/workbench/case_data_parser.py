# -*- coding: utf-8 -*-
"""工作台 UI 使用的 CaseData 输入文件解析器。"""

import json
import os
import re
import shutil
import stat
from dataclasses import dataclass, field


SECTION_RE = re.compile(r"^\[([A-Za-z0-9_]+)\]\s*$")
KEY_VALUE_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$")
RLE_RE = re.compile(r"^\d+\*[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?$")
FILE_EXTENSIONS = (".inc", ".txt", ".csv", ".grdecl", ".data", ".json")


@dataclass
class CaseKeyword:
    key: str
    value: object
    raw_value: str
    value_type: str
    original_raw_value: str = ""
    comment: str = ""
    line_number: int = 0
    is_file_ref: bool = False
    file_path: str = ""
    file_exists: bool = False

    def to_dict(self):
        return {
            "key": self.key,
            "value": self.value,
            "raw_value": self.raw_value,
            "original_raw_value": self.original_raw_value,
            "value_type": self.value_type,
            "comment": self.comment,
            "line_number": self.line_number,
            "is_file_ref": self.is_file_ref,
            "file_path": self.file_path,
            "file_exists": self.file_exists,
            "dirty": self.is_dirty(),
        }

    def is_dirty(self):
        return self.raw_value != self.original_raw_value


@dataclass
class CaseSection:
    name: str
    line_number: int = 0
    comment: str = ""
    keywords: list = field(default_factory=list)
    loose_items: list = field(default_factory=list)

    def to_dict(self):
        return {
            "name": self.name,
            "line_number": self.line_number,
            "comment": self.comment,
            "keywords": [item.to_dict() for item in self.keywords],
            "loose_items": list(self.loose_items),
        }


@dataclass
class CaseData:
    path: str = ""
    base_dir: str = ""
    raw_lines: list = field(default_factory=list)
    sections: list = field(default_factory=list)
    schema: dict = field(default_factory=dict)
    errors: list = field(default_factory=list)
    dirty: bool = False

    def section(self, name):
        name = (name or "").upper()
        for section in self.sections:
            if section.name.upper() == name:
                return section
        return None

    def keyword_count(self):
        return sum(len(section.keywords) for section in self.sections)

    def file_refs(self):
        return [
            keyword
            for section in self.sections
            for keyword in section.keywords
            if keyword.is_file_ref
        ]

    def to_dict(self):
        return {
            "path": self.path,
            "base_dir": self.base_dir,
            "sections": [section.to_dict() for section in self.sections],
            "schema": self.schema,
            "errors": list(self.errors),
            "dirty": self.dirty,
        }


def case_data_from_dict(payload, path=None, base_dir=None):
    """从工程快照恢复 CaseData 对象，不重新读取磁盘文件。"""
    payload = payload or {}
    data_path = path if path is not None else payload.get("path", "")
    data_path = os.path.abspath(data_path) if data_path else ""
    data_base_dir = base_dir if base_dir is not None else payload.get("base_dir", "")
    if not data_base_dir and data_path:
        data_base_dir = os.path.dirname(data_path)

    case_data = CaseData(
        path=data_path,
        base_dir=data_base_dir,
        raw_lines=list(payload.get("raw_lines", []) or []),
        schema=dict(payload.get("schema", {}) or {}),
        errors=list(payload.get("errors", []) or []),
        dirty=bool(payload.get("dirty", False)),
    )
    for section_payload in payload.get("sections", []) or []:
        if not isinstance(section_payload, dict):
            continue
        section = CaseSection(
            name=section_payload.get("name", ""),
            line_number=int(section_payload.get("line_number", 0) or 0),
            comment=section_payload.get("comment", ""),
            loose_items=list(section_payload.get("loose_items", []) or []),
        )
        for keyword_payload in section_payload.get("keywords", []) or []:
            keyword = _keyword_from_dict(case_data, keyword_payload)
            if keyword is not None:
                section.keywords.append(keyword)
        case_data.sections.append(section)
    case_data.dirty = case_data.dirty or any(
        keyword.is_dirty()
        for section in case_data.sections
        for keyword in section.keywords
    )
    return case_data


def _keyword_from_dict(case_data, payload):
    """从工程快照恢复单个关键字。"""
    if not isinstance(payload, dict):
        return None
    raw_value = payload.get("raw_value", "")
    if raw_value is None:
        raw_value = ""
    raw_value = str(raw_value)
    value = payload.get("value")
    value_type = payload.get("value_type", "")
    if "value" not in payload or not value_type:
        value, value_type = _parse_value(raw_value)
    keyword = CaseKeyword(
        key=payload.get("key", ""),
        value=value,
        raw_value=raw_value,
        original_raw_value=str(payload.get("original_raw_value", raw_value)),
        value_type=value_type,
        comment=payload.get("comment", ""),
        line_number=int(payload.get("line_number", 0) or 0),
    )
    if "is_file_ref" in payload:
        keyword.is_file_ref = bool(payload.get("is_file_ref"))
        keyword.file_path = payload.get("file_path", "") or ""
        keyword.file_exists = bool(payload.get("file_exists"))
        if keyword.is_file_ref and not keyword.file_path:
            _resolve_file_ref(case_data, keyword)
    else:
        _resolve_file_ref(case_data, keyword)
    return keyword


def parse_case_data(path):
    case_data = CaseData(path=os.path.abspath(path), base_dir=os.path.dirname(os.path.abspath(path)))
    try:
        with open(path, "r", encoding="utf-8-sig") as file:
            lines = file.readlines()
    except OSError as exc:
        case_data.errors.append(f"文件读取失败: {exc}")
        return case_data

    case_data.raw_lines = list(lines)
    current = None
    pending_comments = []
    last_comment_target = None
    in_schema = False
    schema_lines = []

    for line_number, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()
        if in_schema:
            if line == "END_RETURN_SCHEMA_JSON":
                in_schema = False
                _load_schema(case_data, schema_lines)
                schema_lines = []
            else:
                schema_lines.append(raw_line)
            continue

        if line == "BEGIN_RETURN_SCHEMA_JSON":
            in_schema = True
            pending_comments = []
            continue

        if not line:
            continue

        if line.startswith("//"):
            comment = line[2:].strip()
            if current is not None and last_comment_target is not None:
                _append_comment(last_comment_target, comment)
            else:
                pending_comments.append(comment)
            continue

        section_match = SECTION_RE.match(line)
        if section_match:
            current = CaseSection(
                name=section_match.group(1),
                line_number=line_number,
                comment="\n".join(pending_comments).strip(),
            )
            case_data.sections.append(current)
            pending_comments = []
            last_comment_target = None
            continue

        if current is None:
            pending_comments = []
            continue

        content, inline_comment = _split_inline_comment(line)
        key_match = KEY_VALUE_RE.match(content)
        if key_match:
            key = key_match.group(1)
            raw_value = key_match.group(2).strip()
            value, value_type = _parse_value(raw_value)
            comment_parts = list(pending_comments)
            if inline_comment:
                comment_parts.append(inline_comment)
            keyword = CaseKeyword(
                key=key,
                value=value,
                raw_value=raw_value,
                original_raw_value=raw_value,
                value_type=value_type,
                comment="\n".join(comment_parts).strip(),
                line_number=line_number,
            )
            _resolve_file_ref(case_data, keyword)
            current.keywords.append(keyword)
            pending_comments = []
            last_comment_target = keyword
            continue

        loose = content.strip()
        if loose:
            item = {
                "text": loose,
                "line_number": line_number,
                "comment": "\n".join(pending_comments).strip(),
            }
            current.loose_items.append(item)
            pending_comments = []
            last_comment_target = item

    if in_schema:
        case_data.errors.append("RETURN_SCHEMA_JSON 没有结束标记")
    return case_data


def _split_inline_comment(line):
    if "//" not in line:
        return line.strip(), ""
    content, comment = line.split("//", 1)
    return content.strip(), comment.strip()


def _append_comment(target, comment):
    if not comment:
        return
    if isinstance(target, dict):
        existing = target.get("comment", "")
        target["comment"] = f"{existing}\n{comment}".strip() if existing else comment
        return
    existing = getattr(target, "comment", "")
    target.comment = f"{existing}\n{comment}".strip() if existing else comment


def _parse_value(raw_value):
    text = raw_value.strip()
    if not text:
        return "", "string"
    if "," in text:
        values = [_parse_scalar(part.strip())[0] for part in text.split(",") if part.strip()]
        return values, "list"
    return _parse_scalar(text)


def update_keyword_value(case_data, keyword, raw_value):
    new_raw_value = raw_value.strip()
    if keyword.raw_value == new_raw_value:
        return
    keyword.raw_value = new_raw_value
    keyword.value, keyword.value_type = _parse_value(keyword.raw_value)
    keyword.is_file_ref = False
    keyword.file_path = ""
    keyword.file_exists = False
    _resolve_file_ref(case_data, keyword)
    case_data.dirty = any(
        item.is_dirty()
        for section in case_data.sections
        for item in section.keywords
    )


def save_case_data(case_data, path=None, create_backup=True):
    """将 UI 中修改过的 key=value 行保存回 CaseData 输入文件。

    只重写已解析出的关键字行。注释、空行、section、非结构化文本和 schema 块
    都保留原始 raw_lines 中的内容。
    """
    if case_data is None:
        raise ValueError("CaseData 为空，无法保存")
    target_path = os.path.abspath(path or case_data.path or "")
    if not target_path:
        raise ValueError("CaseData 文件路径为空，无法保存")

    lines = list(case_data.raw_lines)
    if not lines:
        with open(target_path, "r", encoding="utf-8-sig") as file:
            lines = file.readlines()
    if not lines:
        raise ValueError("CaseData 原始内容为空，无法保存")

    for section in case_data.sections:
        for keyword in section.keywords:
            line_index = keyword.line_number - 1
            if 0 <= line_index < len(lines):
                lines[line_index] = _replace_keyword_line(
                    lines[line_index], keyword.key, keyword.raw_value)

    if create_backup and os.path.exists(target_path):
        backup_path = f"{target_path}.bak"
        shutil.copy2(target_path, backup_path)
        os.chmod(backup_path, stat.S_IREAD | stat.S_IWRITE)

    temp_path = f"{target_path}.tmp"
    with open(temp_path, "w", encoding="utf-8", newline="") as file:
        file.writelines(lines)
    if os.path.exists(target_path):
        os.chmod(target_path, stat.S_IREAD | stat.S_IWRITE)
    os.replace(temp_path, target_path)

    case_data.path = target_path
    case_data.base_dir = os.path.dirname(target_path)
    case_data.raw_lines = lines
    case_data.dirty = False
    for section in case_data.sections:
        for keyword in section.keywords:
            keyword.original_raw_value = keyword.raw_value
            _resolve_file_ref(case_data, keyword)
    return target_path


def export_case_data_snapshot(case_data, target_path):
    """把当前工程快照导出为临时 CaseData 文件，不修改原始文件。"""
    if case_data is None:
        raise ValueError("CaseData 为空，无法导出快照")
    target_path = os.path.abspath(target_path or "")
    if not target_path:
        raise ValueError("CaseData 快照导出路径为空")

    lines = _snapshot_template_lines(case_data)
    for section in case_data.sections:
        for keyword in section.keywords:
            line_index = keyword.line_number - 1
            raw_value = _snapshot_keyword_raw_value(keyword)
            if 0 <= line_index < len(lines):
                lines[line_index] = _replace_keyword_line(
                    lines[line_index], keyword.key, raw_value)

    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    with open(target_path, "w", encoding="utf-8", newline="") as file:
        file.writelines(lines)
    return target_path


def _snapshot_template_lines(case_data):
    """优先沿用原文件格式；原文件不可用时退化为最小 CaseData 文本。"""
    if case_data.raw_lines:
        return list(case_data.raw_lines)
    if case_data.path and os.path.exists(case_data.path):
        with open(case_data.path, "r", encoding="utf-8-sig") as file:
            return file.readlines()
    lines = []
    for section in case_data.sections:
        lines.append(f"[{section.name}]\n")
        for keyword in section.keywords:
            lines.append(f"{keyword.key} = {_snapshot_keyword_raw_value(keyword)}\n")
        lines.append("\n")
    return lines


def _snapshot_keyword_raw_value(keyword):
    """临时快照位于工程目录内，文件引用要写成可独立解析的绝对路径。"""
    if keyword.is_file_ref and keyword.file_path:
        return os.path.abspath(keyword.file_path)
    return keyword.raw_value


def _replace_keyword_line(raw_line, key, raw_value):
    newline = ""
    body = raw_line
    if body.endswith("\r\n"):
        body = body[:-2]
        newline = "\r\n"
    elif body.endswith("\n"):
        body = body[:-1]
        newline = "\n"

    content, marker, comment = body.partition("//")
    comment_text = f"{marker}{comment}" if marker else ""
    pattern = re.compile(rf"^(\s*{re.escape(key)}\s*=\s*)(.*?)(\s*)$")
    match = pattern.match(content)
    if not match:
        return f"{key} = {raw_value}{newline}"
    prefix, _, trailing = match.groups()
    return f"{prefix}{raw_value}{trailing}{comment_text}{newline}"


def _parse_scalar(text):
    lowered = text.lower()
    if lowered in {"true", "false"}:
        return lowered == "true", "bool"
    if RLE_RE.match(text):
        return text, "rle"
    try:
        if re.match(r"^[-+]?\d+$", text):
            return int(text), "int"
        return float(text), "float"
    except ValueError:
        return text.strip("\"'"), "string"


def _resolve_file_ref(case_data, keyword):
    value = keyword.value
    if not isinstance(value, str):
        return
    lowered_key = keyword.key.lower()
    lowered_value = value.lower()
    is_file = lowered_key.endswith("_file") or lowered_value.endswith(FILE_EXTENSIONS)
    if not is_file:
        return
    keyword.is_file_ref = True
    keyword.file_path = value if os.path.isabs(value) else os.path.join(case_data.base_dir, value)
    keyword.file_exists = os.path.exists(keyword.file_path)


def _load_schema(case_data, schema_lines):
    text = "".join(schema_lines).strip()
    if not text:
        return
    try:
        case_data.schema = json.loads(text)
    except json.JSONDecodeError as exc:
        case_data.errors.append(f"RETURN_SCHEMA_JSON 解析失败: {exc}")
