"""生产动态曲线样式模板的持久化管理。"""

import json
import math
import os
from copy import deepcopy
from datetime import datetime
from pathlib import Path

from PyQt5.QtCore import QStandardPaths


DEFAULT_TEMPLATE_NAME = "默认样式"
TEMPLATE_FILE_NAME = "production_curve_style_templates.json"
TEMPLATE_VERSION = 1


class ProductionCurveStyleTemplateManager:
    """
    管理生产曲线样式模板。
    模板默认保存在当前 Windows 用户的配置目录中
    """

    def __init__(
        self,
        storage_path=None,
        app_folder_name="OilProject",
    ):
        if storage_path:
            self.storage_path = Path(storage_path)
        else:
            self.storage_path = self._default_storage_path(
                app_folder_name=app_folder_name,
            )

        self._templates = {}
        self._load()

    @staticmethod
    def _default_storage_path(app_folder_name):
        base_dir = QStandardPaths.writableLocation(
            QStandardPaths.AppConfigLocation
        )

        if not base_dir:
            base_dir = os.path.join(
                str(Path.home()),
                ".config",
            )

        return (
            Path(base_dir)
            / str(app_folder_name)
            / TEMPLATE_FILE_NAME
        )

    @staticmethod
    def _normalize_template_name(name):
        name = str(name or "").strip()

        if not name:
            raise ValueError("模板名称不能为空。")

        if name == DEFAULT_TEMPLATE_NAME:
            raise ValueError(
                f"“{DEFAULT_TEMPLATE_NAME}”是系统保留名称，"
                "不能用于用户模板。"
            )

        if len(name) > 80:
            raise ValueError("模板名称不能超过 80 个字符。")

        return name

    @staticmethod
    def _normalize_color(color):
        if not isinstance(color, (tuple, list)):
            return None

        if len(color) < 3:
            return None

        try:
            values = [
                int(color[0]),
                int(color[1]),
                int(color[2]),
            ]
        except Exception:
            return None

        if any(value < 0 or value > 255 for value in values):
            return None

        return values

    @staticmethod
    def _normalize_line_style(line_style):
        aliases = {
            "solid": "solid",
            "实线": "solid",
            "dash": "dash",
            "dashed": "dash",
            "虚线": "dash",
            "dot": "dot",
            "dotted": "dot",
            "点线": "dot",
            "dashdot": "dashdot",
            "dash-dot": "dashdot",
            "点划线": "dashdot",
            "dashdotdot": "dashdotdot",
            "dash-dot-dot": "dashdotdot",
            "双点划线": "dashdotdot",
        }

        return aliases.get(
            str(line_style or "").strip().lower()
        )

    @classmethod
    def _normalize_template_data(cls, template_data):
        if not isinstance(template_data, dict):
            raise ValueError("模板数据必须是字典。")

        curves = template_data.get(
            "curves",
            template_data,
        )

        if not isinstance(curves, dict):
            raise ValueError("模板中没有有效的 curves 数据。")

        normalized_curves = {}

        for raw_key, style_info in curves.items():
            key = str(raw_key or "").strip()

            if not key or key == "date":
                continue

            if not isinstance(style_info, dict):
                continue

            color = cls._normalize_color(
                style_info.get("color")
            )

            try:
                width = float(
                    style_info.get("width", 1.2)
                )
            except Exception:
                width = None

            line_style = cls._normalize_line_style(
                style_info.get(
                    "line_style",
                    "solid",
                )
            )

            if (
                color is None
                or width is None
                or not math.isfinite(width)
                or width <= 0.0
                or line_style is None
            ):
                continue

            normalized_curves[key] = {
                "color": color,
                "width": width,
                "line_style": line_style,
            }

        if not normalized_curves:
            raise ValueError("模板中没有可保存的曲线样式。")

        return {
            "version": TEMPLATE_VERSION,
            "curves": normalized_curves,
        }

    def _load(self):
        self._templates = {}

        if not self.storage_path.exists():
            return

        try:
            payload = json.loads(
                self.storage_path.read_text(
                    encoding="utf-8"
                )
            )
        except Exception as exc:
            print(
                "ProductionCurveStyleTemplateManager "
                f"load failed: {exc}"
            )
            return

        raw_templates = payload.get(
            "templates",
            {},
        )

        if not isinstance(raw_templates, dict):
            return

        for raw_name, raw_record in raw_templates.items():
            name = str(raw_name or "").strip()

            if (
                not name
                or name == DEFAULT_TEMPLATE_NAME
                or not isinstance(raw_record, dict)
            ):
                continue

            try:
                normalized = self._normalize_template_data(
                    raw_record
                )
            except Exception:
                continue

            self._templates[name] = {
                "version": TEMPLATE_VERSION,
                "created_at": str(
                    raw_record.get(
                        "created_at",
                        "",
                    )
                ),
                "updated_at": str(
                    raw_record.get(
                        "updated_at",
                        "",
                    )
                ),
                "curves": normalized["curves"],
            }

    def reload(self):
        self._load()

    def _save(self):
        self.storage_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        payload = {
            "version": TEMPLATE_VERSION,
            "templates": self._templates,
        }

        temporary_path = self.storage_path.with_suffix(
            self.storage_path.suffix + ".tmp"
        )

        temporary_path.write_text(
            json.dumps(
                payload,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        os.replace(
            str(temporary_path),
            str(self.storage_path),
        )

    def get_storage_path(self):
        return str(self.storage_path)

    def get_template_names(self):
        return sorted(
            self._templates.keys(),
            key=lambda value: value.lower(),
        )

    def has_template(self, name):
        name = str(name or "").strip()
        return name in self._templates

    def get_template(self, name):
        name = str(name or "").strip()
        record = self._templates.get(name)

        if record is None:
            return None

        return deepcopy(record)

    def save_template(
        self,
        name,
        template_data,
        overwrite=False,
    ):
        name = self._normalize_template_name(name)
        normalized = self._normalize_template_data(
            template_data
        )

        if self.has_template(name) and not overwrite:
            raise FileExistsError(
                f"模板“{name}”已经存在。"
            )

        now_text = datetime.now().isoformat(
            timespec="seconds"
        )

        old_record = self._templates.get(
            name,
            {},
        )

        created_at = old_record.get(
            "created_at",
            now_text,
        )

        self._templates[name] = {
            "version": TEMPLATE_VERSION,
            "created_at": created_at,
            "updated_at": now_text,
            "curves": normalized["curves"],
        }

        self._save()
        return self.get_template(name)

    def delete_template(self, name):
        name = str(name or "").strip()

        if name not in self._templates:
            return False

        del self._templates[name]
        self._save()
        return True

    def rename_template(
        self,
        old_name,
        new_name,
        overwrite=False,
    ):
        old_name = str(old_name or "").strip()
        new_name = self._normalize_template_name(
            new_name
        )

        if old_name not in self._templates:
            raise KeyError(
                f"找不到模板“{old_name}”。"
            )

        if (
            new_name in self._templates
            and new_name != old_name
            and not overwrite
        ):
            raise FileExistsError(
                f"模板“{new_name}”已经存在。"
            )

        record = self._templates.pop(old_name)
        record["updated_at"] = datetime.now().isoformat(
            timespec="seconds"
        )

        self._templates[new_name] = record
        self._save()
        return self.get_template(new_name)
