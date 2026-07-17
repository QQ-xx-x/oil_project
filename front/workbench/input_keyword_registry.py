# -*- coding: utf-8 -*-
"""Canonical business ownership rules for workbench input keywords.

This module deliberately contains no Qt code and performs no file I/O.  It is
the shared contract that future import, display, validation, synchronization,
and CaseData composition code should query instead of maintaining separate
keyword lists.

Keyword identities are matched case-insensitively as ``(section, keyword)``.
The original spelling stored in :class:`KeywordRule` is retained for display
and for exporting a composed CaseData snapshot.
"""

from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional, Tuple


MODULE_MODEL_CONFIGURATION = "model_configuration"
MODULE_GRID_SPATIAL = "grid_spatial"
MODULE_ROCK_PROPERTIES = "rock_properties"
MODULE_FRACTURE_SYSTEM = "fracture_system_inputs"
MODULE_FLUID_PVT = "fluid_pvt_inputs"
MODULE_INITIAL_CONDITIONS = "initial_conditions"
MODULE_WELL_PRODUCTION = "well_production"
MODULE_SOLVER_OUTPUT = "solver_output"
MODULE_HISTORY_MATCHING = "history_matching_workflow"

REQUIREMENT_REQUIRED = "required"
REQUIREMENT_OPTIONAL = "optional"
REQUIREMENT_CONDITIONAL = "conditional"

STATE_SCOPE_MODULE_INPUT = "module_input"
STATE_SCOPE_MODEL_CONFIG = "model_config"

PARSER_SCALAR = "scalar"
PARSER_LIST = "list"
PARSER_CORNER_GRID = "corner_grid"
PARSER_PROPERTY_ARRAY = "property_array"
PARSER_DFN = "dfn"
PARSER_WELLS = "wells"

VALID_PARSER_KINDS = frozenset((
    PARSER_SCALAR,
    PARSER_LIST,
    PARSER_CORNER_GRID,
    PARSER_PROPERTY_ARRAY,
    PARSER_DFN,
    PARSER_WELLS,
))

WIDGET_NUMBER = "number"
WIDGET_INTEGER = "integer"
WIDGET_BOOLEAN = "boolean"
WIDGET_CHOICE = "choice"
WIDGET_SUMMARY = "summary"
WIDGET_SUMMARY_TABLE = "summary_table"
WIDGET_TABLE = "table"
WIDGET_DERIVED = "derived"


@dataclass(frozen=True)
class BusinessGroupSpec:
    """Stable business grouping rendered below an input-tree module."""

    key: str
    title: str


@dataclass(frozen=True)
class ModuleSpec:
    """Stable business definition for one top-level input-tree node."""

    key: str
    title: str
    accepts_case_keywords: bool = True
    groups: Tuple[BusinessGroupSpec, ...] = ()

    @property
    def reserved_groups(self) -> Tuple[str, ...]:
        """Compatibility view for callers that only need group titles."""

        return tuple(group.title for group in self.groups)


@dataclass(frozen=True)
class KeywordRule:
    """Back-end import policy for one CaseData keyword.

    Keyword rules never directly create widgets.  ``parser_kind`` and
    ``parsed_key`` describe how the source value becomes normalized module
    data; :class:`DisplayFieldRule` independently defines what users see.
    """

    section: str
    keyword: str
    module_key: str
    title: str
    value_type: str = "string"
    importable: bool = True
    parser_kind: str = PARSER_SCALAR
    parsed_key: str = ""
    requirement: str = REQUIREMENT_OPTIONAL
    required_when: Tuple[str, ...] = ()
    state_scope: str = STATE_SCOPE_MODULE_INPUT
    state_key: str = ""
    validation_group: str = ""
    note: str = ""

    @property
    def identity(self) -> Tuple[str, str]:
        return normalize_keyword_identity(self.section, self.keyword)

    @property
    def qualified_name(self) -> str:
        return f"{self.section}.{self.keyword}"


@dataclass(frozen=True)
class ModelConfigFieldRule:
    """One field owned by the reusable model-configuration dialog."""

    key: str
    title: str
    value_type: str
    default: Any
    visible: bool = True
    editable: bool = True
    choices: Tuple[str, ...] = ()
    enabled_when: str = ""
    source_section: str = ""
    source_keyword: str = ""
    note: str = ""

    @property
    def source_identity(self) -> Optional[Tuple[str, str]]:
        if not self.source_section or not self.source_keyword:
            return None
        return normalize_keyword_identity(
            self.source_section, self.source_keyword)


@dataclass(frozen=True)
class DisplayFieldRule:
    """One user-facing field backed by normalized, parsed business data."""

    module_key: str
    key: str
    title: str
    source_path: str
    group: str
    widget_kind: str
    editable: bool = False
    unit: str = ""
    visible_when: str = ""
    columns: Tuple[Tuple[str, str], ...] = ()
    note: str = ""


