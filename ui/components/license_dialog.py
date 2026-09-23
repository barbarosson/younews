"""Activation prompt shown before the main window when a license is required."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QDesktopServices, QUrl
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from config import APP_PROMO_URL
from core.i18n_manager import I18nManager
from core.license import LicenseError, activate
from ui.branding import apply_mascot

_SUPPORT_MAIL = "mailto:hello@younews.media"
_SITE = (APP_PROMO_URL or "https://younews.media").rstrip("/")


class LicenseDialog(QDialog):
    def __init__(self, i18n: I18nManager, parent=None) -> None:
        super().__init__(parent)
        self._i18n = i18n
        self._ok = False
        self.setWindowTitle(i18n.t("license.title"))
        self.setModal(True)
        self.setMinimumWidth(480)
        mascot = QLabel()
        mascot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if not apply_mascot(mascot, 96):
            mascot.hide()
        heading = QLabel(i18n.t("license.heading"))
        heading.setWordWrap(True)
        body = QLabel(i18n.t("license.body"))
        body.setWordWrap(True)
        self.key_edit = QLineEdit()
        self.key_edit.setPlaceholderText(i18n.t("license.placeholder"))
        self.key_edit.returnPressed.connect(self._activate)
        links = QLabel(
            f'<a href="{_SITE}">{i18n.t("license.link_site")}</a>'
            f' · <a href="{_SITE}/contact.html">{i18n.t("license.link_help")}</a>'
            f' · <a href="{_SUPPORT_MAIL}">{i18n.t("license.link_email")}</a>'
        )
        links.setOpenExternalLinks(True)
        links.setWordWrap(True)
        links.setTextFormat(Qt.TextFormat.RichText)
        activate_btn = QPushButton(i18n.t("license.activate"))
        activate_btn.clicked.connect(self._activate)
        buy_btn = QPushButton(i18n.t("license.buy"))
        buy_btn.setObjectName("ghostButton")
        buy_btn.clicked.connect(self._open_buy)
        quit_btn = QPushButton(i18n.t("license.quit"))
        quit_btn.setObjectName("ghostButton")
        quit_btn.clicked.connect(self.reject)
        row = QHBoxLayout()
        row.addWidget(buy_btn)
        row.addStretch(1)
        row.addWidget(quit_btn)
        row.addWidget(activate_btn)
        layout = QVBoxLayout(self)
        layout.addWidget(mascot)
        layout.addWidget(heading)
        layout.addWidget(body)
        layout.addWidget(self.key_edit)
        layout.addWidget(links)
        layout.addLayout(row)

    def closeEvent(self, event) -> None:  # noqa: N802
        if self._ok:
            event.accept()
            return
        event.ignore()
        self.reject()

    def _open_buy(self) -> None:
        QDesktopServices.openUrl(QUrl(_SITE + "/#price"))

    def _activate(self) -> None:
        text = self.key_edit.text()
        if not text.strip():
            QMessageBox.warning(self, self._i18n.t("license.title"), self._i18n.t("license.empty"))
            return
        try:
            activate(text)
        except LicenseError as exc:
            key = str(exc)
            if key == "expired":
                msg = self._i18n.t("license.expired")
            elif key == "other_pc":
                msg = self._i18n.t("license.other_pc")
            else:
                msg = self._i18n.t("license.invalid")
            QMessageBox.warning(self, self._i18n.t("license.title"), msg)
            return
        self._ok = True
        self.accept()
