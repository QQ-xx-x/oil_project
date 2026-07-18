# -*- coding: utf-8 -*-
"""新工程界面使用的工作台原生参数面板。"""

from PyQt5.QtWidgets import (
    QCheckBox, QDoubleSpinBox, QFileDialog, QFrame, QGridLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QPushButton, QSpinBox, QVBoxLayout,
    QWidget,
)

from ..grdecl_parser import convert_grdecl_to_temp_csv


class NoWheelSpinBox(QSpinBox):
    """忽略鼠标滚轮，避免滚动参数页时误改整数参数。"""

    def wheelEvent(self, event):
        event.ignore()


class NoWheelDoubleSpinBox(QDoubleSpinBox):
    """忽略鼠标滚轮，避免滚动参数页时误改浮点参数。"""

    def wheelEvent(self, event):
        event.ignore()


def _panel_layout(widget):
    layout = QVBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(10)
    return layout


def _intro(title, description):
    box = QFrame()
    box.setObjectName("parameterIntro")
    layout = QVBoxLayout(box)
    layout.setContentsMargins(12, 10, 12, 10)
    layout.setSpacing(4)

    title_label = QLabel(title)
    title_label.setObjectName("parameterTitle")
    description_label = QLabel(description)
    description_label.setObjectName("parameterDescription")
    description_label.setWordWrap(True)

    layout.addWidget(title_label)
    layout.addWidget(description_label)
    return box


def _section(title):
    group = QGroupBox(title)
    group.setObjectName("parameterSection")
    grid = QGridLayout(group)
    grid.setContentsMargins(12, 14, 12, 12)
    grid.setHorizontalSpacing(14)
    grid.setVerticalSpacing(8)
    grid.setColumnStretch(0, 1)
    grid.setColumnStretch(1, 0)
    return group, grid


def _spinbox(minimum, maximum, value, step=1):
    spin = NoWheelSpinBox()
    spin.setObjectName("parameterSpinBox")
    spin.setRange(minimum, maximum)
    spin.setSingleStep(step)
    spin.setValue(value)
    spin.setMinimumWidth(170)
    return spin


def _double_spinbox(minimum, maximum, value, decimals=3, step=1.0):
    spin = NoWheelDoubleSpinBox()
    spin.setObjectName("parameterSpinBox")
    spin.setRange(minimum, maximum)
    spin.setDecimals(decimals)
    spin.setSingleStep(step)
    spin.setValue(value)
    spin.setMinimumWidth(170)
    return spin


def _add_row(grid, row, label_text, editor):
    label = QLabel(label_text)
    label.setObjectName("parameterLabel")
    grid.addWidget(label, row, 0)
    grid.addWidget(editor, row, 1)


def _path_picker(line_edit, button_text, caption, file_filter, callback=None):
    holder = QWidget()
    layout = QHBoxLayout(holder)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(4)
    line_edit.setObjectName("parameterPathEdit")
    button = QPushButton(button_text)
    button.setObjectName("parameterBrowseButton")
    button.setFixedWidth(74)

    def choose_file():
        path, _ = QFileDialog.getOpenFileName(holder, caption, "", file_filter)
        if not path:
            return
        if callback is not None:
            callback(path)
        else:
            line_edit.setText(path)

    button.clicked.connect(choose_file)
    layout.addWidget(line_edit, 1)
    layout.addWidget(button)
    return holder