MODULE_SPECS = (
    ModuleSpec(
        MODULE_MODEL_CONFIGURATION,
        "模型配置",
        groups=(
            BusinessGroupSpec("model_type", "模型类型"),
            BusinessGroupSpec("lgr", "LGR"),
            BusinessGroupSpec("feature_modules", "功能模块"),
            BusinessGroupSpec("wr_data_source", "WR数据来源"),
        ),
    ),
    ModuleSpec(
        MODULE_GRID_SPATIAL,
        "网格与空间数据",
        groups=(
            BusinessGroupSpec("grid_properties", "网格属性"),
            BusinessGroupSpec("porosity_permeability", "孔隙度与渗透率"),
        ),
    ),
    ModuleSpec(
        MODULE_ROCK_PROPERTIES,
        "储层岩石属性",
        groups=(
            BusinessGroupSpec("relative_permeability", "相渗指数"),
            BusinessGroupSpec("fine_analysis", "细部解析"),
            BusinessGroupSpec("sensitivity", "敏感性参数"),
            BusinessGroupSpec("shape_factor", "形状因子"),
        ),
    ),
    ModuleSpec(
        MODULE_FRACTURE_SYSTEM,
        "裂缝系统",
        groups=(
            BusinessGroupSpec("natural_fractures", "天然裂缝"),
            BusinessGroupSpec("equivalent_fracture_properties", "等效裂缝属性"),
            BusinessGroupSpec("hydraulic_fractures", "人工裂缝"),
        ),
    ),
    ModuleSpec(
        MODULE_FLUID_PVT,
        "流体与 PVT",
        groups=(
            BusinessGroupSpec("base_fluid_parameters", "基础流体参数"),
            BusinessGroupSpec("gas_components", "气体组分"),
            BusinessGroupSpec("pvt_table", "PVT表"),
        ),
    ),
    ModuleSpec(
        MODULE_INITIAL_CONDITIONS,
        "初始状态",
        groups=(
            BusinessGroupSpec("initial_pressure", "初始压力"),
            BusinessGroupSpec("initial_saturation", "初始饱和度"),
        ),
    ),
    ModuleSpec(
        MODULE_WELL_PRODUCTION,
        "井与生产控制",
        groups=(
            BusinessGroupSpec("well_trajectory", "井轨迹"),
            BusinessGroupSpec("completion_control", "完井与井控"),
        ),
    ),
    ModuleSpec(
        MODULE_SOLVER_OUTPUT,
        "求解与输出控制",
        groups=(BusinessGroupSpec("time_control", "时间控制"),),
    ),
    ModuleSpec(
        MODULE_HISTORY_MATCHING,
        "历史拟合",
        accepts_case_keywords=False,
    ),
)

MODULE_ORDER = tuple(spec.key for spec in MODULE_SPECS)
MODULE_SPEC_BY_KEY = {spec.key: spec for spec in MODULE_SPECS}


def _rule(section: str, keyword: str, module_key: str, title: str,
          value_type: str = "string", *, parser_kind: str = "",
          parsed_key: str = "",
          requirement: str = REQUIREMENT_OPTIONAL,
          required_when: Iterable[str] = (),
          state_scope: str = STATE_SCOPE_MODULE_INPUT,
          state_key: str = "", validation_group: str = "",
          note: str = "") -> KeywordRule:
    return KeywordRule(
        section=section,
        keyword=keyword,
        module_key=module_key,
        title=title,
        value_type=value_type,
        parser_kind=parser_kind or (
            PARSER_LIST if value_type == "list" else PARSER_SCALAR),
        parsed_key=parsed_key or state_key or str(keyword).lower(),
        requirement=requirement,
        required_when=tuple(required_when),
        state_scope=state_scope,
        state_key=state_key or keyword,
        validation_group=validation_group,
        note=note,
    )


