"""Global News Terminal entry point."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PySide6.QtWidgets import QApplication, QMessageBox

from config import APP_NAME, APP_ORG, DEFAULT_THEME
from core.app_extras import acquire_single_instance, apply_proxy_setting, setup_logging
from core.i18n_manager import I18nManager
from database.db import Database
from ui.branding import app_icon
from ui.main_window import MainWindow
from ui.theme import apply_app_theme


def main() -> int:
    setup_logging()
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_ORG)
    lock = acquire_single_instance()
    if lock is None:
        QMessageBox.information(None, APP_NAME, "You News is already running.")
        return 0
    icon = app_icon()
    if not icon.isNull():
        app.setWindowIcon(icon)

    db = Database()
    apply_proxy_setting(db.get_setting("proxy_url") or "")
    apply_app_theme(db.get_setting("theme", DEFAULT_THEME), font_scale=int(db.get_setting("ui_font_scale") or 100))
    i18n = I18nManager(db)
    from core.license import is_activated, license_gate_required

    if license_gate_required() and not is_activated():
        from ui.components.license_dialog import LicenseDialog

        dialog = LicenseDialog(i18n)
        if dialog.exec() != LicenseDialog.DialogCode.Accepted or not is_activated():
            lock.unlock()
            return 1
    window = MainWindow(db, i18n)
    window.show()
    code = app.exec()
    lock.unlock()
    return code


if __name__ == "__main__":
    raise SystemExit(main())
