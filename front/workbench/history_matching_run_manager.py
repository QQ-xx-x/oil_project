# -*- coding: utf-8 -*-
"""绑定算例的历史拟合生命周期和派生算例支持。"""

import copy
import json
import os
import shutil
import uuid
from dataclasses import asdict, dataclass

from .case_models import (
    DATASET_STATUS_READY,
    RUN_TYPE_HISTORY_MATCHING,
    RunRecord,
    utc_now,
)


HISTORY_MATCHING_SNAPSHOT_SCHEMA_VERSION = "history_matching_run_v1"


class HistoryMatchingRunError(ValueError):
    """无法准备或解析历史拟合运行时抛出。"""


@dataclass(frozen=True)
class HistoryMatchingRunContext:
    project_id: str
    case_id: str
    run_id: str
    dataset_id: str
    dataset_path: str
    run_dir: str
    results_dir: str
    members_dir: str
    config_path: str
    observation_path: str
    log_path: str

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_value(cls, value):
        if isinstance(value, cls):
            return value
        value = value or {}
        return cls(**{
            field: str(value.get(field) or "")
            for field in cls.__dataclass_fields__
        })


class HistoryMatchingRunManager:
    """管理历史拟合资源，并更新准确的来源算例。"""

    RESULT_FILES = {
        "result_json": "run_result.json",
        "history_fit_plot": "history_fit_gas_water.png",
        "best_fit_params": "best_fit_params.json",
        "best_fit_output": "best_fit_output.csv",
        "best_fit_summary": "best_fit_summary.json",
        "assimilation_summary": "assimilation_summary.csv",
        "best_seen_member": "best_seen_member.json",
        "ensemble_initial": "ensemble_initial.csv",
        "ensemble_final": "ensemble_final.csv",
        "observation_summary": "observation_summary.json",
    }

    def __init__(self, project_state, artifact_repository):
        if project_state is None or artifact_repository is None:
            raise HistoryMatchingRunError(
                "project_state and artifact_repository are required")
        self.project_state = project_state
        self.artifact_repository = artifact_repository

    def prepare(self, runtime_config, observation_path):
        case = self.project_state.active_case()
        if case is None:
            raise HistoryMatchingRunError("An active case is required")
        dataset = case.active_dataset()
        if dataset is None:
            raise HistoryMatchingRunError(
                "The active case must have an active Dataset")
        if dataset.status != DATASET_STATUS_READY:
            raise HistoryMatchingRunError(
                f"Active Dataset is not ready: {dataset.status}")
        if not dataset.path or not os.path.isfile(
            os.path.join(dataset.path, "manifest.json")
        ):
            raise HistoryMatchingRunError(
                "The active Dataset directory is missing manifest.json")

        source_observation = os.path.abspath(str(observation_path or ""))
        if not os.path.isfile(source_observation):
            raise HistoryMatchingRunError(
                f"Observation CSV does not exist: {source_observation}")

        run_id, run_dir = self.artifact_repository.allocate_run_dir(
            case.case_id, run_type=RUN_TYPE_HISTORY_MATCHING)
        run_dir = os.path.abspath(run_dir)
        results_dir = os.path.join(run_dir, "results")
        members_dir = os.path.join(run_dir, "members")
        observation_copy = os.path.join(
            run_dir, "observation" + os.path.splitext(source_observation)[1].lower())
        config_path = os.path.join(run_dir, "enkf_runtime_config.json")
        log_path = os.path.join(run_dir, "run.log")
        context = HistoryMatchingRunContext(
            project_id=self.project_state.project_id,
            case_id=case.case_id,
            run_id=run_id,
            dataset_id=dataset.dataset_id,
            dataset_path=os.path.abspath(dataset.path) if dataset.path else "",
            run_dir=run_dir,
            results_dir=results_dir,
            members_dir=members_dir,
            config_path=config_path,
            observation_path=observation_copy,
            log_path=log_path,
        )

        config = copy.deepcopy(runtime_config or {})
        config["history_file"] = observation_copy
        config["case_dataset_path"] = context.dataset_path
        config["results_dir"] = results_dir
        config["runs_dir"] = members_dir
        ui_runtime = dict(config.get("_ui_runtime") or {})
        ui_runtime.update({
            "run_dir": run_dir,
            "managed": True,
            "case_id": case.case_id,
            "run_id": run_id,
            "dataset_id": dataset.dataset_id,
        })
        config["_ui_runtime"] = ui_runtime
        config["_managed_run"] = {
            "schema_version": HISTORY_MATCHING_SNAPSHOT_SCHEMA_VERSION,
            "project_id": context.project_id,
            "case_id": context.case_id,
            "run_id": context.run_id,
            "dataset_id": context.dataset_id,
            "created_at": utc_now(),
            "source_observation": source_observation,
        }
        try:
            shutil.copy2(source_observation, observation_copy)
            self._write_json_atomic(config_path, config)
            observation_asset = self.artifact_repository.capture_asset(
                source_observation, source_key="history_observation")
            parameters = {
                "schema_version": HISTORY_MATCHING_SNAPSHOT_SCHEMA_VERSION,
                "optimizer": copy.deepcopy(config.get("enkf") or {}),
                "observation": copy.deepcopy(config.get("observation") or {}),
                "fit_parameters": copy.deepcopy(config.get("fit_parameters") or []),
                "base_params": copy.deepcopy(config.get("base_params") or {}),
                "well_control": copy.deepcopy(config.get("well_control") or {}),
                "simulation_days": config.get("simulation_days"),
                "random_seed": config.get("random_seed"),
                "observation_asset": observation_asset,
            }
            record = RunRecord(
                run_id=run_id,
                case_id=case.case_id,
                run_type=RUN_TYPE_HISTORY_MATCHING,
                dataset_id=dataset.dataset_id,
                dataset_path=context.dataset_path,
                input_revision=dataset.input_revision,
                input_fingerprint=dataset.input_fingerprint,
                model_type=str(
                    (case.input_state.model_config or {}).get("model_type")
                    or "normal"),
                parameters=parameters,
                artifacts={
                    "run_dir": run_dir,
                    "runtime_config": config_path,
                    "observation_csv": observation_copy,
                },
                summary={
                    "ensemble_size": (config.get("enkf") or {}).get("ensemble_size"),
                    "iteration_count": len((config.get("enkf") or {}).get("alphas") or []),
                    "iterations": [],
                },
            )
            self.project_state.add_case_run_record(
                case.case_id, record, activate=True)
        except Exception:
            shutil.rmtree(run_dir, ignore_errors=True)
            raise
        return context

    def record(self, context):
        context = HistoryMatchingRunContext.from_value(context)
        record = self.project_state.run_record(context.case_id, context.run_id)
        if record is None or record.run_type != RUN_TYPE_HISTORY_MATCHING:
            raise HistoryMatchingRunError(
                f"Unknown history-matching run: {context.case_id}/{context.run_id}")
        return record

    def mark_running(self, context):
        record = self.record(context)
        record.mark_running()
        self._touch_case(record.case_id)
        return record

    def record_member(self, context, iteration, member, objective):
        record = self.record(context)
        record.summary["progress"] = {
            "iteration": int(iteration),
            "member": int(member),
            "objective": float(objective),
        }
        self._touch_case(record.case_id)
        return record

    def record_iteration(self, context, iteration, minimum, mean, maximum):
        record = self.record(context)
        entry = {
            "iteration": int(iteration),
            "objective_min": float(minimum),
            "objective_mean": float(mean),
            "objective_max": float(maximum),
        }
        iterations = list(record.summary.get("iterations") or [])
        iterations = [
            item for item in iterations
            if int(item.get("iteration", -1)) != entry["iteration"]
        ]
        iterations.append(entry)
        iterations.sort(key=lambda item: int(item.get("iteration", 0)))
        record.summary["iterations"] = iterations
        record.summary["progress"] = copy.deepcopy(entry)
        self._touch_case(record.case_id)
        return record

    def append_log(self, context, text):
        context = HistoryMatchingRunContext.from_value(context)
        os.makedirs(context.run_dir, exist_ok=True)
        with open(context.log_path, "a", encoding="utf-8") as file:
            file.write(str(text).rstrip("\r\n") + "\n")

    def mark_completed(self, context, payload=None, exit_code=0):
        context = HistoryMatchingRunContext.from_value(context)
        record = self.record(context)
        payload = copy.deepcopy(payload or self.load_payload(context) or {})
        record.artifacts.update(self.collect_artifacts(context))
        summary = self._completion_summary(payload, record.artifacts)
        record.mark_completed(exit_code=exit_code, summary=summary)
        self._touch_case(record.case_id)
        return record

    def mark_failed(self, context, message, exit_code=None, cancelled=False):
        context = HistoryMatchingRunContext.from_value(context)
        record = self.record(context)
        record.artifacts.update(self.collect_artifacts(context))
        if cancelled:
            record.mark_cancelled(message)
        else:
            record.mark_failed(message, exit_code=exit_code)
        record.summary.update(self._artifact_summary(record.artifacts))
        self._touch_case(record.case_id)
        return record

    def collect_artifacts(self, context):
        context = HistoryMatchingRunContext.from_value(context)
        artifacts = {
            "run_dir": context.run_dir,
            "runtime_config": context.config_path,
            "observation_csv": context.observation_path,
        }
        if os.path.isfile(context.log_path):
            artifacts["run_log"] = context.log_path
        if os.path.isdir(context.members_dir):
            artifacts["members_dir"] = context.members_dir
        for key, filename in self.RESULT_FILES.items():
            path = os.path.join(context.results_dir, filename)
            if os.path.isfile(path):
                artifacts[key] = os.path.abspath(path)
        return artifacts

    def load_payload(self, context):
        context = HistoryMatchingRunContext.from_value(context)
        path = os.path.join(context.results_dir, "run_result.json")
        if not os.path.isfile(path):
            return None
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)

    def create_derived_case(self, context, case_name=""):
        context = HistoryMatchingRunContext.from_value(context)
        source = self.project_state.case_by_id(context.case_id)
        record = self.record(context)
        if source is None:
            raise HistoryMatchingRunError(f"Unknown source case: {context.case_id}")
        if record.status != "completed":
            raise HistoryMatchingRunError(
                "Best parameters can only be applied from a completed run")

        payload = self.load_payload(context)
        if not isinstance(payload, dict):
            result_path = (record.artifacts or {}).get("result_json")
            if result_path and os.path.isfile(result_path):
                with open(result_path, "r", encoding="utf-8") as file:
                    payload = json.load(file)
        if not isinstance(payload, dict):
            raise HistoryMatchingRunError("History-matching result payload is missing")

        physical = copy.deepcopy(payload.get("physical_fit_parameters") or {})
        fitted = copy.deepcopy(payload.get("best_fit_parameters") or {})
        input_state = copy.deepcopy(source.input_state)
        overlay = {
            "source_case_id": source.case_id,
            "source_run_id": record.run_id,
            "objective": payload.get("objective"),
            "selected_source": payload.get("selected_source"),
            "best_fit_parameters": fitted,
            "physical_fit_parameters": physical,
            "fit_parameter_specs": copy.deepcopy(
                (record.parameters or {}).get("fit_parameters") or []),
        }
        input_state.module_values["history_matching_best_parameters"] = overlay
        derived_base_params = copy.deepcopy(
            (record.parameters or {}).get("base_params") or {})
        for spec in overlay["fit_parameter_specs"]:
            name = str(spec.get("name") or "")
            path = list(spec.get("path") or [])
            value = physical.get(name, fitted.get(name))
            if path and value is not None:
                self._set_nested(derived_base_params, path, value)
            dependent = dict(spec.get("dependent") or {})
            dependent_path = list(dependent.get("path") or [])
            if (
                value is not None
                and dependent_path
                and dependent.get("formula") == "one_minus_value"
            ):
                self._set_nested(derived_base_params, dependent_path, 1.0 - float(value))
        input_state.module_values["history_matching_base_params"] = derived_base_params
        input_state.touch()
        derived = self.project_state.add_case(
            case_name=case_name or f"{source.case_name}_HM",
            case_type=source.case_type,
            description=(
                f"Derived from {source.case_name}, history-matching run "
                f"{record.run_id}"
            ),
            activate=True,
            input_state=input_state,
        )
        derived.parent_case_id = source.case_id
        derived.derived_from_run_id = record.run_id
        derived.derivation = {
            "type": "history_matching_best_parameters",
            "source_case_id": source.case_id,
            "source_run_id": record.run_id,
            "created_at": utc_now(),
            "objective": payload.get("objective"),
            "selected_source": payload.get("selected_source"),
        }
        derived.touch()
        return derived

    @staticmethod
    def _completion_summary(payload, artifacts):
        summary = HistoryMatchingRunManager._artifact_summary(artifacts)
        summary.update({
            "objective": payload.get("objective"),
            "selected_source": payload.get("selected_source"),
            "mode": payload.get("mode"),
            "best_fit_parameters": copy.deepcopy(
                payload.get("best_fit_parameters") or {}),
            "physical_fit_parameters": copy.deepcopy(
                payload.get("physical_fit_parameters") or {}),
        })
        return summary

    @staticmethod
    def _artifact_summary(artifacts):
        files = {
            path for path in (artifacts or {}).values()
            if isinstance(path, str) and os.path.isfile(path)
        }
        return {
            "artifact_file_count": len(files),
            "artifact_size_bytes": sum(os.path.getsize(path) for path in files),
        }

    def _touch_case(self, case_id):
        case = self.project_state.case_by_id(case_id)
        if case is not None:
            case.touch()

    @staticmethod
    def _set_nested(payload, path, value):
        current = payload
        for key in path[:-1]:
            nested = current.get(key)
            if not isinstance(nested, dict):
                nested = {}
                current[key] = nested
            current = nested
        current[path[-1]] = value

    @staticmethod
    def _write_json_atomic(path, payload):
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        temp_path = f"{path}.tmp_{uuid.uuid4().hex}"
        try:
            with open(temp_path, "w", encoding="utf-8") as file:
                json.dump(payload, file, ensure_ascii=False, indent=2, default=str)
            os.replace(temp_path, path)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