KEYWORD_RULES = (
    # Model configuration: importable from CaseData and manually editable.
    _rule(
        "LGR", "enable_lgr", MODULE_MODEL_CONFIGURATION, "启用 LGR", "bool",
        state_scope=STATE_SCOPE_MODEL_CONFIG, state_key="enable_lgr",
    ),
    _rule(
        "LGR", "d_threshold", MODULE_MODEL_CONFIGURATION,
        "距离阈值 d_threshold", "float",
        requirement=REQUIREMENT_CONDITIONAL,
        required_when=("enable_lgr",),
        state_scope=STATE_SCOPE_MODEL_CONFIG,
        state_key="lgr_d_threshold",
    ),
    _rule(
        "LGR", "nrx", MODULE_MODEL_CONFIGURATION, "X 向加密数 nrx", "int",
        requirement=REQUIREMENT_CONDITIONAL,
        required_when=("enable_lgr",),
        state_scope=STATE_SCOPE_MODEL_CONFIG, state_key="lgr_nrx",
    ),
    _rule(
        "LGR", "nry", MODULE_MODEL_CONFIGURATION, "Y 向加密数 nry", "int",
        requirement=REQUIREMENT_CONDITIONAL,
        required_when=("enable_lgr",),
        state_scope=STATE_SCOPE_MODEL_CONFIG, state_key="lgr_nry",
    ),
    _rule(
        "LGR", "nrz", MODULE_MODEL_CONFIGURATION, "Z 向加密数 nrz", "int",
        requirement=REQUIREMENT_CONDITIONAL,
        required_when=("enable_lgr",),
        state_scope=STATE_SCOPE_MODEL_CONFIG, state_key="lgr_nrz",
    ),

    # Grid and matrix property arrays are one business input module even
    # though the property references physically live in [ROCK].
    _rule(
        "GRID", "grid_file", MODULE_GRID_SPATIAL, "网格文件", "path",
        parser_kind=PARSER_CORNER_GRID, parsed_key="grid",
        requirement=REQUIREMENT_REQUIRED,
    ),
    _rule(
        "ROCK", "matrix_phi_file", MODULE_GRID_SPATIAL, "基质孔隙度", "path",
        parser_kind=PARSER_PROPERTY_ARRAY, parsed_key="matrix_phi",
        requirement=REQUIREMENT_REQUIRED,
    ),
    _rule(
        "ROCK", "matrix_kx_file", MODULE_GRID_SPATIAL, "基质 Kx", "path",
        parser_kind=PARSER_PROPERTY_ARRAY, parsed_key="matrix_kx",
        requirement=REQUIREMENT_REQUIRED,
    ),
    _rule(
        "ROCK", "matrix_ky_file", MODULE_GRID_SPATIAL, "基质 Ky", "path",
        parser_kind=PARSER_PROPERTY_ARRAY, parsed_key="matrix_ky",
        requirement=REQUIREMENT_REQUIRED,
    ),
    _rule(
        "ROCK", "matrix_kz_file", MODULE_GRID_SPATIAL, "基质 Kz", "path",
        parser_kind=PARSER_PROPERTY_ARRAY, parsed_key="matrix_kz",
        requirement=REQUIREMENT_REQUIRED,
    ),

    # Rock-mechanics/business properties.  Future detailed-analysis and
    # sensitivity keywords must be added only when their real names exist.
    _rule("FLUID", "n", MODULE_ROCK_PROPERTIES, "相渗指数 n", "float"),
    _rule(
        "WR", "sigma_file", MODULE_ROCK_PROPERTIES, "形状因子 sigma", "path",
        parser_kind=PARSER_PROPERTY_ARRAY, parsed_key="shape_factor",
        requirement=REQUIREMENT_CONDITIONAL,
        required_when=("model_type=wr", "wr_input_mode=file"),
    ),

    # All fracture information belongs to the fracture module regardless of
    # whether its source keyword is under [ROCK] or [FRACTURE].
    _rule(
        "FRACTURE", "fracture_file", MODULE_FRACTURE_SYSTEM,
        "天然裂缝 DFN", "path",
        parser_kind=PARSER_DFN, parsed_key="natural_fractures",
        requirement=REQUIREMENT_CONDITIONAL,
        required_when=("enable_natural_fractures",),
    ),
    _rule(
        "ROCK", "fracture_phi_file", MODULE_FRACTURE_SYSTEM,
        "等效裂缝孔隙度", "path",
        parser_kind=PARSER_PROPERTY_ARRAY, parsed_key="fracture_phi",
        requirement=REQUIREMENT_CONDITIONAL,
        required_when=("model_type=wr", "wr_input_mode=file"),
    ),
    _rule(
        "ROCK", "fracture_kx_file", MODULE_FRACTURE_SYSTEM,
        "等效裂缝 Kx", "path",
        parser_kind=PARSER_PROPERTY_ARRAY, parsed_key="fracture_kx",
        requirement=REQUIREMENT_CONDITIONAL,
        required_when=("model_type=wr", "wr_input_mode=file"),
    ),
    _rule(
        "ROCK", "fracture_ky_file", MODULE_FRACTURE_SYSTEM,
        "等效裂缝 Ky", "path",
        parser_kind=PARSER_PROPERTY_ARRAY, parsed_key="fracture_ky",
        requirement=REQUIREMENT_CONDITIONAL,
        required_when=("model_type=wr", "wr_input_mode=file"),
    ),
    _rule(
        "ROCK", "fracture_kz_file", MODULE_FRACTURE_SYSTEM,
        "等效裂缝 Kz", "path",
        parser_kind=PARSER_PROPERTY_ARRAY, parsed_key="fracture_kz",
        requirement=REQUIREMENT_CONDITIONAL,
        required_when=("model_type=wr", "wr_input_mode=file"),
    ),

    # Fluid and PVT.  FLUID.n is intentionally owned by rock_properties.
    _rule("FLUID", "mu_w", MODULE_FLUID_PVT, "水相黏度 mu_w", "float"),
    _rule("FLUID", "mu_o", MODULE_FLUID_PVT, "油相黏度 mu_o", "float"),
    _rule("FLUID", "cw", MODULE_FLUID_PVT, "水相压缩系数 cw", "float"),
    _rule("FLUID", "co", MODULE_FLUID_PVT, "油相压缩系数 co", "float"),
    _rule("FLUID", "p_ref", MODULE_FLUID_PVT, "参考压力 p_ref", "float"),
    _rule("FLUID", "Swi", MODULE_FLUID_PVT, "束缚水饱和度 Swi", "float"),
    _rule("FLUID", "Sor", MODULE_FLUID_PVT, "残余油饱和度 Sor", "float"),
    _rule("FLUID", "Sgc", MODULE_FLUID_PVT, "临界气饱和度 Sgc", "float"),
    _rule("GAS", "temperature_C", MODULE_FLUID_PVT, "气藏温度", "float"),
    _rule(
        "GAS", "mole_CH4", MODULE_FLUID_PVT, "CH4 摩尔分数", "float",
        validation_group="gas_mole_fraction",
    ),
    _rule(
        "GAS", "mole_C2H6", MODULE_FLUID_PVT, "C2H6 摩尔分数", "float",
        validation_group="gas_mole_fraction",
    ),
    _rule(
        "GAS", "mole_C3H8", MODULE_FLUID_PVT, "C3H8 摩尔分数", "float",
        validation_group="gas_mole_fraction",
    ),
    _rule(
        "GAS", "mole_N2", MODULE_FLUID_PVT, "N2 摩尔分数", "float",
        validation_group="gas_mole_fraction",
    ),
    _rule(
        "GAS", "mole_CO2", MODULE_FLUID_PVT, "CO2 摩尔分数", "float",
        validation_group="gas_mole_fraction",
    ),
    _rule(
        "GAS", "mole_H2O", MODULE_FLUID_PVT, "H2O 摩尔分数", "float",
        validation_group="gas_mole_fraction",
    ),
    _rule(
        "GAS", "mole_unknown", MODULE_FLUID_PVT, "其他组分摩尔分数", "float",
        validation_group="gas_mole_fraction",
    ),
    _rule(
        "GAS", "gas_table_Pmin_bar", MODULE_FLUID_PVT,
        "PVT 最小压力", "float", validation_group="gas_pvt_range",
    ),
    _rule(
        "GAS", "gas_table_Pmax_bar", MODULE_FLUID_PVT,
        "PVT 最大压力", "float", validation_group="gas_pvt_range",
    ),
    _rule(
        "GAS", "gas_table_n", MODULE_FLUID_PVT,
        "PVT 采样点数", "int", validation_group="gas_pvt_range",
    ),

    # Initial state.  So is derived and therefore is not a registered input.
    _rule(
        "INITIAL", "pressure", MODULE_INITIAL_CONDITIONS, "初始压力", "float"
    ),
    _rule(
        "INITIAL", "Sw", MODULE_INITIAL_CONDITIONS, "初始含水饱和度", "float",
        validation_group="initial_saturation",
    ),
    _rule(
        "INITIAL", "Sg", MODULE_INITIAL_CONDITIONS, "初始含气饱和度", "float",
        validation_group="initial_saturation",
    ),

    # Well input follows the files actually supplied by uniform_data111.txt.
    _rule(
        "WELL", "well_track_file", MODULE_WELL_PRODUCTION, "井轨迹数据", "path",
        parser_kind=PARSER_WELLS, parsed_key="wells",
        validation_group="well_files",
    ),
    _rule(
        "WELL", "well_completion_file", MODULE_WELL_PRODUCTION,
        "完井与井控数据", "path",
        parser_kind=PARSER_WELLS, parsed_key="wells",
        validation_group="well_files",
    ),

    # Only four time-control fields are visible.  The remaining solver and
    # output values are imported and retained without appearing in the normal
    # parameter dialog.
    _rule("SOLVER", "total_time", MODULE_SOLVER_OUTPUT, "总模拟时间", "float"),
    _rule("SOLVER", "dt_init", MODULE_SOLVER_OUTPUT, "初始时间步", "float"),
    _rule("SOLVER", "dt_min", MODULE_SOLVER_OUTPUT, "最小时间步", "float"),
    _rule("SOLVER", "dt_max", MODULE_SOLVER_OUTPUT, "最大时间步", "float"),
    _rule(
        "SOLVER", "newton_max_iter", MODULE_SOLVER_OUTPUT,
        "Newton 最大迭代数", "int",
    ),
    _rule(
        "SOLVER", "newton_tol", MODULE_SOLVER_OUTPUT,
        "Newton 收敛容差", "float",
    ),
    _rule(
        "SOLVER", "linear_tol", MODULE_SOLVER_OUTPUT,
        "线性求解容差", "float",
    ),
    _rule(
        "SOLVER", "linear_max_iter", MODULE_SOLVER_OUTPUT,
        "线性求解最大迭代数", "int",
    ),
    _rule(
        "SOLVER", "dt_cut_factor", MODULE_SOLVER_OUTPUT,
        "时间步缩小系数", "float",
    ),
    _rule(
        "SOLVER", "dt_grow_factor", MODULE_SOLVER_OUTPUT,
        "时间步增长系数", "float",
    ),
    _rule(
        "SOLVER", "max_timestep_retry", MODULE_SOLVER_OUTPUT,
        "时间步最大重试数", "int",
    ),
    _rule(
        "OUTPUT", "field_output_times", MODULE_SOLVER_OUTPUT,
        "空间场输出时间", "list",
        note="当前算法尚未接入；导入并保留但不在普通弹窗展示。",
    ),
)


