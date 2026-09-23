"""You News mark, mascot, and window icon."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QLabel

from config import APP_ICON_ICO, APP_ICON_PNG, APP_MASCOT_MARK_PNG, APP_MASCOT_PNG, APP_WORDMARK_PNG


def app_icon() -> QIcon:
    if APP_ICON_ICO.is_file():
        return QIcon(str(APP_ICON_ICO))
    if APP_ICON_PNG.is_file():
        return QIcon(str(APP_ICON_PNG))
    return QIcon()


def _load(path: Path) -> QPixmap | None:
    if not path.is_file():
        return None
    pixmap = QPixmap(str(path))
    return None if pixmap.isNull() else pixmap


def apply_scaled(label: QLabel, path: Path, *, height: int | None = None, width: int | None = None) -> bool:
    pixmap = _load(path)
    if pixmap is None:
        return False
    if height and pixmap.height():
        scaled = pixmap.scaledToHeight(height, Qt.TransformationMode.SmoothTransformation)
    elif width and pixmap.width():
        scaled = pixmap.scaledToWidth(width, Qt.TransformationMode.SmoothTransformation)
    else:
        scaled = pixmap
    label.setPixmap(scaled)
    return True


def apply_mascot(label: QLabel, height: int = 108) -> bool:
    return apply_scaled(label, APP_MASCOT_PNG, height=max(72, min(height, 160)))


def apply_mascot_mark(label: QLabel, size: int = 40) -> bool:
    path = APP_MASCOT_MARK_PNG if APP_MASCOT_MARK_PNG.is_file() else APP_MASCOT_PNG
    pixmap = _load(path)
    if pixmap is None:
        return False
    scaled = pixmap.scaled(
        size,
        size,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )
    label.setPixmap(scaled)
    return True


def apply_wordmark(label: QLabel, width: int) -> bool:
    path = APP_WORDMARK_PNG if APP_WORDMARK_PNG.is_file() else APP_ICON_PNG
    if not path.is_file():
        return False
    pixmap = QPixmap(str(path))
    if pixmap.isNull():
        return False
    target = max(168, min(width, 240))
    if pixmap.width() >= pixmap.height():
        scaled = pixmap.scaledToWidth(target, Qt.TransformationMode.SmoothTransformation)
        if scaled.height() > 150:
            scaled = pixmap.scaledToHeight(150, Qt.TransformationMode.SmoothTransformation)
    else:
        size = min(132, target)
        scaled = pixmap.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
    label.setPixmap(scaled)
    return True
