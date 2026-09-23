"""JSON translation manager with live language switching and RTL layout."""

from __future__ import annotations

import json
from typing import Any

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import QApplication

from config import DEFAULT_LANGUAGE, LOCALES_DIR, SUPPORTED_LANGUAGES
from database.db import Database


class I18nManager(QObject):
    language_changed = Signal(str)

    def __init__(self, db: Database, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._db = db
        self._strings: dict[str, Any] = {}
        self._rtl = False
        self.language = DEFAULT_LANGUAGE
        saved = db.get_setting("language", DEFAULT_LANGUAGE) or DEFAULT_LANGUAGE
        self.load(saved, persist=False)

    def t(self, key: str, default: str | None = None) -> str:
        value = self._strings.get(key)
        if isinstance(value, str):
            return value
        return default if default is not None else key

    def native_name(self, code: str | None = None) -> str:
        code = code or self.language
        if code == self.language:
            return str(self._strings.get("meta.native_name") or SUPPORTED_LANGUAGES.get(code, code))
        return SUPPORTED_LANGUAGES.get(code, code)

    def english_name(self) -> str:
        return str(self._strings.get("meta.english_name") or "English")

    def is_rtl(self) -> bool:
        return self._rtl

    def load(self, language: str, persist: bool = True) -> None:
        code = language if language in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE
        path = LOCALES_DIR / f"{code}.json"
        fallback = LOCALES_DIR / f"{DEFAULT_LANGUAGE}.json"
        data: dict[str, Any] = {}
        if fallback.exists():
            data.update(_flatten(json.loads(fallback.read_text(encoding="utf-8"))))
        if path.exists():
            data.update(_flatten(json.loads(path.read_text(encoding="utf-8"))))
        self._strings = data
        self._rtl = str(data.get("meta.rtl", data.get("rtl"))).lower() in {"true", "1"}
        self.language = code
        if persist:
            self._db.set_setting("language", code)
        self._apply_layout_direction()
        self.language_changed.emit(code)

    def _apply_layout_direction(self) -> None:
        app = QApplication.instance()
        if app is None:
            return
        direction = Qt.LayoutDirection.RightToLeft if self._rtl else Qt.LayoutDirection.LeftToRight
        app.setLayoutDirection(direction)


def _flatten(payload: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    flat: dict[str, Any] = {}
    for key, value in payload.items():
        path = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, dict):
            flat.update(_flatten(value, path))
        else:
            flat[path] = value
    return flat
