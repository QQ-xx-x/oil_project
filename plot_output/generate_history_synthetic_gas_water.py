import csv
import json
import math
import os
import random
import sys
from bisect import bisect_right
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = Path(__file__).resolve().parent
BUILD_RELEASE = ROOT / "build" / "Release"
RUN_DIR = OUTPUT_DIR / "run_history_synthetic"
HISTORY_FILE = OUTPUT_DIR / "history_synthetic.csv"
PARAM_FILE = RUN_DIR / "params.json"
SIM_FILE = RUN_DIR / "output_sim_lgr_WR.csv"

COORD_FILE = ROOT / "src" / "basic" / "ratio_style_800x400x120_40x20x6_COORD.csv"
ZCORN_FILE = ROOT / "src" / "basic" / "ratio_style_800x400x120_40x20x6_ZCORN.csv"


# Synthetic truth case. These values are intentionally different from the
# Python front-end defaults and from the old .tmp 100d default scripts.
PARAMS = {
    "coord_file": str(COORD_FILE),
    "zcorn_file": str(ZCORN_FILE),
    "simulation_days": 730.0,
    "start_date": "2022-01-01",
    "history_sample_days": 1.0,
    "random_seed": 37520,
    "fractures": {
        "num_fracs": 72,
        "min_len": 14.0,
        "max_len": 36.0,
        "max_dip": 0.82,
        "min_strike": 0.18,
        "max_strike": 2.72,
        "aperture": 0.075,
        "frac_perm": 180.0,
    },
    "hydraulic_fractures": {
        "hf_count": 14,
        "hf_spacing": 58.0,
        "hf_length": 96.0,
        "hf_height": 24.0,
        "hf_aperture": 0.065,
        "hf_perm": 720.0,
        "hf_center_x": 420.0,
        "hf_center_y": 205.0,
        "hf_center_z": 62.0,
    },
    "well": {
        "radius": 0.06,
        "bhp": 42.0,
    },
    "fluid": {
        "mu_w": 0.78,
        "mu_o_placeholder": 3.6,
        "cw": 2.5e-6,
        "co_placeholder": 8.0e-6,
        "p_ref": 120.0,
        "swi": 0.08,
        "sor_placeholder": 0.02,
        "sgc": 0.04,
        "mu_g_fallback": 0.17,
        "cg_fallback": 8.0e-4,
    },
    "gas_pvt": {
        "gas_t_C": 126.0,
        "gas_Mg": 18.2,
        "gas_Tc": 202.0,
        "gas_Pc_bar": 46.0,
        "gas_table_Pmin_bar": 2.0,
        "gas_table_Pmax_bar": 900.0,
        "gas_table_n": 1400,
        "gas_Psc_bar": 1.01325,
    },
    "initial_state": {
        "pressure": 800.0,
        "sw": 0.4,
        "sg": 0.6,
    },
    "lgr": {
        "enabled": True,
        "d_threshold": 4.2,
        "nrx": 2,
        "nry": 2,
        "nrz": 1,
    },
    "dual_porosity": {
        "enabled": True,
        "phi_matrix": 0.055,
        "phi_fracture": 0.36,
        "k_matrix_x": 0.008,
        "k_matrix_y": 0.006,
        "k_matrix_z": 0.0015,
        "k_fracture_x": 1.6,
        "k_fracture_y": 1.2,
        "k_fracture_z": 0.15,
        "matrix_volume_fraction": 0.965,
        "fracture_volume_fraction": 0.035,
        "wr_shape_factor": 0.085,
    },
    "history_noise": {
        "gas_rate_rel_sigma": 0.065,
        "water_rate_rel_sigma": 0.10,
        "bhp_sigma": 0.18,
    },
}


def require_files():
    missing = [p for p in (BUILD_RELEASE, COORD_FILE, ZCORN_FILE) if not p.exists()]
    if missing:
        raise FileNotFoundError("Missing required files: " + ", ".join(str(p) for p in missing))


