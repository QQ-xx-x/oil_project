# -*- coding: utf-8 -*-
"""Functional input tree schema for the workbench.

The schema is intentionally declarative: it describes where every known input
belongs in the UI without changing the underlying project_state storage keys.
"""


CASE_SECTIONS = [
    "GRID", "ROCK", "FRACTURE", "LGR", "FLUID", "GAS",
    "INITIAL", "WELL", "SOLVER", "OUTPUT", "WR",
]


def ui_item(module, key, title=None, unit="", note=""):
    return {
        "source": "ui",
        "module": module,
        "key": key,
        "title": title or key,
        "unit": unit,
        "note": note,
    }


def case_item(section, key, title=None, note=""):
    return {
        "source": "case",
        "section": section,
        "key": key,
        "title": title or key,
        "note": note,
    }


def config_item(group, key, title=None, unit="", note=""):
    return {
        "source": "config",
        "group": group,
        "key": key,
        "title": title or key,
        "unit": unit,
        "note": note,
    }


def array_item(key, title=None, note=""):
    return {
        "source": "array",
        "key": key,
        "title": title or key,
        "note": note,
    }


def dfn_item(key, title=None, note=""):
    return {
        "source": "dfn",
        "key": key,
        "title": title or key,
        "note": note,
    }


def validation_item(key, title=None):
    return {
        "source": "validation",
        "key": key,
        "title": title or key,
    }


def result_item(key, title, view="3d", note=""):
    return {
        "key": key,
        "title": title,
        "view": view,
        "note": note,
    }


def group(key, title, items, page="summary", icon="generic"):
    return {
        "key": key,
        "title": title,
        "items": items,
        "page": page,
        "icon": icon,
    }


