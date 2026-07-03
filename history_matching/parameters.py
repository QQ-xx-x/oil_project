import copy
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np


def load_config(config_path):
    path = Path(config_path)
    with path.open("r", encoding="utf-8") as f:
        config = json.load(f)
    config["_config_path"] = str(path.resolve())
    config["_config_dir"] = str(path.resolve().parent)
    config["_project_root"] = str(path.resolve().parents[1])
    return config


def resolve_path(raw_path, config, base="config"):
    path = Path(raw_path)
    if path.is_absolute():
        return path
    if base == "project":
        return Path(config["_project_root"]) / path
    return Path(config["_config_dir"]) / path


def get_nested(data, path):
    current = data
    for key in path:
        current = current[key]
    return current


def set_nested(data, path, value):
    current = data
    for key in path[:-1]:
        current = current[key]
    current[path[-1]] = value


@dataclass(frozen=True)
class ParameterSpec:
    name: str
    path: tuple
    initial: float
    lower: float
    upper: float
    transform: str
    perturb: float
    dependent: Optional[dict] = None


class ParameterManager:
    def __init__(self, config):
        self.config = config
        self.base_params = copy.deepcopy(config["base_params"])
        self.well_control = config.get("well_control") or {}
        self.well_control_mode = self.well_control.get("mode") or "free"
        if self.well_control_mode not in {"free", "fixed_bhp", "fixed_gas_rate", "fixed_water_rate"}:
            raise ValueError(f"Unsupported well_control mode: {self.well_control_mode}")
        if self.well_control_mode == "fixed_bhp":
            self._apply_fixed_bhp()
        if self.well_control_mode != "free":
            fit_parameters = [
                item for item in config["fit_parameters"] if not self._is_well_bhp_parameter(item)
            ]
        else:
            fit_parameters = config["fit_parameters"]
        self.specs = [self._parse_spec(item) for item in fit_parameters]

    def _is_well_bhp_parameter(self, item):
        return item.get("name") == "well_bhp" or tuple(item.get("path", ())) == ("well", "bhp")

    def _apply_fixed_bhp(self):
        if "bhp" not in self.well_control:
            raise ValueError("well_control.bhp is required when well_control.mode is fixed_bhp.")
        bhp = float(self.well_control["bhp"])
        if not np.isfinite(bhp):
            raise ValueError("well_control.bhp must be a finite number.")
        set_nested(self.base_params, ("well", "bhp"), bhp)

    def _parse_spec(self, item):
        return ParameterSpec(
            name=item["name"],
            path=tuple(item["path"]),
            initial=float(item["initial"]),
            lower=float(item["lower"]),
            upper=float(item["upper"]),
            transform=item.get("transform", "linear"),
            perturb=float(item.get("perturb", 0.0)),
            dependent=item.get("dependent"),
        )

    @property
    def names(self):
        return [spec.name for spec in self.specs]

    def to_internal(self, value, spec):
        value = float(np.clip(value, spec.lower, spec.upper))
        if spec.transform == "log":
            return float(np.log(value))
        if spec.transform == "linear":
            return value
        raise ValueError(f"Unsupported transform for {spec.name}: {spec.transform}")

    def from_internal(self, value, spec):
        if spec.transform == "log":
            physical = float(np.exp(value))
        elif spec.transform == "linear":
            physical = float(value)
        else:
            raise ValueError(f"Unsupported transform for {spec.name}: {spec.transform}")
        return float(np.clip(physical, spec.lower, spec.upper))

    def lower_internal(self, spec):
        return self.to_internal(spec.lower, spec)

    def upper_internal(self, spec):
        return self.to_internal(spec.upper, spec)

    def initial_vector(self):
        return np.array([self.to_internal(spec.initial, spec) for spec in self.specs], dtype=float)

    def lower_vector(self):
        return np.array([self.lower_internal(spec) for spec in self.specs], dtype=float)

    def upper_vector(self):
        return np.array([self.upper_internal(spec) for spec in self.specs], dtype=float)

    def sample_initial_ensemble(self, ensemble_size, seed):
        rng = np.random.default_rng(seed)
        center = self.initial_vector()
        lower = self.lower_vector()
        upper = self.upper_vector()
        ensemble = np.empty((len(self.specs), ensemble_size), dtype=float)

        for i, spec in enumerate(self.specs):
            if spec.perturb <= 0:
                ensemble[i, :] = center[i]
            else:
                ensemble[i, :] = rng.normal(center[i], spec.perturb, size=ensemble_size)

        return self.clip_internal(ensemble)

    def clip_internal(self, vector_or_matrix):
        lower = self.lower_vector()
        upper = self.upper_vector()
        if vector_or_matrix.ndim == 1:
            return np.clip(vector_or_matrix, lower, upper)
        return np.clip(vector_or_matrix, lower[:, None], upper[:, None])

    def vector_to_physical(self, vector):
        return {spec.name: self.from_internal(vector[i], spec) for i, spec in enumerate(self.specs)}

    def vector_to_params(self, vector):
        params = copy.deepcopy(self.base_params)
        for i, spec in enumerate(self.specs):
            value = self.from_internal(vector[i], spec)
            set_nested(params, spec.path, value)
            if spec.dependent:
                formula = spec.dependent.get("formula")
                if formula == "one_minus_value":
                    dependent_value = 1.0 - value
                else:
                    raise ValueError(f"Unsupported dependent formula for {spec.name}: {formula}")
                set_nested(params, spec.dependent["path"], dependent_value)
        return params

    def ensemble_physical_rows(self, ensemble, iteration):
        rows = []
        for member in range(ensemble.shape[1]):
            physical = self.vector_to_physical(ensemble[:, member])
            physical["iteration"] = iteration
            physical["member"] = member
            rows.append(physical)
        return rows

    def mean_params(self, ensemble):
        mean_vector = np.mean(ensemble, axis=1)
        mean_vector = self.clip_internal(mean_vector)
        return self.vector_to_params(mean_vector), self.vector_to_physical(mean_vector)
