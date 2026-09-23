"""Tiny painted narrator faces — two clearly different styles, no 3D."""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget


class NewsAvatar(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._gender = "female"
        self._speaking = False
        self._mouth_open = False
        self._timer = QTimer(self)
        self._timer.setInterval(180)
        self._timer.timeout.connect(self._tick)
        self.setFixedSize(64, 64)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)

    def set_gender(self, gender: str) -> None:
        self._gender = "male" if gender == "male" else "female"
        self.update()

    def set_speaking(self, speaking: bool) -> None:
        self._speaking = bool(speaking)
        if self._speaking:
            self._timer.start()
        else:
            self._timer.stop()
            self._mouth_open = False
            self.update()

    def _tick(self) -> None:
        self._mouth_open = not self._mouth_open
        self.update()

    def paintEvent(self, _event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        if self._gender == "male":
            self._paint_male(painter)
        else:
            self._paint_female(painter)
        painter.end()

    def _paint_female(self, painter: QPainter) -> None:
        skin = QColor("#f6c9b4")
        hair = QColor("#6b2d4a")
        cx, cy = 32.0, 26.0

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#d96b9a"))
        painter.drawEllipse(QRectF(12, 42, 40, 26))

        painter.setBrush(hair)
        painter.drawEllipse(QRectF(8, 18, 14, 38))
        painter.drawEllipse(QRectF(42, 18, 14, 38))
        painter.drawEllipse(QRectF(12, 6, 40, 36))

        painter.setBrush(skin)
        painter.drawEllipse(QRectF(cx - 15, cy - 15, 30, 32))

        painter.setBrush(hair)
        bangs = QPainterPath()
        bangs.moveTo(cx - 15, cy - 4)
        bangs.quadTo(cx - 10, cy - 18, cx, cy - 16)
        bangs.quadTo(cx + 10, cy - 18, cx + 15, cy - 4)
        bangs.quadTo(cx, cy - 10, cx - 15, cy - 4)
        painter.drawPath(bangs)

        painter.setBrush(QColor("#1b1f24"))
        painter.drawEllipse(QRectF(cx - 8, cy - 2, 4.2, 4.8))
        painter.drawEllipse(QRectF(cx + 3.8, cy - 2, 4.2, 4.8))
        painter.setPen(QPen(QColor("#3b1d28"), 1.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawLine(int(cx - 8), int(cy - 4), int(cx - 3), int(cy - 5.5))
        painter.drawLine(int(cx + 4), int(cy - 5.5), int(cx + 9), int(cy - 4))

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#e8b84a"))
        painter.drawEllipse(QRectF(cx - 17, cy + 4, 4.5, 4.5))
        painter.drawEllipse(QRectF(cx + 12.5, cy + 4, 4.5, 4.5))

        if self._speaking and self._mouth_open:
            painter.setBrush(QColor("#c45b6e"))
            painter.drawEllipse(QRectF(cx - 4, cy + 8, 8, 5))
        else:
            painter.setBrush(QColor("#d45a72"))
            painter.drawEllipse(QRectF(cx - 4.5, cy + 8.2, 9, 4.2))

    def _paint_male(self, painter: QPainter) -> None:
        skin = QColor("#e2b48f")
        hair = QColor("#1f1a17")
        cx, cy = 32.0, 25.0

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#2f5f8a"))
        painter.drawRoundedRect(QRectF(14, 42, 36, 24), 6, 6)

        painter.setBrush(skin)
        painter.drawRoundedRect(QRectF(cx - 15, cy - 13, 30, 32), 10, 10)

        painter.setBrush(hair)
        painter.drawRoundedRect(QRectF(cx - 16, cy - 18, 32, 14), 8, 8)
        painter.drawRect(QRectF(cx - 16, cy - 10, 32, 6))

        painter.setBrush(QColor("#1b1f24"))
        painter.drawEllipse(QRectF(cx - 8, cy - 1, 4.4, 4.2))
        painter.drawEllipse(QRectF(cx + 3.6, cy - 1, 4.4, 4.2))

        painter.setBrush(QColor("#5a4638"))
        painter.drawRoundedRect(QRectF(cx - 8, cy + 6.5, 16, 5.5), 2, 2)

        painter.setPen(QPen(QColor("#8a5a48"), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        if self._speaking and self._mouth_open:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#7a3d42"))
            painter.drawEllipse(QRectF(cx - 3.2, cy + 11, 6.4, 3.6))
        else:
            painter.drawLine(int(cx - 4), int(cy + 12), int(cx + 4), int(cy + 12))
