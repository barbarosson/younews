"""Centered You News mascot that pulses while a pane is loading."""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtWidgets import QWidget

from config import APP_ICON_PNG, APP_MASCOT_PNG, APP_WORDMARK_PNG


class BusyOverlay(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("background: rgba(11, 16, 23, 185);")
        self._angle = 0
        self._mascot = APP_MASCOT_PNG.is_file()
        self._source = self._load_mark()
        self._timer = QTimer(self)
        self._timer.setInterval(40)
        self._timer.timeout.connect(self._spin)
        self.hide()

    def _load_mark(self) -> QPixmap:
        for path in (APP_MASCOT_PNG, APP_ICON_PNG, APP_WORDMARK_PNG):
            if path.is_file():
                pixmap = QPixmap(str(path))
                if not pixmap.isNull():
                    size = 148 if path == APP_MASCOT_PNG else 112
                    return pixmap.scaled(
                        size,
                        size,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
        mark = QPixmap(112, 112)
        mark.fill(QColor("#e3b341"))
        return mark

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self._angle = 0
        self._timer.start()

    def hideEvent(self, event) -> None:  # noqa: N802
        self._timer.stop()
        super().hideEvent(event)

    def _spin(self) -> None:
        self._angle = (self._angle + 10) % 360
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        super().paintEvent(event)
        if self._source.isNull():
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        cx = self.width() / 2
        cy = self.height() / 2
        painter.translate(cx, cy)
        if not self._mascot:
            painter.rotate(self._angle)
        painter.translate(-self._source.width() / 2, -self._source.height() / 2)
        painter.setOpacity(0.55 + 0.45 * abs((self._angle % 180) - 90) / 90)
        painter.drawPixmap(0, 0, self._source)
        painter.end()
