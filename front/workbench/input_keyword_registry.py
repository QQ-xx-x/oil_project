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


@dataclass(frozen=True)
class ModuleSpec:
    """Stable business definition for one top-level input-tree node."""

    key: str
    title: str
    accepts_case_keywords: bool = True
    reserved_groups: Tuple[str, ...] = ()


@dataclass(frozen=True)
class KeywordRule:
    """Ownership and presentation policy for one CaseData keyword."""

    section: str
    keyword: str
    module_key: str
    title: str
    value_type: str = "string"
    importable: bool = True
    visible: bool = True
    editable: bool = True
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


MODULE_SPECS = (
    ModuleSpec(
        MODULE_MODEL_CONFIGURATION,
        "模型配置",
        reserved_groups=("模型类型", "LGR", "功能模块", "WR数据来源"),
    ),
    ModuleSpec(
        MODULE_GRID_SPATIAL,
        "网格与空间数据",
        reserved_groups=("角点网格", "基质孔隙度与渗透率"),
    ),
    ModuleSpec(
        MODULE_ROCK_PROPERTIES,
        "储层岩石属性",
        reserved_groups=("相渗指数", "细部解析", "敏感性参数", "形状因子"),
    ),
    ModuleSpec(
        MODULE_FRACTURE_SYSTEM,
        "裂缝系统",
        reserved_groups=("天然裂缝", "等效裂缝属性", "人工裂缝"),
    ),
    ModuleSpec(
        MODULE_FLUID_PVT,
        "流体与 PVT",
        reserved_groups=("基础流体参数", "气体组分", "PVT表"),
    ),
    ModuleSpec(
        MODULE_INITIAL_CONDITIONS,
        "初始状态",
        reserved_groups=("初始压力", "初始饱和度"),
    ),
    ModuleSpec(
        MODULE_WELL_PRODUCTION,
        "井与生产控制",
        reserved_groups=("井轨迹", "完井与井控"),
    ),
    ModuleSpec(
        MODULE_SOLVER_OUTPUT,
        "求解与输出控制",
        reserved_groups=("时间控制", "后台求解参数", "输出控制"),
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
          value_type: str = "string", *, visible: bool = True,
          editable: bool = True,
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
        visible=visible,
        editable=editable,
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
        requirement=REQUIREMENT_REQUIRED,
    ),
    _rule(
        "ROCK", "matrix_phi_file", MODULE_GRID_SPATIAL, "基质孔隙度", "path",
        requirement=REQUIREMENT_REQUIRED,
    ),
    _rule(
        "ROCK", "matrix_kx_file", MODULE_GRID_SPATIAL, "基质 Kx", "path",
        requirement=REQUIREMENT_REQUIRED,
    ),
    _rule(
        "ROCK", "matrix_ky_file", MODULE_GRID_SPATIAL, "基质 Ky", "path",
        requirement=REQUIREMENT_REQUIRED,
    ),
    _rule(
        "ROCK", "matrix_kz_file", MODULE_GRID_SPATIAL, "基质 Kz", "path",
        requirement=REQUIREMENT_REQUIRED,
    ),

    # Rock-mechanics/business properties.  Future detailed-analysis and
    # sensitivity keywords must be added only when their real names exist.
    _rule("FLUID", "n", MODULE_ROCK_PROPERTIES, "相渗指数 n", "float"),
    _rule(
        "WR", "sigma_file", MODULE_ROCK_PROPERTIES, "形状因子 sigma", "path",
        requirement=REQUIREMENT_CONDITIONAL,
        required_when=("model_type=wr", "wr_input_mode=file"),
    ),

    # All fracture information belongs to the fracture module regardless of
    # whether its source keyword is under [ROCK] or [FRACTURE].
    _rule(
        "FRACTURE", "fracture_file", MODULE_FRACTURE_SYSTEM,
        "天然裂缝 DFN", "path",
        requirement=REQUIREMENT_CONDITIONAL,
        required_when=("enable_natural_fractures",),
    ),
    _rule(
        "ROCK", "fracture_phi_file", MODULE_FRACTURE_SYSTEM,
        "等效裂缝孔隙度", "path",
        requirement=REQUIREMENT_CONDITIONAL,
        required_when=("model_type=wr", "wr_input_mode=file"),
    ),
    _rule(
        "ROCK", "fracture_kx_file", MODULE_FRACTURE_SYSTEM,
        "等效裂缝 Kx", "path",
        requirement=REQUIREMENT_CONDITIONAL,
        required_when=("model_type=wr", "wr_input_mode=file"),
    ),
    _rule(
        "ROCK", "fracture_ky_file", MODULE_FRACTURE_SYSTEM,
        "等效裂缝 Ky", "path",
        requirement=REQUIREMENT_CONDITIONAL,
        required_when=("model_type=wr", "wr_input_mode=file"),
    ),
    _rule(
        "ROCK", "fracture_kz_file", MODULE_FRACTURE_SYSTEM,
        "等效裂缝 Kz", "path",
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
        validation_group="well_files",
    ),
    _rule(
        "WELL", "well_completion_file", MODULE_WELL_PRODUCTION,
        "完井与井控数据", "path", validation_group="well_files",
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
        "Newton 最大迭代数", "int", visible=False, editable=False,
    ),
    _rule(
        "SOLVER", "newton_tol", MODULE_SOLVER_OUTPUT,
        "Newton 收敛容差", "float", visible=False, editable=False,
    ),
    _rule(
        "SOLVER", "linear_tol", MODULE_SOLVER_OUTPUT,
        "线性求解容差", "float", visible=False, editable=False,
    ),
    _rule(
        "SOLVER", "linear_max_iter", MODULE_SOLVER_OUTPUT,
        "线性求解最大迭代数", "int", visible=False, editable=False,
    ),
    _rule(
        "SOLVER", "dt_cut_factor", MODULE_SOLVER_OUTPUT,
        "时间步缩小系数", "float", visible=False, editable=False,
    ),
    _rule(
        "SOLVER", "dt_grow_factor", MODULE_SOLVER_OUTPUT,
        "时间步增长系数", "float", visible=False, editable=False,
    ),
    _rule(
        "SOLVER", "max_timestep_retry", MODULE_SOLVER_OUTPUT,
        "时间步最大重试数", "int", visible=False, editable=False,
    ),
    _rule(
        "OUTPUT", "field_output_times", MODULE_SOLVER_OUTPUT,
        "空间场输出时间", "list", visible=False, editable=False,
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


def get_module_spec(module_key: str) -> Optional[ModuleSpec]:
    return MODULE_SPEC_BY_KEY.get(str(module_key or ""))


def get_keyword_rule(section: str, keyword: str) -> Optional[KeywordRule]:
    return KEYWORD_RULE_BY_IDENTITY.get(
        normalize_keyword_identity(section, keyword))


def get_model_config_field(key: str) -> Optional[ModelConfigFieldRule]:
    return MODEL_CONFIG_FIELD_BY_KEY.get(str(key or ""))


def keyword_rules_for_module(module_key: str, *, importable_only: bool = False,
                             visible_only: bool = False) -> Tuple[KeywordRule, ...]:
    """Return rules owned by a module while preserving registry order."""

    rules = []
    for rule in KEYWORD_RULES:
        if rule.module_key != module_key:
            continue
        if importable_only and not rule.importable:
            continue
        if visible_only and not rule.visible:
            continue
        rules.append(rule)
    return tuple(rules)


def is_ignored_case_section(section: str) -> bool:
    return str(section or "").strip().upper() in IGNORED_CASE_SECTIONS


def registry_issues() -> Tuple[str, ...]:
    """Return structural problems without performing business validation."""

    issues = []
    module_keys = [spec.key for spec in MODULE_SPECS]
    if len(module_keys) != len(set(module_keys)):
        issues.append("duplicate module key")

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

    return tuple(issues)


def assert_registry_valid() -> None:
    issues = registry_issues()
    if issues:
        raise RuntimeError("Invalid input keyword registry: " + "; ".join(issues))


assert_registry_valid()

