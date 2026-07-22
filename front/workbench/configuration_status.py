# -*- coding: utf-8 -*-
"""Configuration completeness rules shared by the input tree and dialogs."""

import math
import os

from .input_keyword_registry import MODULE_GRID_SPATIAL
from .project_state import (
    GRID_TYPE_CARTESIAN,
    GRID_TYPE_CORNER_POINT,
    normalize_model_config,
)


STATUS_CONFIGURED_COLOR = "#18864b"
STATUS_MISSING_COLOR = "#c43d3d"

GRID_PROPERTY_STATUS_SPECS = (
    ("matrix_kx", "ROCK.matrix_kx_file", False),
    ("matrix_ky", "ROCK.matrix_ky_file", False),
    ("matrix_kz", "ROCK.matrix_kz_file", False),
    ("matrix_phi", "ROCK.matrix_phi_file", False),
    ("actnum", "GRID.actnum_file", True),
)


def model_configuration_is_configured(project_state):
    config = normalize_model_config(
        getattr(project_state, "model_config", None))
    return bool(
        config.get("confirmed")
        and config.get("grid_type") in {
            GRID_TYPE_CARTESIAN, GRID_TYPE_CORNER_POINT}
        and all(int(config.get(key) or 0) > 0
                for key in ("grid_nx", "grid_ny", "grid_nz"))
    )


def geometry_is_configured(project_state):
    config = normalize_model_config(
        getattr(project_state, "model_config", None))
    if not model_configuration_is_configured(project_state):
        return False
    state = project_state.get_module_input_state(MODULE_GRID_SPATIAL)
    if state is None:
        return False
    values = state.parsed_data.values or {}
    if config.get("grid_type") == GRID_TYPE_CARTESIAN:
        cartesian = ((values.get("geometry") or {}).get("cartesian") or {})
        required = (
            "lx", "ly", "lz", "origin_x", "origin_y", "origin_z",
            "rotation_deg",
        )
        if not all(key in cartesian for key in required):
            return False
        try:
            numbers = [float(cartesian[key]) for key in required]
        except (TypeError, ValueError):
            return False
        return (
            all(math.isfinite(value) for value in numbers)
            and all(float(cartesian[key]) > 0.0 for key in ("lx", "ly", "lz"))
        )

    source = ((state.source or {}).get("keywords") or {}).get(
        "GRID.grid_file") or {}
    path = str(source.get("resolved_path") or "").strip()
    if not path or not os.path.isfile(path):
        return False
    grid = values.get("grid") or {}
    nx = int(config.get("grid_nx") or 0)
    ny = int(config.get("grid_ny") or 0)
    nz = int(config.get("grid_nz") or 0)
    return bool(
        int(grid.get("nx") or 0) == nx
        and int(grid.get("ny") or 0) == ny
        and int(grid.get("nz") or 0) == nz
        and int(grid.get("coord_value_count") or 0) == 6 * (nx + 1) * (ny + 1)
        and int(grid.get("zcorn_value_count") or 0) == 8 * nx * ny * nz
    )


def property_is_configured(config, values, source, value_key,
                           source_identity, binary=False, arrays=None):
    """Return whether one property has valid, grid-sized data."""
    config = normalize_model_config(config)
    expected = (
        int(config.get("grid_nx") or 0)
        * int(config.get("grid_ny") or 0)
        * int(config.get("grid_nz") or 0)
    )
    if expected <= 0:
        return False
    arrays = arrays or {}
    if value_key in arrays:
        try:
            return len(arrays[value_key]) == expected
        except TypeError:
            return False

    keywords = (source or {}).get("keywords") or {}
    record = keywords.get(source_identity) or {}
    path = str(record.get("resolved_path") or "").strip()
    summary_key = "actnum_property" if binary else value_key
    summary = ((values or {}).get(summary_key) or {}).get("summary") or {}
    if path and os.path.isfile(path):
        count = int(summary.get("count") or 0)
        if count == expected and summary.get("length_match_grid", True):
            return True

    if binary:
        grid_record = keywords.get("GRID.grid_file") or {}
        grid_path = str(grid_record.get("resolved_path") or "").strip()
        grid = (values or {}).get("grid") or {}
        return bool(
            grid_path and os.path.isfile(grid_path)
            and int(grid.get("actnum_value_count") or 0) == expected
        )
    return False


def grid_properties_are_configured(project_state):
    config = normalize_model_config(
        getattr(project_state, "model_config", None))
    if not model_configuration_is_configured(project_state):
        return False
    state = project_state.get_module_input_state(MODULE_GRID_SPATIAL)
    if state is None:
        return False
    values = state.parsed_data.values or {}
    source = state.source or {}
    return all(
        property_is_configured(
            config, values, source, value_key, source_identity, binary)
        for value_key, source_identity, binary in GRID_PROPERTY_STATUS_SPECS
    )
