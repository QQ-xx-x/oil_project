# -*- coding: utf-8 -*-
"""工程主界面使用的二维、三维和图表视图窗口。"""

import json
import math
import os
from datetime import datetime, timezone

from PyQt5.QtCore import QEvent, QPointF, QRectF, Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QPainter, QPen, QPolygonF
from PyQt5.QtWidgets import QFileDialog, QCheckBox, QFrame, QLabel, QVBoxLayout, QWidget

from .geometry_preview_style_dialog import (
    COLOR_STYLE_KEYS,
    GeometryPreviewStyleDialog,
    normalize_geometry_preview_style,
)
from .view_toolbar import ViewToolbar
from .view_property_registry import view_property_spec


THREE_D_RESULT_KEYS = {
    "pressure_field",
    "water_saturation_field",
    "porosity_field",
    "permeability_x_field",
    "permeability_y_field",
    "permeability_z_field",
    "permeability_field",  # Kx 的旧版别名
}

DISPLAY_KEY_TO_PROPERTY = {
    "pressure_field": "pressure",
    "water_saturation_field": "sw",
    "porosity_field": "porosity",
    "permeability_x_field": "permeability_x",
    "permeability_y_field": "permeability_y",
    "permeability_z_field": "permeability_z",
    "permeability_field": "permeability_x",
}

DISPLAY_KEY_LABELS = {
    "pressure_field": "Pressure",
    "water_saturation_field": "Sw",
    "porosity_field": "Phi",
    "permeability_x_field": "Kx",
    "permeability_y_field": "Ky",
    "permeability_z_field": "Kz",
    "permeability_field": "Kx",
}

PICK_PROPERTY_LABELS = {
    "pressure": "Pressure",
    "sw": "Sw",
    "porosity": "Phi",
    "permeability_x": "Kx",
    "permeability_y": "Ky",
    "permeability_z": "Kz",
}

FENCE_SECTION_PROPERTIES = (
    "Pressure",
    "Kx",
    "Ky",
    "Kz",
    "Phi",
    "Sw",
)

FENCE_SECTION_STATE_INACTIVE = "inactive"
FENCE_SECTION_STATE_DRAWING = "drawing"
FENCE_SECTION_STATE_RESULT = "result"

STATIC_PREVIEW_LABELS = {
    "MATRIX_PORO": "MATRIX_PORO",
    "MATRIX_PERMX": "MATRIX_PERMX",
    "MATRIX_PERMY": "MATRIX_PERMY",
    "MATRIX_PERMZ": "MATRIX_PERMZ",
    "DFN_PORO": "DFN_PORO",
    "DFN_PERMX": "DFN_PERMX",
    "DFN_PERMY": "DFN_PERMY",
    "DFN_PERMZ": "DFN_PERMZ",
    "SIGMA": "SIGMA",
}

GEOMETRY_PREVIEW_LABELS = {
    "grid": "角点网格",
    "wells": "井轨迹",
    "natural_fractures": "天然裂缝",
    "hydraulic_fractures": "人工裂缝",
    "fractures": "全部裂缝",
}

GEOMETRY_PREVIEW_STYLE_KEYS = frozenset({
    "well_color",
    "well_radius",
    "perforation_color",
    "show_perforations",
    "natural_fracture_color",
    "hydraulic_fracture_color",
    "fracture_show_edges",
    "natural_fracture_edge_color",
    "hydraulic_fracture_edge_color",
    "fracture_edge_line_width",
})

RESULT_STYLES = {
    "pressure_field": {
        "legend": "压力",
        "unit": "bar",
        "ticks": ("800", "500", "200"),
        "colors": ["#ff1800", "#ff9a00", "#fff35a", "#6ad348"],
        "surface": QColor("#e7c332"),
    },
    "water_saturation_field": {
        "legend": "含水饱和度",
        "unit": "0-1",
        "ticks": ("1.0", "0.5", "0.0"),
        "colors": ["#004dff", "#00a8ff", "#00e0c8", "#d7fff1"],
        "surface": QColor("#3ec8d9"),
    },
    "permeability_x_field": {
        "legend": "Kx 渗透率",
        "unit": "mD",
        "ticks": ("100", "10", "1"),
        "colors": ["#ff0000", "#ff9a00", "#ffff00", "#3cff00", "#00ddcc"],
        "surface": QColor("#c5d000"),
    },
    "permeability_y_field": {
        "legend": "Ky 渗透率",
        "unit": "mD",
        "ticks": ("100", "10", "1"),
        "colors": ["#c400ff", "#4b64ff", "#00b7ff", "#00df9a", "#d2f06b"],
        "surface": QColor("#71c7a8"),
    },
    "permeability_z_field": {
        "legend": "Kz 渗透率",
        "unit": "mD",
        "ticks": ("100", "10", "1"),
        "colors": ["#ff3b3b", "#ffb000", "#ffe55a", "#65c96a", "#3da5d9"],
        "surface": QColor("#d0be55"),
    },
    "permeability_field": {
        "legend": "Kx 渗透率",
        "unit": "mD",
        "ticks": ("100", "10", "1"),
        "colors": ["#ff0000", "#ff9a00", "#ffff00", "#3cff00", "#00ddcc"],
        "surface": QColor("#c5d000"),
    },
    "porosity_field": {
        "legend": "孔隙度",
        "unit": "0-1",
        "ticks": ("0.30", "0.15", "0.00"),
        "colors": ["#7428d8", "#4864e8", "#2aa7ff", "#b7e3ff"],
        "surface": QColor("#7aa6ff"),
    },
}


CHART_STYLES = {
    "production_curve": {
        "title": "生产曲线",
        "x": "时间",
        "y": "产量",
        "color": QColor("#2970c8"),
    },
    "relative_permeability_curve": {
        "title": "相对渗透率曲线",
        "x": "含水饱和度 Sw",
        "y": "相对渗透率 kr",
        "color": QColor("#23a65a"),
    },
    "blasingame_curve": {
        "title": "Blasingame 曲线",
        "x": "时间函数",
        "y": "规整化流量",
        "color": QColor("#d45500"),
    },
    "pvt_curve": {
        "title": "PVT 表曲线",
        "x": "压力",
        "y": "Z 因子",
        "color": QColor("#7b4bc4"),
    },
}


