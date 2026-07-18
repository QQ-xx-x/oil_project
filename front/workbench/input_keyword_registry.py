# -*- coding: utf-8 -*-
"""工作台输入关键字的规范业务归属规则。本模块刻意不包含 Qt 代码，也不执行文件 I/O。它是导入、展示、校验、同步和 CaseData 组合代码共享的契约，调用方应查询本模块，而不是维护各自的关键字列表。关键字标识按 `(section, keyword)` 进行不区分大小写的匹配；`KeywordRule` 中保留的原始拼写用于展示和导出组合后的 CaseData 快照。"""

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
    """显示在输入树模块下的稳定业务分组。"""

    key: str
    title: str


@dataclass(frozen=True)
class ModuleSpec:
    """一个顶层输入树节点的稳定业务定义。"""

    key: str
    title: str
    accepts_case_keywords: bool = True
    groups: Tuple[BusinessGroupSpec, ...] = ()

    @property
    def reserved_groups(self) -> Tuple[str, ...]:
        """为仅需要分组标题的调用方提供兼容视图。"""

        return tuple(group.title for group in self.groups)


@dataclass(frozen=True)
class KeywordRule:
    """单个 CaseData 关键字的后端导入策略。关键字规则不会直接创建控件；`parser_kind` 和 `parsed_key` 描述源值如何转换为规范化模块数据，`DisplayFieldRule` 则独立定义用户看到的内容。"""

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
    """可复用模型配置对话框所属的一个字段。"""

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
    """由规范化、已解析业务数据支持的一个用户可见字段。"""

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
        # 模型配置使用独立对话框，输入树中保持为单一叶子节点。
        groups=(),
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
        "岩石物理属性",
        groups=(
            BusinessGroupSpec("relative_permeability", "相渗指数"),
            BusinessGroupSpec("fine_analysis", "吸附解析"),
            BusinessGroupSpec("sensitivity", "应力敏感"),
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
    # 模型配置：可从 CaseData 导入，也可手动编辑。
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

    # 网格和基质属性数组归属同一个业务输入模块，尽管
    # 属性引用实际位于 [ROCK] 数据段中。
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

    # 岩石力学/业务属性。只有在真实关键字确定后，才能添加未来的
    # 细部分析和敏感性关键字。
    _rule("FLUID", "n", MODULE_ROCK_PROPERTIES, "相渗指数 n", "float"),
    _rule(
        "WR", "sigma_file", MODULE_ROCK_PROPERTIES, "形状因子 sigma", "path",
        parser_kind=PARSER_PROPERTY_ARRAY, parsed_key="shape_factor",
        requirement=REQUIREMENT_CONDITIONAL,
        required_when=("model_type=wr", "wr_input_mode=file"),
    ),

    # 全部裂缝信息都归属裂缝模块，无论其
    # 源关键字位于 [ROCK] 还是 [FRACTURE]。
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

    # 流体和 PVT。FLUID.n 刻意归属 rock_properties。
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

    # 初始状态。So 为派生值，因此不注册为输入。
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

    # 井输入遵循 uniform_data111.txt 实际提供的文件。
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

    # 仅显示四个时间控制字段。其余求解器和
    # 输出值会被导入并保留，但不会出现在普通
    # 参数对话框中。
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
        "model_type", "WR 双重介质", "choice", "normal",
        choices=("normal", "wr"),
    ),
    ModelConfigFieldRule(
        "grid_type", "网格类型", "choice", "corner_point",
        visible=False, editable=False, choices=("corner_point",),
    ),
    ModelConfigFieldRule(
        "enable_lgr", "LGR 加密模型", "bool", True,
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
        visible=False, editable=False,
    ),
    ModelConfigFieldRule(
        "enable_hydraulic_fractures", "人工裂缝", "bool", False,
        visible=False, editable=False,
    ),
    ModelConfigFieldRule(
        "enable_real_gas_pvt", "真实气体 PVT", "bool", True,
        visible=False, editable=False,
    ),
    ModelConfigFieldRule(
        "wr_input_mode", "WR 数据来源", "choice", "file",
        visible=False, editable=False,
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
    # 网格和基质属性内容。这些是已解析值和
    # 摘要；源文件名和关键字原始值会被刻意
    # 排除在本注册表之外。
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

    # 岩石属性。
    _display(MODULE_ROCK_PROPERTIES, "relperm_exponent_n", "相渗指数 n", "n",
             "相渗指数", WIDGET_NUMBER, editable=True),
    _display(MODULE_ROCK_PROPERTIES, "shape_factor_summary", "形状因子",
             "shape_factor.summary", "形状因子", WIDGET_SUMMARY_TABLE,
             columns=PROPERTY_SUMMARY_COLUMNS),

    # 天然裂缝、等效裂缝以及未来人工裂缝的业务内容。
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

    # 流体和 PVT 标量内容。
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

    # 初始状态。
    _display(MODULE_INITIAL_CONDITIONS, "initial_pressure", "初始压力",
             "pressure", "初始压力", WIDGET_NUMBER, editable=True),
    _display(MODULE_INITIAL_CONDITIONS, "initial_sw", "初始含水饱和度",
             "sw", "初始饱和度", WIDGET_NUMBER, editable=True),
    _display(MODULE_INITIAL_CONDITIONS, "initial_sg", "初始含气饱和度",
             "sg", "初始饱和度", WIDGET_NUMBER, editable=True),
    _display(MODULE_INITIAL_CONDITIONS, "initial_so", "初始含油饱和度",
             "derived.so", "初始饱和度", WIDGET_DERIVED),

    # 使用已解析的井数据，而不是两个源定位字段。
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

    # 求解器拥有更多已导入值，但普通对话框仅公开
    # 四个已确认的时间控制参数。
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
    """返回全部注册表查询使用的不区分大小写标识。"""

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
    """按注册顺序返回指定模块所属的规则。"""

    rules = []
    for rule in KEYWORD_RULES:
        if rule.module_key != module_key:
            continue
        if importable_only and not rule.importable:
            continue
        rules.append(rule)
    return tuple(rules)


def display_fields_for_module(module_key: str) -> Tuple[DisplayFieldRule, ...]:
    """按展示顺序返回用户可见的业务字段。"""

    return tuple(
        field for field in DISPLAY_FIELD_RULES
        if field.module_key == module_key
    )


def is_ignored_case_section(section: str) -> bool:
    return str(section or "").strip().upper() in IGNORED_CASE_SECTIONS


def registry_issues() -> Tuple[str, ...]:
    """返回结构问题，不执行业务校验。"""

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
        # 人工裂缝展示为未来真实关键字或
        # 手动录入的结构化参数预留。
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
