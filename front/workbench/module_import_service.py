# -*- coding: utf-8 -*-
"""由注册表驱动、相互隔离且具备原子性的业务模块导入。"""

import math
import os

import numpy as np

from front.uniform_parser import (
    parse_dfn,
    parse_grid,
    parse_property,
    parse_wells,
)

from .case_data_parser import parse_case_data
from .input_keyword_registry import (
    MODULE_FLUID_PVT,
    MODULE_FRACTURE_SYSTEM,
    MODULE_GRID_SPATIAL,
    MODULE_INITIAL_CONDITIONS,
    MODULE_ROCK_PROPERTIES,
    MODULE_SOLVER_OUTPUT,
    MODULE_SPEC_BY_KEY,
    MODULE_WELL_PRODUCTION,
    PARSER_CORNER_GRID,
    PARSER_DFN,
    PARSER_LIST,
    PARSER_PROPERTY_ARRAY,
    PARSER_SCALAR,
    PARSER_WELLS,
    REQUIREMENT_CONDITIONAL,
    REQUIREMENT_REQUIRED,
    keyword_rules_for_module,
)
from .module_input_models import (
    ModuleImportResult,
    ModuleInputState,
    ModuleParsedData,
)
from .project_state import normalize_model_config


NULL_VALUE = 99999.0
MATRIX_PERMEABILITY_SCALE = 1.0 / 1000.0


