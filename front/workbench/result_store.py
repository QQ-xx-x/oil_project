# -*- coding: utf-8 -*-
"""工作台界面的内存结果登记表。"""

from dataclasses import dataclass, field


@dataclass
class ResultStore:
    project_root: str
    case_id: str = ""
    run_id: str = ""
    dataset_id: str = ""
    output_sim_path: str = ""
    final_field_path: str = ""
    gas_pvt_table_path: str = ""
    result_json_path: str = ""
    run_status: str = "idle"
    load_status: str = "idle"
    load_error: str = ""
    descriptor: object = None
    simulation_data: object = None
    production_data: dict = field(default_factory=dict)
    pvt_data: dict = field(default_factory=dict)

    def clear_run(self):
        self.case_id = ""
        self.run_id = ""
        self.dataset_id = ""
        self.output_sim_path = ""
        self.final_field_path = ""
        self.gas_pvt_table_path = ""
        self.result_json_path = ""
        self.run_status = "idle"
        self.load_status = "idle"
        self.load_error = ""
        self.descriptor = None
        self.simulation_data = None
        self.production_data = {}
        self.pvt_data = {}

    def has_chart(self, key):
        return bool(self.chart_data(key))

    def chart_data(self, key):
        if key == "production_curve":
            return self.production_data
        if key == "pvt_curve":
            return self.pvt_data
        return {}
