# -*- coding: utf-8 -*-
"""CaseData 标准数据包字段定义。

这个文件只放稳定常量，避免 UI、构建器和算法接口各自写一套字段名。
"""

SCHEMA_VERSION = "case_dataset_v1"
DEFAULT_NULL_VALUE = 99999.0

MANIFEST_FILE = "manifest.json"
CONFIG_FILE = "config.json"
CASE_SECTIONS_FILE = "case_sections.json"
ARRAYS_FILE = "arrays.npz"
DFN_FILE = "dfn.json"
WELLS_FILE = "wells.json"
VALIDATION_FILE = "validation.json"
RAW_DIR = "raw"

GRID_FILE_KEY = "grid_file"
FRACTURE_FILE_KEY = "fracture_file"

GRID_ARRAYS = {
    "coord": "grid_coord",
    "zcorn": "grid_zcorn",
    "actnum": "grid_actnum",
}

PROPERTY_ARRAYS = {
    "matrix_phi_file": "matrix_phi",
    "matrix_kx_file": "matrix_kx",
    "matrix_ky_file": "matrix_ky",
    "matrix_kz_file": "matrix_kz",
    "fracture_phi_file": "fracture_phi",
    "fracture_kx_file": "fracture_kx",
    "fracture_ky_file": "fracture_ky",
    "fracture_kz_file": "fracture_kz",
    "sigma_file": "sigma",
    "actnum_file": "actnum_property",
}

WR_PROPERTY_FILE_KEYS = (
    "fracture_phi_file",
    "fracture_kx_file",
    "fracture_ky_file",
    "fracture_kz_file",
    "sigma_file",
)

REQUIRED_FILE_KEYS = (
    GRID_FILE_KEY,
    "matrix_phi_file",
    "matrix_kx_file",
    "matrix_ky_file",
    "matrix_kz_file",
)

MASK_ACTIVE_KEY = "mask_active"
MASK_PREFIX = "mask_"
