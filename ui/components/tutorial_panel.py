"""In-app tutorials for the main You News workflows."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from core.i18n_manager import I18nManager

TUTORIALS: tuple[tuple[str, str | None], ...] = (
    ("start", None),
    ("headings", None),
    ("sources", "sources"),
    ("filters", "filters"),
    ("social", "social"),
    ("tickers", "tickers"),
    ("save", None),
    ("ai", None),
    ("listen", None),
    ("chat", None),
)


class TutorialPanel(QWidget):
    open_settings_requested = Signal(str)

    def __init__(self, i18n: I18nManager, parent=None) -> None:
        super().__init__(parent)
        self._i18n = i18n
        self.topic_list = QListWidget()
        self.topic_list.setObjectName("tutorialList")
        self.topic_list.setMaximumWidth(220)
        self.body = QTextBrowser()
        self.body.setOpenExternalLinks(False)
        self.open_btn = QPushButton()
        self.open_btn.setObjectName("ghostButton")
        self.open_btn.hide()

        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.addWidget(self.body, 1)
        right.addWidget(self.open_btn, 0, Qt.AlignmentFlag.AlignLeft)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.topic_list)
        layout.addLayout(right, 1)

        self.topic_list.currentRowChanged.connect(self._show_topic)
        self.open_btn.clicked.connect(self._open_settings)
        self.retranslate()

    def retranslate(self) -> None:
        row = self.topic_list.currentRow()
        self.topic_list.blockSignals(True)
        self.topic_list.clear()
        for key, _tab in TUTORIALS:
            item = QListWidgetItem(self._i18n.t(f"tutorial.{key}.title"))
            item.setData(Qt.ItemDataRole.UserRole, key)
            self.topic_list.addItem(item)
        self.topic_list.blockSignals(False)
        if 0 <= row < self.topic_list.count():
            self.topic_list.setCurrentRow(row)
        elif self.topic_list.count():
            self.topic_list.setCurrentRow(0)
        self.open_btn.setText(self._i18n.t("tutorial.open_settings"))
        self._show_topic(self.topic_list.currentRow())

    def show_topic(self, key: str) -> None:
        for row in range(self.topic_list.count()):
            item = self.topic_list.item(row)
            if item and item.data(Qt.ItemDataRole.UserRole) == key:
                self.topic_list.setCurrentRow(row)
                return

    def _current_key(self) -> str:
        item = self.topic_list.currentItem()
        if item is None:
            return TUTORIALS[0][0]
        return str(item.data(Qt.ItemDataRole.UserRole) or TUTORIALS[0][0])

    def _show_topic(self, _row: int) -> None:
        key = self._current_key()
        title = self._i18n.t(f"tutorial.{key}.title")
        body = self._i18n.t(f"tutorial.{key}.body")
        self.body.setHtml(f"<h2>{title}</h2>{body}")
        tab = dict(TUTORIALS).get(key)
        self.open_btn.setVisible(bool(tab))

    def _open_settings(self) -> None:
        tab = dict(TUTORIALS).get(self._current_key())
        if tab:
            self.open_settings_requested.emit(tab)


class TutorialDialog(QDialog):
    open_settings_requested = Signal(str)

    def __init__(self, i18n: I18nManager, parent=None, topic: str | None = None) -> None:
        super().__init__(parent)
        self._i18n = i18n
        self.setModal(True)
        self.resize(760, 560)
        self.panel = TutorialPanel(i18n, self)
        self.close_btn = QPushButton()
        self.close_btn.setObjectName("ghostButton")
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(self.close_btn)
        layout = QVBoxLayout(self)
        layout.addWidget(self.panel, 1)
        layout.addLayout(buttons)
        self.close_btn.clicked.connect(self.accept)
        self.panel.open_settings_requested.connect(self.open_settings_requested)
        self.retranslate()
        if topic:
            self.panel.show_topic(topic)

    def retranslate(self) -> None:
        self.setWindowTitle(self._i18n.t("tutorial.title"))
        self.close_btn.setText(self._i18n.t("app.close"))
        self.panel.retranslate()