MODEL_CONFIG_FIELD_RULES = (
    ModelConfigFieldRule(
        "model_type", "模型类型", "choice", "normal",
        choices=("normal", "wr"),
    ),
    ModelConfigFieldRule(
        "grid_type", "网格类型", "choice", "corner_point",
        visible=False, editable=False, choices=("corner_point",),
    ),
    ModelConfigFieldRule(
        "enable_lgr", "启用 LGR", "bool", True,
        source_section="LGR", source_keyword="enable_lgr",
    ),
    ModelConfigFieldRule(
        "lgr_d_threshold", "距离阈值 d_threshold", "float", 5.05,
        enabled_when="enable_lgr",
        source_section="LGR", source_keyword="d_threshold",
    ),
    ModelConfigFieldRule(
        "lgr_nrx", "X 向加密数 nrx", "int", 2,
        enabled_when="enable_lgr", source_section="LGR", source_keyword="nrx",
    ),
    ModelConfigFieldRule(
        "lgr_nry", "Y 向加密数 nry", "int", 2,
        enabled_when="enable_lgr", source_section="LGR", source_keyword="nry",
    ),
    ModelConfigFieldRule(
        "lgr_nrz", "Z 向加密数 nrz", "int", 2,
        enabled_when="enable_lgr", source_section="LGR", source_keyword="nrz",
    ),
    ModelConfigFieldRule(
        "enable_natural_fractures", "天然裂缝 DFN", "bool", True,
    ),
    ModelConfigFieldRule(
        "enable_hydraulic_fractures", "人工裂缝", "bool", False,
    ),
    ModelConfigFieldRule(
        "enable_real_gas_pvt", "真实气体 PVT", "bool", True,
    ),
    ModelConfigFieldRule(
        "wr_input_mode", "WR 数据来源", "choice", "file",
        choices=("file", "constant", "mixed"), enabled_when="model_type=wr",
    ),
    ModelConfigFieldRule(
        "confirmed", "模型配置已确认", "bool", False,
        visible=False, editable=False,
    ),
)


def _display(module_key: str, key: str, title: str, source_path: str,
             group: str, widget_kind: str, *, editable: bool = False,
             unit: str = "", visible_when: str = "",
             columns: Iterable[Tuple[str, str]] = (),
             note: str = "") -> DisplayFieldRule:
    return DisplayFieldRule(
        module_key=module_key,
        key=key,
        title=title,
        source_path=source_path,
        group=group,
        widget_kind=widget_kind,
        editable=editable,
        unit=unit,
        visible_when=visible_when,
        columns=tuple(columns),
        note=note,
    )