class ModuleImportService:
    """从一个 CaseData 源精确导入一个已注册模块。"""

    def __init__(self, project_state=None):
        self.project_state = project_state

    def import_module(self, module_key, case_data_path):
        """先构建候选状态，再原子替换其所属模块。"""

        prepared = self.prepare_module(module_key, case_data_path)
        if not prepared.success or prepared.state is None:
            return prepared
        if self.project_state is None:
            return prepared
        try:
            committed = self.project_state.replace_module_input_state(
                prepared.module_key, prepared.state)
        except (TypeError, ValueError):
            return ModuleImportResult(
                module_key=prepared.module_key,
                success=False,
                errors=("模块数据无法提交，原有数据已保留。",),
                warnings=prepared.warnings,
                replaced_revision=prepared.replaced_revision,
            )
        return ModuleImportResult(
            module_key=prepared.module_key,
            success=True,
            state=committed,
            warnings=prepared.warnings,
            replaced_revision=prepared.replaced_revision,
        )

    def prepare_module(self, module_key, case_data_path):
        """解析并校验分离的草稿，不修改 ProjectState。"""

        module_key = str(module_key or "")
        previous = (
            self.project_state.get_module_input_state(module_key)
            if self.project_state is not None else None
        )
        replaced_revision = previous.revision if previous is not None else 0
        candidate, errors, warnings = self._build_candidate(
            module_key, case_data_path)
        if candidate is None:
            return ModuleImportResult(
                module_key=module_key,
                success=False,
                errors=tuple(errors),
                warnings=tuple(warnings),
                replaced_revision=replaced_revision,
            )
        return ModuleImportResult(
            module_key=module_key,
            success=True,
            state=candidate,
            warnings=tuple(warnings),
            replaced_revision=replaced_revision,
        )

    def _build_candidate(self, module_key, case_data_path):
        errors = []
        warnings = []
        checks = {}
        module = MODULE_SPEC_BY_KEY.get(module_key)
        if module is None or not module.accepts_case_keywords:
            return None, ["当前节点不支持模块数据导入。"], warnings

        source_path = os.path.abspath(str(case_data_path or "").strip())
        if not source_path or not os.path.isfile(source_path):
            return None, ["无法读取所选数据。"], warnings

        case_data = parse_case_data(source_path)
        if case_data.errors:
            return None, ["所选数据格式无效。"], warnings

        rules = keyword_rules_for_module(module_key, importable_only=True)
        keyword_index = _keyword_index(case_data)
        found = {
            rule: keyword_index[rule.identity]
            for rule in rules
            if rule.identity in keyword_index
        }
        if not found:
            return None, ["所选数据中没有当前模块可导入的内容。"], warnings

        parsed_values = {}
        raw_values = {}
        for rule, keyword in found.items():
            raw_values[rule.qualified_name] = keyword.raw_value
            if rule.parser_kind not in {PARSER_SCALAR, PARSER_LIST}:
                continue
            try:
                parsed_values[rule.parsed_key] = _coerce_keyword_value(
                    keyword.value, keyword.raw_value, rule.value_type,
                    rule.parser_kind)
            except (TypeError, ValueError):
                errors.append(f"{rule.title}的数值格式无效。")

        context = normalize_model_config(
            getattr(self.project_state, "model_config", None))
        context.update(parsed_values)
        for rule in rules:
            required = rule.requirement == REQUIREMENT_REQUIRED
            if rule.requirement == REQUIREMENT_CONDITIONAL:
                required = _conditions_met(rule.required_when, context)
            if required and rule not in found:
                errors.append(f"缺少必填数据：{rule.title}。")

        resolved_paths = {}
        for rule, keyword in found.items():
            if rule.value_type != "path":
                continue
            path = _resolve_locator(case_data.base_dir, keyword.raw_value)
            resolved_paths[rule] = path
            if not path or not os.path.isfile(path):
                errors.append(f"{rule.title}的数据不可用。")

        if errors:
            return None, errors, warnings

        runtime = {}
        for rule in rules:
            if rule not in found or rule.parser_kind != PARSER_CORNER_GRID:
                continue
            try:
                grid = parse_grid(resolved_paths[rule])
                parsed_values[rule.parsed_key] = _grid_business_data(grid)
                runtime["grid"] = grid
                grid_checks, grid_errors = _validate_grid_structure(grid)
                checks.update(grid_checks)
                errors.extend(grid_errors)
            except Exception:
                errors.append(f"{rule.title}解析失败。")

        for rule in rules:
            if rule not in found or rule.parser_kind != PARSER_PROPERTY_ARRAY:
                continue
            try:
                values = parse_property(resolved_paths[rule])
                summary = self._property_summary(rule, values, runtime)
                parsed_values[rule.parsed_key] = {"summary": summary}
                checks[f"{rule.title}数量"] = {
                    "ok": summary["length_match_grid"],
                    "detail": (
                        f"{summary['count']} / {summary['expected_count']}"
                        if summary["expected_count"] else
                        str(summary["count"])
                    ),
                }
                if not summary["length_match_grid"]:
                    errors.append(f"{rule.title}的数据数量与网格不一致。")
            except Exception:
                errors.append(f"{rule.title}解析失败。")

        for rule in rules:
            if rule not in found or rule.parser_kind != PARSER_DFN:
                continue
            try:
                dfn = parse_dfn(resolved_paths[rule])
                parsed_values[rule.parsed_key] = natural_fracture_business_data(dfn)
            except Exception:
                errors.append(f"{rule.title}解析失败。")

        well_rules = [
            rule for rule in rules
            if rule.parser_kind == PARSER_WELLS and rule in found
        ]
        if well_rules:
            self._parse_wells(
                rules, found, resolved_paths, parsed_values, errors, warnings)

        business_validation = validate_module_business_data(
            module_key, parsed_values)
        errors.extend(business_validation["errors"])
        warnings.extend(business_validation["warnings"])
        checks.update(business_validation["checks"])
        if errors:
            return None, errors, warnings

        validation = {
            "ok": True,
            "errors": [],
            "warnings": list(warnings),
            "imported_value_count": len(found),
            "checks": checks,
        }
        source = _internal_source_record(
            case_data, found, resolved_paths)
        candidate = ModuleInputState(
            module_key=module_key,
            raw_values=raw_values,
            parsed_data=ModuleParsedData(values=parsed_values),
            validation=validation,
            source=source,
            dirty=False,
            revision=0,
        )
        return candidate, errors, warnings

    def _property_summary(self, rule, values, runtime):
        numbers = np.asarray(values, dtype=np.float64)
        null_mask = np.isclose(numbers, NULL_VALUE)
        finite_mask = np.isfinite(numbers)
        transformed = numbers.copy()
        scale = None
        if rule.keyword.lower() in {
                "matrix_kx_file", "matrix_ky_file", "matrix_kz_file"}:
            transformed[~null_mask] *= MATRIX_PERMEABILITY_SCALE
            scale = MATRIX_PERMEABILITY_SCALE

        valid_mask = finite_mask & ~null_mask
        grid = runtime.get("grid") or {}
        actnum = np.asarray(grid.get("actnum") or [], dtype=np.int8)
        if len(actnum):
            combined = np.zeros(len(transformed), dtype=bool)
            count = min(len(combined), len(actnum))
            combined[:count] = valid_mask[:count] & (actnum[:count] == 1)
            valid_mask = combined

        expected_count = self._expected_grid_count(runtime)
        valid_values = transformed[valid_mask]
        return {
            "count": int(len(transformed)),
            "expected_count": int(expected_count or 0),
            "length_match_grid": bool(
                not expected_count or len(transformed) == expected_count),
            "valid_count": int(np.sum(valid_mask)),
            "null_count": int(np.sum(null_mask)),
            "min": _safe_stat(np.min, valid_values),
            "max": _safe_stat(np.max, valid_values),
            "mean": _safe_stat(np.mean, valid_values),
            "scale": scale,
        }

    def _expected_grid_count(self, runtime):
        grid = runtime.get("grid") or {}
        count = int(grid.get("total_cell_count") or 0)
        if count or self.project_state is None:
            return count
        grid_state = self.project_state.get_module_input_state(
            MODULE_GRID_SPATIAL)
        if grid_state is None:
            return 0
        grid_data = grid_state.parsed_data.values.get("grid") or {}
        return int(grid_data.get("total_cell_count") or 0)

    @staticmethod
    def _parse_wells(rules, found, resolved_paths, parsed_values,
                     errors, warnings):
        by_keyword = {
            rule.keyword.lower(): rule
            for rule in rules if rule.parser_kind == PARSER_WELLS
        }
        track_rule = by_keyword.get("well_track_file")
        completion_rule = by_keyword.get("well_completion_file")
        if track_rule not in found or completion_rule not in found:
            errors.append("井轨迹和完井控制数据必须同时提供。")
            return
        try:
            wells = parse_wells(
                resolved_paths[track_rule], resolved_paths[completion_rule])
        except Exception:
            errors.append("井与生产控制数据解析失败。")
            return
        for warning in ((wells.get("validation") or {}).get("warnings") or []):
            warnings.append(str(warning))
        # 解析器来源信息仅属于 ModuleInputState.source；
        # 已解析业务数据必须能安全用于未来的普通对话框。
        wells = dict(wells)
        wells.pop("source_files", None)
        parsed_values[track_rule.parsed_key] = _well_business_data(wells)


