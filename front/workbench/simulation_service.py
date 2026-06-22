# -*- coding: utf-8 -*-
"""工作台界面使用的异步模拟运行服务。"""

import json
import os
import sys
import tempfile

from PyQt5.QtCore import QObject, QProcess, pyqtSignal

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
    started = pyqtSignal(dict)
    log_message = pyqtSignal(str)
    finished = pyqtSignal(object, str)
    failed = pyqtSignal(str)

    def __init__(self, project_root, parent=None):
        super().__init__(parent)
        self.project_root = project_root
        self.process = None
        self.result_path = ""
        self._output_buffer = ""

    def is_running(self):
        return self.process is not None and self.process.state() != QProcess.NotRunning

    def run(self, project_state):
        if self.is_running():
            self.failed.emit("模拟已经在运行。")
            return

        try:
            params = self._build_run_params(project_state)
        except (
            CornerParameterError,
            CaseDataSimulationAdapterError,
            CaseDatasetSimulationAdapterError,
        ) as exc:
            self.failed.emit(str(exc))
            return

        tmp_dir = os.path.join(self.project_root, ".tmp")
        os.makedirs(tmp_dir, exist_ok=True)
        fd, self.result_path = tempfile.mkstemp(
            prefix="workbench_corner_result_", suffix=".json", dir=tmp_dir)
        os.close(fd)
        self._output_buffer = ""

        self.process = QProcess(self)
        self.process.setWorkingDirectory(self.project_root)
        self.process.setProgram(sys.executable)
        self.process.setArguments([
            "-u",
            "-m",
            "front.simulation_runner",
            "--output",
            self.result_path,
            "--params",
            json.dumps(params, ensure_ascii=False),
        ])
        self.process.setProcessChannelMode(QProcess.MergedChannels)
        self.process.readyReadStandardOutput.connect(self._handle_output)
        self.process.finished.connect(self._handle_finished)
        self.process.errorOccurred.connect(self._handle_error)

        self.started.emit(params)
        if params.get("interface_source") == "case_dataset":
            self.log_message.emit("[运行] case_dataset 模拟参数已提交")
        elif params.get("interface_source") == "case_data":
            self.log_message.emit("[运行] CaseData 模拟参数已提交")
        else:
            self.log_message.emit("[运行] Corner Grid LGR 模拟已启动")
        self.process.start()

    def _build_run_params(self, project_state):
        dataset_path = str(getattr(project_state, "case_dataset_path", "") or "").strip()
        dataset_summary = getattr(project_state, "case_dataset_summary", {}) or {}
        if dataset_path:
            if dataset_summary.get("stale"):
                reason = dataset_summary.get("stale_reason") or "CaseData 已修改，请重新生成 Dataset"
                raise CaseDatasetSimulationAdapterError(reason)
            return build_case_dataset_params(dataset_path)

        case_data_path = str(getattr(project_state, "case_data_path", "") or "").strip()
        if case_data_path:
            case_input = build_case_data_simulation_input(case_data_path)
            if not case_input.validation.get("ok", False):
                errors = case_input.validation.get("errors") or []
                raise CaseDataSimulationAdapterError(
                    "CaseData 输入校验未通过: " + "; ".join(errors)
                )
            for warning in case_input.validation.get("warnings") or []:
                self.log_message.emit(f"[CaseData 警告] {warning}")
            return case_input.params
        return build_corner_grid_params(project_state)

    def stop(self):
        if self.is_running():
            self.log_message.emit("[运行] 正在终止模拟")
            self.process.kill()

    def _handle_output(self):
        if self.process is None:
            return
        chunk = bytes(self.process.readAllStandardOutput()).decode(
            "utf-8", errors="replace")
        if not chunk:
            return
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
        self.process = None

        if exit_status != QProcess.NormalExit or exit_code != 0:
            self.failed.emit(f"模拟失败，进程退出码: {exit_code}")
            if process is not None:
                process.deleteLater()
            return

        if not self.result_path or not os.path.exists(self.result_path):
            self.failed.emit("模拟结束，但没有生成结果 JSON。")
            if process is not None:
                process.deleteLater()
            return

        try:
            sim_data = SimulationData()
            sim_data.load_json(self.result_path)
        except Exception as exc:
            self.failed.emit(f"结果 JSON 加载失败: {exc}")
            if process is not None:
                process.deleteLater()
            return

        self.log_message.emit("[运行] 模拟完成")
        self.finished.emit(sim_data, self.result_path)
        if process is not None:
            process.deleteLater()

    def _handle_error(self, process_error):
        if process_error == QProcess.FailedToStart:
            self.failed.emit("模拟进程启动失败。")