class WorkbenchGridPanel(QWidget):
    """网格数量和模型尺寸参数。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = _panel_layout(self)
        layout.addWidget(_intro(
            "网格参数",
            "设置模型基础网格数量和物理尺寸。"))

        count_group, count_grid = _section("网格数量")
        self.spin_nx = _spinbox(1, 10000, 20)
        self.spin_ny = _spinbox(1, 10000, 10)
        self.spin_nz = _spinbox(1, 10000, 5)
        _add_row(count_grid, 0, "X 方向网格数 Nx", self.spin_nx)
        _add_row(count_grid, 1, "Y 方向网格数 Ny", self.spin_ny)
        _add_row(count_grid, 2, "Z 方向网格数 Nz", self.spin_nz)
        layout.addWidget(count_group)

        size_group, size_grid = _section("模型尺寸")
        self.spin_lx = _double_spinbox(1.0, 1000000.0, 1000.0, decimals=1)
        self.spin_ly = _double_spinbox(1.0, 1000000.0, 500.0, decimals=1)
        self.spin_lz = _double_spinbox(1.0, 1000000.0, 100.0, decimals=1)
        _add_row(size_grid, 0, "X 方向长度 Lx (m)", self.spin_lx)
        _add_row(size_grid, 1, "Y 方向长度 Ly (m)", self.spin_ly)
        _add_row(size_grid, 2, "Z 方向长度 Lz (m)", self.spin_lz)
        layout.addWidget(size_group)

        import_group, import_grid = _section("角点网格导入")
        self.edit_grdecl_file = QLineEdit()
        self.edit_coord_file = QLineEdit()
        self.edit_zcorn_file = QLineEdit()

        _add_row(import_grid, 0, "GRDECL 文件", _path_picker(
            self.edit_grdecl_file, "导入", "导入 GRDECL 网格文件",
            "ECLIPSE Grid Files (*.GRDECL *.grdecl);;All Files (*)",
            self._convert_grdecl))
        _add_row(import_grid, 1, "COORD CSV", _path_picker(
            self.edit_coord_file, "选择", "选择 COORD CSV 文件",
            "CSV Files (*.csv);;All Files (*)"))
        _add_row(import_grid, 2, "ZCORN CSV", _path_picker(
            self.edit_zcorn_file, "选择", "选择 ZCORN CSV 文件",
            "CSV Files (*.csv);;All Files (*)"))
        layout.addWidget(import_group)

        lgr_group, lgr_grid = _section("LGR 加密")
        self.check_enable_lgr = QCheckBox("默认启用角点网格加密")
        self.check_enable_lgr.setObjectName("parameterCheckBox")
        self.check_enable_lgr.setChecked(True)
        self.spin_d_threshold = _double_spinbox(0.0, 1000000.0, 5.05, decimals=3, step=0.1)
        self.spin_lgr_nrx = _spinbox(1, 20, 2)
        self.spin_lgr_nry = _spinbox(1, 20, 2)
        self.spin_lgr_nrz = _spinbox(1, 20, 2)
        lgr_grid.addWidget(self.check_enable_lgr, 0, 0, 1, 2)
        _add_row(lgr_grid, 1, "距离阈值 d_threshold", self.spin_d_threshold)
        _add_row(lgr_grid, 2, "X 向加密数 lgr_nrx", self.spin_lgr_nrx)
        _add_row(lgr_grid, 3, "Y 向加密数 lgr_nry", self.spin_lgr_nry)
        _add_row(lgr_grid, 4, "Z 向加密数 lgr_nrz", self.spin_lgr_nrz)
        layout.addWidget(lgr_group)
        layout.addStretch()

    def get_values(self):
        return {
            "nx": self.spin_nx.value(),
            "ny": self.spin_ny.value(),
            "nz": self.spin_nz.value(),
            "lx": self.spin_lx.value(),
            "ly": self.spin_ly.value(),
            "lz": self.spin_lz.value(),
            "grdecl_file": self.edit_grdecl_file.text().strip(),
            "coord_file": self.edit_coord_file.text().strip(),
            "zcorn_file": self.edit_zcorn_file.text().strip(),
            "corner_grid_refinement": "加密",
            "enable_lgr": self.check_enable_lgr.isChecked(),
            "d_threshold": self.spin_d_threshold.value(),
            "lgr_nrx": self.spin_lgr_nrx.value(),
            "lgr_nry": self.spin_lgr_nry.value(),
            "lgr_nrz": self.spin_lgr_nrz.value(),
        }

    def _convert_grdecl(self, path):
        coord_file, zcorn_file = convert_grdecl_to_temp_csv(path)
        self.edit_grdecl_file.setText(path)
        self.edit_coord_file.setText(coord_file)
        self.edit_zcorn_file.setText(zcorn_file)


class WorkbenchInitialStatePanel(QWidget):
    """初始压力和饱和度参数。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = _panel_layout(self)
        layout.addWidget(_intro(
            "初始状态",
            "设置模拟开始时的压力和相饱和度。"))

        pressure_group, pressure_grid = _section("压力条件")
        self.spin_initial_pressure = _double_spinbox(
            0.0, 1000000.0, 800.0, decimals=2, step=1.0)
        _add_row(pressure_grid, 0, "初始压力 Pressure (bar)", self.spin_initial_pressure)
        layout.addWidget(pressure_group)

        saturation_group, saturation_grid = _section("饱和度条件")
        self.spin_initial_sw = _double_spinbox(
            0.0, 1.0, 0.05, decimals=4, step=0.01)
        self.spin_initial_sg = _double_spinbox(
            0.0, 1.0, 0.9, decimals=4, step=0.01)
        _add_row(saturation_grid, 0, "初始含水饱和度 Sw", self.spin_initial_sw)
        _add_row(saturation_grid, 1, "初始含气饱和度 Sg", self.spin_initial_sg)
        layout.addWidget(saturation_group)
        layout.addStretch()

    def get_values(self):
        return {
            "initial_pressure": self.spin_initial_pressure.value(),
            "initial_sw": self.spin_initial_sw.value(),
            "initial_sg": self.spin_initial_sg.value(),
        }


