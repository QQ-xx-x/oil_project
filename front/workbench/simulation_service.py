# -*- coding: utf-8 -*-
"""Asynchronous workbench simulation service with case-bound run context."""

import json
import os
import sys
import tempfile
from pathlib import Path

from PyQt5.QtCore import (
    QObject,
    QProcess,
    QProcessEnvironment,
    pyqtSignal,
)

from ..data_models import SimulationData
from .case_data_simulation_adapter import (
    CaseDataSimulationAdapterError,
    build_case_data_simulation_input,
)
from .case_dataset_simulation_adapter import (
    CaseDatasetSimulationAdapterError,
    build_case_dataset_params,
)
from .corner_parameter_adapter import CornerParameterError, build_corner_grid_params


class WorkbenchSimulationService(QObject):
    # Compatibility signals used by integrations written before run contexts.
    started = pyqtSignal(dict)
    log_message = pyqtSignal(str)
    finished = pyqtSignal(object, str)
    failed = pyqtSignal(str)

    # Case-safe signals. Every terminal callback carries its originating run.
    run_started = pyqtSignal(dict, dict)
    run_finished = pyqtSignal(object, str, dict)
    run_failed = pyqtSignal(str, dict)

    def __init__(self, project_root, parent=None):
        super().__init__(parent)
        self.project_root = os.path.abspath(project_root)
        self.app_root = str(Path(__file__).resolve().parents[2])
        self.process = None
        self.result_path = ""
        self.run_context = {}
        self._output_buffer = ""
        self._stop_requested = False
        self._failure_emitted = False

    def is_running(self):
        return self.process is not None and self.process.state() != QProcess.NotRunning

    def build_run_params(self, project_state):
        return self._build_run_params(project_state)

    def run(self, project_state=None, run_context=None, params=None):
        context = dict(run_context or {})
        if self.is_running():
            message = "A simulation is already running"
            self.run_failed.emit(message, context)
            self.failed.emit(message)
            return False

        try:
            params = dict(params) if params is not None else self._build_run_params(
                project_state)
        except (
            CornerParameterError,
            CaseDataSimulationAdapterError,
            CaseDatasetSimulationAdapterError,
        ) as exc:
            self._emit_failure(str(exc), context)
            return False

        run_dir = str(context.get("run_dir") or "").strip()
        if run_dir:
            run_dir = os.path.abspath(run_dir)
            os.makedirs(run_dir, exist_ok=True)
            result_path = str(
                context.get("result_path")
                or os.path.join(run_dir, "simulation_result.json")
            )
            log_path = str(
                context.get("log_path")
                or os.path.join(run_dir, "run.log")
            )
        else:
            tmp_dir = os.path.join(self.project_root, ".tmp")
            os.makedirs(tmp_dir, exist_ok=True)
            fd, result_path = tempfile.mkstemp(
                prefix="workbench_corner_result_",
                suffix=".json",
                dir=tmp_dir,
            )
            os.close(fd)
            run_dir = self.app_root
            log_path = ""

        context.update({
            "run_dir": run_dir,
            "result_path": os.path.abspath(result_path),
            "log_path": os.path.abspath(log_path) if log_path else "",
        })
        self.run_context = context
        self.result_path = context["result_path"]
        self._output_buffer = ""
        self._stop_requested = False
        self._failure_emitted = False
        self._initialize_log(context.get("log_path"))

        process = QProcess(self)
        process.setWorkingDirectory(run_dir)
        process.setProgram(sys.executable)
        process.setArguments([
            "-u",
            "-m",
            "front.simulation_runner",
            "--output",
            self.result_path,
            "--params",
            json.dumps(params, ensure_ascii=False),
        ])
        environment = QProcessEnvironment.systemEnvironment()
        python_path = environment.value("PYTHONPATH")
        entries = [self.app_root]
        if python_path:
            entries.append(python_path)
        environment.insert("PYTHONPATH", os.pathsep.join(entries))
        process.setProcessEnvironment(environment)
        process.setProcessChannelMode(QProcess.MergedChannels)
        process.readyReadStandardOutput.connect(self._handle_output)
        process.finished.connect(self._handle_finished)
        process.errorOccurred.connect(self._handle_error)
        self.process = process

        process.start()
        self.started.emit(params)
        self.run_started.emit(params, dict(context))
        source = params.get("interface_source")
        if source == "case_dataset":
            self.log_message.emit("[Run] case_dataset parameters submitted")
        elif source == "case_data":
            self.log_message.emit("[Run] CaseData parameters submitted")
        else:
            self.log_message.emit("[Run] Corner Grid simulation started")
        return True

    def _build_run_params(self, project_state):
        if hasattr(project_state, "is_case_dataset_ready"):
            if not project_state.is_case_dataset_ready():
                reason = project_state.case_dataset_readiness_reason()
                raise CaseDatasetSimulationAdapterError(reason)
        dataset_path = str(
            getattr(project_state, "case_dataset_path", "") or "").strip()
        dataset_summary = getattr(
            project_state, "case_dataset_summary", {}) or {}
        if dataset_path:
            if dataset_summary.get("stale"):
                reason = dataset_summary.get("stale_reason") or (
                    "CaseData changed; rebuild the Dataset before running")
                raise CaseDatasetSimulationAdapterError(reason)
            return build_case_dataset_params(dataset_path)
        raise CaseDatasetSimulationAdapterError(
            "当前算例尚未生成 Dataset")

    def stop(self):
        if not self.is_running():
            return False
        self._stop_requested = True
        self.log_message.emit("[Run] Stopping simulation")
        self.process.kill()
        return True

    def _handle_output(self):
        if self.process is None:
            return
        raw = bytes(self.process.readAllStandardOutput())
        if not raw:
            return
        self._append_log(raw)
        chunk = raw.decode("utf-8", errors="replace")
        self._output_buffer += chunk
        while "\n" in self._output_buffer:
            line, self._output_buffer = self._output_buffer.split("\n", 1)
            line = line.rstrip()
            if line:
                self.log_message.emit(line)

    def _flush_output(self):
        tail = self._output_buffer.strip()
        self._output_buffer = ""
        if tail:
            self.log_message.emit(tail)

    def _handle_finished(self, exit_code, exit_status):
        self._handle_output()
        self._flush_output()
        process = self.process
        context = dict(self.run_context or {})
        context["exit_code"] = int(exit_code)
        context["cancelled"] = bool(self._stop_requested)
        self.process = None

        if self._failure_emitted:
            self._cleanup_process(process)
            self._clear_active_run()
            return
        if self._stop_requested:
            self._emit_failure("Simulation cancelled", context)
            self._cleanup_process(process)
            self._clear_active_run()
            return
        if exit_status != QProcess.NormalExit or exit_code != 0:
            self._emit_failure(
                f"Simulation failed with process exit code {exit_code}",
                context,
            )
            self._cleanup_process(process)
            self._clear_active_run()
            return
        if not self.result_path or not os.path.exists(self.result_path):
            self._emit_failure(
                "Simulation finished without producing a result JSON",
                context,
            )
            self._cleanup_process(process)
            self._clear_active_run()
            return

        try:
            sim_data = SimulationData()
            sim_data.load_json(self.result_path)
        except Exception as exc:
            self._emit_failure(f"Failed to load result JSON: {exc}", context)
            self._cleanup_process(process)
            self._clear_active_run()
            return

        self.log_message.emit("[Run] Simulation completed")
        self.run_finished.emit(sim_data, self.result_path, context)
        self.finished.emit(sim_data, self.result_path)
        self._cleanup_process(process)
        self._clear_active_run()

    def _handle_error(self, process_error):
        if process_error != QProcess.FailedToStart or self._failure_emitted:
            return
        process = self.process
        self.process = None
        context = dict(self.run_context or {})
        context["cancelled"] = False
        self._emit_failure("Simulation process failed to start", context)
        self._cleanup_process(process)
        self._clear_active_run()

    def _emit_failure(self, message, context=None):
        self._failure_emitted = True
        context = dict(context or self.run_context or {})
        self.run_failed.emit(str(message), context)
        self.failed.emit(str(message))

    def _initialize_log(self, log_path):
        if not log_path:
            return
        os.makedirs(os.path.dirname(os.path.abspath(log_path)), exist_ok=True)
        with open(log_path, "wb") as file:
            file.write(b"")

    def _append_log(self, raw):
        log_path = str((self.run_context or {}).get("log_path") or "")
        if not log_path:
            return
        try:
            with open(log_path, "ab") as file:
                file.write(raw)
        except OSError as exc:
            self.log_message.emit(f"[Run] Failed to write run log: {exc}")

    @staticmethod
    def _cleanup_process(process):
        if process is not None:
            process.deleteLater()

    def _clear_active_run(self):
        self.run_context = {}
        self._stop_requested = False


__all__ = ["WorkbenchSimulationService"]
