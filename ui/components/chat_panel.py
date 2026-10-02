from __future__ import annotations

from html import escape

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from config import DEFAULT_THEME, normalize_theme
from core.i18n_manager import I18nManager

ROLE_USER = "user"
ROLE_ASSISTANT = "assistant"


class ChatPanel(QFrame):
    message_submitted = Signal(str)
    article_requested = Signal(int)
    url_requested = Signal(str)
    cleared = Signal()

    def __init__(self, i18n: I18nManager, parent=None, db=None) -> None:
        super().__init__(parent)
        self.setObjectName("chatPanel")
        self._i18n = i18n
        self._db = db
        self._history: list[dict[str, str]] = []
        self._busy = False
        self._theme = normalize_theme(db.get_setting("theme", DEFAULT_THEME) if db else DEFAULT_THEME)

        self.title_label = QLabel()
        self.title_label.setObjectName("paneTitle")
        self.hint_label = QLabel()
        self.hint_label.setObjectName("chatHint")
        self.hint_label.setWordWrap(True)
        self.log = QTextBrowser()
        self.log.setObjectName("chatLog")
        self.log.setOpenExternalLinks(False)
        self.log.setOpenLinks(False)
        self.input = QLineEdit()
        self.send_btn = QPushButton()
        self.clear_btn = QPushButton()
        self.clear_btn.setObjectName("ghostButton")
        self.suggestions = QWidget()
        self.suggestions_layout = QVBoxLayout(self.suggestions)
        self.suggestions_layout.setContentsMargins(0, 0, 0, 0)
        self.suggestions_layout.setSpacing(4)

        row = QHBoxLayout()
        row.addWidget(self.input, 1)
        row.addWidget(self.send_btn)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.addWidget(self.title_label)
        layout.addWidget(self.hint_label)
        layout.addWidget(self.log, 1)
        layout.addWidget(self.suggestions)
        layout.addLayout(row)
        layout.addWidget(self.clear_btn, 0, Qt.AlignmentFlag.AlignLeft)

        self.send_btn.clicked.connect(self._submit)
        self.input.returnPressed.connect(self._submit)
        self.clear_btn.clicked.connect(self.reset)
        self.log.anchorClicked.connect(self._on_anchor)
        self.retranslate()
        stored = self._db.list_chat_messages() if self._db else []
        if stored:
            self._history = stored
            self._render()
            self.offer_desk_help()
        else:
            self.reset()

    def history(self) -> list[dict[str, str]]:
        return list(self._history)

    def retranslate(self) -> None:
        self.title_label.setText(self._i18n.t("chat.title"))
        self.hint_label.setText(self._i18n.t("chat.hint"))
        self.input.setPlaceholderText(self._i18n.t("chat.placeholder"))
        self.send_btn.setText(self._i18n.t("chat.send"))
        self.clear_btn.setText(self._i18n.t("chat.clear"))
        if not self._history:
            self._render()

    def set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.send_btn.setEnabled(not busy)
        self.input.setEnabled(not busy)
        self.send_btn.setText(self._i18n.t("chat.thinking") if busy else self._i18n.t("chat.send"))

    def reset(self) -> None:
        self._history = []
        if self._db:
            self._db.clear_chat_messages()
        self._render()
        self.offer_desk_help()
        self.cleared.emit()

    def offer_desk_help(self) -> None:
        self.set_suggestions(
            [
                self._i18n.t("chat.suggest_pack"),
                self._i18n.t("chat.suggest_topic"),
                self._i18n.t("chat.suggest_social"),
                self._i18n.t("chat.suggest_tickers"),
            ]
        )

    def append_user(self, text: str) -> None:
        self._history.append({"role": ROLE_USER, "text": text})
        if self._db:
            self._db.append_chat_message(ROLE_USER, text)
        self._render()

    def append_assistant(self, text: str, article_links: list[tuple[int, str]] | None = None) -> None:
        payload = text
        if article_links:
            lines = [text, "", self._i18n.t("chat.stories")]
            for article_id, title in article_links:
                lines.append(f"- [{title}](younews://article/{article_id})")
            payload = "\n".join(lines)
        self._history.append({"role": ROLE_ASSISTANT, "text": payload})
        if self._db:
            self._db.append_chat_message(ROLE_ASSISTANT, payload)
        self._render()

    def set_suggestions(self, items: list[str]) -> None:
        while self.suggestions_layout.count():
            item = self.suggestions_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self._suggestion_buttons = []
        for text in items[:4]:
            button = QPushButton(text)
            button.setObjectName("ghostButton")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setToolTip(text)
            button.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
            button.clicked.connect(lambda _checked=False, value=text: self._use_suggestion(value))
            self.suggestions_layout.addWidget(button)
            self._suggestion_buttons.append((button, text))
        self._elide_suggestions()

    def _elide_suggestions(self) -> None:
        for button, text in getattr(self, "_suggestion_buttons", []):
            room = max(40, self.width() - 52)
            button.setText(button.fontMetrics().elidedText(text, Qt.TextElideMode.ElideRight, room))

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._elide_suggestions()

    def set_theme(self, theme: str | None) -> None:
        self._theme = normalize_theme(theme)
        self._render()

    def _use_suggestion(self, text: str) -> None:
        if self._busy:
            return
        self.input.setText(text)
        self._submit()

    def _submit(self) -> None:
        if self._busy:
            return
        text = self.input.text().strip()
        if not text:
            return
        self.input.clear()
        self.append_user(text)
        self.message_submitted.emit(text)

    def _on_anchor(self, url: QUrl) -> None:
        href = url.toString()
        if href.startswith("younews://article/"):
            try:
                self.article_requested.emit(int(href.rsplit("/", 1)[-1]))
            except ValueError:
                return
            return
        if href.startswith("http://") or href.startswith("https://"):
            self.url_requested.emit(href)
            QDesktopServices.openUrl(url)

    def _render(self) -> None:
        if not self._history:
            html = (
                f"<p class='welcome'><b>{escape(self._i18n.t('chat.welcome'))}</b></p>"
                f"<p>{escape(self._i18n.t('chat.welcome_body'))}</p>"
            )
            self.log.setHtml(self._wrap(html))
            return
        chunks: list[str] = []
        for item in self._history:
            css = "user" if item["role"] == ROLE_USER else "bot"
            label = self._i18n.t("chat.you") if item["role"] == ROLE_USER else self._i18n.t("chat.bot")
            chunks.append(
                f"<div class='{css}'><div class='who'>{escape(label)}</div>"
                f"<div class='msg'>{_format_body(item['text'])}</div></div>"
            )
        self.log.setHtml(self._wrap("".join(chunks)))
        self.log.verticalScrollBar().setValue(self.log.verticalScrollBar().maximum())

    def _wrap(self, inner: str) -> str:
        light = self._theme == "light"
        if light:
            text, user_bg, bot_bg, link = "#1f2328", "#dbeafe", "#ffffff", "#0969da"
        else:
            text, user_bg, bot_bg, link = "#e6edf3", "#1d2d44", "#182433", "#58a6ff"
        return (
            "<html><head><style>"
            f"body{{font-family:'Segoe UI';font-size:13px;color:{text};}}"
            ".welcome{margin:8px 0;}"
            f".user,.bot{{margin:0 0 12px 0;padding:8px 10px;border-radius:10px;color:{text};}}"
            f".user{{background:{user_bg};}}"
            f".bot{{background:{bot_bg};}}"
            ".who{font-size:11px;opacity:.7;margin-bottom:4px;font-weight:700;}"
            f"a{{color:{link};}}"
            "</style></head><body>"
            f"{inner}</body></html>"
        )


def _format_body(text: str) -> str:
    lines = []
    for raw in (text or "").splitlines():
        stripped = raw.strip()
        if stripped.startswith("- "):
            stripped = stripped[2:]
        match = re_link(stripped)
        if match:
            title, href = match
            if href.startswith("younews://") or href.startswith("http"):
                lines.append(f"• <a href='{escape(href, quote=True)}'>{escape(title)}</a>")
                continue
        lines.append(escape(stripped) if stripped else "<br>")
    return "<br>".join(lines)


def re_link(line: str) -> tuple[str, str] | None:
    if line.startswith("[") and "](" in line and line.endswith(")"):
        title, _, rest = line[1:].partition("](")
        href = rest[:-1]
        if title and href:
            return title, href
    return None