class WorkbenchMatrixPanel(QWidget):
    """基质孔隙度和渗透率参数。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = _panel_layout(self)
        layout.addWidget(_intro(
            "基质属性",
            "设置基质孔隙度和三个方向渗透率。"))

        porosity_group, porosity_grid = _section("孔隙参数")
        self.spin_porosity = _double_spinbox(
            0.0, 1.0, 0.04, decimals=4, step=0.005)
        _add_row(porosity_grid, 0, "孔隙度 Porosity", self.spin_porosity)
        layout.addWidget(porosity_group)

        permeability_group, permeability_grid = _section("渗透率参数")
        self.spin_perm_x = _double_spinbox(
            0.0, 1000000.0, 0.005, decimals=6, step=0.001)
        self.spin_perm_y = _double_spinbox(
            0.0, 1000000.0, 0.005, decimals=6, step=0.001)
        self.spin_perm_z = _double_spinbox(
            0.0, 1000000.0, 0.005, decimals=6, step=0.001)
        _add_row(permeability_grid, 0, "X 方向渗透率 Kx (Darcy)", self.spin_perm_x)
        _add_row(permeability_grid, 1, "Y 方向渗透率 Ky (Darcy)", self.spin_perm_y)
        _add_row(permeability_grid, 2, "Z 方向渗透率 Kz (Darcy)", self.spin_perm_z)
        layout.addWidget(permeability_group)
        layout.addStretch()

    def get_values(self):
        return {
            "porosity": self.spin_porosity.value(),
            "perm_x": self.spin_perm_x.value(),
            "perm_y": self.spin_perm_y.value(),
            "perm_z": self.spin_perm_z.value(),
        }


class WorkbenchDualPorosityPanel(QWidget):
    """Warren-Root 双重孔隙度参数。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = _panel_layout(self)
        layout.addWidget(_intro(
            "双重介质",
            "设置裂缝介质、体积分数和 Warren-Root 形状因子。"))

        enable_group, enable_grid = _section("启用状态")
        self.check_enable = QCheckBox("启用双重介质模型")
        self.check_enable.setObjectName("parameterCheckBox")
        enable_grid.addWidget(self.check_enable, 0, 0, 1, 2)
        layout.addWidget(enable_group)

        fracture_group, fracture_grid = _section("裂缝介质属性")
        self.spin_phi_fracture = _double_spinbox(0.0, 1.0, 0.4, decimals=4, step=0.01)
        self.spin_k_fx = _double_spinbox(0.0, 1000000.0, 1.0, decimals=6, step=0.1)
        self.spin_k_fy = _double_spinbox(0.0, 1000000.0, 1.0, decimals=6, step=0.1)
        self.spin_k_fz = _double_spinbox(0.0, 1000000.0, 0.1, decimals=6, step=0.01)
        _add_row(fracture_grid, 0, "裂缝孔隙度 phi_fracture", self.spin_phi_fracture)
        _add_row(fracture_grid, 1, "X 方向裂缝渗透率 K_fx (Darcy)", self.spin_k_fx)
        _add_row(fracture_grid, 2, "Y 方向裂缝渗透率 K_fy (Darcy)", self.spin_k_fy)
        _add_row(fracture_grid, 3, "Z 方向裂缝渗透率 K_fz (Darcy)", self.spin_k_fz)
        layout.addWidget(fracture_group)

        coupling_group, coupling_grid = _section("体积分数与耦合")
        self.spin_matrix_vol_frac = _double_spinbox(0.0, 1.0, 0.98, decimals=4, step=0.01)
        self.spin_fracture_vol_frac = _double_spinbox(0.0, 1.0, 0.02, decimals=4, step=0.01)
        self.spin_wr_shape_factor = _double_spinbox(0.0, 1000.0, 0.12, decimals=4, step=0.01)
        _add_row(coupling_grid, 0, "基质体积分数", self.spin_matrix_vol_frac)
        _add_row(coupling_grid, 1, "裂缝体积分数", self.spin_fracture_vol_frac)
        _add_row(coupling_grid, 2, "WR 形状因子", self.spin_wr_shape_factor)
        layout.addWidget(coupling_group)

        self.dual_porosity_widgets = [
            self.spin_phi_fracture, self.spin_k_fx, self.spin_k_fy,
            self.spin_k_fz, self.spin_matrix_vol_frac,
            self.spin_fracture_vol_frac, self.spin_wr_shape_factor,
        ]
        self.check_enable.toggled.connect(self.set_dual_porosity_controls_enabled)
        self.set_dual_porosity_controls_enabled(self.check_enable.isChecked())
        layout.addStretch()

    def set_dual_porosity_controls_enabled(self, enabled):
        for widget in self.dual_porosity_widgets:
            widget.setEnabled(enabled)

    def get_values(self):
        return {
            "enable_dual_porosity": self.check_enable.isChecked(),
            "phi_fracture": self.spin_phi_fracture.value(),
            "k_fracture_x": self.spin_k_fx.value(),
            "k_fracture_y": self.spin_k_fy.value(),
            "k_fracture_z": self.spin_k_fz.value(),
            "matrix_volume_fraction": self.spin_matrix_vol_frac.value(),
            "fracture_volume_fraction": self.spin_fracture_vol_frac.value(),
            "wr_shape_factor": self.spin_wr_shape_factor.value(),
        }


