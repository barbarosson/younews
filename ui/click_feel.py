"""Pointer cursor and a short press flash so clicks are obvious."""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, QTimer, Qt
from PySide6.QtWidgets import (
    QAbstractButton,
    QAbstractItemView,
    QApplication,
    QComboBox,
    QHeaderView,
    QSlider,
    QTabBar,
)


_CLICKABLE = (
    QAbstractButton,
    QComboBox,
    QTabBar,
    QAbstractItemView,
    QHeaderView,
    QSlider,
)


class ClickFeelFilter(QObject):
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802
        kind = event.type()
        if kind == QEvent.Type.Enter and isinstance(watched, _CLICKABLE):
            if watched.isEnabled():  # type: ignore[attr-defined]
                watched.setCursor(Qt.CursorShape.PointingHandCursor)
        elif kind == QEvent.Type.MouseButtonPress and isinstance(watched, QAbstractButton):
            if event.button() == Qt.MouseButton.LeftButton and watched.isEnabled():  # type: ignore[attr-defined]
                _flash(watched, True)
        elif kind == QEvent.Type.MouseButtonRelease and isinstance(watched, QAbstractButton):
            QTimer.singleShot(90, lambda w=watched: _flash(w, False))
        elif kind == QEvent.Type.MouseButtonDblClick and isinstance(watched, QAbstractButton):
            _flash(watched, True)
            QTimer.singleShot(90, lambda w=watched: _flash(w, False))
        return False


def _flash(widget, on: bool) -> None:
    try:
        widget.setProperty("clickHeld", on)
        style = widget.style()
        style.unpolish(widget)
        style.polish(widget)
        widget.update()
    except RuntimeError:
        pass


def install_click_feel(app: QApplication | None = None) -> None:
    instance = app or QApplication.instance()
    if instance is None:
        return
    existing = instance.property("_youNewsClickFeel")
    if existing is not None:
        return
    filt = ClickFeelFilter(instance)
    instance.installEventFilter(filt)
    instance.setProperty("_youNewsClickFeel", filt)
