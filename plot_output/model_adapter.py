import csv
import hashlib
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
    def __init__(self, config, run_signature_context=None):
        self.config = config
        self.run_signature_context = run_signature_context or {}
        build_release = resolve_path(config["build_release"], config)
        if not build_release.exists():
            raise FileNotFoundError(f"Build release directory does not exist: {build_release}")
        sys.path.insert(0, str(build_release))
        import edfm_core_corner_lgr

        self.module = edfm_core_corner_lgr
        self.module_path = Path(edfm_core_corner_lgr.__file__).resolve()

    def run_member(self, params, run_dir, quiet=True):
        run_path = Path(run_dir)
        run_path.mkdir(parents=True, exist_ok=True)
        params_path = run_path / "params.json"

        output_name = "output_sim_lgr_WR.csv" if params["dual_porosity"]["enabled"] else "output_sim_lgr_noWR.csv"
        output_path = run_path / output_name
        signature_path = run_path / "run_signature.json"
        signature = self._run_signature(params, output_name)
        if self._can_reuse_existing_output(params, output_path, signature_path, signature):
            return read_simulation_output(output_path), output_path

        params_path.write_text(json.dumps(params, indent=2), encoding="utf-8")

        old_cwd = Path.cwd()
        os.chdir(run_path)
        try:
            with redirect_process_output(run_path / "run.log", enabled=quiet):
                self._run_cpp_simulation(params)
        finally:
            os.chdir(old_cwd)

        simulation = read_simulation_output(output_path)
        signature_record = {
            "input_signature": signature,
            "output_sha256": file_sha256(output_path),
        }
        signature_path.write_text(json.dumps(signature_record, indent=2, sort_keys=True), encoding="utf-8")
        return simulation, output_path

    def _run_signature(self, params, output_name):
        return {
            "version": 1,
            "params_sha256": stable_json_sha256(params),
            "params": params,
            "output_name": output_name,
            "simulation_days": float(params["simulation_days"]),
            "coord_file": self._file_identity(params["coord_file"]),
            "zcorn_file": self._file_identity(params["zcorn_file"]),
            "module_file": self._file_identity(self.module_path),
            "context": self.run_signature_context,
        }

    def _can_reuse_existing_output(self, params, output_path, signature_path, expected_signature):
        if not self.config.get("enkf", {}).get("reuse_existing_outputs", False):
            return False
        if not output_path.exists() or not signature_path.exists():
            return False

        try:
            old_signature = json.loads(signature_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False
        old_input_signature = old_signature.get("input_signature", old_signature)
        if old_input_signature != expected_signature:
            return False
        old_output_sha = old_signature.get("output_sha256")
        if old_output_sha is not None and file_sha256(output_path) != old_output_sha:
            return False

        try:
            simulation = read_simulation_output(output_path)
        except (OSError, ValueError, KeyError):
            return False
        return simulation["day"][-1] >= float(params["simulation_days"]) - 1e-6

    def _file_identity(self, path):
        resolved = resolve_path(str(path), self.config)
        return {
            "path": str(resolved.resolve()),
            "sha256": file_sha256(resolved),
        }

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


def stable_json_sha256(payload):
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def file_sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def copy_best_output(output_path, destination):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(output_path, destination)