def run_simulation():
    sys.path.insert(0, str(BUILD_RELEASE))
    import edfm_core_corner_lgr

    RUN_DIR.mkdir(parents=True, exist_ok=True)
    PARAM_FILE.write_text(json.dumps(PARAMS, indent=2), encoding="utf-8")

    old_cwd = Path.cwd()
    os.chdir(RUN_DIR)
    try:
        sim = edfm_core_corner_lgr.EDFMSimulator()
        sim.setCornerPointFiles(str(COORD_FILE), str(ZCORN_FILE))

        nf = PARAMS["fractures"]
        sim.setFractureParameters(
            nf["num_fracs"],
            nf["min_len"],
            nf["max_len"],
            nf["max_dip"],
            nf["min_strike"],
            nf["max_strike"],
            nf["aperture"],
            nf["frac_perm"],
        )

        hf = PARAMS["hydraulic_fractures"]
        sim.setHydraulicFractureParameters(
            hf["hf_count"],
            hf["hf_spacing"],
            hf["hf_length"],
            hf["hf_height"],
            hf["hf_aperture"],
            hf["hf_perm"],
            hf["hf_center_x"],
            hf["hf_center_y"],
            hf["hf_center_z"],
        )

        well = PARAMS["well"]
        sim.setWellParameters(well["radius"], well["bhp"])

        fluid = PARAMS["fluid"]
        sim.setOilWaterProperties(
            fluid["mu_w"],
            fluid["mu_o_placeholder"],
            fluid["cw"],
            fluid["co_placeholder"],
            fluid["p_ref"],
            fluid["swi"],
            fluid["sor_placeholder"],
            fluid["sgc"],
            fluid["mu_g_fallback"],
            fluid["cg_fallback"],
        )

        gpvt = PARAMS["gas_pvt"]
        sim.setGasPVTParameters(
            gpvt["gas_t_C"],
            gpvt["gas_Mg"],
            gpvt["gas_Tc"],
            gpvt["gas_Pc_bar"],
            gpvt["gas_table_Pmin_bar"],
            gpvt["gas_table_Pmax_bar"],
            gpvt["gas_table_n"],
            gpvt["gas_Psc_bar"],
        )

        init = PARAMS["initial_state"]
        sim.setInitialStateParameters(init["pressure"], init["sw"], init["sg"])

        lgr = PARAMS["lgr"]
        sim.setLGRParameters(lgr["enabled"], lgr["d_threshold"], lgr["nrx"], lgr["nry"], lgr["nrz"])

        dp = PARAMS["dual_porosity"]
        sim.setDualPorosityParameters(
            dp["enabled"],
            dp["phi_matrix"],
            dp["phi_fracture"],
            dp["k_matrix_x"],
            dp["k_matrix_y"],
            dp["k_matrix_z"],
            dp["k_fracture_x"],
            dp["k_fracture_y"],
            dp["k_fracture_z"],
            dp["matrix_volume_fraction"],
            dp["fracture_volume_fraction"],
            dp["wr_shape_factor"],
        )

        sim.setSimulationParameters(PARAMS["simulation_days"])
        sim.runSimulation()
    finally:
        os.chdir(old_cwd)


def read_simulation_rows():
    if not SIM_FILE.exists():
        raise FileNotFoundError(f"Expected simulation output was not created: {SIM_FILE}")

    rows = []
    with SIM_FILE.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(
                {
                    "time": float(row["Time"]),
                    "cum_water": float(row["CumWater"]),
                    "cum_gas": float(row["CumGas"]),
                    "avg_pressure": float(row["AvgPressure"]),
                    "water_rate": max(0.0, float(row["Qw"])),
                    "gas_rate": max(0.0, float(row["Qg"])),
                }
            )

    rows.insert(
        0,
        {
            "time": 0.0,
            "cum_water": 0.0,
            "cum_gas": 0.0,
            "avg_pressure": rows[0]["avg_pressure"],
            "water_rate": rows[0]["water_rate"],
            "gas_rate": rows[0]["gas_rate"],
        },
    )
    return rows


def interpolate(rows, day, key):
    times = [row["time"] for row in rows]
    pos = bisect_right(times, day)
    if pos <= 0:
        return rows[0][key]
    if pos >= len(rows):
        return rows[-1][key]

    left = rows[pos - 1]
    right = rows[pos]
    span = max(right["time"] - left["time"], 1e-12)
    frac = (day - left["time"]) / span
    return left[key] + frac * (right[key] - left[key])


def base_daily_rate(rows, day, cum_key):
    if day <= 0.0:
        return max(0.0, interpolate(rows, 1.0, cum_key))

    prev_day = max(0.0, day - 1.0)
    cum_prev = interpolate(rows, prev_day, cum_key)
    cum_now = interpolate(rows, day, cum_key)
    return max(0.0, cum_now - cum_prev)


def stage_multiplier(day):
    stages = [
        (0.0, 75.0, 1.18),
        (75.0, 165.0, 0.72),
        (165.0, 285.0, 0.98),
        (285.0, 410.0, 0.62),
        (410.0, 545.0, 1.26),
        (545.0, 640.0, 0.78),
        (640.0, 731.0, 1.05),
    ]
    for lo, hi, factor in stages:
        if lo <= day < hi:
            return factor
    return 1.0