def normalize_module_business_data(module_key, values):
    """在校验和提交前规范化可编辑业务表格。"""

    normalized = dict(values or {})
    if module_key != MODULE_WELL_PRODUCTION:
        return normalized

    wells = dict(normalized.get("wells") or {})
    tracks = list(wells.get("tracks") or [])
    completions = list(wells.get("completions") or [])
    prior_types = {
        row.get("well_name"): row.get("well_type", "")
        for row in wells.get("well_list") or []
        if isinstance(row, dict)
    }
    names = sorted({
        str(row.get("well_name") or "").strip()
        for row in tracks + completions if isinstance(row, dict)
    } - {""})
    well_list = []
    for name in names:
        well_tracks = [
            row for row in tracks
            if isinstance(row, dict) and row.get("well_name") == name
        ]
        md_values = [
            _as_float(row.get("md_m")) for row in well_tracks
            if _as_float(row.get("md_m")) is not None
        ]
        well_type = prior_types.get(name, "")
        if not well_type:
            matching = next((
                row for row in completions
                if isinstance(row, dict) and row.get("well_name") == name
            ), {})
            well_type = matching.get("well_type", "")
        well_list.append({
            "well_name": name,
            "well_type": well_type,
            "track_point_count": len(well_tracks),
            "md_min": min(md_values) if md_values else None,
            "md_max": max(md_values) if md_values else None,
        })

    event_counts = {
        "PERF": 0, "OPEN": 0, "SHUT": 0, "CONTROL": 0,
    }
    for row in completions:
        if not isinstance(row, dict):
            continue
        event = str(row.get("event") or "").upper()
        if event in event_counts:
            event_counts[event] += 1
    summary = dict(wells.get("summary") or {})
    summary.update({
        "well_count": len(well_list),
        "completion_definition_count": event_counts["PERF"],
        "event_count": len(completions),
        "perf_event_count": event_counts["PERF"],
        "open_event_count": event_counts["OPEN"],
        "shut_event_count": event_counts["SHUT"],
        "control_event_count": event_counts["CONTROL"],
    })
    wells.update({
        "summary": summary,
        "well_list": well_list,
        "tracks": tracks,
        "completions": completions,
    })
    normalized["wells"] = wells
    return normalized


