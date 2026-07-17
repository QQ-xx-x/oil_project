# -*- coding: utf-8 -*-
"""Dialog for selecting the project-level simulation model configuration."""

from PyQt5.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFileDialog,
    QFormLayout, QGroupBox, QHBoxLayout, QLabel, QMessageBox, QPushButton,
    QRadioButton, QSpinBox, QVBoxLayout,
)

from .model_config_import import (
    ModelConfigImportError,
    load_lgr_model_config_values,
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
    """Edit the persistent, business-facing model configuration."""

    def __init__(self, project_state, parent=None):
        super().__init__(parent)
        self.project_state = project_state
        self.setObjectName("modelConfigDialog")
        self.setWindowTitle("模型配置")
        self.resize(540, 650)

        current = normalize_model_config(
            getattr(project_state, "model_config", None),
            getattr(project_state, "corner_grid_refinement", None),
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        title = QLabel("模型配置")
        title.setObjectName("parameterTitle")
        root.addWidget(title)

        hint = QLabel(
            "配置模型类型、局部加密和可选功能。相关业务分组会根据这里的开关调整状态。"
        )
        hint.setObjectName("parameterDescription")
        hint.setWordWrap(True)
        root.addWidget(hint)

        import_row = QHBoxLayout()
        self.import_button = QPushButton("导入模块数据")
        self.import_button.setObjectName("importModelConfigButton")
        self.import_status = QLabel("")
        self.import_status.setObjectName("parameterDescription")
        import_row.addWidget(self.import_button)
        import_row.addWidget(self.import_status, 1)
        root.addLayout(import_row)

        root.addWidget(self._model_group(current))
        root.addWidget(self._feature_group(current))
        root.addWidget(self._lgr_group(current))
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
        self._sync_lgr_enabled()
        self.normal_radio.toggled.connect(self._sync_wr_enabled)
        self.wr_radio.toggled.connect(self._sync_wr_enabled)
        self.lgr_check.toggled.connect(self._sync_lgr_enabled)
        self.import_button.clicked.connect(self._import_lgr_values)

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

    def _lgr_group(self, config):
        self.lgr_group = QGroupBox("LGR 参数")
        layout = QFormLayout(self.lgr_group)

        self.lgr_d_threshold = QDoubleSpinBox()
        self.lgr_d_threshold.setRange(0.0, 1.0e12)
        self.lgr_d_threshold.setDecimals(6)
        self.lgr_d_threshold.setValue(
            float(config.get("lgr_d_threshold", 5.05)))

        self.lgr_nrx = self._refinement_spin_box(
            config.get("lgr_nrx", 2))
        self.lgr_nry = self._refinement_spin_box(
            config.get("lgr_nry", 2))
        self.lgr_nrz = self._refinement_spin_box(
            config.get("lgr_nrz", 2))

        layout.addRow("距离阈值", self.lgr_d_threshold)
        layout.addRow("X 向加密数", self.lgr_nrx)
        layout.addRow("Y 向加密数", self.lgr_nry)
        layout.addRow("Z 向加密数", self.lgr_nrz)
        return self.lgr_group

    @staticmethod
    def _refinement_spin_box(value):
        editor = QSpinBox()
        editor.setRange(1, 1000000)
        editor.setValue(int(value or 2))
        return editor

    def _wr_group(self, config):
        self.wr_group = QGroupBox("WR 数据来源")
        layout = QVBoxLayout(self.wr_group)
        self.wr_file_radio = QRadioButton("空间属性数据模式")
        self.wr_constant_radio = QRadioButton("常数参数模式")
        self.wr_mixed_radio = QRadioButton(
            "混合模式（空间属性优先，常数补充）")
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

    def _sync_lgr_enabled(self):
        self.lgr_group.setEnabled(self.lgr_check.isChecked())

    def _import_lgr_values(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "导入模型配置数据",
            "",
            "CaseData (*.txt *.data);;所有文件 (*)",
        )
        if not path:
            return
        try:
            values = load_lgr_model_config_values(path)
        except ModelConfigImportError as exc:
            QMessageBox.warning(self, "导入失败", str(exc))
            return
        self._apply_imported_lgr_values(values)
        self.import_status.setText(
            f"已导入 {len(values)} 项 LGR 参数")

    def _apply_imported_lgr_values(self, values):
        """Atomically copy already validated business values into editors."""

        if "enable_lgr" in values:
            self.lgr_check.setChecked(bool(values["enable_lgr"]))
        if "lgr_d_threshold" in values:
            self.lgr_d_threshold.setValue(
                float(values["lgr_d_threshold"]))
        for key, editor in (
                ("lgr_nrx", self.lgr_nrx),
                ("lgr_nry", self.lgr_nry),
                ("lgr_nrz", self.lgr_nrz)):
            if key in values:
                editor.setValue(int(values[key]))

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
            "lgr_d_threshold": self.lgr_d_threshold.value(),
            "lgr_nrx": self.lgr_nrx.value(),
            "lgr_nry": self.lgr_nry.value(),
            "lgr_nrz": self.lgr_nrz.value(),
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
    new_config = dialog.selected_config()
    project_state.set_model_config(new_config)
    return True


def model_config_summary(config):
    config = normalize_model_config(config)
    model_name = "WR 双重介质模型" if config.get("model_type") == MODEL_TYPE_WR else "正常模型"
    if config.get("enable_lgr"):
        lgr = (
            f"LGR：距离阈值 {config.get('lgr_d_threshold')}，"
            f"加密数 {config.get('lgr_nrx')}/"
            f"{config.get('lgr_nry')}/{config.get('lgr_nrz')}"
        )
    else:
        lgr = "不启用 LGR"
    wr_mode = {
        WR_INPUT_MODE_FILE: "空间属性",
        WR_INPUT_MODE_CONSTANT: "常数参数",
        WR_INPUT_MODE_MIXED: "混合",
    }.get(config.get("wr_input_mode"), "空间属性")
    return f"{model_name}，{lgr}，WR 数据来源={wr_mode}"