class ThreeDViewport(QWidget):
    interaction_message = pyqtSignal(str)
    fence_state_changed = pyqtSignal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("threeDViewport")
        self.setMinimumHeight(360)
        self._real_view = None
        self._real_renderer = None
        self._real_view_error = ""
        self.simulation_data = None
        self.preview_data = None
        self._geometry_preview_style = None
        self._preview_mode_active = False
        self.context_title = "当前结果：三维视图"
        self.context_detail = "在结果树中选择结果或图层后，这里显示对应占位视图。"
        self.display_key = "pressure_field"
        self._rendered_display_key = None
        self._slice_state = None
        self._threshold_state = None
        self._camera_state = None
        self.current_render_context = self._make_render_context("pressure_field")
        self.interaction_mode = "normal"
        self.fence_section_property = "Pressure"
        self._fence_section_state = FENCE_SECTION_STATE_INACTIVE
        self._fence_qt_event_filter_installed = False
        self._simulation_data_revision = 0
        self._pending_post_show_render_revision = None
        self._post_show_render_timer = QTimer(self)
        self._post_show_render_timer.setSingleShot(True)
        self._post_show_render_timer.timeout.connect(
            self._finalize_post_show_simulation_render
        )
        self.coordinate_axes_visible = False
        self.camera_direction_locked = False
        self.layers = {
            "grid": True,
            "well": True,
            "natural_fractures": True,
            "hydraulic_fractures": True,
            "dual_porosity": False,
            "grid_refinement": True,
        }

    def _make_render_context(self, display_key, mode="full", axis=None, layer_index=None):
        display_key = display_key if display_key in DISPLAY_KEY_TO_PROPERTY else "pressure_field"
        return {
            "display_key": display_key,
            "property_name": DISPLAY_KEY_TO_PROPERTY[display_key],
            "mode": mode,
            "axis": axis,
            "layer_index": layer_index,
        }

    def _set_full_render_context(self, display_key):
        if display_key in DISPLAY_KEY_TO_PROPERTY:
            self.current_render_context = self._make_render_context(display_key)

    def _set_layer_render_context(self, display_key, axis, layer):
        if display_key in DISPLAY_KEY_TO_PROPERTY:
            self.current_render_context = self._make_render_context(
                display_key,
                mode="layer",
                axis=str(axis).lower(),
                layer_index=int(layer),
            )

    def _set_interaction_mode(self, mode):
        mode = mode or "normal"
        if mode != "fence":
            self._deactivate_fence_interaction(
                clear_result=False,
                render=False,
            )
        if mode != "magnify":
            self._deactivate_magnify(render=False)
        if mode != "measure":
            self._disable_measure(clear_line=False)
        if mode != "pick":
            self._disable_cell_picking(clear_highlight=False)
        self.interaction_mode = mode

    def _deactivate_fence_interaction(
        self,
        clear_result=False,
        render=False,
    ):
        self._uninstall_fence_qt_interaction()
        state = self.fence_section_ui_state()
        if not state["drawing"] and not state["has_result"]:
            if self.interaction_mode == "fence":
                self.interaction_mode = "normal"
            return True

        ok, _ = self.exit_fence_section(
            clear_result=clear_result,
            render=render,
        )
        return ok

    def _install_fence_qt_interaction(self):
        view = self._real_view
        plotter = getattr(view, "plotter", None) if view is not None else None
        if plotter is None:
            return False
        if not self._fence_qt_event_filter_installed:
            plotter.installEventFilter(self)
            self._fence_qt_event_filter_installed = True
        if hasattr(view, "set_cross_cursor"):
            view.set_cross_cursor(True)

        renderer = self._real_renderer
        remove_observers = getattr(
            renderer,
            "_remove_fence_section_observers",
            None,
        )
        if remove_observers is not None:
            try:
                remove_observers()
            except Exception:
                pass
        return True

    def _uninstall_fence_qt_interaction(self):
        view = self._real_view
        plotter = getattr(view, "plotter", None) if view is not None else None
        if self._fence_qt_event_filter_installed and plotter is not None:
            try:
                plotter.removeEventFilter(self)
            except Exception:
                pass
        self._fence_qt_event_filter_installed = False
        if view is not None and hasattr(view, "set_cross_cursor"):
            view.set_cross_cursor(False)

    def _sync_fence_qt_event_position(self, event):
        view = self._real_view
        plotter = getattr(view, "plotter", None) if view is not None else None
        renderer = self._real_renderer
        if plotter is None or renderer is None:
            return None

        try:
            pos = event.pos()
            logical_x = int(pos.x())
            logical_y = int(pos.y())
            width = max(1, int(plotter.width()))
            height = max(1, int(plotter.height()))
            logical_x = max(0, min(width - 1, logical_x))
            logical_y = max(0, min(height - 1, logical_y))
        except Exception:
            return None

        get_interactor = getattr(
            renderer,
            "_get_fence_section_interactor",
            None,
        )
        interactor = get_interactor() if get_interactor is not None else None
        if interactor is None:
            return None

        set_event_information = getattr(
            plotter,
            "_setEventInformation",
            None,
        )
        if set_event_information is not None:
            try:
                ctrl = bool(event.modifiers() & Qt.ControlModifier)
                shift = bool(event.modifiers() & Qt.ShiftModifier)
                repeat = int(event.type() == QEvent.MouseButtonDblClick)
                set_event_information(
                    logical_x,
                    logical_y,
                    ctrl,
                    shift,
                    chr(0),
                    repeat,
                    None,
                )
                display_x, display_y = interactor.GetEventPosition()
                return (
                    renderer,
                    interactor,
                    int(display_x),
                    int(display_y),
                )
            except Exception:
                pass

        try:
            pixel_ratio = float(plotter._getPixelRatio())
        except Exception:
            try:
                pixel_ratio = float(plotter.devicePixelRatioF())
            except Exception:
                pixel_ratio = 1.0
        display_x = int(round(logical_x * pixel_ratio))
        display_y = int(round((height - 1 - logical_y) * pixel_ratio))

        try:
            interactor.SetEventPosition(display_x, display_y)
        except Exception:
            try:
                interactor.SetEventInformation(
                    display_x,
                    display_y,
                    0,
                    0,
                    "0",
                    0,
                    None,
                )
            except Exception:
                return None
        return renderer, interactor, display_x, display_y

    def _fence_world_point_from_display(self, display_x, display_y):
        renderer = self._real_renderer
        cache = getattr(renderer, "cache", {}) or {}
        bounds = cache.get("fence_section_bounds")
        convert = getattr(renderer, "display_to_world_xy", None)
        if bounds is None or convert is None:
            return None
        try:
            point = convert(
                display_x=float(display_x),
                display_y=float(display_y),
                world_bounds=bounds,
            )
            if point is None:
                return None
            xmin, xmax, ymin, ymax, zmin, zmax = [
                float(value) for value in bounds
            ]
            px, py, _ = point
            span = max(
                xmax - xmin,
                ymax - ymin,
                zmax - zmin,
                1.0,
            )
            tolerance = span * 1e-7
            if (
                px < xmin - tolerance
                or px > xmax + tolerance
                or py < ymin - tolerance
                or py > ymax + tolerance
            ):
                return None
            return float(px), float(py), float(zmax)
        except Exception:
            return None

    def eventFilter(self, obj, event):  # noqa: N802
        view = self._real_view
        plotter = getattr(view, "plotter", None) if view is not None else None
        if (
            self._fence_qt_event_filter_installed
            and obj is plotter
            and self.interaction_mode == "fence"
        ):
            state = self.fence_section_ui_state()
            if not state["drawing"]:
                self._uninstall_fence_qt_interaction()
            else:
                event_type = event.type()
                if event_type in {
                    QEvent.MouseButtonPress,
                    QEvent.MouseButtonDblClick,
                } and event.button() == Qt.LeftButton:
                    synced = self._sync_fence_qt_event_position(event)
                    if synced is not None:
                        renderer, interactor, display_x, display_y = synced
                        cache = getattr(renderer, "cache", {}) or {}
                        points_before = len(
                            cache.get("fence_section_points", []) or []
                        )
                        callback = getattr(
                            renderer,
                            "_on_fence_section_left_button_press",
                            None,
                        )
                        callback_error = None
                        if callback is not None:
                            try:
                                callback(interactor, "LeftButtonPressEvent")
                            except Exception as exc:
                                # 渲染器回调意外失败时，保留
                                # Qt 侧的世界坐标拾取回退。
                                callback_error = exc
                        points_after = len(
                            cache.get("fence_section_points", []) or []
                        )
                        if points_after == points_before:
                            point = self._fence_world_point_from_display(
                                display_x,
                                display_y,
                            )
                            append_point = getattr(
                                renderer,
                                "_append_fence_section_point",
                                None,
                            )
                            if point is not None and append_point is not None:
                                append_point(point)
                            points_after = len(
                                cache.get("fence_section_points", []) or []
                            )

                        if points_after > points_before:
                            self.interaction_message.emit(
                                f"[折线剖面] 已添加路径点 {points_after}"
                            )
                            self.fence_state_changed.emit(
                                self.fence_section_ui_state()
                            )
                        elif event_type == QEvent.MouseButtonPress:
                            if callback_error is not None:
                                self.interaction_message.emit(
                                    "[折线剖面] 点击处理失败："
                                    f"{callback_error}"
                                )
                            else:
                                self.interaction_message.emit(
                                    "[折线剖面] 点击位置未添加路径点，"
                                    "请在有效网格范围内点击或避开重复点"
                                )

                        if (
                            event_type == QEvent.MouseButtonDblClick
                            and self.fence_section_ui_state()["drawing"]
                        ):
                            complete = getattr(
                                renderer,
                                "complete_vertical_fence_section",
                                None,
                            )
                            if complete is not None:
                                complete()
                    return True
                if event_type == QEvent.MouseMove:
                    synced = self._sync_fence_qt_event_position(event)
                    if synced is not None:
                        renderer, interactor, display_x, display_y = synced
                        callback = getattr(
                            renderer,
                            "_on_fence_section_mouse_move",
                            None,
                        )
                        if callback is not None:
                            callback(interactor, "MouseMoveEvent")
                    return True
                if (
                    event_type == QEvent.MouseButtonRelease
                    and event.button() == Qt.LeftButton
                ):
                    return True
        return super().eventFilter(obj, event)

    def _current_pick_property(self):
        property_name = self.current_render_context.get("property_name", "pressure")
        return PICK_PROPERTY_LABELS.get(property_name, "Pressure")

    def _current_display_label(self):
        display_key = self.current_render_context.get("display_key", self.display_key)
        return DISPLAY_KEY_LABELS.get(display_key, display_key)

    def set_fence_section_property_preference(self, property_name):
        """更新界面侧的围栏属性，不调用渲染器。"""
        property_name = str(property_name or "").strip()
        if property_name not in FENCE_SECTION_PROPERTIES:
            return False
        self.fence_section_property = property_name
        return True

    def fence_section_ui_state(self):
        """返回从当前渲染器缓存派生的只读界面状态。"""
        renderer = self._real_renderer
        cache = getattr(renderer, "cache", {}) or {}

        drawing = bool(cache.get("fence_section_drawing", False))
        has_result = bool(
            cache.get("fence_section_actor") is not None
            or cache.get("fence_section_data") is not None
        )

        if drawing or has_result:
            property_name = str(
                cache.get("fence_section_property")
                or self.fence_section_property
            ).strip()
        else:
            property_name = self.fence_section_property
        if property_name not in FENCE_SECTION_PROPERTIES:
            property_name = self.fence_section_property

        points = cache.get("fence_section_points", []) or []
        try:
            point_count = len(points)
        except TypeError:
            point_count = 0

        if drawing:
            state = FENCE_SECTION_STATE_DRAWING
        elif has_result:
            state = FENCE_SECTION_STATE_RESULT
        else:
            state = FENCE_SECTION_STATE_INACTIVE

        self._fence_section_state = state
        self.fence_section_property = property_name

        return {
            "state": state,
            "property_name": property_name,
            "drawing": drawing,
            "has_result": has_result,
            "point_count": point_count,
            "renderer_available": renderer is not None,
            "has_simulation_data": self.simulation_data is not None,
            "can_start": self.simulation_data is not None,
            "can_complete": drawing,
            "can_cancel": drawing,
            "can_clear": has_result,
            "can_exit": drawing or has_result,
            "can_change_property": True,
        }

    def _fence_renderer_method(self, *method_names):
        renderer = self._real_renderer
        if renderer is None:
            return None
        for method_name in method_names:
            method = getattr(renderer, method_name, None)
            if method is not None:
                return method
        return None

    def _fence_renderer_failure_message(self, fallback):
        renderer = self._real_renderer
        cache = getattr(renderer, "cache", {}) or {}
        detail = str(cache.get("fence_section_last_info") or "").strip()
        if detail:
            return f"{fallback}：{detail}"
        return fallback

    def _ensure_fence_renderer(self):
        if self.simulation_data is None:
            return None, "[折线剖面] 当前没有可用的模拟结果"
        if self._real_renderer is None and not self._ensure_real_view():
            detail = self._real_view_error or "未知错误"
            return None, f"[折线剖面] 无法初始化 3D 渲染器：{detail}"
        if self._real_renderer is None:
            return None, "[折线剖面] 当前没有可用的 3D 渲染器"
        return self._real_renderer, ""

    def start_fence_section(self, property_name=None):
        property_name = str(
            property_name or self.fence_section_property
        ).strip()
        if not self.set_fence_section_property_preference(property_name):
            return False, f"[折线剖面] 不支持的属性：{property_name}"

        renderer, message = self._ensure_fence_renderer()
        if renderer is None:
            return False, message

        if (
            self._preview_mode_active
            or self._slice_state is not None
            or self._threshold_state is not None
            or self.time_playback_info().get("ready")
        ):
            self._slice_state = None
            self._threshold_state = None
            self._set_full_render_context(self.display_key)
            self._render_real_result()

        method = self._fence_renderer_method(
            "enable_fence_section",
            "enable_vertical_fence_section",
        )
        if method is None:
            return False, "[折线剖面] 渲染端缺少开启剖面接口"

        self._set_interaction_mode("fence")
        try:
            ok = bool(method(
                self.simulation_data,
                property_name=property_name,
            ))
        except Exception as exc:
            self._set_interaction_mode("normal")
            return False, f"[折线剖面] 开启失败：{exc}"

        state = self.fence_section_ui_state()
        if not ok or not state["drawing"]:
            self._set_interaction_mode("normal")
            return False, self._fence_renderer_failure_message(
                "[折线剖面] 未能进入路径选点状态"
            )

        self._install_fence_qt_interaction()
        return True, (
            f"[折线剖面] 已开始绘制 {property_name}："
            "左键添加路径点，双击或点击“完成”生成剖面"
        )

    def complete_fence_section(self):
        state = self.fence_section_ui_state()
        if not state["drawing"]:
            return False, "[折线剖面] 当前不在路径绘制状态"
        if state["point_count"] < 2:
            return False, "[折线剖面] 至少需要选择两个有效路径点"

        method = self._fence_renderer_method(
            "complete_vertical_fence_section",
        )
        if method is None:
            return False, "[折线剖面] 渲染端缺少完成剖面接口"

        try:
            ok = bool(method())
        except Exception as exc:
            return False, f"[折线剖面] 生成失败：{exc}"

        state = self.fence_section_ui_state()
        if not ok or not state["has_result"]:
            if not state["drawing"]:
                self._uninstall_fence_qt_interaction()
                self.interaction_mode = "normal"
            return False, self._fence_renderer_failure_message(
                "[折线剖面] 剖面生成失败"
            )
        self._uninstall_fence_qt_interaction()
        return True, f"[折线剖面] 剖面生成完成：{state['property_name']}"

    def cancel_fence_section(self):
        state = self.fence_section_ui_state()
        if not state["drawing"]:
            return False, "[折线剖面] 当前没有正在进行的路径绘制"

        method = self._fence_renderer_method(
            "cancel_vertical_fence_section",
        )
        if method is None:
            return False, "[折线剖面] 渲染端缺少取消绘制接口"

        try:
            method(render=True)
        except Exception as exc:
            return False, f"[折线剖面] 取消绘制失败：{exc}"

        state = self.fence_section_ui_state()
        if state["drawing"]:
            return False, "[折线剖面] 取消绘制后状态未正确复位"
        self._uninstall_fence_qt_interaction()
        if self.interaction_mode == "fence":
            self.interaction_mode = "normal"
        return True, "[折线剖面] 已取消当前路径绘制"

    def clear_fence_section(self):
        state = self.fence_section_ui_state()
        if not state["has_result"]:
            return False, "[折线剖面] 当前没有可清除的剖面结果"

        method = self._fence_renderer_method(
            "clear_fence_section",
            "clear_vertical_fence_section",
        )
        if method is None:
            return False, "[折线剖面] 渲染端缺少清除剖面接口"

        try:
            method(render=True)
        except Exception as exc:
            return False, f"[折线剖面] 清除剖面失败：{exc}"

        state = self.fence_section_ui_state()
        if state["has_result"]:
            return False, "[折线剖面] 清除后仍检测到剖面结果"
        self._uninstall_fence_qt_interaction()
        if self.interaction_mode == "fence":
            self.interaction_mode = "normal"
        return True, "[折线剖面] 已清除剖面结果"

    def exit_fence_section(self, clear_result=True, render=True):
        state = self.fence_section_ui_state()
        if not state["drawing"] and not state["has_result"]:
            return False, "[折线剖面] 当前未开启剖面功能"

        method = self._fence_renderer_method(
            "disable_fence_section",
            "disable_vertical_fence_section",
        )
        if method is None:
            return False, "[折线剖面] 渲染端缺少退出剖面接口"

        try:
            method(
                clear_result=bool(clear_result),
                render=bool(render),
            )
        except Exception as exc:
            return False, f"[折线剖面] 退出失败：{exc}"

        state = self.fence_section_ui_state()
        if state["drawing"]:
            return False, "[折线剖面] 退出后仍处于路径绘制状态"
        if clear_result and state["has_result"]:
            return False, "[折线剖面] 退出后剖面结果未清除"
        self._uninstall_fence_qt_interaction()
        if self.interaction_mode == "fence":
            self.interaction_mode = "normal"
        if clear_result:
            return True, "[折线剖面] 已退出并清除剖面"
        return True, "[折线剖面] 已退出绘制交互并保留剖面"

    def set_fence_property(self, property_name):
        property_name = str(property_name or "").strip()
        previous_property = self.fence_section_property
        if not self.set_fence_section_property_preference(property_name):
            return False, f"[折线剖面] 不支持的属性：{property_name}"

        state = self.fence_section_ui_state()
        if not state["drawing"] and not state["has_result"]:
            return True, f"[折线剖面] 当前属性：{property_name}"

        method = self._fence_renderer_method(
            "set_vertical_fence_section_property",
        )
        if method is None:
            self.fence_section_property = previous_property
            return False, "[折线剖面] 渲染端缺少属性切换接口"

        try:
            ok = bool(method(property_name))
        except Exception as exc:
            self.fence_section_property = previous_property
            return False, f"[折线剖面] 属性切换失败：{exc}"

        state = self.fence_section_ui_state()
        if not ok or state["property_name"] != property_name:
            self.fence_section_property = previous_property
            return False, self._fence_renderer_failure_message(
                f"[折线剖面] 无法切换到属性 {property_name}"
            )
        return True, f"[折线剖面] 当前属性：{property_name}"

    def _handle_renderer_interaction_message(self, message):
        message = str(message or "").strip()
        if message:
            self.interaction_message.emit(message)

        state = self.fence_section_ui_state()
        if not state["drawing"]:
            self._uninstall_fence_qt_interaction()
        if (
            self.interaction_mode == "fence"
            and not state["drawing"]
            and not state["has_result"]
        ):
            self.interaction_mode = "normal"
        self.fence_state_changed.emit(state)

    def _reset_fence_section_for_context_change(self, render=False):
        state = self.fence_section_ui_state()
        ok = True
        if state["drawing"] or state["has_result"]:
            ok, _ = self.exit_fence_section(
                clear_result=True,
                render=render,
            )
        elif self.interaction_mode == "fence":
            self.interaction_mode = "normal"

        state = self.fence_section_ui_state()
        self.fence_state_changed.emit(state)
        return ok

    def shutdown_interactions(self):
        self._reset_fence_section_for_context_change(render=False)
        if self.interaction_mode != "normal":
            self._set_interaction_mode("normal")
        return True

    def has_simulation_data(self):
        return self.simulation_data is not None

    def _no_simulation_result_message(self, feature):
        return f"[{feature}] 当前 3D 窗口没有可用模拟结果，请先运行或加载模拟结果"

    def set_context(self, title, detail, display_key=None):
        if display_key and display_key not in THREE_D_RESULT_KEYS:
            return
        self.context_title = title
        self.context_detail = detail
        if display_key:
            if display_key != self.display_key:
                self._slice_state = None
                self._threshold_state = None
            self.display_key = display_key
            self._set_full_render_context(display_key)
        should_render = (
            self.simulation_data is not None
            and self._rendered_display_key != self.display_key
        )
        if should_render and self._ensure_real_view():
            self._render_real_result()
        self.update()

    def set_simulation_data(self, sim_data):
        if sim_data is not self.simulation_data:
            self._reset_fence_section_for_context_change(render=False)
            self._simulation_data_revision += 1
        self._post_show_render_timer.stop()
        self._pending_post_show_render_revision = None

        needs_post_show_refresh = self._real_view is None
        if self._real_view is not None:
            try:
                needs_post_show_refresh = bool(self._real_view.isHidden())
            except Exception:
                needs_post_show_refresh = False

        self.simulation_data = sim_data
        if sim_data is None:
            self._rendered_display_key = None
            if self._real_view is not None:
                self._real_view.hide()
            self.update()
            return
        if sim_data is not None and self._ensure_real_view():
            self._restore_saved_visual_state()
            if needs_post_show_refresh:
                self._pending_post_show_render_revision = (
                    self._simulation_data_revision
                )
                # 切换算例/项目后，show() 和第一次 VTK 重建会在同一调用
                # 栈中发生。待 Qt 处理完挂起的显示/OpenGL 事件后，
                # 再渲染一次。
                self._post_show_render_timer.start(0)
        self.update()

    def _finalize_post_show_simulation_render(self):
        revision = self._pending_post_show_render_revision
        self._pending_post_show_render_revision = None
        if (
            revision is None
            or revision != self._simulation_data_revision
            or self.simulation_data is None
        ):
            return
        if not self._ensure_real_view():
            return
        self._restore_saved_visual_state()
        self.update()

    def refresh_after_show(self):
        """3D 标签页重新可见后刷新其 OpenGL 画面。"""

        if self.simulation_data is None or not self._ensure_real_view():
            self.update()
            return False
        if self._rendered_display_key is None:
            self._restore_saved_visual_state()
        else:
            try:
                if hasattr(self._real_view, "render_now"):
                    self._real_view.render_now()
                else:
                    plotter = getattr(self._real_renderer, "plotter", None)
                    if plotter is not None and hasattr(plotter, "render"):
                        plotter.render()
            except Exception:
                self._restore_saved_visual_state()
        self.update()
        return True

    def set_preview_data(self, sim_data):
        if sim_data is self.preview_data:
            return
        self._reset_fence_section_for_context_change(render=False)
        self.preview_data = sim_data
        if self._preview_mode_active and self._real_renderer is not None:
            self._real_renderer.clear_cache()
            self._preview_mode_active = False
            self._rendered_display_key = None
            self.update()

    def _preview_source_data(self):
        return self.preview_data or self.simulation_data

    def _geometry_preview_controller(self, ensure=True):
        if self._real_renderer is None:
            if not ensure or not self._ensure_real_view():
                detail = self._real_view_error or "未知错误"
                return None, f"[预览样式] 无法初始化 3D 渲染器：{detail}"

        preview = getattr(
            self._real_renderer,
            "geometry_preview",
            None,
        )
        if preview is None:
            return None, "[预览样式] 渲染端缺少 geometry_preview"
        return preview, ""

    def get_geometry_preview_style(self):
        """为当前三维视口返回 `(ok, message, style)`。"""
        if self._real_renderer is None and self._geometry_preview_style is not None:
            return True, "[预览样式] 已读取缓存样式", dict(
                self._geometry_preview_style)

        preview, error = self._geometry_preview_controller(ensure=True)
        if preview is None:
            return False, error, {}

        getter = getattr(preview, "get_geometry_style", None)
        if getter is None:
            return False, "[预览样式] 渲染端缺少 get_geometry_style", {}

        try:
            style = getter()
        except Exception as exc:
            return False, f"[预览样式] 读取失败：{exc}", {}

        if not isinstance(style, dict):
            return False, "[预览样式] 渲染端返回了无效的样式数据", {}

        self._geometry_preview_style = dict(style)
        return True, "[预览样式] 已读取当前样式", dict(style)

    def set_geometry_preview_style(
        self,
        style=None,
        render_now=True,
        **style_changes,
    ):
        """校验几何预览样式更改并转发给渲染层。"""
        if style is None:
            payload = {}
        elif isinstance(style, dict):
            payload = dict(style)
        else:
            return False, "[预览样式] 样式参数必须是字典", {}

        payload.update(style_changes)
        unknown_keys = sorted(
            set(payload) - GEOMETRY_PREVIEW_STYLE_KEYS
        )
        if unknown_keys:
            names = ", ".join(unknown_keys)
            return False, f"[预览样式] 不支持的样式参数：{names}", {}

        preview, error = self._geometry_preview_controller(ensure=True)
        if preview is None:
            return False, error, {}

        setter = getattr(preview, "set_geometry_style", None)
        if setter is None:
            return False, "[预览样式] 渲染端缺少 set_geometry_style", {}

        try:
            normalized = setter(
                **payload,
                sim_data=self._preview_source_data(),
                render_now=bool(render_now),
            )
        except (TypeError, ValueError) as exc:
            return False, f"[预览样式] 参数无效：{exc}", {}
        except Exception as exc:
            return False, f"[预览样式] 更新失败：{exc}", {}

        if not isinstance(normalized, dict):
            return False, "[预览样式] 渲染端返回了无效的样式数据", {}

        self._geometry_preview_style = dict(normalized)
        if render_now:
            self.update()
        return True, "[预览样式] 已更新几何预览样式", dict(normalized)

    def _apply_cached_geometry_preview_style(self, render_now=False):
        if self._geometry_preview_style is None:
            return True, ""
        ok, message, _ = self.set_geometry_preview_style(
            dict(self._geometry_preview_style),
            render_now=render_now,
        )
        return ok, message

    def export_geometry_preview_style_state(self):
        """返回可安全序列化为 JSON 的样式状态，且不创建渲染器。"""
        style = self._geometry_preview_style
        if self._real_renderer is not None:
            ok, _message, current = self.get_geometry_preview_style()
            if ok:
                style = current
        if not isinstance(style, dict):
            return None

        normalized = normalize_geometry_preview_style(style)
        payload = dict(normalized)
        for key in COLOR_STYLE_KEYS:
            payload[key] = list(normalized[key])
        return payload

    def restore_geometry_preview_style_state(self, style):
        """缓存持久化样式，仅在渲染已存在时应用。"""
        if style is None:
            self._geometry_preview_style = None
            return True, ""
        if not isinstance(style, dict):
            return False, "[预览样式] 保存的样式状态无效"

        self._geometry_preview_style = normalize_geometry_preview_style(style)
        if self._real_renderer is not None:
            return self._apply_cached_geometry_preview_style(
                render_now=False)
        return True, ""

    def _enter_preview_mode(self):
        self._reset_fence_section_for_context_change(render=False)
        if self.interaction_mode != "normal":
            self._set_interaction_mode("normal")
        if not self._preview_mode_active and self._real_renderer is not None:
            self._real_renderer.clear_cache()
            self._preview_mode_active = True
            self._rendered_display_key = None

    def toggle_geometry_preview(self, preview_kind):
        preview_kind = str(preview_kind or "").strip()
        method_name = {
            "grid": "render_grid",
            "wells": "render_wells",
            "natural_fractures": "render_natural_fractures",
            "hydraulic_fractures": "render_hydraulic_fractures",
            "fractures": "render_fractures",
        }.get(preview_kind)
        label = GEOMETRY_PREVIEW_LABELS.get(preview_kind, preview_kind)
        if method_name is None:
            return False, f"[预览] 不支持的几何预览：{preview_kind}"
        sim_data = self._preview_source_data()
        if sim_data is None:
            return False, "[预览] 当前没有可用预览数据，请先构建 CaseDataset"
        if not self._ensure_real_view():
            return False, f"[预览] 无法初始化 3D 渲染器：{self._real_view_error or '未知错误'}"
        renderer = self._real_renderer
        preview = getattr(renderer, "geometry_preview", None)
        if preview is None:
            return False, "[预览] 渲染端缺少 geometry_preview"
        method = getattr(preview, method_name, None)
        if method is None:
            return False, f"[预览] 渲染端缺少 {method_name}"
        state_method = getattr(preview, self._geometry_preview_state_method(preview_kind), None)
        was_visible = bool(state_method()) if state_method is not None else False
        self._enter_preview_mode()
        try:
            method(sim_data, render_now=True)
        except Exception as exc:
            return False, f"[预览] {label}预览失败：{exc}"
        is_visible = bool(state_method()) if state_method is not None else False
        self.update()
        if was_visible and not is_visible:
            return True, f"[预览] 已隐藏{label}"
        if is_visible:
            return True, f"[预览] 已显示{label}"
        return False, f"[预览] 没有可显示的{label}数据"

    def _geometry_preview_state_method(self, preview_kind):
        return {
            "grid": "is_grid_visible",
            "wells": "is_wells_visible",
            "natural_fractures": "is_natural_fractures_visible",
            "hydraulic_fractures": "is_hydraulic_fractures_visible",
            "fractures": "is_fractures_visible",
        }.get(preview_kind, "")

    def toggle_static_property_preview(self, property_key):
        property_key = str(property_key or "").strip()
        label = STATIC_PREVIEW_LABELS.get(property_key, property_key)
        sim_data = self._preview_source_data()
        if sim_data is None:
            return False, "[静态属性预览] 当前没有可用预览数据，请先构建 CaseDataset"
        if not self._ensure_real_view():
            return False, f"[静态属性预览] 无法初始化 3D 渲染器：{self._real_view_error or '未知错误'}"
        renderer = self._real_renderer
        preview = getattr(renderer, "static_property_preview", None)
        if preview is None:
            return False, "[静态属性预览] 渲染端缺少 static_property_preview"
        was_visible = False
        if hasattr(preview, "is_current_property"):
            try:
                was_visible = bool(preview.is_current_property(property_key))
            except Exception:
                was_visible = False
        self._enter_preview_mode()
        try:
            preview.render_property(sim_data, property_key, render_now=True)
        except Exception as exc:
            return False, f"[静态属性预览] {label} 预览失败：{exc}"
        is_visible = False
        if hasattr(preview, "is_current_property"):
            try:
                is_visible = bool(preview.is_current_property(property_key))
            except Exception:
                is_visible = False
        self.update()
        if was_visible and not is_visible:
            return True, f"[静态属性预览] 已隐藏 {label}"
        if is_visible:
            return True, f"[静态属性预览] 已显示 {label}"
        return False, f"[静态属性预览] 没有可显示的 {label} 数据"

    def toggle_static_property_layer_preview(self, property_key, axis, layer):
        property_key = str(property_key or "").strip()
        axis = str(axis or "").strip().lower()
        label = STATIC_PREVIEW_LABELS.get(property_key, property_key)
        try:
            layer = int(layer)
        except (TypeError, ValueError):
            return False, "[分层预览] 层号必须是整数"
        if axis not in {"i", "j", "k"}:
            return False, f"[分层预览] 不支持的方向：{axis}"
        sim_data = self._preview_source_data()
        if sim_data is None:
            return False, "[分层预览] 当前没有可用预览数据，请先构建 CaseDataset"
        if not self._ensure_real_view():
            return False, f"[分层预览] 无法初始化 3D 渲染器：{self._real_view_error or '未知错误'}"
        renderer = self._real_renderer
        preview = getattr(renderer, "static_property_preview", None)
        if preview is None:
            return False, "[分层预览] 渲染端缺少 static_property_preview"
        was_visible = False
        if hasattr(preview, "is_current_property_layer"):
            try:
                was_visible = bool(preview.is_current_property_layer(
                    property_key, axis, layer, index_base=1))
            except Exception:
                was_visible = False
        self._enter_preview_mode()
        try:
            preview.render_property_layer(
                sim_data,
                property_key=property_key,
                axis=axis,
                layer_index=layer,
                index_base=1,
                render_now=True,
            )
        except Exception as exc:
            return False, f"[分层预览] {label} {axis.upper()}={layer} 预览失败：{exc}"
        is_visible = False
        if hasattr(preview, "is_current_property_layer"):
            try:
                is_visible = bool(preview.is_current_property_layer(
                    property_key, axis, layer, index_base=1))
            except Exception:
                is_visible = False
        self.update()
        if was_visible and not is_visible:
            return True, f"[分层预览] 已隐藏 {label} {axis.upper()}={layer}"
        if is_visible:
            return True, f"[分层预览] 已显示 {label} {axis.upper()}={layer}"
        return False, f"[分层预览] 没有可显示的 {label} {axis.upper()}={layer} 数据"

    def set_layer_state(self, layer_key, enabled):
        if layer_key in self.layers:
            self.layers[layer_key] = bool(enabled)
            if self.simulation_data is not None and self._real_renderer is not None:
                self._apply_real_layer_state(layer_key, enabled)
            self.update()

    def render_property_field(self, property_key):
        if property_key not in DISPLAY_KEY_TO_PROPERTY:
            return False, f"[属性场] 不支持的属性：{property_key}"
        self._slice_state = None
        self._threshold_state = None
        self.display_key = property_key
        self._set_full_render_context(property_key)
        if self.simulation_data is None:
            self.update()
            return False, "[属性场] 当前 3D 窗口没有可用模拟结果"
        if not self._ensure_real_view():
            return False, f"[属性场] 无法初始化 3D 渲染器：{self._real_view_error or '未知错误'}"
        self._render_real_result()
        self.update()
        return True, f"[属性场] 已显示 {DISPLAY_KEY_LABELS.get(property_key, property_key)}"

    def handle_tool_request(self, command, export_path=None, export_scale=1.0):
        command = str(command or "").strip()
        if not command:
            return False, ""
        result_required = {
            "fit_view",
            "coordinate_axes_toggle",
            "measure_toggle",
            "pick_toggle",
            "magnify_toggle",
            "camera_lock_toggle",
            "export_graphic",
        }
        if self.simulation_data is None and (
                command in result_required or command.startswith("view_")):
            return False, self._no_simulation_result_message(
                self._tool_message_label(command))
        if not self._ensure_real_view():
            return False, f"[工具] 无法初始化 3D 渲染器：{self._real_view_error or '未知错误'}"

        if command == "fit_view":
            return self.reset_camera_view()
        if command == "coordinate_axes_toggle":
            return self.toggle_coordinate_axes()
        if command == "measure_toggle":
            return self.toggle_measure()
        if command == "pick_toggle":
            return self.toggle_cell_picking()
        if command == "magnify_toggle":
            return self.toggle_2d_magnify()
        if command == "camera_lock_toggle":
            return self.toggle_camera_direction_lock()
        if command == "export_graphic":
            return self.export_graphic(export_path, export_scale)
        if command.startswith("view_"):
            return self.set_camera_view(command.replace("view_", "", 1))
        return False, f"[工具] 暂不支持的 3D 工具：{command}"

    def _tool_message_label(self, command):
        if command == "measure_toggle":
            return "测距"
        if command == "pick_toggle":
            return "拾取"
        if command == "magnify_toggle":
            return "Magnify"
        if command == "coordinate_axes_toggle":
            return "坐标轴"
        if command == "camera_lock_toggle" or command.startswith("view_"):
            return "视图"
        if command == "export_graphic":
            return "截图"
        return "工具"

    def toggle_measure(self):
        renderer = self._real_renderer
        if self.simulation_data is None:
            return False, self._no_simulation_result_message("测距")
        if renderer is None:
            return False, "[测距] 当前没有可用 3D 渲染器"
        if self.interaction_mode == "measure":
            self._disable_measure(clear_line=True)
            self.interaction_mode = "normal"
            return True, "[测距] 已关闭并清除当前测距线"
        if not hasattr(renderer, "enable_petrel_distance_measure"):
            return False, "[测距] 渲染端缺少 enable_petrel_distance_measure"
        self._set_interaction_mode("measure")
        try:
            renderer.enable_petrel_distance_measure()
        except Exception as exc:
            self.interaction_mode = "normal"
            return False, f"[测距] 开启失败：{exc}"
        return True, "[测距] 已开启：点击模型选择起点和终点"

    def _disable_measure(self, clear_line=False):
        renderer = self._real_renderer
        if renderer is None or not hasattr(renderer, "disable_petrel_distance_measure"):
            return
        cache = getattr(renderer, "cache", {}) or {}
        if not cache.get("measure_enabled") and not cache.get("measure_observer_ids"):
            return
        try:
            renderer.disable_petrel_distance_measure(clear_line=clear_line)
        except Exception:
            pass

    def toggle_cell_picking(self):
        renderer = self._real_renderer
        sim_data = self.simulation_data
        if renderer is None or sim_data is None:
            return False, "[拾取] 当前 3D 窗口没有可用模拟结果"
        if self.interaction_mode == "pick":
            self._disable_cell_picking(clear_highlight=True)
            self.interaction_mode = "normal"
            return True, "[拾取] 已关闭并清除当前高亮"
        if not hasattr(renderer, "enable_cell_info_picking"):
            return False, "[拾取] 渲染端缺少 enable_cell_info_picking"
        self._set_interaction_mode("pick")
        axis = self.current_render_context.get("axis")
        layer_index = self.current_render_context.get("layer_index")
        if self.current_render_context.get("mode") != "layer":
            axis = None
            layer_index = None
        try:
            renderer.enable_cell_info_picking(
                sim_data,
                property_name=self._current_pick_property(),
                axis=axis,
                layer_index=layer_index,
            )
        except Exception as exc:
            self.interaction_mode = "normal"
            return False, f"[拾取] 开启失败：{exc}"
        scope = "整体场" if axis is None else f"{str(axis).upper()}={layer_index}"
        return True, f"[拾取] 已开启：{self._current_pick_property()} / {scope}"

    def _disable_cell_picking(self, clear_highlight=False):
        renderer = self._real_renderer
        if renderer is None or not hasattr(renderer, "disable_cell_info_picking"):
            return
        cache = getattr(renderer, "cache", {}) or {}
        if not cache.get("cell_pick_enabled") and cache.get("cell_pick_observer_id") is None:
            return
        try:
            renderer.disable_cell_info_picking(clear_highlight=clear_highlight)
        except Exception:
            pass

    def toggle_2d_magnify(self):
        renderer = self._real_renderer
        sim_data = self.simulation_data
        if renderer is None or sim_data is None:
            return False, "[Magnify] 当前 3D 窗口没有可用模拟结果"
        if self.interaction_mode == "magnify":
            self._deactivate_magnify(render=True)
            self.interaction_mode = "normal"
            return True, "[Magnify] 已退出"
        if not hasattr(renderer, "activate_2d_magnify"):
            return False, "[Magnify] 渲染端缺少 activate_2d_magnify"
        self._set_interaction_mode("magnify")
        try:
            bounds = renderer.activate_2d_magnify(sim_data)
        except Exception as exc:
            self._deactivate_magnify(render=False)
            self.interaction_mode = "normal"
            return False, f"[Magnify] 开启失败：{exc}"
        if not bounds:
            self._deactivate_magnify(render=False)
            self.interaction_mode = "normal"
            return False, "[Magnify] 请先切换到俯视图/XY 正交视图，再拖拽框选放大"
        if self._real_view is not None and hasattr(self._real_view, "install_selection_interaction"):
            self._real_view.install_selection_interaction(
                self._begin_magnify_drag,
                self._update_magnify_drag,
                self._finish_magnify_drag,
            )
            if hasattr(self._real_view, "set_cross_cursor"):
                self._real_view.set_cross_cursor(True)
        return True, "[Magnify] 已开启：在 XY 俯视图中左键拖拽框选放大"

    def _deactivate_magnify(self, render=True):
        if self._real_view is not None:
            if hasattr(self._real_view, "uninstall_selection_interaction"):
                self._real_view.uninstall_selection_interaction()
            if hasattr(self._real_view, "set_cross_cursor"):
                self._real_view.set_cross_cursor(False)
        renderer = self._real_renderer
        if renderer is not None and hasattr(renderer, "deactivate_2d_magnify"):
            cache = getattr(renderer, "cache", {}) or {}
            if not cache.get("magnify_2d_active") and not cache.get("magnify_2d_dragging"):
                return
            try:
                renderer.deactivate_2d_magnify(render=render)
            except Exception:
                pass

    def _magnify_event_position(self):
        if self._real_view is None or not hasattr(self._real_view, "get_mouse_event_position"):
            return None
        try:
            return self._real_view.get_mouse_event_position()
        except Exception:
            return None

    def _begin_magnify_drag(self):
        renderer = self._real_renderer
        pos = self._magnify_event_position()
        if renderer is None or pos is None or not hasattr(renderer, "begin_2d_magnify_drag"):
            return
        renderer.begin_2d_magnify_drag(pos[0], pos[1])

    def _update_magnify_drag(self):
        renderer = self._real_renderer
        pos = self._magnify_event_position()
        if renderer is None or pos is None or not hasattr(renderer, "update_2d_magnify_drag"):
            return
        renderer.update_2d_magnify_drag(pos[0], pos[1])

    def _finish_magnify_drag(self):
        renderer = self._real_renderer
        pos = self._magnify_event_position()
        if renderer is None or pos is None or not hasattr(renderer, "finish_2d_magnify_drag"):
            self._deactivate_magnify(render=True)
            self.interaction_mode = "normal"
            return
        renderer.finish_2d_magnify_drag(pos[0], pos[1])
        self._deactivate_magnify(render=False)
        self.interaction_mode = "normal"

    def reset_camera_view(self):
        renderer = self._real_renderer
        if renderer is None:
            return False, "[视图] 当前没有可用 3D 渲染器"
        try:
            renderer.plotter.reset_camera(render=False)
            renderer.plotter.reset_camera_clipping_range()
            renderer.render_now()
        except AttributeError:
            try:
                renderer.plotter.reset_camera()
                renderer.render_now()
            except Exception as exc:
                return False, f"[视图] 适配全部失败：{exc}"
        except Exception as exc:
            return False, f"[视图] 适配全部失败：{exc}"
        return True, "[视图] 已适配全部"

    def toggle_coordinate_axes(self):
        renderer = self._real_renderer
        sim_data = self.simulation_data
        if renderer is None or sim_data is None:
            return False, "[坐标轴] 当前 3D 窗口没有可用模拟结果"
        if self.coordinate_axes_visible:
            if hasattr(renderer, "hide_coordinate_axes"):
                renderer.hide_coordinate_axes()
            elif hasattr(renderer, "disable_camera_aware_coordinate_axes"):
                renderer.disable_camera_aware_coordinate_axes(clear_axes=False)
            self.coordinate_axes_visible = False
            return True, "[坐标轴] 已隐藏动态坐标轴"
        if not hasattr(renderer, "show_coordinate_axes_for_model"):
            return False, "[坐标轴] 渲染端缺少 show_coordinate_axes_for_model"
        ok = bool(renderer.show_coordinate_axes_for_model(sim_data))
        self.coordinate_axes_visible = ok
        if ok:
            return True, "[坐标轴] 已显示动态坐标轴"
        return False, "[坐标轴] 显示失败，当前模型缺少有效角点网格数据"

    def set_camera_view(self, view_name):
        renderer = self._real_renderer
        if renderer is None:
            return False, "[视图] 当前没有可用 3D 渲染器"
        method_name = f"view_{view_name}"
        method = getattr(renderer, method_name, None)
        if method is None:
            return False, f"[视图] 渲染端缺少函数：{method_name}"
        try:
            method()
        except Exception as exc:
            return False, f"[视图] 切换失败：{exc}"
        names = {
            "front": "前视图",
            "back": "后视图",
            "left": "左视图",
            "right": "右视图",
            "top": "俯视图",
            "bottom": "仰视图",
        }
        return True, f"[视图] 已切换到{names.get(view_name, view_name)}"

    def toggle_camera_direction_lock(self):
        renderer = self._real_renderer
        if renderer is None:
            return False, "[视图] 当前没有可用 3D 渲染器"
        if not hasattr(renderer, "toggle_camera_direction_lock"):
            return False, "[视图] 渲染端缺少 toggle_camera_direction_lock"
        try:
            renderer.toggle_camera_direction_lock()
            self.camera_direction_locked = bool(
                getattr(renderer, "camera_direction_locked", not self.camera_direction_locked)
            )
        except Exception as exc:
            return False, f"[视图] 视角方向锁定切换失败：{exc}"
        state_text = "锁定" if self.camera_direction_locked else "解锁"
        return True, f"[视图] 已{state_text}视角方向"

    def export_graphic(self, filepath, scale=1.0):
        renderer = self._real_renderer
        if self.simulation_data is None:
            return False, self._no_simulation_result_message("截图")
        if renderer is None:
            return False, "[截图] 当前没有可用 3D 渲染器"
        if not filepath:
            return False, "[截图] 已取消导出"
        if not hasattr(renderer, "export_graphic"):
            return False, "[截图] 渲染端缺少 export_graphic"
        try:
            saved_path = renderer.export_graphic(filepath=filepath, scale=scale)
        except Exception as exc:
            return False, f"[截图] 导出失败：{exc}"
        if saved_path:
            return True, f"[截图] 已导出：{saved_path}"
        return False, "[截图] 导出失败"

    def apply_threshold_filter(self, min_text="", max_text=""):
        renderer = self._real_renderer
        sim_data = self.simulation_data
        if renderer is None or sim_data is None:
            return False, "[阈值] 当前 3D 窗口没有可用模拟结果"
        if not hasattr(renderer, "render_threshold_property_field"):
            return False, "[阈值] 渲染端缺少 render_threshold_property_field"
        min_value, min_error = self._parse_threshold_value(min_text, "最小值")
        if min_error:
            return False, min_error
        max_value, max_error = self._parse_threshold_value(max_text, "最大值")
        if max_error:
            return False, max_error
        if min_value is None and max_value is None:
            return False, "[阈值] 请至少填写最小值或最大值"
        if min_value is not None and max_value is not None and min_value > max_value:
            return False, "[阈值] 最小值不能大于最大值"
        self._reset_fence_section_for_context_change(render=False)
        if self.interaction_mode != "normal":
            self._set_interaction_mode("normal")
        display_key = self.current_render_context.get("display_key", self.display_key)
        self._slice_state = None
        self._set_full_render_context(display_key)
        self.display_key = display_key
        self._threshold_state = {
            "display_key": display_key,
            "min": min_value,
            "max": max_value,
        }
        property_name = self._current_pick_property()
        try:
            renderer.clear_cache()
            renderer.render_threshold_property_field(
                sim_data,
                property_name=property_name,
                min_value=min_value,
                max_value=max_value,
            )
        except Exception as exc:
            self._threshold_state = None
            self._render_real_result()
            return False, f"[阈值] 应用失败：{exc}"
        self._rendered_display_key = (
            f"threshold:{self.current_render_context.get('display_key')}:"
            f"{min_value}:{max_value}"
        )
        return True, (
            f"[阈值] 已过滤 {self._current_display_label()} "
            f"min={self._format_threshold_value(min_value)} "
            f"max={self._format_threshold_value(max_value)}"
        )

    def clear_threshold_filter(self):
        self._threshold_state = None
        renderer = self._real_renderer
        if renderer is None:
            return False, "[阈值] 当前没有可用 3D 渲染器"
        if hasattr(renderer, "hide_threshold_property_field"):
            try:
                renderer.hide_threshold_property_field()
            except Exception as exc:
                return False, f"[阈值] 清除失败：{exc}"
        if self.simulation_data is not None:
            self._render_real_result()
        return True, "[阈值] 已清除阈值过滤"

    def _parse_threshold_value(self, text, label):
        text = str(text or "").strip()
        if not text:
            return None, ""
        try:
            value = float(text)
        except ValueError:
            return None, f"[阈值] {label}必须是数字"
        if not math.isfinite(value):
            return None, f"[阈值] {label}必须是有限数字"
        return value, ""

    def _format_threshold_value(self, value):
        if value is None:
            return "不限"
        return f"{value:.6g}"

    def prepare_time_playback(self, step_index=0):
        sim_data = self.simulation_data
        if sim_data is None:
            return False, self._no_simulation_result_message("时间步")
        property_name = self.current_render_context.get("property_name", "pressure")
        if getattr(sim_data, "time_steps", None) is None:
            return False, "[时间步] 当前结果缺少 time_steps，无法播放动态结果"
        steps_attr = self._time_playback_steps_attr(property_name)
        if not steps_attr or getattr(sim_data, steps_attr, None) is None:
            return False, f"[时间步] 当前结果缺少 {self._current_display_label()} 的时间步数据"
        if not self._ensure_real_view():
            return False, f"[时间步] 无法初始化 3D 渲染器：{self._real_view_error or '未知错误'}"
        renderer = self._real_renderer
        if not hasattr(renderer, "prepare_corner_time_playback"):
            return False, "[时间步] 渲染端缺少 prepare_corner_time_playback"
        self._reset_fence_section_for_context_change(render=False)
        if self.interaction_mode != "normal":
            self._set_interaction_mode("normal")
        mode = self.current_render_context.get("mode", "full")
        axis = self.current_render_context.get("axis")
        layer_index = self.current_render_context.get("layer_index")
        try:
            if mode == "layer" and axis is not None and layer_index is not None:
                info = renderer.prepare_corner_time_playback_by_layer(
                    sim_data,
                    property_name=property_name,
                    axis=axis,
                    layer_index=int(layer_index),
                    start_index=int(step_index),
                    show_edges=False,
                )
            else:
                info = renderer.prepare_corner_time_playback(
                    sim_data,
                    property_name=property_name,
                    start_index=int(step_index),
                    show_edges=False,
                )
        except Exception as exc:
            return False, f"[时间步] 准备失败：{exc}"
        if not info or not info.get("ready"):
            return False, "[时间步] 准备失败，渲染端未返回可用播放状态"
        self._rendered_display_key = (
            f"time:{self.current_render_context.get('display_key')}:"
            f"{info.get('current_index', 0)}"
        )
        return True, self._format_time_playback_info("[时间步] 已准备", info)

    def show_time_step(self, step_index):
        renderer = self._real_renderer
        if renderer is None or not hasattr(renderer, "show_corner_time_step"):
            return False, "[时间步] 当前没有可用时间步渲染器"
        try:
            info = renderer.show_corner_time_step(int(step_index))
        except Exception as exc:
            return False, f"[时间步] 切换失败：{exc}"
        if not info:
            return False, "[时间步] 尚未准备播放，请先点击准备"
        self._rendered_display_key = (
            f"time:{self.current_render_context.get('display_key')}:"
            f"{info.get('index', 0)}"
        )
        return True, self._format_time_step_info("[时间步] 已显示", info)

    def show_next_time_step(self):
        renderer = self._real_renderer
        if renderer is None or not hasattr(renderer, "show_next_corner_time_step"):
            return False, "[时间步] 当前没有可用时间步渲染器"
        try:
            info = renderer.show_next_corner_time_step(loop=True)
        except Exception as exc:
            return False, f"[时间步] 下一帧失败：{exc}"
        if not info:
            return False, "[时间步] 尚未准备播放，请先点击准备"
        self._rendered_display_key = (
            f"time:{self.current_render_context.get('display_key')}:"
            f"{info.get('index', 0)}"
        )
        return True, self._format_time_step_info("[时间步] 已显示", info)

    def show_previous_time_step(self):
        renderer = self._real_renderer
        if renderer is None or not hasattr(renderer, "show_previous_corner_time_step"):
            return False, "[时间步] 当前没有可用时间步渲染器"
        try:
            info = renderer.show_previous_corner_time_step(loop=True)
        except Exception as exc:
            return False, f"[时间步] 上一帧失败：{exc}"
        if not info:
            return False, "[时间步] 尚未准备播放，请先点击准备"
        self._rendered_display_key = (
            f"time:{self.current_render_context.get('display_key')}:"
            f"{info.get('index', 0)}"
        )
        return True, self._format_time_step_info("[时间步] 已显示", info)

    def stop_time_playback(self):
        renderer = self._real_renderer
        if renderer is None:
            return False, "[时间步] 当前没有可用 3D 渲染器"
        if not hasattr(renderer, "clear_corner_time_playback"):
            return False, "[时间步] 渲染端缺少 clear_corner_time_playback"
        try:
            renderer.clear_corner_time_playback(
                sim_data=self.simulation_data,
                restore_final_field=False,
            )
        except Exception as exc:
            return False, f"[时间步] 停止失败：{exc}"
        if self.simulation_data is not None:
            self._render_real_result()
        return True, "[时间步] 已停止并恢复静态场"

    def time_playback_info(self):
        renderer = self._real_renderer
        if renderer is None or not hasattr(renderer, "get_time_playback_info"):
            return {}
        try:
            return renderer.get_time_playback_info() or {}
        except Exception:
            return {}

    def _time_playback_steps_attr(self, property_name):
        return {
            "pressure": "pressure_steps",
            "sw": "sw_steps",
            "porosity": "porosity_steps",
            "permeability_x": "permeability_x_steps",
            "permeability_y": "permeability_y_steps",
            "permeability_z": "permeability_z_steps",
        }.get(str(property_name or "").strip())

    def _format_time_playback_info(self, prefix, info):
        step_count = int(info.get("step_count") or 0)
        current_index = int(info.get("current_index") or 0)
        current_time = self._format_time_value(info.get("current_time"))
        scope = self._format_time_scope(info)
        return (
            f"{prefix} {self._current_display_label()} {scope} "
            f"step={current_index}/{max(step_count - 1, 0)} "
            f"time={current_time}，单元={int(info.get('visible_cell_count') or 0)}"
        )

    def _format_time_step_info(self, prefix, info):
        index = int(info.get("index") or 0)
        current_time = self._format_time_value(info.get("time"))
        value_min = self._format_threshold_value(info.get("value_min"))
        value_max = self._format_threshold_value(info.get("value_max"))
        return (
            f"{prefix} {self._current_display_label()} "
            f"step={index} time={current_time} "
            f"value=[{value_min}, {value_max}]"
        )

    def _format_time_scope(self, info):
        if info.get("mode") == "layer":
            axis = str(info.get("axis") or "").upper()
            layer_index = info.get("layer_index")
            return f"{axis}={layer_index}"
        return "整体场"

    def _format_time_value(self, value):
        if value is None:
            return "未知"
        try:
            return f"{float(value):.6g}"
        except (TypeError, ValueError):
            return str(value)

    def export_ui_state(self):
        slice_state = None
        if self._slice_state is not None:
            property_key, axis, layer = self._slice_state
            slice_state = {
                "property_key": property_key,
                "axis": axis,
                "layer": int(layer),
            }
        return {
            "context_title": self.context_title,
            "context_detail": self.context_detail,
            "display_key": self.display_key,
            "render_context": dict(self.current_render_context or {}),
            "slice_state": slice_state,
            "threshold_state": dict(self._threshold_state or {}),
            "camera_state": self._export_camera_state(),
            "coordinate_axes_visible": bool(self.coordinate_axes_visible),
            "camera_direction_locked": bool(self.camera_direction_locked),
            "fence_section_property": self.fence_section_property,
            "layers": dict(self.layers),
            "geometry_preview_style": (
                self.export_geometry_preview_style_state()
            ),
        }

    def restore_ui_state(self, state):
        if not isinstance(state, dict):
            return
        self._reset_fence_section_for_context_change(render=False)
        fence_property = state.get(
            "fence_section_property",
            self.fence_section_property,
        )
        self.set_fence_section_property_preference(fence_property)
        self.context_title = state.get("context_title") or self.context_title
        self.context_detail = state.get("context_detail") or self.context_detail
        display_key = state.get("display_key") or self.display_key
        if display_key in DISPLAY_KEY_TO_PROPERTY:
            self.display_key = display_key
            self._set_full_render_context(display_key)
        render_context = self._normalize_render_context(state.get("render_context"))
        if render_context is not None:
            self.current_render_context = render_context
            self.display_key = render_context.get("display_key", self.display_key)
        self._slice_state = self._normalize_slice_state(state.get("slice_state"))
        self._threshold_state = self._normalize_threshold_state(state.get("threshold_state"))
        self._camera_state = self._normalize_camera_state(state.get("camera_state"))
        self.coordinate_axes_visible = bool(state.get("coordinate_axes_visible", False))
        self.camera_direction_locked = bool(state.get("camera_direction_locked", False))
        if "geometry_preview_style" in state:
            style_ok, style_message = (
                self.restore_geometry_preview_style_state(
                    state.get("geometry_preview_style")
                )
            )
            if not style_ok:
                self.interaction_message.emit(style_message)
        layers = state.get("layers")
        if isinstance(layers, dict):
            for layer_key, enabled in layers.items():
                if layer_key in self.layers:
                    self.layers[layer_key] = bool(enabled)
        if self.simulation_data is not None and self._ensure_real_view():
            self._restore_saved_visual_state()
        self.update()

    def _normalize_render_context(self, state):
        if not isinstance(state, dict):
            return None
        display_key = state.get("display_key")
        if display_key not in DISPLAY_KEY_TO_PROPERTY:
            return None
        mode = state.get("mode") or "full"
        axis = state.get("axis")
        layer_index = state.get("layer_index")
        if mode == "layer" and axis is not None and layer_index is not None:
            try:
                return self._make_render_context(
                    display_key,
                    mode="layer",
                    axis=str(axis).lower(),
                    layer_index=int(layer_index),
                )
            except (TypeError, ValueError):
                return self._make_render_context(display_key)
        return self._make_render_context(display_key)

    def _normalize_slice_state(self, state):
        if not isinstance(state, dict):
            return None
        property_key = state.get("property_key")
        axis = str(state.get("axis") or "").lower()
        if property_key not in DISPLAY_KEY_TO_PROPERTY or axis not in {"i", "j", "k"}:
            return None
        try:
            layer = int(state.get("layer", 0))
        except (TypeError, ValueError):
            layer = 0
        return (property_key, axis, layer)

    def _normalize_threshold_state(self, state):
        if not isinstance(state, dict):
            return None
        display_key = state.get("display_key") or self.display_key
        if display_key not in DISPLAY_KEY_TO_PROPERTY:
            return None
        min_value = self._coerce_optional_float(state.get("min"))
        max_value = self._coerce_optional_float(state.get("max"))
        if min_value is None and max_value is None:
            return None
        return {"display_key": display_key, "min": min_value, "max": max_value}

    def _coerce_optional_float(self, value):
        if value is None or value == "":
            return None
        try:
            result = float(value)
        except (TypeError, ValueError):
            return None
        if not math.isfinite(result):
            return None
        return result

    def _export_camera_state(self):
        renderer = self._real_renderer
        plotter = getattr(renderer, "plotter", None) if renderer is not None else None
        if plotter is None:
            return dict(self._camera_state or {})
        try:
            camera_position = getattr(plotter, "camera_position", None)
        except Exception:
            camera_position = None
        state = self._normalize_camera_state({"camera_position": camera_position})
        if not state:
            return dict(self._camera_state or {})
        camera = getattr(plotter, "camera", None)
        if camera is not None:
            for attr_name, getter_name, state_key in [
                ("parallel_projection", "GetParallelProjection", "parallel_projection"),
                ("parallel_scale", "GetParallelScale", "parallel_scale"),
                ("view_angle", "GetViewAngle", "view_angle"),
            ]:
                getter = getattr(camera, getter_name, None)
                if getter is None:
                    continue
                try:
                    value = getter()
                except Exception:
                    continue
                state[state_key] = bool(value) if attr_name == "parallel_projection" else value
        return state

    def _normalize_camera_state(self, state):
        if not isinstance(state, dict):
            return None
        camera_position = state.get("camera_position")
        if not isinstance(camera_position, (list, tuple)) or len(camera_position) != 3:
            return None
        normalized = []
        for point in camera_position:
            if not isinstance(point, (list, tuple)) or len(point) != 3:
                return None
            try:
                normalized.append([float(point[0]), float(point[1]), float(point[2])])
            except (TypeError, ValueError):
                return None
        result = {"camera_position": normalized}
        for key in ("parallel_projection", "parallel_scale", "view_angle"):
            if key in state:
                result[key] = state[key]
        return result

    def _apply_saved_camera_state(self):
        if not self._camera_state:
            return
        renderer = self._real_renderer
        plotter = getattr(renderer, "plotter", None) if renderer is not None else None
        if plotter is None:
            return
        try:
            plotter.camera_position = [tuple(point) for point in self._camera_state["camera_position"]]
            camera = getattr(plotter, "camera", None)
            if camera is not None:
                if "parallel_projection" in self._camera_state:
                    setter = getattr(camera, "SetParallelProjection", None)
                    if setter is not None:
                        setter(bool(self._camera_state["parallel_projection"]))
                if "parallel_scale" in self._camera_state:
                    setter = getattr(camera, "SetParallelScale", None)
                    if setter is not None:
                        setter(float(self._camera_state["parallel_scale"]))
                if "view_angle" in self._camera_state:
                    setter = getattr(camera, "SetViewAngle", None)
                    if setter is not None:
                        setter(float(self._camera_state["view_angle"]))
            if hasattr(plotter, "reset_camera_clipping_range"):
                plotter.reset_camera_clipping_range()
            if hasattr(plotter, "render"):
                plotter.render()
            self._camera_state = None
        except Exception:
            pass

    def _restore_saved_visual_state(self):
        if self._threshold_state:
            display_key = self._threshold_state.get("display_key") or self.display_key
            if display_key in DISPLAY_KEY_TO_PROPERTY:
                self.display_key = display_key
                self._set_full_render_context(display_key)
            min_value = self._threshold_state.get("min")
            max_value = self._threshold_state.get("max")
            ok, _ = self.apply_threshold_filter(
                "" if min_value is None else str(min_value),
                "" if max_value is None else str(max_value),
            )
            if ok:
                self._apply_saved_camera_state()
                return
        if self._slice_state is not None:
            property_key, axis, layer = self._slice_state
            ok, _ = self.render_property_slice(property_key, axis, layer)
            if ok:
                self._apply_saved_camera_state()
                return
        self._render_real_result()
        self._apply_saved_camera_state()

    def _ensure_real_view(self):
        if self._real_renderer is not None:
            if self._real_view is not None and not self._real_view.isVisible():
                self._real_view.show()
            return True
        if self._real_view_error:
            return False
        try:
            from visual.pyvista_renderer import PyVistaRenderer
            from visual.pyvista_view import PyVistaView
        except Exception as exc:
            self._real_view_error = str(exc)
            return False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._real_view = PyVistaView(self)
        layout.addWidget(self._real_view)
        self._real_renderer = PyVistaRenderer(self._real_view)
        if hasattr(self._real_view, "interaction_message"):
            self._real_view.interaction_message.connect(
                self._handle_renderer_interaction_message)
        style_ok, style_message = self._apply_cached_geometry_preview_style(
            render_now=False)
        if not style_ok:
            self.interaction_message.emit(style_message)
        self._real_view.show()
        return True

    def _render_real_result(self):
        renderer = self._real_renderer
        sim_data = self.simulation_data
        if renderer is None or sim_data is None:
            return
        self._reset_fence_section_for_context_change(render=False)
        if self.interaction_mode != "normal":
            self._set_interaction_mode("normal")
        renderer.clear_cache()
        self._preview_mode_active = False
        self._rendered_display_key = self.display_key
        if (
                getattr(sim_data, "corner_point_grid", None) is not None
                and hasattr(renderer, "render_corner_point_grid")):
            renderer.render_corner_point_grid(sim_data)
        rendered_field = False
        if getattr(sim_data, "cell_geometry_with_pressure", None) is not None:
            rendered_field = self._render_corner_property_field(renderer, sim_data)
        if (
                not rendered_field
                and getattr(sim_data, "pressure_field", None)
                and hasattr(renderer, "render_mode3_smooth_pressure")):
            renderer.render_mode3_smooth_pressure(sim_data)
        if getattr(sim_data, "corner_lgr_parent_grid_geometry", None) is not None or (
                getattr(sim_data, "corner_lgr_refined_grid_geometry", None) is not None):
            if hasattr(renderer, "render_corner_lgr_grid"):
                renderer.render_corner_lgr_grid(sim_data)
        if getattr(sim_data, "fractures", None):
            if hasattr(renderer, "render_corner_fractures"):
                renderer.render_corner_fractures(sim_data)
            elif hasattr(renderer, "render_fractures"):
                renderer.render_fractures(sim_data)
        if getattr(sim_data, "wells", None) and hasattr(renderer, "render_wells"):
            renderer.render_wells(sim_data)
        for layer_key, enabled in self.layers.items():
            self._apply_real_layer_state(layer_key, enabled)
        if self.coordinate_axes_visible and hasattr(renderer, "show_coordinate_axes_for_model"):
            self.coordinate_axes_visible = bool(renderer.show_coordinate_axes_for_model(sim_data))

    def render_property_slice(self, property_key, axis, layer):
        self._slice_state = (property_key, axis, int(layer))
        self._threshold_state = None
        self.display_key = property_key
        if not self._ensure_real_view():
            return False, f"[切片] 无法初始化 3D 渲染器：{self._real_view_error or '未知错误'}"
        ok, message = self._render_slice_result()
        if ok:
            self._set_layer_render_context(property_key, axis, layer)
        self.update()
        return ok, message

    def reset_property_slice(self):
        self._slice_state = None
        self._set_full_render_context(self.display_key)
        if not self._ensure_real_view():
            return False, f"[切片] 无法初始化 3D 渲染器：{self._real_view_error or '未知错误'}"
        self._render_real_result()
        self.update()
        return True, "[切片] 已恢复整体场显示"

    def _render_slice_result(self):
        renderer = self._real_renderer
        sim_data = self.simulation_data
        if renderer is None or sim_data is None or self._slice_state is None:
            return False, "[切片] 当前 3D 窗口没有可用模拟结果"
        property_key, axis, layer = self._slice_state
        valid, reason = self._validate_slice_request(sim_data, property_key, axis, layer)
        if not valid:
            return False, reason
        self._reset_fence_section_for_context_change(render=False)
        if self.interaction_mode != "normal":
            self._set_interaction_mode("normal")
        renderer.clear_cache()
        method_name = self._slice_method_name(property_key, axis)
        method = getattr(renderer, method_name, None)
        if method is None:
            self._render_real_result()
            return False, f"[切片] 渲染端缺少函数：{method_name}"
        arg_name = f"{axis}_layer"
        try:
            method(sim_data, **{arg_name: int(layer)})
        except TypeError as exc:
            try:
                method(sim_data, int(layer))
            except Exception as fallback_exc:
                self._render_real_result()
                return False, f"[切片] 渲染失败：{fallback_exc}"
        except Exception as exc:
            self._render_real_result()
            return False, f"[切片] 渲染失败：{exc}"
        self._rendered_display_key = f"{property_key}:{axis}:{int(layer)}"
        for layer_key, enabled in self.layers.items():
            if layer_key in {"grid", "grid_refinement"}:
                continue
            self._apply_real_layer_state(layer_key, enabled)
        if self.coordinate_axes_visible and hasattr(renderer, "show_coordinate_axes_for_model"):
            self.coordinate_axes_visible = bool(renderer.show_coordinate_axes_for_model(sim_data))
        return True, f"[切片] 已显示 {self._slice_property_label(property_key)} {axis.upper()}={int(layer)}"

    def _validate_slice_request(self, sim_data, property_key, axis, layer):
        if axis not in {"i", "j", "k"}:
            return False, f"[切片] 不支持的方向：{axis}"
        grid_info = getattr(sim_data, "grid_info", None) or {}
        dimension_key = {"i": "nx", "j": "ny", "k": "nz"}[axis]
        max_count = int(grid_info.get(dimension_key) or 0)
        if max_count <= 0:
            return False, f"[切片] 缺少网格维度 {dimension_key}，无法切片"
        if layer < 0 or layer >= max_count:
            return False, f"[切片] 层号越界：{axis.upper()}={layer}，有效范围 0-{max_count - 1}"
        if getattr(sim_data, "corner_point_grid", None) is None:
            return False, "[切片] 缺少 Corner Point Grid 数据"
        if getattr(sim_data, "cell_geometry_with_pressure", None) is None:
            return False, "[切片] 缺少 cell_geometry_with_pressure 数据，无法显示属性切片"
        return True, ""

    def _slice_property_label(self, property_key):
        return {
            "pressure_field": "Pressure",
            "water_saturation_field": "Sw",
            "porosity_field": "Phi",
            "permeability_x_field": "Kx",
            "permeability_y_field": "Ky",
            "permeability_z_field": "Kz",
            "permeability_field": "Kx",
        }.get(property_key, property_key)

    def _slice_method_name(self, property_key, axis):
        property_prefix = {
            "pressure_field": "render_corner_grid_by_layer",
            "water_saturation_field": "render_corner_sw_by_layer",
            "porosity_field": "render_corner_phi_by_layer",
            "permeability_x_field": "render_corner_kx_by_layer",
            "permeability_y_field": "render_corner_ky_by_layer",
            "permeability_z_field": "render_corner_kz_by_layer",
            "permeability_field": "render_corner_kx_by_layer",
        }.get(property_key, "render_corner_grid_by_layer")
        return f"{property_prefix}_{axis}"

    def _render_corner_property_field(self, renderer, sim_data):
        method_name = {
            "pressure_field": "render_corner_pressure_field",
            "water_saturation_field": "render_corner_sw_field",
            "porosity_field": "render_corner_phi_field",
            "permeability_x_field": "render_corner_kx_field",
            "permeability_y_field": "render_corner_ky_field",
            "permeability_z_field": "render_corner_kz_field",
            "permeability_field": "render_corner_kx_field",
        }.get(self.display_key, "render_corner_pressure_field")
        method = getattr(renderer, method_name, None)
        if method is None:
            fallback = getattr(renderer, "render_corner_pressure_field", None)
            if fallback is None:
                return False
            fallback(sim_data)
            return True
        method(sim_data)
        return True

    def _apply_real_layer_state(self, layer_key, enabled):
        renderer = self._real_renderer
        sim_data = self.simulation_data
        if renderer is None or sim_data is None:
            return
        if layer_key == "grid":
            if hasattr(renderer, "toggle_grid_visibility"):
                renderer.toggle_grid_visibility(bool(enabled))
            elif hasattr(renderer, "ensure_grid_lines"):
                renderer.ensure_grid_lines(sim_data)
                renderer.toggle_grid_lines(bool(enabled))
        elif layer_key == "grid_refinement":
            if hasattr(renderer, "toggle_corner_lgr_grid_visibility"):
                renderer.toggle_corner_lgr_grid_visibility(bool(enabled))
        elif layer_key in {"natural_fractures", "hydraulic_fractures"}:
            if hasattr(renderer, "ensure_fractures"):
                renderer.ensure_fractures(sim_data)
            fracture_type = "hydraulic" if layer_key == "hydraulic_fractures" else "natural"
            if hasattr(renderer, "toggle_fractures_visibility"):
                try:
                    renderer.toggle_fractures_visibility(bool(enabled), fracture_type)
                except TypeError:
                    renderer.toggle_fractures_visibility(bool(enabled))
            elif hasattr(renderer, "toggle_fractures"):
                try:
                    renderer.toggle_fractures(bool(enabled), fracture_type)
                except TypeError:
                    renderer.toggle_fractures(bool(enabled))
        elif layer_key == "well":
            if enabled and hasattr(renderer, "render_wells"):
                renderer.render_wells(sim_data)
            if hasattr(renderer, "toggle_wells_visibility"):
                renderer.toggle_wells_visibility(bool(enabled))
        elif layer_key == "pressure":
            if hasattr(renderer, "toggle_pressure_visibility"):
                renderer.toggle_pressure_visibility(bool(enabled))

    def paintEvent(self, event):
        if self._real_view is not None and self._real_view.isVisible():
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        if self.simulation_data is None:
            painter.fillRect(self.rect(), QColor("#e8edf2"))
            painter.end()
            return
        painter.fillRect(self.rect(), QColor("#050505"))

        style = RESULT_STYLES.get(self.display_key, RESULT_STYLES["pressure_field"])
        w, h = self.width(), self.height()
        origin = QPointF(w * 0.16, h * 0.72)
        x_vec = QPointF(w * 0.60, -h * 0.20)
        y_vec = QPointF(w * 0.24, h * 0.18)

        if self.layers["grid"]:
            self._draw_result_surface(painter, origin, x_vec, y_vec, style)

        if self.layers["grid_refinement"]:
            painter.setPen(QPen(QColor("#ffcc33"), 2))
            refined = QRectF(
                origin + QPointF(w * 0.34, -h * 0.10),
                origin + QPointF(w * 0.53, h * 0.04),
            )
            painter.drawRect(refined.normalized())

        if self.layers["natural_fractures"]:
            self._draw_fracture_swarm(painter, origin, x_vec, y_vec, QColor("#f0a000"))

        if self.layers["hydraulic_fractures"]:
            self._draw_hydraulic_fractures(painter, origin, w, h)

        if self.layers["well"]:
            self._draw_wells(painter, origin, w, h)

        self._draw_color_bar(painter, style)
        self._draw_context(painter)
        self._draw_axis_glyph(painter)
        painter.end()

    def _draw_result_surface(self, painter, origin, x_vec, y_vec, style):
        surface_color = style["surface"]
        plane = QPolygonF([origin, origin + x_vec, origin + x_vec + y_vec, origin + y_vec])
        fill_color = QColor(surface_color)
        fill_color.setAlpha(78)
        painter.setPen(Qt.NoPen)
        painter.setBrush(fill_color)
        painter.drawPolygon(plane)

        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor(surface_color).darker(130), 1))
        rows, cols = 46, 70
        for i in range(rows + 1):
            t = i / rows
            p1 = origin + y_vec * t
            painter.drawLine(p1, p1 + x_vec)
        for j in range(cols + 1):
            t = j / cols
            p1 = origin + x_vec * t
            painter.drawLine(p1, p1 + y_vec)
        painter.setPen(QPen(QColor(surface_color).lighter(135), 2))
        for band in [0.18, 0.38, 0.62]:
            painter.drawLine(
                origin + x_vec * band + y_vec * 0.04,
                origin + x_vec * (band + 0.18) + y_vec * 0.82,
            )
        self._draw_result_patches(painter, origin, x_vec, y_vec, style)

    def _draw_result_patches(self, painter, origin, x_vec, y_vec, style):
        colors = [QColor(color) for color in style["colors"]]
        patches = [
            (0.18, 0.22, 0.18, 0.20, colors[1]),
            (0.43, 0.34, 0.22, 0.18, colors[2]),
            (0.62, 0.56, 0.18, 0.22, colors[-1]),
        ]
        painter.setPen(Qt.NoPen)
        for sx, sy, sw, sh, color in patches:
            color.setAlpha(115)
            polygon = QPolygonF([
                origin + x_vec * sx + y_vec * sy,
                origin + x_vec * (sx + sw) + y_vec * sy,
                origin + x_vec * (sx + sw) + y_vec * (sy + sh),
                origin + x_vec * sx + y_vec * (sy + sh),
            ])
            painter.setBrush(color)
            painter.drawPolygon(polygon)

    def _draw_fracture_swarm(self, painter, origin, x_vec, y_vec, color):
        painter.setPen(QPen(color, 1.8))
        for offset in [0.08, 0.16, 0.24, 0.34, 0.46, 0.58]:
            start = origin + x_vec * offset + y_vec * (0.12 + offset * 0.25)
            end = origin + x_vec * (offset + 0.10) + y_vec * (0.58 + offset * 0.10)
            painter.drawLine(start, end)

    def _draw_hydraulic_fractures(self, painter, origin, w, h):
        painter.setPen(QPen(QColor("#00a8ff"), 2))
        for base_x, label in [(0.42, "HF-1"), (0.50, "HF-2"), (0.58, "HF-3")]:
            start = origin + QPointF(w * base_x, -h * 0.34)
            end = origin + QPointF(w * (base_x + 0.055), -h * 0.06)
            painter.drawLine(start, end)
            painter.setPen(QPen(QColor("#00d2ff"), 1))
            painter.drawLine(start + QPointF(-12, 20), start + QPointF(14, 44))
            painter.setPen(QPen(QColor("#00a8ff"), 2))
            painter.setFont(QFont("Arial", 8))
            painter.drawText(end + QPointF(5, 4), label)

    def _draw_wells(self, painter, origin, w, h):
        painter.setFont(QFont("Arial", 9, QFont.Bold))
        main_points = [
            origin + QPointF(w * 0.25, -h * 0.05),
            origin + QPointF(w * 0.31, -h * 0.16),
            origin + QPointF(w * 0.35, -h * 0.37),
            origin + QPointF(w * 0.38, -h * 0.56),
        ]
        painter.setPen(QPen(QColor("#e21b1b"), 3))
        painter.drawPolyline(*main_points)
        painter.setPen(QColor("#ffffff"))
        painter.drawText(main_points[-1] + QPointF(5, -3), "MHVW37520")

        for idx, x in enumerate([0.48, 0.57, 0.66], start=1):
            points = [
                origin + QPointF(w * x, -h * 0.05),
                origin + QPointF(w * (x + 0.035), -h * 0.26),
                origin + QPointF(w * (x + 0.02), -h * 0.50),
            ]
            painter.setPen(QPen(QColor("#00a8ff"), 2))
            painter.drawPolyline(*points)
            painter.setPen(QColor("#cdeeff"))
            painter.drawText(points[-1] + QPointF(5, 2), f"W-{idx}")

    def _draw_color_bar(self, painter, style):
        x, y = 18, 56
        colors = style["colors"]
        step = 110 / len(colors)
        for i, color in enumerate(colors):
            painter.fillRect(x, int(y + i * step), 38, int(step) + 1, QColor(color))
        painter.setPen(QColor("#ffffff"))
        painter.setFont(QFont("Microsoft YaHei UI", 8))
        painter.drawText(x, y - 8, f"{style['legend']} ({style['unit']})")
        for index, tick in enumerate(style["ticks"]):
            painter.drawText(x + 46, y + 8 + index * 46, tick)

    def _draw_context(self, painter):
        painter.setPen(QColor("#ffffff"))
        painter.setFont(QFont("Microsoft YaHei UI", 10, QFont.Bold))
        painter.drawText(18, 22, self.context_title)
        painter.setFont(QFont("Microsoft YaHei UI", 9))
        painter.setPen(QColor("#cfd7e6"))
        painter.drawText(18, 40, self.context_detail)

    def _draw_layer_status(self, painter):
        labels = [
            ("网格", "grid"),
            ("加密", "grid_refinement"),
            ("井", "well"),
            ("天然裂缝", "natural_fractures"),
            ("人工裂缝", "hydraulic_fractures"),
        ]
        x = self.width() - 190
        y = 42
        painter.setFont(QFont("Microsoft YaHei UI", 8))
        for index, (text, key) in enumerate(labels):
            enabled = self.layers[key]
            painter.setPen(QColor("#3ccf62") if enabled else QColor("#6a6f7a"))
            painter.drawText(x, y + index * 18, f"{'■' if enabled else '□'} {text}")

    def _draw_axis_glyph(self, painter):
        base = QPointF(self.width() - 84, self.height() - 42)
        painter.setBrush(QColor("#1ed33a"))
        painter.setPen(QPen(QColor("#0d751d"), 1))
        painter.drawPolygon(base, base + QPointF(34, -16), base + QPointF(20, -50))
        painter.setBrush(QColor("#e32424"))
        painter.drawPolygon(
            base + QPointF(30, -2),
            base + QPointF(62, -19),
            base + QPointF(52, -32),
        )


