# -*- coding: utf-8 -*-
"""Run-aware result tree for the active case."""

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem

from .case_models import RUN_TYPE_HISTORY_MATCHING, RUN_TYPE_SIMULATION
from .icons import painted_icon
from .result_catalog import (
    RESULT_AVAILABLE,
    RESULT_CORRUPT,
    RESULT_MISSING,
    RESULT_PENDING,
    RunResultCatalog,
)


KEY_ROLE = Qt.UserRole
TYPE_ROLE = Qt.UserRole + 1
VIEW_ROLE = Qt.UserRole + 2
RUN_ROLE = Qt.UserRole + 3
RESULT_KEY_ROLE = Qt.UserRole + 4
AVAILABILITY_ROLE = Qt.UserRole + 5


class ResultsTree(QTreeWidget):
    # Legacy signal retained for integrations that only consume result keys.
    result_selected = pyqtSignal(str, str, str)
    run_selected = pyqtSignal(str)
    run_result_selected = pyqtSignal(str, str, str, str)
    analysis_result_selected = pyqtSignal(str, str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._building = False
        self._case = None
        self._catalog = RunResultCatalog()
        self.setObjectName("resultsTree")
        self.setHeaderHidden(True)
        self.currentItemChanged.connect(self._emit_selection)
        self.bind_case(None)

    def bind_case(self, case_state, preserve_state=None):
        self._case = case_state
        self._catalog = RunResultCatalog.from_case(case_state)
        self._building = True
        try:
            self.clear()
            root = self._item(
                "结果", "results_root", icon_name="result",
                tooltip="当前算例的仿真、历史拟合和分析结果",
            )
            simulation_descriptors = [
                item for item in self._catalog.descriptors
                if item.run_type == RUN_TYPE_SIMULATION
            ]
            history_descriptors = [
                item for item in self._catalog.descriptors
                if item.run_type == RUN_TYPE_HISTORY_MATCHING
            ]
            simulation_runs = self._run_group(
                "仿真运行", "simulation_runs", simulation_descriptors,
                "尚无仿真运行", "runs_empty", "process",
            )
            history_runs = self._run_group(
                "历史拟合运行", "history_matching_runs", history_descriptors,
                "尚无历史拟合运行", "history_runs_empty", "chart",
            )
            root.addChild(simulation_runs)
            root.addChild(history_runs)

            analysis = self._item("算例分析", "case_analysis", icon_name="chart")
            for label, key, icon_name in (
                ("历史拟合", "history_matching", "chart"),
                ("相对渗透率曲线", "relative_permeability_curve", "permeability"),
            ):
                analysis.addChild(self._result_item(
                    label, key, "chart", "", icon_name))
            root.addChild(analysis)
            self.addTopLevelItem(root)
            root.setExpanded(True)
            simulation_runs.setExpanded(True)
            history_runs.setExpanded(True)
            analysis.setExpanded(True)

            if preserve_state:
                self._restore_state(preserve_state)
            elif case_state is not None and case_state.active_run_id:
                item = self._find_run_item(case_state.active_run_id)
                if item is not None:
                    self.setCurrentItem(item)
                    item.setExpanded(True)
        finally:
            self._building = False

    def _run_group(self, label, key, descriptors, empty_label, empty_key, icon):
        group = self._item(
            f"{label} ({len(descriptors)})", key, icon_name=icon)
        for descriptor in descriptors:
            group.addChild(self._build_run_item(descriptor))
        if not descriptors:
            empty = self._item(
                empty_label, empty_key, item_type="status", icon_name="info")
            empty.setDisabled(True)
            group.addChild(empty)
        return group

    def refresh(self):
        self.bind_case(self._case, preserve_state=self.export_ui_state())

    def descriptor(self, run_id):
        return self._catalog.by_run_id(run_id)

    def _build_run_item(self, descriptor):
        status_label = {
            "preparing": "准备中", "running": "运行中", "completed": "已完成",
            "failed": "失败", "cancelled": "已取消", "interrupted": "已中断",
        }.get(descriptor.status, descriptor.status or "未知")
        suffix = f" · {descriptor.display_time}" if descriptor.display_time else ""
        run_kind = (
            "历史拟合" if descriptor.run_type == RUN_TYPE_HISTORY_MATCHING
            else "仿真"
        )
        run_item = self._item(
            f"{descriptor.run_id} · {status_label}{suffix}",
            f"run:{descriptor.run_id}", item_type="run",
            run_id=descriptor.run_id, availability=descriptor.availability,
            icon_name="chart" if descriptor.run_type == RUN_TYPE_HISTORY_MATCHING else "process",
            tooltip=(
                f"Dataset: {descriptor.dataset_id or '-'}\n"
                f"Type: {run_kind}\nModel: {descriptor.model_type}\n"
                f"Status: {descriptor.status}"
            ),
        )
        if descriptor.availability == RESULT_AVAILABLE:
            if descriptor.field_results:
                fields = self._item(
                    "三维网格结果", f"run:{descriptor.run_id}:fields",
                    run_id=descriptor.run_id, icon_name="grid",
                )
                icons = {
                    "pressure_field": "pressure",
                    "water_saturation_field": "saturation",
                    "porosity_field": "porosity",
                    "permeability_x_field": "permeability",
                    "permeability_y_field": "permeability",
                    "permeability_z_field": "permeability",
                }
                for label, key in descriptor.field_results:
                    fields.addChild(self._result_item(
                        label, key, "3d", descriptor.run_id,
                        icons.get(key, "result")))
                run_item.addChild(fields)
            if descriptor.chart_results:
                charts = self._item(
                    "曲线与分析结果", f"run:{descriptor.run_id}:charts",
                    run_id=descriptor.run_id, icon_name="chart",
                )
                for label, key in descriptor.chart_results:
                    charts.addChild(self._result_item(
                        label, key, "chart", descriptor.run_id, "chart"))
                run_item.addChild(charts)
        else:
            message = {
                RESULT_PENDING: "运行尚未结束",
                RESULT_MISSING: "结果文件缺失或为空",
                RESULT_CORRUPT: "结果文件无法解析",
            }.get(descriptor.availability, "本次运行没有可加载结果")
            status_item = self._item(
                message, f"run:{descriptor.run_id}:status", item_type="status",
                run_id=descriptor.run_id, availability=descriptor.availability,
                icon_name="warning" if descriptor.errors else "info",
                tooltip="\n".join(descriptor.errors or descriptor.warnings),
            )
            status_item.setDisabled(True)
            run_item.addChild(status_item)
        return run_item

    def _result_item(self, label, result_key, view, run_id, icon_name):
        composite = (
            f"run:{run_id}:result:{result_key}"
            if run_id else f"analysis:{result_key}"
        )
        return self._item(
            label, composite, item_type="result" if view == "3d" else "chart",
            view=view, run_id=run_id, result_key=result_key,
            availability=RESULT_AVAILABLE, icon_name=icon_name,
        )

    def _item(self, text, key, item_type="folder", view="3d", run_id="",
              result_key="", availability="", icon_name="folder", tooltip=None):
        item = QTreeWidgetItem([text])
        item.setData(0, KEY_ROLE, key)
        item.setData(0, TYPE_ROLE, item_type)
        item.setData(0, VIEW_ROLE, view)
        item.setData(0, RUN_ROLE, run_id)
        item.setData(0, RESULT_KEY_ROLE, result_key)
        item.setData(0, AVAILABILITY_ROLE, availability)
        item.setIcon(0, painted_icon(icon_name, 16))
        if tooltip:
            item.setToolTip(0, tooltip)
        return item

    def _emit_selection(self, current, previous=None):
        if self._building or current is None:
            return
        item_type = current.data(0, TYPE_ROLE) or "folder"
        run_id = current.data(0, RUN_ROLE) or ""
        if item_type == "run" and run_id:
            self.run_selected.emit(run_id)
            return
        result_key = current.data(0, RESULT_KEY_ROLE) or ""
        if not result_key:
            return
        view = current.data(0, VIEW_ROLE) or "3d"
        if run_id:
            self.run_result_selected.emit(
                run_id, result_key, current.text(0), view)
        else:
            self.analysis_result_selected.emit(
                result_key, current.text(0), view)
        self.result_selected.emit(result_key, current.text(0), view)

    def activate_current(self):
        self._emit_selection(self.currentItem())

    def select_run(self, run_id, emit=True):
        item = self._find_run_item(run_id)
        if item is None:
            return False
        changed = self.currentItem() is not item
        self.setCurrentItem(item)
        item.setExpanded(True)
        self.scrollToItem(item)
        if emit and not changed:
            self._emit_selection(item)
        return True

    def select_key(self, key, run_id=None):
        item = self._find_result_item(key, run_id)
        if item is None:
            return False
        changed = self.currentItem() is not item
        self.setCurrentItem(item)
        self.scrollToItem(item)
        parent = item.parent()
        while parent is not None:
            parent.setExpanded(True)
            parent = parent.parent()
        if not changed:
            self._emit_selection(item)
        return True

    def _find_run_item(self, run_id):
        for item in self._iter_items():
            if item.data(0, TYPE_ROLE) == "run" and item.data(0, RUN_ROLE) == run_id:
                return item
        return None

    def _find_result_item(self, result_key, run_id=None):
        preferred_run = run_id
        if preferred_run is None and self._case is not None:
            preferred_run = self._case.active_run_id or None
        fallback = None
        for item in self._iter_items():
            if item.data(0, RESULT_KEY_ROLE) != result_key:
                continue
            item_run = item.data(0, RUN_ROLE) or ""
            if preferred_run is not None and item_run == preferred_run:
                return item
            if fallback is None:
                fallback = item
        return fallback

    def export_ui_state(self):
        expanded_keys = []
        for item in self._iter_items():
            key = item.data(0, KEY_ROLE)
            if key and item.isExpanded():
                expanded_keys.append(key)
        current = self.currentItem()
        return {
            "current_key": current.data(0, KEY_ROLE) if current else None,
            "current_run_id": current.data(0, RUN_ROLE) if current else None,
            "current_result_key": (
                current.data(0, RESULT_KEY_ROLE) if current else None),
            "expanded_keys": expanded_keys,
        }

    def restore_ui_state(self, state):
        self._building = True
        try:
            self._restore_state(state or {})
        finally:
            self._building = False

    def _restore_state(self, state):
        if not isinstance(state, dict):
            return
        expanded = set(state.get("expanded_keys") or [])
        always_expanded = {
            "results_root", "simulation_runs", "history_matching_runs",
            "case_analysis",
        }
        for item in self._iter_items():
            key = item.data(0, KEY_ROLE)
            if key:
                item.setExpanded(key in expanded or key in always_expanded)
        current = None
        current_key = state.get("current_key")
        if current_key:
            current = self._find_item_by_key(current_key)
        if current is None and state.get("current_result_key"):
            current = self._find_result_item(
                state.get("current_result_key"), state.get("current_run_id"))
        if current is None and state.get("current_run_id"):
            current = self._find_run_item(state.get("current_run_id"))
        if current is not None:
            self.setCurrentItem(current)
            self.scrollToItem(current)

    def _find_item_by_key(self, key):
        for item in self._iter_items():
            if item.data(0, KEY_ROLE) == key:
                return item
        return None

    def _iter_items(self):
        for index in range(self.topLevelItemCount()):
            yield from self._iter_item_recursive(self.topLevelItem(index))

    def _iter_item_recursive(self, item):
        yield item
        for index in range(item.childCount()):
            yield from self._iter_item_recursive(item.child(index))


__all__ = [
    "AVAILABILITY_ROLE", "KEY_ROLE", "RESULT_KEY_ROLE", "RUN_ROLE", "ResultsTree",
]
