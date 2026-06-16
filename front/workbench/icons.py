# -*- coding: utf-8 -*-
"""工作台界面使用的小型绘制图标。"""

from PyQt5.QtCore import QByteArray, QPointF, QRectF, Qt
from PyQt5.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from PyQt5.QtSvg import QSvgRenderer

from .icon_assets import common_svg_icon, oilfield_svg_icon
from .icon_registry import canonical_icon_kind


def painted_icon(kind, size=28, status=None):
    kind = canonical_icon_kind(kind)
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor("#6f7782"), max(1, size // 13))
    painter.setPen(pen)
    painter.setBrush(QColor("#f5f6f9"))
    pad = max(3, size // 7)
    rect = QRectF(pad, pad, size - 2 * pad, size - 2 * pad)

    if _paint_svg_icon(painter, kind, size):
        if status:
            _draw_status_badge(painter, status, size)
        painter.end()
        return QIcon(pixmap)

    if kind == "case_root":
        painter.setBrush(QColor("#4f95ad"))
        painter.drawEllipse(QRectF(size * 0.18, size * 0.16,
                                   size * 0.64, size * 0.22))
        painter.drawRect(QRectF(size * 0.18, size * 0.27,
                                size * 0.64, size * 0.45))
        painter.drawEllipse(QRectF(size * 0.18, size * 0.61,
                                   size * 0.64, size * 0.20))
        painter.setPen(QPen(QColor("#ffffff"), max(1, size // 18)))
        painter.drawLine(QPointF(size * 0.34, size * 0.43),
                         QPointF(size * 0.66, size * 0.43))
        painter.drawLine(QPointF(size * 0.34, size * 0.55),
                         QPointF(size * 0.66, size * 0.55))
    elif kind == "case_section":
        painter.setBrush(QColor("#dde6ef"))
        painter.drawRoundedRect(QRectF(pad, size * 0.30, size - 2 * pad,
                                       size * 0.50), 2, 2)
        painter.setBrush(QColor("#8aa5bd"))
        painter.drawRect(QRectF(pad + 2, size * 0.22, size * 0.36,
                                size * 0.16))
    elif kind == "keyword_param":
        painter.setBrush(QColor("#ffffff"))
        painter.drawRoundedRect(rect, 2, 2)
        painter.setPen(QPen(QColor("#526477"), max(1, size // 14)))
        for row, knob_x in enumerate((0.34, 0.62, 0.46)):
            y = size * (0.34 + row * 0.16)
            painter.drawLine(QPointF(size * 0.24, y), QPointF(size * 0.76, y))
            painter.setBrush(QColor("#7fa6c5"))
            painter.drawEllipse(QRectF(size * knob_x - size * 0.045,
                                       y - size * 0.045,
                                       size * 0.09, size * 0.09))
            painter.setBrush(QColor("#ffffff"))
    elif kind == "file":
        painter.setBrush(QColor("#ffffff"))
        painter.drawRoundedRect(rect, 2, 2)
        painter.setBrush(QColor("#dfe7ef"))
        painter.drawPolygon(
            QPointF(size * 0.62, pad),
            QPointF(size - pad, size * 0.36),
            QPointF(size * 0.62, size * 0.36),
        )
        painter.setPen(QPen(QColor("#7b8794"), max(1, size // 18)))
        painter.drawLine(QPointF(size * 0.30, size * 0.50),
                         QPointF(size * 0.70, size * 0.50))
        painter.drawLine(QPointF(size * 0.30, size * 0.62),
                         QPointF(size * 0.64, size * 0.62))
    elif kind == "property_file":
        painter.setBrush(QColor("#ffffff"))
        painter.drawRoundedRect(rect, 2, 2)
        painter.setBrush(QColor("#67a37f"))
        for row in range(3):
            y = size * (0.34 + row * 0.15)
            painter.drawRect(QRectF(size * 0.28, y, size * 0.44, size * 0.055))
    elif kind == "grid_file":
        painter.setBrush(QColor("#ffffff"))
        painter.drawRoundedRect(rect, 2, 2)
        painter.setPen(QPen(QColor("#35627b"), max(1, size // 18)))
        grid_rect = QRectF(size * 0.26, size * 0.28, size * 0.48, size * 0.48)
        painter.drawRect(grid_rect)
        for i in range(1, 3):
            x = grid_rect.left() + grid_rect.width() * i / 3
            y = grid_rect.top() + grid_rect.height() * i / 3
            painter.drawLine(QPointF(x, grid_rect.top()), QPointF(x, grid_rect.bottom()))
            painter.drawLine(QPointF(grid_rect.left(), y), QPointF(grid_rect.right(), y))
    elif kind == "dfn_file":
        painter.setBrush(QColor("#ffffff"))
        painter.drawRoundedRect(rect, 2, 2)
        painter.setPen(QPen(QColor("#b85d4f"), max(1, size // 11)))
        painter.drawPolyline(
            QPointF(size * 0.24, size * 0.68),
            QPointF(size * 0.40, size * 0.38),
            QPointF(size * 0.55, size * 0.60),
            QPointF(size * 0.76, size * 0.30),
        )
    elif kind == "run":
        painter.setBrush(QColor("#2f9e66"))
        painter.setPen(QPen(QColor("#1e6f49"), max(1, size // 18)))
        painter.drawEllipse(rect)
        painter.setBrush(QColor("#ffffff"))
        painter.setPen(Qt.NoPen)
        painter.drawPolygon(
            QPointF(size * 0.42, size * 0.32),
            QPointF(size * 0.42, size * 0.70),
            QPointF(size * 0.72, size * 0.51),
        )
    elif kind == "validate":
        painter.setBrush(QColor("#eef6fb"))
        painter.setPen(QPen(QColor("#4f7893"), max(1, size // 16)))
        painter.drawRoundedRect(rect, 3, 3)
        painter.setPen(QPen(QColor("#2f9e66"), max(2, size // 10)))
        painter.drawLine(QPointF(size * 0.28, size * 0.52),
                         QPointF(size * 0.43, size * 0.68))
        painter.drawLine(QPointF(size * 0.43, size * 0.68),
                         QPointF(size * 0.74, size * 0.32))
    elif kind == "result":
        painter.setBrush(QColor("#ffffff"))
        painter.drawRoundedRect(rect, 2, 2)
        painter.setPen(QPen(QColor("#2f6f9f"), max(1, size // 15)))
        painter.drawLine(QPointF(size * 0.25, size * 0.72),
                         QPointF(size * 0.25, size * 0.48))
        painter.drawLine(QPointF(size * 0.44, size * 0.72),
                         QPointF(size * 0.44, size * 0.36))
        painter.drawLine(QPointF(size * 0.63, size * 0.72),
                         QPointF(size * 0.63, size * 0.26))
        painter.setBrush(QColor("#2f9e66"))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QRectF(size * 0.58, size * 0.56,
                                   size * 0.20, size * 0.20))
    elif kind == "layer":
        painter.setPen(QPen(QColor("#526477"), max(1, size // 18)))
        for offset, color in [(0.16, "#dce9f1"), (0.30, "#b9cfdd"), (0.44, "#88a8ba")]:
            painter.setBrush(QColor(color))
            painter.drawPolygon(
                QPointF(size * 0.50, size * offset),
                QPointF(size * 0.80, size * (offset + 0.14)),
                QPointF(size * 0.50, size * (offset + 0.28)),
                QPointF(size * 0.20, size * (offset + 0.14)),
            )
    elif kind == "pressure":
        painter.setBrush(QColor("#ffffff"))
        painter.drawRoundedRect(rect, 2, 2)
        painter.setBrush(QColor("#d9534f"))
        painter.setPen(Qt.NoPen)
        painter.drawRect(QRectF(size * 0.28, size * 0.32,
                                size * 0.10, size * 0.36))
        painter.setBrush(QColor("#f0ad4e"))
        painter.drawRect(QRectF(size * 0.45, size * 0.42,
                                size * 0.10, size * 0.26))
        painter.setBrush(QColor("#2f6f9f"))
        painter.drawRect(QRectF(size * 0.62, size * 0.24,
                                size * 0.10, size * 0.44))
    elif kind == "saturation":
        painter.setBrush(QColor("#dff3fb"))
        painter.setPen(QPen(QColor("#2e83b8"), max(1, size // 14)))
        painter.drawEllipse(QRectF(size * 0.26, size * 0.36,
                                   size * 0.48, size * 0.42))
        painter.setBrush(QColor("#2e83b8"))
        painter.drawPolygon(
            QPointF(size * 0.50, size * 0.18),
            QPointF(size * 0.30, size * 0.50),
            QPointF(size * 0.70, size * 0.50),
        )
    elif kind == "permeability":
        painter.setBrush(QColor("#ffffff"))
        painter.drawRoundedRect(rect, 2, 2)
        painter.setPen(QPen(QColor("#5d8d68"), max(1, size // 13)))
        for y in (0.34, 0.50, 0.66):
            painter.drawLine(QPointF(size * 0.24, size * y),
                             QPointF(size * 0.70, size * y))
            painter.drawLine(QPointF(size * 0.70, size * y),
                             QPointF(size * 0.58, size * (y - 0.09)))
            painter.drawLine(QPointF(size * 0.70, size * y),
                             QPointF(size * 0.58, size * (y + 0.09)))
    elif kind == "porosity":
        painter.setBrush(QColor("#ffffff"))
        painter.drawRoundedRect(rect, 2, 2)
        painter.setPen(QPen(QColor("#6f7782"), max(1, size // 18)))
        painter.setBrush(QColor("#b7d8c5"))
        for x, y, r in [
            (0.32, 0.34, 0.12), (0.58, 0.30, 0.10), (0.46, 0.54, 0.13),
            (0.68, 0.62, 0.09), (0.28, 0.66, 0.08),
        ]:
            painter.drawEllipse(QRectF(size * (x - r / 2), size * (y - r / 2),
                                       size * r, size * r))
    elif kind == "rock":
        painter.setBrush(QColor("#c8b99b"))
        painter.setPen(QPen(QColor("#806f55"), max(1, size // 18)))
        painter.drawPolygon(
            QPointF(size * 0.24, size * 0.64),
            QPointF(size * 0.36, size * 0.28),
            QPointF(size * 0.62, size * 0.22),
            QPointF(size * 0.80, size * 0.48),
            QPointF(size * 0.66, size * 0.76),
            QPointF(size * 0.36, size * 0.78),
        )
    elif kind == "fluid":
        painter.setBrush(QColor("#dff3fb"))
        painter.setPen(QPen(QColor("#2e83b8"), max(1, size // 15)))
        painter.drawEllipse(QRectF(size * 0.22, size * 0.35,
                                   size * 0.56, size * 0.40))
        painter.setBrush(QColor("#2e83b8"))
        painter.drawEllipse(QRectF(size * 0.36, size * 0.20,
                                   size * 0.28, size * 0.28))
    elif kind == "fracture":
        painter.setBrush(QColor("#fff7f2"))
        painter.drawRoundedRect(rect, 2, 2)
        painter.setPen(QPen(QColor("#b85d4f"), max(2, size // 10)))
        painter.drawPolyline(
            QPointF(size * 0.28, size * 0.76),
            QPointF(size * 0.40, size * 0.46),
            QPointF(size * 0.55, size * 0.58),
            QPointF(size * 0.70, size * 0.22),
        )
    elif kind == "solver":
        painter.setBrush(QColor("#edf2f7"))
        painter.drawRoundedRect(rect, 2, 2)
        painter.setPen(QPen(QColor("#526477"), max(1, size // 14)))
        for x, y in [(0.34, 0.36), (0.66, 0.36), (0.50, 0.66)]:
            painter.setBrush(QColor("#ffffff"))
            painter.drawEllipse(QRectF(size * x - size * 0.08,
                                       size * y - size * 0.08,
                                       size * 0.16, size * 0.16))
        painter.drawLine(QPointF(size * 0.40, size * 0.40),
                         QPointF(size * 0.60, size * 0.40))
        painter.drawLine(QPointF(size * 0.38, size * 0.42),
                         QPointF(size * 0.48, size * 0.60))
        painter.drawLine(QPointF(size * 0.62, size * 0.42),
                         QPointF(size * 0.52, size * 0.60))
    elif kind == "lgr":
        painter.setBrush(QColor("#88c0d0"))
        painter.drawRect(rect)
        painter.setPen(QPen(QColor("#35627b"), max(1, size // 18)))
        for i in range(1, 4):
            x = pad + (size - 2 * pad) * i / 4
            y = pad + (size - 2 * pad) * i / 4
            painter.drawLine(QPointF(x, pad), QPointF(x, size - pad))
            painter.drawLine(QPointF(pad, y), QPointF(size - pad, y))
        painter.setBrush(QColor("#f2c24e"))
        painter.drawRect(QRectF(size * 0.42, size * 0.42,
                                size * 0.20, size * 0.20))
    elif kind == "copy":
        painter.setBrush(QColor("#eef2f6"))
        painter.drawRoundedRect(QRectF(size * 0.26, size * 0.18,
                                       size * 0.44, size * 0.50), 2, 2)
        painter.setBrush(QColor("#ffffff"))
        painter.drawRoundedRect(QRectF(size * 0.34, size * 0.28,
                                       size * 0.44, size * 0.50), 2, 2)
    elif kind == "folder":
        painter.setBrush(QColor("#d79b32"))
        painter.drawRoundedRect(QRectF(pad, size * 0.34, size - 2 * pad,
                                       size * 0.46), 2, 2)
        painter.drawRect(QRectF(pad + 2, size * 0.27, size * 0.34,
                                size * 0.16))
    elif kind == "new":
        painter.drawRoundedRect(rect, 2, 2)
        painter.setPen(QPen(QColor("#d88c18"), max(2, size // 10)))
        painter.drawLine(QPointF(size / 2, size * 0.30),
                         QPointF(size / 2, size * 0.70))
        painter.drawLine(QPointF(size * 0.30, size / 2),
                         QPointF(size * 0.70, size / 2))
    elif kind == "save":
        painter.setBrush(QColor("#8c9bad"))
        painter.drawRect(rect)
        painter.setBrush(QColor("#ffffff"))
        painter.drawRect(QRectF(size * 0.38, size * 0.20, size * 0.29,
                                size * 0.24))
        painter.drawRect(QRectF(size * 0.29, size * 0.56, size * 0.42,
                                size * 0.18))
    elif kind in ("undo", "redo"):
        direction = -1 if kind == "undo" else 1
        painter.setPen(QPen(QColor("#717884"), max(2, size // 10)))
        painter.drawArc(QRectF(size * 0.25, size * 0.30, size * 0.50,
                               size * 0.40), 25 * 16, 195 * 16)
        x = size * (0.28 if direction == -1 else 0.72)
        painter.drawLine(QPointF(x, size * 0.28),
                         QPointF(x - direction * size * 0.15, size * 0.39))
        painter.drawLine(QPointF(x, size * 0.28),
                         QPointF(x - direction * size * 0.02, size * 0.47))
    elif kind == "search":
        painter.setPen(QPen(QColor("#646d78"), max(2, size // 11)))
        painter.drawEllipse(QRectF(size * 0.22, size * 0.18, size * 0.42,
                                   size * 0.42))
        painter.drawLine(QPointF(size * 0.59, size * 0.58),
                         QPointF(size * 0.79, size * 0.79))
    elif kind == "monitor":
        painter.setPen(QPen(QColor("#ffffff"), max(1, size // 14)))
        painter.setBrush(QColor("#44a15d"))
        painter.drawRoundedRect(rect, 2, 2)
        painter.drawPolyline(
            QPointF(size * 0.19, size * 0.54),
            QPointF(size * 0.34, size * 0.54),
            QPointF(size * 0.43, size * 0.32),
            QPointF(size * 0.54, size * 0.70),
            QPointF(size * 0.65, size * 0.48),
            QPointF(size * 0.82, size * 0.48))
    elif kind == "database":
        painter.setBrush(QColor("#4f95ad"))
        painter.drawEllipse(QRectF(size * 0.22, size * 0.20,
                                   size * 0.55, size * 0.20))
        painter.drawRect(QRectF(size * 0.22, size * 0.30,
                                size * 0.55, size * 0.43))
        painter.drawEllipse(QRectF(size * 0.22, size * 0.62,
                                   size * 0.55, size * 0.18))
    elif kind == "import":
        painter.drawRoundedRect(rect, 2, 2)
        painter.setPen(QPen(QColor("#2c8c68"), max(2, size // 12)))
        painter.drawLine(QPointF(size * 0.50, size * 0.30),
                         QPointF(size * 0.50, size * 0.69))
        painter.drawLine(QPointF(size * 0.50, size * 0.69),
                         QPointF(size * 0.36, size * 0.54))
        painter.drawLine(QPointF(size * 0.50, size * 0.69),
                         QPointF(size * 0.64, size * 0.54))
    elif kind == "window":
        painter.setBrush(QColor("#f8f9fb"))
        painter.drawRect(rect)
        painter.setBrush(QColor("#aeb8c5"))
        painter.drawRect(QRectF(pad, pad, size - 2 * pad, size * 0.17))
    elif kind == "warning":
        painter.setBrush(QColor("#ffd34d"))
        painter.setPen(QPen(QColor("#b47a00"), max(1, size // 16)))
        painter.drawPolygon(
            QPointF(size * 0.50, size * 0.16),
            QPointF(size * 0.84, size * 0.78),
            QPointF(size * 0.16, size * 0.78),
        )
        painter.setPen(QPen(QColor("#5d4200"), max(1, size // 12)))
        painter.drawLine(QPointF(size * 0.50, size * 0.34), QPointF(size * 0.50, size * 0.58))
        painter.drawPoint(QPointF(size * 0.50, size * 0.68))
    elif kind == "chart":
        painter.setBrush(QColor("#ffffff"))
        painter.drawRect(rect)
        painter.setPen(QPen(QColor("#2670c9"), max(1, size // 12)))
        painter.drawPolyline(
            QPointF(size * 0.20, size * 0.72),
            QPointF(size * 0.36, size * 0.56),
            QPointF(size * 0.52, size * 0.64),
            QPointF(size * 0.74, size * 0.32),
        )
    elif kind == "grid":
        painter.setBrush(QColor("#88c0d0"))
        painter.drawRect(rect)
        painter.setPen(QPen(QColor("#35627b"), max(1, size // 18)))
        for i in range(1, 4):
            x = pad + (size - 2 * pad) * i / 4
            y = pad + (size - 2 * pad) * i / 4
            painter.drawLine(QPointF(x, pad), QPointF(x, size - pad))
            painter.drawLine(QPointF(pad, y), QPointF(size - pad, y))
    elif kind == "well":
        painter.setPen(QPen(QColor("#1d9bd1"), max(2, size // 9)))
        painter.drawLine(QPointF(size * 0.50, size * 0.14), QPointF(size * 0.50, size * 0.82))
        painter.setPen(QPen(QColor("#e15b32"), max(1, size // 12)))
        painter.drawLine(QPointF(size * 0.50, size * 0.50), QPointF(size * 0.74, size * 0.70))
    elif kind == "case":
        painter.setBrush(QColor("#4f95ad"))
        painter.drawEllipse(QRectF(size * 0.20, size * 0.16, size * 0.60, size * 0.24))
        painter.drawRect(QRectF(size * 0.20, size * 0.28, size * 0.60, size * 0.45))
        painter.drawEllipse(QRectF(size * 0.20, size * 0.62, size * 0.60, size * 0.22))
    elif kind == "process":
        painter.setBrush(QColor("#ffffff"))
        painter.drawRoundedRect(rect, 2, 2)
        painter.setPen(QPen(QColor("#2c8c68"), max(1, size // 12)))
        painter.drawLine(QPointF(size * 0.28, size * 0.34), QPointF(size * 0.72, size * 0.34))
        painter.drawLine(QPointF(size * 0.28, size * 0.50), QPointF(size * 0.72, size * 0.50))
        painter.drawLine(QPointF(size * 0.28, size * 0.66), QPointF(size * 0.58, size * 0.66))
    else:
        painter.setBrush(QColor("#d5dae1"))
        painter.drawRoundedRect(rect, 3, 3)

    if status:
        _draw_status_badge(painter, status, size)
    painter.end()
    return QIcon(pixmap)


def _paint_svg_icon(painter, kind, size):
    svg = oilfield_svg_icon(kind) or common_svg_icon(kind)
    if svg is None:
        return False
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    if not renderer.isValid():
        return False
    renderer.render(painter, QRectF(0, 0, size, size))
    return True


def _draw_status_badge(painter, status, size):
    colors = {
        "ok": "#2fa36b",
        "missing": "#d9473f",
        "warning": "#d89822",
        "dirty": "#d89822",
        "blocked": "#8f4ab8",
    }
    color = QColor(colors.get(status, "#687282"))
    radius = max(4, size // 4)
    center_x = size - radius - 1
    center_y = size - radius - 1
    badge = QRectF(center_x - radius, center_y - radius,
                   radius * 2, radius * 2)
    painter.setPen(QPen(QColor("#ffffff"), max(1, size // 18)))
    painter.setBrush(color)
    painter.drawEllipse(badge)

    painter.setPen(QPen(QColor("#ffffff"), max(1, size // 12)))
    if status == "ok":
        painter.drawLine(QPointF(center_x - radius * 0.45, center_y),
                         QPointF(center_x - radius * 0.12, center_y + radius * 0.34))
        painter.drawLine(QPointF(center_x - radius * 0.12, center_y + radius * 0.34),
                         QPointF(center_x + radius * 0.50, center_y - radius * 0.36))
    elif status == "missing":
        painter.drawLine(QPointF(center_x - radius * 0.40, center_y),
                         QPointF(center_x + radius * 0.40, center_y))
    elif status in {"warning", "dirty", "blocked"}:
        painter.drawLine(QPointF(center_x, center_y - radius * 0.42),
                         QPointF(center_x, center_y + radius * 0.18))
        painter.drawPoint(QPointF(center_x, center_y + radius * 0.48))


def project_thumbnail(accent="#c89432"):
    pixmap = QPixmap(86, 56)
    pixmap.fill(QColor("#fbfcfd"))
    painter = QPainter(pixmap)
    painter.setPen(QPen(QColor("#bcc3cb"), 1))
    painter.drawRect(0, 0, 85, 55)
    painter.setPen(QPen(QColor(accent), 2))
    painter.drawPolyline(
        QPointF(8, 45), QPointF(18, 35), QPointF(29, 37),
        QPointF(40, 25), QPointF(54, 20), QPointF(67, 14),
        QPointF(78, 12))
    painter.setPen(QPen(QColor("#d8dde4"), 1))
    painter.drawLine(8, 45, 78, 45)
    painter.end()
    return pixmap
