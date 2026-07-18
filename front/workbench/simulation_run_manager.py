# -*- coding: utf-8 -*-
"""绑定算例的模拟运行生命周期和资源登记。"""

import copy
import json
import os
import shutil
import uuid
from dataclasses import asdict, dataclass

from .case_models import (
    DATASET_STATUS_READY,
    RUN_TYPE_SIMULATION,
    RunRecord,
    utc_now,
)


RUN_SNAPSHOT_SCHEMA_VERSION = "simulation_run_v1"


class SimulationRunError(ValueError):
    """无法准备或解析模拟运行时抛出。"""


@dataclass(frozen=True)
class SimulationRunContext:
    project_id: str
    case_id: str
    run_id: str
    dataset_id: str
    dataset_path: str
    run_dir: str
    result_path: str
    parameters_path: str
    log_path: str

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_value(cls, value):
        if isinstance(value, cls):
            return value
        value = value or {}
        return cls(
            project_id=str(value.get("project_id") or ""),
            case_id=str(value.get("case_id") or ""),
            run_id=str(value.get("run_id") or ""),
            dataset_id=str(value.get("dataset_id") or ""),
            dataset_path=str(value.get("dataset_path") or ""),
            run_dir=str(value.get("run_dir") or ""),
            result_path=str(value.get("result_path") or ""),
            parameters_path=str(value.get("parameters_path") or ""),
            log_path=str(value.get("log_path") or ""),
        )


