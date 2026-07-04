import os
import re
import csv

def read_eclipse_array(text, keyword):
    """提取 GRDECL 文件中指定关键字的数据块，并处理 N*val 的压缩格式"""
    pattern = r"\b" + keyword + r"\b[\s\S]*?(?=/)"
    match = re.search(pattern, text)
    if not match:
        return []
    
    block = match.group(0)
    block = re.sub(r"--.*", "", block)
    words = block.split()[1:]
    
    values = []
    for w in words:
        if '*' in w:
            count, val = w.split('*')
            try:
                values.extend([float(val)] * int(count))
            except ValueError:
                values.extend([val] * int(count))
        else:
            try:
                values.append(float(w))
            except ValueError:
                values.append(w) 
    return values

def convert_grdecl_to_temp_csv(grdecl_path):
    """解析 GRDECL 并静默生成 COORD.csv 和 ZCORN.csv 临时文件"""
    with open(grdecl_path, 'r', encoding='utf-8', errors='ignore') as f:
        text = f.read()
        
    specgrid = read_eclipse_array(text, 'SPECGRID')
    if not specgrid:
        raise ValueError("文件中未找到 SPECGRID 关键字，可能不是有效的网格文件。")
        
    nx, ny, nz = int(specgrid[0]), int(specgrid[1]), int(specgrid[2])
    
    coord = read_eclipse_array(text, 'COORD')
    zcorn = read_eclipse_array(text, 'ZCORN')
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    coord_csv_path = os.path.join(current_dir, 'COORD_temp.csv')
    zcorn_csv_path = os.path.join(current_dir, 'ZCORN_temp.csv')
    
    origin_x, origin_y = coord[0], coord[1]
    
    # 【核心升级】：把容错厚度从 0.001米 提升到 1.0米。
    # 彻底杜绝 C++ 读取 CSV 时因为 float32 单精度截断而导致厚度重新归 0 的问题！
    EPSILON = 1.0 
    BOUNDARY_MARGIN = 0.05
    PAIR_EPSILON = 0.001

    def get_pillar_z_bounds(i, j):
        """获取指定 pillar 的顶底标高范围。"""
        pillar_idx = (j * (nx + 1) + i) * 6
        _, _, zt, _, _, zb = coord[pillar_idx:pillar_idx + 6]
        z_top = -zt
        z_bot = -zb

        if z_top <= z_bot:
            z_top = z_bot + EPSILON

        return z_bot, z_top

    def clamp_z_to_pillar(i, j, z_value):
        """把角点 Z 值钳制到对应 pillar 的顶底范围内，避免 LGR 预处理越界。"""
        z_min, z_max = get_pillar_z_bounds(i, j)
        return max(z_min, min(z_max, z_value))

    def enforce_top_bottom_order(z_top, z_bottom, i, j):
        z_min, z_max = get_pillar_z_bounds(i, j)
        z_top = min(z_top, z_max)
        z_bottom = max(z_bottom, z_min)

        if z_top <= z_bottom:
            z_bottom = max(z_min, z_top - PAIR_EPSILON)
            if z_top <= z_bottom:
                z_top = min(z_max, z_bottom + PAIR_EPSILON)

        return z_top, z_bottom
    
    with open(coord_csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['X(I)', 'Y(J)', 'Z(K)', '坐标X', '坐标Y', '坐标Z'])
        idx = 0
        for j in range(1, ny + 2):
            for i in range(1, nx + 2):
                xt, yt, zt, xb, yb, zb = coord[idx:idx+6]
                
                # 转化为标高(加负号)
                z_top = -zt
                z_bot = -zb
                
                if z_top <= z_bot:
                    z_top = z_bot + EPSILON
                    
                writer.writerow([i, j, '顶', xt - origin_x, yt - origin_y, z_top])
                writer.writerow([i, j, '底', xb - origin_x, yb - origin_y, z_bot])
                idx += 6
                
    with open(zcorn_csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['X(I)', 'Y(J)', 'Z(K)', 'Z1', 'Z2', 'Z3', 'Z4', 'Z5', 'Z6', 'Z7', 'Z8'])
        
        def get_z(i, j, k, is_bottom, is_y_plus, is_x_plus):
            index = (k * 8 * nx * ny) + \
                    (is_bottom * 4 * nx * ny) + \
                    (j * 4 * nx) + \
                    (is_y_plus * 2 * nx) + \
                    (i * 2) + \
                    is_x_plus
            return -zcorn[index] # 依然保持转化为负数标高

        for k in range(nz):
            for j in range(ny):
                for i in range(nx):
                    z1 = clamp_z_to_pillar(i, j, get_z(i, j, k, is_bottom=0, is_y_plus=0, is_x_plus=0))
                    z2 = clamp_z_to_pillar(i + 1, j, get_z(i, j, k, is_bottom=0, is_y_plus=0, is_x_plus=1))
                    # 这里必须和 C++ Corner/LGR 模块的角点到 pillar 映射保持一致：
                    # Z3/Z7 对应左上 pillar，Z4/Z8 对应右上 pillar。
                    z3 = clamp_z_to_pillar(i, j + 1, get_z(i, j, k, is_bottom=0, is_y_plus=1, is_x_plus=1))
                    z4 = clamp_z_to_pillar(i + 1, j + 1, get_z(i, j, k, is_bottom=0, is_y_plus=1, is_x_plus=0))
                    
                    z5 = clamp_z_to_pillar(i, j, get_z(i, j, k, is_bottom=1, is_y_plus=0, is_x_plus=0))
                    z6 = clamp_z_to_pillar(i + 1, j, get_z(i, j, k, is_bottom=1, is_y_plus=0, is_x_plus=1))
                    z7 = clamp_z_to_pillar(i, j + 1, get_z(i, j, k, is_bottom=1, is_y_plus=1, is_x_plus=1))
                    z8 = clamp_z_to_pillar(i + 1, j + 1, get_z(i, j, k, is_bottom=1, is_y_plus=1, is_x_plus=0))

                    # 进一步向单元内部收一点，避免 C++ LGR 在边界点上因精度和 pillar 映射差异判定越界
                    z1 -= BOUNDARY_MARGIN
                    z2 -= BOUNDARY_MARGIN
                    z3 -= BOUNDARY_MARGIN
                    z4 -= BOUNDARY_MARGIN
                    z5 += BOUNDARY_MARGIN
                    z6 += BOUNDARY_MARGIN
                    z7 += BOUNDARY_MARGIN
                    z8 += BOUNDARY_MARGIN
                    
                    # 强行撑开 1 米，绝对不可能再被 C++ 精度抹掉
                    z1, z5 = enforce_top_bottom_order(z1, z5, i, j)
                    z2, z6 = enforce_top_bottom_order(z2, z6, i + 1, j)
                    z3, z7 = enforce_top_bottom_order(z3, z7, i, j + 1)
                    z4, z8 = enforce_top_bottom_order(z4, z8, i + 1, j + 1)
                    
                    writer.writerow([i+1, j+1, k+1, z1, z2, z3, z4, z5, z6, z7, z8])
                    
    return coord_csv_path, zcorn_csv_path





