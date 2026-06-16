"""
uniform_parser.py — 独立解析函数模块

提供 4 个独立解析函数，每个函数接收一个文件路径，返回对应的结构化数据。

用法:
    from front.uniform_parser import parse_config, parse_grid, parse_property, parse_dfn

    # 1. 读取 uniform_data.txt 中的键值参数
    cfg = parse_config("uniform_data.txt")
    print(cfg['fluid']['mu_w'])          # 1.0

    # 2. 解析 grid.inc
    grid = parse_grid("tn模型数据/grid.inc")
    print(grid['nx'], grid['ny'], grid['nz'])   # 132 160 10

    # 3. 解析属性文件 (MATRIX_*.txt, DFN_*.txt, SIGMA.txt, ACTNUM.txt)
    phi = parse_property("tn模型数据/MATRIX_PORO.txt")
    print(len(phi))                      # 211200

    # 4. 解析 dfn.txt
    dfn = parse_dfn("tn模型数据/dfn.txt")
    print(len(dfn['fractures']))         # 200
"""

import os
import re
from typing import Any, Dict, List, Optional, Tuple


# ============================================================
# 公共工具函数
# ============================================================

def _split_tokens(text: str) -> List[str]:
    return text.strip().split()


def _is_n_star_value(token: str) -> bool:
    return '*' in token and not token.startswith('*')


def _expand_rle_token(token: str) -> List[float]:
    if _is_n_star_value(token):
        parts = token.split('*', 1)
        n = int(parts[0])
        val = float(parts[1])
        return [val] * n
    else:
        return [float(token)]


def expand_rle(text: str, expected_len: Optional[int] = None) -> List[float]:
    """展开 RLE 压缩数组：133*99999 → 133 个 99999.0"""
    tokens = _split_tokens(text)
    tokens = [t for t in tokens if t and t != '/']  # 过滤 / 终止符
    result: List[float] = []
    for token in tokens:
        result.extend(_expand_rle_token(token))
    if expected_len is not None and len(result) != expected_len:
        raise ValueError(f"RLE 展开长度 {len(result)} != 预期 {expected_len}")
    return result


def _read_text(path: str) -> str:
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def _parse_section_value(raw: str) -> Any:
    """字符串 → Python 类型。"""
    raw = raw.strip()
    if raw.lower() in ('true', 'false'):
        return raw.lower() == 'true'
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        pass
    return raw


# ============================================================
# ① parse_config — 读取 uniform_data.txt 的键值参数
# ============================================================

