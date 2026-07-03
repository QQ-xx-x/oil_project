import argparse
import csv
import json
import math
import os
import random
import shutil
import sys
import tempfile
from contextlib import contextmanager
from datetime import date, timedelta
from pathlib import Path


OUTPUT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = OUTPUT_DIR.parent
BUILD_RELEASE = PROJECT_ROOT / "build" / "Release"
DEFAULT_OUT = OUTPUT_DIR / "history_fit_target.csv"
DEFAULT_PARAMS_OUT = OUTPUT_DIR / "history_fit_truth_params.json"
DEFAULT_LOG_OUT = OUTPUT_DIR / "history_fit_truth_run.log"
DEFAULT_NOISE_BOUNDS = {
    "gas": (0.20, 2.60),
    "water": (0.08, 3.40),
}

COORD_FILE = PROJECT_ROOT / "src" / "basic" / "ratio_style_800x400x120_40x20x6_COORD.csv"
ZCORN_FILE = PROJECT_ROOT / "src" / "basic" / "ratio_style_800x400x120_40x20x6_ZCORN.csv"


TRUTH_PARAMS = {
    "coord_file": str(COORD_FILE),
    "zcorn_file": str(ZCORN_FILE),
    "simulation_days": 730.0,
    "start_date": "2022-01-01",
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
}