def shutin_multiplier(day):
    windows = [
        (54.0, 61.0),
        (143.0, 149.0),
        (232.0, 237.0),
        (358.0, 369.0),
        (487.0, 494.0),
        (618.0, 626.0),
    ]
    for lo, hi in windows:
        if lo <= day <= hi:
            return 0.04
    return 1.0


def operational_rate(base, rng, day, month_factors, phase):
    month_idx = min(len(month_factors) - 1, int(day // 30.0))
    factor = stage_multiplier(day)
    factor *= month_factors[month_idx]
    factor *= shutin_multiplier(day)
    factor *= 1.0 + 0.18 * math.sin(day / 23.0 + phase)
    factor *= rng.lognormvariate(-0.5 * 0.38 * 0.38, 0.38)

    draw = rng.random()
    if draw < 0.055:
        factor *= rng.uniform(0.03, 0.22)
    elif draw > 0.965:
        factor *= rng.uniform(1.8, 3.4)

    return max(0.0, base * factor)


def water_slug_rate(rng, day):
    if day < 25.0:
        return 0.0
    trend = 1.0 + 0.0025 * day
    background = rng.gammavariate(1.1, 0.035) * trend
    if rng.random() < 0.11:
        background += rng.uniform(0.12, 0.75) * trend
    if rng.random() < 0.025:
        background += rng.uniform(0.9, 2.8) * trend
    return background


def generate_history_csv(rows):
    rng = random.Random(PARAMS["random_seed"])
    sample_days = PARAMS["history_sample_days"]
    n_samples = int(PARAMS["simulation_days"] / sample_days) + 1
    start = date.fromisoformat(PARAMS["start_date"])
    well = PARAMS["well"]
    gas_month_factors = [rng.lognormvariate(-0.5 * 0.24 * 0.24, 0.24) for _ in range(26)]
    water_month_factors = [rng.lognormvariate(-0.5 * 0.34 * 0.34, 0.34) for _ in range(26)]

    history = []
    prev_day = 0.0
    prev_qw = None
    prev_qg = None
    water_cum = 0.0
    gas_cum = 0.0

    for i in range(n_samples):
        day = round(i * sample_days, 8)
        qw_base = base_daily_rate(rows, day, "cum_water")
        qg_base = base_daily_rate(rows, day, "cum_gas")

        water_rate = operational_rate(qw_base, rng, day, water_month_factors, 0.4)
        water_rate += water_slug_rate(rng, day)
        gas_rate = operational_rate(qg_base, rng, day, gas_month_factors, 1.7)

        if prev_qw is not None:
            dt = day - prev_day
            water_cum += 0.5 * (prev_qw + water_rate) * dt
            gas_cum += 0.5 * (prev_qg + gas_rate) * dt

        bhp = well["bhp"] + 0.25 * math.sin(day / 95.0) + rng.gauss(0.0, PARAMS["history_noise"]["bhp_sigma"])
        history.append(
            {
                "date": (start + timedelta(days=int(round(day)))).isoformat(),
                "day": f"{day:.3f}",
                "water_rate_sm3_d": f"{water_rate:.8g}",
                "gas_rate_sm3_d": f"{gas_rate:.8g}",
                "water_cum_sm3": f"{water_cum:.8g}",
                "gas_cum_sm3": f"{gas_cum:.8g}",
                "bhp": f"{bhp:.5g}",
                "status": "normal",
            }
        )

        prev_day = day
        prev_qw = water_rate
        prev_qg = gas_rate

    with HISTORY_FILE.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "date",
                "day",
                "water_rate_sm3_d",
                "gas_rate_sm3_d",
                "water_cum_sm3",
                "gas_cum_sm3",
                "bhp",
                "status",
            ],
        )
        writer.writeheader()
        writer.writerows(history)

    return history


def main():
    require_files()
    if "--from-existing" in sys.argv and SIM_FILE.exists():
        print(f"reuse_simulation_csv={SIM_FILE}")
    else:
        run_simulation()
    rows = read_simulation_rows()
    history = generate_history_csv(rows)
    print(f"simulation_csv={SIM_FILE}")
    print(f"history_csv={HISTORY_FILE}")
    print(f"params_json={PARAM_FILE}")
    print(f"history_rows={len(history)}")
    print(f"last_row={json.dumps(history[-1], ensure_ascii=False)}")


if __name__ == "__main__":
    main()