def parse_config(path: str) -> Dict[str, Any]:
    """解析 uniform_data.txt 中所有 [SECTION] 的 key=value 参数。

    返回:
        {
            'lgr':     {enable_lgr, d_threshold, nrx, nry, nrz},
            'fluid':   {mu_w, mu_o, cw, co, p_ref, swi, sor, sgc, n},
            'gas':     {temperature_c, mole_CH4, ..., gas_table_pmin_bar, ...},
            'initial': {pressure, sw, sg},
            'well':    {producer_bhp, well_radius},
            'solver':  {total_time, dt_init, dt_min, ...},
        }
    """
    text = _read_text(path)

    # 解析所有 [SECTION] 块
    section_names = ['GRID', 'ROCK', 'FRACTURE', 'LGR', 'FLUID',
                     'GAS', 'INITIAL', 'WELL', 'SOLVER', 'OUTPUT', 'WR']
    sections: Dict[str, Dict[str, str]] = {}

    for name in section_names:
        pattern = re.compile(
            rf'\[{re.escape(name)}\](.*?)(?=\[|BEGIN_RETURN_SCHEMA|\Z)', re.DOTALL)
        m = pattern.search(text)
        if not m:
            sections[name] = {}
            continue
        sec: Dict[str, str] = {}
        for line in m.group(1).strip().split('\n'):
            stripped = line.strip()
            if not stripped or stripped.startswith('//'):
                continue
            if '=' in stripped:
                k, _, v = stripped.partition('=')
                sec[k.strip()] = v.strip()
        sections[name] = sec

    # LGR
    lgr = sections.get('LGR', {})
    result_lgr = {
        'enable_lgr':  _parse_section_value(lgr.get('enable_lgr', 'false')),
        'd_threshold': _parse_section_value(lgr.get('d_threshold', '5.05')),
        'nrx':         _parse_section_value(lgr.get('nrx', '2')),
        'nry':         _parse_section_value(lgr.get('nry', '2')),
        'nrz':         _parse_section_value(lgr.get('nrz', '2')),
    }

    # Fluid
    fl = sections.get('FLUID', {})
    result_fluid = {
        'mu_w':   _parse_section_value(fl.get('mu_w', '1.0')),
        'mu_o':   _parse_section_value(fl.get('mu_o', '5.0')),
        'cw':     _parse_section_value(fl.get('cw', '1e-8')),
        'co':     _parse_section_value(fl.get('co', '1e-5')),
        'p_ref':  _parse_section_value(fl.get('p_ref', '100')),
        'swi':    _parse_section_value(fl.get('Swi', '0.05')),
        'sor':    _parse_section_value(fl.get('Sor', '0.01')),
        'sgc':    _parse_section_value(fl.get('Sgc', '0.05')),
        'n':      _parse_section_value(fl.get('n', '2')),
    }

    # Gas
    gs = sections.get('GAS', {})
    result_gas = {
        'temperature_c':       _parse_section_value(gs.get('temperature_C', '140')),
        'mole_CH4':            _parse_section_value(gs.get('mole_CH4', '0.4')),
        'mole_C2H6':           _parse_section_value(gs.get('mole_C2H6', '0.0')),
        'mole_C3H8':           _parse_section_value(gs.get('mole_C3H8', '0.0')),
        'mole_N2':             _parse_section_value(gs.get('mole_N2', '0.0')),
        'mole_CO2':            _parse_section_value(gs.get('mole_CO2', '0.0')),
        'mole_H2O':            _parse_section_value(gs.get('mole_H2O', '0.0')),
        'mole_unknown':        _parse_section_value(gs.get('mole_unknown', '0.0')),
        'gas_table_pmin_bar':  _parse_section_value(gs.get('gas_table_Pmin_bar', '1')),
        'gas_table_pmax_bar':  _parse_section_value(gs.get('gas_table_Pmax_bar', '1000')),
        'gas_table_n':         _parse_section_value(gs.get('gas_table_n', '2000')),
    }

    # Initial
    init = sections.get('INITIAL', {})
    sw = _parse_section_value(init.get('Sw', '0.2'))
    sg = _parse_section_value(init.get('Sg', '0.7'))
    if isinstance(sw, str): sw = float(sw)
    if isinstance(sg, str): sg = float(sg)
    result_initial = {
        'pressure': _parse_section_value(init.get('pressure', '800')),
        'sw': sw,
        'sg': sg,
        'so': 1.0 - sw - sg,
    }

    # Well
    wl = sections.get('WELL', {})
    result_well = {
        'producer_bhp': _parse_section_value(wl.get('producer_bhp', '100')),
        'well_radius':  _parse_section_value(wl.get('well_radius', '0.05')),
    }

    # Solver
    sv = sections.get('SOLVER', {})
    result_solver = {
        'total_time':         _parse_section_value(sv.get('total_time', '1200')),
        'dt_init':            _parse_section_value(sv.get('dt_init', '0.001')),
        'dt_min':             _parse_section_value(sv.get('dt_min', '1e-6')),
        'dt_max':             _parse_section_value(sv.get('dt_max', '30')),
        'newton_max_iter':    _parse_section_value(sv.get('newton_max_iter', '15')),
        'newton_tol':         _parse_section_value(sv.get('newton_tol', '1e-3')),
        'linear_tol':         _parse_section_value(sv.get('linear_tol', '1e-8')),
        'linear_max_iter':    _parse_section_value(sv.get('linear_max_iter', '1000')),
        'dt_cut_factor':      _parse_section_value(sv.get('dt_cut_factor', '0.25')),
        'dt_grow_factor':     _parse_section_value(sv.get('dt_grow_factor', '1.5')),
        'max_timestep_retry': _parse_section_value(sv.get('max_timestep_retry', '20')),
    }

    return {
        'lgr':     result_lgr,
        'fluid':   result_fluid,
        'gas':     result_gas,
        'initial': result_initial,
        'well':    result_well,
        'solver':  result_solver,
    }