def validate_module_business_data(module_key, values):
    """校验规范化的用户可见值，不读取源文件。"""

    values = values or {}
    errors = []
    warnings = []
    checks = {}

    def add_check(name, ok, detail="", error="", warning=""):
        checks[name] = {"ok": bool(ok), "detail": str(detail)}
        if ok:
            return
        if error:
            errors.append(error)
        elif warning:
            warnings.append(warning)

    def positive(key, title, allow_zero=False):
        if values.get(key) is None:
            return
        number = _as_float(values.get(key))
        ok = number is not None and (number >= 0 if allow_zero else number > 0)
        add_check(
            title, ok, values.get(key),
            error=f"{title}必须{'大于或等于' if allow_zero else '大于'}零。")

    def fraction(key, title):
        if values.get(key) is None:
            return
        number = _as_float(values.get(key))
        add_check(
            title, number is not None and 0 <= number <= 1,
            values.get(key), error=f"{title}必须在 0 到 1 之间。")

    if module_key == MODULE_FLUID_PVT:
        positive("mu_w", "水相黏度")
        positive("mu_o", "油相黏度")
        positive("cw", "水相压缩系数", allow_zero=True)
        positive("co", "油相压缩系数", allow_zero=True)
        positive("p_ref", "参考压力")
        for key, title in (("swi", "束缚水饱和度"),
                           ("sor", "残余油饱和度"),
                           ("sgc", "临界气饱和度")):
            fraction(key, title)
        if values.get("temperature_c") is not None:
            temperature = _as_float(values.get("temperature_c"))
            add_check(
                "气藏温度", temperature is not None and temperature > -273.15,
                values.get("temperature_c"),
                error="气藏温度必须高于绝对零度。")

        mole_keys = (
            "mole_ch4", "mole_c2h6", "mole_c3h8", "mole_n2",
            "mole_co2", "mole_h2o", "mole_unknown",
        )
        available_moles = []
        for key in mole_keys:
            if values.get(key) is None:
                continue
            number = _as_float(values.get(key))
            add_check(
                f"{key} 范围", number is not None and 0 <= number <= 1,
                values.get(key), error="气体组分摩尔分数必须在 0 到 1 之间。")
            if number is not None:
                available_moles.append(number)
        if available_moles:
            total = sum(available_moles)
            add_check(
                "气体组分总和", math.isclose(
                    total, 1.0, rel_tol=1e-6, abs_tol=1e-6),
                f"{total:.10g}", warning="气体组分摩尔分数之和不等于 1。")

        pmin = _as_float(values.get("gas_table_pmin_bar"))
        pmax = _as_float(values.get("gas_table_pmax_bar"))
        if pmin is not None and pmax is not None:
            add_check(
                "PVT 压力范围", pmin >= 0 and pmax > pmin,
                f"{pmin:g} ～ {pmax:g} bar",
                error="PVT 最大压力必须大于非负的最小压力。")
        if values.get("gas_table_n") is not None:
            count = _as_float(values.get("gas_table_n"))
            add_check(
                "PVT 采样点数", count is not None and count.is_integer()
                and count >= 2, values.get("gas_table_n"),
                error="PVT 采样点数必须是不小于 2 的整数。")

    elif module_key == MODULE_INITIAL_CONDITIONS:
        positive("pressure", "初始压力")
        fraction("sw", "初始含水饱和度")
        fraction("sg", "初始含气饱和度")
        sw = _as_float(values.get("sw"))
        sg = _as_float(values.get("sg"))
        if sw is not None and sg is not None:
            total = sw + sg
            add_check(
                "初始饱和度总和", total <= 1.0 + 1e-9,
                f"Sw + Sg = {total:.10g}",
                error="初始含水和含气饱和度之和不能大于 1。")

    elif module_key == MODULE_SOLVER_OUTPUT:
        for key, title in (("total_time", "总模拟时间"),
                           ("dt_init", "初始时间步"),
                           ("dt_min", "最小时间步"),
                           ("dt_max", "最大时间步")):
            positive(key, title)
        dt_min = _as_float(values.get("dt_min"))
        dt_init = _as_float(values.get("dt_init"))
        dt_max = _as_float(values.get("dt_max"))
        if None not in (dt_min, dt_init, dt_max):
            add_check(
                "时间步范围", dt_min <= dt_init <= dt_max,
                f"{dt_min:g} ≤ {dt_init:g} ≤ {dt_max:g}",
                error="时间步必须满足 dt_min ≤ dt_init ≤ dt_max。")

    elif module_key == MODULE_ROCK_PROPERTIES:
        positive("n", "相渗指数 n")

    elif module_key == MODULE_FRACTURE_SYSTEM:
        natural = values.get("natural_fractures") or {}
        if natural:
            declared = int(natural.get("fracture_count") or 0)
            parsed = len(natural.get("fractures") or [])
            add_check(
                "天然裂缝数量", declared == parsed,
                f"{parsed} / {declared}",
                warning="天然裂缝声明数量与实际解析数量不一致。")
            add_check(
                "天然裂缝节点", int(natural.get("node_count") or 0) > 0,
                natural.get("node_count") or 0,
                warning="天然裂缝没有有效节点。")
        hydraulic = values.get("hydraulic_fractures") or []
        if hydraulic:
            ids = [
                str(row.get("fracture_id") or "").strip()
                for row in hydraulic if isinstance(row, dict)
            ]
            add_check(
                "人工裂缝标识", all(ids) and len(ids) == len(set(ids)),
                f"{len(ids)} 条",
                error="人工裂缝ID不能为空且不能重复。")

    elif module_key == MODULE_WELL_PRODUCTION:
        wells = values.get("wells") or {}
        summary = wells.get("summary") or {}
        well_list = wells.get("well_list") or []
        tracks = wells.get("tracks") or []
        completions = wells.get("completions") or []
        if wells:
            add_check(
                "井数量", int(summary.get("well_count") or 0) == len(well_list)
                and len(well_list) > 0,
                len(well_list), error="井列表不能为空且数量必须一致。")
            track_counts = {
                row.get("well_name"): int(row.get("track_point_count") or 0)
                for row in well_list if isinstance(row, dict)
            }
            add_check(
                "井轨迹点", bool(tracks) and all(
                    count >= 2 for count in track_counts.values()),
                f"{len(tracks)} 个轨迹点",
                error="每口井至少需要两个轨迹点。")
            add_check(
                "完井与井控事件",
                int(summary.get("event_count") or 0) == len(completions),
                f"{len(completions)} 条",
                error="完井与井控事件数量不一致。")

    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "checks": checks,
    }


