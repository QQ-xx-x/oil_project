# -*- coding: utf-8 -*-
"""Persistent case-level models used by the reservoir workbench.

The UI historically stored all inputs directly on ``ProjectState``.  These
models provide the real ownership boundary for multi-case projects while
``ProjectState`` keeps a compatibility facade for existing panels.
"""

import copy
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


MODEL_TYPE_NORMAL = "normal"
MODEL_TYPE_WR = "wr"
GRID_TYPE_CORNER_POINT = "corner_point"
WR_INPUT_MODE_FILE = "file"
WR_INPUT_MODE_CONSTANT = "constant"
WR_INPUT_MODE_MIXED = "mixed"
CASE_TYPE_GAS_WATER = "gas_water"

DATASET_STATUS_READY = "ready"
DATASET_STATUS_STALE = "stale"
DATASET_STATUS_INVALID = "invalid"

RUN_TYPE_SIMULATION = "simulation"
RUN_TYPE_HISTORY_MATCHING = "history_matching"
RUN_TYPE_HISTORY_TARGET = "history_target"
RUN_STATUS_PREPARING = "preparing"
RUN_STATUS_RUNNING = "running"
RUN_STATUS_COMPLETED = "completed"
RUN_STATUS_FAILED = "failed"
RUN_STATUS_CANCELLED = "cancelled"
RUN_STATUS_INTERRUPTED = "interrupted"


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def new_case_id():
    return f"case_{uuid.uuid4().hex[:12]}"


def new_project_id():
    return f"project_{uuid.uuid4().hex[:12]}"


def new_dataset_id():
    return f"dataset_{uuid.uuid4().hex[:12]}"


def new_run_id():
    return f"run_{uuid.uuid4().hex[:12]}"


def default_model_config():
    return {
        "schema_version": 1,
        "model_type": MODEL_TYPE_NORMAL,
        "grid_type": GRID_TYPE_CORNER_POINT,
        "enable_lgr": True,
        "enable_natural_fractures": True,
        "enable_hydraulic_fractures": False,
        "enable_real_gas_pvt": True,
        "wr_input_mode": WR_INPUT_MODE_FILE,
        "confirmed": False,
    }


def normalize_model_config(config=None, legacy_refinement=None):
    normalized = default_model_config()
    if legacy_refinement is not None and not config:
        normalized["enable_lgr"] = str(legacy_refinement).strip() not in {
            "", "0", "false", "False", "不加密",
        }

    if isinstance(config, dict):
        normalized.update({
            key: value
            for key, value in config.items()
            if key in normalized
        })

    if normalized["model_type"] not in {MODEL_TYPE_NORMAL, MODEL_TYPE_WR}:
        normalized["model_type"] = MODEL_TYPE_NORMAL
    if normalized["grid_type"] != GRID_TYPE_CORNER_POINT:
        normalized["grid_type"] = GRID_TYPE_CORNER_POINT
    if normalized["wr_input_mode"] not in {
        WR_INPUT_MODE_FILE,
        WR_INPUT_MODE_CONSTANT,
        WR_INPUT_MODE_MIXED,
    }:
        normalized["wr_input_mode"] = WR_INPUT_MODE_FILE

    for key in (
        "enable_lgr",
        "enable_natural_fractures",
        "enable_hydraulic_fractures",
        "enable_real_gas_pvt",
        "confirmed",
    ):
        normalized[key] = bool(normalized.get(key))
    normalized["schema_version"] = int(normalized.get("schema_version") or 1)
    return normalized