# ============================================================
# ② parse_grid — 解析 grid.inc
# ============================================================

def parse_grid(path: str) -> Dict[str, Any]:
    """解析 Eclipse 格式的 grid.inc 文件。

    返回:
        {
            'nx': 132, 'ny': 160, 'nz': 10,
            'total_cell_count': 211200,
            'coord': [128478 个 float],
            'zcorn': [1689600 个 float],
            'actnum': [211200 个 0/1],
            'active_cell_count': 193320,
            'inactive_cell_count': 17880,
            'active_cell_indices': [...],
            'inactive_cell_indices': [...]
        }
    """
    all_lines = [l for l in _read_text(path).split('\n')
                 if not l.strip().startswith('--')]

    def _extract_block(lines: List[str], keyword: str, start_idx: int) \
            -> Tuple[List[str], int]:
        i = start_idx
        while i < len(lines):
            if lines[i].strip() == keyword:
                i += 1
                break
            i += 1
        data_lines: List[str] = []
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                i += 1
                continue
            if line.endswith('/'):
                rest = line[:-1].strip()
                if rest:
                    data_lines.append(rest)
                i += 1
                break
            if line == '/':
                i += 1
                break
            data_lines.append(line)
            i += 1
        return data_lines, i

    # SPECGRID
    sg_m = re.search(r'SPECGRID\s+(.*?)/', '\n'.join(all_lines), re.DOTALL)
    if not sg_m:
        raise ValueError(f"在 {path} 中找不到 SPECGRID")
    sg_tokens = _split_tokens(sg_m.group(1))
    nx = int(sg_tokens[0])
    ny = int(sg_tokens[1])
    nz = int(sg_tokens[2])
    total = nx * ny * nz

    # COORD
    coord_lines, coord_end = _extract_block(all_lines, 'COORD', 0)
    coord_vals = expand_rle(' '.join(coord_lines))

    # ZCORN
    zcorn_lines, zcorn_end = _extract_block(all_lines, 'ZCORN', coord_end)
    zcorn_vals = expand_rle(' '.join(zcorn_lines))

    # ACTNUM
    actnum_lines, _ = _extract_block(all_lines, 'ACTNUM', zcorn_end)
    actnum_text = ' '.join(actnum_lines)
    actnum_vals: List[int] = []
    for tok in _split_tokens(actnum_text):
        if not tok or tok == '/':
            continue
        if _is_n_star_value(tok):
            parts = tok.split('*', 1)
            n = int(parts[0])
            v = int(float(parts[1]))
            actnum_vals.extend([v] * n)
        else:
            actnum_vals.append(int(float(tok)))

    active_count = sum(1 for v in actnum_vals if v == 1)

    return {
        'nx': nx, 'ny': ny, 'nz': nz,
        'total_cell_count': total,
        'coord': coord_vals,
        'zcorn': zcorn_vals,
        'actnum': actnum_vals,
        'active_cell_count': active_count,
        'inactive_cell_count': total - active_count,
        'active_cell_indices': [i for i, v in enumerate(actnum_vals) if v == 1],
        'inactive_cell_indices': [i for i, v in enumerate(actnum_vals) if v == 0],
    }


# ============================================================
# ③ parse_property — 解析属性文件 (MATRIX_*, DFN_*, SIGMA, ACTNUM)
# ============================================================

