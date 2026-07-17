# -*- coding: utf-8 -*-
"""Workbench project state with an active-case compatibility facade."""

import copy
import os

from .case_config_sync import (
    sync_project_modules_from_case_data,
    sync_project_modules_from_dataset,
)
from .case_models import (
    CASE_TYPE_GAS_WATER,
    DATASET_STATUS_INVALID,
    DATASET_STATUS_READY,
    GRID_TYPE_CORNER_POINT,
    MODEL_TYPE_NORMAL,
    MODEL_TYPE_WR,
    WR_INPUT_MODE_CONSTANT,
    WR_INPUT_MODE_FILE,
    WR_INPUT_MODE_MIXED,
    CaseState,
    DatasetRecord,
    InputState,
    RunRecord,
    default_model_config,
    new_case_id,
    new_project_id,
    normalize_model_config,
    utc_now,
)
from .module_input_models import (
    ModuleImportResult,
    ModuleInputState,
    ModuleParsedData,
)


# Backward-compatible public names used by older integrations.
CaseInfo = CaseState
_utc_now = utc_now
_new_case_id = new_case_id


class ProjectState:
    """Persistent project state.

    Case-owned values are exposed through the historical project-level
    attributes so existing panels do not need a flag-day migration.  Reading
    ``project_state.module_values`` therefore means "the active case's module
    values".
    """

    LEGACY_INPUT_FIELDS = (
        "model_config",
        "case_data_path",
        "case_data_summary",
        "case_data_sections",
        "case_data_schema",
        "checked_items",
        "module_values",
        "module_inputs",
        "input_assets",
        "input_revision",
        "input_fingerprint",
    )

    def __init__(
            self,
            project_id="",
            project_name="",
            project_file_path="",
            algorithm="corner_edfm",
            corner_grid_refinement="加密",
            model_config=None,
            case_data_path="",
            case_data_summary=None,
            case_data_sections=None,
            case_data_schema=None,
            case_dataset_path="",
            case_dataset_summary=None,
            checked_items=None,
            module_values=None,
            module_inputs=None,
            input_assets=None,
            ui_state=None,
            cases=None,
            active_case_id=""):
        self.project_id = project_id or new_project_id()
        self.project_name = project_name or ""
        self.project_file_path = project_file_path or ""
        self.algorithm = algorithm or "corner_edfm"
        self.ui_state = dict(ui_state or {})
        self._artifact_repository = None

        self._unbound_input = InputState(
            model_config=normalize_model_config(
                model_config, corner_grid_refinement),
            case_data_path=case_data_path or "",
            case_data_summary=copy.deepcopy(case_data_summary or {}),
            case_data_sections=copy.deepcopy(case_data_sections or []),
            case_data_schema=copy.deepcopy(case_data_schema or {}),
            checked_items=copy.deepcopy(checked_items or {}),
            module_values=copy.deepcopy(module_values or {}),
            module_inputs=copy.deepcopy(module_inputs or {}),
            input_assets=copy.deepcopy(input_assets or {}),
        )
        self._unbound_dataset_path = case_dataset_path or ""
        self._unbound_dataset_summary = copy.deepcopy(
            case_dataset_summary or {})

        self.cases = self._normalize_cases(cases or [])
        self.active_case_id = active_case_id or ""
        if self.active_case_id and not self.case_by_id(self.active_case_id):
            self.active_case_id = ""
        if not self.active_case_id and self.cases:
            self.active_case_id = self.cases[0].case_id

        legacy_values_supplied = any([
            model_config is not None,
            bool(case_data_path),
            bool(case_data_summary),
            bool(case_data_sections),
            bool(case_data_schema),
            bool(case_dataset_path),
            bool(case_dataset_summary),
            bool(checked_items),
            bool(module_values),
            bool(module_inputs),
            bool(input_assets),
        ])
        active_case = self.active_case()
        if active_case is not None and legacy_values_supplied:
            active_case.input_state = copy.deepcopy(self._unbound_input)
            if case_dataset_path or case_dataset_summary:
                active_case.add_dataset(DatasetRecord(
                    path=case_dataset_path or "",
                    summary=copy.deepcopy(case_dataset_summary or {}),
                    input_revision=active_case.input_state.input_revision,
                ))

    # ------------------------------------------------------------------
    # Active-case compatibility properties
    # ------------------------------------------------------------------
    def _active_input(self):
        case = self.active_case()
        return case.input_state if case is not None else self._unbound_input

    @property
    def artifact_repository(self):
        return self._artifact_repository

    def attach_artifact_repository(self, repository):
        self._artifact_repository = repository
        if repository is not None:
            for case in self.cases:
                refreshed = {}
                for module_key, module_state in case.input_state.module_inputs.items():
                    state = copy.deepcopy(module_state)
                    self._capture_module_source_assets(
                        case.input_state, state, repository)
                    refreshed[module_key] = state
                if refreshed:
                    case.input_state.module_inputs = refreshed
        return repository

    @staticmethod
    def _capture_module_source_assets(input_state, module_state, repository):
        """Make path-backed module inputs portable without changing revision."""

        source = dict(module_state.source or {})
        keyword_records = copy.deepcopy(source.get("keywords") or {})
        assets = dict(input_state.input_assets or {})
        for qualified_name, record in keyword_records.items():
            if not isinstance(record, dict):
                continue
            source_path = str(record.get("resolved_path") or "").strip()
            if not source_path or not os.path.isfile(source_path):
                continue
            try:
                asset = repository.capture_asset(
                    source_path, source_key=qualified_name)
            except (OSError, ValueError):
                continue
            managed_path = str(asset.get("managed_path") or "")
            if not managed_path or not os.path.isfile(managed_path):
                continue
            assets[f"module:{qualified_name}"] = asset
            record["resolved_path"] = os.path.abspath(managed_path)
            record["exists"] = True
        source["keywords"] = keyword_records
        module_state.source = source
        input_state.input_assets = assets
        return module_state

    @property
    def corner_grid_refinement(self):
        return "加密" if self.model_config.get("enable_lgr") else "不加密"

    @corner_grid_refinement.setter
    def corner_grid_refinement(self, value):
        config = dict(self.model_config or {})
        config["enable_lgr"] = str(value).strip() not in {
            "", "0", "false", "False", "不加密",
        }
        self._active_input().model_config = normalize_model_config(config)

    @property
    def model_config(self):
        return self._active_input().model_config

    @model_config.setter
    def model_config(self, value):
        self._active_input().model_config = normalize_model_config(value)

    @property
    def case_data_path(self):
        return self._active_input().case_data_path

    @case_data_path.setter
    def case_data_path(self, value):
        self._active_input().case_data_path = value or ""

    @property
    def case_data_summary(self):
        return self._active_input().case_data_summary

    @case_data_summary.setter
    def case_data_summary(self, value):
        self._active_input().case_data_summary = dict(value or {})

    @property
    def case_data_sections(self):
        return self._active_input().case_data_sections

    @case_data_sections.setter
    def case_data_sections(self, value):
        self._active_input().case_data_sections = list(value or [])

    @property
    def case_data_schema(self):
        return self._active_input().case_data_schema

    @case_data_schema.setter
    def case_data_schema(self, value):
        self._active_input().case_data_schema = dict(value or {})

    @property
    def checked_items(self):
        return self._active_input().checked_items

    @checked_items.setter
    def checked_items(self, value):
        self._active_input().checked_items = dict(value or {})

    @property
    def module_values(self):
        return self._active_input().module_values

    @module_values.setter
    def module_values(self, value):
        self._active_input().module_values = dict(value or {})

    @property
    def module_inputs(self):
        return self._active_input().module_inputs

    @module_inputs.setter
    def module_inputs(self, value):
        self._active_input().module_inputs = {
            str(module_key): ModuleInputState.from_dict(state, module_key)
            for module_key, state in dict(value or {}).items()
        }

    @property
    def input_assets(self):
        return self._active_input().input_assets

    @input_assets.setter
    def input_assets(self, value):
        self._active_input().input_assets = dict(value or {})

    @property
    def case_dataset_path(self):
        case = self.active_case()
        if case is None:
            return self._unbound_dataset_path
        record = case.active_dataset()
        return record.path if record is not None else ""

    @case_dataset_path.setter
    def case_dataset_path(self, value):
        value = value or ""
        case = self.active_case()
        if case is None:
            self._unbound_dataset_path = value
            return
        record = case.active_dataset()
        if not value:
            case.active_dataset_id = ""
            return
        if record is None:
            record = DatasetRecord(path=value)
            case.add_dataset(record, activate=True)
        else:
            record.path = value

    @property
    def case_dataset_summary(self):
        case = self.active_case()
        if case is None:
            return self._unbound_dataset_summary
        record = case.active_dataset()
        return record.summary if record is not None else {}

    @case_dataset_summary.setter
    def case_dataset_summary(self, value):
        summary = dict(value or {})
        case = self.active_case()
        if case is None:
            self._unbound_dataset_summary = summary
            return
        record = case.active_dataset()
        if record is None:
            if not summary:
                return
            record = DatasetRecord(summary=summary)
            case.add_dataset(record, activate=True)
        else:
            record.summary = summary

    # ------------------------------------------------------------------
    # Case lifecycle
    # ------------------------------------------------------------------
    def _normalize_cases(self, cases):
        normalized = []
        seen = set()
        for item in cases or []:
            case = item if isinstance(item, CaseState) else CaseState.from_dict(item)
            if case.case_id in seen:
                case.case_id = new_case_id()
                for run in case.run_records:
                    run.case_id = case.case_id
            seen.add(case.case_id)
            normalized.append(case)
        return normalized

    def case_by_id(self, case_id):
        for case in self.cases:
            if case.case_id == case_id:
                return case
        return None

    def active_case(self):
        return self.case_by_id(self.active_case_id)

    def has_active_case(self):
        return self.active_case() is not None

    def active_dataset_record(self):
        case = self.active_case()
        return case.active_dataset() if case is not None else None

    def is_case_dataset_ready(self):
        """Return whether the active case can safely start a simulation."""

        record = self.active_dataset_record()
        if record is None or record.status != DATASET_STATUS_READY:
            return False
        if record.summary.get("stale"):
            return False
        active_input = self._active_input()
        if int(record.input_revision or 0) != int(active_input.input_revision or 0):
            return False
        if not record.path or not os.path.isdir(record.path):
            return False
        return os.path.isfile(os.path.join(record.path, "manifest.json"))

    def case_dataset_readiness_reason(self):
        """Return a source-free business explanation for the run button."""

        record = self.active_dataset_record()
        if record is None:
            return "当前算例尚未生成 Dataset"
        if record.status == DATASET_STATUS_INVALID:
            return "当前 Dataset 校验未通过"
        if record.status != DATASET_STATUS_READY or record.summary.get("stale"):
            return record.summary.get("stale_reason") or "当前 Dataset 已过期"
        if int(record.input_revision or 0) != int(
                self._active_input().input_revision or 0):
            return "模块数据已修改，请重新生成 Dataset"
        if not record.path or not os.path.isfile(
                os.path.join(record.path, "manifest.json")):
            return "当前 Dataset 内容不完整"
        return "Dataset 已就绪"

    def active_run_record(self):
        case = self.active_case()
        return case.active_run() if case is not None else None

    def add_run_record(self, record, activate=True):
        case = self.active_case()
        if case is None:
            raise ValueError("请先创建或选择算例后再登记运行")
        return case.add_run(record, activate=activate)

    def add_case_run_record(self, case_id, record, activate=True):
        case = self.case_by_id(case_id)
        if case is None:
            raise ValueError(f"Unknown case_id: {case_id}")
        return case.add_run(record, activate=activate)

    def run_record(self, case_id, run_id):
        case = self.case_by_id(case_id)
        return case.run_by_id(run_id) if case is not None else None

    def interrupt_unfinished_runs(self, message="Application closed before the run finished"):
        interrupted = []
        for case in self.cases:
            interrupted.extend(case.interrupt_unfinished_runs(message))
        return interrupted

    def select_run(self, run_id):
        case = self.active_case()
        if case is None or case.run_by_id(run_id) is None:
            return False
        case.active_run_id = run_id
        return True

    def add_case(self, case_name="NewCase", case_type=CASE_TYPE_GAS_WATER,
                 description="", activate=True, input_state=None):
        existing_names = {case.case_name for case in self.cases}
        name = case_name or "NewCase"
        if name in existing_names:
            base = name
            index = 1
            while f"{base}{index}" in existing_names:
                index += 1
            name = f"{base}{index}"
        case = CaseState(
            case_name=name,
            case_type=case_type,
            description=description,
            input_state=copy.deepcopy(input_state) if input_state else InputState(),
        )
        self.cases.append(case)
        if activate:
            self.active_case_id = case.case_id
        return case

    def suggest_duplicate_case_name(self, source_name):
        """Return a readable, unused name for a copied case."""
        existing_names = {case.case_name for case in self.cases}
        base = f"{source_name or 'NewCase'}_副本"
        if base not in existing_names:
            return base
        index = 2
        while f"{base}{index}" in existing_names:
            index += 1
        return f"{base}{index}"

    def select_case(self, case_id):
        if not self.case_by_id(case_id):
            return False
        self.active_case_id = case_id
        return True

    def rename_case(self, case_id, case_name):
        case = self.case_by_id(case_id)
        if not case or not case_name:
            return False
        case.case_name = case_name
        case.touch()
        return True

    def delete_case(self, case_id, allow_unfinished=False):
        case = self.case_by_id(case_id)
        if (
            case is not None
            and case.has_unfinished_runs()
            and not allow_unfinished
        ):
            return False
        before = len(self.cases)
        self.cases = [case for case in self.cases if case.case_id != case_id]
        if len(self.cases) == before:
            return False
        if self.active_case_id == case_id:
            self.active_case_id = self.cases[0].case_id if self.cases else ""
        return True

    def duplicate_case(self, case_id, case_name=""):
        source = self.case_by_id(case_id)
        if not source:
            return None

        # A copy owns an independent editable configuration. Dataset and Run
        # records (including simulation/history-matching artifacts) remain
        # owned by the source case and are deliberately not cloned.
        cloned_input = copy.deepcopy(source.input_state)
        cloned_input.input_revision = 0
        cloned_input.input_fingerprint = ""
        duplicated = self.add_case(
            case_name=case_name or self.suggest_duplicate_case_name(
                source.case_name),
            case_type=source.case_type,
            description=source.description,
            activate=True,
            input_state=cloned_input,
        )
        duplicated.derivation = {
            "kind": "case_copy",
            "source_case_id": source.case_id,
        }
        return duplicated

    def ensure_legacy_case(self):
        if self.cases:
            return self.active_case()
        has_legacy_input = any([
            self._unbound_input.case_data_path,
            self._unbound_dataset_path,
            self._unbound_input.case_data_sections,
            self._unbound_input.module_values,
            self._unbound_input.module_inputs,
        ])
        if not has_legacy_input:
            return None
        case = self.add_case(
            case_name=self.project_name or "DefaultCase",
            input_state=self._unbound_input,
        )
        if self._unbound_dataset_path or self._unbound_dataset_summary:
            record = DatasetRecord(
                path=self._unbound_dataset_path,
                summary=copy.deepcopy(self._unbound_dataset_summary),
                input_revision=case.input_state.input_revision,
            )
            case.add_dataset(record, activate=True)
        return case

    # ------------------------------------------------------------------
    # Existing input APIs, now scoped to the active case
    # ------------------------------------------------------------------
    def _touch_active_input(self):
        state = self._active_input()
        state.touch()
        case = self.active_case()
        if case is not None:
            case.touch()

    def set_model_config(self, config):
        current = normalize_model_config(self.model_config)
        normalized = normalize_model_config(config, self.corner_grid_refinement)
        self.model_config = normalized
        if current != normalized:
            self._touch_active_input()
            self.mark_case_dataset_stale(
                "模型配置已修改，请重新生成 Dataset")

    def update_model_config(self, **updates):
        config = dict(self.model_config or {})
        config.update(updates)
        self.set_model_config(config)

    def is_wr_model(self):
        return self.model_config.get("model_type") == MODEL_TYPE_WR

    def set_checked(self, key, checked):
        if key:
            self.checked_items[key] = bool(checked)

    def is_checked(self, key, default=False):
        return self.checked_items.get(key, default)

    def set_module_values(self, key, values):
        if not key:
            return
        normalized = dict(values or {})
        if self.module_values.get(key) == normalized:
            return
        self.module_values[key] = normalized
        self._touch_active_input()

    def get_module_values(self, key):
        return dict(self.module_values.get(key, {}))

    def get_module_input_state(self, module_key):
        """Return an isolated copy of one module's committed state."""

        state = self.module_inputs.get(str(module_key or ""))
        return copy.deepcopy(state) if state is not None else None

    def replace_module_input_state(self, module_key, candidate):
        """Atomically commit one validated module revision."""

        module_key = str(module_key or "")
        if not module_key:
            raise ValueError("模块标识不能为空")
        state = ModuleInputState.from_dict(candidate, module_key)
        if state.module_key != module_key:
            raise ValueError("模块状态归属不一致")
        validation = state.validation or {}
        if not validation.get("ok", False):
            raise ValueError("不能提交未通过校验的模块状态")

        previous = self.module_inputs.get(module_key)
        case = self.active_case()
        repository = self.artifact_repository
        if repository is not None and case is not None:
            self._capture_module_source_assets(
                case.input_state, state, repository)
        state.revision = (previous.revision if previous is not None else 0) + 1
        state.dirty = False
        updated = dict(self.module_inputs)
        updated[module_key] = state
        self.module_inputs = updated
        self._touch_active_input()
        self.mark_case_dataset_stale(
            "模块输入已更新，请重新生成 Dataset")
        return copy.deepcopy(state)

    def set_case_data(self, case_data):
        case = self.active_case()
        if case_data is None:
            self.case_data_path = ""
            self.case_data_summary = {}
            self.case_data_sections = []
            self.case_data_schema = {}
            if case is not None:
                case.dataset_records = []
                case.active_dataset_id = ""
                case.touch()
            else:
                self._unbound_dataset_path = ""
                self._unbound_dataset_summary = {}
            self._touch_active_input()
            return

        previous_path = self.case_data_path
        previous_sections = copy.deepcopy(self.case_data_sections)
        previous_schema = copy.deepcopy(self.case_data_schema)
        file_refs = case_data.file_refs()
        missing_refs = [item for item in file_refs if not item.file_exists]
        self.case_data_path = case_data.path
        self.case_data_sections = [section.to_dict() for section in case_data.sections]
        self.case_data_schema = dict(case_data.schema or {})
        self.case_data_summary = {
            "section_count": len(case_data.sections),
            "keyword_count": case_data.keyword_count(),
            "file_ref_count": len(file_refs),
            "missing_file_ref_count": len(missing_refs),
            "error_count": len(case_data.errors),
        }
        repository = self.artifact_repository
        if repository is not None and case is not None:
            try:
                repository.capture_case_data(case, case_data)
            except (OSError, ValueError) as exc:
                self.case_data_summary["asset_capture_error"] = str(exc)
        sync_project_modules_from_case_data(self)

        path_changed = (
            previous_path
            and os.path.abspath(previous_path) != os.path.abspath(self.case_data_path)
        )
        input_changed = bool(
            path_changed
            or previous_sections != self.case_data_sections
            or previous_schema != self.case_data_schema
        )
        if input_changed:
            self._touch_active_input()
        if input_changed and self.case_dataset_path:
            reason = (
                "CaseData 来源已修改，请重新生成 Dataset"
                if path_changed else "CaseData 已修改，请重新生成 Dataset"
            )
            self.mark_case_dataset_stale(reason)

    def set_case_dataset(self, dataset_path, manifest=None, validation=None,
                         dataset_id=""):
        """Register a newly built Dataset on the active case."""
        dataset_path = os.path.abspath(dataset_path or "") if dataset_path else ""
        manifest = manifest or {}
        validation = validation or manifest.get("validation", {}) or {}
        summary = {
            "schema_version": manifest.get("schema_version", ""),
            "source_case_file": manifest.get("source_case_file", ""),
            "array_count": len(manifest.get("arrays", {}) or {}),
            "source_file_count": len(manifest.get("source_files", []) or []),
            "error_count": validation.get(
                "error_count", len(validation.get("errors", []) or [])),
            "warning_count": validation.get(
                "warning_count", len(validation.get("warnings", []) or [])),
            "manifest_path": os.path.join(dataset_path, "manifest.json")
            if dataset_path else "",
        }
        has_errors = bool(validation.get("errors")) or bool(summary["error_count"])
        record = DatasetRecord(
            dataset_id=dataset_id or "",
            path=dataset_path,
            input_revision=self._active_input().input_revision,
            input_fingerprint=self._active_input().input_fingerprint,
            schema_version=manifest.get("schema_version", "") or "",
            validation=copy.deepcopy(validation),
            summary=summary,
            status=DATASET_STATUS_INVALID if has_errors else DATASET_STATUS_READY,
        )
        case = self.active_case()
        if case is None:
            self._unbound_dataset_path = dataset_path
            self._unbound_dataset_summary = summary
        else:
            case.add_dataset(record, activate=True)

        sync_project_modules_from_dataset(self, dataset_path)
        # Dataset-derived module synchronization is part of this build, so the
        # record must point at the resulting active input revision.
        record.input_revision = self._active_input().input_revision
        record.input_fingerprint = self._active_input().input_fingerprint
        return record

    def mark_case_dataset_stale(
            self, reason="CaseData 已修改，请重新生成 Dataset"):
        """Mark only the active case's Dataset as stale."""
        case = self.active_case()
        if case is None:
            if self._unbound_dataset_path:
                self._unbound_dataset_summary["stale"] = True
                self._unbound_dataset_summary["stale_reason"] = reason
            return
        record = case.active_dataset()
        if record is None:
            return
        record.mark_stale(reason)
        case.touch()

    # ------------------------------------------------------------------
    # Serialization and legacy migration
    # ------------------------------------------------------------------
    def _active_legacy_payload(self):
        return {
            "corner_grid_refinement": self.corner_grid_refinement,
            "model_config": copy.deepcopy(self.model_config),
            "case_data_path": self.case_data_path,
            "case_data_summary": copy.deepcopy(self.case_data_summary),
            "case_data_sections": copy.deepcopy(self.case_data_sections),
            "case_data_schema": copy.deepcopy(self.case_data_schema),
            "case_dataset_path": self.case_dataset_path,
            "case_dataset_summary": copy.deepcopy(self.case_dataset_summary),
            "checked_items": copy.deepcopy(self.checked_items),
            "module_values": copy.deepcopy(self.module_values),
            "module_inputs": {
                module_key: state.to_dict()
                for module_key, state in self.module_inputs.items()
            },
            "input_assets": copy.deepcopy(self.input_assets),
            "input_revision": self._active_input().input_revision,
            "input_fingerprint": self._active_input().input_fingerprint,
        }

    def to_dict(self):
        """Export state while retaining active-case legacy aliases."""
        payload = {
            "project_id": self.project_id,
            "project_name": self.project_name,
            "project_file_path": self.project_file_path,
            "algorithm": self.algorithm,
            "ui_state": copy.deepcopy(self.ui_state),
            "cases": [case.to_dict() for case in self.cases],
            "active_case_id": self.active_case_id,
        }
        payload.update(self._active_legacy_payload())
        return payload

    @classmethod
    def from_dict(cls, payload):
        """Load rich case state or migrate the historical global state."""
        payload = payload or {}
        cases_payload = copy.deepcopy(payload.get("cases") or [])
        state = cls(
            project_id=payload.get("project_id", "") or "",
            project_name=payload.get("project_name", ""),
            project_file_path=payload.get("project_file_path", ""),
            algorithm=payload.get("algorithm", "corner_edfm"),
            ui_state=copy.deepcopy(payload.get("ui_state") or {}),
            cases=cases_payload,
            active_case_id=payload.get("active_case_id", "") or "",
        )

        legacy_input = InputState.from_dict(
            payload,
            legacy_refinement=payload.get("corner_grid_refinement"),
        )
        has_legacy_input = any([
            legacy_input.case_data_path,
            legacy_input.case_data_sections,
            legacy_input.module_values,
            legacy_input.module_inputs,
            payload.get("case_dataset_path"),
        ])
        cases_have_input_state = any(
            isinstance(item, dict) and "input_state" in item
            for item in cases_payload
        )

        if not state.cases and has_legacy_input:
            case = state.add_case(
                case_name=state.project_name or "DefaultCase",
                input_state=legacy_input,
            )
        elif state.cases:
            case = state.active_case()
            if case is None:
                state.active_case_id = state.cases[0].case_id
                case = state.active_case()
            # Old files stored metadata-only cases.  New files still carry the
            # top-level aliases so package path relocation can override the
            # active case's embedded absolute paths.
            if not cases_have_input_state or any(
                    field_name in payload for field_name in cls.LEGACY_INPUT_FIELDS):
                case.input_state = legacy_input
        else:
            state._unbound_input = legacy_input
            case = None

        dataset_path = payload.get("case_dataset_path", "") or ""
        dataset_summary = copy.deepcopy(
            payload.get("case_dataset_summary") or {})
        if case is not None and (dataset_path or dataset_summary):
            record = case.active_dataset()
            if record is None:
                record = DatasetRecord(
                    path=dataset_path,
                    summary=dataset_summary,
                    schema_version=dataset_summary.get("schema_version", ""),
                    input_revision=case.input_state.input_revision,
                )
                case.add_dataset(record, activate=True)
            else:
                if dataset_path:
                    record.path = dataset_path
                if dataset_summary:
                    record.summary = dataset_summary
        elif case is None:
            state._unbound_dataset_path = dataset_path
            state._unbound_dataset_summary = dataset_summary

        state.ensure_legacy_case()
        state.interrupt_unfinished_runs()
        if state.case_data_sections:
            sync_project_modules_from_case_data(state)
        if state.case_dataset_path:
            sync_project_modules_from_dataset(state, state.case_dataset_path)
        return state


__all__ = [
    "CASE_TYPE_GAS_WATER",
    "GRID_TYPE_CORNER_POINT",
    "MODEL_TYPE_NORMAL",
    "MODEL_TYPE_WR",
    "WR_INPUT_MODE_CONSTANT",
    "WR_INPUT_MODE_FILE",
    "WR_INPUT_MODE_MIXED",
    "CaseInfo",
    "CaseState",
    "DatasetRecord",
    "InputState",
    "ModuleImportResult",
    "ModuleInputState",
    "ModuleParsedData",
    "ProjectState",
    "RunRecord",
    "default_model_config",
    "normalize_model_config",
]