@dataclass
class InputState:
    """Editable inputs owned by one case."""

    model_config: dict = field(default_factory=default_model_config)
    case_data_path: str = ""
    case_data_summary: dict = field(default_factory=dict)
    case_data_sections: list = field(default_factory=list)
    case_data_schema: dict = field(default_factory=dict)
    checked_items: dict = field(default_factory=dict)
    module_values: dict = field(default_factory=dict)
    input_assets: dict = field(default_factory=dict)
    input_revision: int = 0
    input_fingerprint: str = ""

    def __post_init__(self):
        self.model_config = normalize_model_config(self.model_config)
        self.case_data_summary = dict(self.case_data_summary or {})
        self.case_data_sections = list(self.case_data_sections or [])
        self.case_data_schema = dict(self.case_data_schema or {})
        self.checked_items = dict(self.checked_items or {})
        self.module_values = dict(self.module_values or {})
        self.input_assets = dict(self.input_assets or {})
        self.input_revision = max(0, int(self.input_revision or 0))

    def touch(self):
        self.input_revision += 1
        self.input_fingerprint = ""
        return self.input_revision

    def to_dict(self):
        return {
            "model_config": copy.deepcopy(self.model_config),
            "case_data_path": self.case_data_path,
            "case_data_summary": copy.deepcopy(self.case_data_summary),
            "case_data_sections": copy.deepcopy(self.case_data_sections),
            "case_data_schema": copy.deepcopy(self.case_data_schema),
            "checked_items": copy.deepcopy(self.checked_items),
            "module_values": copy.deepcopy(self.module_values),
            "input_assets": copy.deepcopy(self.input_assets),
            "input_revision": self.input_revision,
            "input_fingerprint": self.input_fingerprint,
        }

    @classmethod
    def from_dict(cls, payload, legacy_refinement=None):
        payload = payload or {}
        return cls(
            model_config=normalize_model_config(
                payload.get("model_config"), legacy_refinement),
            case_data_path=payload.get("case_data_path", "") or "",
            case_data_summary=copy.deepcopy(
                payload.get("case_data_summary") or {}),
            case_data_sections=copy.deepcopy(
                payload.get("case_data_sections") or []),
            case_data_schema=copy.deepcopy(
                payload.get("case_data_schema") or {}),
            checked_items=copy.deepcopy(payload.get("checked_items") or {}),
            module_values=copy.deepcopy(payload.get("module_values") or {}),
            input_assets=copy.deepcopy(payload.get("input_assets") or {}),
            input_revision=payload.get("input_revision", 0),
            input_fingerprint=payload.get("input_fingerprint", "") or "",
        )


@dataclass
class DatasetRecord:
    """One built Dataset revision owned by a case."""

    dataset_id: str = ""
    path: str = ""
    input_revision: int = 0
    input_fingerprint: str = ""
    schema_version: str = ""
    validation: dict = field(default_factory=dict)
    summary: dict = field(default_factory=dict)
    status: str = DATASET_STATUS_READY
    created_at: str = ""

    def __post_init__(self):
        if not self.dataset_id:
            self.dataset_id = new_dataset_id()
        if self.status not in {
            DATASET_STATUS_READY,
            DATASET_STATUS_STALE,
            DATASET_STATUS_INVALID,
        }:
            self.status = DATASET_STATUS_READY
        if not self.created_at:
            self.created_at = utc_now()
        self.validation = dict(self.validation or {})
        self.summary = dict(self.summary or {})

    def mark_stale(self, reason):
        self.status = DATASET_STATUS_STALE
        self.summary["stale"] = True
        self.summary["stale_reason"] = str(reason or "")

    def to_dict(self):
        return {
            "dataset_id": self.dataset_id,
            "path": self.path,
            "input_revision": int(self.input_revision or 0),
            "input_fingerprint": self.input_fingerprint,
            "schema_version": self.schema_version,
            "validation": copy.deepcopy(self.validation),
            "summary": copy.deepcopy(self.summary),
            "status": self.status,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, payload):
        payload = payload or {}
        return cls(
            dataset_id=payload.get("dataset_id", "") or "",
            path=payload.get("path", "") or "",
            input_revision=payload.get("input_revision", 0),
            input_fingerprint=payload.get("input_fingerprint", "") or "",
            schema_version=payload.get("schema_version", "") or "",
            validation=copy.deepcopy(payload.get("validation") or {}),
            summary=copy.deepcopy(payload.get("summary") or {}),
            status=payload.get("status", DATASET_STATUS_READY),
            created_at=payload.get("created_at", "") or "",
        )


