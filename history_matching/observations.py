import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from parameters import resolve_path


@dataclass
class ObservationSet:
    days: np.ndarray
    channels: list
    values: np.ndarray
    std: np.ndarray
    labels: list

    def transform_simulation(self, simulation):
        pieces = []
        for channel in self.channels:
            model_key = channel["model_key"]
            raw = np.interp(self.days, simulation["day"], simulation[model_key])
            pieces.append(apply_transform(raw, channel))
        return np.concatenate(pieces)

    def normalized_residual(self, simulation_vector):
        return (simulation_vector - self.values) / np.maximum(self.std, 1e-12)

    def objective(self, simulation_vector):
        residual = self.normalized_residual(simulation_vector)
        return float(np.sqrt(np.mean(residual * residual)))


def apply_transform(values, channel):
    arr = np.asarray(values, dtype=float)
    transform = channel.get("transform", "linear")
    if transform == "linear":
        return arr
    if transform == "log":
        eps = float(channel.get("epsilon", 1e-12))
        return np.log(np.maximum(arr, 0.0) + eps)
    raise ValueError(f"Unsupported observation transform: {transform}")


def transformed_std(raw_values, channel):
    raw = np.asarray(raw_values, dtype=float)
    rel = float(channel.get("relative_error", 0.0))
    abs_err = float(channel.get("absolute_error", 0.0))
    weight = max(float(channel.get("weight", 1.0)), 1e-12)
    sigma_raw = np.maximum(abs_err, rel * np.maximum(np.abs(raw), 1e-12))

    transform = channel.get("transform", "linear")
    if transform == "linear":
        sigma = sigma_raw
    elif transform == "log":
        eps = float(channel.get("epsilon", 1e-12))
        sigma = sigma_raw / np.maximum(raw + eps, 1e-12)
        sigma = np.maximum(sigma, 1e-4)
    else:
        raise ValueError(f"Unsupported observation transform: {transform}")

    return sigma / weight


def read_history_csv(path):
    rows = []
    with Path(path).open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    if not rows:
        raise ValueError(f"History file is empty: {path}")

    data = {"day": np.array([float(row["day"]) for row in rows], dtype=float)}
    for key in rows[0]:
        if key in {"date", "status", "day"}:
            continue
        try:
            data[key] = np.array([float(row[key]) for row in rows], dtype=float)
        except ValueError:
            continue
    return data


def build_observations(config):
    history_path = resolve_path(config["history_file"], config)
    history = read_history_csv(history_path)
    obs_cfg = config["observation"]
    well_control = config.get("well_control") or {}
    mode = well_control.get("mode") or "free"
    if mode not in {"free", "fixed_bhp", "fixed_gas_rate", "fixed_water_rate"}:
        raise ValueError(f"Unsupported well_control mode: {mode}")
    channels = obs_cfg["channels"]
    if mode == "fixed_bhp":
        channels = [
            channel
            for channel in channels
            if channel.get("name") != "bhp" and channel.get("model_key") != "bhp"
        ]
    elif mode == "fixed_gas_rate":
        channels = [
            channel
            for channel in channels
            if channel.get("name") not in {"gas_rate", "gas_cum"}
            and channel.get("model_key") not in {"gas_rate", "gas_cum"}
        ]
    elif mode == "fixed_water_rate":
        channels = [
            channel
            for channel in channels
            if channel.get("name") not in {"water_rate", "water_cum"}
            and channel.get("model_key") not in {"water_rate", "water_cum"}
        ]
    start_day = float(obs_cfg.get("start_day", np.min(history["day"])))
    end_day = float(obs_cfg.get("end_day", np.max(history["day"])))
    stride = float(obs_cfg.get("stride_days", 1.0))
    days = np.arange(start_day, end_day + 0.5 * stride, stride, dtype=float)

    values = []
    std = []
    labels = []
    for channel in channels:
        raw = np.interp(days, history["day"], history[channel["column"]])
        values.append(apply_transform(raw, channel))
        std.append(transformed_std(raw, channel))
        labels.extend([f"{channel['name']}@{day:g}d" for day in days])

    return ObservationSet(
        days=days,
        channels=channels,
        values=np.concatenate(values),
        std=np.concatenate(std),
        labels=labels,
    )