class WorkbenchOilWaterPanel(QWidget):
    """油水相参数。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = _panel_layout(self)
        layout.addWidget(_intro(
            "油水相基础参数",
            "设置油水相黏度、压缩系数、参考压力和端点饱和度。"))

        viscosity_group, viscosity_grid = _section("黏度与压缩性")
        self.spin_mu_w = _double_spinbox(0.0, 1000.0, 1.0, decimals=4, step=0.1)
        self.spin_mu_o = _double_spinbox(0.0, 1000.0, 5.0, decimals=4, step=0.1)
        self.spin_cw = _double_spinbox(0.0, 1.0, 1e-8, decimals=8, step=1e-8)
        self.spin_co = _double_spinbox(0.0, 1.0, 1e-5, decimals=8, step=1e-6)
        _add_row(viscosity_grid, 0, "水相黏度 mu_w (cP)", self.spin_mu_w)
        _add_row(viscosity_grid, 1, "油相黏度 mu_o (cP)", self.spin_mu_o)
        _add_row(viscosity_grid, 2, "水相压缩系数 cw (1/bar)", self.spin_cw)
        _add_row(viscosity_grid, 3, "油相压缩系数 co (1/bar)", self.spin_co)
        layout.addWidget(viscosity_group)

        saturation_group, saturation_grid = _section("参考压力与饱和度")
        self.spin_p_ref = _double_spinbox(0.0, 1000000.0, 100.0, decimals=2, step=1.0)
        self.spin_swi = _double_spinbox(0.0, 1.0, 0.05, decimals=4, step=0.01)
        self.spin_sor = _double_spinbox(0.0, 1.0, 0.01, decimals=4, step=0.01)
        self.spin_sgc = _double_spinbox(0.0, 1.0, 0.05, decimals=4, step=0.01)
        _add_row(saturation_grid, 0, "参考压力 P_ref (bar)", self.spin_p_ref)
        _add_row(saturation_grid, 1, "束缚水饱和度 Swi", self.spin_swi)
        _add_row(saturation_grid, 2, "残余油饱和度 Sor", self.spin_sor)
        _add_row(saturation_grid, 3, "临界气饱和度 Sgc", self.spin_sgc)
        layout.addWidget(saturation_group)
        layout.addStretch()

    def get_values(self):
        return {
            "mu_w": self.spin_mu_w.value(),
            "mu_o": self.spin_mu_o.value(),
            "mu_g": 0.2,
            "cw": self.spin_cw.value(),
            "co": self.spin_co.value(),
            "cg": 1e-3,
            "p_ref": self.spin_p_ref.value(),
            "swi": self.spin_swi.value(),
            "sor": self.spin_sor.value(),
            "sgc": self.spin_sgc.value(),
        }


class WorkbenchGasPvtPanel(QWidget):
    """真实气体 PVT 表参数。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = _panel_layout(self)
        layout.addWidget(_intro(
            "气相真实气体 PVT",
            "设置气体组分参数和 PVT 表的压力范围。"))

        gas_group, gas_grid = _section("气体物性")
        self.spin_gas_t_c = _double_spinbox(-273.15, 1000.0, 140.0, decimals=2, step=1.0)
        self.spin_gas_mg = _double_spinbox(0.0, 1000.0, 16.04, decimals=4, step=0.1)
        self.spin_gas_tc = _double_spinbox(0.0, 5000.0, 190.58, decimals=2, step=1.0)
        self.spin_gas_pc_bar = _double_spinbox(0.0, 10000.0, 45.44, decimals=2, step=1.0)
        _add_row(gas_grid, 0, "地层温度 gas_t_C (°C)", self.spin_gas_t_c)
        _add_row(gas_grid, 1, "摩尔质量 Mg", self.spin_gas_mg)
        _add_row(gas_grid, 2, "临界温度 Tc (K)", self.spin_gas_tc)
        _add_row(gas_grid, 3, "临界压力 Pc (bar)", self.spin_gas_pc_bar)
        layout.addWidget(gas_group)

        table_group, table_grid = _section("PVT 表")
        self.spin_gas_table_pmin_bar = _double_spinbox(
            0.0, 1000000.0, 1.0, decimals=2, step=1.0)
        self.spin_gas_table_pmax_bar = _double_spinbox(
            0.0, 1000000.0, 1000.0, decimals=2, step=10.0)
        self.spin_gas_table_n = _spinbox(2, 100000, 2000, step=100)
        _add_row(table_grid, 0, "压力下限 Pmin (bar)", self.spin_gas_table_pmin_bar)
        _add_row(table_grid, 1, "压力上限 Pmax (bar)", self.spin_gas_table_pmax_bar)
        _add_row(table_grid, 2, "采样点数 n", self.spin_gas_table_n)
        layout.addWidget(table_group)
        layout.addStretch()

    def get_values(self):
        return {
            "gas_t_C": self.spin_gas_t_c.value(),
            "gas_Mg": self.spin_gas_mg.value(),
            "gas_Tc": self.spin_gas_tc.value(),
            "gas_Pc_bar": self.spin_gas_pc_bar.value(),
            "gas_table_Pmin_bar": self.spin_gas_table_pmin_bar.value(),
            "gas_table_Pmax_bar": self.spin_gas_table_pmax_bar.value(),
            "gas_table_n": self.spin_gas_table_n.value(),
        }


