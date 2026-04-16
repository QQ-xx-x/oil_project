"""
供主窗口使用的 PyVista Qt 视图封装。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PyQt5.QtWidgets import QVBoxLayout, QWidget
from PyQt5.QtCore import Qt, QEvent


def _ensure_local_pyvista_site() -> None:
    """当基础环境无法直接读取时，补充项目内的 PyVista 依赖路径。"""
    project_root = Path(__file__).resolve().parent.parent
    local_site = project_root / ".deps" / "pyvista_site"
    local_site_str = str(local_site)
    if local_site.exists() and local_site_str not in sys.path:
        # 追加到 sys.path 末尾，避免覆盖当前环境里已经可用的基础库，
        # 比如 numpy、matplotlib 等。
        sys.path.append(local_site_str)


_ensure_local_pyvista_site()

from pyvistaqt import QtInteractor


class PyVistaView(QWidget):
    """承载 PyVista QtInteractor 的 Qt 视图组件。

    这里保留了一些兼容属性，便于迁移阶段继续兼容现有主窗口和旧渲染器的调用方式。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.plotter = QtInteractor(self)
        self.layout.addWidget(self.plotter)

        # 兼容层：保留现有代码中会访问到的属性名，后续再统一收口。
        self.vtk_widget = self.plotter
        self.renderer = self.plotter.renderer

        self.plotter.set_background("black")
        self.plotter.setMouseTracking(True)

        # 选区交互：使用 Qt 事件模型，不再依赖 VTK observer / interactor。
        self._selection_enabled = False
        self._selection_press_cb = None
        self._selection_move_cb = None
        self._selection_release_cb = None
        self._selection_event_filter_installed = False
        self._last_mouse_pos_display = (0, 0)

    def reset_camera(self):
        self.plotter.reset_camera()
        self.plotter.render()

    def render_now(self) -> None:
        """立即触发一次渲染刷新。"""
        self.plotter.render()

    def set_cross_cursor(self, enabled: bool) -> None:
        """设置十字光标（用于框选模式）。"""
        self.setCursor(Qt.CrossCursor if enabled else Qt.ArrowCursor)

    def get_view_size(self) -> tuple[int, int]:
        """获取视图区域像素大小。"""
        size = self.plotter.size()
        return int(size.width()), int(size.height())

    def get_mouse_event_position(self) -> tuple[int, int]:
        """获取最近一次鼠标事件的显示坐标（像素）。

        注意：这里仅返回 Qt 事件缓存的坐标，不再向底层 interactor 查询。
        """
        return self._last_mouse_pos_display

    def _update_last_mouse_pos_from_qt(self, event) -> None:
        """把 Qt 鼠标坐标缓存为 VTK Display 坐标系（原点在左下角）。"""
        pos = event.pos()
        x = int(pos.x())
        y_qt = int(pos.y())
        w = max(1, int(self.plotter.width()))
        h = max(1, int(self.plotter.height()))

        x = max(0, min(w - 1, x))
        y_qt = max(0, min(h - 1, y_qt))

        # VTK 的 Display 坐标原点在左下角，Qt 在左上角，需要翻转 Y。
        y = (h - 1) - y_qt
        self._last_mouse_pos_display = (x, y)

    def eventFilter(self, obj, event):  # noqa: N802
        """Qt 事件过滤：在框选模式下拦截鼠标事件并转发给主窗口回调。"""
        if obj is self.plotter and self._selection_enabled:
            et = event.type()
            if et == QEvent.MouseButtonPress and getattr(event, "button", None) is not None:
                if event.button() == Qt.LeftButton:
                    self._update_last_mouse_pos_from_qt(event)
                    if self._selection_press_cb is not None:
                        self._selection_press_cb()
                    return True
            elif et == QEvent.MouseMove:
                self._update_last_mouse_pos_from_qt(event)
                if self._selection_move_cb is not None:
                    self._selection_move_cb()
                return True
            elif et == QEvent.MouseButtonRelease and getattr(event, "button", None) is not None:
                if event.button() == Qt.LeftButton:
                    self._update_last_mouse_pos_from_qt(event)
                    if self._selection_release_cb is not None:
                        self._selection_release_cb()
                    return True

        return super().eventFilter(obj, event)

    def install_selection_interaction(self, press_cb, move_cb, release_cb) -> None:
        """安装框选交互回调。

        回调签名由主窗口决定，视图只负责把 VTK 事件转发出去。
        """
        self.uninstall_selection_interaction()
        self._selection_press_cb = press_cb
        self._selection_move_cb = move_cb
        self._selection_release_cb = release_cb
        self._selection_enabled = True

        if not self._selection_event_filter_installed:
            self.plotter.installEventFilter(self)
            self._selection_event_filter_installed = True

    def uninstall_selection_interaction(self) -> None:
        """卸载框选交互回调。"""
        self._selection_enabled = False
        self._selection_press_cb = None
        self._selection_move_cb = None
        self._selection_release_cb = None

        if self._selection_event_filter_installed:
            try:
                self.plotter.removeEventFilter(self)
            except Exception:
                pass
            self._selection_event_filter_installed = False