def parse_property(path: str, expected_len: Optional[int] = None) -> List[float]:
    """解析 tNavigator 属性文件（RLE 压缩格式）。

    支持: MATRIX_PORO.txt, MATRIX_PERMX/Y/Z.txt,
          DFN_PORO.txt, DFN_PERMX/Y/Z.txt,
          SIGMA.txt, ACTNUM.txt

    自动跳过: -- 注释行, Null Value = 99999 头信息, 关键字行 ('MATRIX_PORO')

    返回: 展开后的 float 数组
    """
    text = _read_text(path)
    lines = text.split('\n')

    # 找到数据起始行（跳过 -- 注释、Null Value 声明、关键字行）
    data_lines: List[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith('--'):
            continue
        if 'Null Value' in stripped and '=' in stripped:
            continue
        if stripped.startswith("'") and "'" in stripped[1:]:
            continue
        if stripped == '/':
            continue
        data_lines.append(stripped)

    data_text = ' '.join(data_lines)
    return expand_rle(data_text, expected_len)


def filter_active_values(values: List[float], actnum: Optional[List[int]] = None,
                         null_value: float = 99999.0) -> List[float]:
    """按 actnum==1 且 value != null_value 过滤属性数组。

    如果不提供 actnum，则仅过滤 null_value。
    """
    if actnum is None or len(actnum) == 0:
        return [v for v in values if v != null_value]
    n = min(len(values), len(actnum))
    return [values[i] for i in range(n) if actnum[i] == 1 and values[i] != null_value]


# ============================================================
# ④ parse_dfn — 解析 dfn.txt 裂缝几何文件
# ============================================================

def parse_dfn(path: str) -> Dict[str, Any]:
    """解析 Fracman 格式的 dfn.txt 文件。

    返回:
        {
            'fracture_count': 200, 'node_count': 831, 'property_count': 3,
            'properties': [{property_id:1, name:'Permeability'}, ...],
            'sets': [{set_id:1, set_name:'DFN1'}, ...],
            'fractures': [{
                'fracture_id': 1, 'vertex_count': 5, 'set_id': 1,
                'permeability': 85.41, 'compressibility': 3.4e38,
                'aperture': 1e-6, 'vertices': [[x,y,z], ...],
                'normal': [nx, ny, nz]
            }, ...],
            'bbox_min': [x,y,z], 'bbox_max': [x,y,z]
        }
    """
    text = _read_text(path)

    # --- BEGIN FORMAT ---
    fmt_m = re.search(r'BEGIN FORMAT(.*?)END FORMAT', text, re.DOTALL)
    fmt: Dict[str, str] = {}
    if fmt_m:
        for line in fmt_m.group(1).strip().split('\n'):
            if '=' in line:
                k, _, v = line.partition('=')
                fmt[k.strip()] = v.strip()

    nc = int(fmt.get('No_Fractures', 0))
    nn = int(fmt.get('No_Nodes', 0))
    np = int(fmt.get('No_Properties', 0))

    # --- BEGIN PROPERTIES ---
    prop_m = re.search(r'BEGIN PROPERTIES(.*?)END PROPERTIES', text, re.DOTALL)
    props: List[Dict] = []
    if prop_m:
        for line in prop_m.group(1).strip().split('\n'):
            line = line.strip()
            if not line:
                continue
            m2 = re.match(r'(Prop\d+)\s*=\s*\(.*?\)"(.*?)"', line)
            if m2:
                props.append({
                    'property_id': int(m2.group(1).replace('Prop', '')),
                    'name': m2.group(2),
                })

    # --- BEGIN SETS ---
    sets_m = re.search(r'BEGIN SETS(.*?)END SETS', text, re.DOTALL)
    sets: List[Dict] = []
    if sets_m:
        for line in sets_m.group(1).strip().split('\n'):
            line = line.strip()
            if not line:
                continue
            m2 = re.match(r'(Set\d+)\s*=\s*"(.*?)"', line)
            if m2:
                sets.append({
                    'set_id': int(m2.group(1).replace('Set', '')),
                    'set_name': m2.group(2),
                })

    # --- BEGIN FRACTURE ---
    frac_m = re.search(r'BEGIN FRACTURE(.*)', text, re.DOTALL)
    fractures: List[Dict] = []
    all_vertices: List[List[float]] = []

    if frac_m:
        frac_lines = frac_m.group(1).strip().split('\n')
        i = 0
        while i < len(frac_lines):
            line = frac_lines[i].strip()
            if not line:
                i += 1
                continue
            tokens = _split_tokens(line)
            if len(tokens) < 6:
                i += 1
                continue

            fid = int(tokens[0])
            nv = int(tokens[1])
            sid = int(tokens[2])
            perm = float(tokens[3])
            comp = float(tokens[4])
            apt = float(tokens[5])

            i += 1
            vertices: List[List[float]] = []
            for _ in range(nv):
                if i >= len(frac_lines):
                    break
                vt = _split_tokens(frac_lines[i].strip())
                if len(vt) >= 4:
                    v = [float(vt[1]), float(vt[2]), float(vt[3])]
                    vertices.append(v)
                    all_vertices.append(v)
                i += 1

            normal: List[float] = [0.0, 0.0, 0.0]
            if i < len(frac_lines):
                nt = _split_tokens(frac_lines[i].strip())
                if len(nt) >= 4:
                    normal = [float(nt[1]), float(nt[2]), float(nt[3])]
                i += 1

            fractures.append({
                'fracture_id': fid,
                'vertex_count': nv,
                'set_id': sid,
                'permeability': perm,
                'compressibility': comp,
                'aperture': apt,
                'vertices': vertices,
                'normal': normal,
            })

    # bbox
    bbox_min = [float('inf')] * 3
    bbox_max = [float('-inf')] * 3
    for v in all_vertices:
        for d in range(3):
            if v[d] < bbox_min[d]: bbox_min[d] = v[d]
            if v[d] > bbox_max[d]: bbox_max[d] = v[d]
    if not all_vertices:
        bbox_min = [0.0, 0.0, 0.0]
        bbox_max = [0.0, 0.0, 0.0]

    return {
        'fracture_count': nc,
        'node_count': nn,
        'property_count': np,
        'properties': props,
        'sets': sets,
        'fractures': fractures,
        'bbox_min': bbox_min,
        'bbox_max': bbox_max,
    }


# ============================================================
# 命令行测试入口
# ============================================================

if __name__ == '__main__':
    import sys
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    data_dir = sys.argv[1] if len(sys.argv) > 1 else 'tn模型数据'

    def _res(fname):
        return os.path.join(data_dir, fname) if os.path.isdir(data_dir) else fname

    print("=" * 60)
    print("测试 4 个解析函数")
    print("=" * 60)

    # ① parse_config
    print("\n--- parse_config ---")
    cfg = parse_config('uniform_data.txt')
    print(f"  LGR:     {cfg['lgr']}")
    print(f"  Fluid:   {cfg['fluid']}")
    print(f"  Gas:     {cfg['gas']}")
    print(f"  Initial: {cfg['initial']}")
    print(f"  Well:    {cfg['well']}")
    print(f"  Solver:  {cfg['solver']}")

    # ② parse_grid
    print("\n--- parse_grid ---")
    grid = parse_grid(_res('grid.inc'))
    print(f"  网格: {grid['nx']}x{grid['ny']}x{grid['nz']}")
    print(f"  总单元: {grid['total_cell_count']}  活跃: {grid['active_cell_count']}  非活跃: {grid['inactive_cell_count']}")
    print(f"  COORD: {len(grid['coord'])}, ZCORN: {len(grid['zcorn'])}, ACTNUM: {len(grid['actnum'])}")

    # ③ parse_property
    print("\n--- parse_property ---")
    for fname in ['MATRIX_PORO.txt', 'MATRIX_PERMX.txt', 'DFN_PERMX.txt', 'SIGMA.txt']:
        vals = parse_property(_res(fname))
        print(f"  {fname}: {len(vals)} 值")

    # ④ parse_dfn
    print("\n--- parse_dfn ---")
    dfn = parse_dfn(_res('dfn.txt'))
    print(f"  裂缝: {dfn['fracture_count']} 条, 节点: {dfn['node_count']}")
    print(f"  解析: {len(dfn['fractures'])} 条")
    print(f"  BBOX: {dfn['bbox_min']} → {dfn['bbox_max']}")
    print(f"  第1条: id={dfn['fractures'][0]['fracture_id']}, "
          f"顶点={dfn['fractures'][0]['vertex_count']}, "
          f"渗透率={dfn['fractures'][0]['permeability']}")

    print("\n" + "=" * 60)
    print("4 个函数全部正常")