PROPERTY_SUMMARY_COLUMNS = (
    ("count", "总数量"),
    ("valid_count", "有效值"),
    ("null_count", "空值"),
    ("min", "最小值"),
    ("max", "最大值"),
    ("mean", "平均值"),
)

FRACTURE_STAT_COLUMNS = (
    ("count", "数量"),
    ("min", "最小值"),
    ("max", "最大值"),
    ("mean", "平均值"),
)

DISPLAY_FIELD_RULES = (
    # Grid and matrix-property content.  These are parsed values and
    # summaries; source filenames and keyword raw values are intentionally
    # absent from this registry.
    _display(MODULE_GRID_SPATIAL, "grid_nx", "Nx", "grid.nx",
             "网格属性", WIDGET_INTEGER),
    _display(MODULE_GRID_SPATIAL, "grid_ny", "Ny", "grid.ny",
             "网格属性", WIDGET_INTEGER),
    _display(MODULE_GRID_SPATIAL, "grid_nz", "Nz", "grid.nz",
             "网格属性", WIDGET_INTEGER),
    _display(MODULE_GRID_SPATIAL, "total_cell_count", "总网格数",
             "grid.total_cell_count", "网格属性", WIDGET_INTEGER),
    _display(MODULE_GRID_SPATIAL, "active_cell_count", "活跃网格数",
             "grid.active_cell_count", "网格属性", WIDGET_INTEGER),
    _display(MODULE_GRID_SPATIAL, "inactive_cell_count", "非活跃网格数",
             "grid.inactive_cell_count", "网格属性", WIDGET_INTEGER),
    _display(MODULE_GRID_SPATIAL, "grid_bbox_min", "坐标范围最小点",
             "grid.bbox_min", "网格属性", WIDGET_SUMMARY),
    _display(MODULE_GRID_SPATIAL, "grid_bbox_max", "坐标范围最大点",
             "grid.bbox_max", "网格属性", WIDGET_SUMMARY),
    _display(MODULE_GRID_SPATIAL, "coord_value_count", "COORD 数值数量",
             "grid.coord_value_count", "网格属性", WIDGET_INTEGER),
    _display(MODULE_GRID_SPATIAL, "zcorn_value_count", "ZCORN 数值数量",
             "grid.zcorn_value_count", "网格属性", WIDGET_INTEGER),
    _display(MODULE_GRID_SPATIAL, "actnum_value_count", "ACTNUM 数值数量",
             "grid.actnum_value_count", "网格属性", WIDGET_INTEGER),
    _display(MODULE_GRID_SPATIAL, "matrix_phi_summary", "基质孔隙度",
             "matrix_phi.summary", "孔隙度与渗透率", WIDGET_SUMMARY_TABLE,
             columns=PROPERTY_SUMMARY_COLUMNS),
    _display(MODULE_GRID_SPATIAL, "matrix_kx_summary", "基质 Kx",
             "matrix_kx.summary", "孔隙度与渗透率", WIDGET_SUMMARY_TABLE,
             columns=PROPERTY_SUMMARY_COLUMNS, unit="mD"),
    _display(MODULE_GRID_SPATIAL, "matrix_ky_summary", "基质 Ky",
             "matrix_ky.summary", "孔隙度与渗透率", WIDGET_SUMMARY_TABLE,
             columns=PROPERTY_SUMMARY_COLUMNS, unit="mD"),
    _display(MODULE_GRID_SPATIAL, "matrix_kz_summary", "基质 Kz",
             "matrix_kz.summary", "孔隙度与渗透率", WIDGET_SUMMARY_TABLE,
             columns=PROPERTY_SUMMARY_COLUMNS, unit="mD"),

    # Rock properties.
    _display(MODULE_ROCK_PROPERTIES, "relperm_exponent_n", "相渗指数 n", "n",
             "相渗指数", WIDGET_NUMBER, editable=True),
    _display(MODULE_ROCK_PROPERTIES, "shape_factor_summary", "形状因子",
             "shape_factor.summary", "形状因子", WIDGET_SUMMARY_TABLE,
             columns=PROPERTY_SUMMARY_COLUMNS),

    # Natural, equivalent and future hydraulic-fracture business content.
    _display(MODULE_FRACTURE_SYSTEM, "natural_fracture_summary", "天然裂缝概况",
             "natural_fractures.summary", "天然裂缝", WIDGET_SUMMARY),
    _display(MODULE_FRACTURE_SYSTEM, "natural_fracture_bbox_min", "包围盒最小点",
             "natural_fractures.summary.bbox_min", "天然裂缝", WIDGET_SUMMARY),
    _display(MODULE_FRACTURE_SYSTEM, "natural_fracture_bbox_max", "包围盒最大点",
             "natural_fractures.summary.bbox_max", "天然裂缝", WIDGET_SUMMARY),
    _display(MODULE_FRACTURE_SYSTEM, "natural_fracture_sets", "裂缝集合",
             "natural_fractures.sets", "天然裂缝", WIDGET_TABLE,
             columns=(("set_id", "集合ID"), ("set_name", "集合名称"))),
    _display(MODULE_FRACTURE_SYSTEM, "natural_fracture_perm", "渗透率统计",
             "natural_fractures.summary.permeability", "天然裂缝",
             WIDGET_SUMMARY_TABLE, columns=FRACTURE_STAT_COLUMNS, unit="mD"),
    _display(MODULE_FRACTURE_SYSTEM, "natural_fracture_compressibility",
             "压缩系数统计", "natural_fractures.summary.compressibility",
             "天然裂缝", WIDGET_SUMMARY_TABLE,
             columns=FRACTURE_STAT_COLUMNS),
    _display(MODULE_FRACTURE_SYSTEM, "natural_fracture_aperture", "开度统计",
             "natural_fractures.summary.aperture", "天然裂缝",
             WIDGET_SUMMARY_TABLE, columns=FRACTURE_STAT_COLUMNS, unit="m"),
    _display(MODULE_FRACTURE_SYSTEM, "natural_fracture_table", "天然裂缝列表",
             "natural_fractures.fractures", "天然裂缝", WIDGET_TABLE,
             columns=(("fracture_id", "裂缝ID"), ("vertex_count", "顶点数"),
                      ("set_id", "集合"), ("permeability", "渗透率"),
                      ("compressibility", "压缩系数"),
                      ("aperture", "开度"))),
    _display(MODULE_FRACTURE_SYSTEM, "fracture_phi_summary", "等效裂缝孔隙度",
             "fracture_phi.summary", "等效裂缝属性", WIDGET_SUMMARY_TABLE,
             columns=PROPERTY_SUMMARY_COLUMNS),
    _display(MODULE_FRACTURE_SYSTEM, "fracture_kx_summary", "等效裂缝 Kx",
             "fracture_kx.summary", "等效裂缝属性", WIDGET_SUMMARY_TABLE,
             columns=PROPERTY_SUMMARY_COLUMNS, unit="mD"),
    _display(MODULE_FRACTURE_SYSTEM, "fracture_ky_summary", "等效裂缝 Ky",
             "fracture_ky.summary", "等效裂缝属性", WIDGET_SUMMARY_TABLE,
             columns=PROPERTY_SUMMARY_COLUMNS, unit="mD"),
    _display(MODULE_FRACTURE_SYSTEM, "fracture_kz_summary", "等效裂缝 Kz",
             "fracture_kz.summary", "等效裂缝属性", WIDGET_SUMMARY_TABLE,
             columns=PROPERTY_SUMMARY_COLUMNS, unit="mD"),
    _display(MODULE_FRACTURE_SYSTEM, "hydraulic_fractures", "人工裂缝参数",
             "hydraulic_fractures", "人工裂缝", WIDGET_TABLE, editable=True,
             visible_when="enable_hydraulic_fractures",
             columns=(("fracture_id", "裂缝ID"), ("well_name", "井名"),
                      ("stage", "压裂段"), ("center_x", "中心X"),
                      ("center_y", "中心Y"), ("center_z", "中心Z"),
                      ("length", "裂缝长度"), ("height", "缝高"),
                      ("aperture", "开度"), ("perm", "渗透率"),
                      ("conductivity", "导流能力"))),

    # Fluid and PVT scalar content.
    _display(MODULE_FLUID_PVT, "mu_w", "水相黏度", "mu_w",
             "基础流体参数", WIDGET_NUMBER, editable=True, unit="cP"),
    _display(MODULE_FLUID_PVT, "mu_o", "油相黏度", "mu_o",
             "基础流体参数", WIDGET_NUMBER, editable=True, unit="cP"),
    _display(MODULE_FLUID_PVT, "cw", "水相压缩系数", "cw",
             "基础流体参数", WIDGET_NUMBER, editable=True),
    _display(MODULE_FLUID_PVT, "co", "油相压缩系数", "co",
             "基础流体参数", WIDGET_NUMBER, editable=True),
    _display(MODULE_FLUID_PVT, "p_ref", "参考压力", "p_ref",
             "基础流体参数", WIDGET_NUMBER, editable=True),
    _display(MODULE_FLUID_PVT, "swi", "束缚水饱和度", "swi",
             "基础流体参数", WIDGET_NUMBER, editable=True),
    _display(MODULE_FLUID_PVT, "sor", "残余油饱和度", "sor",
             "基础流体参数", WIDGET_NUMBER, editable=True),
    _display(MODULE_FLUID_PVT, "sgc", "临界气饱和度", "sgc",
             "基础流体参数", WIDGET_NUMBER, editable=True),
    _display(MODULE_FLUID_PVT, "temperature_c", "气藏温度", "temperature_c",
             "气体组分", WIDGET_NUMBER, editable=True, unit="°C"),
    _display(MODULE_FLUID_PVT, "mole_ch4", "CH4 摩尔分数", "mole_ch4",
             "气体组分", WIDGET_NUMBER, editable=True),
    _display(MODULE_FLUID_PVT, "mole_c2h6", "C2H6 摩尔分数", "mole_c2h6",
             "气体组分", WIDGET_NUMBER, editable=True),
    _display(MODULE_FLUID_PVT, "mole_c3h8", "C3H8 摩尔分数", "mole_c3h8",
             "气体组分", WIDGET_NUMBER, editable=True),
    _display(MODULE_FLUID_PVT, "mole_n2", "N2 摩尔分数", "mole_n2",
             "气体组分", WIDGET_NUMBER, editable=True),
    _display(MODULE_FLUID_PVT, "mole_co2", "CO2 摩尔分数", "mole_co2",
             "气体组分", WIDGET_NUMBER, editable=True),
    _display(MODULE_FLUID_PVT, "mole_h2o", "H2O 摩尔分数", "mole_h2o",
             "气体组分", WIDGET_NUMBER, editable=True),
    _display(MODULE_FLUID_PVT, "mole_unknown", "其他组分摩尔分数",
             "mole_unknown", "气体组分", WIDGET_NUMBER, editable=True),
    _display(MODULE_FLUID_PVT, "mole_fraction_sum", "组分总和",
             "derived.mole_fraction_sum", "气体组分", WIDGET_DERIVED),
    _display(MODULE_FLUID_PVT, "gas_table_pmin_bar", "PVT 最小压力",
             "gas_table_pmin_bar", "PVT表", WIDGET_NUMBER,
             editable=True, unit="bar"),
    _display(MODULE_FLUID_PVT, "gas_table_pmax_bar", "PVT 最大压力",
             "gas_table_pmax_bar", "PVT表", WIDGET_NUMBER,
             editable=True, unit="bar"),
    _display(MODULE_FLUID_PVT, "gas_table_n", "PVT 采样点数", "gas_table_n",
             "PVT表", WIDGET_INTEGER, editable=True),

    # Initial state.
    _display(MODULE_INITIAL_CONDITIONS, "initial_pressure", "初始压力",
             "pressure", "初始压力", WIDGET_NUMBER, editable=True),
    _display(MODULE_INITIAL_CONDITIONS, "initial_sw", "初始含水饱和度",
             "sw", "初始饱和度", WIDGET_NUMBER, editable=True),
    _display(MODULE_INITIAL_CONDITIONS, "initial_sg", "初始含气饱和度",
             "sg", "初始饱和度", WIDGET_NUMBER, editable=True),
    _display(MODULE_INITIAL_CONDITIONS, "initial_so", "初始含油饱和度",
             "derived.so", "初始饱和度", WIDGET_DERIVED),

    # Parsed well content rather than the two source locators.
    _display(MODULE_WELL_PRODUCTION, "well_summary", "井概况", "wells.summary",
             "井轨迹", WIDGET_SUMMARY),
    _display(MODULE_WELL_PRODUCTION, "well_list", "井列表", "wells.well_list",
             "井轨迹", WIDGET_TABLE,
             columns=(("well_name", "井名"), ("well_type", "井类型"),
                      ("track_point_count", "轨迹点数"),
                      ("md_min", "起始MD"), ("md_max", "终止MD"))),
    _display(MODULE_WELL_PRODUCTION, "well_tracks", "井轨迹",
             "wells.tracks", "井轨迹", WIDGET_TABLE, editable=True,
             columns=(("well_name", "井名"), ("md_m", "MD"),
                      ("x_m", "X"), ("y_m", "Y"), ("z_m", "Z"))),
    _display(MODULE_WELL_PRODUCTION, "well_completions", "完井与井控",
             "wells.completions", "完井与井控", WIDGET_TABLE, editable=True,
             columns=(("well_name", "井名"), ("date", "日期"),
                      ("event", "事件"), ("comp_id", "完井段"),
                      ("md_top_m", "MD顶部"), ("md_bottom_m", "MD底部"),
                      ("rw_m", "井半径"), ("control_type", "控制方式"),
                      ("bhp_bar", "BHP"),
                      ("connection_target", "连接对象"))),

    # The solver owns more imported values, but the normal dialog exposes only
    # the four confirmed time-control parameters.
    _display(MODULE_SOLVER_OUTPUT, "total_time", "总模拟时间", "total_time",
             "时间控制", WIDGET_NUMBER, editable=True),
    _display(MODULE_SOLVER_OUTPUT, "dt_init", "初始时间步", "dt_init",
             "时间控制", WIDGET_NUMBER, editable=True),
    _display(MODULE_SOLVER_OUTPUT, "dt_min", "最小时间步", "dt_min",
             "时间控制", WIDGET_NUMBER, editable=True),
    _display(MODULE_SOLVER_OUTPUT, "dt_max", "最大时间步", "dt_max",
             "时间控制", WIDGET_NUMBER, editable=True),
)


