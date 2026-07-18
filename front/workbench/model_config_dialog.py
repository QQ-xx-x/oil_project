# -*- coding: utf-8 -*-
"""用于选择项目级模拟模型配置的对话框。"""

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
    WR_INPUT_MODE_FILE,
    normalize_model_config,
)


class ModelConfigDialog(QDialog):
    """编辑持久化、面向业务的模型配置。"""

    def __init__(self, project_state, parent=None):
        super().__init__(parent)
        self.project_state = project_state
        self.setObjectName("modelConfigDialog")
        self.setWindowTitle("模型配置")
        self.resize(540, 470)

        current = normalize_model_config(
            getattr(project_state, "model_config", None),
            getattr(project_state, "corner_grid_refinement", None),
        )
        self._current_config = current

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        title = QLabel("模型配置")
        title.setObjectName("parameterTitle")
        root.addWidget(title)

        import_row = QHBoxLayout()
        self.import_button = QPushButton("导入")
        self.import_button.setObjectName("importModelConfigButton")
        self.import_status = QLabel("")
        self.import_status.setObjectName("parameterDescription")
        import_row.addWidget(self.import_button)
        import_row.addWidget(self.import_status, 1)
        root.addLayout(import_row)

        root.addWidget(self._model_group(current))
        root.addWidget(self._feature_group(current))
        root.addWidget(self._lgr_group(current))
        root.addStretch()

        buttons = QDialogButtonBox()
        ok_button = QPushButton("确定")
        cancel_button = QPushButton("取消")
        buttons.addButton(ok_button, QDialogButtonBox.AcceptRole)
        buttons.addButton(cancel_button, QDialogButtonBox.RejectRole)
        ok_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        root.addWidget(buttons)

        self._sync_lgr_enabled()
        self.unrefined_radio.toggled.connect(self._sync_lgr_enabled)
        self.lgr_radio.toggled.connect(self._sync_lgr_enabled)
        self.import_button.clicked.connect(self._import_lgr_values)

    def _model_group(self, config):
        group = QGroupBox("模型类型")
        layout = QVBoxLayout(group)
        self.unrefined_radio = QRadioButton("未加密模型")
        self.lgr_radio = QRadioButton("LGR 加密模型")
        self.unrefined_radio.setChecked(not bool(config.get("enable_lgr", True)))
        self.lgr_radio.setChecked(bool(config.get("enable_lgr", True)))
        layout.addWidget(self.unrefined_radio)
        layout.addWidget(self.lgr_radio)
        return group

    def _feature_group(self, config):
        group = QGroupBox("功能模块")
        layout = QVBoxLayout(group)
        self.wr_check = QCheckBox("WR 双重介质")
        self.wr_check.setChecked(config.get("model_type") == MODEL_TYPE_WR)
        layout.addWidget(self.wr_check)
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

    def _sync_lgr_enabled(self):
        self.lgr_group.setVisible(self.lgr_radio.isChecked())
        if self.isVisible():
            self.resize(self.width(), self.sizeHint().height())

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
        """将已校验的业务值原子地复制到编辑器。"""

        if "enable_lgr" in values:
            self.lgr_radio.setChecked(bool(values["enable_lgr"]))
            self.unrefined_radio.setChecked(not bool(values["enable_lgr"]))
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
        return normalize_model_config({
            "model_type": (
                MODEL_TYPE_WR
                if self.wr_check.isChecked()
                else MODEL_TYPE_NORMAL
            ),
            "grid_type": "corner_point",
            "enable_lgr": self.lgr_radio.isChecked(),
            "lgr_d_threshold": self.lgr_d_threshold.value(),
            "lgr_nrx": self.lgr_nrx.value(),
            "lgr_nry": self.lgr_nry.value(),
            "lgr_nrz": self.lgr_nrz.value(),
            # 这些开关会保留在存储结构中以兼容现有项目，
            # 但不再作为面向用户的模型配置选项。
            "enable_natural_fractures": self._current_config.get(
                "enable_natural_fractures", True),
            "enable_hydraulic_fractures": self._current_config.get(
                "enable_hydraulic_fractures", False),
            "enable_real_gas_pvt": True,
            "wr_input_mode": WR_INPUT_MODE_FILE,
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
    if config.get("enable_lgr"):
        model_name = (
            f"LGR 加密模型：距离阈值 {config.get('lgr_d_threshold')}，"
            f"加密数 {config.get('lgr_nrx')}/"
            f"{config.get('lgr_nry')}/{config.get('lgr_nrz')}"
        )
    else:
        model_name = "未加密模型"
    wr = (
        "WR 双重介质已启用"
        if config.get("model_type") == MODEL_TYPE_WR
        else "未启用 WR"
    )
    return f"{model_name}，{wr}"