def context_from_record(project_id, run_record):
    """根据持久化的历史拟合 RunRecord 重建不可变上下文。"""
    artifacts = dict(getattr(run_record, "artifacts", {}) or {})
    run_dir = os.path.abspath(str(artifacts.get("run_dir") or ""))
    results_dir = os.path.join(run_dir, "results") if run_dir else ""
    return HistoryMatchingRunContext(
        project_id=str(project_id or ""),
        case_id=str(getattr(run_record, "case_id", "") or ""),
        run_id=str(getattr(run_record, "run_id", "") or ""),
        dataset_id=str(getattr(run_record, "dataset_id", "") or ""),
        dataset_path=str(getattr(run_record, "dataset_path", "") or ""),
        run_dir=run_dir,
        results_dir=results_dir,
        members_dir=str(artifacts.get("members_dir") or (
            os.path.join(run_dir, "members") if run_dir else "")),
        config_path=str(artifacts.get("runtime_config") or (
            os.path.join(run_dir, "enkf_runtime_config.json") if run_dir else "")),
        observation_path=str(artifacts.get("observation_csv") or (
            os.path.join(run_dir, "observation.csv") if run_dir else "")),
        log_path=str(artifacts.get("run_log") or (
            os.path.join(run_dir, "run.log") if run_dir else "")),
    )


__all__ = [
    "HISTORY_MATCHING_SNAPSHOT_SCHEMA_VERSION",
    "HistoryMatchingRunContext",
    "HistoryMatchingRunError",
    "HistoryMatchingRunManager",
    "context_from_record",
]
