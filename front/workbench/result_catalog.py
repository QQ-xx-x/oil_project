# -*- coding: utf-8 -*-
"""Run-aware result descriptors for the workbench result tree."""

import os
from dataclasses import dataclass, field

from .case_models import (
    RUN_STATUS_COMPLETED,
    RUN_TYPE_HISTORY_MATCHING,
    RUN_TYPE_SIMULATION,
)


RESULT_AVAILABLE = "available"
RESULT_MISSING = "missing"
RESULT_CORRUPT = "corrupt"
RESULT_PENDING = "pending"
RESULT_UNAVAILABLE = "unavailable"


FIELD_RESULTS = (
    ("压力场", "pressure_field"),
    ("含水饱和度场", "water_saturation_field"),
    ("孔隙度场", "porosity_field"),
    ("Kx 渗透率场", "permeability_x_field"),
    ("Ky 渗透率场", "permeability_y_field"),
    ("Kz 渗透率场", "permeability_z_field"),
)

CHART_RESULTS = (
    ("生产曲线", "production_curve", "output_sim_path"),
    ("PVT 表曲线", "pvt_curve", "gas_pvt_table_path"),
    ("Blasingame 曲线", "blasingame_curve", "output_sim_path"),
)


@dataclass(frozen=True)
class RunResultDescriptor:
    case_id: str
    run_id: str
    run_type: str
    dataset_id: str
    status: str
    created_at: str
    finished_at: str
    model_type: str
    result_json_path: str
    run_dir: str
    availability: str
    field_results: tuple = field(default_factory=tuple)
    chart_results: tuple = field(default_factory=tuple)
    artifacts: dict = field(default_factory=dict)
    errors: tuple = field(default_factory=tuple)
    warnings: tuple = field(default_factory=tuple)

    @property
    def has_result_json(self):
        return self.availability == RESULT_AVAILABLE

    @property
    def display_time(self):
        value = self.finished_at or self.created_at or ""
        return value.replace("T", " ")[:19]


class RunResultCatalog:
    def __init__(self, case_id="", descriptors=None):
        self.case_id = case_id or ""
        self.descriptors = list(descriptors or [])

    @classmethod
    def from_case(cls, case_state):
        if case_state is None:
            return cls()
        descriptors = [
            build_run_result_descriptor(case_state, record)
            for record in reversed(case_state.run_records or [])
            if getattr(record, "run_type", RUN_TYPE_SIMULATION) in {
                RUN_TYPE_SIMULATION,
                RUN_TYPE_HISTORY_MATCHING,
            }
        ]
        return cls(case_state.case_id, descriptors)

    def by_run_id(self, run_id):
        for descriptor in self.descriptors:
            if descriptor.run_id == run_id:
                return descriptor
        return None


def build_run_result_descriptor(case_state, run_record):
    artifacts = dict(getattr(run_record, "artifacts", {}) or {})
    result_path = str(artifacts.get("result_json") or "")
    run_dir = str(artifacts.get("run_dir") or "")
    errors = []
    warnings = []
    status = str(getattr(run_record, "status", "") or "")
    run_type = str(
        getattr(run_record, "run_type", RUN_TYPE_SIMULATION)
        or RUN_TYPE_SIMULATION)

    load_error = str(
        (getattr(run_record, "summary", {}) or {}).get(
            "result_load_error") or "")
    if status != RUN_STATUS_COMPLETED:
        availability = (
            RESULT_PENDING
            if status in {"preparing", "running"}
            else RESULT_UNAVAILABLE
        )
        message = str(getattr(run_record, "error_message", "") or "")
        if message:
            if status == "failed":
                errors.append(message)
            else:
                warnings.append(message)
    elif load_error:
        availability = RESULT_CORRUPT
        errors.append(load_error)
    elif not result_path:
        availability = RESULT_MISSING
        errors.append("运行记录没有登记 result_json")
    elif not os.path.isfile(result_path):
        availability = RESULT_MISSING
        errors.append(f"结果 JSON 不存在: {result_path}")
    elif os.path.getsize(result_path) <= 0:
        availability = RESULT_MISSING
        errors.append(f"结果 JSON 为空: {result_path}")
    else:
        availability = RESULT_AVAILABLE

    field_results = (
        FIELD_RESULTS
        if availability == RESULT_AVAILABLE and run_type == RUN_TYPE_SIMULATION
        else ()
    )
    chart_results = []
    if run_type == RUN_TYPE_HISTORY_MATCHING:
        if availability == RESULT_AVAILABLE:
            chart_results.append(("历史拟合结果", "history_matching"))
    else:
        for label, key, artifact_key in CHART_RESULTS:
            path = str(artifacts.get(artifact_key) or "")
            if path and os.path.isfile(path):
                chart_results.append((label, key))

    if run_dir and not os.path.isdir(run_dir):
        warnings.append(f"Run 目录不存在: {run_dir}")

    return RunResultDescriptor(
        case_id=getattr(case_state, "case_id", "") or "",
        run_id=getattr(run_record, "run_id", "") or "",
        run_type=run_type,
        dataset_id=getattr(run_record, "dataset_id", "") or "",
        status=status,
        created_at=getattr(run_record, "created_at", "") or "",
        finished_at=getattr(run_record, "finished_at", "") or "",
        model_type=getattr(run_record, "model_type", "normal") or "normal",
        result_json_path=result_path,
        run_dir=run_dir,
        availability=availability,
        field_results=tuple(field_results),
        chart_results=tuple(chart_results),
        artifacts=artifacts,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


__all__ = [
    "RESULT_AVAILABLE",
    "RESULT_CORRUPT",
    "RESULT_MISSING",
    "RESULT_PENDING",
    "RESULT_UNAVAILABLE",
    "RunResultCatalog",
    "RunResultDescriptor",
    "build_run_result_descriptor",
]
