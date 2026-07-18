# -*- coding: utf-8 -*-
"""功能输入视图使用的只读数据访问辅助工具。"""

import json
import os

import numpy as np

from .case_dataset_schema import (
    ARRAYS_FILE,
    CONFIG_FILE,
    DFN_FILE,
    MANIFEST_FILE,
    VALIDATION_FILE,
)


class InputDataModel:
    """通过统一 API 提供项目、CaseData、数据集和数组输入。"""

    def __init__(self, project_state):
        self.project_state = project_state
        self._manifest = None
        self._config = None
        self._validation = None
        self._dfn = None
        self._arrays = None
        self._load_errors = {}

    def project_value(self, key, default=""):
        return getattr(self.project_state, key, default)

    def ui_value(self, module, key, default=""):
        values = self.project_state.get_module_values(module)
        return values.get(key, default)

    def case_keyword(self, section_name, key):
        section = self.case_section(section_name)
        if not section:
            return None
        for keyword in section.get("keywords", []) or []:
            if keyword.get("key") == key:
                return keyword
        return None

    def case_section(self, section_name):
        target = str(section_name or "").upper()
        for section in getattr(self.project_state, "case_data_sections", []) or []:
            if str(section.get("name", "")).upper() == target:
                return section
        return None

    def case_sections(self):
        return list(getattr(self.project_state, "case_data_sections", []) or [])

    def config_value(self, group, key, default=""):
        payload = self.config()
        section = payload.get(group, {}) if isinstance(payload, dict) else {}
        if isinstance(section, dict):
            return section.get(key, default)
        return default

    def manifest(self):
        if self._manifest is None:
            self._manifest = self._read_dataset_json(MANIFEST_FILE)
        return self._manifest or {}

    def config(self):
        if self._config is None:
            payload = self._read_dataset_json(CONFIG_FILE)
            self._config = payload.get("config", payload) if isinstance(payload, dict) else {}
        return self._config or {}

    def validation(self):
        if self._validation is None:
            self._validation = self._read_dataset_json(VALIDATION_FILE)
        return self._validation or {}

    def dfn(self):
        if self._dfn is None:
            payload = self._read_dataset_json(DFN_FILE)
            self._dfn = payload.get("dfn", payload) if isinstance(payload, dict) else {}
        return self._dfn or {}

    def arrays(self):
        if self._arrays is None:
            self._arrays = self._read_arrays()
        return self._arrays or {}

    def dataset_dir(self):
        return getattr(self.project_state, "case_dataset_path", "") or ""

    def dataset_exists(self):
        path = self.dataset_dir()
        return bool(path and os.path.isdir(path))

    def load_errors(self):
        return dict(self._load_errors)

    def item_value(self, item):
        source = item.get("source")
        if source == "project":
            return self.project_value(item.get("key", ""))
        if source == "ui":
            return self.ui_value(item.get("module", ""), item.get("key", ""))
        if source == "case":
            keyword = self.case_keyword(item.get("section", ""), item.get("key", ""))
            return keyword.get("raw_value", "") if keyword else ""
        if source == "config":
            return self.config_value(item.get("group", ""), item.get("key", ""))
        if source == "array":
            summary = self.array_summary(item.get("key", ""))
            return summary.get("status", "")
        if source == "dfn":
            return self.dfn_value(item.get("key", ""))
        if source == "validation":
            return self.validation_value(item.get("key", ""))
        if source == "case_section":
            section = self.case_section(item.get("key", ""))
            if not section:
                return "未加载"
            return f"{len(section.get('keywords', []) or [])} 个关键字"
        return ""

    def item_status(self, item):
        source = item.get("source")
        if source == "case":
            keyword = self.case_keyword(item.get("section", ""), item.get("key", ""))
            if not keyword:
                return "未提供"
            if keyword.get("is_file_ref"):
                return "文件存在" if keyword.get("file_exists") else "文件缺失"
            return "已提供"
        if source == "array":
            return self.array_summary(item.get("key", "")).get("status", "未生成")
        if source == "dfn":
            dfn = self.dfn()
            return "已生成" if dfn else "未生成"
        if source == "config":
            value = self.item_value(item)
            return "已提供" if value != "" else "未提供"
        if source == "validation":
            validation = self.validation()
            if not validation:
                return "未生成"
            return "通过" if validation.get("ok") else "有错误"
        value = self.item_value(item)
        return "已设置" if value not in ("", None) else "未设置"

    def file_records(self):
        records = []
        for section in self.case_sections():
            for keyword in section.get("keywords", []) or []:
                if not keyword.get("is_file_ref"):
                    continue
                records.append({
                    "section": section.get("name", ""),
                    "key": keyword.get("key", ""),
                    "value": keyword.get("raw_value", ""),
                    "path": keyword.get("file_path", ""),
                    "exists": bool(keyword.get("file_exists")),
                    "line": keyword.get("line_number", ""),
                })
        return records

    def array_summary(self, key):
        arrays = self.arrays()
        if key not in arrays:
            return {"key": key, "status": "未生成"}
        values = np.asarray(arrays[key])
        summary = {
            "key": key,
            "status": "已生成",
            "shape": " x ".join(str(part) for part in values.shape),
            "dtype": str(values.dtype),
            "count": int(values.size),
        }
        if values.size and np.issubdtype(values.dtype, np.number):
            flat = values.reshape(-1)
            finite = flat[np.isfinite(flat.astype(float, copy=False))]
            if finite.size:
                summary.update({
                    "min": float(np.min(finite)),
                    "max": float(np.max(finite)),
                    "mean": float(np.mean(finite)),
                })
        return summary

    def array_preview(self, key, limit=100):
        arrays = self.arrays()
        if key not in arrays:
            return []
        flat = np.asarray(arrays[key]).reshape(-1)
        return [flat[index].item() if hasattr(flat[index], "item") else flat[index]
                for index in range(min(limit, flat.size))]

    def dfn_value(self, key):
        dfn = self.dfn()
        value = dfn.get(key, "") if isinstance(dfn, dict) else ""
        if value == "":
            value = self.dfn_summary().get(key, "")
        if isinstance(value, list):
            return f"{len(value)} 项"
        return value

    def dfn_summary(self):
        dfn = self.dfn()
        if not isinstance(dfn, dict) or not dfn:
            return {}
        return {
            "fracture_count": dfn.get("fracture_count", 0),
            "node_count": dfn.get("node_count", 0),
            "property_count": dfn.get("property_count", 0),
            "set_count": len(dfn.get("sets", []) or []),
            "parsed_fractures": len(dfn.get("fractures", []) or []),
            "bbox_min": dfn.get("bbox_min", []),
            "bbox_max": dfn.get("bbox_max", []),
        }

    def dfn_fractures(self, limit=200):
        dfn = self.dfn()
        return list((dfn.get("fractures", []) or [])[:limit]) if isinstance(dfn, dict) else []

    def validation_value(self, key):
        validation = self.validation()
        if not validation:
            return ""
        if key in {"errors", "warnings"}:
            return f"{len(validation.get(key, []) or [])} 项"
        return validation.get(key, "")

    def validation_items(self):
        validation = self.validation()
        items = []
        for kind in ("errors", "warnings"):
            for message in validation.get(kind, []) or []:
                items.append({"level": kind[:-1], "message": str(message)})
        checks = validation.get("checks", {}) or {}
        for name, payload in checks.items():
            items.append({
                "level": "check",
                "message": f"{name}: {'OK' if payload.get('ok') else 'FAILED'} {payload.get('detail', '')}",
            })
        return items

    def _read_dataset_json(self, filename):
        path = self._dataset_file(filename)
        if not path:
            return {}
        try:
            with open(path, "r", encoding="utf-8") as file:
                return json.load(file)
        except (OSError, ValueError) as exc:
            self._load_errors[filename] = str(exc)
            return {}

    def _read_arrays(self):
        path = self._dataset_file(ARRAYS_FILE)
        if not path:
            return {}
        try:
            with np.load(path, allow_pickle=False) as npz_file:
                return {name: np.asarray(npz_file[name]) for name in npz_file.files}
        except (OSError, ValueError) as exc:
            self._load_errors[ARRAYS_FILE] = str(exc)
            return {}

    def _dataset_file(self, fallback_name):
        dataset_dir = self.dataset_dir()
        if not dataset_dir or not os.path.isdir(dataset_dir):
            return ""
        manifest = self._manifest if self._manifest is not None else None
        field_map = {
            CONFIG_FILE: "config_file",
            DFN_FILE: "dfn_file",
            VALIDATION_FILE: "validation_file",
            ARRAYS_FILE: "arrays_file",
        }
        filename = fallback_name
        if fallback_name != MANIFEST_FILE:
            if manifest is None:
                manifest_path = os.path.join(dataset_dir, MANIFEST_FILE)
                try:
                    with open(manifest_path, "r", encoding="utf-8") as file:
                        manifest = json.load(file)
                    self._manifest = manifest
                except (OSError, ValueError):
                    manifest = {}
            filename = manifest.get(field_map.get(fallback_name, ""), fallback_name)
        path = filename if os.path.isabs(filename) else os.path.join(dataset_dir, filename)
        return path if os.path.exists(path) else ""
