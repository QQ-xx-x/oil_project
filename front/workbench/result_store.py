# -*- coding: utf-8 -*-
"""工作台界面的内存结果登记表。"""

from dataclasses import dataclass, field


@dataclass
class ResultStore:
    project_root: str
    output_sim_path: str = ""
    final_field_path: str = ""
    gas_pvt_table_path: str = ""
    result_json_path: str = ""
    run_status: str = "idle"
    simulation_data: object = None
    production_data: dict = field(default_factory=dict)
    pvt_data: dict = field(default_factory=dict)

    def has_chart(self, key):
        return bool(self.chart_data(key))

    def chart_data(self, key):
        if key == "production_curve":
            return self.production_data
        if key == "pvt_curve":
            return self.pvt_data
        return {}