class WorkbenchWellPanel(QWidget):
    """井位和控制参数。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = _panel_layout(self)
        layout.addWidget(_intro(
            "井基础参数",
            "设置井位置、井底压力、井径和井指数。"))

        location_group, location_grid = _section("井位置")
        self.spin_well_x = _double_spinbox(0.0, 100000.0, 500.0, decimals=2, step=10.0)
        self.spin_well_y = _double_spinbox(0.0, 100000.0, 250.0, decimals=2, step=10.0)
        self.spin_well_z = _double_spinbox(0.0, 10000.0, 50.0, decimals=2, step=1.0)
        _add_row(location_grid, 0, "X 坐标 (m)", self.spin_well_x)
        _add_row(location_grid, 1, "Y 坐标 (m)", self.spin_well_y)
        _add_row(location_grid, 2, "Z 坐标 (m)", self.spin_well_z)
        layout.addWidget(location_group)

        control_group, control_grid = _section("井控制")
        self.spin_well_pressure = _double_spinbox(0.0, 100000.0, 50.0, decimals=2, step=1.0)
        self.spin_well_radius = _double_spinbox(0.001, 100.0, 0.05, decimals=3, step=0.001)
        self.spin_well_WI = _double_spinbox(0.0, 1000000.0, 0.0, decimals=2, step=1.0)
        _add_row(control_grid, 0, "井底压力 P_bhp (bar)", self.spin_well_pressure)
        _add_row(control_grid, 1, "井半径 Radius (m)", self.spin_well_radius)
        _add_row(control_grid, 2, "井指数 WI", self.spin_well_WI)
        layout.addWidget(control_group)
        layout.addStretch()

    def get_values(self):
        return {
            "x": self.spin_well_x.value(),
            "y": self.spin_well_y.value(),
            "z": self.spin_well_z.value(),
            "pressure": self.spin_well_pressure.value(),
            "radius": self.spin_well_radius.value(),
            "WI": self.spin_well_WI.value(),
        }


class WorkbenchNaturalFracturesPanel(QWidget):
    """天然裂缝参数。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = _panel_layout(self)
        layout.addWidget(_intro(
            "天然裂缝",
            "设置天然裂缝数量、长度范围、开度和渗透率。"))

        group, grid = _section("天然裂缝属性")
        self.spin_num_fracs = _spinbox(0, 500, 100)
        self.spin_min_len = _double_spinbox(0.0, 100000.0, 10.0, decimals=2, step=1.0)
        self.spin_max_len = _double_spinbox(0.0, 100000.0, 20.0, decimals=2, step=1.0)
        self.spin_aperture = _double_spinbox(0.0, 10.0, 0.1, decimals=4, step=0.001)
        self.spin_perm = _double_spinbox(0.0, 1000000.0, 100.0, decimals=2, step=10.0)
        _add_row(grid, 0, "裂缝数量", self.spin_num_fracs)
        _add_row(grid, 1, "最小长度 Min Length (m)", self.spin_min_len)
        _add_row(grid, 2, "最大长度 Max Length (m)", self.spin_max_len)
        _add_row(grid, 3, "开度 Aperture (m)", self.spin_aperture)
        _add_row(grid, 4, "渗透率 Permeability (D)", self.spin_perm)
        layout.addWidget(group)
        layout.addStretch()

    def get_values(self):
        return {
            "num_fracs": self.spin_num_fracs.value(),
            "min_len": self.spin_min_len.value(),
            "max_len": self.spin_max_len.value(),
            "aperture": self.spin_aperture.value(),
            "perm": self.spin_perm.value(),
        }


