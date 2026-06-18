# case_dataset 算法对接说明

## 1. 定位

`case_dataset` 是 UI 从 `uniform_data/casedata` 及其引用文件生成的标准输入数据目录。算法侧不要再直接依赖用户电脑上的原始 `uniform_data.txt`、`grid.inc`、属性文件绝对路径，而应该以 `case_dataset` 目录为统一入口读取。

推荐入口：

```text
dataset_dir/
  manifest.json
  config.json
  case_sections.json
  arrays.npz
  dfn.json
  validation.json
  raw/
```

其中：

- `manifest.json`：总索引，记录 schema 版本、各文件名、数组摘要、来源文件记录。
- `config.json`：从 `uniform_data` 解析出的普通配置参数。
- `case_sections.json`：CaseData 原始 section/keyword 结构，供 UI 或调试查看。
- `arrays.npz`：核心数值数组，算法主要读取这个文件。
- `dfn.json`：裂缝几何数据。
- `validation.json`：构建时的校验结果。
- `raw/`：原始输入文件备份，仅用于追溯，不建议作为算法主输入。

## 2. 路径规则

算法侧只需要一个参数：

```text
dataset_dir = "某个 case_dataset 目录"
```

读取内部文件时，以 `dataset_dir` 为根目录拼接 `manifest.json` 中的相对路径：

```python
arrays_path = os.path.join(dataset_dir, manifest["arrays_file"])
config_path = os.path.join(dataset_dir, manifest["config_file"])
```

注意：

- `manifest["source_case_file"]`
- `manifest["source_files"][xxx]["path"]`
- `manifest["arrays"][xxx]["source_path"]`

这些字段是原始来源记录，可能是某台电脑上的绝对路径。它们只用于调试和追溯，不应该作为跨电脑运行依赖。

## 3. Python 参考读取接口

UI 侧已经提供参考实现：

```python
from front.workbench.case_dataset_reader import load_case_dataset

dataset = load_case_dataset("D:/project/case_dataset")

print(dataset.grid.nx, dataset.grid.ny, dataset.grid.nz)
coord = dataset.grid.coord
zcorn = dataset.grid.zcorn
actnum = dataset.grid.actnum

matrix_phi = dataset.properties["matrix_phi"]
matrix_phi_valid = dataset.valid_masks["matrix_phi"]
matrix_phi_effective = dataset.valid_values("matrix_phi")
```

也可以用命令行自检：

```bash
python -m front.workbench.case_dataset_reader D:/project/case_dataset
```

如果 `validation.json` 里有错误，默认会抛出异常；警告不会阻断读取。

## 4. 数组命名

`arrays.npz` 中目前使用以下稳定键名：

### 网格数组

| 键名 | 含义 |
| --- | --- |
| `grid_coord` | `grid.inc` 中的 COORD 数组 |
| `grid_zcorn` | `grid.inc` 中的 ZCORN 数组 |
| `grid_actnum` | `grid.inc` 中的 ACTNUM 数组 |
| `mask_active` | `grid_actnum == 1` 的布尔掩码 |

### 属性数组

| 键名 | 原 CaseData 关键字 | 含义 |
| --- | --- | --- |
| `matrix_phi` | `matrix_phi_file` | 基质孔隙度 |
| `matrix_kx` | `matrix_kx_file` | 基质 X 方向渗透率 |
| `matrix_ky` | `matrix_ky_file` | 基质 Y 方向渗透率 |
| `matrix_kz` | `matrix_kz_file` | 基质 Z 方向渗透率 |
| `fracture_phi` | `fracture_phi_file` | 裂缝等效孔隙度 |
| `fracture_kx` | `fracture_kx_file` | 裂缝等效 X 方向渗透率 |
| `fracture_ky` | `fracture_ky_file` | 裂缝等效 Y 方向渗透率 |
| `fracture_kz` | `fracture_kz_file` | 裂缝等效 Z 方向渗透率 |
| `sigma` | `sigma_file` | 形状因子 |
| `actnum_property` | `actnum_file` | 可选属性 ACTNUM 文件 |

每个属性数组如果存在，会配套一个有效值掩码：

```text
mask_matrix_phi_valid
mask_matrix_kx_valid
mask_matrix_ky_valid
mask_matrix_kz_valid
mask_fracture_phi_valid
mask_fracture_kx_valid
mask_fracture_ky_valid
mask_fracture_kz_valid
mask_sigma_valid
mask_actnum_property_valid
```

## 5. 有效值规则

前端和数据包当前约定：

```text
有效属性值 = grid_actnum == 1 and value != 99999
```

因此算法展示或统计属性数组时应跳过：

- `ACTNUM = 0` 的非活跃网格。
- 属性值为 `99999` 的无效值。

推荐读取方式：

```python
values = dataset.properties["matrix_phi"]
mask = dataset.valid_masks["matrix_phi"]
effective_values = values[mask]
```

如果 C++ 直接读取 `arrays.npz`，也需要读取对应的 `mask_xxx_valid` 掩码。

## 6. 配置参数

`config.json` 结构：

```json
{
  "schema_version": "case_dataset_v1",
  "config": {
    "lgr": {},
    "fluid": {},
    "gas": {},
    "initial": {},
    "well": {},
    "solver": {}
  }
}
```

算法侧建议读取 `config` 内部字段，不要直接依赖 UI 控件名。

## 7. 裂缝几何

`dfn.json` 结构：

```json
{
  "schema_version": "case_dataset_v1",
  "dfn": {
    "fracture_count": 200,
    "fractures": [],
    "bbox_min": [],
    "bbox_max": []
  }
}
```

如果 CaseData 没有提供裂缝文件，`dfn` 可能为 `null`，算法侧需要允许这种情况。

## 8. 推荐算法接入方式

短期推荐：

1. UI 生成 `case_dataset`。
2. UI 把 `dataset_dir` 传给 Python 运行入口。
3. Python 用 `case_dataset_reader.py` 读取。
4. Python 通过 pybind 把 `grid/property/config/dfn` 传给 C++。

中长期也可以由 C++ 直接读取 `case_dataset`，但需要 C++ 支持：

- 读取 JSON。
- 读取 `.npz` 或改为算法侧更方便的二进制格式。
- 按同样的数组键名和有效值规则处理数据。

## 9. 当前注意事项

- `arrays.npz` 是二进制压缩文件，不能用文本编辑器查看。
- `source_files.path` 是来源记录，不是算法运行路径。
- 当前缺少可选 `actnum_file` 时可能有 1 个 warning；只要 `grid_actnum` 存在，这不影响主流程。
- 如果 UI 修改并保存了 CaseData 参数，需要重新生成 `case_dataset`，否则旧数据包不代表最新输入。
