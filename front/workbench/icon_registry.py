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
    "matrix": IconSpec("matrix", GROUP_OILFIELD, SOURCE_OILFIELD_SVG, "基质属性"),
    "dual_porosity": IconSpec("dual_porosity", GROUP_OILFIELD, SOURCE_OILFIELD_SVG, "双重介质"),
    "fluid": IconSpec("fluid", GROUP_OILFIELD, SOURCE_OILFIELD_SVG, "流体/PVT"),
    "gas": IconSpec("gas", GROUP_OILFIELD, SOURCE_OILFIELD_SVG, "气相 PVT"),
    "oil_water": IconSpec("oil_water", GROUP_OILFIELD, SOURCE_OILFIELD_SVG, "油水相"),
    "fracture": IconSpec("fracture", GROUP_OILFIELD, SOURCE_OILFIELD_SVG, "裂缝"),
    "well": IconSpec("well", GROUP_OILFIELD, SOURCE_OILFIELD_SVG, "井"),
    "solver": IconSpec("solver", GROUP_OILFIELD, SOURCE_OILFIELD_SVG, "求解器"),
    "initial": IconSpec("initial", GROUP_OILFIELD, SOURCE_OILFIELD_SVG, "初始条件"),
    "output": IconSpec("output", GROUP_OILFIELD, SOURCE_OILFIELD_SVG, "输出控制"),
    "wr": IconSpec("wr", GROUP_OILFIELD, SOURCE_OILFIELD_SVG, "井结果/WR"),
    "case": IconSpec("case", GROUP_OILFIELD, SOURCE_OILFIELD_SVG, "算例"),

    "pressure": IconSpec("pressure", GROUP_RESULT, SOURCE_OILFIELD_SVG, "压力场"),
    "saturation": IconSpec("saturation", GROUP_RESULT, SOURCE_OILFIELD_SVG, "饱和度场"),
    "porosity": IconSpec("porosity", GROUP_RESULT, SOURCE_OILFIELD_SVG, "孔隙度场"),
    "permeability": IconSpec("permeability", GROUP_RESULT, SOURCE_OILFIELD_SVG, "渗透率场"),
    "actnum": IconSpec("actnum", GROUP_RESULT, SOURCE_OILFIELD_SVG, "有效网格"),
    "sigma": IconSpec("sigma", GROUP_RESULT, SOURCE_OILFIELD_SVG, "形状因子"),
    "matrix_property_file": IconSpec("matrix_property_file", GROUP_FILE, SOURCE_OILFIELD_SVG, "基质属性文件"),
    "fracture_property_file": IconSpec("fracture_property_file", GROUP_FILE, SOURCE_OILFIELD_SVG, "裂缝属性文件"),
    "actnum_file": IconSpec("actnum_file", GROUP_FILE, SOURCE_OILFIELD_SVG, "ACTNUM 文件"),
    "sigma_file": IconSpec("sigma_file", GROUP_FILE, SOURCE_OILFIELD_SVG, "SIGMA 文件"),
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
    "undo": IconSpec("undo", GROUP_COMMON, SOURCE_COMMON_SVG, "撤销"),
    "redo": IconSpec("redo", GROUP_COMMON, SOURCE_COMMON_SVG, "重做"),
    "camera": IconSpec("camera", GROUP_COMMON, SOURCE_COMMON_SVG, "截图/捕获"),
    "export": IconSpec("export", GROUP_COMMON, SOURCE_COMMON_SVG, "导出"),
    "cut": IconSpec("cut", GROUP_COMMON, SOURCE_COMMON_SVG, "剪切"),
    "paste": IconSpec("paste", GROUP_COMMON, SOURCE_COMMON_SVG, "粘贴"),
    "print": IconSpec("print", GROUP_COMMON, SOURCE_COMMON_SVG, "打印"),
    "refresh": IconSpec("refresh", GROUP_COMMON, SOURCE_COMMON_SVG, "刷新"),
    "settings": IconSpec("settings", GROUP_COMMON, SOURCE_COMMON_SVG, "设置/选项"),
    "help": IconSpec("help", GROUP_COMMON, SOURCE_COMMON_SVG, "帮助"),
    "table": IconSpec("table", GROUP_COMMON, SOURCE_COMMON_SVG, "表格"),
    "home": IconSpec("home", GROUP_COMMON, SOURCE_COMMON_SVG, "首页"),
    "fullscreen": IconSpec("fullscreen", GROUP_COMMON, SOURCE_COMMON_SVG, "全屏"),
    "object": IconSpec("object", GROUP_COMMON, SOURCE_COMMON_SVG, "通用对象"),
    "subscribe": IconSpec("subscribe", GROUP_COMMON, SOURCE_COMMON_SVG, "订阅"),
    "restrict": IconSpec("restrict", GROUP_COMMON, SOURCE_COMMON_SVG, "限制范围"),
    "fit_view": IconSpec("fit_view", GROUP_COMMON, SOURCE_COMMON_SVG, "适配视图"),
    "pan": IconSpec("pan", GROUP_COMMON, SOURCE_COMMON_SVG, "平移"),
    "select": IconSpec("select", GROUP_COMMON, SOURCE_COMMON_SVG, "选择"),
    "measure": IconSpec("measure", GROUP_COMMON, SOURCE_COMMON_SVG, "测量"),
    "link": IconSpec("link", GROUP_COMMON, SOURCE_COMMON_SVG, "链接"),
    "report": IconSpec("report", GROUP_COMMON, SOURCE_COMMON_SVG, "报告"),
    "background": IconSpec("background", GROUP_COMMON, SOURCE_COMMON_SVG, "背景"),
    "close": IconSpec("close", GROUP_COMMON, SOURCE_COMMON_SVG, "关闭"),
    "clear": IconSpec("clear", GROUP_COMMON, SOURCE_COMMON_SVG, "清空/删除"),

    "generic": IconSpec("generic", GROUP_FALLBACK, SOURCE_PAINTED_FALLBACK, "通用兜底"),
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
    "pvt": "fluid",
    "oil": "oil_water",
    "water": "oil_water",
    "fracture_file": "dfn_file",
    "simulation": "run",
    "check": "validate",
    "qc": "validate",
    "results": "result",
    "layers": "layer",
    "options": "settings",
    "option": "settings",
    "setting": "settings",
    "config": "settings",
    "screenshot": "camera",
    "capture": "camera",
    "bitmap": "camera",
    "sheet": "table",
    "spreadsheet": "table",
    "full_screen": "fullscreen",
    "view_all": "fit_view",
    "fit": "fit_view",
    "delete": "clear",
    "trash": "clear",
    "remove": "clear",
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