@dataclass
class RunRecord:
    """Persistent metadata for a simulation or analysis run."""

    run_id: str = ""
    case_id: str = ""
    run_type: str = RUN_TYPE_SIMULATION
    dataset_id: str = ""
    dataset_path: str = ""
    input_revision: int = 0
    input_fingerprint: str = ""
    model_type: str = MODEL_TYPE_NORMAL
    status: str = RUN_STATUS_PREPARING
    parameters: dict = field(default_factory=dict)
    artifacts: dict = field(default_factory=dict)
    summary: dict = field(default_factory=dict)
    created_at: str = ""
    started_at: str = ""
    finished_at: str = ""
    exit_code: int = None
    error_message: str = ""

    def __post_init__(self):
        if not self.run_id:
            self.run_id = new_run_id()
        if not self.created_at:
            self.created_at = utc_now()
        if self.run_type not in {
            RUN_TYPE_SIMULATION,
            RUN_TYPE_HISTORY_MATCHING,
            RUN_TYPE_HISTORY_TARGET,
        }:
            self.run_type = RUN_TYPE_SIMULATION
        if self.status not in {
            RUN_STATUS_PREPARING,
            RUN_STATUS_RUNNING,
            RUN_STATUS_COMPLETED,
            RUN_STATUS_FAILED,
            RUN_STATUS_CANCELLED,
            RUN_STATUS_INTERRUPTED,
        }:
            self.status = RUN_STATUS_PREPARING
        self.parameters = dict(self.parameters or {})
        self.artifacts = dict(self.artifacts or {})
        self.summary = dict(self.summary or {})

    def mark_running(self):
        self.status = RUN_STATUS_RUNNING
        if not self.started_at:
            self.started_at = utc_now()
        self.finished_at = ""
        self.exit_code = None
        self.error_message = ""

    def mark_completed(self, exit_code=0, summary=None):
        if not self.started_at:
            self.started_at = self.created_at or utc_now()
        self.status = RUN_STATUS_COMPLETED
        self.finished_at = utc_now()
        self.exit_code = int(exit_code or 0)
        self.error_message = ""
        if summary:
            self.summary.update(copy.deepcopy(summary))

    def mark_failed(self, message, exit_code=None):
        if not self.started_at:
            self.started_at = self.created_at or utc_now()
        self.status = RUN_STATUS_FAILED
        self.finished_at = utc_now()
        self.exit_code = exit_code
        self.error_message = str(message or "")

    def mark_cancelled(self, message=""):
        if not self.started_at:
            self.started_at = self.created_at or utc_now()
        self.status = RUN_STATUS_CANCELLED
        self.finished_at = utc_now()
        self.exit_code = None
        self.error_message = str(message or "")

    def mark_interrupted(self, message=""):
        if not self.started_at:
            self.started_at = self.created_at or utc_now()
        self.status = RUN_STATUS_INTERRUPTED
        self.finished_at = utc_now()
        self.exit_code = None
        self.error_message = str(message or "")

    def to_dict(self):
        return {
            "run_id": self.run_id,
            "case_id": self.case_id,
            "run_type": self.run_type,
            "dataset_id": self.dataset_id,
            "dataset_path": self.dataset_path,
            "input_revision": self.input_revision,
            "input_fingerprint": self.input_fingerprint,
            "model_type": self.model_type,
            "status": self.status,
            "parameters": copy.deepcopy(self.parameters),
            "artifacts": copy.deepcopy(self.artifacts),
            "summary": copy.deepcopy(self.summary),
            "created_at": self.created_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "exit_code": self.exit_code,
            "error_message": self.error_message,
        }

    @classmethod
    def from_dict(cls, payload):
        payload = payload or {}
        return cls(
            run_id=payload.get("run_id", "") or "",
            case_id=payload.get("case_id", "") or "",
            run_type=payload.get("run_type", RUN_TYPE_SIMULATION),
            dataset_id=payload.get("dataset_id", "") or "",
            dataset_path=payload.get("dataset_path", "") or "",
            input_revision=payload.get("input_revision", 0),
            input_fingerprint=payload.get("input_fingerprint", "") or "",
            model_type=payload.get("model_type", MODEL_TYPE_NORMAL),
            status=payload.get("status", RUN_STATUS_PREPARING),
            parameters=copy.deepcopy(payload.get("parameters") or {}),
            artifacts=copy.deepcopy(payload.get("artifacts") or {}),
            summary=copy.deepcopy(payload.get("summary") or {}),
            created_at=payload.get("created_at", "") or "",
            started_at=payload.get("started_at", "") or "",
            finished_at=payload.get("finished_at", "") or "",
            exit_code=payload.get("exit_code"),
            error_message=payload.get("error_message", "") or "",
        )