IGNORED_CASE_SECTIONS = frozenset(("RETURN_SCHEMA",))


def normalize_keyword_identity(section: str, keyword: str) -> Tuple[str, str]:
    """Return the case-insensitive identity used by all registry lookups."""

    return (
        str(section or "").strip().upper(),
        str(keyword or "").strip().lower(),
    )


KEYWORD_RULE_BY_IDENTITY: Dict[Tuple[str, str], KeywordRule] = {
    rule.identity: rule for rule in KEYWORD_RULES
}
MODEL_CONFIG_FIELD_BY_KEY: Dict[str, ModelConfigFieldRule] = {
    field.key: field for field in MODEL_CONFIG_FIELD_RULES
}
DISPLAY_FIELD_BY_IDENTITY: Dict[Tuple[str, str], DisplayFieldRule] = {
    (field.module_key, field.key): field for field in DISPLAY_FIELD_RULES
}


def get_module_spec(module_key: str) -> Optional[ModuleSpec]:
    return MODULE_SPEC_BY_KEY.get(str(module_key or ""))


def get_keyword_rule(section: str, keyword: str) -> Optional[KeywordRule]:
    return KEYWORD_RULE_BY_IDENTITY.get(
        normalize_keyword_identity(section, keyword))


def get_model_config_field(key: str) -> Optional[ModelConfigFieldRule]:
    return MODEL_CONFIG_FIELD_BY_KEY.get(str(key or ""))


