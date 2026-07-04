# -*- coding: utf-8 -*-
"""Dialog for selecting the project-level simulation model configuration."""

from PyQt5.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QGroupBox, QHBoxLayout, QLabel,
    QPushButton, QRadioButton, QVBoxLayout,
)

from .project_state import (
    MODEL_TYPE_NORMAL,
    MODEL_TYPE_WR,
    WR_INPUT_MODE_CONSTANT,
    WR_INPUT_MODE_FILE,
    WR_INPUT_MODE_MIXED,
    normalize_model_config,
)


class ModelConfigDialog(QDialog):
    """Small dialog that writes the model mode into ProjectState."""

    def __init__(self, project_state, parent=None):
        super().__init__(parent)
        self.project_state = project_state
        self.setObjectName("modelConfigDialog")
        self.setWindowTitle("模型方案选择")
        self.resize(460, 430)

        current = normalize_model_config(
            getattr(project_state, "model_config", None),
            getattr(project_state, "corner_grid_refinement", None),
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        title = QLabel("选择本工程的模拟方案")
        title.setObjectName("parameterTitle")
        root.addWidget(title)

        hint = QLabel(
            "该选择决定后续数据校验、运行参数和结果解释。输入树只展示当前方案需要的数据。"
        )
        hint.setObjectName("parameterDescription")
        hint.setWordWrap(True)
        root.addWidget(hint)

        root.addWidget(self._model_group(current))
        root.addWidget(self._feature_group(current))
        root.addWidget(self._wr_group(current))
        root.addStretch()

        buttons = QDialogButtonBox()
        ok_button = QPushButton("确定")
        cancel_button = QPushButton("取消")
        buttons.addButton(ok_button, QDialogButtonBox.AcceptRole)
        buttons.addButton(cancel_button, QDialogButtonBox.RejectRole)
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        root.addWidget(buttons)

        self._sync_wr_enabled()
        self.normal_radio.toggled.connect(self._sync_wr_enabled)
        self.wr_radio.toggled.connect(self._sync_wr_enabled)

    def _model_group(self, config):
        group = QGroupBox("模型类型")
        layout = QVBoxLayout(group)
        self.normal_radio = QRadioButton("正常模型")
        self.wr_radio = QRadioButton("WR 双重介质模型")
        self.normal_radio.setChecked(config.get("model_type") != MODEL_TYPE_WR)
        self.wr_radio.setChecked(config.get("model_type") == MODEL_TYPE_WR)
        layout.addWidget(self.normal_radio)
        layout.addWidget(self.wr_radio)
        return group

    def _feature_group(self, config):
        group = QGroupBox("功能模块")
        layout = QVBoxLayout(group)
        self.lgr_check = QCheckBox("LGR 加密")
        self.natural_fracture_check = QCheckBox("天然裂缝 DFN")
        self.hydraulic_fracture_check = QCheckBox("人工裂缝")
        self.real_gas_check = QCheckBox("真实气体 PVT")
        self.lgr_check.setChecked(bool(config.get("enable_lgr", True)))
        self.natural_fracture_check.setChecked(
            bool(config.get("enable_natural_fractures", True)))
        self.hydraulic_fracture_check.setChecked(
            bool(config.get("enable_hydraulic_fractures", False)))
        self.real_gas_check.setChecked(bool(config.get("enable_real_gas_pvt", True)))
        layout.addWidget(self.lgr_check)
        layout.addWidget(self.natural_fracture_check)
        layout.addWidget(self.hydraulic_fracture_check)
        layout.addWidget(self.real_gas_check)
        return group

    def _wr_group(self, config):
        self.wr_group = QGroupBox("WR 数据来源")
        layout = QVBoxLayout(self.wr_group)
        self.wr_file_radio = QRadioButton(
            "属性文件模式：fracture_phi/kx/ky/kz + sigma")
        self.wr_constant_radio = QRadioButton(
            "常数参数模式：phi_f/k_f/wr_shape_factor")
        self.wr_mixed_radio = QRadioButton("混合模式：文件优先，常数兜底")
        mode = config.get("wr_input_mode", WR_INPUT_MODE_FILE)
        self.wr_file_radio.setChecked(mode == WR_INPUT_MODE_FILE)
        self.wr_constant_radio.setChecked(mode == WR_INPUT_MODE_CONSTANT)
        self.wr_mixed_radio.setChecked(mode == WR_INPUT_MODE_MIXED)
        layout.addWidget(self.wr_file_radio)
        layout.addWidget(self.wr_constant_radio)
        layout.addWidget(self.wr_mixed_radio)
        note = QLabel("选择正常模型时，WR 数据来源不会参与当前运行方案。")
        note.setWordWrap(True)
        layout.addWidget(note)
        return self.wr_group

    def _sync_wr_enabled(self):
        enabled = self.wr_radio.isChecked()
        self.wr_group.setEnabled(enabled)

    def selected_config(self):
        if self.wr_file_radio.isChecked():
            wr_mode = WR_INPUT_MODE_FILE
        elif self.wr_constant_radio.isChecked():
            wr_mode = WR_INPUT_MODE_CONSTANT
        else:
            wr_mode = WR_INPUT_MODE_MIXED
        return normalize_model_config({
            "model_type": MODEL_TYPE_WR if self.wr_radio.isChecked() else MODEL_TYPE_NORMAL,
            "grid_type": "corner_point",
            "enable_lgr": self.lgr_check.isChecked(),
            "enable_natural_fractures": self.natural_fracture_check.isChecked(),
            "enable_hydraulic_fractures": self.hydraulic_fracture_check.isChecked(),
            "enable_real_gas_pvt": self.real_gas_check.isChecked(),
            "wr_input_mode": wr_mode,
            "confirmed": True,
        })


def ensure_model_config_confirmed(project_state, parent=None, force=False):
    config = normalize_model_config(
        getattr(project_state, "model_config", None),
        getattr(project_state, "corner_grid_refinement", None),
    )
    if config.get("confirmed") and not force:
        return True
    dialog = ModelConfigDialog(project_state, parent)
    if dialog.exec_() != QDialog.Accepted:
        return False
    old_config = normalize_model_config(
        getattr(project_state, "model_config", None),
        getattr(project_state, "corner_grid_refinement", None),
    )
    new_config = dialog.selected_config()
    project_state.set_model_config(new_config)
    if old_config != new_config and hasattr(project_state, "mark_case_dataset_stale"):
        project_state.mark_case_dataset_stale("模型方案已修改，请重新生成 Dataset")
    return True


def model_config_summary(config):
    config = normalize_model_config(config)
    model_name = "WR 双重介质模型" if config.get("model_type") == MODEL_TYPE_WR else "正常模型"
    lgr = "LGR 加密" if config.get("enable_lgr") else "不加密"
    wr_mode = {
        WR_INPUT_MODE_FILE: "属性文件",
        WR_INPUT_MODE_CONSTANT: "常数参数",
        WR_INPUT_MODE_MIXED: "混合",
    }.get(config.get("wr_input_mode"), "属性文件")
    return f"{model_name}，{lgr}，WR 数据来源={wr_mode}"