@dataclass
class CaseState:
    """Complete persistent state owned by one simulation case."""

    case_id: str = ""
    case_name: str = "NewCase"
    case_type: str = CASE_TYPE_GAS_WATER
    description: str = ""
    parent_case_id: str = ""
    derived_from_run_id: str = ""
    derivation: dict = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""
    input_state: InputState = field(default_factory=InputState)
    dataset_records: list = field(default_factory=list)
    active_dataset_id: str = ""
    run_records: list = field(default_factory=list)
    active_run_id: str = ""
    ui_state: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.case_id:
            self.case_id = new_case_id()
        if not self.case_name:
            self.case_name = "NewCase"
        if self.case_type != CASE_TYPE_GAS_WATER:
            self.case_type = CASE_TYPE_GAS_WATER
        now = utc_now()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = self.created_at
        if not isinstance(self.input_state, InputState):
            self.input_state = InputState.from_dict(self.input_state)
        self.dataset_records = [
            item if isinstance(item, DatasetRecord) else DatasetRecord.from_dict(item)
            for item in (self.dataset_records or [])
        ]
        seen_dataset_ids = set()
        for record in self.dataset_records:
            if record.dataset_id in seen_dataset_ids:
                record.dataset_id = new_dataset_id()
            seen_dataset_ids.add(record.dataset_id)
        self.run_records = [
            item if isinstance(item, RunRecord) else RunRecord.from_dict(item)
            for item in (self.run_records or [])
        ]
        seen_run_ids = set()
        for record in self.run_records:
            if record.run_id in seen_run_ids:
                record.run_id = new_run_id()
            seen_run_ids.add(record.run_id)
            # The containing Case is the authority. Repair old or malformed
            # records so later callbacks cannot write across case boundaries.
            record.case_id = self.case_id
        if self.active_dataset_id and not self.dataset_by_id(self.active_dataset_id):
            self.active_dataset_id = ""
        if not self.active_dataset_id and self.dataset_records:
            self.active_dataset_id = self.dataset_records[-1].dataset_id
        if self.active_run_id and not self.run_by_id(self.active_run_id):
            self.active_run_id = ""
        if not self.active_run_id and self.run_records:
            self.active_run_id = self.run_records[-1].run_id
        self.ui_state = dict(self.ui_state or {})
        self.derivation = dict(self.derivation or {})

    def touch(self):
        self.updated_at = utc_now()

    def dataset_by_id(self, dataset_id):
        for record in self.dataset_records:
            if record.dataset_id == dataset_id:
                return record
        return None

    def active_dataset(self):
        return self.dataset_by_id(self.active_dataset_id)

    def add_dataset(self, record, activate=True):
        if not isinstance(record, DatasetRecord):
            record = DatasetRecord.from_dict(record)
        self.dataset_records.append(record)
        if activate:
            self.active_dataset_id = record.dataset_id
        self.touch()
        return record

    def run_by_id(self, run_id):
        for record in self.run_records:
            if record.run_id == run_id:
                return record
        return None

    def active_run(self):
        return self.run_by_id(self.active_run_id)

    def add_run(self, record, activate=True):
        if not isinstance(record, RunRecord):
            record = RunRecord.from_dict(record)
        if not record.case_id:
            record.case_id = self.case_id
        self.run_records.append(record)
        if activate:
            self.active_run_id = record.run_id
        self.touch()
        return record

    def interrupt_unfinished_runs(self, message="Application closed before the run finished"):
        interrupted = []
        for record in self.run_records:
            if record.status in {RUN_STATUS_PREPARING, RUN_STATUS_RUNNING}:
                record.mark_interrupted(message)
                interrupted.append(record)
        if interrupted:
            self.touch()
        return interrupted

    def unfinished_runs(self):
        return [
            record for record in self.run_records
            if record.status in {RUN_STATUS_PREPARING, RUN_STATUS_RUNNING}
        ]

    def has_unfinished_runs(self):
        return bool(self.unfinished_runs())

    def to_dict(self):
        return {
            "case_id": self.case_id,
            "case_name": self.case_name,
            "case_type": self.case_type,
            "description": self.description,
            "parent_case_id": self.parent_case_id,
            "derived_from_run_id": self.derived_from_run_id,
            "derivation": copy.deepcopy(self.derivation),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "input_state": self.input_state.to_dict(),
            "dataset_records": [item.to_dict() for item in self.dataset_records],
            "active_dataset_id": self.active_dataset_id,
            "run_records": [item.to_dict() for item in self.run_records],
            "active_run_id": self.active_run_id,
            "ui_state": copy.deepcopy(self.ui_state),
        }

    @classmethod
    def from_dict(cls, payload):
        payload = payload or {}
        return cls(
            case_id=payload.get("case_id", "") or "",
            case_name=payload.get("case_name", "NewCase") or "NewCase",
            case_type=payload.get("case_type", CASE_TYPE_GAS_WATER),
            description=payload.get("description", "") or "",
            parent_case_id=payload.get("parent_case_id", "") or "",
            derived_from_run_id=payload.get("derived_from_run_id", "") or "",
            derivation=copy.deepcopy(payload.get("derivation") or {}),
            created_at=payload.get("created_at", "") or "",
            updated_at=payload.get("updated_at", "") or "",
            input_state=InputState.from_dict(payload.get("input_state") or {}),
            dataset_records=copy.deepcopy(payload.get("dataset_records") or []),
            active_dataset_id=payload.get("active_dataset_id", "") or "",
            run_records=copy.deepcopy(payload.get("run_records") or []),
            active_run_id=payload.get("active_run_id", "") or "",
            ui_state=copy.deepcopy(payload.get("ui_state") or {}),
        )
