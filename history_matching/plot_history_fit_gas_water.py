import csv
import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


OUTPUT_DIR = Path(__file__).resolve().parent
DEFAULT_HISTORY_FILE = OUTPUT_DIR / "history_fit_target.csv"
DEFAULT_FIT_FILE = OUTPUT_DIR / "results_fit_target" / "best_fit_output.csv"
DEFAULT_OUT_FILE = OUTPUT_DIR / "results_fit_target" / "history_fit_gas_water.png"


def read_history(history_file):
    rows = []
    with Path(history_file).open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(
                {
                    "day": float(row["day"]),
                    "water_rate": float(row["water_rate_sm3_d"]),
                    "gas_rate": float(row["gas_rate_sm3_d"]),
                    "water_cum": float(row["water_cum_sm3"]),
                    "gas_cum": float(row["gas_cum_sm3"]),
                }
            )
    return rows


def read_fit(fit_file):
    rows = [{"day": 0.0, "water_rate": 0.0, "gas_rate": 0.0, "water_cum": 0.0, "gas_cum": 0.0}]
    with Path(fit_file).open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(
                {
                    "day": float(row["Time"]),
                    "water_rate": max(0.0, float(row["Qw"])),
                    "gas_rate": max(0.0, float(row["Qg"])),
                    "water_cum": float(row["CumWater"]),
                    "gas_cum": float(row["CumGas"]),
                }
            )
    return rows


def series(rows, key):
    return [row[key] for row in rows]


def interp_series(rows, day, key):
    if day <= rows[0]["day"]:
        return rows[0][key]
    for left, right in zip(rows[:-1], rows[1:]):
        if left["day"] <= day <= right["day"]:
            span = max(right["day"] - left["day"], 1e-12)
            frac = (day - left["day"]) / span
            return left[key] + frac * (right[key] - left[key])
    return rows[-1][key]


def resample_fit_to_history_days(fit, history):
    days = series(history, "day")
    return [
        {
            "day": day,
            "water_rate": interp_series(fit, day, "water_rate"),
            "gas_rate": interp_series(fit, day, "gas_rate"),
            "water_cum": interp_series(fit, day, "water_cum"),
            "gas_cum": interp_series(fit, day, "gas_cum"),
        }
        for day in days
    ]


def plot_panel(ax, history, fit, phase_name, rate_key, cum_key, color):
    ax_rate = ax.twinx()

    ax.scatter(
        series(history, "day"),
        series(history, cum_key),
        s=16,
        facecolors="none",
        edgecolors=color,
        linewidths=0.75,
        alpha=0.88,
        label=f"Observed, {phase_name} production cumulative",
    )
    ax_rate.scatter(
        series(history, "day"),
        series(history, rate_key),
        s=8,
        color=color,
        alpha=0.50,
        label=f"Observed, {phase_name} production rate",
    )
    ax.plot(
        series(fit, "day"),
        series(fit, cum_key),
        color=color,
        linestyle="--",
        linewidth=1.6,
        label=f"EnKF fit, {phase_name} production cumulative",
    )
    ax_rate.plot(
        series(fit, "day"),
        series(fit, rate_key),
        color="#222222",
        linewidth=1.1,
        alpha=0.85,
        label=f"EnKF fit, {phase_name} production rate",
    )

    ax.set_title(f"{phase_name} Production History Match")
    ax.set_xlabel("Production day [d]")
    ax.set_ylabel(f"{phase_name} production cumulative [sm3]")
    ax_rate.set_ylabel(f"{phase_name} production rate [sm3/d]")
    ax.set_xlim(0.0, max(series(history, "day")))
    ax.grid(True, color="#d7d7d7", linewidth=0.6, alpha=0.85)
    ax.set_axisbelow(True)

    left_handles, left_labels = ax.get_legend_handles_labels()
    right_handles, right_labels = ax_rate.get_legend_handles_labels()
    ax.legend(
        left_handles + right_handles,
        left_labels + right_labels,
        loc="upper center",
        fontsize=8,
        frameon=True,
    )


def main():
    parser = argparse.ArgumentParser(description="Plot observed history target and EnKF fit curves.")
    parser.add_argument("--history", default=str(DEFAULT_HISTORY_FILE))
    parser.add_argument("--fit", default=str(DEFAULT_FIT_FILE))
    parser.add_argument("--output", default=str(DEFAULT_OUT_FILE))
    args = parser.parse_args()

    fit_file = Path(args.fit)
    out_file = Path(args.output)
    if not fit_file.exists():
        raise FileNotFoundError(f"Best fit output does not exist yet: {fit_file}")
    history = read_history(args.history)
    fit = resample_fit_to_history_days(read_fit(fit_file), history)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    fig, (ax_gas, ax_water) = plt.subplots(1, 2, figsize=(15, 5.6), constrained_layout=True)
    plot_panel(ax_gas, history, fit, "Gas", "gas_rate", "gas_cum", "#1f77b4")
    plot_panel(ax_water, history, fit, "Water", "water_rate", "water_cum", "#2ca02c")
    fig.savefig(out_file, dpi=180)
    print(f"plot={out_file}")


if __name__ == "__main__":
    main()