def require_files():
    missing = [path for path in (BUILD_RELEASE, COORD_FILE, ZCORN_FILE) if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing required files: " + ", ".join(str(path) for path in missing))


def choose_seed(seed):
    if seed is not None:
        return seed
    return random.SystemRandom().randrange(1, 2**63)


@contextmanager
def redirect_process_output(log_path, enabled=True):
    if not enabled:
        yield
        return

    log_path = Path(log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8", errors="ignore") as log:
        stdout_fd = os.dup(1)
        stderr_fd = os.dup(2)
        try:
            os.dup2(log.fileno(), 1)
            os.dup2(log.fileno(), 2)
            yield
        finally:
            os.dup2(stdout_fd, 1)
            os.dup2(stderr_fd, 2)
            os.close(stdout_fd)
            os.close(stderr_fd)


def run_truth_simulation(params, run_dir, log_path, quiet=True):
    sys.path.insert(0, str(BUILD_RELEASE))
    import edfm_core_corner_lgr

    run_path = Path(run_dir)
    run_path.mkdir(parents=True, exist_ok=True)
    (run_path / "truth_params.json").write_text(json.dumps(params, indent=2), encoding="utf-8")

    old_cwd = Path.cwd()
    os.chdir(run_path)
    try:
        sim = edfm_core_corner_lgr.EDFMSimulator()
        sim.setCornerPointFiles(str(params["coord_file"]), str(params["zcorn_file"]))

        nf = params["fractures"]
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

        hf = params["hydraulic_fractures"]
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

        well = params["well"]
        sim.setWellParameters(well["radius"], well["bhp"])

        fluid = params["fluid"]
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

        gpvt = params["gas_pvt"]
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

        init = params["initial_state"]
        sim.setInitialStateParameters(init["pressure"], init["sw"], init["sg"])

        lgr = params["lgr"]
        sim.setLGRParameters(lgr["enabled"], lgr["d_threshold"], lgr["nrx"], lgr["nry"], lgr["nrz"])

        dp = params["dual_porosity"]
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

        sim.setSimulationParameters(params["simulation_days"])
        with redirect_process_output(log_path, enabled=quiet):
            sim.runSimulation()
    finally:
        os.chdir(old_cwd)

    sim_file = run_path / "output_sim_lgr_WR.csv"
    if not sim_file.exists():
        raise FileNotFoundError(f"Truth simulation did not create expected internal output: {sim_file}")
    return read_simulation(sim_file)


def read_simulation(path):
    rows = [{"day": 0.0, "water_rate": 0.0, "gas_rate": 0.0}]
    with Path(path).open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(
                {
                    "day": float(row["Time"]),
                    "water_rate": max(0.0, float(row["Qw"])),
                    "gas_rate": max(0.0, float(row["Qg"])),
                }
            )
    return rows


def interp(rows, day, key):
    if day <= rows[0]["day"]:
        return rows[0][key]
    for left, right in zip(rows[:-1], rows[1:]):
        if left["day"] <= day <= right["day"]:
            span = max(right["day"] - left["day"], 1e-12)
            frac = (day - left["day"]) / span
            return left[key] + frac * (right[key] - left[key])
    return rows[-1][key]


def bounded_lognormal_factor(rng, rel_sigma, bounds):
    if rel_sigma <= 0.0:
        return 1.0
    lo, hi = bounds
    for _ in range(100):
        factor = rng.lognormvariate(-0.5 * rel_sigma * rel_sigma, rel_sigma)
        if lo <= factor <= hi:
            return factor
    return min(max(factor, lo), hi)


def noisy_rate(value, rng, rel_sigma, bounds):
    return max(0.0, value * bounded_lognormal_factor(rng, rel_sigma, bounds))


def stage_multiplier(day, phase):
    if phase == "gas":
        stages = [
            (0.0, 70.0, 1.10),
            (70.0, 160.0, 0.82),
            (160.0, 280.0, 0.95),
            (280.0, 420.0, 0.72),
            (420.0, 560.0, 1.16),
            (560.0, 650.0, 0.78),
            (650.0, 731.0, 1.03),
        ]
    else:
        stages = [
            (0.0, 80.0, 1.18),
            (80.0, 180.0, 0.76),
            (180.0, 315.0, 1.04),
            (315.0, 455.0, 0.70),
            (455.0, 585.0, 1.24),
            (585.0, 660.0, 0.62),
            (660.0, 731.0, 1.08),
        ]
    for lo, hi, factor in stages:
        if lo <= day < hi:
            return factor
    return 1.0


def shutin_multiplier(day, rng):
    windows = [
        (52.0, 60.0),
        (145.0, 151.0),
        (238.0, 244.0),
        (365.0, 375.0),
        (508.0, 516.0),
        (628.0, 637.0),
    ]
    for lo, hi in windows:
        if lo <= day <= hi:
            return rng.uniform(0.0, 0.10)
    return 1.0


def observed_factor(day, rng, month_factors, phase, rel_sigma, bounds):
    month_idx = min(len(month_factors) - 1, int(day // 30.0))
    factor = stage_multiplier(day, phase)
    factor *= month_factors[month_idx]
    factor *= shutin_multiplier(day, rng)
    factor *= max(0.05, 1.0 + 0.16 * math.sin(day / 19.0 + (0.4 if phase == "water" else 1.7)))
    factor *= max(0.05, 1.0 + 0.08 * math.sin(day / 7.5 + (1.2 if phase == "water" else 0.2)))
    factor *= bounded_lognormal_factor(rng, rel_sigma, bounds)

    draw = rng.random()
    if draw < 0.045:
        factor *= rng.uniform(0.02, 0.25)
    elif draw > 0.965:
        factor *= rng.uniform(1.7, 3.2)
    return max(0.0, factor)


def water_slug_rate(rng, day, base_rate):
    if day < 20.0:
        return 0.0
    trend = 1.0 + 0.0015 * day
    slug = rng.gammavariate(1.15, 0.035 * max(base_rate, 1.0)) * trend
    if rng.random() < 0.10:
        slug += rng.uniform(0.04, 0.22) * max(base_rate, 1.0) * trend
    if rng.random() < 0.025:
        slug += rng.uniform(0.35, 0.95) * max(base_rate, 1.0) * trend
    return slug


def trapezoid_total(days, values):
    total = 0.0
    for i in range(1, len(days)):
        total += 0.5 * (values[i - 1] + values[i]) * (days[i] - days[i - 1])
    return total


def normalize_observed_rates(days, clean_rates, observed_rates, rng, phase):
    clean_total = trapezoid_total(days, clean_rates)
    observed_total = trapezoid_total(days, observed_rates)
    if clean_total <= 0.0 or observed_total <= 0.0:
        return observed_rates
    if phase == "gas":
        target_bias = rng.uniform(0.97, 1.04)
    else:
        target_bias = rng.uniform(0.95, 1.08)
    scale = clean_total * target_bias / observed_total
    return [max(0.0, value * scale) for value in observed_rates]


def generate_target(sim_rows, out_path, seed, total_days, start_date, rate_noise, noise_bounds, target_style):
    rng = random.Random(seed)
    days = [float(day_int) for day_int in range(int(total_days) + 1)]
    clean_water_rates = [interp(sim_rows, day, "water_rate") for day in days]
    clean_gas_rates = [interp(sim_rows, day, "gas_rate") for day in days]

    if target_style == "smooth":
        water_rates = [
            noisy_rate(value, rng, min(rate_noise["water"], 0.08), (0.82, 1.20))
            for value in clean_water_rates
        ]
        gas_rates = [
            noisy_rate(value, rng, min(rate_noise["gas"], 0.06), (0.88, 1.13))
            for value in clean_gas_rates
        ]
    else:
        n_months = int(total_days // 30.0) + 3
        gas_month_factors = [
            bounded_lognormal_factor(rng, 0.22, (0.62, 1.45)) for _ in range(n_months)
        ]
        water_month_factors = [
            bounded_lognormal_factor(rng, 0.32, (0.48, 1.75)) for _ in range(n_months)
        ]
        gas_rates = [
            clean * observed_factor(day, rng, gas_month_factors, "gas", rate_noise["gas"], noise_bounds["gas"])
            for day, clean in zip(days, clean_gas_rates)
        ]
        water_rates = [
            clean * observed_factor(day, rng, water_month_factors, "water", rate_noise["water"], noise_bounds["water"])
            + water_slug_rate(rng, day, clean)
            for day, clean in zip(days, clean_water_rates)
        ]
        gas_rates[0] = 0.0
        water_rates[0] = 0.0
        gas_rates = normalize_observed_rates(days, clean_gas_rates, gas_rates, rng, "gas")
        water_rates = normalize_observed_rates(days, clean_water_rates, water_rates, rng, "water")

    target_rows = []
    start = date.fromisoformat(start_date)
    prev_day = 0.0
    prev_water_rate = None
    prev_gas_rate = None
    water_cum = 0.0
    gas_cum = 0.0

    for day, water_rate, gas_rate in zip(days, water_rates, gas_rates):
        if prev_water_rate is not None:
            dt = day - prev_day
            water_cum += 0.5 * (prev_water_rate + water_rate) * dt
            gas_cum += 0.5 * (prev_gas_rate + gas_rate) * dt

        target_rows.append(
            {
                "date": (start + timedelta(days=int(round(day)))).isoformat(),
                "day": f"{day:.3f}",
                "water_rate_sm3_d": f"{water_rate:.8g}",
                "gas_rate_sm3_d": f"{gas_rate:.8g}",
                "water_cum_sm3": f"{water_cum:.8g}",
                "gas_cum_sm3": f"{gas_cum:.8g}",
                "bhp": "",
                "status": target_style,
            }
        )
        prev_day = day
        prev_water_rate = water_rate
        prev_gas_rate = gas_rate

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as f:
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
        writer.writerows(target_rows)
    return target_rows


def main():
    parser = argparse.ArgumentParser(description="Run truth simulation and directly generate history fitting target CSV.")
    parser.add_argument("--output", default=str(DEFAULT_OUT), help="Output history_fit_target.csv path.")
    parser.add_argument("--truth-params-output", default=str(DEFAULT_PARAMS_OUT), help="Saved truth parameter JSON path.")
    parser.add_argument("--log", default=str(DEFAULT_LOG_OUT), help="Truth simulation log path.")
    parser.add_argument("--verbose", action="store_true", help="Print C++ simulation logs to the terminal.")
    parser.add_argument("--seed", type=int, default=None, help="Random seed. Omit it to generate new observation noise every run.")
    parser.add_argument("--target-style", choices=["observed", "smooth"], default="observed")
    parser.add_argument("--gas-rate-noise", type=float, default=0.28)
    parser.add_argument("--water-rate-noise", type=float, default=0.45)
    parser.add_argument("--gas-factor-min", type=float, default=DEFAULT_NOISE_BOUNDS["gas"][0])
    parser.add_argument("--gas-factor-max", type=float, default=DEFAULT_NOISE_BOUNDS["gas"][1])
    parser.add_argument("--water-factor-min", type=float, default=DEFAULT_NOISE_BOUNDS["water"][0])
    parser.add_argument("--water-factor-max", type=float, default=DEFAULT_NOISE_BOUNDS["water"][1])
    parser.add_argument("--keep-run-dir", action="store_true", help="Keep the internal simulation directory for debugging.")
    parser.add_argument("--run-dir", default=None, help="Internal simulation directory. Defaults to a temporary directory.")
    args = parser.parse_args()

    require_files()
    seed = choose_seed(args.seed)
    noise_bounds = {
        "gas": (args.gas_factor_min, args.gas_factor_max),
        "water": (args.water_factor_min, args.water_factor_max),
    }

    run_dir = Path(args.run_dir) if args.run_dir else Path(tempfile.mkdtemp(prefix="truth_fit_", dir=OUTPUT_DIR))
    params = json.loads(json.dumps(TRUTH_PARAMS))

    try:
        sim_rows = run_truth_simulation(params, run_dir, Path(args.log), quiet=not args.verbose)
        rows = generate_target(
            sim_rows,
            Path(args.output),
            seed,
            params["simulation_days"],
            params["start_date"],
            {"gas": args.gas_rate_noise, "water": args.water_rate_noise},
            noise_bounds,
            args.target_style,
        )
    finally:
        if not args.keep_run_dir and args.run_dir is None and run_dir.exists():
            shutil.rmtree(run_dir)

    params_out = Path(args.truth_params_output)
    params_out.parent.mkdir(parents=True, exist_ok=True)
    params_out.write_text(json.dumps(params, indent=2), encoding="utf-8")

    print(f"target={Path(args.output)}")
    print(f"truth_params={params_out}")
    if not args.verbose:
        print(f"log={Path(args.log)}")
    print(f"seed={seed}")
    print(f"target_style={args.target_style}")
    print(f"noise_bounds={json.dumps(noise_bounds, ensure_ascii=False)}")
    print(f"rows={len(rows)}")
    print(f"last_row={json.dumps(rows[-1], ensure_ascii=False)}")
    if args.keep_run_dir or args.run_dir is not None:
        print(f"internal_run_dir={run_dir}")


if __name__ == "__main__":
    main()