def _keyword_index(case_data):
    index = {}
    for section in case_data.sections:
        section_name = str(section.name or "").strip().upper()
        for keyword in section.keywords:
            identity = (section_name, str(keyword.key or "").strip().lower())
            index[identity] = keyword
    return index


def _resolve_locator(base_dir, raw_value):
    value = str(raw_value or "").strip().strip("\"'")
    if not value:
        return ""
    if os.path.isabs(value):
        return os.path.abspath(value)
    return os.path.abspath(os.path.join(base_dir or "", value))


def _coerce_keyword_value(value, raw_value, value_type, parser_kind):
    if parser_kind == PARSER_LIST:
        if isinstance(value, list):
            return list(value)
        text = str(raw_value or "").replace(",", " ")
        return [float(token) for token in text.split() if token]
    if value_type == "bool":
        if isinstance(value, bool):
            return value
        text = str(value).strip().lower()
        if text in {"true", "1", "yes", "on"}:
            return True
        if text in {"false", "0", "no", "off"}:
            return False
        raise ValueError("invalid bool")
    if value_type == "int":
        if isinstance(value, bool):
            raise ValueError("invalid int")
        number = float(value)
        if not number.is_integer():
            raise ValueError("invalid int")
        return int(number)
    if value_type == "float":
        if isinstance(value, bool):
            raise ValueError("invalid float")
        return float(value)
    return value


