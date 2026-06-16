# -*- coding: utf-8 -*-
"""用于发现现有模拟输出的轻量流程运行器。"""

import csv
import os

from .result_store import ResultStore


class WorkbenchWorkflowRunner:
    def __init__(self, project_root):
        self.project_root = project_root

    def collect_parameters(self, project_state):
        return dict(getattr(project_state, "module_values", {}) or {})

    def run_simulation(self, project_state):
        """First integration pass: scan existing outputs instead of launching solvers."""
        parameters = self.collect_parameters(project_state)
        store = self.discover_results()
        messages = [
            f"[运行] 已收集输入参数模块：{len(parameters)} 个",
            "[运行] 当前阶段执行结果扫描，真实求解器后续接入",
        ]
        if store.output_sim_path:
            messages.append(f"[运行] 已识别 {os.path.basename(store.output_sim_path)}")
            if store.production_data:
                messages.append(
                    f"[运行] 已加载生产曲线：{len(store.production_data.get('points', []))} 个点")
        else:
            messages.append("[运行] 未发现 output_sim 结果文件")
        if store.gas_pvt_table_path:
            messages.append(f"[运行] 已识别 {os.path.basename(store.gas_pvt_table_path)}")
        if store.final_field_path:
            messages.append(f"[运行] 已识别 {os.path.basename(store.final_field_path)}")
        messages.append("[运行] 最小结果闭环完成")
        return store, messages

    def discover_results(self):
        store = ResultStore(project_root=self.project_root)
        store.output_sim_path = self._first_existing([
            "output_sim.csv",
            "output_sim_lgr.csv",
            "output_sim_lgr_noWR.csv",
            "output_sim_lgr_WR.csv",
        ])
        store.gas_pvt_table_path = self._first_existing(["gas_pvt_table.csv"])
        store.final_field_path = self._first_existing([
            "final_field.csv",
            "final_field_lgr.csv",
            "final_field_lgr_noWR.csv",
            "final_field_lgr_WR.csv",
        ])
        if store.output_sim_path:
            store.production_data = self._read_xy_chart(
                store.output_sim_path,
                title="生产曲线",
                x_label="时间",
                y_label="产量",
                preferred_x=("time", "days", "day"),
                preferred_y=("cumoil", "oil_rate", "rate", "production", "cumgas"),
            )
        if store.gas_pvt_table_path:
            store.pvt_data = self._read_xy_chart(
                store.gas_pvt_table_path,
                title="PVT 表曲线",
                x_label="压力",
                y_label="Z 因子",
                preferred_x=("p_bar", "pressure", "p"),
                preferred_y=("z", "bg", "mu_g_cp"),
            )
        return store

    def _first_existing(self, names):
        for name in names:
            path = os.path.join(self.project_root, name)
            if os.path.exists(path):
                return path
        return ""

    def _read_xy_chart(self, path, title, x_label, y_label, preferred_x, preferred_y):
        rows = []
        with open(path, "r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            if not reader.fieldnames:
                return {}
            fields = list(reader.fieldnames)
            x_field = self._choose_field(fields, preferred_x) or fields[0]
            y_field = self._choose_field(fields, preferred_y, exclude={x_field})
            if y_field is None:
                y_field = self._first_numeric_field(path, fields, exclude={x_field})
            if y_field is None:
                return {}
            for row in reader:
                x = self._to_float(row.get(x_field))
                y = self._to_float(row.get(y_field))
                if x is not None and y is not None:
                    rows.append((x, y))
        return {
            "title": title,
            "x_label": x_label,
            "y_label": y_label,
            "x_field": x_field,
            "y_field": y_field,
            "points": rows,
            "source": path,
        }

    def _choose_field(self, fields, preferred, exclude=None):
        exclude = exclude or set()
        lookup = {field.lower(): field for field in fields if field not in exclude}
        for name in preferred:
            if name.lower() in lookup:
                return lookup[name.lower()]
        return None

    def _first_numeric_field(self, path, fields, exclude=None):
        exclude = exclude or set()
        with open(path, "r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            for row in reader:
                for field in fields:
                    if field in exclude:
                        continue
                    if self._to_float(row.get(field)) is not None:
                        return field
                break
        return None

    def _to_float(self, value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
