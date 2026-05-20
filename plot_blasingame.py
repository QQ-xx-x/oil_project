import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS"]
plt.rcParams["axes.unicode_minus"] = False


pvt = pd.read_csv("gas_pvt_table.csv")

P = pvt["P_bar"].values
Z = pvt["Z"].values
mu = pvt["mu_g_cp"].values
cg = pvt["Cg_1_per_bar"].values

integrand = 2.0 * P / (mu * Z)
m = np.zeros_like(P)
m[1:] = np.cumsum(0.5 * (integrand[1:] + integrand[:-1]) * np.diff(P))


def interp_m(p):
    return np.interp(p, P, m)


def interp_mu(p):
    return np.interp(p, P, mu)


def interp_cg(p):
    return np.interp(p, P, cg)


def build_blasingame_series(filename):
    prod = pd.read_csv(filename)
    time = prod["Time"].values
    qg = prod["Qg"].values
    avg_pressure = prod["AvgPressure"].values

    mask = (time > 0) & (qg > 0) & (avg_pressure > 0)
    time = time[mask]
    qg = qg[mask]
    avg_pressure = avg_pressure[mask]

    mu_avg = interp_mu(avg_pressure)
    cg_avg = interp_cg(avg_pressure)
    pseudotime_factor = (mu_i * cg_i) / (mu_avg * cg_avg)

    pseudo_cumulative = np.empty_like(qg)
    pseudo_cumulative[0] = qg[0] * pseudotime_factor[0] * time[0]
    pseudo_cumulative[1:] = pseudo_cumulative[0] + np.cumsum(
        0.5
        * (
            qg[1:] * pseudotime_factor[1:]
            + qg[:-1] * pseudotime_factor[:-1]
        )
        * np.diff(time)
    )
    tca = pseudo_cumulative / qg
    y1 = qg / dm

    # Start from t=0 so the first integral point matches the first rate point.
    y1_integral_area = np.empty_like(y1)
    y1_integral_area[0] = y1[0] * tca[0]
    y1_integral_area[1:] = y1_integral_area[0] + np.cumsum(
        0.5 * (y1[1:] + y1[:-1]) * np.diff(tca)
    )
    y2 = y1_integral_area / tca
    y1_derivative = -np.gradient(y1, np.log(tca))
    y2_derivative = -np.gradient(y2, np.log(tca))
    return tca, y1, y2, y1_derivative, y2_derivative


Pi = 800.0
Pwf = 50.0
dm = interp_m(Pi) - interp_m(Pwf)
mu_i = interp_mu(Pi)
cg_i = interp_cg(Pi)

series = {
    "WR": build_blasingame_series("output_sim_lgr_WR.csv"),
    "noWR": build_blasingame_series("output_sim_lgr_noWR.csv"),
}

plt.figure()
for label, (tca, y1, _, _, _) in series.items():
    plt.loglog(tca, y1, "o-", ms=3, label=label)
plt.xlabel("物质平衡拟时间（天）")
plt.ylabel("归一化产气量，qg / Delta m")
plt.grid(True, which="both")
plt.legend()

plt.figure()
for label, (tca, _, y2, _, _) in series.items():
    plt.loglog(tca, y2, "o-", ms=3, label=label)
plt.xlabel("物质平衡拟时间（天）")
plt.ylabel("归一化产气量积分")
plt.grid(True, which="both")
plt.legend()

plt.figure()
for label, (tca, _, _, y1_derivative, _) in series.items():
    derivative_mask = y1_derivative > 0
    plt.loglog(
        tca[derivative_mask],
        y1_derivative[derivative_mask],
        "o-",
        ms=3,
        label=label,
    )
plt.xlabel("物质平衡拟时间（天）")
plt.ylabel("归一化产气量导数，-d(qg / Delta m) / dln(t)")
plt.grid(True, which="both")
plt.legend()

plt.figure()
for label, (tca, _, _, _, y2_derivative) in series.items():
    derivative_mask = y2_derivative > 0
    plt.loglog(
        tca[derivative_mask],
        y2_derivative[derivative_mask],
        "o-",
        ms=3,
        label=label,
    )
plt.xlabel("物质平衡拟时间（天）")
plt.ylabel("归一化产气量积分导数，-d(积分) / dln(t)")
plt.grid(True, which="both")
plt.legend()

plt.show()
