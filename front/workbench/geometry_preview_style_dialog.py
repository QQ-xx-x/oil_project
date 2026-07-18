# -*- coding: utf-8 -*-
"""当前三维视口的几何预览样式控件。"""

import math

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QColor, qGray
from PyQt5.QtWidgets import (
    QCheckBox,
    QColorDialog,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QVBoxLayout,
)


# 运行时调用方提供渲染器的规范样式。这些值是
# 防御性回退，使独立对话框在测试输入不完整或
# 恢复旧版界面状态时仍可使用。
GEOMETRY_PREVIEW_STYLE_FALLBACK = {
    "well_color": (0.08, 0.24, 0.62),
    "well_radius": 2.0,
    "perforation_color": (1.0, 0.82, 0.0),
    "show_perforations": True,
    "natural_fracture_color": (0.0, 0.25, 0.4),
    "hydraulic_fracture_color": (0.72, 0.38, 0.38),
    "fracture_show_edges": False,
    "natural_fracture_edge_color": (0.0, 0.15, 0.25),
    "hydraulic_fracture_edge_color": (0.54, 0.29, 0.29),
    "fracture_edge_line_width": 0.0,
}

COLOR_STYLE_KEYS = (
    "well_color",
    "perforation_color",
    "natural_fracture_color",
    "hydraulic_fracture_color",
    "natural_fracture_edge_color",
    "hydraulic_fracture_edge_color",
)


def _color_tuple(value, fallback):
    color = None
    if isinstance(value, QColor):
        color = QColor(value)
    elif isinstance(value, str):
        candidate = QColor(value.strip())
        if candidate.isValid():
            color = candidate
    elif isinstance(value, (tuple, list)) and len(value) >= 3:
        try:
            components = [float(value[index]) for index in range(3)]
            if not all(math.isfinite(component) for component in components):
                raise ValueError("color components must be finite")
            if max(components) > 1.0:
                components = [component / 255.0 for component in components]
            components = [max(0.0, min(1.0, component)) for component in components]
            return tuple(components)
        except (TypeError, ValueError):
            color = None

    if color is not None and color.isValid():
        return tuple(float(component) for component in color.getRgbF()[:3])
    return tuple(float(component) for component in fallback[:3])


def normalize_geometry_preview_style(style):
    """返回供对话框使用的完整、可安全序列化为 JSON 的样式字典。"""
    source = style if isinstance(style, dict) else {}
    normalized = dict(GEOMETRY_PREVIEW_STYLE_FALLBACK)

    for key in COLOR_STYLE_KEYS:
        normalized[key] = _color_tuple(
            source.get(key, normalized[key]),
            normalized[key],
        )

    normalized["show_perforations"] = bool(
        source.get("show_perforations", normalized["show_perforations"])
    )
    normalized["fracture_show_edges"] = bool(
        source.get("fracture_show_edges", normalized["fracture_show_edges"])
    )

    try:
        well_radius = float(source.get("well_radius", normalized["well_radius"]))
    except (TypeError, ValueError):
        well_radius = normalized["well_radius"]
    if not math.isfinite(well_radius) or well_radius <= 0.0:
        well_radius = normalized["well_radius"]
    normalized["well_radius"] = well_radius

    try:
        edge_width = float(source.get(
            "fracture_edge_line_width",
            normalized["fracture_edge_line_width"],
        ))
    except (TypeError, ValueError):
        edge_width = normalized["fracture_edge_line_width"]
    if not math.isfinite(edge_width):
        edge_width = normalized["fracture_edge_line_width"]
    normalized["fracture_edge_line_width"] = max(0.0, edge_width)
    return normalized


