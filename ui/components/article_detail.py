from __future__ import annotations

import json
from html import escape

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from config import ARTICLE_EMOJIS
from core.i18n_manager import I18nManager
from core.speech_engine import SpeechEngine, plain_text
from database.models import Article
from ui.components.news_avatar import NewsAvatar

SENTIMENT_OBJECTS = {
    "bullish/positive": "sentimentBullish",
    "bearish/negative": "sentimentBearish",
    "neutral": "sentimentNeutral",
}

_COMPACT_H = 28
_NOTE_OPEN_H = 72


class CompactNoteEdit(QPlainTextEdit):
    """One-line until focused, then expands for typing."""

    editing_finished = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("compactNote")
        self.setTabChangesFocus(True)
        self.setFixedHeight(_COMPACT_H)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.document().setDocumentMargin(2)

    def focusInEvent(self, event) -> None:  # noqa: N802
        super().focusInEvent(event)
        self.setFixedHeight(_NOTE_OPEN_H)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

    def focusOutEvent(self, event) -> None:  # noqa: N802
        super().focusOutEvent(event)
        self.setFixedHeight(_COMPACT_H)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.editing_finished.emit()


class ArticleDetail(QFrame):
    summarize_requested = Signal(int)
    translate_requested = Signal(int)
    save_toggled = Signal(int, bool)
    emoji_selected = Signal(int, str)
    narrator_gender_changed = Signal(str)
    fulltext_requested = Signal(int)
    export_requested = Signal(int)
    copy_link_requested = Signal(str)
    share_requested = Signal()
    print_requested = Signal(int)
    pdf_requested = Signal(int)
    browser_requested = Signal(int)
    lightbox_requested = Signal(str)
    note_changed = Signal(int, str)
    tags_changed = Signal(int, str)
    folder_changed = Signal(int, str)

    def __init__(self, i18n: I18nManager, parent=None) -> None:
        super().__init__(parent)
        self._i18n = i18n
        self._article: Article | None = None
        self._briefing: dict | None = None
        self._showing_translation = False
        self._busy_mode = ""
        self._speech = SpeechEngine(self)
        self._speech.speaking_changed.connect(self._on_speaking)

        self.title_label = QLabel()
        self.title_label.setObjectName("detailTitle")
        self.title_label.setWordWrap(True)
        self.meta_label = QLabel()
        self.sentiment_badge = QLabel()
        self.sentiment_badge.setVisible(False)
        self.summarize_btn = QPushButton()
        self.translate_btn = QPushButton()
        self.translate_btn.setObjectName("ghostButton")
        self.fulltext_btn = QPushButton()
        self.fulltext_btn.setObjectName("ghostButton")
        self.export_btn = QPushButton()
        self.export_btn.setObjectName("ghostButton")
        self.copy_btn = QPushButton()
        self.copy_btn.setObjectName("ghostButton")
        self.share_btn = QPushButton()
        self.share_btn.setObjectName("ghostButton")
        self.print_btn = QPushButton()
        self.print_btn.setObjectName("ghostButton")
        self.pdf_btn = QPushButton()
        self.pdf_btn.setObjectName("ghostButton")
        self.browser_btn = QPushButton()
        self.browser_btn.setObjectName("ghostButton")
        self.photo_btn = QPushButton()
        self.photo_btn.setObjectName("ghostButton")
        self.folder_edit = QLineEdit()
        self.folder_edit.setObjectName("compactMeta")
        self.folder_edit.setFixedHeight(_COMPACT_H)
        self.folder_edit.setClearButtonEnabled(True)
        self.tags_edit = QLineEdit()
        self.tags_edit.setObjectName("compactMeta")
        self.tags_edit.setFixedHeight(_COMPACT_H)
        self.tags_edit.setClearButtonEnabled(True)
        self.note_edit = CompactNoteEdit()
        self.meta_fields = QWidget()
        self.meta_fields.setObjectName("compactMetaRow")
        meta_row = QHBoxLayout(self.meta_fields)
        meta_row.setContentsMargins(0, 0, 0, 0)
        meta_row.setSpacing(6)
        meta_row.addWidget(self.folder_edit, 1)
        meta_row.addWidget(self.tags_edit, 2)
        meta_row.addWidget(self.note_edit, 3)
        self.avatar = NewsAvatar()
        self.voice_female = QPushButton()
        self.voice_female.setObjectName("ghostButton")
        self.voice_female.setCheckable(True)
        self.voice_male = QPushButton()
        self.voice_male.setObjectName("ghostButton")
        self.voice_male.setCheckable(True)
        self.narrate_btn = QPushButton()
        self.narrate_btn.setObjectName("ghostButton")
        self.narrator_bar = QWidget()
        narrator_row = QHBoxLayout(self.narrator_bar)
        narrator_row.setContentsMargins(0, 0, 0, 0)
        narrator_row.setSpacing(8)
        narrator_row.addWidget(self.avatar)
        narrator_row.addWidget(self.voice_female)
        narrator_row.addWidget(self.voice_male)
        narrator_row.addWidget(self.narrate_btn)
        narrator_row.addStretch(1)
        self.save_btn = QPushButton()
        self.save_btn.setObjectName("saveButton")
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.emoji_hint = QLabel()
        self.emoji_hint.setObjectName("saveHint")
        self.emoji_bar = QWidget()
        emoji_row = QHBoxLayout(self.emoji_bar)
        emoji_row.setContentsMargins(0, 0, 0, 0)
        emoji_row.setSpacing(4)
        self._emoji_buttons: list[QPushButton] = []
        for mark in ARTICLE_EMOJIS:
            button = QPushButton(mark)
            button.setObjectName("emojiButton")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setFixedWidth(36)
            button.clicked.connect(lambda _checked=False, value=mark: self._on_emoji_clicked(value))
            emoji_row.addWidget(button)
            self._emoji_buttons.append(button)
        emoji_row.addStretch(1)
        self.save_panel = QFrame()
        self.save_panel.setObjectName("savePanel")
        save_layout = QVBoxLayout(self.save_panel)
        save_layout.setContentsMargins(10, 10, 10, 10)
        save_layout.setSpacing(8)
        save_row = QHBoxLayout()
        save_row.setContentsMargins(0, 0, 0, 0)
        save_row.addWidget(self.save_btn)
        save_row.addStretch(1)
        save_layout.addLayout(save_row)
        save_layout.addWidget(self.emoji_hint)
        save_layout.addWidget(self.emoji_bar)
        self.body = QTextBrowser()
        self.body.setOpenExternalLinks(True)
        self.placeholder = QLabel()
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)

        header = QHBoxLayout()
        header.setSpacing(6)
        header.addWidget(self.sentiment_badge)
        header.addStretch(1)
        header.addWidget(self.translate_btn)
        header.addWidget(self.fulltext_btn)
        header.addWidget(self.summarize_btn)
        tools = QHBoxLayout()
        tools.setSpacing(6)
        tools.addWidget(self.export_btn)
        tools.addWidget(self.copy_btn)
        tools.addWidget(self.share_btn)
        tools.addWidget(self.print_btn)
        tools.addWidget(self.pdf_btn)
        tools.addWidget(self.browser_btn)
        tools.addWidget(self.photo_btn)
        tools.addStretch(1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.addWidget(self.placeholder)
        layout.addWidget(self.title_label)
        layout.addWidget(self.meta_label)
        layout.addLayout(header)
        layout.addLayout(tools)
        layout.addWidget(self.narrator_bar)
        layout.addWidget(self.save_panel)
        layout.addWidget(self.meta_fields)
        layout.addWidget(self.body, 1)

        self.summarize_btn.clicked.connect(self._emit_summarize)
        self.translate_btn.clicked.connect(self._on_translate_clicked)
        self.fulltext_btn.clicked.connect(self._emit_fulltext)
        self.export_btn.clicked.connect(self._emit_export)
        self.copy_btn.clicked.connect(self._emit_copy)
        self.share_btn.clicked.connect(self._emit_share)
        self.print_btn.clicked.connect(self._emit_print)
        self.pdf_btn.clicked.connect(self._emit_pdf)
        self.browser_btn.clicked.connect(self._emit_browser)
        self.photo_btn.clicked.connect(self._emit_photo)
        self.note_edit.editing_finished.connect(self._emit_note)
        self.tags_edit.editingFinished.connect(self._emit_tags)
        self.folder_edit.editingFinished.connect(self._emit_folder)
        self.save_btn.clicked.connect(self._on_save_clicked)
        self.voice_female.clicked.connect(lambda: self.set_narrator_gender("female", persist=True))
        self.voice_male.clicked.connect(lambda: self.set_narrator_gender("male", persist=True))
        self.narrate_btn.clicked.connect(self._on_narrate)
        self.set_narrator_gender("female", persist=False)
        self.show_empty()
        self.retranslate()

    def retranslate(self) -> None:
        self.summarize_btn.setText(self._i18n.t("app.summarize"))
        self.fulltext_btn.setText(self._i18n.t("app.full_text"))
        self.export_btn.setText(self._i18n.t("app.export_md"))
        self.copy_btn.setText(self._i18n.t("app.copy_link"))
        self.share_btn.setText(self._i18n.t("share.title"))
        self.print_btn.setText(self._i18n.t("app.print"))
        self.pdf_btn.setText(self._i18n.t("app.pdf"))
        self.browser_btn.setText(self._i18n.t("app.in_app_browser"))
        self.photo_btn.setText(self._i18n.t("app.lightbox"))
        self.folder_edit.setPlaceholderText(self._i18n.t("app.folder_hint"))
        self.tags_edit.setPlaceholderText(self._i18n.t("app.tags_hint"))
        self.note_edit.setPlaceholderText(self._i18n.t("app.note_hint"))
        self.folder_edit.setToolTip(self._i18n.t("app.folder"))
        self.tags_edit.setToolTip(self._i18n.t("app.tags"))
        self.note_edit.setToolTip(self._i18n.t("app.note"))
        self.placeholder.setText(self._i18n.t("app.no_article"))
        self.emoji_hint.setText(self._i18n.t("app.emoji_hint"))
        self.voice_female.setText(self._i18n.t("ai.voice_female"))
        self.voice_male.setText(self._i18n.t("ai.voice_male"))
        self._refresh_narrate_button()
        self._speech.set_language(self._i18n.language)
        self._refresh_save_button()
        if self._briefing:
            self.show_briefing(self._briefing)
        elif self._article:
            if not self._translation_for_current_language():
                self._showing_translation = False
            self._render_article()
        else:
            self._refresh_translate_button()

    def show_empty(self) -> None:
        self._article = None
        self._briefing = None
        self._showing_translation = False
        self.placeholder.setVisible(True)
        self.title_label.setVisible(False)
        self.meta_label.setVisible(False)
        self.summarize_btn.setVisible(False)
        self.translate_btn.setVisible(False)
        self.fulltext_btn.setVisible(False)
        self.export_btn.setVisible(False)
        self.copy_btn.setVisible(False)
        self.share_btn.setVisible(False)
        self.print_btn.setVisible(False)
        self.pdf_btn.setVisible(False)
        self.browser_btn.setVisible(False)
        self.photo_btn.setVisible(False)
        self.meta_fields.setVisible(False)
        self.save_panel.setVisible(False)
        self.narrator_bar.setVisible(False)
        self.sentiment_badge.setVisible(False)
        self.body.setVisible(False)
        self._speech.stop()

    def show_article(self, article: Article, *, show_translation: bool | None = None) -> None:
        same = self._article is not None and self._article.id == article.id
        if not same:
            self._speech.stop()
        self._briefing = None
        self._article = article
        self.placeholder.setVisible(False)
        self.title_label.setVisible(True)
        self.meta_label.setVisible(True)
        self.summarize_btn.setVisible(True)
        self.translate_btn.setVisible(True)
        self.fulltext_btn.setVisible(True)
        self.export_btn.setVisible(True)
        self.copy_btn.setVisible(True)
        self.share_btn.setVisible(True)
        self.print_btn.setVisible(True)
        self.pdf_btn.setVisible(True)
        self.browser_btn.setVisible(True)
        self.photo_btn.setVisible(True)
        self.meta_fields.setVisible(True)
        self.save_panel.setVisible(True)
        self.narrator_bar.setVisible(True)
        self.body.setVisible(True)
        has_current = self._translation_for_current_language() is not None
        if show_translation is not None:
            self._showing_translation = bool(show_translation) and has_current
        elif not same:
            self._showing_translation = has_current
        elif not has_current:
            self._showing_translation = False
        self._render_article()

    def show_briefing(self, payload: dict) -> None:
        self._speech.stop()
        self._article = None
        self._briefing = payload
        self._showing_translation = False
        self.placeholder.setVisible(False)
        self.title_label.setVisible(True)
        self.meta_label.setVisible(True)
        self.summarize_btn.setVisible(False)
        self.translate_btn.setVisible(False)
        self.fulltext_btn.setVisible(False)
        self.export_btn.setVisible(False)
        self.copy_btn.setVisible(False)
        self.share_btn.setVisible(True)
        self.print_btn.setVisible(False)
        self.pdf_btn.setVisible(False)
        self.browser_btn.setVisible(False)
        self.photo_btn.setVisible(False)
        self.meta_fields.setVisible(False)
        self.save_panel.setVisible(False)
        self.narrator_bar.setVisible(True)
        self.body.setVisible(True)
        hours = int(payload.get("hours") or 0)
        count = int(payload.get("count") or 0)
        module_name = str(payload.get("module_name") or "")
        if payload.get("selected"):
            title = self._i18n.t("ai.briefing_selected_title").replace("{count}", str(count))
        else:
            title = (
                self._i18n.t("ai.briefing_title")
                .replace("{hours}", str(hours))
                .replace("{module}", module_name)
            )
        self.title_label.setText(title)
        self.meta_label.setText(self._i18n.t("ai.brief_count").replace("{count}", str(count)))
        summary = escape(str(payload.get("summary") or "")).replace("\n", "<br>")
        takeaways = payload.get("takeaways") or []
        bullets = "".join(f"<li>{escape(str(item))}</li>" for item in takeaways)
        takeaway_html = (
            f"<h3>{self._i18n.t('ai.takeaways')}</h3><ul>{bullets}</ul>" if bullets else ""
        )
        headlines = payload.get("headlines") or []
        covered = "".join(self._covered_item_html(item) for item in headlines)
        covered_html = (
            f"<h3>{self._i18n.t('ai.covered')}</h3><ul>{covered}</ul>" if covered else ""
        )
        self.body.setHtml(
            f"<h3>{self._i18n.t('ai.summary')}</h3><p>{summary}</p>{takeaway_html}{covered_html}"
        )
        self._render_sentiment(payload.get("sentiment"))
        self._refresh_narrate_button()

    def set_busy(self, busy: bool, mode: str = "") -> None:
        self._busy_mode = mode if busy else ""
        self.summarize_btn.setEnabled(not busy)
        self.translate_btn.setEnabled(not busy)
        if busy and mode == "translate":
            self.translate_btn.setText(self._i18n.t("ai.translating"))
            self.summarize_btn.setText(self._i18n.t("app.summarize"))
        elif busy:
            self.summarize_btn.setText(self._i18n.t("ai.summarizing"))
            self._refresh_translate_button()
        else:
            self.summarize_btn.setText(self._i18n.t("app.summarize"))
            self._refresh_translate_button()

    def _render_article(self) -> None:
        article = self._article
        if article is None:
            return
        translated = self._translation_for_current_language() if self._showing_translation else None
        title = translated[0] if translated else article.title
        content = (translated[1] if translated else "") or (article.content or "")
        self.title_label.setText(title)
        source = article.source_name or self._i18n.t("app.source")
        when = article.pub_date.strftime("%Y-%m-%d %H:%M") if article.pub_date else ""
        self.meta_label.setText(f"{source}  ·  {when}")
        html_parts = []
        if article.ai_summary:
            html_parts.append(
                f"<h3>{self._i18n.t('ai.summary')}</h3><p>{escape(article.ai_summary)}</p>"
            )
        if content:
            from core.app_extras import looks_like_paywall, sanitize_article_html

            if looks_like_paywall(content):
                html_parts.append(f"<p><em>{self._i18n.t('app.paywall')}</em></p>")
            html_parts.append(sanitize_article_html(content))
        if article.link:
            html_parts.append(f'<p><a href="{escape(article.link, quote=True)}">{escape(article.link)}</a></p>')
        self.body.setHtml("".join(html_parts) or "")
        self._render_sentiment(article.sentiment, article.module_id)
        self._refresh_save_button()
        self._refresh_emoji_buttons()
        self.note_edit.blockSignals(True)
        self.note_edit.setPlainText(article.note or "")
        self.note_edit.blockSignals(False)
        if not self.note_edit.hasFocus():
            self.note_edit.setFixedHeight(_COMPACT_H)
        self.tags_edit.setText(article.tags or "")
        self.folder_edit.setText(article.folder or "")
        self.photo_btn.setEnabled(bool(article.image_path))
        self.browser_btn.setEnabled(bool(article.link and str(article.link).startswith("http")))
        if not self._busy_mode:
            self._refresh_translate_button()
        self._refresh_narrate_button()

    def _translation_for_current_language(self) -> tuple[str, str] | None:
        article = self._article
        if article is None:
            return None
        if (article.translation_lang or "") != self._i18n.language:
            return None
        raw = (article.ai_translation or "").strip()
        if not raw:
            return None
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return article.title, raw
        if isinstance(payload, dict):
            title = str(payload.get("title") or article.title).strip()
            body = str(payload.get("body") or payload.get("text") or "").strip()
            if title or body:
                return title or article.title, body
        return article.title, raw

    def _refresh_translate_button(self) -> None:
        if self._showing_translation and self._translation_for_current_language():
            self.translate_btn.setText(self._i18n.t("ai.show_original"))
        elif self._translation_for_current_language():
            self.translate_btn.setText(self._i18n.t("ai.show_translation"))
        else:
            self.translate_btn.setText(self._i18n.t("ai.translate"))

    def _render_sentiment(self, sentiment: str | None, module_id: str | None = None) -> None:
        if not sentiment:
            self.sentiment_badge.setVisible(False)
            return
        object_name = SENTIMENT_OBJECTS.get(sentiment, "sentimentNeutral")
        self.sentiment_badge.setObjectName(object_name)
        finance = (module_id or "") in {"economy_markets", "crypto_web3", "economy"}
        if finance:
            label_key = {
                "bullish/positive": "sentiment.bullish",
                "bearish/negative": "sentiment.bearish",
                "neutral": "sentiment.neutral",
            }.get(sentiment, "sentiment.neutral")
        else:
            label_key = {
                "bullish/positive": "sentiment.positive",
                "bearish/negative": "sentiment.negative",
                "neutral": "sentiment.neutral",
            }.get(sentiment, "sentiment.neutral")
        self.sentiment_badge.setText(self._i18n.t(label_key))
        self.sentiment_badge.setVisible(True)
        self.sentiment_badge.style().unpolish(self.sentiment_badge)
        self.sentiment_badge.style().polish(self.sentiment_badge)

    def _emit_fulltext(self) -> None:
        if self._article:
            self.fulltext_requested.emit(self._article.id)

    def _emit_export(self) -> None:
        if self._article:
            self.export_requested.emit(self._article.id)

    def _emit_copy(self) -> None:
        if self._article and self._article.link:
            self.copy_link_requested.emit(self._article.link)

    def _emit_share(self) -> None:
        self.share_requested.emit()

    def share_article(self):
        return self._article

    def share_briefing(self) -> dict | None:
        return self._briefing

    def _emit_print(self) -> None:
        if self._article:
            self.print_requested.emit(self._article.id)

    def _emit_pdf(self) -> None:
        if self._article:
            self.pdf_requested.emit(self._article.id)

    def _emit_browser(self) -> None:
        if self._article:
            self.browser_requested.emit(self._article.id)

    def _emit_photo(self) -> None:
        if self._article and self._article.image_path:
            self.lightbox_requested.emit(str(self._article.image_path))

    def _emit_note(self) -> None:
        if self._article:
            self.note_changed.emit(self._article.id, self.note_edit.toPlainText())

    def _emit_tags(self) -> None:
        if self._article:
            self.tags_changed.emit(self._article.id, self.tags_edit.text())

    def _emit_folder(self) -> None:
        if self._article:
            self.folder_changed.emit(self._article.id, self.folder_edit.text())

    def _covered_item_html(self, item: object) -> str:
        if isinstance(item, dict):
            title = str(item.get("title") or "").strip()
            source = str(item.get("source") or "").strip()
            url = str(item.get("url") or "").strip()
            label = f"{source}: {title}" if source and title else (title or source or url)
            if not label:
                return ""
            if url.startswith("http://") or url.startswith("https://"):
                return (
                    f'<li><a href="{escape(url, quote=True)}">{escape(label)}</a></li>'
                )
            return f"<li>{escape(label)}</li>"
        text = str(item).strip()
        return f"<li>{escape(text)}</li>" if text else ""

    def set_narrator_gender(self, gender: str, persist: bool = False) -> None:
        value = "male" if gender == "male" else "female"
        self._speech.set_gender(value)
        self.avatar.set_gender(value)
        self.voice_female.setChecked(value == "female")
        self.voice_male.setChecked(value == "male")
        self._set_object_name(self.voice_female, "narratorVoiceOn" if value == "female" else "ghostButton")
        self._set_object_name(self.voice_male, "narratorVoiceOn" if value == "male" else "ghostButton")
        if persist:
            self.narrator_gender_changed.emit(value)

    def _on_speaking(self, speaking: bool) -> None:
        self.avatar.set_speaking(speaking)
        self._refresh_narrate_button()

    def _refresh_narrate_button(self) -> None:
        available = self._speech.available
        self.narrate_btn.setEnabled(available and bool(self._speakable_text()))
        if self._speech.speaking:
            self.narrate_btn.setText(self._i18n.t("ai.narrate_stop"))
        else:
            self.narrate_btn.setText(self._i18n.t("ai.narrate"))
        if not available:
            self.narrator_bar.setToolTip(self._i18n.t("ai.narrate_unavailable"))
            return
        installed = ", ".join(code.upper() for code in self._speech.installed_languages()) or "—"
        missing = ", ".join(code.upper() for code in self._speech.missing_languages()) or "—"
        self.narrator_bar.setToolTip(
            self._i18n.t("ai.narrate_hint")
            .replace("{installed}", installed)
            .replace("{missing}", missing)
        )

    def _speakable_text(self) -> str:
        if self._briefing:
            parts = [str(self._briefing.get("summary") or "")]
            parts.extend(str(item) for item in (self._briefing.get("takeaways") or []) if item)
            return plain_text(" ".join(parts))
        article = self._article
        if article is None:
            return ""
        translated = self._translation_for_current_language() if self._showing_translation else None
        title = translated[0] if translated else article.title
        body = (translated[1] if translated else "") or (article.content or "")
        if article.ai_summary:
            return plain_text(f"{title}. {article.ai_summary}")
        from core.app_extras import sanitize_article_html

        return plain_text(f"{title}. {sanitize_article_html(body)}")

    def _on_narrate(self) -> None:
        if self._speech.speaking:
            self._speech.stop()
            return
        text = self._speakable_text()
        if not text:
            return
        self._speech.speak(text)

    def _refresh_save_button(self) -> None:
        saved = bool(self._article and self._article.is_saved)
        self.save_btn.setText(self._i18n.t("app.unsave_story") if saved else self._i18n.t("app.save_story"))
        self._set_object_name(self.save_btn, "saveButtonOn" if saved else "saveButton")
        self._set_object_name(self.save_panel, "savePanelOn" if saved else "savePanel")

    def _refresh_emoji_buttons(self) -> None:
        current = (self._article.emoji if self._article else "") or ""
        for button in self._emoji_buttons:
            selected = button.text() == current
            self._set_object_name(button, "emojiButtonOn" if selected else "emojiButton")

    def _set_object_name(self, widget: QWidget, name: str) -> None:
        if widget.objectName() == name:
            return
        widget.setObjectName(name)
        style = widget.style()
        style.unpolish(widget)
        style.polish(widget)
        widget.update()

    def _on_save_clicked(self) -> None:
        if not self._article:
            return
        self.save_toggled.emit(self._article.id, not bool(self._article.is_saved))

    def _on_emoji_clicked(self, mark: str) -> None:
        if not self._article:
            return
        next_value = "" if (self._article.emoji or "") == mark else mark
        self.emoji_selected.emit(self._article.id, next_value)

    def _emit_summarize(self) -> None:
        if self._article:
            self.summarize_requested.emit(self._article.id)

    def _on_translate_clicked(self) -> None:
        if not self._article:
            return
        if self._showing_translation:
            self._showing_translation = False
            self._render_article()
            return
        if self._translation_for_current_language():
            self._showing_translation = True
            self._render_article()
            return
        self.translate_requested.emit(self._article.id)
