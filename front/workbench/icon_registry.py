# -*- coding: utf-8 -*-
"""工作台图标语义注册表。"""

from dataclasses import dataclass


@dataclass(frozen=True)
class IconSpec:
    key: str
    group: str
    source: str
    label: str


SOURCE_OILFIELD_SVG = "oilfield_svg"
SOURCE_COMMON_SVG = "common_svg"
SOURCE_PAINTED_FALLBACK = "painted_fallback"

GROUP_COMMON = "通用操作"
GROUP_OILFIELD = "油藏对象"
GROUP_FILE = "文件引用"
GROUP_RESULT = "结果展示"
GROUP_FALLBACK = "兜底图标"


ICON_SPECS = {
    "case_root": IconSpec("case_root", GROUP_FILE, SOURCE_OILFIELD_SVG, "CaseData 根节点"),
    "case_section": IconSpec("case_section", GROUP_FILE, SOURCE_OILFIELD_SVG, "CaseData section"),
    "keyword_param": IconSpec("keyword_param", GROUP_FILE, SOURCE_OILFIELD_SVG, "参数关键字"),
    "grid_file": IconSpec("grid_file", GROUP_FILE, SOURCE_OILFIELD_SVG, "grid.inc 文件"),
    "property_file": IconSpec("property_file", GROUP_FILE, SOURCE_OILFIELD_SVG, "属性数组文件"),
    "dfn_file": IconSpec("dfn_file", GROUP_FILE, SOURCE_OILFIELD_SVG, "裂缝几何文件"),
    "file": IconSpec("file", GROUP_FILE, SOURCE_COMMON_SVG, "普通文件"),
    "folder": IconSpec("folder", GROUP_FILE, SOURCE_COMMON_SVG, "文件夹"),

    "grid": IconSpec("grid", GROUP_OILFIELD, SOURCE_OILFIELD_SVG, "网格"),
    "lgr": IconSpec("lgr", GROUP_OILFIELD, SOURCE_OILFIELD_SVG, "局部网格加密"),
    "rock": IconSpec("rock", GROUP_OILFIELD, SOURCE_OILFIELD_SVG, "岩石属性"),
    "fluid": IconSpec("fluid", GROUP_OILFIELD, SOURCE_OILFIELD_SVG, "流体/PVT"),
    "fracture": IconSpec("fracture", GROUP_OILFIELD, SOURCE_OILFIELD_SVG, "裂缝"),
    "well": IconSpec("well", GROUP_OILFIELD, SOURCE_OILFIELD_SVG, "井"),
    "solver": IconSpec("solver", GROUP_OILFIELD, SOURCE_OILFIELD_SVG, "求解器"),
    "case": IconSpec("case", GROUP_OILFIELD, SOURCE_OILFIELD_SVG, "算例"),

    "pressure": IconSpec("pressure", GROUP_RESULT, SOURCE_OILFIELD_SVG, "压力场"),
    "saturation": IconSpec("saturation", GROUP_RESULT, SOURCE_OILFIELD_SVG, "饱和度场"),
    "porosity": IconSpec("porosity", GROUP_RESULT, SOURCE_OILFIELD_SVG, "孔隙度场"),
    "permeability": IconSpec("permeability", GROUP_RESULT, SOURCE_OILFIELD_SVG, "渗透率场"),
    "result": IconSpec("result", GROUP_RESULT, SOURCE_OILFIELD_SVG, "模拟结果"),
    "layer": IconSpec("layer", GROUP_RESULT, SOURCE_OILFIELD_SVG, "图层"),

    "new": IconSpec("new", GROUP_COMMON, SOURCE_COMMON_SVG, "新建"),
    "save": IconSpec("save", GROUP_COMMON, SOURCE_COMMON_SVG, "保存"),
    "copy": IconSpec("copy", GROUP_COMMON, SOURCE_COMMON_SVG, "复制"),
    "search": IconSpec("search", GROUP_COMMON, SOURCE_COMMON_SVG, "搜索"),
    "window": IconSpec("window", GROUP_COMMON, SOURCE_COMMON_SVG, "窗口"),
    "chart": IconSpec("chart", GROUP_COMMON, SOURCE_COMMON_SVG, "图表"),
    "database": IconSpec("database", GROUP_COMMON, SOURCE_COMMON_SVG, "数据集"),
    "import": IconSpec("import", GROUP_COMMON, SOURCE_COMMON_SVG, "导入/导出"),
    "run": IconSpec("run", GROUP_COMMON, SOURCE_COMMON_SVG, "运行"),
    "validate": IconSpec("validate", GROUP_COMMON, SOURCE_COMMON_SVG, "校验"),
    "process": IconSpec("process", GROUP_COMMON, SOURCE_COMMON_SVG, "流程"),
    "warning": IconSpec("warning", GROUP_COMMON, SOURCE_COMMON_SVG, "警告"),
    "monitor": IconSpec("monitor", GROUP_COMMON, SOURCE_COMMON_SVG, "监控"),

    "generic": IconSpec("generic", GROUP_FALLBACK, SOURCE_PAINTED_FALLBACK, "通用兜底"),
    "undo": IconSpec("undo", GROUP_FALLBACK, SOURCE_PAINTED_FALLBACK, "撤销"),
    "redo": IconSpec("redo", GROUP_FALLBACK, SOURCE_PAINTED_FALLBACK, "重做"),
    "camera": IconSpec("camera", GROUP_FALLBACK, SOURCE_PAINTED_FALLBACK, "截图/捕获"),
}


ICON_ALIASES = {
    "open": "folder",
    "folder_open": "folder",
    "case_data": "case_root",
    "section": "case_section",
    "keyword": "keyword_param",
    "param": "keyword_param",
    "grid_inc": "grid_file",
    "property": "property_file",
    "dfn": "dfn_file",
    "gas": "fluid",
    "oil": "fluid",
    "water": "fluid",
    "fracture_file": "dfn_file",
    "simulation": "run",
    "check": "validate",
    "qc": "validate",
    "results": "result",
    "layers": "layer",
    "export": "import",
    "paste": "copy",
}


STATUS_SPECS = {
    "ok": "已找到/有效",
    "missing": "缺失",
    "dirty": "已修改未保存",
    "warning": "需要注意",
    "blocked": "阻塞",
}


def canonical_icon_kind(kind):
    key = str(kind or "generic").strip()
    if not key:
        key = "generic"
    return ICON_ALIASES.get(key, key)


def icon_spec(kind):
    key = canonical_icon_kind(kind)
    return ICON_SPECS.get(key, ICON_SPECS["generic"])


def known_icon_keys():
    return tuple(sorted(ICON_SPECS))


def oilfield_svg_keys():
    return tuple(
        key for key, spec in ICON_SPECS.items()
        if spec.source == SOURCE_OILFIELD_SVG
    )


def common_svg_keys():
    return tuple(
        key for key, spec in ICON_SPECS.items()
        if spec.source == SOURCE_COMMON_SVG
    )