INPUT_MODULES = [
    {
        "key": "input_overview",
        "title": "输入总览",
        "icon": "case_root",
        "related_results": [
            result_item("result_files", "结果文件", "result"),
            result_item("dynamic_results_data", "动态结果数据", "result"),
        ],
        "children": [
            group("project_sources", "工程输入来源", [
                {"source": "project", "key": "case_data_path", "title": "CaseData 文件"},
                {"source": "project", "key": "case_dataset_path", "title": "case_dataset 目录"},
                validation_item("ok", "Dataset 校验状态"),
                validation_item("errors", "校验错误"),
                validation_item("warnings", "校验警告"),
            ], page="overview", icon="case_root"),
        ],
    },
    {
        "key": "case_data_manifest",
        "title": "CaseData 原始输入",
        "icon": "case_root",
        "special": "case_data",
        "related_results": [
            result_item("result_files", "结果文件", "result"),
            result_item("dynamic_results_data", "动态结果数据", "result"),
        ],
        "children": [
            group("case_sections", "Section / Keyword", [
                {"source": "case_section", "key": section, "title": section}
                for section in CASE_SECTIONS
            ], page="case", icon="case_section"),
        ],
    },
    {
        "key": "grid_spatial",
        "title": "网格与空间数据",
        "icon": "grid",
        "related_results": [
            result_item("layer_grid", "显示网格图层", "layer"),
            result_item("layer_grid_refinement", "显示 LGR 图层", "layer"),
            result_item("pressure_field", "查看压力场", "3d"),
        ],
        "children": [
            group("grid_files", "网格文件", [
                ui_item("grid_basic", "grdecl_file", "GRDECL 文件"),
                ui_item("grid_basic", "coord_file", "COORD CSV"),
                ui_item("grid_basic", "zcorn_file", "ZCORN CSV"),
                case_item("GRID", "grid_file", "CaseData grid_file"),
            ], page="files", icon="grid_file"),
            group("grid_dimensions", "网格尺寸", [
                ui_item("grid_basic", "nx", "Nx"),
                ui_item("grid_basic", "ny", "Ny"),
                ui_item("grid_basic", "nz", "Nz"),
                ui_item("grid_basic", "lx", "Lx", "m"),
                ui_item("grid_basic", "ly", "Ly", "m"),
                ui_item("grid_basic", "lz", "Lz", "m"),
            ], page="parameters", icon="grid"),
            group("corner_grid_arrays", "Corner Grid 数组", [
                array_item("grid_coord", "COORD"),
                array_item("grid_zcorn", "ZCORN"),
                array_item("grid_actnum", "ACTNUM"),
                array_item("mask_active", "Active Mask"),
            ], page="arrays", icon="grid_file"),
            group("lgr_refinement", "LGR 加密", [
                ui_item("grid_basic", "enable_lgr", "启用 LGR"),
                ui_item("grid_basic", "d_threshold", "距离阈值 d_threshold"),
                ui_item("grid_basic", "lgr_nrx", "X 向加密数 lgr_nrx"),
                ui_item("grid_basic", "lgr_nry", "Y 向加密数 lgr_nry"),
                ui_item("grid_basic", "lgr_nrz", "Z 向加密数 lgr_nrz"),
                config_item("lgr", "enable_lgr", "CaseData enable_lgr"),
                config_item("lgr", "d_threshold", "CaseData d_threshold"),
                config_item("lgr", "nrx", "CaseData nrx"),
                config_item("lgr", "nry", "CaseData nry"),
                config_item("lgr", "nrz", "CaseData nrz"),
            ], page="parameters", icon="lgr"),
        ],
    },
    {
        "key": "rock_properties",
        "title": "储层岩石属性",
        "icon": "matrix",
        "related_results": [
            result_item("porosity_field", "查看孔隙度场", "3d"),
            result_item("permeability_x_field", "查看 Kx 渗透率场", "3d"),
            result_item("permeability_y_field", "查看 Ky 渗透率场", "3d"),
            result_item("permeability_z_field", "查看 Kz 渗透率场", "3d"),
        ],
        "children": [
            group("matrix_properties", "基质属性", [
                ui_item("matrix_properties", "porosity", "孔隙度 porosity"),
                ui_item("matrix_properties", "perm_x", "Kx"),
                ui_item("matrix_properties", "perm_y", "Ky"),
                ui_item("matrix_properties", "perm_z", "Kz"),
                case_item("ROCK", "matrix_phi_file", "matrix_phi_file"),
                case_item("ROCK", "matrix_kx_file", "matrix_kx_file"),
                case_item("ROCK", "matrix_ky_file", "matrix_ky_file"),
                case_item("ROCK", "matrix_kz_file", "matrix_kz_file"),
            ], page="parameters", icon="matrix"),
            group("property_arrays", "属性场文件与数组", [
                array_item("matrix_phi", "基质孔隙度 matrix_phi"),
                array_item("matrix_kx", "基质 Kx matrix_kx"),
                array_item("matrix_ky", "基质 Ky matrix_ky"),
                array_item("matrix_kz", "基质 Kz matrix_kz"),
                array_item("actnum_property", "属性 ACTNUM"),
            ], page="arrays", icon="matrix_property_file"),
            group("fracture_equivalent_properties", "裂缝等效属性", [
                case_item("FRACTURE", "fracture_phi_file", "fracture_phi_file"),
                case_item("FRACTURE", "fracture_kx_file", "fracture_kx_file"),
                case_item("FRACTURE", "fracture_ky_file", "fracture_ky_file"),
                case_item("FRACTURE", "fracture_kz_file", "fracture_kz_file"),
                case_item("WR", "sigma_file", "sigma_file"),
                array_item("fracture_phi", "裂缝孔隙度 fracture_phi"),
                array_item("fracture_kx", "裂缝 Kx fracture_kx"),
                array_item("fracture_ky", "裂缝 Ky fracture_ky"),
                array_item("fracture_kz", "裂缝 Kz fracture_kz"),
                array_item("sigma", "形状因子 sigma"),
            ], page="arrays", icon="fracture_property_file"),
            group("dual_porosity", "双重介质 / WR", [
                ui_item("dual_porosity", "enable_dual_porosity", "启用双重介质"),
                ui_item("dual_porosity", "phi_fracture", "裂缝孔隙度 phi_fracture"),
                ui_item("dual_porosity", "k_fracture_x", "裂缝 Kx"),
                ui_item("dual_porosity", "k_fracture_y", "裂缝 Ky"),
                ui_item("dual_porosity", "k_fracture_z", "裂缝 Kz"),
                ui_item("dual_porosity", "matrix_volume_fraction", "基质体积分数"),
                ui_item("dual_porosity", "fracture_volume_fraction", "裂缝体积分数"),
                ui_item("dual_porosity", "wr_shape_factor", "WR 形状因子"),
            ], page="parameters", icon="dual_porosity"),
        ],
    },
    {
        "key": "fluid_pvt_inputs",
        "title": "流体与 PVT",
        "icon": "fluid",
        "related_results": [
            result_item("water_saturation_field", "查看含水饱和度场", "3d"),
            result_item("relative_permeability_curve", "打开相对渗透率曲线", "chart"),
            result_item("pvt_curve", "打开 PVT 曲线", "chart"),
        ],
        "children": [
            group("oil_water_properties", "油水基础参数", [
                ui_item("oil_water_properties", "mu_w", "水相黏度 mu_w"),
                ui_item("oil_water_properties", "mu_o", "油相黏度 mu_o"),
                ui_item("oil_water_properties", "mu_g", "气相黏度 mu_g"),
                ui_item("oil_water_properties", "cw", "水相压缩系数 cw"),
                ui_item("oil_water_properties", "co", "油相压缩系数 co"),
                ui_item("oil_water_properties", "cg", "气相压缩系数 cg"),
                ui_item("oil_water_properties", "p_ref", "参考压力 p_ref"),
                ui_item("oil_water_properties", "swi", "束缚水 Swi"),
                ui_item("oil_water_properties", "sor", "残余油 Sor"),
                ui_item("oil_water_properties", "sgc", "临界气 Sgc"),
                config_item("fluid", "n", "相渗指数 n"),
            ], page="parameters", icon="oil_water"),
            group("gas_properties", "气体参数", [
                ui_item("gas_pvt", "gas_t_C", "地层温度 gas_t_C"),
                ui_item("gas_pvt", "gas_Mg", "摩尔质量 gas_Mg"),
                ui_item("gas_pvt", "gas_Tc", "临界温度 gas_Tc"),
                ui_item("gas_pvt", "gas_Pc_bar", "临界压力 gas_Pc_bar"),
                config_item("gas", "temperature_c", "CaseData temperature_C"),
                config_item("gas", "mole_CH4", "CH4 摩尔分数"),
                config_item("gas", "mole_C2H6", "C2H6 摩尔分数"),
                config_item("gas", "mole_C3H8", "C3H8 摩尔分数"),
                config_item("gas", "mole_N2", "N2 摩尔分数"),
                config_item("gas", "mole_CO2", "CO2 摩尔分数"),
                config_item("gas", "mole_H2O", "H2O 摩尔分数"),
                config_item("gas", "mole_unknown", "unknown 摩尔分数"),
            ], page="parameters", icon="gas"),
            group("pvt_table", "PVT 表", [
                ui_item("gas_pvt", "gas_table_Pmin_bar", "Pmin"),
                ui_item("gas_pvt", "gas_table_Pmax_bar", "Pmax"),
                ui_item("gas_pvt", "gas_table_n", "采样点数"),
                config_item("gas", "gas_table_pmin_bar", "CaseData Pmin"),
                config_item("gas", "gas_table_pmax_bar", "CaseData Pmax"),
                config_item("gas", "gas_table_n", "CaseData table_n"),
            ], page="parameters", icon="gas"),
        ],
    },
    {
        "key": "initial_conditions",
        "title": "初始状态",
        "icon": "initial",
        "related_results": [
            result_item("pressure_field", "查看压力场", "3d"),
            result_item("water_saturation_field", "查看含水饱和度场", "3d"),
        ],
        "children": [
            group("initial_pressure", "压力条件", [
                ui_item("initial_state", "initial_pressure", "初始压力"),
                config_item("initial", "pressure", "CaseData pressure"),
            ], page="parameters", icon="initial"),
            group("initial_saturation", "饱和度条件", [
                ui_item("initial_state", "initial_sw", "初始含水饱和度 Sw"),
                ui_item("initial_state", "initial_sg", "初始含气饱和度 Sg"),
                config_item("initial", "sw", "CaseData Sw"),
                config_item("initial", "sg", "CaseData Sg"),
                config_item("initial", "so", "计算油相饱和度 So"),
            ], page="parameters", icon="initial"),
        ],
    },
    {
        "key": "well_production",
        "title": "井与生产控制",
        "icon": "well",
        "related_results": [
            result_item("layer_well", "显示井轨迹图层", "layer"),
            result_item("production_curve", "打开生产曲线", "chart"),
            result_item("blasingame_curve", "打开 Blasingame 曲线", "chart"),
        ],
        "children": [
            group("well_location", "井位置", [
                ui_item("well_parameters", "x", "X 坐标"),
                ui_item("well_parameters", "y", "Y 坐标"),
                ui_item("well_parameters", "z", "Z 坐标"),
            ], page="parameters", icon="well"),
            group("well_control", "井控制", [
                ui_item("well_parameters", "pressure", "井底压力"),
                ui_item("well_parameters", "radius", "井半径"),
                ui_item("well_parameters", "WI", "井指数"),
                config_item("well", "producer_bhp", "CaseData producer_bhp"),
                config_item("well", "well_radius", "CaseData well_radius"),
            ], page="parameters", icon="well"),
        ],
    },
    {
        "key": "fracture_system_inputs",
        "title": "裂缝系统",
        "icon": "fracture",
        "related_results": [
            result_item("layer_natural_fractures", "显示天然裂缝图层", "layer"),
            result_item("layer_hydraulic_fractures", "显示人工裂缝图层", "layer"),
            result_item("blasingame_curve", "打开 Blasingame 曲线", "chart"),
        ],
        "children": [
            group("natural_fractures", "天然裂缝", [
                dfn_item("fracture_count", "DFN 裂缝数"),
                dfn_item("node_count", "DFN 节点数"),
                dfn_item("property_count", "DFN 属性数"),
                dfn_item("set_count", "DFN 裂缝集合数"),
                dfn_item("parsed_fractures", "已解析裂缝数"),
                dfn_item("bbox_min", "包围盒最小点"),
                dfn_item("bbox_max", "包围盒最大点"),
            ], page="dfn", icon="fracture"),
            group("hydraulic_fractures", "人工裂缝", [
                ui_item("hydraulic_fractures", "num_stages", "压裂段数"),
                ui_item("hydraulic_fractures", "spacing_x", "裂缝间距"),
                ui_item("hydraulic_fractures", "length", "裂缝总长度"),
                ui_item("hydraulic_fractures", "height", "缝高"),
                ui_item("hydraulic_fractures", "aperture", "开度"),
                ui_item("hydraulic_fractures", "perm", "渗透率"),
                ui_item("hydraulic_fractures", "conductivity", "导流能力"),
            ], page="parameters", icon="fracture"),
            group("dfn_file", "DFN 文件", [
                case_item("FRACTURE", "fracture_file", "fracture_file"),
            ], page="files", icon="dfn_file"),
            group("dfn_data", "DFN 数据", [
                dfn_item("fracture_count", "裂缝数"),
                dfn_item("node_count", "节点数"),
                dfn_item("property_count", "属性数"),
                dfn_item("properties", "属性定义"),
                dfn_item("sets", "裂缝集合"),
                dfn_item("fractures", "裂缝表"),
                dfn_item("bbox_min", "包围盒最小点"),
                dfn_item("bbox_max", "包围盒最大点"),
            ], page="dfn", icon="dfn_file"),
        ],
    },
    {
        "key": "solver_output",
        "title": "求解与输出控制",
        "icon": "solver",
        "related_results": [
            result_item("dynamic_results_data", "动态结果数据", "result"),
            result_item("pressure_field", "查看压力场", "3d"),
            result_item("water_saturation_field", "查看含水饱和度场", "3d"),
        ],
        "children": [
            group("time_control", "时间控制", [
                ui_item("simulation_control", "simulation_time", "模拟时间"),
                ui_item("simulation_control", "time_step", "时间步长"),
                config_item("solver", "total_time", "CaseData total_time"),
                config_item("solver", "dt_init", "CaseData dt_init"),
                config_item("solver", "dt_min", "CaseData dt_min"),
                config_item("solver", "dt_max", "CaseData dt_max"),
            ], page="parameters", icon="solver"),
            group("nonlinear_solver", "非线性求解", [
                config_item("solver", "newton_max_iter", "newton_max_iter"),
                config_item("solver", "newton_tol", "newton_tol"),
            ], page="parameters", icon="solver"),
            group("linear_solver", "线性求解", [
                config_item("solver", "linear_tol", "linear_tol"),
                config_item("solver", "linear_max_iter", "linear_max_iter"),
            ], page="parameters", icon="solver"),
            group("timestep_control", "时间步调整", [
                config_item("solver", "dt_cut_factor", "dt_cut_factor"),
                config_item("solver", "dt_grow_factor", "dt_grow_factor"),
                config_item("solver", "max_timestep_retry", "max_timestep_retry"),
            ], page="parameters", icon="solver"),
            group("output_control", "输出控制", [
                case_item("OUTPUT", "output_prefix", "OUTPUT section"),
            ], page="case", icon="output"),
        ],
    },
]


def module_by_key(module_key):
    for module in INPUT_MODULES:
        if module["key"] == module_key:
            return module
    return None


def child_by_key(module_key, child_key):
    module = module_by_key(module_key)
    if not module:
        return None
    for child in module.get("children", []):
        if child["key"] == child_key:
            return child
    return None


def iter_schema_nodes():
    for module in INPUT_MODULES:
        yield module, None, None
        for child in module.get("children", []):
            yield module, child, None
            for item in child.get("items", []):
                yield module, child, item
