import argparse
import csv
import json
import random
from pathlib import Path


OUTPUT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = OUTPUT_DIR.parent
DEFAULT_SIM_CANDIDATES = [
    OUTPUT_DIR / "run_history_synthetic" / "output_sim_lgr_WR.csv",
    PROJECT_ROOT / ".tmp" / "run_history_synthetic" / "output_sim_lgr_WR.csv",
]
DEFAULT_OUT = OUTPUT_DIR / "history_fit_target.csv"
DEFAULT_NOISE_BOUNDS = {
    "gas": (0.88, 1.13),
    "water": (0.82, 1.20),
}


def read_simulation(path):
    rows = [{"day": 0.0, "water_cum": 0.0, "gas_cum": 0.0, "water_rate": 0.0, "gas_rate": 0.0}]
    with Path(path).open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(
                {
                    "day": float(row["Time"]),
                    "water_cum": float(row["CumWater"]),
                    "gas_cum": float(row["CumGas"]),
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


def pick_default_simulation():
    for candidate in DEFAULT_SIM_CANDIDATES:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        "No default true simulation output found. Tried: "
        + ", ".join(str(path) for path in DEFAULT_SIM_CANDIDATES)
    )


def choose_seed(seed):
    if seed is not None:
        return seed
    return random.SystemRandom().randrange(1, 2**63)


def bounded_lognormal_factor(rng, rel_sigma, bounds):
    if rel_sigma <= 0.0:
        return 1.0
    lo, hi = bounds
    for _ in range(100):
        factor = rng.lognormvariate(-0.5 * rel_sigma * rel_sigma, rel_sigma)
        if lo <= factor <= hi:
            return factor
    return min(max(factor, lo), hi)


def small_noise(value, rng, rel_sigma, bounds):
    factor = bounded_lognormal_factor(rng, rel_sigma, bounds)
    return max(0.0, value * factor)


def generate_target(sim_rows, out_path, seed, total_days, rate_noise, noise_bounds):
    rng = random.Random(seed)
    target_rows = []
    prev_day = 0.0
    prev_water_rate = None
    prev_gas_rate = None
    water_cum = 0.0
    gas_cum = 0.0

    for day_int in range(int(total_days) + 1):
        day = float(day_int)
        water_rate_clean = interp(sim_rows, day, "water_rate")
        gas_rate_clean = interp(sim_rows, day, "gas_rate")
        water_rate = small_noise(water_rate_clean, rng, rate_noise["water"], noise_bounds["water"])
        gas_rate = small_noise(gas_rate_clean, rng, rate_noise["gas"], noise_bounds["gas"])

        if prev_water_rate is not None:
            dt = day - prev_day
            water_cum += 0.5 * (prev_water_rate + water_rate) * dt
            gas_cum += 0.5 * (prev_gas_rate + gas_rate) * dt

        target_rows.append(
            {
                "date": "",
                "day": f"{day:.3f}",
                "water_rate_sm3_d": f"{water_rate:.8g}",
                "gas_rate_sm3_d": f"{gas_rate:.8g}",
                "water_cum_sm3": f"{water_cum:.8g}",
                "gas_cum_sm3": f"{gas_cum:.8g}",
                "bhp": "",
                "status": "fit_target",
            }
        )
        prev_day = day
        prev_water_rate = water_rate
        prev_gas_rate = gas_rate

    with Path(out_path).open("w", newline="", encoding="utf-8") as f:
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
    parser = argparse.ArgumentParser(description="Generate a model-consistent fitting target history CSV.")
    parser.add_argument("--simulation", default=None, help="Truth simulation output_sim_lgr_WR.csv.")
    parser.add_argument("--output", default=str(DEFAULT_OUT), help="Output history_fit_target.csv path.")
    parser.add_argument("--seed", type=int, default=None, help="Random seed. Omit it to generate a new target every run.")
    parser.add_argument("--days", type=float, default=730.0)
    parser.add_argument("--gas-rate-noise", type=float, default=0.04)
    parser.add_argument("--water-rate-noise", type=float, default=0.06)
    parser.add_argument("--gas-factor-min", type=float, default=DEFAULT_NOISE_BOUNDS["gas"][0])
    parser.add_argument("--gas-factor-max", type=float, default=DEFAULT_NOISE_BOUNDS["gas"][1])
    parser.add_argument("--water-factor-min", type=float, default=DEFAULT_NOISE_BOUNDS["water"][0])
    parser.add_argument("--water-factor-max", type=float, default=DEFAULT_NOISE_BOUNDS["water"][1])
    args = parser.parse_args()

    sim_path = Path(args.simulation) if args.simulation else pick_default_simulation()
    seed = choose_seed(args.seed)
    noise_bounds = {
        "gas": (args.gas_factor_min, args.gas_factor_max),
        "water": (args.water_factor_min, args.water_factor_max),
    }
    sim_rows = read_simulation(sim_path)
    rows = generate_target(
        sim_rows,
        Path(args.output),
        seed,
        args.days,
        {"gas": args.gas_rate_noise, "water": args.water_rate_noise},
        noise_bounds,
    )
    print(f"simulation={sim_path}")
    print(f"target={Path(args.output)}")
    print(f"seed={seed}")
    print(f"noise_bounds={json.dumps(noise_bounds, ensure_ascii=False)}")
    print(f"rows={len(rows)}")
    print(f"last_row={json.dumps(rows[-1], ensure_ascii=False)}")


if __name__ == "__main__":
    main()