def get_display_field(module_key: str, key: str) -> Optional[DisplayFieldRule]:
    return DISPLAY_FIELD_BY_IDENTITY.get(
        (str(module_key or ""), str(key or "")))


def keyword_rules_for_module(module_key: str, *,
                             importable_only: bool = False) -> Tuple[KeywordRule, ...]:
    """Return rules owned by a module while preserving registry order."""

    rules = []
    for rule in KEYWORD_RULES:
        if rule.module_key != module_key:
            continue
        if importable_only and not rule.importable:
            continue
        rules.append(rule)
    return tuple(rules)


def display_fields_for_module(module_key: str) -> Tuple[DisplayFieldRule, ...]:
    """Return user-facing business fields while preserving display order."""

    return tuple(
        field for field in DISPLAY_FIELD_RULES
        if field.module_key == module_key
    )


def is_ignored_case_section(section: str) -> bool:
    return str(section or "").strip().upper() in IGNORED_CASE_SECTIONS


def registry_issues() -> Tuple[str, ...]:
    """Return structural problems without performing business validation."""

    issues = []
    module_keys = [spec.key for spec in MODULE_SPECS]
    if len(module_keys) != len(set(module_keys)):
        issues.append("duplicate module key")
    for spec in MODULE_SPECS:
        group_keys = [group.key for group in spec.groups]
        group_titles = [group.title for group in spec.groups]
        if len(group_keys) != len(set(group_keys)):
            issues.append(f"duplicate business-group key: {spec.key}")
        if len(group_titles) != len(set(group_titles)):
            issues.append(f"duplicate business-group title: {spec.key}")

    field_keys = [field.key for field in MODEL_CONFIG_FIELD_RULES]
    if len(field_keys) != len(set(field_keys)):
        issues.append("duplicate model-config field key")

    seen_identities = set()
    valid_requirements = {
        REQUIREMENT_REQUIRED,
        REQUIREMENT_OPTIONAL,
        REQUIREMENT_CONDITIONAL,
    }
    for rule in KEYWORD_RULES:
        if rule.identity in seen_identities:
            issues.append(f"duplicate keyword identity: {rule.qualified_name}")
        seen_identities.add(rule.identity)

        module = MODULE_SPEC_BY_KEY.get(rule.module_key)
        if module is None:
            issues.append(
                f"unknown module {rule.module_key}: {rule.qualified_name}")
        elif not module.accepts_case_keywords:
            issues.append(
                f"module rejects CaseData keywords: {rule.module_key}")

        if rule.requirement not in valid_requirements:
            issues.append(
                f"invalid requirement {rule.requirement}: {rule.qualified_name}")
        if (rule.requirement == REQUIREMENT_CONDITIONAL and
                not rule.required_when):
            issues.append(
                f"conditional keyword lacks condition: {rule.qualified_name}")
        if rule.parser_kind not in VALID_PARSER_KINDS:
            issues.append(
                f"invalid parser kind {rule.parser_kind}: {rule.qualified_name}")
        if not rule.parsed_key:
            issues.append(f"missing parsed target: {rule.qualified_name}")
        if (rule.value_type == "path" and
                rule.parser_kind in {PARSER_SCALAR, PARSER_LIST}):
            issues.append(
                f"path keyword lacks content parser: {rule.qualified_name}")
        if rule.state_scope == STATE_SCOPE_MODEL_CONFIG:
            field = MODEL_CONFIG_FIELD_BY_KEY.get(rule.state_key)
            if field is None:
                issues.append(
                    f"missing model-config target {rule.state_key}: "
                    f"{rule.qualified_name}")
            elif field.source_identity != rule.identity:
                issues.append(
                    f"model-config source mismatch: {rule.qualified_name}")

    for field in MODEL_CONFIG_FIELD_RULES:
        if field.source_identity is None:
            continue
        source_rule = KEYWORD_RULE_BY_IDENTITY.get(field.source_identity)
        if source_rule is None:
            issues.append(f"missing source keyword for model-config field {field.key}")
        elif source_rule.state_scope != STATE_SCOPE_MODEL_CONFIG:
            issues.append(f"invalid source scope for model-config field {field.key}")
        elif source_rule.state_key != field.key:
            issues.append(f"source target mismatch for model-config field {field.key}")

    valid_widgets = {
        WIDGET_NUMBER,
        WIDGET_INTEGER,
        WIDGET_BOOLEAN,
        WIDGET_CHOICE,
        WIDGET_SUMMARY,
        WIDGET_SUMMARY_TABLE,
        WIDGET_TABLE,
        WIDGET_DERIVED,
    }
    parsed_roots_by_module = {}
    for rule in KEYWORD_RULES:
        root = rule.parsed_key.split(".", 1)[0]
        parsed_roots_by_module.setdefault(rule.module_key, set()).add(root)
    virtual_display_roots = {
        "derived",
        # Artificial-fracture display is reserved for future real keywords or
        # manually entered structured parameters.
        "hydraulic_fractures",
    }
    seen_display_identities = set()
    for field in DISPLAY_FIELD_RULES:
        identity = (field.module_key, field.key)
        if identity in seen_display_identities:
            issues.append(
                f"duplicate display field: {field.module_key}.{field.key}")
        seen_display_identities.add(identity)
        if field.module_key not in MODULE_SPEC_BY_KEY:
            issues.append(
                f"unknown display module: {field.module_key}.{field.key}")
        else:
            group_titles = set(
                MODULE_SPEC_BY_KEY[field.module_key].reserved_groups)
            if field.group not in group_titles:
                issues.append(
                    f"unknown display group: "
                    f"{field.module_key}.{field.key} -> {field.group}")
        if not field.source_path:
            issues.append(
                f"missing display source: {field.module_key}.{field.key}")
        source_root = field.source_path.split(".", 1)[0]
        if (source_root not in parsed_roots_by_module.get(field.module_key, set())
                and source_root not in virtual_display_roots):
            issues.append(
                f"display source has no parsed producer: "
                f"{field.module_key}.{field.key} -> {field.source_path}")
        if field.widget_kind not in valid_widgets:
            issues.append(
                f"invalid widget kind {field.widget_kind}: "
                f"{field.module_key}.{field.key}")
        searchable_text = " ".join((
            field.key, field.title, field.source_path)).lower()
        if "_file" in searchable_text or "文件路径" in searchable_text:
            issues.append(
                f"source-file information leaked into display field: "
                f"{field.module_key}.{field.key}")

    return tuple(issues)


def assert_registry_valid() -> None:
    issues = registry_issues()
    if issues:
        raise RuntimeError("Invalid input keyword registry: " + "; ".join(issues))


assert_registry_valid()