class WorkbenchHydraulicFracturesPanel(QWidget):
    """人工裂缝参数。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = _panel_layout(self)
        layout.addWidget(_intro(
            "人工裂缝",
            "设置压裂段数、裂缝几何尺寸、渗透率和导流能力。"))

        geometry_group, geometry_grid = _section("裂缝几何")
        self.spin_num_stages = _spinbox(1, 50, 20)
        self.spin_spacing_x = _double_spinbox(0.0, 100000.0, 31.58, decimals=2, step=1.0)
        self.spin_length = _double_spinbox(0.0, 10000.0, 120.0, decimals=2, step=1.0)
        self.spin_height = _double_spinbox(0.0, 1000.0, 30.0, decimals=2, step=1.0)
        _add_row(geometry_grid, 0, "压裂段数", self.spin_num_stages)
        _add_row(geometry_grid, 1, "裂缝间距 Fracture Spacing (m)", self.spin_spacing_x)
        _add_row(geometry_grid, 2, "裂缝总长度 Length (m)", self.spin_length)
        _add_row(geometry_grid, 3, "缝高 (m)", self.spin_height)
        layout.addWidget(geometry_group)

        property_group, property_grid = _section("裂缝属性")
        self.spin_aperture = _double_spinbox(0.0, 10.0, 0.1, decimals=4, step=0.001)
        self.spin_perm = _double_spinbox(0.0, 1000000.0, 1000.0, decimals=2, step=10.0)
        self.spin_conductivity = _double_spinbox(
            0.0, 1000000.0, 100.0, decimals=2, step=10.0)
        _add_row(property_grid, 0, "开度 Aperture (m)", self.spin_aperture)
        _add_row(property_grid, 1, "渗透率 Permeability (D)", self.spin_perm)
        _add_row(property_grid, 2, "导流能力 Conductivity (D·m)", self.spin_conductivity)
        layout.addWidget(property_group)
        layout.addStretch()

    def get_values(self):
        return {
            "num_stages": self.spin_num_stages.value(),
            "spacing_x": self.spin_spacing_x.value(),
            "length": self.spin_length.value(),
            "height": self.spin_height.value(),
            "aperture": self.spin_aperture.value(),
            "perm": self.spin_perm.value(),
            "conductivity": self.spin_conductivity.value(),
        }


class WorkbenchSimulationPanel(QWidget):
    """模拟时间控制参数。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = _panel_layout(self)
        layout.addWidget(_intro(
            "模拟控制",
            "设置模拟总时长和基础时间步长。"))

        group, grid = _section("时间控制")
        self.spin_simulation_time = _double_spinbox(
            0.0, 1000000.0, 100.0, decimals=3, step=1.0)
        self.spin_time_step = _double_spinbox(
            0.0, 1000000.0, 1.0, decimals=4, step=0.1)
        _add_row(grid, 0, "模拟时间 Simulation Time (days)", self.spin_simulation_time)
        _add_row(grid, 1, "时间步长 Time Step (days)", self.spin_time_step)
        layout.addWidget(group)
        layout.addStretch()

    def get_values(self):
        return {
            "simulation_time": self.spin_simulation_time.value(),
            "time_step": self.spin_time_step.value(),
        }