class TwoDViewport(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("twoDViewport")
        self.context_title = "当前结果：二维视图"
        self.context_detail = "二维窗口用于查看井、网格与结果投影。"
        self.display_key = None

    def set_context(self, title, detail, display_key=None):
        self.context_title = title
        self.context_detail = detail
        self.display_key = display_key
        self.update()

    def export_ui_state(self):
        return {
            "context_title": self.context_title,
            "context_detail": self.context_detail,
            "display_key": self.display_key,
        }

    def restore_ui_state(self, state):
        if not isinstance(state, dict):
            return
        self.context_title = state.get("context_title") or self.context_title
        self.context_detail = state.get("context_detail") or self.context_detail
        self.display_key = state.get("display_key")
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#f6f7fa"))

        w, h = self.width(), self.height()
        map_rect = QRectF(w * 0.12, h * 0.14, w * 0.76, h * 0.70)
        boundary = QPolygonF([
            QPointF(map_rect.left() + map_rect.width() * 0.04, map_rect.top() + map_rect.height() * 0.18),
            QPointF(map_rect.left() + map_rect.width() * 0.84, map_rect.top() + map_rect.height() * 0.04),
            QPointF(map_rect.left() + map_rect.width() * 0.96, map_rect.top() + map_rect.height() * 0.76),
            QPointF(map_rect.left() + map_rect.width() * 0.18, map_rect.top() + map_rect.height() * 0.95),
        ])
        painter.setPen(QPen(QColor("#9aa8ba"), 1.2))
        painter.setBrush(QColor("#eef2f6"))
        painter.drawPolygon(boundary)

        painter.setClipRect(map_rect)
        painter.setPen(QPen(QColor("#d4dbe5"), 1))
        for i in range(1, 18):
            x = map_rect.left() + map_rect.width() * i / 18
            painter.drawLine(QPointF(x, map_rect.top()), QPointF(x - 20, map_rect.bottom()))
        for i in range(1, 13):
            y = map_rect.top() + map_rect.height() * i / 13
            painter.drawLine(QPointF(map_rect.left(), y + 8), QPointF(map_rect.right(), y - 12))
        painter.setClipping(False)

        self._draw_plan_fractures(painter, map_rect)
        self._draw_plan_wells(painter, map_rect)
        self._draw_plan_scale(painter, map_rect)

        painter.setPen(QColor("#20242b"))
        painter.setFont(QFont("Microsoft YaHei UI", 10, QFont.Bold))
        painter.drawText(18, 24, self.context_title)
        painter.setFont(QFont("Microsoft YaHei UI", 9))
        painter.drawText(18, 44, self.context_detail)
        painter.setFont(QFont("Microsoft YaHei UI", 8))
        painter.setPen(QColor("#596273"))
        painter.drawText(QRectF(w - 190, 18, 170, 22), Qt.AlignRight, "图层：井轨迹 / 裂缝 / 网格")
        painter.end()

    def _draw_plan_fractures(self, painter, rect):
        painter.setPen(QPen(QColor("#d8962f"), 1.6))
        for idx, t in enumerate([0.18, 0.28, 0.38, 0.52, 0.67, 0.78]):
            start = QPointF(rect.left() + rect.width() * t, rect.top() + rect.height() * 0.20)
            end = QPointF(rect.left() + rect.width() * (t + 0.12), rect.top() + rect.height() * 0.76)
            painter.drawLine(start, end)
        painter.setPen(QPen(QColor("#16a9d8"), 2))
        for t in [0.46, 0.56, 0.66]:
            x = rect.left() + rect.width() * t
            painter.drawLine(
                QPointF(x, rect.top() + rect.height() * 0.16),
                QPointF(x + rect.width() * 0.04, rect.top() + rect.height() * 0.72),
            )

    def _draw_plan_wells(self, painter, rect):
        wells = [
            ("MHVW37520", QColor("#d32323"), [
                (0.30, 0.80), (0.38, 0.62), (0.43, 0.43), (0.45, 0.24),
            ]),
            ("400A1200", QColor("#126bd6"), [(0.58, 0.18), (0.60, 0.46), (0.56, 0.72)]),
            ("400B1200", QColor("#126bd6"), [(0.70, 0.15), (0.72, 0.45), (0.69, 0.74)]),
        ]
        painter.setFont(QFont("Arial", 9, QFont.Bold))
        for name, color, coords in wells:
            points = [
                QPointF(rect.left() + rect.width() * x, rect.top() + rect.height() * y)
                for x, y in coords
            ]
            painter.setPen(QPen(color, 2.5))
            painter.drawPolyline(*points)
            painter.setBrush(color)
            painter.drawEllipse(points[-1], 4, 4)
            painter.setPen(QColor("#20242b"))
            painter.drawText(points[-1] + QPointF(6, -4), name)

    def _draw_plan_scale(self, painter, rect):
        base = QPointF(rect.left() + 16, rect.bottom() - 20)
        painter.setPen(QPen(QColor("#697386"), 2))
        painter.drawLine(base, base + QPointF(90, 0))
        painter.drawLine(base, base + QPointF(0, -9))
        painter.drawLine(base + QPointF(90, 0), base + QPointF(90, -9))
        painter.setPen(QColor("#697386"))
        painter.setFont(QFont("Microsoft YaHei UI", 8))
        painter.drawText(base + QPointF(24, -12), "750 m")


class ChartViewport(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("chartViewport")
        self.context_title = "当前图表：生产曲线"
        self.context_detail = "图表窗口用于显示模拟结果曲线。"
        self.display_key = "production_curve"
        self.chart_data = {}

    def set_context(self, title, detail, display_key=None):
        self.context_title = title
        self.context_detail = detail
        if display_key:
            self.display_key = display_key
        self.update()

    def set_chart_data(self, chart_key, data):
        if chart_key:
            self.chart_data[chart_key] = dict(data or {})
            self.update()

    def export_ui_state(self):
        return {
            "context_title": self.context_title,
            "context_detail": self.context_detail,
            "display_key": self.display_key,
        }

    def restore_ui_state(self, state):
        if not isinstance(state, dict):
            return
        self.context_title = state.get("context_title") or self.context_title
        self.context_detail = state.get("context_detail") or self.context_detail
        display_key = state.get("display_key")
        if display_key:
            self.display_key = display_key
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#ffffff"))
        painter.setRenderHint(QPainter.Antialiasing)

        style = CHART_STYLES.get(self.display_key, CHART_STYLES["production_curve"])
        data = self.chart_data.get(self.display_key) or {}
        axis = self._axis_info(style, data)
        rect = QRectF(82, 82, max(120, self.width() - 128), max(100, self.height() - 154))

        self._draw_titles(painter, data, style)
        self._draw_chart_frame(painter, rect, axis)

        if data.get("series"):
            self._draw_series_curves(painter, rect, style, data, axis)
        elif data.get("points"):
            self._draw_data_curve(painter, rect, style, data, axis)
        else:
            self._draw_curve(painter, rect, style, axis)

        self._draw_axis_titles(painter, rect, axis)
        painter.end()

    def _draw_titles(self, painter, data, style):
        title = data.get("title") or self.context_title
        detail = self.context_detail
        painter.setPen(QColor("#30343a"))
        painter.setFont(QFont("Microsoft YaHei UI", 10, QFont.Bold))
        painter.drawText(18, 24, title)
        painter.setFont(QFont("Microsoft YaHei UI", 9))
        painter.drawText(18, 44, detail or style["title"])

    def _axis_info(self, style, data):
        if self.display_key == "relative_permeability_curve":
            ticks = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
            return {
                "x_min": 0.0,
                "x_max": 1.0,
                "y_min": 0.0,
                "y_max": 1.0,
                "x_ticks": ticks,
                "y_ticks": ticks,
                "x_label": data.get("x_label", style["x"]),
                "y_label": data.get("y_label", style["y"]),
            }

        points = self._collect_points(data)
        if points:
            xs = [point[0] for point in points]
            ys = [point[1] for point in points]
            x_min, x_max = min(xs), max(xs)
            y_min, y_max = min(ys), max(ys)
        else:
            x_min, x_max = 0.0, 1.0
            y_min, y_max = 0.0, 1.0

        x_min, x_max = self._expand_range(x_min, x_max, 0.04)
        y_min, y_max = self._expand_range(y_min, y_max, 0.08)
        return {
            "x_min": x_min,
            "x_max": x_max,
            "y_min": y_min,
            "y_max": y_max,
            "x_ticks": self._make_ticks(x_min, x_max, 5),
            "y_ticks": self._make_ticks(y_min, y_max, 5),
            "x_label": data.get("x_label", style["x"]),
            "y_label": data.get("y_label", style["y"]),
        }

    def _collect_points(self, data):
        if data.get("series"):
            return [
                point
                for item in data.get("series", [])
                for point in item.get("points", [])
                if len(point) >= 2
            ]
        return [point for point in data.get("points", []) if len(point) >= 2]

    def _expand_range(self, min_value, max_value, ratio):
        if max_value == min_value:
            base = abs(min_value) or 1.0
            return min_value - base * ratio, max_value + base * ratio
        pad = (max_value - min_value) * ratio
        return min_value - pad, max_value + pad

    def _make_ticks(self, min_value, max_value, count):
        if count <= 1:
            return [min_value]
        return [
            min_value + (max_value - min_value) * index / (count - 1)
            for index in range(count)
        ]

    def _draw_chart_frame(self, painter, rect, axis):
        painter.fillRect(rect, QColor("#ffffff"))
        painter.setFont(QFont("Microsoft YaHei UI", 8))

        grid_pen = QPen(QColor("#d2d8e2"), 1)
        axis_pen = QPen(QColor("#7f8794"), 1)
        text_color = QColor("#4a5160")

        painter.setPen(grid_pen)
        for tick in axis["y_ticks"]:
            y = self._map_y(tick, rect, axis)
            painter.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))
        for tick in axis["x_ticks"]:
            x = self._map_x(tick, rect, axis)
            painter.drawLine(QPointF(x, rect.top()), QPointF(x, rect.bottom()))

        painter.setPen(axis_pen)
        painter.drawRect(rect)
        painter.setPen(text_color)
        for tick in axis["y_ticks"]:
            y = self._map_y(tick, rect, axis)
            painter.drawText(
                QRectF(12, y - 9, rect.left() - 20, 18),
                Qt.AlignRight | Qt.AlignVCenter,
                self._format_tick(tick),
            )
        for tick in axis["x_ticks"]:
            x = self._map_x(tick, rect, axis)
            painter.drawText(
                QRectF(x - 28, rect.bottom() + 6, 56, 18),
                Qt.AlignHCenter | Qt.AlignTop,
                self._format_tick(tick),
            )

    def _draw_axis_titles(self, painter, rect, axis):
        painter.setPen(QColor("#30343a"))
        painter.setFont(QFont("Microsoft YaHei UI", 9))
        painter.drawText(
            QRectF(rect.left(), self.height() - 36, rect.width(), 24),
            Qt.AlignHCenter | Qt.AlignVCenter,
            axis["x_label"],
        )

        painter.save()
        painter.translate(18, rect.center().y())
        painter.rotate(-90)
        painter.drawText(
            QRectF(-rect.height() / 2, 0, rect.height(), 24),
            Qt.AlignHCenter | Qt.AlignVCenter,
            axis["y_label"],
        )
        painter.restore()

    def _draw_series_curves(self, painter, rect, style, data, axis):
        series = data.get("series", [])
        legend_items = []

        for index, item in enumerate(series):
            color = QColor(item.get("color", style["color"]))
            mapped = []
            points = item.get("points", [])
            step = max(1, len(points) // 700)
            for x_value, y_value in points[::step]:
                mapped.append(
                    QPointF(
                        self._map_x(x_value, rect, axis),
                        self._map_y(y_value, rect, axis),
                    )
                )
            if len(mapped) >= 2:
                painter.setPen(QPen(color, 2))
                painter.drawPolyline(*mapped)
            for point in mapped[:: max(1, len(mapped) // 24)]:
                painter.setPen(QPen(color, 1))
                painter.setBrush(color)
                painter.drawEllipse(point, 2.2, 2.2)
            legend_items.append((item.get("name", f"series {index + 1}"), color))

        self._draw_legend(painter, rect, legend_items)
        if "so_fixed" in data:
            painter.setPen(QColor("#5d6675"))
            painter.setFont(QFont("Microsoft YaHei UI", 8))
            painter.drawText(
                int(rect.left() + 148),
                int(rect.top() + 25),
                f"So_fixed={data['so_fixed']:.4f}",
            )

    def _draw_legend(self, painter, rect, legend_items):
        if not legend_items:
            return
        width = 132
        height = 22 + len(legend_items) * 18
        box = QRectF(rect.left() + 10, rect.top() + 10, width, height)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#ffffff"))
        painter.drawRect(box)
        painter.setPen(QPen(QColor("#c8ced8"), 1))
        painter.drawRect(box)
        painter.setFont(QFont("Microsoft YaHei UI", 8))
        for index, (name, color) in enumerate(legend_items):
            y = box.top() + 20 + index * 18
            painter.setPen(QPen(color, 2))
            painter.drawLine(QPointF(box.left() + 10, y - 4), QPointF(box.left() + 34, y - 4))
            painter.setPen(QColor("#30343a"))
            painter.drawText(int(box.left() + 42), int(y), name)

    def _draw_data_curve(self, painter, rect, style, data, axis):
        points = data.get("points", [])
        if len(points) < 2:
            return
        mapped = []
        step = max(1, len(points) // 700)
        for x_value, y_value in points[::step]:
            mapped.append(
                QPointF(self._map_x(x_value, rect, axis), self._map_y(y_value, rect, axis))
            )
        painter.setPen(QPen(style["color"], 2))
        painter.drawPolyline(*mapped)
        painter.setPen(QColor("#5d6675"))
        painter.setFont(QFont("Microsoft YaHei UI", 8))
        painter.drawText(
            int(rect.left() + 10),
            int(rect.top() + 24),
            f"{data.get('y_field', 'Y')} / {data.get('x_field', 'X')}  点数: {len(points)}",
        )

    def _draw_curve(self, painter, rect, style, axis):
        if self.display_key == "relative_permeability_curve":
            curves = [
                ("krw", QColor("#13a85a"), lambda t: t ** 1.8),
                ("kro", QColor("#d45500"), lambda t: (1 - t) ** 1.6),
            ]
        elif self.display_key == "production_curve":
            curves = [
                ("日产油", QColor("#1f66c2"), lambda t: 0.82 * math.exp(-2.2 * t) + 0.10),
                ("日产水", QColor("#00a6d6"), lambda t: 0.10 + 0.70 * (t ** 1.35)),
                ("日产气", QColor("#db8b1f"), lambda t: 0.32 + 0.20 * math.sin(t * math.pi * 1.3)),
            ]
        elif self.display_key == "blasingame_curve":
            curves = [
                ("规整化流量", QColor("#d45500"), lambda t: 0.82 - 0.46 * math.log10(1 + 9 * t)),
                ("积分函数", QColor("#7b4bc4"), lambda t: 0.74 - 0.34 * math.sqrt(t)),
            ]
        elif self.display_key == "pvt_curve":
            curves = [
                ("Z 因子", QColor("#7b4bc4"), lambda t: 0.28 + 0.50 * (1 - math.exp(-2.4 * t))),
            ]
        else:
            curves = [
                (style["title"], style["color"], lambda t: 0.08 + 0.78 * (1 - 0.86 ** (t * 24))),
            ]

        legend_items = []
        for name, color, formula in curves:
            painter.setPen(QPen(color, 2))
            points = []
            for i in range(70):
                t = i / 69
                x_value = axis["x_min"] + (axis["x_max"] - axis["x_min"]) * t
                y_norm = max(0.04, min(0.96, formula(t)))
                y_value = axis["y_min"] + (axis["y_max"] - axis["y_min"]) * y_norm
                points.append(QPointF(self._map_x(x_value, rect, axis), self._map_y(y_value, rect, axis)))
            painter.drawPolyline(*points)
            legend_items.append((name, color))
        self._draw_legend(painter, rect, legend_items)

    def _map_x(self, value, rect, axis):
        span = axis["x_max"] - axis["x_min"] or 1.0
        return rect.left() + rect.width() * ((value - axis["x_min"]) / span)

    def _map_y(self, value, rect, axis):
        span = axis["y_max"] - axis["y_min"] or 1.0
        return rect.bottom() - rect.height() * ((value - axis["y_min"]) / span)

    def _format_tick(self, value):
        if abs(value) >= 1000:
            return f"{value:.0f}"
        if abs(value) >= 10:
            return f"{value:.1f}"
        return f"{value:.2f}".rstrip("0").rstrip(".")


class LayerControlPanel(QFrame):
    layer_toggled = pyqtSignal(str, bool)

    ITEMS = [
        ("网格", "grid"),
        ("网格加密区域", "grid_refinement"),
        ("井轨迹", "well"),
        ("天然裂缝", "natural_fractures"),
        ("人工裂缝", "hydraulic_fractures"),
    ]

    def __init__(self, layers=None, parent=None):
        super().__init__(parent)
        self.setObjectName("layerControlPanel")
        self._checks = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        title = QLabel("图层")
        title.setObjectName("layerControlTitle")
        layout.addWidget(title)

        layer_state = dict(layers or {})
        for text, key in self.ITEMS:
            check = QCheckBox(text)
            check.setObjectName("layerControlCheck")
            check.setChecked(bool(layer_state.get(key, False)))
            check.toggled.connect(
                lambda enabled, layer_key=key: self.layer_toggled.emit(layer_key, enabled))
            self._checks[key] = check
            layout.addWidget(check)

    def set_layer_state(self, layer_key, enabled):
        check = self._checks.get(layer_key)
        if check is None:
            return
        previous = check.blockSignals(True)
        try:
            check.setChecked(bool(enabled))
        finally:
            check.blockSignals(previous)

    def set_layer_states(self, layers):
        for layer_key, enabled in (layers or {}).items():
            self.set_layer_state(layer_key, enabled)

    def layer_label(self, layer_key):
        for text, key in self.ITEMS:
            if key == layer_key:
                return text
        return layer_key


class ViewPage(QFrame):
    new_window_requested = pyqtSignal()
    clone_window_requested = pyqtSignal()
    close_window_requested = pyqtSignal()
    view_message = pyqtSignal(str)
    result_property_selected = pyqtSignal(str)
    preview_requested = pyqtSignal(object, str, str, str, int)

    def __init__(self, viewport, view_type="3d", parent=None):
        super().__init__(parent)
        self.viewport = viewport
        self.view_type = view_type
        self.setObjectName("viewPage")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.toolbar = ViewToolbar(view_type)
        self.toolbar.new_window_requested.connect(self.new_window_requested)
        self.toolbar.clone_window_requested.connect(self.clone_window_requested)
        self.toolbar.close_window_requested.connect(self.close_window_requested)
        self._time_playback_timer = None
        self.layer_control = None
        if view_type == "3d":
            self._time_playback_timer = QTimer(self)
            self._time_playback_timer.setInterval(800)
            self._time_playback_timer.timeout.connect(self._advance_time_playback)
            self.toolbar.tool_requested.connect(self._handle_tool_requested)
            self.toolbar.property_selected.connect(self._handle_property_selected)
            self.toolbar.slice_requested.connect(self._handle_slice_requested)
            self.toolbar.slice_reset_requested.connect(self._handle_slice_reset_requested)
            self.toolbar.threshold_requested.connect(self._handle_threshold_requested)
            self.toolbar.threshold_clear_requested.connect(self._handle_threshold_clear_requested)
            self.toolbar.time_playback_requested.connect(self._handle_time_playback_requested)
            self.toolbar.geometry_preview_requested.connect(self._handle_geometry_preview_requested)
            self.toolbar.geometry_style_requested.connect(
                self._handle_geometry_style_requested)
            self.toolbar.static_preview_requested.connect(self._handle_static_preview_requested)
            self.toolbar.static_layer_preview_requested.connect(self._handle_static_layer_preview_requested)
            self.toolbar.fence_action_requested.connect(
                self._handle_fence_action_requested)
            if hasattr(self.viewport, "interaction_message"):
                self.viewport.interaction_message.connect(self.view_message.emit)
            if hasattr(self.viewport, "fence_state_changed"):
                self.viewport.fence_state_changed.connect(
                    self._handle_fence_state_changed)
        layout.addWidget(self.toolbar)
        self.viewport_container = QFrame()
        self.viewport_container.setObjectName("viewContentFrame")
        viewport_layout = QVBoxLayout(self.viewport_container)
        viewport_layout.setContentsMargins(0, 0, 0, 0)
        viewport_layout.setSpacing(0)
        viewport_layout.addWidget(viewport, 1)
        layout.addWidget(self.viewport_container, 1)
        if view_type == "3d":
            self.layer_control = LayerControlPanel(
                getattr(self.viewport, "layers", {}), self.viewport_container)
            self.layer_control.layer_toggled.connect(self._handle_layer_toggled)
            self._sync_layer_control_visibility()
            self.layer_control.raise_()
            QTimer.singleShot(0, self._position_layer_control)
            self._sync_fence_controls()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_layer_control()

    def _position_layer_control(self):
        if self.layer_control is None:
            return
        self._sync_layer_control_visibility()
        if not self.layer_control.isVisible():
            return
        margin = 10
        self.layer_control.adjustSize()
        width = max(142, self.layer_control.sizeHint().width())
        height = self.layer_control.sizeHint().height()
        x = max(margin, self.viewport_container.width() - width - margin)
        self.layer_control.setGeometry(x, margin, width, height)
        self.layer_control.raise_()

    def _sync_layer_control_visibility(self):
        if self.layer_control is None:
            return
        self.layer_control.setVisible(True)

    def _handle_layer_toggled(self, layer_key, enabled):
        self.set_layer_state(layer_key, enabled, update_panel=False)
        label = self.layer_control.layer_label(layer_key) if self.layer_control else layer_key
        state_text = "显示" if enabled else "隐藏"
        self.view_message.emit(f"[图层] {label} 已{state_text}")

    def _handle_fence_state_changed(self, state=None):
        self._sync_fence_controls()

    def _sync_fence_controls(self):
        if self.view_type != "3d":
            return False
        if not hasattr(self.toolbar, "set_fence_controls_state"):
            return False
        if not hasattr(self.viewport, "fence_section_ui_state"):
            return False

        state = dict(self.viewport.fence_section_ui_state() or {})
        adapter_capabilities = {
            "can_start": "start_fence_section",
            "can_complete": "complete_fence_section",
            "can_cancel": "cancel_fence_section",
            "can_clear": "clear_fence_section",
            "can_exit": "exit_fence_section",
        }
        for state_key, method_name in adapter_capabilities.items():
            if not hasattr(self.viewport, method_name):
                state[state_key] = False

        self.toolbar.set_fence_controls_state(state)
        return True

    def _handle_fence_action_requested(self, action):
        action = str(action or "").strip().lower()
        method_names = {
            "start": "start_fence_section",
            "complete": "complete_fence_section",
            "cancel": "cancel_fence_section",
            "clear": "clear_fence_section",
            "exit": "exit_fence_section",
        }
        method_name = method_names.get(action)
        if method_name is None:
            message = f"[折线剖面] 不支持的操作：{action}"
            self.view_message.emit(message)
            return False, message

        method = getattr(self.viewport, method_name, None)
        if method is None:
            message = f"[折线剖面] 前端适配方法尚不可用：{method_name}"
            self.view_message.emit(message)
            self._sync_fence_controls()
            return False, message

        self._stop_time_playback_timer()
        try:
            if action == "start":
                property_name = (
                    self.toolbar.current_property_spec().fence_name)
                if not property_name:
                    message = (
                        "[折线剖面] 当前属性不支持折线剖面")
                    self.view_message.emit(message)
                    return False, message
                result = method(property_name)
            else:
                result = method()
        except Exception as exc:
            ok = False
            message = f"[折线剖面] 操作失败：{exc}"
        else:
            if isinstance(result, tuple) and len(result) >= 2:
                ok, message = bool(result[0]), str(result[1])
            else:
                ok = bool(result)
                message = (
                    f"[折线剖面] {action} 操作完成"
                    if ok else f"[折线剖面] {action} 操作失败"
                )

        self.view_message.emit(message)
        self._sync_fence_controls()
        return ok, message

    def _handle_tool_requested(self, command):
        export_path = None
        if command == "export_graphic":
            if hasattr(self.viewport, "has_simulation_data") and not self.viewport.has_simulation_data():
                self.view_message.emit("[截图] 当前 3D 窗口没有可用模拟结果，请先运行或加载模拟结果")
                return
            export_path, _ = QFileDialog.getSaveFileName(
                self,
                "导出当前 3D 视图",
                "",
                "PNG 图像 (*.png);;JPEG 图像 (*.jpg *.jpeg);;所有文件 (*.*)",
            )
            if not export_path:
                self.view_message.emit("[截图] 已取消导出")
                return
        if hasattr(self.viewport, "handle_tool_request"):
            scale = self.toolbar.export_scale() if hasattr(self.toolbar, "export_scale") else 1.0
            ok, message = self.viewport.handle_tool_request(
                command,
                export_path=export_path,
                export_scale=scale,
            )
            if ok and command == "export_graphic" and export_path:
                try:
                    metadata_path = self._write_export_metadata(export_path)
                    message = f"{message} | metadata: {metadata_path}"
                except OSError as exc:
                    message = f"{message} | metadata failed: {exc}"
            self.view_message.emit(message)

    def _write_export_metadata(self, export_path):
        viewport = getattr(self, "viewport", None)
        sim_data = getattr(viewport, "simulation_data", None)
        result_context = dict(
            getattr(sim_data, "result_context", None) or {})
        for key in ("case_id", "run_id", "dataset_id"):
            value = self.property(key)
            if value:
                result_context[key] = str(value)
        render_context = dict(
            getattr(viewport, "current_render_context", None) or {})
        slice_state = getattr(viewport, "_slice_state", None)
        if slice_state is not None:
            property_key, axis, layer = slice_state
            slice_payload = {
                "property_key": property_key,
                "axis": axis,
                "layer": int(layer),
            }
        else:
            slice_payload = None
        time_step = None
        if hasattr(self.toolbar, "time_step_index"):
            time_step = int(self.toolbar.time_step_index.value())
        payload = {
            "schema_version": "preview_export_v1",
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "image_path": os.path.abspath(export_path),
            "result_context": result_context,
            "display_key": getattr(viewport, "display_key", ""),
            "render_context": render_context,
            "slice": slice_payload,
            "time_step_index": time_step,
        }
        metadata_path = f"{os.path.abspath(export_path)}.metadata.json"
        with open(metadata_path, "w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, indent=2)
        return metadata_path

    def _handle_property_selected(self, property_key):
        self._stop_time_playback_timer()
        spec = view_property_spec(property_key)
        self._sync_current_property_to_fence(spec)
        if spec.result_key:
            if hasattr(self.viewport, "render_property_field"):
                ok, message = self.viewport.render_property_field(
                    spec.result_key)
                self.view_message.emit(message)
            self.result_property_selected.emit(spec.result_key)
        elif spec.static_key:
            self.preview_requested.emit(
                self, "static", spec.static_key, "", 0)

    def _sync_current_property_to_fence(self, spec=None):
        spec = spec or self.toolbar.current_property_spec()
        if not spec.fence_name:
            self._sync_fence_controls()
            return False
        setter = getattr(
            self.viewport, "set_fence_section_property_preference", None)
        if setter is None:
            return False
        try:
            setter(spec.fence_name)
        except Exception:
            return False
        self._sync_fence_controls()
        return True

    def _handle_slice_requested(self, property_key, axis, layer):
        self._stop_time_playback_timer()
        if hasattr(self.viewport, "render_property_slice"):
            ok, message = self.viewport.render_property_slice(property_key, axis, layer)
            self.view_message.emit(message)

    def _handle_slice_reset_requested(self):
        self._stop_time_playback_timer()
        if hasattr(self.viewport, "reset_property_slice"):
            ok, message = self.viewport.reset_property_slice()
            self.view_message.emit(message)

    def _handle_threshold_requested(self, min_text, max_text):
        self._stop_time_playback_timer()
        if hasattr(self.viewport, "apply_threshold_filter"):
            ok, message = self.viewport.apply_threshold_filter(min_text, max_text)
            self.view_message.emit(message)

    def _handle_threshold_clear_requested(self):
        self._stop_time_playback_timer()
        if hasattr(self.viewport, "clear_threshold_filter"):
            ok, message = self.viewport.clear_threshold_filter()
            self.view_message.emit(message)

    def _handle_time_playback_requested(self, action, step_index):
        action = str(action or "").strip()
        if action == "prepare":
            self._stop_time_playback_timer()
            ok, message = self.viewport.prepare_time_playback(step_index)
            self._sync_time_step_control()
            self.view_message.emit(message)
            return
        if action == "play":
            if self._time_playback_timer is not None and self._time_playback_timer.isActive():
                self._time_playback_timer.stop()
                self.view_message.emit("[时间步] 已暂停自动播放")
                return
            info = self._current_time_playback_info()
            if not info.get("ready"):
                ok, message = self.viewport.prepare_time_playback(step_index)
                if not ok:
                    self.view_message.emit(message)
                    return
            self._sync_time_step_control()
            if self._time_playback_timer is not None:
                self._time_playback_timer.start()
            self.view_message.emit("[时间步] 已开始自动播放")
            return
        if action == "previous":
            self._stop_time_playback_timer()
            ok, message = self.viewport.show_previous_time_step()
            self._sync_time_step_control()
            self.view_message.emit(message)
            return
        if action == "next":
            self._stop_time_playback_timer()
            ok, message = self.viewport.show_next_time_step()
            self._sync_time_step_control()
            self.view_message.emit(message)
            return
        if action == "stop":
            self._stop_time_playback_timer()
            ok, message = self.viewport.stop_time_playback()
            self._sync_time_step_control()
            self.view_message.emit(message)

    def _handle_geometry_preview_requested(self, preview_kind):
        self._stop_time_playback_timer()
        self.preview_requested.emit(self, "geometry", preview_kind, "", 0)

    def _handle_geometry_style_requested(self):
        self._stop_time_playback_timer()
        getter = getattr(
            self.viewport,
            "get_geometry_preview_style",
            None,
        )
        if getter is None:
            self.view_message.emit(
                "[预览样式] 当前窗口不支持几何预览样式")
            return

        ok, message, style = getter()
        if not ok:
            self.view_message.emit(message)
            return

        dialog = GeometryPreviewStyleDialog(
            initial_style=style,
            apply_callback=self._apply_geometry_preview_style,
            parent=self,
        )
        dialog.apply_failed.connect(self.view_message.emit)
        dialog.message_emitted.connect(self.view_message.emit)
        dialog.style_applied.connect(
            lambda _style: self.view_message.emit(
                "[预览样式] 已应用当前窗口样式"))
        dialog.exec_()

    def _apply_geometry_preview_style(self, style):
        setter = getattr(
            self.viewport,
            "set_geometry_preview_style",
            None,
        )
        if setter is None:
            return (
                False,
                "[预览样式] 当前窗口不支持设置几何预览样式",
                {},
            )

        try:
            result = setter(
                dict(style),
                render_now=True,
            )
        except Exception as exc:
            return False, f"[预览样式] 更新失败：{exc}", {}

        if not isinstance(result, tuple) or len(result) < 3:
            return False, "[预览样式] 样式接口返回了无效结果", {}

        ok, message, normalized = result[:3]
        if not ok:
            return False, str(message or "[预览样式] 更新失败"), {}
        if not isinstance(normalized, dict):
            return False, "[预览样式] 样式接口返回了无效数据", {}
        return True, "", dict(normalized)

    def _handle_static_preview_requested(self, property_key):
        self._stop_time_playback_timer()
        self.preview_requested.emit(self, "static", property_key, "", 0)

    def _handle_static_layer_preview_requested(self, property_key, axis, layer):
        self._stop_time_playback_timer()
        self.preview_requested.emit(self, "static_layer", property_key, axis, int(layer))

    def handle_preview_request(self, preview_type, key, axis="", layer=0):
        if preview_type == "geometry" and hasattr(self.viewport, "toggle_geometry_preview"):
            ok, message = self.viewport.toggle_geometry_preview(key)
        elif preview_type == "static" and hasattr(self.viewport, "toggle_static_property_preview"):
            ok, message = self.viewport.toggle_static_property_preview(key)
        elif preview_type == "static_layer" and hasattr(self.viewport, "toggle_static_property_layer_preview"):
            ok, message = self.viewport.toggle_static_property_layer_preview(key, axis, layer)
        else:
            ok, message = False, f"[预览] 当前窗口不支持预览操作：{preview_type}"
        self.view_message.emit(message)
        return ok, message

    def _advance_time_playback(self):
        if not hasattr(self.viewport, "show_next_time_step"):
            self._stop_time_playback_timer()
            return
        ok, message = self.viewport.show_next_time_step()
        if not ok:
            self._stop_time_playback_timer()
            self.view_message.emit(message)
            return
        self._sync_time_step_control()

    def _stop_time_playback_timer(self):
        if self._time_playback_timer is not None and self._time_playback_timer.isActive():
            self._time_playback_timer.stop()

    def _current_time_playback_info(self):
        if hasattr(self.viewport, "time_playback_info"):
            return self.viewport.time_playback_info() or {}
        return {}

    def _sync_time_step_control(self):
        info = self._current_time_playback_info()
        if not info.get("ready"):
            return
        if hasattr(self.toolbar, "set_time_step_index"):
            self.toolbar.set_time_step_index(
                info.get("current_index", 0),
                info.get("step_count", None),
            )

    def set_context(self, title, detail, display_key=None):
        self._stop_time_playback_timer()
        if hasattr(self.viewport, "set_context"):
            self.viewport.set_context(title, detail, display_key)
        self._sync_layer_control_visibility()
        if self.view_type == "3d" and display_key:
            self.set_property_selection(display_key)

    def set_property_selection(self, property_key):
        if self.view_type != "3d":
            return False
        if hasattr(self.toolbar, "set_property_key"):
            return self.toolbar.set_property_key(property_key, emit=False)
        return False

    def set_layer_state(self, layer_key, enabled, update_panel=True):
        if hasattr(self.viewport, "set_layer_state"):
            self.viewport.set_layer_state(layer_key, enabled)
        if update_panel and self.layer_control is not None:
            self.layer_control.set_layer_state(layer_key, enabled)

    def set_simulation_data(self, sim_data):
        if hasattr(self.viewport, "set_simulation_data"):
            self.viewport.set_simulation_data(sim_data)
        if (
            sim_data is not None
            and self.view_type == "3d"
            and hasattr(self.viewport, "prepare_time_playback")
            and hasattr(self.toolbar, "time_step_index")
            and getattr(sim_data, "time_steps", None) is not None
        ):
            self.viewport.prepare_time_playback(
                int(self.toolbar.time_step_index.value()))
            self._sync_time_step_control()
        self._sync_layer_control_visibility()
        self._position_layer_control()
        self._sync_fence_controls()

    def set_preview_data(self, sim_data):
        if hasattr(self.viewport, "set_preview_data"):
            self.viewport.set_preview_data(sim_data)

    def set_chart_data(self, chart_key, data):
        if hasattr(self.viewport, "set_chart_data"):
            self.viewport.set_chart_data(chart_key, data)

    def prepare_for_close(self):
        self._stop_time_playback_timer()
        if hasattr(self.viewport, "shutdown_interactions"):
            try:
                self.viewport.shutdown_interactions()
            except Exception:
                pass

    def export_ui_state(self):
        toolbar_state = {}
        viewport_state = {}
        if hasattr(self.toolbar, "export_ui_state"):
            toolbar_state = self.toolbar.export_ui_state()
        if hasattr(self.viewport, "export_ui_state"):
            viewport_state = self.viewport.export_ui_state()
        return {
            "view_type": self.view_type,
            "toolbar": toolbar_state,
            "viewport": viewport_state,
        }

    def restore_ui_state(self, state):
        if not isinstance(state, dict):
            return
        self._stop_time_playback_timer()
        if hasattr(self.toolbar, "restore_ui_state"):
            self.toolbar.restore_ui_state(state.get("toolbar") or {})
        if hasattr(self.viewport, "restore_ui_state"):
            self.viewport.restore_ui_state(state.get("viewport") or {})
        if self.view_type == "3d":
            self._sync_current_property_to_fence()
        self._sync_fence_controls()
        if self.layer_control is not None:
            self.layer_control.set_layer_states(getattr(self.viewport, "layers", {}))
            self._sync_layer_control_visibility()
            self._position_layer_control()
