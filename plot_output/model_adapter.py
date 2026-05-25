import csv
import json
import os
import shutil
import sys
from contextlib import contextmanager
from pathlib import Path

import numpy as np

from parameters import resolve_path


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


class ForwardModelAdapter:
    def __init__(self, config):
        self.config = config
        build_release = resolve_path(config["build_release"], config)
        if not build_release.exists():
            raise FileNotFoundError(f"Build release directory does not exist: {build_release}")
        sys.path.insert(0, str(build_release))
        import edfm_core_corner_lgr

        self.module = edfm_core_corner_lgr

    def run_member(self, params, run_dir, quiet=True):
        run_path = Path(run_dir)
        run_path.mkdir(parents=True, exist_ok=True)
        params_path = run_path / "params.json"
        params_path.write_text(json.dumps(params, indent=2), encoding="utf-8")

        output_name = "output_sim_lgr_WR.csv" if params["dual_porosity"]["enabled"] else "output_sim_lgr_noWR.csv"
        output_path = run_path / output_name
        if self.config.get("enkf", {}).get("reuse_existing_outputs", False) and output_path.exists():
            simulation = read_simulation_output(output_path)
            if simulation["day"][-1] >= float(params["simulation_days"]) - 1e-6:
                return simulation, output_path

        old_cwd = Path.cwd()
        os.chdir(run_path)
        try:
            with redirect_process_output(run_path / "run.log", enabled=quiet):
                self._run_cpp_simulation(params)
        finally:
            os.chdir(old_cwd)

        simulation = read_simulation_output(output_path)
        return simulation, output_path

    def _run_cpp_simulation(self, params):
        sim = self.module.EDFMSimulator()
        coord_file = resolve_path(params["coord_file"], self.config)
        zcorn_file = resolve_path(params["zcorn_file"], self.config)
        sim.setCornerPointFiles(str(coord_file), str(zcorn_file))

        nf = params["fractures"]
        sim.setFractureParameters(
            int(nf["num_fracs"]),
            float(nf["min_len"]),
            float(nf["max_len"]),
            float(nf["max_dip"]),
            float(nf["min_strike"]),
            float(nf["max_strike"]),
            float(nf["aperture"]),
            float(nf["frac_perm"]),
        )

        hf = params["hydraulic_fractures"]
        sim.setHydraulicFractureParameters(
            int(hf["hf_count"]),
            float(hf["hf_spacing"]),
            float(hf["hf_length"]),
            float(hf["hf_height"]),
            float(hf["hf_aperture"]),
            float(hf["hf_perm"]),
            float(hf["hf_center_x"]),
            float(hf["hf_center_y"]),
            float(hf["hf_center_z"]),
        )

        well = params["well"]
        sim.setWellParameters(float(well["radius"]), float(well["bhp"]))

        fluid = params["fluid"]
        sim.setOilWaterProperties(
            float(fluid["mu_w"]),
            float(fluid["mu_o_placeholder"]),
            float(fluid["cw"]),
            float(fluid["co_placeholder"]),
            float(fluid["p_ref"]),
            float(fluid["swi"]),
            float(fluid["sor_placeholder"]),
            float(fluid["sgc"]),
            float(fluid["mu_g_fallback"]),
            float(fluid["cg_fallback"]),
        )

        gpvt = params["gas_pvt"]
        sim.setGasPVTParameters(
            float(gpvt["gas_t_C"]),
            float(gpvt["gas_Mg"]),
            float(gpvt["gas_Tc"]),
            float(gpvt["gas_Pc_bar"]),
            float(gpvt["gas_table_Pmin_bar"]),
            float(gpvt["gas_table_Pmax_bar"]),
            int(gpvt["gas_table_n"]),
            float(gpvt["gas_Psc_bar"]),
        )

        init = params["initial_state"]
        sim.setInitialStateParameters(float(init["pressure"]), float(init["sw"]), float(init["sg"]))

        lgr = params["lgr"]
        sim.setLGRParameters(
            bool(lgr["enabled"]),
            float(lgr["d_threshold"]),
            int(lgr["nrx"]),
            int(lgr["nry"]),
            int(lgr["nrz"]),
        )

        dp = params["dual_porosity"]
        sim.setDualPorosityParameters(
            bool(dp["enabled"]),
            float(dp["phi_matrix"]),
            float(dp["phi_fracture"]),
            float(dp["k_matrix_x"]),
            float(dp["k_matrix_y"]),
            float(dp["k_matrix_z"]),
            float(dp["k_fracture_x"]),
            float(dp["k_fracture_y"]),
            float(dp["k_fracture_z"]),
            float(dp["matrix_volume_fraction"]),
            float(dp["fracture_volume_fraction"]),
            float(dp["wr_shape_factor"]),
        )

        sim.setSimulationParameters(float(params["simulation_days"]))
        sim.runSimulation()


def read_simulation_output(path):
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Simulation output not found: {path}")

    rows = []
    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    if not rows:
        raise ValueError(f"Simulation output is empty: {path}")

    day = np.array([float(row["Time"]) for row in rows], dtype=float)
    water_cum = np.array([float(row["CumWater"]) for row in rows], dtype=float)
    gas_cum = np.array([float(row["CumGas"]) for row in rows], dtype=float)
    water_rate = np.array([max(0.0, float(row["Qw"])) for row in rows], dtype=float)
    gas_rate = np.array([max(0.0, float(row["Qg"])) for row in rows], dtype=float)

    if day[0] > 0.0:
        day = np.insert(day, 0, 0.0)
        water_cum = np.insert(water_cum, 0, 0.0)
        gas_cum = np.insert(gas_cum, 0, 0.0)
        water_rate = np.insert(water_rate, 0, water_rate[0])
        gas_rate = np.insert(gas_rate, 0, gas_rate[0])

    return {
        "day": day,
        "water_cum": water_cum,
        "gas_cum": gas_cum,
        "water_rate": water_rate,
        "gas_rate": gas_rate,
        "output_path": str(path),
    }


def copy_best_output(output_path, destination):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(output_path, destination)
