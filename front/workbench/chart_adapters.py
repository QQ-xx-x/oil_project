# -*- coding: utf-8 -*-
"""将工程输入状态转换为图表数据的适配器。"""

import math

from ..pvt_plot import compute_gas_water_section


GAS_DEVIATION_COEFFS = (
    0.3265, -1.07, -0.5339, 0.01569, -0.05165,
    0.5475, -0.7361, 0.1844, 0.1056, 0.6134, 0.7210,
)


def build_relative_permeability_data(project_state):
    initial_state = project_state.get_module_values("initial_state")
    fluid = project_state.get_module_values("oil_water_properties")

    sw = initial_state.get("initial_sw", 0.05)
    sg = initial_state.get("initial_sg", 0.9)
    swi = fluid.get("swi", 0.05)
    sor = fluid.get("sor", 0.01)
    sgc = fluid.get("sgc", 0.05)

    curves = compute_gas_water_section(sw, sg, swi, sor, sgc)
    sw_values = curves["sw_values"]
    krw = curves["krw"]
    krg = curves["krg"]

    return {
        "title": "相对渗透率曲线",
        "x_label": "含水饱和度 Sw",
        "y_label": "相对渗透率 kr",
        "x_field": "Sw",
        "y_field": "kr",
        "so_fixed": curves["so_fixed"],
        "series": [
            {
                "name": "krw",
                "color": "#23a65a",
                "points": list(zip(sw_values.tolist(), krw.tolist())),
            },
            {
                "name": "krg",
                "color": "#d45500",
                "points": list(zip(sw_values.tolist(), krg.tolist())),
            },
        ],
    }


def build_gas_pvt_curve_data(project_state):
    """根据当前工作台输入构建气体 PVT 偏差因子曲线。"""
    params = project_state.get_module_values("gas_pvt")
    return build_gas_pvt_curve_from_values(params)


def build_gas_pvt_curve_from_values(params):
    """根据流体模块业务值构建气体 PVT 偏差因子曲线。"""

    params = params or {}
    gas_t_c = _float(
        params.get("temperature_c", params.get("gas_t_C", 140.0)),
        "temperature_c")
    gas_mg = _float(params.get("gas_Mg", 16.04), "gas_Mg")
    gas_tc = _float(params.get("gas_Tc", 190.58), "gas_Tc")
    gas_pc_bar = _float(params.get("gas_Pc_bar", 45.44), "gas_Pc_bar")
    p_min = _float(
        params.get("gas_table_pmin_bar", params.get("gas_table_Pmin_bar", 1.0)),
        "gas_table_pmin_bar")
    p_max = _float(
        params.get("gas_table_pmax_bar", params.get("gas_table_Pmax_bar", 1000.0)),
        "gas_table_pmax_bar")
    requested_n = int(params.get("gas_table_n", 2000))

    gas_t_k = gas_t_c + 273.15
    if gas_t_k <= 0.0:
        raise ValueError("气体温度换算到 K 后必须大于 0")
    if gas_mg <= 0.0:
        raise ValueError("气体摩尔质量 Mg 必须大于 0")
    if gas_tc <= 0.0:
        raise ValueError("临界温度 Tc 必须大于 0")
    if gas_pc_bar <= 0.0:
        raise ValueError("临界压力 Pc 必须大于 0")
    if not (p_min > 0.0 and p_max > p_min):
        raise ValueError("PVT 表压力范围必须满足 0 < Pmin < Pmax")
    if requested_n < 2:
        raise ValueError("PVT 表采样点数 n 必须至少为 2")

    n_points = min(requested_n, 2000)
    pressure_values = [
        p_min + (p_max - p_min) * index / (n_points - 1)
        for index in range(n_points)
    ]
    points = [
        (pressure, _gas_z_factor(pressure, gas_t_k, gas_tc, gas_pc_bar))
        for pressure in pressure_values
    ]

    return {
        "title": "PVT 表曲线",
        "x_label": "压力 P (bar)",
        "y_label": "气体偏差因子 Z",
        "x_field": "P_bar",
        "y_field": "Z",
        "points": points,
        "source": "当前输入参数",
        "metadata": {
            "gas_t_C": gas_t_c,
            "gas_Mg": gas_mg,
            "gas_Tc": gas_tc,
            "gas_Pc_bar": gas_pc_bar,
            "gas_table_n": requested_n,
        },
    }


def _float(value, name):
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} 必须是数字") from exc
    if not math.isfinite(result):
        raise ValueError(f"{name} 必须是有限数字")
    return result


def _gas_z_factor(p_bar, gas_t_k, gas_tc_k, gas_pc_bar):
    """用于界面绘图的 Dranchuk-Abou-Kassem 风格偏差因子计算。"""
    a = GAS_DEVIATION_COEFFS
    tr = gas_t_k / gas_tc_k
    pr = max(p_bar, 1e-12) / gas_pc_bar
    rho_r = max(1e-12, 0.27 * pr / tr)

    for _ in range(100):
        term2 = a[0] + a[1] / tr + a[2] / tr ** 3 + a[3] / tr ** 4 + a[4] / tr ** 5
        term3 = a[5] + a[6] / tr + a[7] / (tr * tr)
        exp_term = math.exp(-a[10] * rho_r * rho_r)

        f_value = (
            -0.27 * pr / tr
            + rho_r
            + term2 * rho_r * rho_r
            + term3 * rho_r ** 3
            - a[8] * (a[6] / tr + a[7] / (tr * tr)) * rho_r ** 6
            + a[9] * (1.0 + a[10] * rho_r * rho_r)
            * (rho_r ** 3 / tr ** 3)
            * exp_term
        )
        derivative = (
            1.0
            + 2.0 * term2 * rho_r
            + 3.0 * term3 * rho_r * rho_r
            - 6.0 * a[8] * (a[6] / tr + a[7] / (tr * tr)) * rho_r ** 5
            + (a[9] / tr ** 3)
            * (
                3.0 * rho_r * rho_r
                + a[10] * (3.0 * rho_r ** 4 - 2.0 * a[10] * rho_r ** 6)
            )
            * exp_term
        )
        if not math.isfinite(f_value) or not math.isfinite(derivative) or abs(derivative) < 1e-14:
            break
        rho_r = max(1e-12, rho_r - f_value / derivative)
        if abs(f_value) < 1e-10:
            break

    z_factor = 0.27 * pr / max(rho_r * tr, 1e-12)
    if not math.isfinite(z_factor) or z_factor <= 0.0:
        return 1.0
    return z_factor
