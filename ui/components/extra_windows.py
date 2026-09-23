"""About, first-run, mini tape, in-app reader, image lightbox, share."""

from __future__ import annotations

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from config import APP_CHANGELOG, APP_NAME, APP_VERSION, SUPPORTED_LANGUAGES, UI_LANGUAGES
from core.i18n_manager import I18nManager
from core.share import TARGETS, open_share, share_text
from core.source_packs import apply_source_pack
from database.db import Database
from database.models import Article
from ui.branding import apply_mascot
from ui.components.ticker_bar import TickerBar


class AboutDialog(QDialog):
    def __init__(self, i18n: I18nManager, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(i18n.t("app.about"))
        self.resize(520, 560)
        mascot = QLabel()
        mascot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if not apply_mascot(mascot, 128):
            mascot.hide()
        body = QTextBrowser()
        body.setOpenExternalLinks(True)
        body.setHtml(
            f"<h2>{APP_NAME} {APP_VERSION}</h2>"
            f"<p>{i18n.t('app.about_license')}</p>"
            f"{i18n.t('app.about_links')}"
            f"{i18n.t('app.disclaimer')}"
            f"<pre>{APP_CHANGELOG}</pre>"
        )
        close = QPushButton(i18n.t("app.close"))
        close.clicked.connect(self.accept)
        layout = QVBoxLayout(self)
        layout.addWidget(mascot)
        layout.addWidget(body, 1)
        layout.addWidget(close, 0, Qt.AlignmentFlag.AlignRight)


class FirstRunWizard(QDialog):
    """Language + optional starter pack before the desk is used."""

    def __init__(self, db: Database, i18n: I18nManager, parent=None) -> None:
        super().__init__(parent)
        self._db = db
        self._i18n = i18n
        self.pack_id: str | None = None
        self.setWindowTitle(i18n.t("app.wizard_title"))
        self.setMinimumWidth(520)
        self.resize(560, 520)
        mascot = QLabel()
        mascot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if not apply_mascot(mascot, 100):
            mascot.hide()
        body = QLabel(i18n.t("app.wizard_body"))
        body.setWordWrap(True)

        lang_label = QLabel(i18n.t("app.wizard_language"))
        self.language_combo = QComboBox()
        for code, name in UI_LANGUAGES.items():
            self.language_combo.addItem(name, code)
        if self.language_combo.findData(i18n.language) < 0 and i18n.language in SUPPORTED_LANGUAGES:
            self.language_combo.addItem(SUPPORTED_LANGUAGES[i18n.language], i18n.language)
        idx = self.language_combo.findData(i18n.language)
        if idx >= 0:
            self.language_combo.setCurrentIndex(idx)

        pack_box = QGroupBox(i18n.t("app.wizard_pack"))
        pack_layout = QVBoxLayout(pack_box)
        self.pack_none = QRadioButton(i18n.t("app.wizard_pack_none"))
        self.pack_tr = QRadioButton(i18n.t("app.wizard_pack_tr"))
        self.pack_us = QRadioButton(i18n.t("app.wizard_pack_us"))
        if i18n.language == "tr":
            self.pack_tr.setChecked(True)
        else:
            self.pack_us.setChecked(True)
        pack_layout.addWidget(self.pack_tr)
        pack_layout.addWidget(self.pack_us)
        pack_layout.addWidget(self.pack_none)

        notice = QLabel()
        notice.setWordWrap(True)
        notice.setTextFormat(Qt.TextFormat.RichText)
        notice.setText(i18n.t("app.disclaimer"))
        ok = QPushButton(i18n.t("app.wizard_continue"))
        ok.clicked.connect(self._finish)
        layout = QVBoxLayout(self)
        layout.addWidget(mascot)
        layout.addWidget(body)
        layout.addWidget(lang_label)
        layout.addWidget(self.language_combo)
        layout.addWidget(pack_box)
        layout.addWidget(notice, 1)
        layout.addWidget(ok, 0, Qt.AlignmentFlag.AlignRight)

    def _finish(self) -> None:
        code = self.language_combo.currentData()
        if code:
            self._i18n.load(str(code))
        if self.pack_tr.isChecked():
            self.pack_id = "tr"
        elif self.pack_us.isChecked():
            self.pack_id = "us"
        else:
            self.pack_id = None
        if self.pack_id:
            apply_source_pack(self._db, self.pack_id)
        self.accept()


class MiniTapeWindow(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent, Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.setWindowTitle(APP_NAME)
        self.resize(900, 100)
        self.ticker = TickerBar(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.ticker)


class ReaderDialog(QDialog):
    def __init__(self, title: str, url: str, i18n: I18nManager, parent=None) -> None:
        super().__init__(parent)
        self._i18n = i18n
        self._url = (url or "").strip()
        self.setWindowTitle(title or i18n.t("app.in_app_browser"))
        self.resize(860, 640)
        self.browser = QTextBrowser()
        self.browser.setOpenExternalLinks(True)
        self.browser.setHtml(f"<p>{i18n.t('app.reading')}</p>")
        open_btn = QPushButton(i18n.t("app.open_original"))
        open_btn.setObjectName("ghostButton")
        open_btn.clicked.connect(self._open_original)
        close = QPushButton(i18n.t("app.close"))
        close.clicked.connect(self.accept)
        row = QHBoxLayout()
        row.addWidget(open_btn)
        row.addStretch(1)
        row.addWidget(close)
        layout = QVBoxLayout(self)
        layout.addWidget(self.browser, 1)
        layout.addLayout(row)

    def set_html(self, html: str) -> None:
        self.browser.setHtml(html or f"<p>{self._i18n.t('app.read_failed')}</p>")

    def set_error(self, _message: str = "") -> None:
        self.browser.setHtml(f"<p>{self._i18n.t('app.read_failed')}</p>")

    def _open_original(self) -> None:
        if self._url.startswith("http"):
            QDesktopServices.openUrl(QUrl(self._url))


class LightboxDialog(QDialog):
    def __init__(self, image_path: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(APP_NAME)
        self.resize(800, 600)
        label = QLabel()
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pix = QPixmap(image_path)
        if not pix.isNull():
            label.setPixmap(
                pix.scaled(
                    760,
                    540,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        layout = QVBoxLayout(self)
        layout.addWidget(label)
        close = QPushButton("OK")
        close.clicked.connect(self.accept)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(close)
        layout.addLayout(row)


class ShareDialog(QDialog):
    def __init__(self, article: Article, i18n: I18nManager, parent=None) -> None:
        super().__init__(parent)
        self._article = article
        self._i18n = i18n
        self.setWindowTitle(i18n.t("share.title"))
        self.resize(520, 520)
        hint = QLabel(i18n.t("share.hint"))
        hint.setWordWrap(True)
        self.preview = QTextEdit()
        self.preview.setPlainText(share_text(article, i18n))
        self.status = QLabel("")
        self.status.setWordWrap(True)
        grid = QGridLayout()
        grid.setSpacing(8)
        for index, (target, key) in enumerate(TARGETS):
            button = QPushButton(i18n.t(key))
            if target == "copy":
                button.setObjectName("ghostButton")
            button.clicked.connect(lambda _checked=False, value=target: self._share(value))
            grid.addWidget(button, index // 2, index % 2)
        close = QPushButton(i18n.t("app.close"))
        close.setObjectName("ghostButton")
        close.clicked.connect(self.accept)
        layout = QVBoxLayout(self)
        layout.addWidget(hint)
        layout.addWidget(self.preview, 1)
        layout.addLayout(grid)
        layout.addWidget(self.status)
        layout.addWidget(close, 0, Qt.AlignmentFlag.AlignRight)

    def _share(self, target: str) -> None:
        text = self.preview.toPlainText().strip()
        if not text:
            text = share_text(self._article, self._i18n)
            self.preview.setPlainText(text)
        result = open_share(
            target,
            text,
            link=(self._article.link or "").strip(),
            title=(self._article.title or APP_NAME).strip(),
        )
        if result == "copied":
            self.status.setText(self._i18n.t("share.copied"))
        elif result == "opened":
            self.status.setText(self._i18n.t("share.opened"))