def _conditions_met(conditions, context):
    for condition in conditions or ():
        text = str(condition or "").strip()
        if "=" in text:
            key, expected = text.split("=", 1)
            actual = context.get(key.strip())
            if str(actual).strip().lower() != expected.strip().lower():
                return False
        elif not bool(context.get(text)):
            return False
    return True


def _grid_business_data(grid):
    coord = np.asarray(grid.get("coord") or [], dtype=np.float64)
    zcorn = np.asarray(grid.get("zcorn") or [], dtype=np.float64)
    actnum = np.asarray(grid.get("actnum") or [], dtype=np.int8)
    bbox_min, bbox_max = _grid_bbox(coord, zcorn)
    return {
        "nx": int(grid.get("nx") or 0),
        "ny": int(grid.get("ny") or 0),
        "nz": int(grid.get("nz") or 0),
        "total_cell_count": int(grid.get("total_cell_count") or 0),
        "active_cell_count": int(np.sum(actnum == 1)),
        "inactive_cell_count": int(np.sum(actnum == 0)),
        "coord_value_count": int(len(coord)),
        "zcorn_value_count": int(len(zcorn)),
        "actnum_value_count": int(len(actnum)),
        "bbox_min": bbox_min,
        "bbox_max": bbox_max,
    }


def _validate_grid_structure(grid):
    """返回面向业务的网格检查结果，不暴露源数据细节。"""

    nx = int(grid.get("nx") or 0)
    ny = int(grid.get("ny") or 0)
    nz = int(grid.get("nz") or 0)
    total = int(grid.get("total_cell_count") or 0)
    coord = np.asarray(grid.get("coord") or [], dtype=np.float64)
    zcorn = np.asarray(grid.get("zcorn") or [], dtype=np.float64)
    actnum = np.asarray(grid.get("actnum") or [], dtype=np.int8)

    expected_total = nx * ny * nz
    expected_coord = 6 * (nx + 1) * (ny + 1) if nx > 0 and ny > 0 else 0
    expected_zcorn = 8 * expected_total if expected_total > 0 else 0
    expected_actnum = expected_total if expected_total > 0 else 0
    active_count = int(np.sum(actnum == 1))
    inactive_count = int(np.sum(actnum == 0))

    checks = {}
    errors = []

    def add_check(name, ok, detail, error_message):
        checks[name] = {"ok": bool(ok), "detail": str(detail)}
        if not ok:
            errors.append(error_message)

    add_check(
        "网格维度", nx > 0 and ny > 0 and nz > 0,
        f"{nx} × {ny} × {nz}", "网格维度必须为正整数。")
    add_check(
        "网格总数", total > 0 and total == expected_total,
        f"{total} / {expected_total}", "网格总数与网格维度不一致。")
    add_check(
        "COORD 数值数量", expected_coord > 0 and len(coord) == expected_coord,
        f"{len(coord)} / {expected_coord}",
        "COORD 数值数量与网格维度不一致。")
    add_check(
        "ZCORN 数值数量", expected_zcorn > 0 and len(zcorn) == expected_zcorn,
        f"{len(zcorn)} / {expected_zcorn}",
        "ZCORN 数值数量与网格总数不一致。")
    add_check(
        "ACTNUM 数值数量", expected_actnum > 0 and len(actnum) == expected_actnum,
        f"{len(actnum)} / {expected_actnum}",
        "ACTNUM 数值数量与网格总数不一致。")
    add_check(
        "网格启用状态", len(actnum) > 0 and active_count + inactive_count == len(actnum),
        f"活跃 {active_count}，非活跃 {inactive_count}",
        "ACTNUM 只能包含活跃或非活跃状态。")
    add_check(
        "网格坐标数值", len(coord) > 0 and len(zcorn) > 0
        and bool(np.all(np.isfinite(coord))) and bool(np.all(np.isfinite(zcorn))),
        "数值有效" if (len(coord) and len(zcorn)
                         and np.all(np.isfinite(coord))
                         and np.all(np.isfinite(zcorn))) else "存在无效数值",
        "网格坐标中存在无效数值。")
    return checks, errors


