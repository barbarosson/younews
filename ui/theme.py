"""Apply Global News Terminal QSS themes at runtime."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication

from config import load_theme_stylesheet, parse_font_scale, resolve_theme
from ui.click_feel import install_click_feel


def apply_app_theme(theme: str | None, font_scale: int | None = None) -> str:
    resolved = resolve_theme(theme)
    app = QApplication.instance()
    if app is not None:
        install_click_feel(app)
        app.setStyleSheet(load_theme_stylesheet(resolved))
        if font_scale:
            font = app.font()
            point = max(8, int(round(10 * (parse_font_scale(str(font_scale)) / 100))))
            font.setPointSize(point)
            app.setFont(font)
    return resolved