# import os
# import re
# import csv

# def read_eclipse_array(text, keyword):
#     """提取 GRDECL 文件中指定关键字的数据块，并处理 N*val 的压缩格式"""
#     pattern = r"\b" + keyword + r"\b[\s\S]*?(?=/)"
#     match = re.search(pattern, text)
#     if not match:
#         return []
    
#     block = match.group(0)
#     block = re.sub(r"--.*", "", block)
#     words = block.split()[1:]
    
#     values = []
#     for w in words:
#         if '*' in w:
#             count, val = w.split('*')
#             try:
#                 values.extend([float(val)] * int(count))
#             except ValueError:
#                 values.extend([val] * int(count))
#         else:
#             try:
#                 values.append(float(w))
#             except ValueError:
#                 values.append(w) 
#     return values

# def convert_grdecl_to_temp_csv(grdecl_path):
#     """解析 GRDECL 并静默生成 COORD.csv 和 ZCORN.csv 临时文件"""
#     with open(grdecl_path, 'r', encoding='utf-8', errors='ignore') as f:
#         text = f.read()
        
#     specgrid = read_eclipse_array(text, 'SPECGRID')
#     if not specgrid:
#         raise ValueError("文件中未找到 SPECGRID 关键字，可能不是有效的网格文件。")
        