def _grid_bbox(coord, zcorn):
    if len(coord) >= 6:
        pillars = coord[:len(coord) - (len(coord) % 6)].reshape((-1, 6))
        x_values = pillars[:, (0, 3)].reshape(-1)
        y_values = pillars[:, (1, 4)].reshape(-1)
        x_min, x_max = float(np.min(x_values)), float(np.max(x_values))
        y_min, y_max = float(np.min(y_values)), float(np.max(y_values))
    else:
        x_min = x_max = y_min = y_max = 0.0
    if len(zcorn):
        z_min, z_max = float(np.min(zcorn)), float(np.max(zcorn))
    else:
        z_min = z_max = 0.0
    return [x_min, y_min, z_min], [x_max, y_max, z_max]


def natural_fracture_business_data(dfn):
    """把 DFN 解析结果转换为裂缝界面使用的业务结构。"""

    data = dict(dfn or {})
    fractures = list(data.get("fractures") or [])
    data["summary"] = {
        "fracture_count": int(data.get("fracture_count") or 0),
        "parsed_fracture_count": len(fractures),
        "node_count": int(data.get("node_count") or 0),
        "property_count": int(data.get("property_count") or 0),
        "set_count": len(data.get("sets") or []),
        "bbox_min": list(data.get("bbox_min") or []),
        "bbox_max": list(data.get("bbox_max") or []),
        "permeability": _fracture_stat(fractures, "permeability"),
        "compressibility": _fracture_stat(fractures, "compressibility"),
        "aperture": _fracture_stat(fractures, "aperture"),
    }
    return data


def _fracture_stat(fractures, key):
    values = np.asarray([
        item.get(key) for item in fractures
        if item.get(key) is not None
    ], dtype=np.float64)
    return {
        "count": int(len(values)),
        "min": _safe_stat(np.min, values),
        "max": _safe_stat(np.max, values),
        "mean": _safe_stat(np.mean, values),
    }


def _well_business_data(wells):
    data = dict(wells or {})
    well_list = []
    tracks = []
    completions = []
    for well in data.get("wells") or []:
        well_name = well.get("well_name", "")
        track = list(well.get("track") or [])
        well_list.append({
            "well_name": well_name,
            "well_type": well.get("well_type", ""),
            "track_point_count": len(track),
            "md_min": well.get("md_min_m"),
            "md_max": well.get("md_max_m"),
        })
        for point in track:
            row = dict(point)
            row["well_name"] = well_name
            tracks.append(row)

        definitions = {
            definition.get("comp_id", ""): definition
            for definition in well.get("completion_definitions") or []
        }
        for definition in definitions.values():
            row = dict(definition)
            row.update({"event": "PERF", "date": row.get("date_day")})
            completions.append(row)
        for event in well.get("events") or []:
            definition = definitions.get(event.get("comp_id", ""), {})
            row = dict(definition)
            row.update(event)
            row["date"] = event.get("date_day")
            completions.append(row)
    tracks.sort(key=lambda row: (
        str(row.get("well_name") or ""),
        _as_float(row.get("md_m")) or 0.0,
    ))
    completions.sort(key=lambda row: (
        _as_float(row.get("date")) or 0.0,
        int(row.get("source_row") or 0),
    ))
    return {
        "schema_version": data.get("schema_version", ""),
        "summary": dict(data.get("summary") or {}),
        "well_list": well_list,
        "tracks": tracks,
        "completions": completions,
    }


def _safe_stat(function, values):
    if not len(values):
        return None
    value = float(function(values))
    return value if math.isfinite(value) else None


def _as_float(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _internal_source_record(case_data, found, resolved_paths):
    records = {}
    for rule, keyword in found.items():
        record = {"raw_value": keyword.raw_value}
        if rule in resolved_paths:
            record.update({
                "resolved_path": resolved_paths[rule],
                "exists": os.path.isfile(resolved_paths[rule]),
            })
        records[rule.qualified_name] = record
    try:
        stat = os.stat(case_data.path)
        source_size = int(stat.st_size)
        modified_ns = int(stat.st_mtime_ns)
    except OSError:
        source_size = 0
        modified_ns = 0
    return {
        "case_data_path": os.path.abspath(case_data.path or ""),
        "base_dir": os.path.abspath(case_data.base_dir or ""),
        "source_size": source_size,
        "modified_ns": modified_ns,
        "keywords": records,
    }
