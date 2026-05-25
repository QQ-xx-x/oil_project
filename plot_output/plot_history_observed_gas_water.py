import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = Path(__file__).resolve().parent
DEFAULT_HISTORY_FILE = OUTPUT_DIR / "history_fit_target.csv"
DEFAULT_OUT_FILE = OUTPUT_DIR / "history_fit_target_gas_water.png"


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
                    "status": row.get("status", ""),
                }
            )
    return rows


def series(rows, key):
    return [row[key] for row in rows]


def plot_production_panel(ax, rows, phase_name, rate_key, cum_key, color):
    ax_rate = ax.twinx()

    ax.scatter(
        series(rows, "day"),
        series(rows, cum_key),
        s=18,
        facecolors="none",
        edgecolors=color,
        linewidths=0.8,
        alpha=0.9,
        label=f"Fit target, {phase_name} production cumulative",
    )
    ax_rate.scatter(
        series(rows, "day"),
        series(rows, rate_key),
        s=9,
        color=color,
        alpha=0.55,
        label=f"Fit target, {phase_name} production rate",
    )

    ax.set_title(f"History Fit Target {phase_name} Production")
    ax.set_xlabel("Production day [d]")
    ax.set_ylabel(f"{phase_name} production cumulative [sm3]")
    ax_rate.set_ylabel(f"{phase_name} production rate [sm3/d]")
    ax.set_xlim(min(series(rows, "day")), max(series(rows, "day")))
    ax.grid(True, color="#d7d7d7", linewidth=0.6, alpha=0.85)
    ax.set_axisbelow(True)

    left_handles, left_labels = ax.get_legend_handles_labels()
    right_handles, right_labels = ax_rate.get_legend_handles_labels()
    ax.legend(
        left_handles + right_handles,
        left_labels + right_labels,
        loc="upper center",
        ncol=1,
        fontsize=8,
        frameon=True,
    )


def main():
    parser = argparse.ArgumentParser(description="Plot history fitting target gas-water production data.")
    parser.add_argument("--history", default=str(DEFAULT_HISTORY_FILE), help="History target CSV.")
    parser.add_argument("--output", default=str(DEFAULT_OUT_FILE), help="Output PNG path.")
    args = parser.parse_args()

    rows = read_history(args.history)
    out_file = Path(args.output)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    fig, (ax_gas, ax_water) = plt.subplots(1, 2, figsize=(15, 5.6), constrained_layout=True)

    plot_production_panel(ax_gas, rows, "Gas", "gas_rate", "gas_cum", "#1f77b4")
    plot_production_panel(ax_water, rows, "Water", "water_rate", "water_cum", "#2ca02c")

    fig.savefig(out_file, dpi=180)
    print(f"plot={out_file}")


if __name__ == "__main__":
    main()
