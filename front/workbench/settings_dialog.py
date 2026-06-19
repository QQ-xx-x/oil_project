# -*- coding: utf-8 -*-
"""从工程输入树打开的参数设置对话框。"""

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QLabel,
    QLineEdit, QPlainTextEdit, QPushButton, QScrollArea, QTabWidget,
    QVBoxLayout, QWidget,
)


class ObjectSettingsDialog(QDialog):
    def __init__(self, object_name, object_type="工程对象", parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{object_name} 的设置")
        self.resize(430, 330)
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)

        tabs = QTabWidget()
        tabs.addTab(self._info_tab(object_name, object_type), "信息")
        tabs.addTab(self._comments_tab(), "备注")
        root.addWidget(tabs, 1)

        buttons = QDialogButtonBox()
        apply_button = QPushButton("应用")
        ok_button = QPushButton("确定")
        cancel_button = QPushButton("取消")
        buttons.addButton(apply_button, QDialogButtonBox.ApplyRole)
        buttons.addButton(ok_button, QDialogButtonBox.AcceptRole)
        buttons.addButton(cancel_button, QDialogButtonBox.RejectRole)
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        root.addWidget(buttons)

    def _info_tab(self, object_name, object_type):
        page = QWidget()
        layout = QFormLayout(page)
        layout.setContentsMargins(12, 12, 12, 8)
        layout.setSpacing(8)

        name = QLineEdit(object_name)
        color_row = QHBoxLayout()
        color = QComboBox()
        color.addItems(["蓝色", "红色", "绿色", "黄色", "青色"])
        color_row.addWidget(color, 1)
        color_hint = QLabel("●")
        color_hint.setStyleSheet("color: #00aeea; font-size: 20px;")
        color_hint.setAlignment(Qt.AlignCenter)
        color_row.addWidget(color_hint)

        object_type_box = QComboBox()
        object_type_box.addItems([
            object_type, "井对象", "网格对象", "裂缝对象", "流体相", "模拟参数",
        ])

        layout.addRow("名称:", name)
        layout.addRow("颜色:", color_row)
        layout.addRow("类型:", object_type_box)
        layout.addRow("工程文件:", QLabel("对象随工程保存"))
        layout.addRow("原始文件:", QLabel("由平台管理"))
        return page

    def _comments_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(8, 8, 8, 8)
        comments = QPlainTextEdit()
        comments.setPlaceholderText("在这里记录对象说明、来源或参数备注。")
        layout.addWidget(comments)
        return page


class ParameterSettingsDialog(QDialog):
    """Wrap a legacy parameter panel in a project-tree style dialog."""

    values_applied = pyqtSignal(dict)

    def __init__(self, module_key, module_title, panel_factory, project_state,
                 object_type="参数模块", parent=None):
        super().__init__(parent)
        self.module_key = module_key
        self.project_state = project_state
        self.values_were_applied = False
        self.panel = panel_factory()
        self._restore_saved_values()
        self.setObjectName("parameterSettingsDialog")
        self.setWindowTitle(f"{module_title} 参数设置")
        if self.panel.objectName() in {"caseDataPanel", "caseDataKeywordPanel"}:
            self.resize(920, 650)
        else:
            self.resize(560, 520)

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        tabs = QTabWidget()
        tabs.addTab(self._parameter_tab(), "参数")
        tabs.addTab(self._info_tab(module_title, object_type), "信息")
        tabs.addTab(self._comments_tab(), "备注")
        root.addWidget(tabs, 1)

        buttons = QDialogButtonBox()
        apply_button = QPushButton("应用")
        ok_button = QPushButton("确定")
        cancel_button = QPushButton("取消")
        buttons.addButton(apply_button, QDialogButtonBox.ApplyRole)
        buttons.addButton(ok_button, QDialogButtonBox.AcceptRole)
        buttons.addButton(cancel_button, QDialogButtonBox.RejectRole)
        apply_button.clicked.connect(self.apply_values)
        ok_button.clicked.connect(self._accept_with_apply)
        cancel_button.clicked.connect(self.reject)
        root.addWidget(buttons)

    def _parameter_tab(self):
        if self.panel.objectName() in {"caseDataPanel", "caseDataKeywordPanel"}:
            return self.panel
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        holder = QWidget()
        layout = QVBoxLayout(holder)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.addWidget(self.panel)
        layout.addStretch()
        scroll.setWidget(holder)
        return scroll

    def _info_tab(self, module_title, object_type):
        page = QWidget()
        layout = QFormLayout(page)
        layout.setContentsMargins(12, 12, 12, 8)
        layout.setSpacing(8)
        layout.addRow("名称:", QLineEdit(module_title))
        layout.addRow("类型:", QLabel(object_type))
        layout.addRow("状态:", QLabel("双击打开参数，勾选控制是否参与当前工程。"))
        saved = self.project_state.get_module_values(self.module_key)
        layout.addRow("已保存参数:", QLabel(f"{len(saved)} 项" if saved else "尚未应用"))
        return page

    def _comments_tab(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(8, 8, 8, 8)
        comments = QPlainTextEdit()
        comments.setPlaceholderText("记录该参数模块的来源、假设或调参说明。")
        layout.addWidget(comments)
        return page

    def apply_values(self):
        if hasattr(self.panel, "get_values"):
            values = self.panel.get_values()
            self.project_state.set_module_values(self.module_key, values)
            self.values_were_applied = True
            self.values_applied.emit(dict(values))

    def _accept_with_apply(self):
        self.apply_values()
        self.accept()

    def _restore_saved_values(self):
        values = self.project_state.get_module_values(self.module_key)
        if not values:
            return
        attr_overrides = {
            "enable_dual_porosity": "check_enable",
            "k_fracture_x": "spin_k_fx",
            "k_fracture_y": "spin_k_fy",
            "k_fracture_z": "spin_k_fz",
            "matrix_volume_fraction": "spin_matrix_vol_frac",
            "fracture_volume_fraction": "spin_fracture_vol_frac",
            "wr_shape_factor": "spin_wr_shape_factor",
            "gas_Mg": "spin_gas_mg",
            "gas_Tc": "spin_gas_tc",
            "gas_Pc_bar": "spin_gas_pc_bar",
            "gas_table_Pmin_bar": "spin_gas_table_pmin_bar",
            "gas_table_Pmax_bar": "spin_gas_table_pmax_bar",
            "x": "spin_well_x",
            "y": "spin_well_y",
            "z": "spin_well_z",
            "pressure": "spin_well_pressure",
            "radius": "spin_well_radius",
            "WI": "spin_well_WI",
            "grdecl_file": "edit_grdecl_file",
            "coord_file": "edit_coord_file",
            "zcorn_file": "edit_zcorn_file",
            "enable_lgr": "check_enable_lgr",
            "d_threshold": "spin_d_threshold",
        }
        lower_attrs = {name.lower(): name for name in dir(self.panel)}
        for key, value in values.items():
            candidates = [
                attr_overrides.get(key),
                f"spin_{key}",
                f"check_{key}",
                key,
            ]
            target = None
            for candidate in candidates:
                if not candidate:
                    continue
                attr_name = lower_attrs.get(candidate.lower())
                if attr_name:
                    target = getattr(self.panel, attr_name)
                    break
            if target is None:
                continue
            if isinstance(value, bool) and hasattr(target, "setChecked"):
                target.setChecked(value)
            elif hasattr(target, "setValue"):
                target.setValue(value)
            elif hasattr(target, "setText"):
                target.setText(str(value))