class _ColorButton(QPushButton):
    color_changed = pyqtSignal(object)

    def __init__(self, color, title, parent=None):
        super().__init__(parent)
        self._dialog_title = title
        self._color = QColor("#000000")
        self.setObjectName("geometryPreviewColorButton")
        self.setFixedWidth(112)
        self.clicked.connect(self._choose_color)
        self.set_color(color)

    def color(self):
        return QColor(self._color)

    def set_color(self, value):
        rgb = _color_tuple(value, (0.0, 0.0, 0.0))
        self._color = QColor.fromRgbF(*rgb)
        foreground = "#ffffff" if qGray(self._color.rgb()) < 145 else "#20242a"
        self.setText(self._color.name().upper())
        self.setToolTip(f"点击选择颜色：{self._color.name().upper()}")
        self.setStyleSheet(
            "QPushButton {"
            f"background-color: {self._color.name()};"
            f"color: {foreground};"
            "border: 1px solid #7f8792;"
            "border-radius: 2px;"
            "padding: 3px 8px;"
            "}"
        )

    def rgb_tuple(self):
        return tuple(float(component) for component in self._color.getRgbF()[:3])

    def _choose_color(self):
        color = QColorDialog.getColor(
            self._color,
            self,
            self._dialog_title,
        )
        if not color.isValid():
            return
        self.set_color(color)
        self.color_changed.emit(self.color())


