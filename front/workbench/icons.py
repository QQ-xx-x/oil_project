# -*- coding: utf-8 -*-
"""Small painted icons used by the standalone workbench UI."""

from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import QColor, QIcon, QPainter, QPen, QPixmap


def painted_icon(kind, size=28):
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor("#6f7782"), max(1, size // 13))
    painter.setPen(pen)
    painter.setBrush(QColor("#f5f6f9"))
    pad = max(3, size // 7)
    rect = QRectF(pad, pad, size - 2 * pad, size - 2 * pad)

    if kind == "folder":
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

    painter.end()
    return QIcon(pixmap)


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
