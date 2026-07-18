# -*- coding: utf-8 -*-
"""3D 工作区统一属性选择及功能能力映射。"""

from dataclasses import dataclass


CAP_RESULT = "result"
CAP_SLICE = "slice"
CAP_THRESHOLD = "threshold"
CAP_TIME = "time"
CAP_STATIC = "static"
CAP_FENCE = "fence"


@dataclass(frozen=True)
class ViewPropertySpec:
    key: str
    label: str
    result_key: str = ""
    static_key: str = ""
    fence_name: str = ""
    capabilities: frozenset = frozenset()

    def supports(self, capability):
        return str(capability or "") in self.capabilities


_RESULT_CAPABILITIES = frozenset((
    CAP_RESULT,
    CAP_SLICE,
    CAP_THRESHOLD,
    CAP_TIME,
    CAP_FENCE,
))
_MATRIX_CAPABILITIES = frozenset((*_RESULT_CAPABILITIES, CAP_STATIC))
_STATIC_CAPABILITIES = frozenset((CAP_STATIC,))


VIEW_PROPERTY_SPECS = (
    ViewPropertySpec(
        "pressure_field", "Pressure",
        result_key="pressure_field", fence_name="Pressure",
        capabilities=_RESULT_CAPABILITIES,
    ),
    ViewPropertySpec(
        "water_saturation_field", "Sw",
        result_key="water_saturation_field", fence_name="Sw",
        capabilities=_RESULT_CAPABILITIES,
    ),
    ViewPropertySpec(
        "porosity_field", "Phi (Matrix)",
        result_key="porosity_field", static_key="MATRIX_PORO",
        fence_name="Phi", capabilities=_MATRIX_CAPABILITIES,
    ),
    ViewPropertySpec(
        "permeability_x_field", "Kx (Matrix)",
        result_key="permeability_x_field", static_key="MATRIX_PERMX",
        fence_name="Kx", capabilities=_MATRIX_CAPABILITIES,
    ),
    ViewPropertySpec(
        "permeability_y_field", "Ky (Matrix)",
        result_key="permeability_y_field", static_key="MATRIX_PERMY",
        fence_name="Ky", capabilities=_MATRIX_CAPABILITIES,
    ),
    ViewPropertySpec(
        "permeability_z_field", "Kz (Matrix)",
        result_key="permeability_z_field", static_key="MATRIX_PERMZ",
        fence_name="Kz", capabilities=_MATRIX_CAPABILITIES,
    ),
    ViewPropertySpec(
        "DFN_PORO", "Phi (DFN)", static_key="DFN_PORO",
        capabilities=_STATIC_CAPABILITIES,
    ),
    ViewPropertySpec(
        "DFN_PERMX", "Kx (DFN)", static_key="DFN_PERMX",
        capabilities=_STATIC_CAPABILITIES,
    ),
    ViewPropertySpec(
        "DFN_PERMY", "Ky (DFN)", static_key="DFN_PERMY",
        capabilities=_STATIC_CAPABILITIES,
    ),
    ViewPropertySpec(
        "DFN_PERMZ", "Kz (DFN)", static_key="DFN_PERMZ",
        capabilities=_STATIC_CAPABILITIES,
    ),
    ViewPropertySpec(
        "SIGMA", "SIGMA", static_key="SIGMA",
        capabilities=_STATIC_CAPABILITIES,
    ),
)

VIEW_PROPERTY_BY_KEY = {spec.key: spec for spec in VIEW_PROPERTY_SPECS}

_PROPERTY_ALIASES = {
    "MATRIX_PORO": "porosity_field",
    "MATRIX_PERMX": "permeability_x_field",
    "MATRIX_PERMY": "permeability_y_field",
    "MATRIX_PERMZ": "permeability_z_field",
    "permeability_field": "permeability_x_field",
    "Pressure": "pressure_field",
    "Sw": "water_saturation_field",
    "Phi": "porosity_field",
    "Kx": "permeability_x_field",
    "Ky": "permeability_y_field",
    "Kz": "permeability_z_field",
}


def normalize_view_property_key(value, default="pressure_field"):
    key = str(value or "").strip()
    key = _PROPERTY_ALIASES.get(key, key)
    return key if key in VIEW_PROPERTY_BY_KEY else default


def view_property_spec(value):
    return VIEW_PROPERTY_BY_KEY[normalize_view_property_key(value)]