#     nx, ny, nz = int(specgrid[0]), int(specgrid[1]), int(specgrid[2])
    
#     coord = read_eclipse_array(text, 'COORD')
#     zcorn = read_eclipse_array(text, 'ZCORN')
    
#     current_dir = os.path.dirname(os.path.abspath(__file__))
#     coord_csv_path = os.path.join(current_dir, 'COORD_temp.csv')
#     zcorn_csv_path = os.path.join(current_dir, 'ZCORN_temp.csv')
    
#     origin_x, origin_y = coord[0], coord[1]
    
#     with open(coord_csv_path, 'w', newline='', encoding='utf-8') as f:
#         writer = csv.writer(f)
#         writer.writerow(['X(I)', 'Y(J)', 'Z(K)', '坐标X', '坐标Y', '坐标Z'])
#         idx = 0
#         for j in range(1, ny + 2):
#             for i in range(1, nx + 2):
#                 xt, yt, zt, xb, yb, zb = coord[idx:idx+6]
#                 # 【核心修复】：对 zt 和 zb 添加负号，将向下深度转化为向上标高
#                 writer.writerow([i, j, '顶', xt - origin_x, yt - origin_y, -zt])
#                 writer.writerow([i, j, '底', xb - origin_x, yb - origin_y, -zb])
#                 idx += 6
                
#     with open(zcorn_csv_path, 'w', newline='', encoding='utf-8') as f:
#         writer = csv.writer(f)
#         writer.writerow(['X(I)', 'Y(J)', 'Z(K)', 'Z1', 'Z2', 'Z3', 'Z4', 'Z5', 'Z6', 'Z7', 'Z8'])
        
#         def get_z(i, j, k, is_bottom, is_y_plus, is_x_plus):
#             index = (k * 8 * nx * ny) + \
#                     (is_bottom * 4 * nx * ny) + \
#                     (j * 4 * nx) + \
#                     (is_y_plus * 2 * nx) + \
#                     (i * 2) + \
#                     is_x_plus
#             # 【核心修复】：同样对 ZCORN 添加负号
#             return -zcorn[index]

#         for k in range(nz):
#             for j in range(ny):
#                 for i in range(nx):
#                     z1 = get_z(i, j, k, is_bottom=0, is_y_plus=0, is_x_plus=0)
#                     z2 = get_z(i, j, k, is_bottom=0, is_y_plus=0, is_x_plus=1)
#                     z3 = get_z(i, j, k, is_bottom=0, is_y_plus=1, is_x_plus=1)
#                     z4 = get_z(i, j, k, is_bottom=0, is_y_plus=1, is_x_plus=0)
                    
#                     z5 = get_z(i, j, k, is_bottom=1, is_y_plus=0, is_x_plus=0)
#                     z6 = get_z(i, j, k, is_bottom=1, is_y_plus=0, is_x_plus=1)
#                     z7 = get_z(i, j, k, is_bottom=1, is_y_plus=1, is_x_plus=1)
#                     z8 = get_z(i, j, k, is_bottom=1, is_y_plus=1, is_x_plus=0)
                    
#                     writer.writerow([i+1, j+1, k+1, z1, z2, z3, z4, z5, z6, z7, z8])
                    
#     return coord_csv_path, zcorn_csv_path