class GeometryPreviewStyleDialog(QDialog):
    """编辑渲染器支持的几何样式，并提供实时预览和回滚。"""

    style_changed = pyqtSignal(dict)
    style_applied = pyqtSignal(dict)
    style_reverted = pyqtSignal(dict)
    apply_failed = pyqtSignal(str)
    message_emitted = pyqtSignal(str)

    def __init__(self, initial_style=None, apply_callback=None, parent=None):
        super().__init__(parent)
        self._apply_callback = apply_callback
        self._updating_controls = False
        self._baseline_style = normalize_geometry_preview_style(initial_style)
        self._last_valid_style = dict(self._baseline_style)

        self.setObjectName("geometryPreviewStyleDialog")
        self.setWindowTitle("几何预览样式")
        self.setMinimumWidth(480)
        self.resize(500, 470)

        self._build_ui()
        self._load_style(self._baseline_style)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        hint = QLabel(
            "样式修改会立即应用到当前 3D 窗口中已显示的井或裂缝。"
            "数值输入在编辑完成后更新。"
        )
        hint.setWordWrap(True)
        hint.setObjectName("geometryPreviewStyleHint")
        root.addWidget(hint)

        root.addWidget(self._build_well_group())
        root.addWidget(self._build_perforation_group())
        root.addWidget(self._build_fracture_group())
        root.addStretch(1)

        self.button_box = QDialogButtonBox()
        self.apply_button = QPushButton("应用")
        self.ok_button = QPushButton("确定")
        self.cancel_button = QPushButton("取消")
        self.button_box.addButton(
            self.apply_button,
            QDialogButtonBox.ApplyRole,
        )
        self.button_box.addButton(
            self.ok_button,
            QDialogButtonBox.AcceptRole,
        )
        self.button_box.addButton(
            self.cancel_button,
            QDialogButtonBox.RejectRole,
        )
        self.apply_button.clicked.connect(self._apply_clicked)
        self.ok_button.clicked.connect(self._accept_clicked)
        self.cancel_button.clicked.connect(self.reject)
        root.addWidget(self.button_box)

    def _build_well_group(self):
        group = QGroupBox("井筒")
        layout = QFormLayout(group)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        self.well_color_button = _ColorButton(
            (0.0, 0.0, 0.0),
            "选择井筒颜色",
        )
        self.well_radius_spin = QDoubleSpinBox()
        self.well_radius_spin.setObjectName("geometryPreviewWellRadiusSpin")
        self.well_radius_spin.setRange(0.001, 1000000.0)
        self.well_radius_spin.setDecimals(3)
        self.well_radius_spin.setSingleStep(0.5)
        self.well_radius_spin.setSuffix(" 模型单位")
        self.well_radius_spin.setMaximumWidth(180)

        layout.addRow("井筒颜色:", self.well_color_button)
        layout.addRow("井筒半径:", self.well_radius_spin)

        self.well_color_button.color_changed.connect(self._on_live_change)
        self.well_radius_spin.editingFinished.connect(self._on_live_change)
        return group

    def _build_perforation_group(self):
        group = QGroupBox("射孔段")
        layout = QFormLayout(group)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        self.show_perforations_check = QCheckBox("显示射孔段")
        self.show_perforations_check.setObjectName(
            "geometryPreviewShowPerforationsCheck")
        self.perforation_color_button = _ColorButton(
            (0.0, 0.0, 0.0),
            "选择射孔段颜色",
        )

        layout.addRow("显示状态:", self.show_perforations_check)
        layout.addRow("射孔段颜色:", self.perforation_color_button)

        self.show_perforations_check.toggled.connect(
            self._on_perforations_toggled)
        self.perforation_color_button.color_changed.connect(
            self._on_live_change)
        return group

    def _build_fracture_group(self):
        group = QGroupBox("裂缝")
        layout = QFormLayout(group)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        self.natural_fracture_color_button = _ColorButton(
            (0.0, 0.0, 0.0),
            "选择天然裂缝面颜色",
        )
        self.hydraulic_fracture_color_button = _ColorButton(
            (0.0, 0.0, 0.0),
            "选择人工裂缝面颜色",
        )
        self.fracture_show_edges_check = QCheckBox("显示裂缝边界")
        self.fracture_show_edges_check.setObjectName(
            "geometryPreviewShowFractureEdgesCheck")
        self.natural_fracture_edge_color_button = _ColorButton(
            (0.0, 0.0, 0.0),
            "选择天然裂缝边界颜色",
        )
        self.hydraulic_fracture_edge_color_button = _ColorButton(
            (0.0, 0.0, 0.0),
            "选择人工裂缝边界颜色",
        )
        self.fracture_edge_width_spin = QDoubleSpinBox()
        self.fracture_edge_width_spin.setObjectName(
            "geometryPreviewFractureEdgeWidthSpin")
        self.fracture_edge_width_spin.setRange(0.0, 20.0)
        self.fracture_edge_width_spin.setDecimals(1)
        self.fracture_edge_width_spin.setSingleStep(0.1)
        self.fracture_edge_width_spin.setSuffix(" px")
        self.fracture_edge_width_spin.setMaximumWidth(120)

        layout.addRow(
            "天然裂缝面颜色:",
            self.natural_fracture_color_button,
        )
        layout.addRow(
            "人工裂缝面颜色:",
            self.hydraulic_fracture_color_button,
        )
        layout.addRow("边界显示:", self.fracture_show_edges_check)
        layout.addRow(
            "天然裂缝边界颜色:",
            self.natural_fracture_edge_color_button,
        )
        layout.addRow(
            "人工裂缝边界颜色:",
            self.hydraulic_fracture_edge_color_button,
        )
        layout.addRow("边界宽度:", self.fracture_edge_width_spin)

        self.natural_fracture_color_button.color_changed.connect(
            self._on_live_change)
        self.hydraulic_fracture_color_button.color_changed.connect(
            self._on_live_change)
        self.fracture_show_edges_check.toggled.connect(
            self._on_fracture_edges_toggled)
        self.natural_fracture_edge_color_button.color_changed.connect(
            self._on_live_change)
        self.hydraulic_fracture_edge_color_button.color_changed.connect(
            self._on_live_change)
        self.fracture_edge_width_spin.editingFinished.connect(
            self._on_live_change)
        return group

    def current_style(self):
        return {
            "well_color": self.well_color_button.rgb_tuple(),
            "well_radius": float(self.well_radius_spin.value()),
            "perforation_color": self.perforation_color_button.rgb_tuple(),
            "show_perforations": self.show_perforations_check.isChecked(),
            "natural_fracture_color": (
                self.natural_fracture_color_button.rgb_tuple()
            ),
            "hydraulic_fracture_color": (
                self.hydraulic_fracture_color_button.rgb_tuple()
            ),
            "fracture_show_edges": self.fracture_show_edges_check.isChecked(),
            "natural_fracture_edge_color": (
                self.natural_fracture_edge_color_button.rgb_tuple()
            ),
            "hydraulic_fracture_edge_color": (
                self.hydraulic_fracture_edge_color_button.rgb_tuple()
            ),
            "fracture_edge_line_width": float(
                self.fracture_edge_width_spin.value()
            ),
        }

    def set_style(self, style, commit_baseline=False):
        normalized = normalize_geometry_preview_style(style)
        self._last_valid_style = dict(normalized)
        if commit_baseline:
            self._baseline_style = dict(normalized)
        self._load_style(normalized)

    def _load_style(self, style):
        normalized = normalize_geometry_preview_style(style)
        self._updating_controls = True
        try:
            self.well_color_button.set_color(normalized["well_color"])
            self.well_radius_spin.setValue(normalized["well_radius"])
            self.perforation_color_button.set_color(
                normalized["perforation_color"])
            self.show_perforations_check.setChecked(
                normalized["show_perforations"])
            self.natural_fracture_color_button.set_color(
                normalized["natural_fracture_color"])
            self.hydraulic_fracture_color_button.set_color(
                normalized["hydraulic_fracture_color"])
            self.fracture_show_edges_check.setChecked(
                normalized["fracture_show_edges"])
            self.natural_fracture_edge_color_button.set_color(
                normalized["natural_fracture_edge_color"])
            self.hydraulic_fracture_edge_color_button.set_color(
                normalized["hydraulic_fracture_edge_color"])
            self.fracture_edge_width_spin.setValue(
                normalized["fracture_edge_line_width"])
            self._sync_dependent_controls()
        finally:
            self._updating_controls = False

    def _sync_dependent_controls(self):
        self.perforation_color_button.setEnabled(
            self.show_perforations_check.isChecked())
        edges_enabled = self.fracture_show_edges_check.isChecked()
        self.natural_fracture_edge_color_button.setEnabled(edges_enabled)
        self.hydraulic_fracture_edge_color_button.setEnabled(edges_enabled)
        self.fracture_edge_width_spin.setEnabled(edges_enabled)

    def _on_perforations_toggled(self, _checked):
        self._sync_dependent_controls()
        self._on_live_change()

    def _on_fracture_edges_toggled(self, checked):
        if self._updating_controls:
            return
        if checked and self.fracture_edge_width_spin.value() <= 0.0:
            self._updating_controls = True
            try:
                self.fracture_edge_width_spin.setValue(1.0)
            finally:
                self._updating_controls = False
        self._sync_dependent_controls()
        self._on_live_change()

    def _on_live_change(self, *_args):
        if self._updating_controls:
            return
        self._submit_style(self.current_style())

    def _invoke_apply_callback(self, style):
        if self._apply_callback is None:
            return True, "", dict(style)
        try:
            result = self._apply_callback(dict(style))
        except Exception as exc:
            return False, f"[预览样式] 应用失败：{exc}", {}

        if isinstance(result, dict):
            return True, "", result
        if isinstance(result, tuple) and len(result) >= 3:
            ok = bool(result[0])
            normalized = result[2]
            if ok and not isinstance(normalized, dict):
                return False, "[预览样式] 应用接口返回了无效样式", {}
            return ok, str(result[1] or ""), normalized
        if isinstance(result, tuple) and len(result) == 2:
            return bool(result[0]), str(result[1] or ""), dict(style)
        return False, "[预览样式] 应用接口返回了无效结果", {}

    def _submit_style(self, style):
        candidate = normalize_geometry_preview_style(style)
        ok, message, normalized = self._invoke_apply_callback(candidate)
        if not ok:
            self._load_style(self._last_valid_style)
            self.apply_failed.emit(message)
            return False

        canonical = normalize_geometry_preview_style(normalized)
        self._last_valid_style = dict(canonical)
        if canonical != candidate:
            self._load_style(canonical)
        self.style_changed.emit(dict(canonical))
        if message:
            self.message_emitted.emit(message)
        return True

    def _apply_clicked(self):
        if not self._submit_style(self.current_style()):
            return
        self._baseline_style = dict(self._last_valid_style)
        self.style_applied.emit(dict(self._baseline_style))

    def _accept_clicked(self):
        if not self._submit_style(self.current_style()):
            return
        self._baseline_style = dict(self._last_valid_style)
        self.style_applied.emit(dict(self._baseline_style))
        super().accept()

    def reject(self):
        baseline = dict(self._baseline_style)
        if baseline != self._last_valid_style:
            ok, message, normalized = self._invoke_apply_callback(baseline)
            if not ok:
                self.apply_failed.emit(message)
                return
            baseline = normalize_geometry_preview_style(normalized)
            self._last_valid_style = dict(baseline)
            self._load_style(baseline)
            self.style_changed.emit(dict(baseline))
            if message:
                self.message_emitted.emit(message)
        self.style_reverted.emit(dict(baseline))
        super().reject()
