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
                    z1 = get_z(i, j, k, is_bottom=0, is_y_plus=0, is_x_plus=0)
                    z2 = get_z(i, j, k, is_bottom=0, is_y_plus=0, is_x_plus=1)
                    z3 = get_z(i, j, k, is_bottom=0, is_y_plus=1, is_x_plus=1)
                    z4 = get_z(i, j, k, is_bottom=0, is_y_plus=1, is_x_plus=0)
                    
                    z5 = get_z(i, j, k, is_bottom=1, is_y_plus=0, is_x_plus=0)
                    z6 = get_z(i, j, k, is_bottom=1, is_y_plus=0, is_x_plus=1)
                    z7 = get_z(i, j, k, is_bottom=1, is_y_plus=1, is_x_plus=1)
                    z8 = get_z(i, j, k, is_bottom=1, is_y_plus=1, is_x_plus=0)
                    
                    # 强行撑开 1 米，绝对不可能再被 C++ 精度抹掉
                    if z1 <= z5: z1 = z5 + EPSILON
                    if z2 <= z6: z2 = z6 + EPSILON
                    if z3 <= z7: z3 = z7 + EPSILON
                    if z4 <= z8: z4 = z8 + EPSILON
                    
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