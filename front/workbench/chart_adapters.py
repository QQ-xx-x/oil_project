# -*- coding: utf-8 -*-
"""将工程输入状态转换为图表数据的适配器。"""

import math

from ..pvt_plot import compute_gas_water_section


GAS_DEVIATION_COEFFS = (
    0.3265, -1.07, -0.5339, 0.01569, -0.05165,
    0.5475, -0.7361, 0.1844, 0.1056, 0.6134, 0.7210,
)

GAS_VISCOSITY_COEFFS = (
    -2.46211820, 2.97054714, -0.286264054, 8.05420522e-3,
    2.80860949, -3.49803305, 0.360373020, -0.0104432413,
    -0.793385684, 1.39643306, -0.149144925, 4.41015512e-3,
    0.0839387178, -0.186408848, 0.0203367881, -6.09579263e-4,
)

GAS_COMPONENTS = (
    ("mole_ch4", "mole_CH4", 190.58, 45.44, 16.04, 0.4),
    ("mole_c2h6", "mole_C2H6", 305.42, 48.16, 30.07, 0.1),
    ("mole_c3h8", "mole_C3H8", 369.82, 41.94, 44.10, 0.1),
    ("mole_n2", "mole_N2", 125.97, 33.49, 28.10, 0.1),
    ("mole_co2", "mole_CO2", 304.25, 72.90, 44.00, 0.1),
    ("mole_h2o", "mole_H2O", 647.00, 218.30, 18.02, 0.1),
    ("mole_unknown", "mole_unknown", 350.00, 50.00, 35.00, 0.1),
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
    """根据流体模块业务值构建气体 PVT 曲线和 PVDG 预览表。"""

    params = params or {}
    gas_t_c = _float(
        params.get("temperature_c", params.get("gas_t_C", 140.0)),
        "temperature_c")
    gas_tc, gas_pc_bar, gas_mg = _gas_mixture_pseudo_props(params)
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
    standard_pressure = _float(
        params.get("gas_Psc_bar", 1.01325), "gas_Psc_bar")
    if standard_pressure <= 0.0:
        raise ValueError("气体标准压力 Psc 必须大于 0")

    points = []
    pvdg_rows = []
    for pressure in pressure_values:
        z_factor = _gas_z_factor(
            pressure, gas_t_k, gas_tc, gas_pc_bar)
        bg = _gas_formation_volume_factor(
            pressure, z_factor, gas_t_k, standard_pressure)
        viscosity = _gas_viscosity(
            pressure, gas_t_k, gas_tc, gas_pc_bar, gas_mg)
        points.append((pressure, z_factor))
        pvdg_rows.append((pressure, bg, viscosity))

    return {
        "title": "PVT 表曲线",
        "x_label": "压力 P (bar)",
        "y_label": "气体偏差因子 Z",
        "x_field": "P_bar",
        "y_field": "Z",
        "points": points,
        "pvdg_rows": pvdg_rows,
        "source": "当前输入参数",
        "metadata": {
            "gas_t_C": gas_t_c,
            "gas_Mg": gas_mg,
            "gas_Tc": gas_tc,
            "gas_Pc_bar": gas_pc_bar,
            "gas_Psc_bar": standard_pressure,
            "gas_table_n": requested_n,
        },
    }


def _gas_mixture_pseudo_props(params):
    fractions = []
    for normalized_key, source_key, _tc, _pc, _mw, default in GAS_COMPONENTS:
        raw_value = params.get(normalized_key, params.get(source_key, default))
        fraction = _float(raw_value, normalized_key)
        if fraction < 0.0:
            raise ValueError("气体组分摩尔分数不能小于 0")
        fractions.append(fraction)

    total = sum(fractions)
    if not math.isclose(total, 1.0, rel_tol=0.0, abs_tol=1e-8):
        raise ValueError(f"气体组分摩尔分数之和必须为 1，当前为 {total:.10g}")

    pseudo_tc = sum(
        fraction * component[2]
        for fraction, component in zip(fractions, GAS_COMPONENTS)
    )
    pseudo_pc = sum(
        fraction * component[3]
        for fraction, component in zip(fractions, GAS_COMPONENTS)
    )
    mixture_mw = sum(
        fraction * component[4]
        for fraction, component in zip(fractions, GAS_COMPONENTS)
    )
    if min(pseudo_tc, pseudo_pc, mixture_mw) <= 0.0:
        raise ValueError("气体混合物拟临界参数无效")
    return pseudo_tc, pseudo_pc, mixture_mw


def _gas_formation_volume_factor(
        pressure_bar, z_factor, gas_t_k, standard_pressure_bar):
    pressure = max(float(pressure_bar), 1e-12)
    value = (
        max(float(z_factor), 1e-12)
        * (float(gas_t_k) / 293.15)
        * (float(standard_pressure_bar) / pressure)
    )
    return value if math.isfinite(value) and value > 0.0 else 1e-12


def _gas_viscosity(
        pressure_bar, gas_t_k, pseudo_tc_k, pseudo_pc_bar, mixture_mw):
    coefficients = GAS_VISCOSITY_COEFFS
    pressure = max(float(pressure_bar), 1e-12)
    relative_density = float(mixture_mw) / 28.97
    reduced_temperature = float(gas_t_k) / float(pseudo_tc_k)
    reduced_pressure = pressure / float(pseudo_pc_bar)

    base_viscosity = (
        (1.709e-5 - 2.062e-6 * relative_density)
        * (1.8 * float(gas_t_k) + 32.0)
        + 8.118e-3
        - 6.15e-3 * math.log10(relative_density)
    )
    p = reduced_pressure
    t = reduced_temperature
    exponent = (
        coefficients[0] + coefficients[1] * p
        + coefficients[2] * p ** 2 + coefficients[3] * p ** 3
        + t * (coefficients[4] + coefficients[5] * p
               + coefficients[6] * p ** 2 + coefficients[7] * p ** 3)
        + t ** 2 * (coefficients[8] + coefficients[9] * p
                    + coefficients[10] * p ** 2
                    + coefficients[11] * p ** 3)
        + t ** 3 * (coefficients[12] + coefficients[13] * p
                    + coefficients[14] * p ** 2
                    + coefficients[15] * p ** 3)
    )
    value = base_viscosity * math.exp(exponent) / reduced_temperature
    return value if math.isfinite(value) and value > 0.0 else 0.2


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