class SimulationRunManager:
    """创建和更新 RunRecord，不依赖之后的当前算例。"""

    RESULT_FILES = {
        "output_sim_path": (
            "output_sim_lgr_noWR.csv",
            "output_sim_lgr_WR.csv",
            "output_sim.csv",
            "output_sim_lgr.csv",
        ),
        "final_field_path": (
            "final_field.csv",
            "final_field_lgr.csv",
            "final_field_lgr_noWR.csv",
            "final_field_lgr_WR.csv",
        ),
        "gas_pvt_table_path": ("gas_pvt_table.csv",),
    }

    def __init__(self, project_state, artifact_repository):
        if project_state is None or artifact_repository is None:
            raise SimulationRunError(
                "project_state and artifact_repository are required")
        self.project_state = project_state
        self.artifact_repository = artifact_repository

    def prepare(self, parameters):
        case = self.project_state.active_case()
        if case is None:
            raise SimulationRunError("An active case is required")
        dataset = case.active_dataset()
        if dataset is not None and dataset.status != DATASET_STATUS_READY:
            raise SimulationRunError(
                f"Active Dataset is not ready: {dataset.status}")
        interface_source = str(
            (parameters or {}).get("interface_source") or "")
        if interface_source == "case_dataset":
            if dataset is None:
                raise SimulationRunError(
                    "A ready active Dataset is required for this run")
        dataset_id = dataset.dataset_id if dataset is not None else ""
        dataset_path = dataset.path if dataset is not None else ""
        input_revision = (
            dataset.input_revision
            if dataset is not None else case.input_state.input_revision
        )
        input_fingerprint = (
            dataset.input_fingerprint
            if dataset is not None else case.input_state.input_fingerprint
        )
        run_id, run_dir = self.artifact_repository.allocate_run_dir(
            case.case_id,
            run_type=RUN_TYPE_SIMULATION,
        )
        context = SimulationRunContext(
            project_id=self.project_state.project_id,
            case_id=case.case_id,
            run_id=run_id,
            dataset_id=dataset_id,
            dataset_path=os.path.abspath(dataset_path) if dataset_path else "",
            run_dir=os.path.abspath(run_dir),
            result_path=os.path.join(run_dir, "simulation_result.json"),
            parameters_path=os.path.join(run_dir, "parameters.json"),
            log_path=os.path.join(run_dir, "run.log"),
        )
        model_config = copy.deepcopy(case.input_state.model_config or {})
        parameter_copy = copy.deepcopy(parameters or {})
        snapshot = {
            "schema_version": RUN_SNAPSHOT_SCHEMA_VERSION,
            "created_at": utc_now(),
            "project_id": self.project_state.project_id,
            "case_id": case.case_id,
            "case_name": case.case_name,
            "run_id": run_id,
            "dataset_id": dataset_id,
            "dataset_path": context.dataset_path,
            "input_revision": input_revision,
            "input_fingerprint": input_fingerprint,
            "model_config": model_config,
            "parameters": parameter_copy,
        }
        try:
            self._write_json_atomic(context.parameters_path, snapshot)
            record = RunRecord(
                run_id=run_id,
                case_id=case.case_id,
                run_type=RUN_TYPE_SIMULATION,
                dataset_id=dataset_id,
                dataset_path=context.dataset_path,
                input_revision=input_revision,
                input_fingerprint=input_fingerprint,
                model_type=str(
                    parameter_copy.get("model_type")
                    or model_config.get("model_type")
                    or "normal"),
                parameters=parameter_copy,
                artifacts={
                    "run_dir": context.run_dir,
                    "parameters_json": context.parameters_path,
                },
                summary={
                    "interface_source": parameter_copy.get(
                        "interface_source", "corner_parameters"),
                    "algorithm": parameter_copy.get("algorithm", "corner_edfm"),
                },
            )
            self.project_state.add_case_run_record(
                case.case_id, record, activate=True)
        except Exception:
            shutil.rmtree(run_dir, ignore_errors=True)
            raise
        return context

    def record(self, context):
        context = SimulationRunContext.from_value(context)
        record = self.project_state.run_record(context.case_id, context.run_id)
        if record is None:
            raise SimulationRunError(
                f"Unknown simulation run: {context.case_id}/{context.run_id}")
        return record

    def mark_running(self, context):
        record = self.record(context)
        record.mark_running()
        self._touch_case(record.case_id)
        return record

    def mark_completed(self, context, result_path=None, exit_code=0, summary=None):
        context = SimulationRunContext.from_value(context)
        record = self.record(context)
        record.artifacts.update(self.collect_artifacts(
            context, result_path=result_path))
        artifact_summary = self._artifact_summary(record.artifacts)
        if summary:
            artifact_summary.update(copy.deepcopy(summary))
        record.mark_completed(exit_code=exit_code, summary=artifact_summary)
        self._touch_case(record.case_id)
        return record

    def mark_failed(self, context, message, exit_code=None, cancelled=False):
        context = SimulationRunContext.from_value(context)
        record = self.record(context)
        record.artifacts.update(self.collect_artifacts(context))
        if cancelled:
            record.mark_cancelled(message)
        else:
            record.mark_failed(message, exit_code=exit_code)
        record.summary.update(self._artifact_summary(record.artifacts))
        self._touch_case(record.case_id)
        return record

    def collect_artifacts(self, context, result_path=None):
        context = SimulationRunContext.from_value(context)
        artifacts = {"run_dir": context.run_dir}
        candidates = {
            "parameters_json": context.parameters_path,
            "run_log": context.log_path,
            "result_json": result_path or context.result_path,
        }
        for key, path in candidates.items():
            if path and os.path.isfile(path):
                artifacts[key] = os.path.abspath(path)
        for key, names in self.RESULT_FILES.items():
            path = self._first_existing(context.run_dir, names)
            if path:
                artifacts[key] = path
        return artifacts

    def _touch_case(self, case_id):
        case = self.project_state.case_by_id(case_id)
        if case is not None:
            case.touch()

    @staticmethod
    def _first_existing(root, names):
        for name in names:
            path = os.path.abspath(os.path.join(root, name))
            if os.path.isfile(path):
                return path
        return ""

    @staticmethod
    def _artifact_summary(artifacts):
        files = [
            path for path in (artifacts or {}).values()
            if isinstance(path, str) and os.path.isfile(path)
        ]
        return {
            "artifact_file_count": len(set(files)),
            "artifact_size_bytes": sum(
                os.path.getsize(path) for path in set(files)),
        }

    @staticmethod
    def _write_json_atomic(path, payload):
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        temp_path = f"{path}.tmp_{uuid.uuid4().hex}"
        try:
            with open(temp_path, "w", encoding="utf-8") as file:
                json.dump(
                    payload,
                    file,
                    ensure_ascii=False,
                    indent=2,
                    default=_json_default,
                )
            os.replace(temp_path, path)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


def _json_default(value):
    if hasattr(value, "tolist"):
        return value.tolist()
    if hasattr(value, "item"):
        return value.item()
    return str(value)


__all__ = [
    "RUN_SNAPSHOT_SCHEMA_VERSION",
    "SimulationRunContext",
    "SimulationRunError",
    "SimulationRunManager",
]