def semantic_icon_kind(kind, text="", tooltip="", command=""):
    base_kind = canonical_icon_kind(kind)
    if ICON_SPECS.get(base_kind, ICON_SPECS["generic"]).source == SOURCE_OILFIELD_SVG:
        return base_kind

    content = f"{text} {tooltip} {command}".lower()
    if any(token in content for token in ("casedata", "case data")):
        return "case_root"
    if any(token in content for token in ("算例", "case")):
        return "case"
    if any(token in content for token in ("模板", "template")):
        return "folder"
    if any(token in content for token in ("帮助", "help")):
        return "help"
    if any(token in content for token in ("关闭", "close")):
        return "close"
    if any(token in content for token in ("清空", "删除", "移除", "clear", "delete", "remove", "trash")):
        return "clear"
    if any(token in content for token in ("选项", "设置", "settings", "option")):
        return "settings"
    if any(token in content for token in ("打印", "print")):
        return "print"
    if any(token in content for token in ("粘贴", "paste")):
        return "paste"
    if any(token in content for token in ("剪切", "cut")):
        return "cut"
    if any(token in content for token in ("复制", "克隆", "copy", "clone")):
        return "copy"
    if any(token in content for token in ("导出", "发送到", "export", "send to")):
        return "export"
    if any(token in content for token in ("导入", "import")):
        return "import"
    if any(token in content for token in ("刷新", "自动刷新", "refresh")):
        return "refresh"
    if any(token in content for token in ("气相", "真实气体", "gas")):
        return "gas"
    if any(token in content for token in ("油水", "oil-water", "oil water")):
        return "oil_water"
    if any(token in content for token in ("流体", "黑油", "pvt", "fluid")):
        return "fluid"
    if any(token in content for token in ("表格", "表", "spreadsheet", "sheet")):
        return "table"
    if any(token in content for token in ("首页", "home")):
        return "home"
    if any(token in content for token in ("全屏", "fullscreen")):
        return "fullscreen"
    if any(token in content for token in ("截图", "捕获", "相机", "位图", "camera", "capture", "bitmap")):
        return "camera"
    if any(token in content for token in ("订阅", "subscribe")):
        return "subscribe"
    if any(token in content for token in ("限制", "restrict")):
        return "restrict"
    if any(token in content for token in ("链接", "link")):
        return "link"
    if any(token in content for token in ("报告", "report")):
        return "report"
    if any(token in content for token in ("选择", "拾取", "select", "picker")):
        return "select"
    if any(token in content for token in ("平移", "pan")):
        return "pan"
    if any(token in content for token in ("视图全部", "适配全部", "view all", "fit")):
        return "fit_view"
    if any(token in content for token in ("测量", "measure")):
        return "measure"
    if any(token in content for token in ("背景", "background")):
        return "background"
    if any(token in content for token in ("对象", "object")):
        return "object"
    if any(token in content for token in ("校验", "检查", "质控", "qc", "validate", "check")):
        return "validate"
    if any(token in content for token in ("运行", "run simulation", "flow simulation")):
        return "run"
    if any(token in content for token in ("结果", "result")):
        return "result"
    if any(token in content for token in ("图层", "layer")):
        return "layer"
    if any(token in content for token in ("压力", "pressure")):
        return "pressure"
    if any(token in content for token in ("饱和度", "saturation")):
        return "saturation"
    if any(token in content for token in ("渗透率", "相渗", "permeability")):
        return "permeability"
    if any(token in content for token in ("孔隙", "poro")):
        return "porosity"
    if any(token in content for token in ("有效网格", "actnum")):
        return "actnum"
    if any(token in content for token in ("形状因子", "sigma")):
        return "sigma"
    if any(token in content for token in ("裂缝", "fracture", "dfn")):
        return "fracture"
    if any(token in content for token in ("井", "well")):
        return "well"
    if any(token in content for token in ("初始", "initial")):
        return "initial"
    if any(token in content for token in ("输出控制", "输出", "output")):
        return "output"
    if any(token in content for token in ("岩石", "rock", "petrophysical")):
        return "rock"
    if any(token in content for token in ("网格加密", "局部网格", "lgr")):
        return "lgr"
    if any(token in content for token in ("网格", "grid", "mesh")):
        return "grid"
    if any(token in content for token in ("模拟", "simulation")):
        return "solver"
    if any(token in content for token in ("曲线", "图表", "plot", "chart")):
        return "chart"
    return canonical_icon_kind(kind)


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
