# -*- coding: utf-8 -*-
"""视图窗口使用的紧凑工具栏。"""

from PyQt5.QtCore import QSize, Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit, QSpinBox, QToolButton,
    QVBoxLayout,
)

from .icon_registry import semantic_icon_kind
from .icons import painted_icon


class ViewToolbar(QFrame):
    new_window_requested = pyqtSignal()
    clone_window_requested = pyqtSignal()
    close_window_requested = pyqtSignal()
    tool_requested = pyqtSignal(str)
    property_selected = pyqtSignal(str)
    slice_requested = pyqtSignal(str, str, int)
    slice_reset_requested = pyqtSignal()
    threshold_requested = pyqtSignal(str, str)
    threshold_clear_requested = pyqtSignal()
    time_playback_requested = pyqtSignal(str, int)
    geometry_preview_requested = pyqtSignal(str)
    geometry_style_requested = pyqtSignal()
    static_preview_requested = pyqtSignal(str)
    static_layer_preview_requested = pyqtSignal(str, str, int)
    fence_action_requested = pyqtSignal(str)
    fence_property_selected = pyqtSignal(str)

    STATIC_PREVIEW_PROPERTIES = [
        ("MATRIX_PORO", "MATRIX_PORO"),
        ("MATRIX_PERMX", "MATRIX_PERMX"),
        ("MATRIX_PERMY", "MATRIX_PERMY"),
        ("MATRIX_PERMZ", "MATRIX_PERMZ"),
        ("DFN_PORO", "DFN_PORO"),
        ("DFN_PERMX", "DFN_PERMX"),
        ("DFN_PERMY", "DFN_PERMY"),
        ("DFN_PERMZ", "DFN_PERMZ"),
        ("SIGMA", "SIGMA"),
    ]

    TOOLSETS = {
        "3d": [
            ("适配全部", "fit_view", "fit_view"),
            ("坐标轴", "grid", "coordinate_axes_toggle"),
            ("拾取单元", "select", "pick_toggle"),
            ("测距", "measure", "measure_toggle"),
            ("2D Magnify", "search", "magnify_toggle"),
            ("前视图", "fit_view", "view_front"),
            ("后视图", "fit_view", "view_back"),
            ("左视图", "fit_view", "view_left"),
            ("右视图", "fit_view", "view_right"),
            ("俯视图", "fit_view", "view_top"),
            ("仰视图", "fit_view", "view_bottom"),
            ("锁定视角方向", "restrict", "camera_lock_toggle"),
            ("截图", "camera", "export_graphic"),
        ],
        "2d": [
            ("选择对象", "select"), ("平移视图", "pan"), ("缩放视图", "search"),
            ("适配全部", "fit_view"), ("比例尺", "measure"), ("显示网格", "grid"),
            ("测量", "measure"), ("截图", "camera"),
        ],
        "chart": [
            ("刷新图表", "refresh"), ("框选缩放", "search"), ("重置视图", "undo"),
            ("保存图像", "save"), ("显示图例", "chart"), ("曲线设置", "settings"),
            ("导出数据", "export"),
        ],
    }

    def __init__(self, view_type="3d", parent=None):
        super().__init__(parent)
        self.setObjectName("viewToolbar")
        self.setProperty("viewType", view_type)
        if view_type == "3d":
            root_layout = QVBoxLayout(self)
            root_layout.setContentsMargins(4, 2, 5, 2)
            root_layout.setSpacing(1)
            layout = QHBoxLayout()
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(2)
            controls_layout = QHBoxLayout()
            controls_layout.setContentsMargins(0, 0, 0, 0)
            controls_layout.setSpacing(2)
            preview_layout = QHBoxLayout()
            preview_layout.setContentsMargins(0, 0, 0, 0)
            preview_layout.setSpacing(2)
            fence_layout = QHBoxLayout()
            fence_layout.setContentsMargins(0, 0, 0, 0)
            fence_layout.setSpacing(2)
            root_layout.addLayout(layout)
            root_layout.addLayout(controls_layout)
            root_layout.addLayout(preview_layout)
            root_layout.addLayout(fence_layout)
        else:
            layout = QHBoxLayout(self)
            layout.setContentsMargins(4, 2, 5, 2)
            layout.setSpacing(2)
            controls_layout = layout
            preview_layout = layout

        for tooltip, kind, signal in [
            ("新建窗口", "new", self.new_window_requested),
            ("复制当前窗口", "copy", self.clone_window_requested),
            ("关闭当前窗口", "warning", self.close_window_requested),
        ]:
            button = self._button(tooltip, kind)
            button.setProperty("windowTool", True)
            button.clicked.connect(signal.emit)
            layout.addWidget(button)

        divider = QFrame()
        divider.setObjectName("viewToolbarDivider")
        divider.setFrameShape(QFrame.VLine)
        layout.addWidget(divider)

        for item in self.TOOLSETS.get(view_type, self.TOOLSETS["3d"]):
            if len(item) == 3:
                tooltip, kind, command = item
            else:
                tooltip, kind = item
                command = ""
            button = self._button(tooltip, kind)
            if command:
                button.clicked.connect(
                    lambda checked=False, cmd=command: self.tool_requested.emit(cmd))
            layout.addWidget(button)

        selector = QComboBox()
        if view_type == "chart":
            selector.addItems(["曲线类型", "相渗", "生产", "PVT"])
        elif view_type == "2d":
            selector.addItems(["图层", "井位", "网格", "裂缝"])
        else:
            for text, key in [
                ("Pressure", "pressure_field"),
                ("Sw", "water_saturation_field"),
                ("Phi", "porosity_field"),
                ("Kx", "permeability_x_field"),
                ("Ky", "permeability_y_field"),
                ("Kz", "permeability_z_field"),
            ]:
                selector.addItem(text, key)
            selector.currentIndexChanged.connect(self._emit_property_selected)
        selector.setObjectName("viewSelector")
        self.view_selector = selector
        layout.addWidget(selector)

        if view_type != "chart":
            layout.addWidget(QLabel("比例"))
            scale = QComboBox()
            scale.addItems(["1", "0.5", "0.2"])
            scale.setCurrentText("1")
            scale.setObjectName("scaleSelector")
            self.scale_selector = scale
            layout.addWidget(scale)
        if view_type == "3d":
            self._add_slice_controls(controls_layout)
            self._add_threshold_controls(controls_layout)
            self._add_time_controls(controls_layout)
            controls_layout.addStretch()
            self._add_preview_controls(preview_layout)
            preview_layout.addStretch()
            self._add_fence_controls(fence_layout)
            fence_layout.addStretch()
        layout.addStretch()

    def _add_fence_controls(self, layout):
        layout.addWidget(QLabel("折线剖面"))

        self.fence_draw_button = self._button("绘制折线垂向剖面", "select")
        self.fence_draw_button.setObjectName("fenceSectionDrawButton")
        self.fence_draw_button.setText("绘制")
        self.fence_draw_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.fence_draw_button.setFixedSize(64, 23)
        self.fence_draw_button.setCheckable(True)
        self.fence_draw_button.clicked.connect(
            lambda checked=False: self.fence_action_requested.emit("start"))
        layout.addWidget(self.fence_draw_button)

        layout.addWidget(QLabel("属性"))
        self.fence_property = QComboBox()
        self.fence_property.setObjectName("fenceSectionPropertySelector")
        self.fence_property.addItems(["Pressure", "Kx", "Ky", "Kz", "Phi", "Sw"])
        self.fence_property.setFixedWidth(92)
        self.fence_property.currentTextChanged.connect(
            self.fence_property_selected.emit)
        layout.addWidget(self.fence_property)

        for text, tooltip, kind, action, object_name, width in [
            ("完成", "完成折线剖面绘制", "refresh", "complete", "fenceSectionCompleteButton", 64),
            ("取消绘制", "取消当前路径绘制", "undo", "cancel", "fenceSectionCancelButton", 82),
            ("清除剖面", "清除已经生成的剖面", "clear", "clear", "fenceSectionClearButton", 82),
            ("退出", "退出折线剖面功能", "close", "exit", "fenceSectionExitButton", 64),
        ]:
            button = self._button(tooltip, kind)
            button.setObjectName(object_name)
            button.setText(text)
            button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
            button.setFixedSize(width, 23)
            button.clicked.connect(
                lambda checked=False, name=action:
                    self.fence_action_requested.emit(name))
            layout.addWidget(button)
            setattr(self, f"fence_{action}_button", button)

        self.set_fence_controls_state({
            "state": "inactive",
            "property_name": "Pressure",
            "can_start": False,
            "can_complete": False,
            "can_cancel": False,
            "can_clear": False,
            "can_exit": False,
            "can_change_property": True,
        })

    def set_fence_controls_state(self, state):
        if not hasattr(self, "fence_draw_button"):
            return False

        state = state if isinstance(state, dict) else {}
        state_name = str(state.get("state") or "inactive")

        previous = self.fence_draw_button.blockSignals(True)
        try:
            self.fence_draw_button.setChecked(state_name == "drawing")
        finally:
            self.fence_draw_button.blockSignals(previous)

        self.fence_draw_button.setEnabled(bool(state.get("can_start", False)))
        self.fence_complete_button.setEnabled(bool(state.get("can_complete", False)))
        self.fence_cancel_button.setEnabled(bool(state.get("can_cancel", False)))
        self.fence_clear_button.setEnabled(bool(state.get("can_clear", False)))
        self.fence_exit_button.setEnabled(bool(state.get("can_exit", False)))
        self.fence_property.setEnabled(bool(state.get("can_change_property", True)))

        property_name = str(state.get("property_name") or "Pressure")
        property_index = self.fence_property.findText(property_name)
        if property_index >= 0:
            previous = self.fence_property.blockSignals(True)
            try:
                self.fence_property.setCurrentIndex(property_index)
            finally:
                self.fence_property.blockSignals(previous)

        return True

    def _add_slice_controls(self, layout):
        layout.addWidget(QLabel("切片"))
        self.slice_property = QComboBox()
        self.slice_property.setObjectName("slicePropertySelector")
        for text, key in [
            ("Pressure", "pressure_field"),
            ("Sw", "water_saturation_field"),
            ("Phi", "porosity_field"),
            ("Kx", "permeability_x_field"),
            ("Ky", "permeability_y_field"),
            ("Kz", "permeability_z_field"),
        ]:
            self.slice_property.addItem(text, key)
        layout.addWidget(self.slice_property)

        self.slice_axis = QComboBox()
        self.slice_axis.setObjectName("sliceAxisSelector")
        self.slice_axis.addItems(["I", "J", "K"])
        layout.addWidget(self.slice_axis)

        self.slice_layer = QSpinBox()
        self.slice_layer.setObjectName("sliceLayerSpinBox")
        self.slice_layer.setRange(0, 999999)
        self.slice_layer.setValue(0)
        self.slice_layer.setFixedWidth(58)
        self.slice_layer.setToolTip("切片层号，当前按 0 开始计数")
        layout.addWidget(self.slice_layer)

        apply_button = self._button("显示切片", "grid")
        apply_button.setText("显示")
        apply_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        apply_button.setFixedSize(64, 23)
        apply_button.clicked.connect(self._emit_slice_request)
        layout.addWidget(apply_button)

        reset_button = self._button("恢复整体场", "refresh")
        reset_button.setText("恢复")
        reset_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        reset_button.setFixedSize(64, 23)
        reset_button.clicked.connect(self.slice_reset_requested.emit)
        layout.addWidget(reset_button)

    def _add_threshold_controls(self, layout):
        layout.addWidget(QLabel("阈值"))

        self.threshold_min = QLineEdit()
        self.threshold_min.setObjectName("thresholdMinEdit")
        self.threshold_min.setPlaceholderText("min")
        self.threshold_min.setFixedWidth(58)
        self.threshold_min.setToolTip("当前属性最小阈值，留空表示不限制")
        layout.addWidget(self.threshold_min)

        self.threshold_max = QLineEdit()
        self.threshold_max.setObjectName("thresholdMaxEdit")
        self.threshold_max.setPlaceholderText("max")
        self.threshold_max.setFixedWidth(58)
        self.threshold_max.setToolTip("当前属性最大阈值，留空表示不限制")
        layout.addWidget(self.threshold_max)

        apply_button = self._button("应用当前属性阈值", "restrict")
        apply_button.setText("过滤")
        apply_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        apply_button.setFixedSize(64, 23)
        apply_button.clicked.connect(self._emit_threshold_request)
        layout.addWidget(apply_button)

        clear_button = self._button("清除阈值过滤", "clear")
        clear_button.setText("清除")
        clear_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        clear_button.setFixedSize(64, 23)
        clear_button.clicked.connect(self.threshold_clear_requested.emit)
        layout.addWidget(clear_button)

    def _add_time_controls(self, layout):
        layout.addWidget(QLabel("时间步"))

        self.time_step_index = QSpinBox()
        self.time_step_index.setObjectName("timeStepIndexSpinBox")
        self.time_step_index.setRange(0, 999999)
        self.time_step_index.setValue(0)
        self.time_step_index.setFixedWidth(58)
        self.time_step_index.setToolTip("时间步帧号，当前按 0 开始计数")
        layout.addWidget(self.time_step_index)

        for text, tooltip, kind, action, width in [
            ("准备", "准备当前属性的时间步播放", "refresh", "prepare", 54),
            ("播放", "播放/暂停时间步", "refresh", "play", 54),
            ("上", "上一时间步", "undo", "previous", 42),
            ("下", "下一时间步", "refresh", "next", 42),
            ("停止", "停止时间步播放并恢复静态场", "clear", "stop", 54),
        ]:
            button = self._button(tooltip, kind)
            button.setText(text)
            button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
            button.setFixedSize(width, 23)
            button.clicked.connect(
                lambda checked=False, name=action: self._emit_time_playback_request(name))
            layout.addWidget(button)

    def _add_preview_controls(self, layout):
        layout.addWidget(QLabel("预览"))

        for text, tooltip, kind, preview_kind, width in [
            ("网格", "预览角点网格", "grid", "grid", 54),
            ("井", "预览井轨迹", "well", "wells", 42),
            ("天然裂缝", "预览天然裂缝", "fracture", "natural_fractures", 78),
            ("人工裂缝", "预览人工裂缝", "fracture", "hydraulic_fractures", 78),
            ("全部裂缝", "预览全部裂缝", "fracture", "fractures", 78),
        ]:
            button = self._button(tooltip, kind)
            button.setText(text)
            button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
            button.setFixedSize(width, 23)
            button.clicked.connect(
                lambda checked=False, name=preview_kind:
                    self.geometry_preview_requested.emit(name))
            layout.addWidget(button)

        self.geometry_style_button = self._button(
            "设置井、射孔段和裂缝预览样式",
            "settings",
        )
        self.geometry_style_button.setObjectName(
            "geometryPreviewStyleButton")
        self.geometry_style_button.setText("样式")
        self.geometry_style_button.setToolButtonStyle(
            Qt.ToolButtonTextBesideIcon)
        self.geometry_style_button.setFixedSize(58, 23)
        self.geometry_style_button.clicked.connect(
            lambda checked=False: self.geometry_style_requested.emit())
        layout.addWidget(self.geometry_style_button)

        layout.addWidget(QLabel("静态属性"))
        self.static_preview_property = QComboBox()
        self.static_preview_property.setObjectName("staticPreviewPropertySelector")
        for text, key in self.STATIC_PREVIEW_PROPERTIES:
            self.static_preview_property.addItem(text, key)
        self.static_preview_property.setFixedWidth(118)
        layout.addWidget(self.static_preview_property)

        static_button = self._button("预览整体静态属性场", "pressure")
        static_button.setText("整体")
        static_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        static_button.setFixedSize(62, 23)
        static_button.clicked.connect(self._emit_static_preview_request)
        layout.addWidget(static_button)

        layout.addWidget(QLabel("分层"))
        self.static_layer_property = QComboBox()
        self.static_layer_property.setObjectName("staticLayerPreviewPropertySelector")
        for text, key in self.STATIC_PREVIEW_PROPERTIES:
            self.static_layer_property.addItem(text, key)
        self.static_layer_property.setFixedWidth(118)
        layout.addWidget(self.static_layer_property)

        self.static_layer_axis = QComboBox()
        self.static_layer_axis.setObjectName("staticLayerPreviewAxisSelector")
        self.static_layer_axis.addItems(["I", "J", "K"])
        self.static_layer_axis.setFixedWidth(46)
        layout.addWidget(self.static_layer_axis)

        self.static_layer_index = QSpinBox()
        self.static_layer_index.setObjectName("staticLayerPreviewIndexSpinBox")
        self.static_layer_index.setRange(1, 999999)
        self.static_layer_index.setValue(1)
        self.static_layer_index.setFixedWidth(58)
        self.static_layer_index.setToolTip("预览层号，按 1 开始计数")
        layout.addWidget(self.static_layer_index)

        layer_button = self._button("预览静态属性分层", "grid")
        layer_button.setText("预览")
        layer_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        layer_button.setFixedSize(62, 23)
        layer_button.clicked.connect(self._emit_static_layer_preview_request)
        layout.addWidget(layer_button)

    def _emit_slice_request(self):
        property_key = self.slice_property.currentData() or "pressure_field"
        axis = self.slice_axis.currentText().lower()
        layer = int(self.slice_layer.value())
        self.slice_requested.emit(property_key, axis, layer)

    def _emit_property_selected(self, *args):
        property_key = self.view_selector.currentData()
        if property_key:
            self.property_selected.emit(property_key)

    def set_property_key(self, property_key, emit=False):
        if not hasattr(self, "view_selector"):
            return False
        found = self.view_selector.findData(property_key)
        if found < 0:
            return False
        previous = self.view_selector.blockSignals(True)
        try:
            self.view_selector.setCurrentIndex(found)
        finally:
            self.view_selector.blockSignals(previous)
        if emit:
            self.property_selected.emit(property_key)
        return True

    def _emit_threshold_request(self):
        self.threshold_requested.emit(
            self.threshold_min.text().strip(),
            self.threshold_max.text().strip(),
        )

    def _emit_time_playback_request(self, action):
        self.time_playback_requested.emit(action, int(self.time_step_index.value()))

    def _emit_static_preview_request(self):
        property_key = self.static_preview_property.currentData() or "MATRIX_PORO"
        self.static_preview_requested.emit(property_key)

    def _emit_static_layer_preview_request(self):
        property_key = self.static_layer_property.currentData() or "MATRIX_PORO"
        axis = self.static_layer_axis.currentText().lower()
        layer = int(self.static_layer_index.value())
        self.static_layer_preview_requested.emit(property_key, axis, layer)

    def set_time_step_index(self, index, step_count=None):
        try:
            if step_count is not None and int(step_count) > 0:
                self.time_step_index.setRange(0, int(step_count) - 1)
            self.time_step_index.setValue(max(0, int(index)))
        except (AttributeError, TypeError, ValueError):
            pass

    def export_ui_state(self):
        state = {
            "view_selector_index": self.view_selector.currentIndex(),
            "view_selector_data": self.view_selector.currentData(),
            "view_selector_text": self.view_selector.currentText(),
        }
        if hasattr(self, "scale_selector"):
            state["scale"] = self.scale_selector.currentText()
        if hasattr(self, "slice_property"):
            state["slice_property"] = self.slice_property.currentData()
            state["slice_axis"] = self.slice_axis.currentText()
            state["slice_layer"] = int(self.slice_layer.value())
        if hasattr(self, "threshold_min"):
            state["threshold_min"] = self.threshold_min.text()
            state["threshold_max"] = self.threshold_max.text()
        if hasattr(self, "time_step_index"):
            state["time_step_index"] = int(self.time_step_index.value())
        if hasattr(self, "static_preview_property"):
            state["static_preview_property"] = self.static_preview_property.currentData()
            state["static_layer_property"] = self.static_layer_property.currentData()
            state["static_layer_axis"] = self.static_layer_axis.currentText()
            state["static_layer_index"] = int(self.static_layer_index.value())
        return state

    def restore_ui_state(self, state):
        if not isinstance(state, dict):
            return
        self._set_combo_from_state(
            self.view_selector,
            state.get("view_selector_data"),
            state.get("view_selector_text"),
            state.get("view_selector_index"),
        )
        if hasattr(self, "scale_selector") and state.get("scale") is not None:
            self._set_combo_text(self.scale_selector, state.get("scale"))
        if hasattr(self, "slice_property"):
            self._set_combo_from_state(self.slice_property, state.get("slice_property"), None, None)
            self._set_combo_text(self.slice_axis, state.get("slice_axis"))
            try:
                self.slice_layer.setValue(max(0, int(state.get("slice_layer", 0))))
            except (TypeError, ValueError):
                pass
        if hasattr(self, "threshold_min"):
            min_text = state.get("threshold_min", "")
            max_text = state.get("threshold_max", "")
            self.threshold_min.setText("" if min_text is None else str(min_text))
            self.threshold_max.setText("" if max_text is None else str(max_text))
        if hasattr(self, "time_step_index"):
            try:
                self.time_step_index.setValue(max(0, int(state.get("time_step_index", 0))))
            except (TypeError, ValueError):
                pass
        if hasattr(self, "static_preview_property"):
            self._set_combo_from_state(
                self.static_preview_property,
                state.get("static_preview_property"),
                None,
                None,
            )
            self._set_combo_from_state(
                self.static_layer_property,
                state.get("static_layer_property"),
                None,
                None,
            )
            self._set_combo_text(self.static_layer_axis, state.get("static_layer_axis"))
            try:
                self.static_layer_index.setValue(max(1, int(state.get("static_layer_index", 1))))
            except (TypeError, ValueError):
                pass

    def _set_combo_from_state(self, combo, data, text, index):
        previous = combo.blockSignals(True)
        try:
            if data is not None:
                found = combo.findData(data)
                if found >= 0:
                    combo.setCurrentIndex(found)
                    return
            if text:
                found = combo.findText(str(text))
                if found >= 0:
                    combo.setCurrentIndex(found)
                    return
            try:
                index = int(index)
            except (TypeError, ValueError):
                return
            if 0 <= index < combo.count():
                combo.setCurrentIndex(index)
        finally:
            combo.blockSignals(previous)

    def _set_combo_text(self, combo, text):
        previous = combo.blockSignals(True)
        try:
            found = combo.findText(str(text))
            if found >= 0:
                combo.setCurrentIndex(found)
        finally:
            combo.blockSignals(previous)

    def export_scale(self):
        try:
            return float(self.scale_selector.currentText())
        except (AttributeError, TypeError, ValueError):
            return 1.0

    def _button(self, tooltip, kind):
        button = QToolButton()
        button.setObjectName("viewToolbarButton")
        button.setIcon(painted_icon(semantic_icon_kind(kind, tooltip), 18))
        button.setIconSize(QSize(18, 18))
        button.setToolTip(tooltip)
        button.setFixedSize(24, 23)
        button.setAutoRaise(True)
        return button
