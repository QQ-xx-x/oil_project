import csv
import hashlib
import json
import os
import shutil
import sys
from contextlib import contextmanager
from pathlib import Path

import numpy as np

# 确保项目根目录在 sys.path，防止 CWD 切换后找不到 front 模块
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from front.simulation_runner import run_simulation as _run_sim

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
        self.module = None  # 不再直接调 C++，改为走 simulation_runner
        self.module_path = Path(__file__).resolve()
        self.last_run_reused = False

    def run_member(self, params, run_dir, quiet=True):
        self.last_run_reused = False
        run_path = Path(run_dir)
        run_path.mkdir(parents=True, exist_ok=True)
        params_path = run_path / "params.json"

        output_name = "output_sim_lgr_WR.csv" if params["dual_porosity"]["enabled"] else "output_sim_lgr_noWR.csv"
        output_path = run_path / output_name
        signature_path = run_path / "run_signature.json"
        signature = self._run_signature(params, output_name)
        if self._can_reuse_existing_output(params, output_path, signature_path, signature):
            self.last_run_reused = True
            return read_simulation_output(output_path), output_path

        params_path.write_text(json.dumps(params, indent=2), encoding="utf-8")

        old_cwd = Path.cwd()
        os.chdir(run_path)
        try:
            # with redirect_process_output(run_path / "run.log", enabled=quiet):
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
        sig = {
            "version": 1,
            "params_sha256": stable_json_sha256(params),
            "params": params,
            "output_name": output_name,
            "simulation_days": float(params.get("simulation_days", 730.0)),
            "case_dataset_path": self.config.get("case_dataset_path", ""),
            "context": self.run_signature_context,
        }
        # 向后兼容: 旧的 coord/zcorn 路径如果存在则记录
        if "coord_file" in params:
            sig["coord_file"] = self._file_identity(params["coord_file"])
        if "zcorn_file" in params:
            sig["zcorn_file"] = self._file_identity(params["zcorn_file"])
        return sig

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
        try:
            resolved = resolve_path(str(path), self.config)
            return {
                "path": str(resolved.resolve()),
                "sha256": file_sha256(resolved) if resolved.exists() else "",
            }
        except Exception:
            return {"path": str(path), "sha256": ""}

    def _rate_control_schedule(self, mode):
        well_control = self.config.get("well_control") or {}
        if "days" in well_control and "rates" in well_control:
            return [float(day) for day in well_control["days"]], [float(rate) for rate in well_control["rates"]]
        if "rate" in well_control:
            rate = float(well_control["rate"])
            return [0.0, float(self.config["simulation_days"])], [rate, rate]

        default_column = "gas_rate_sm3_d" if mode == "fixed_gas_rate" else "water_rate_sm3_d"
        column = well_control.get("column") or well_control.get("rate_column") or default_column
        history_path = resolve_path(self.config["history_file"], self.config)
        days = []
        rates = []
        with history_path.open("r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if column not in (reader.fieldnames or []):
                raise ValueError(f"Rate control column does not exist in history file: {column}")
            for row in reader:
                try:
                    day = float(row["day"])
                    rate = float(row[column])
                except ValueError:
                    continue
                days.append(day)
                rates.append(max(0.0, rate))
        if not days:
            raise ValueError(f"Rate control schedule is empty for column: {column}")
        return days, rates

    def _run_cpp_simulation(self, params):
        # 将 EnKF 嵌套参数结构展平为 simulation_runner 参数字典
        nf = params.get("fractures", {})
        hf = params.get("hydraulic_fractures", {})
        well = params.get("well", {})
        fluid = params.get("fluid", {})
        gpvt = params.get("gas_pvt", {})
        init = params.get("initial_state", {})
        lgr = params.get("lgr", {})
        dp = params.get("dual_porosity", {})

        # 解析 case_dataset 路径为绝对路径（防止 CWD 变化后失效）
        ds_path = self.config.get("case_dataset_path", "case_dataset_test")
        ds_path = str(resolve_path(ds_path, self.config).resolve())

        run_params = {
            "interface_source": "case_data",
            "corner_grid_refinement": "加密",
            "case_dataset_path": ds_path,
            "num_fracs": int(nf.get("num_fracs", 10)),
            "min_len": float(nf.get("min_len", 10.0)),
            "max_len": float(nf.get("max_len", 20.0)),
            "max_dip": float(nf.get("max_dip", 0.82)),
            "min_strike": float(nf.get("min_strike", 0.18)),
            "max_strike": float(nf.get("max_strike", 2.72)),
            "aperture": float(nf.get("aperture", 0.075)),
            "frac_perm": float(nf.get("frac_perm", 180.0)),
            "hf_count": int(hf.get("hf_count", 14)),
            "hf_spacing": float(hf.get("hf_spacing", 58.0)),
            "hf_length": float(hf.get("hf_length", 96.0)),
            "hf_height": float(hf.get("hf_height", 24.0)),
            "hf_aperture": float(hf.get("hf_aperture", 0.065)),
            "hf_perm": float(hf.get("hf_perm", 720.0)),
            "hf_center_x": float(hf.get("hf_center_x", -1.0)),
            "hf_center_y": float(hf.get("hf_center_y", -1.0)),
            "hf_center_z": float(hf.get("hf_center_z", -1.0)),
            "well_radius": float(well.get("radius", 0.06)),
            "well_pressure": float(well.get("bhp", 42.0)),
            "mu_w": float(fluid.get("mu_w", 0.78)),
            "mu_o": float(fluid.get("mu_o_placeholder", 3.6)),
            "cw": float(fluid.get("cw", 2.5e-6)),
            "co": float(fluid.get("co_placeholder", 8.0e-6)),
            "p_ref": float(fluid.get("p_ref", 120.0)),
            "swi": float(fluid.get("swi", 0.08)),
            "sor": float(fluid.get("sor_placeholder", 0.02)),
            "sgc": float(fluid.get("sgc", 0.04)),
            "mu_g": float(fluid.get("mu_g_fallback", 0.17)),
            "cg": float(fluid.get("cg_fallback", 8.0e-4)),
            "gas_t_C": float(gpvt.get("gas_t_C", 126.0)),
            "gas_Mg": float(gpvt.get("gas_Mg", 18.2)),
            "gas_Tc": float(gpvt.get("gas_Tc", 202.0)),
            "gas_Pc_bar": float(gpvt.get("gas_Pc_bar", 46.0)),
            "gas_table_Pmin_bar": float(gpvt.get("gas_table_Pmin_bar", 2.0)),
            "gas_table_Pmax_bar": float(gpvt.get("gas_table_Pmax_bar", 900.0)),
            "gas_table_n": int(gpvt.get("gas_table_n", 1400)),
            "gas_Psc_bar": float(gpvt.get("gas_Psc_bar", 1.01325)),
            "pressure": float(init.get("pressure", 800.0)),
            "sw": float(init.get("sw", 0.4)),
            "sg": float(init.get("sg", 0.6)),
            "enable_lgr": bool(lgr.get("enabled", True)),
            "d_threshold": float(lgr.get("d_threshold", 4.2)),
            "lgr_nrx": int(lgr.get("nrx", 2)),
            "lgr_nry": int(lgr.get("nry", 2)),
            "lgr_nrz": int(lgr.get("nrz", 1)),
            "enable_dual_porosity": bool(dp.get("enabled", True)),
            "phi_matrix": float(dp.get("phi_matrix", 0.055)),
            "phi_fracture": float(dp.get("phi_fracture", 0.36)),
            "k_matrix_x": float(dp.get("k_matrix_x", 0.008)),
            "k_matrix_y": float(dp.get("k_matrix_y", 0.006)),
            "k_matrix_z": float(dp.get("k_matrix_z", 0.0015)),
            "k_fracture_x": float(dp.get("k_fracture_x", 1.6)),
            "k_fracture_y": float(dp.get("k_fracture_y", 1.2)),
            "k_fracture_z": float(dp.get("k_fracture_z", 0.15)),
            "matrix_volume_fraction": float(dp.get("matrix_volume_fraction", 0.965)),
            "fracture_volume_fraction": float(dp.get("fracture_volume_fraction", 0.035)),
            "wr_shape_factor": float(dp.get("wr_shape_factor", 0.085)),
            "simulation_time": float(params.get("simulation_days", 730.0)),
        }
        _run_sim(run_params)


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
    bhp = None
    if "BHP" in rows[0]:
        bhp = np.array([float(row["BHP"]) for row in rows], dtype=float)

    if day[0] > 0.0:
        day = np.insert(day, 0, 0.0)
        water_cum = np.insert(water_cum, 0, 0.0)
        gas_cum = np.insert(gas_cum, 0, 0.0)
        water_rate = np.insert(water_rate, 0, water_rate[0])
        gas_rate = np.insert(gas_rate, 0, gas_rate[0])
        if bhp is not None:
            bhp = np.insert(bhp, 0, bhp[0])

    simulation = {
        "day": day,
        "water_cum": water_cum,
        "gas_cum": gas_cum,
        "water_rate": water_rate,
        "gas_rate": gas_rate,
        "output_path": str(path),
    }
    if bhp is not None:
        simulation["bhp"] = bhp
    return simulation


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
