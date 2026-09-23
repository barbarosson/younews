from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from PySide6.QtGui import QAction, QDesktopServices, QIcon, QKeySequence, QTextDocument
from PySide6.QtCore import QByteArray, Qt, QTimer, QUrl
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QSizePolicy,
    QSplitter,
    QStatusBar,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from config import (
    ARTICLE_RETENTION_HOURS,
    DEFAULT_THEME,
    get_provider_api_key,
    normalize_ai_provider,
    parse_alert_pct,
    parse_feed_refresh_minutes,
    parse_font_scale,
    normalize_article_date_sort,
)
from core.i18n_manager import I18nManager
from core.market_engine import MarketEngine
from core.social_resolve import repair_youtube_follows
from core.speech_engine import detect_speak_language
from core.workers import AiWorker, BriefingWorker, ChatWorker, FeedRefreshWorker, FullTextWorker, ImagePrefetchWorker, PageReadWorker, TranslateWorker
from database.db import Database
from ui.branding import app_icon
from ui.components.article_detail import ArticleDetail
from ui.components.article_list import ArticleList
from ui.components.busy_overlay import BusyOverlay
from ui.components.chat_panel import ChatPanel
from ui.components.settings_dialog import SettingsDialog
from ui.components.sidebar import Sidebar
from ui.components.ticker_bar import TickerBar, news_terms_for
from ui.components.watchlist_dialog import WatchlistDialog
from ui.components.tutorial_panel import TutorialDialog
from ui.theme import apply_app_theme


class MainWindow(QMainWindow):
    def __init__(self, db: Database, i18n: I18nManager) -> None:
        super().__init__()
        self.db = db
        self.i18n = i18n
        icon = app_icon()
        if not icon.isNull():
            self.setWindowIcon(icon)
        self._feed_worker: FeedRefreshWorker | None = None
        self._ai_worker: AiWorker | None = None
        self._briefing_worker: BriefingWorker | None = None
        self._translate_worker: TranslateWorker | None = None
        self._translate_silent = False
        self._chat_worker: ChatWorker | None = None
        self._image_worker: ImagePrefetchWorker | None = None
        self._fulltext_worker: FullTextWorker | None = None
        self._page_worker: PageReadWorker | None = None
        self._pending_thumbs: list = []
        self._ticker_pin: tuple[str, str] | None = None
        self._ai_queue: list[int] = []
        self._last_quotes: dict[str, float] = {}
        self._tray: QSystemTrayIcon | None = None
        self._mini_tape = None
        self._offline = QLabel()
        self._offline.setObjectName("offlineBadge")

        self.sidebar = Sidebar(db, i18n)
        self.article_list = ArticleList(i18n)
        self.article_detail = ArticleDetail(i18n)
        self.chat_panel = ChatPanel(i18n, db=db)
        self.chat_panel.hide()
        self.sidebar.setMinimumWidth(200)
        self.sidebar.setMaximumWidth(280)
        self.article_list.setMinimumWidth(340)
        self.article_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.article_detail.setMinimumWidth(400)
        self.article_detail.setMaximumWidth(680)
        self.article_detail.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        self.chat_panel.setMinimumWidth(0)
        self.chat_panel.setMaximumWidth(380)
        self.ticker = TickerBar()
        self.ticker.set_theme(self.db.get_setting("theme"))
        self.market = MarketEngine(self.db, self)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.addWidget(self.sidebar)
        self.splitter.addWidget(self.article_list)
        self.splitter.addWidget(self.article_detail)
        self.splitter.addWidget(self.chat_panel)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 3)
        self.splitter.setStretchFactor(2, 1)
        self.splitter.setStretchFactor(3, 0)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setCollapsible(0, True)
        self.splitter.setCollapsible(3, True)
        self.splitter.setSizes(self._balanced_sizes(1280))

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.ticker)
        layout.addWidget(self._offline)
        layout.addWidget(self.splitter, 1)
        self.setCentralWidget(central)
        self._busy_overlay = BusyOverlay(central)
        self._busy_depth = 0
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(220)
        self._search_timer.timeout.connect(lambda: self._reload_articles(busy=False))
        self.setStatusBar(QStatusBar())
        self._last_update_label = QLabel()
        self.statusBar().addPermanentWidget(self._last_update_label)
        self._feed_timer = QTimer(self)
        self._feed_timer.timeout.connect(lambda: self.refresh_feeds(force=False))

        self.sidebar.module_selected.connect(self._on_heading_change)
        self.sidebar.language_selected.connect(self.i18n.load)
        if hasattr(self.sidebar, "theme_selected"):
            self.sidebar.theme_selected.connect(self._apply_theme)
        self.sidebar.settings_requested.connect(self._open_settings)
        self.sidebar.help_requested.connect(self._open_tutorials)
        self.sidebar.refresh_requested.connect(self.refresh_feeds)
        self.sidebar.chat_requested.connect(self._toggle_chat)
        self.article_list.search.textChanged.connect(lambda _: self._search_timer.start())
        self.article_list.sort_changed.connect(self._on_article_sort)
        self.article_list.source_changed.connect(lambda: self._reload_articles(busy=False))
        self.article_list.hours_changed.connect(lambda: self._reload_articles(recount=True))
        self.article_list.follows_requested.connect(lambda: self._open_settings("social"))
        self.article_list.article_selected.connect(self._show_article)
        self.article_list.mark_all_read_requested.connect(self._mark_visible_read)
        self.article_detail.summarize_requested.connect(self._summarize)
        self.article_detail.translate_requested.connect(self._translate)
        self.article_detail.fulltext_requested.connect(self._fetch_fulltext)
        self.article_detail.export_requested.connect(self._export_article)
        self.article_detail.copy_link_requested.connect(self._copy_link)
        self.article_detail.share_requested.connect(self._share_current)
        self.article_detail.print_requested.connect(self._print_article)
        self.article_detail.pdf_requested.connect(self._pdf_article)
        self.article_detail.browser_requested.connect(self._open_in_app)
        self.article_detail.lightbox_requested.connect(self._lightbox)
        self.article_detail.note_changed.connect(lambda aid, text: self.db.set_article_note(aid, text))
        self.article_detail.tags_changed.connect(lambda aid, text: self.db.set_article_tags(aid, text))
        self.article_detail.folder_changed.connect(lambda aid, text: self.db.set_article_folder(aid, text))
        self.article_detail.save_toggled.connect(self._on_save_toggled)
        self.article_detail.emoji_selected.connect(self._on_emoji_selected)
        self.article_detail.set_narrator_gender(self.db.get_setting("narrator_voice", "female"), persist=False)
        self.article_detail.narrator_gender_changed.connect(
            lambda gender: self.db.set_setting("narrator_voice", gender)
        )
        self.article_list.economy_briefing_requested.connect(self._brief_current)
        self.article_list.module_briefing_requested.connect(self._brief_current)
        self.article_list.selected_briefing_requested.connect(self._brief_selected)
        self.i18n.language_changed.connect(self._on_language)
        self.market.quotes_ready.connect(self._on_quotes)
        self.market.failed.connect(self.ticker.set_status)
        self.ticker.quote_hovered.connect(self._on_ticker_hover)
        self.ticker.quote_clicked.connect(self._on_ticker_click)
        self.ticker.hover_cleared.connect(self._on_ticker_leave)
        self.ticker.watchlist_requested.connect(self._open_watchlist)
        self.chat_panel.message_submitted.connect(self._on_chat_message)
        self.chat_panel.article_requested.connect(self._show_article)
        self.chat_panel.url_requested.connect(self._open_chat_url)

        refresh_action = QAction(self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self.refresh_feeds)
        self.addAction(refresh_action)
        help_action = QAction(self)
        help_action.setShortcut("F1")
        help_action.triggered.connect(self._open_tutorials)
        self.addAction(help_action)
        for key, handler in (("J", self._select_next), ("K", self._select_prev), ("O", self._open_current_link), ("U", self._unread_current)):
            act = QAction(self)
            act.setShortcut(QKeySequence(key))
            act.triggered.connect(handler)
            self.addAction(act)
        share_action = QAction(self)
        share_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        share_action.triggered.connect(self._share_current)
        self.addAction(share_action)

        self.resize(1280, 800)
        self._restore_window()
        self._setup_tray()
        self._briefing_timer = QTimer(self)
        self._briefing_timer.setInterval(60_000)
        self._briefing_timer.timeout.connect(self._maybe_scheduled_briefing)
        self._briefing_timer.start()
        self.article_list.set_date_sort(self.db.get_setting("article_date_sort"))
        self._sync_ticker_tape()
        self._apply_theme(self.db.get_setting("theme", DEFAULT_THEME), persist=False)
        self._on_language(self.i18n.language)
        self._apply_feed_refresh_timer()
        self._apply_layout_prefs()
        QTimer.singleShot(0, self._first_run_and_restore)
        self._offline_timer = QTimer(self)
        self._offline_timer.setInterval(30_000)
        self._offline_timer.timeout.connect(self._refresh_offline)
        self._offline_timer.start()
        self._refresh_offline()
        if os.environ.get("GNT_SKIP_NETWORK") != "1":
            try:
                repair_youtube_follows(self.db)
            except Exception:
                pass
            self.market.start()
            self.refresh_feeds()

    def _on_language(self, _code: str) -> None:
        self.setWindowTitle(self.i18n.t("app.title"))
        self.sidebar.retranslate()
        self.article_list.retranslate()
        self.article_detail.retranslate()
        self.chat_panel.retranslate()
        self.ticker.retranslate(
            self.i18n.t("ticker.live"),
            self.i18n.t("ticker.waiting"),
            self.i18n.t("ticker.watchlist"),
        )
        self._refresh_last_update_ui()
        self._reload_articles(recount=True)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._place_busy_overlay()
        self._balance_panes()

    def _place_busy_overlay(self) -> None:
        overlay = getattr(self, "_busy_overlay", None)
        central = self.centralWidget()
        if overlay is None or central is None:
            return
        overlay.setGeometry(central.rect())
        overlay.raise_()

    def _set_busy(self, on: bool) -> None:
        if on:
            self._busy_depth += 1
            if self._busy_depth == 1:
                self._place_busy_overlay()
                self._busy_overlay.show()
                self._busy_overlay.raise_()
                QApplication.processEvents()
            return
        self._busy_depth = max(0, self._busy_depth - 1)
        if self._busy_depth == 0:
            self._busy_overlay.hide()

    def _reload_articles(self, module_id: str | None = None, *, recount: bool = False, busy: bool = True) -> None:
        if busy:
            self._set_busy(True)
        try:
            self._load_articles(module_id, recount=recount)
        finally:
            if busy:
                self._set_busy(False)

    def _load_articles(self, module_id: str | None = None, *, recount: bool = False) -> None:
        if self._ticker_pin:
            self._apply_ticker_filter(self._ticker_pin[0], self._ticker_pin[1], pin=True)
            if recount and hasattr(self.sidebar, "set_counts"):
                self.sidebar.set_counts(self.db.headline_counts(max_age_hours=self.article_list.hours()))
            return
        current = module_id or self.sidebar.current_module_id()
        archived = bool(getattr(self.sidebar, "is_archive", lambda: False)())
        window = None if archived else self.article_list.hours()
        self.article_list.set_module(current, heading=self._current_heading_label())
        topic_ids = self.sidebar.current_topic_ids() if hasattr(self.sidebar, "current_topic_ids") else None
        order = self.article_list.date_sort()
        source_id = self.article_list.source_id()
        articles = self.db.list_articles(
            current,
            self.article_list.search.text(),
            topic_ids=topic_ids,
            date_order=order,
            saved_only=archived,
            unread_only=self.article_list.unread_only() and not archived,
            max_age_hours=window,
            folder=self.article_list.folder() if hasattr(self.article_list, "folder") else None,
        )
        if hasattr(self.article_list, "set_folder_options"):
            self.article_list.set_folder_options(self.db.list_article_folders())
        if hasattr(self.article_list, "set_display_options"):
            self.article_list.set_display_options(
                compact=self.db.get_setting("compact_list", "0") == "1",
                low_data=self.db.get_setting("low_data", "0") == "1",
                relative=self.db.get_setting("relative_time", "1") == "1",
            )
        sources: list[tuple[int, str]] = []
        seen: set[int] = set()
        visible: list = []
        for article in articles:
            if article.source_id is not None and article.source_id not in seen:
                seen.add(article.source_id)
                sources.append(
                    (article.source_id, (article.source_name or "").strip() or f"#{article.source_id}")
                )
            if source_id is None or article.source_id == source_id:
                visible.append(article)
        sources.sort(key=lambda item: item[1].casefold())
        self.article_list.set_source_options(sources)
        empty_text = None
        if not visible and archived:
            empty_text = self.i18n.t("app.empty_archive")
        elif not visible and current == "social_media":
            empty_text = self.i18n.t("social.empty")
        elif not visible and self.sidebar.current_topic_id():
            empty_text = self.i18n.t("app.empty_topic")
        self.article_list.set_articles(visible, empty_text=empty_text)
        if visible and hasattr(self.article_list, "set_breaking"):
            first = visible[0]
            age = 0
            if first.pub_date:
                age = (datetime.now(first.pub_date.tzinfo) - first.pub_date).total_seconds()
            if age <= 1800 and not first.is_read:
                self.article_list.set_breaking(f"{self.i18n.t('app.breaking')}  {first.title}")
            else:
                self.article_list.set_breaking("")
        if recount and hasattr(self.sidebar, "set_counts"):
            self.sidebar.set_counts(self.db.headline_counts(max_age_hours=window))
        self._prefetch_thumbnails(visible)

    def _prefetch_thumbnails(self, articles: list) -> None:
        if self.db.get_setting("low_data", "0") == "1":
            return
        needed = [
            article
            for article in articles
            if not (article.image_path and Path(str(article.image_path)).is_file())
        ]
        if not needed:
            return
        if self._image_worker and self._image_worker.isRunning():
            self._pending_thumbs = needed
            return
        self._image_worker = ImagePrefetchWorker(self.db, needed, self)
        self._image_worker.thumbnail_ready.connect(self.article_list.apply_thumbnail)
        self._image_worker.finished_ok.connect(self._on_thumbs_done)
        self._image_worker.start()

    def _on_thumbs_done(self) -> None:
        pending = self._pending_thumbs
        self._pending_thumbs = []
        if pending:
            self._prefetch_thumbnails(pending)

    def _show_article(self, article_id: int) -> None:
        article = self.db.get_article(article_id)
        if article is None:
            return
        self.db.mark_read(article_id)
        article.is_read = True
        self.article_detail.show_article(article)
        self.db.set_setting("last_article_id", str(article_id))
        if hasattr(self.article_list, "mark_item_read"):
            self.article_list.mark_item_read(article_id)
        self._maybe_auto_translate(article)
        self._maybe_auto_summarize(article)

    def _maybe_auto_translate(self, article) -> None:
        if not self._can_auto_translate():
            return
        if (article.translation_lang or "") == self.i18n.language and (article.ai_translation or "").strip():
            return
        if detect_speak_language(article.title or "", "en") == self.i18n.language:
            return
        if self._ai_busy():
            return
        self._translate(article.id, silent=True, title_only=True)

    def _can_auto_translate(self) -> bool:
        provider = normalize_ai_provider(self.db.get_setting("ai_provider"))
        if provider == "ollama":
            return True
        return bool(get_provider_api_key(provider))

    def _maybe_auto_summarize(self, article) -> None:
        if self.db.get_setting("auto_ai_summary", "0") != "1":
            return
        if article.ai_summary:
            return
        if self._ai_busy():
            return
        self._summarize(article.id)

    def _apply_theme(self, theme: str, persist: bool = True) -> None:
        scale = parse_font_scale(self.db.get_setting("ui_font_scale"))
        resolved = apply_app_theme(theme, font_scale=scale)
        if persist:
            self.db.set_setting("theme", resolved)
        self.ticker.set_theme(resolved)
        sync = getattr(self.sidebar, "sync_theme", None)
        if callable(sync):
            sync(resolved)

    def _open_settings(self, tab: str | None = None) -> None:
        dialog = SettingsDialog(self.db, self.i18n, self, initial_tab=tab)
        if hasattr(dialog, "theme_changed"):
            dialog.theme_changed.connect(lambda theme: self._apply_theme(theme, persist=False))
        if hasattr(dialog, "mini_tape_requested"):
            dialog.mini_tape_requested.connect(self._show_mini_tape)
        dialog.exec()
        reload = getattr(self.sidebar, "reload_modules", None) or getattr(self.sidebar, "reload_tree", None)
        if callable(reload):
            reload()
        self._apply_feed_refresh_timer()
        if getattr(dialog, "sources_changed", False) or getattr(dialog.social_panel, "sources_changed", False):
            self.refresh_feeds()
        else:
            self._reload_articles(recount=True)
        self._sync_ticker_tape()
        self._apply_layout_prefs()
        if dialog.result():
            self.market.refresh()

    def _open_tutorials(self) -> None:
        dialog = TutorialDialog(self.i18n, self)

        def go(tab: str) -> None:
            dialog.accept()
            self._open_settings(tab)

        dialog.open_settings_requested.connect(go)
        dialog.exec()

    def _on_article_sort(self, order: str) -> None:
        resolved = normalize_article_date_sort(order)
        self.db.set_setting("article_date_sort", resolved)
        self._reload_articles()

    def _open_watchlist(self) -> None:
        dialog = WatchlistDialog(self.db, self.i18n, self)
        dialog.watchlist_changed.connect(self._on_watchlist_changed)
        dialog.exec()
        self._on_watchlist_changed()

    def _on_watchlist_changed(self) -> None:
        self._sync_ticker_tape()
        self.market.refresh()

    def _sync_ticker_tape(self) -> None:
        pairs = [(item.symbol, item.label) for item in self.db.list_tickers(self.db.get_setting("active_watchlist") or "main")]
        self.ticker.set_symbols(pairs)
        self.ticker.set_theme(self.db.get_setting("theme"))
        try:
            speed = int(self.db.get_setting("tape_speed", "100") or 100)
        except ValueError:
            speed = 100
        self.ticker.set_speed(speed)
        self.ticker.set_compact(self.db.get_setting("compact_tape", "0") == "1")
        self.ticker.setVisible(self.db.get_setting("hide_tape", "0") != "1")

    def _on_heading_change(self, module_id: str) -> None:
        self._clear_ticker_pin()
        self._reload_articles(module_id)

    def _clear_ticker_pin(self) -> None:
        self._ticker_pin = None
        if hasattr(self.ticker, "set_pinned_symbol"):
            self.ticker.set_pinned_symbol("")

    def _apply_ticker_filter(self, symbol: str, label: str, *, pin: bool) -> None:
        terms = news_terms_for(symbol, label)
        articles = self.db.list_articles_matching(terms, date_order=self.article_list.date_sort())
        banner = self.i18n.t("ticker.related").replace("{name}", label or symbol)
        if pin:
            banner = self.i18n.t("ticker.related_pinned").replace("{name}", label or symbol)
        self.article_list.set_context_banner(banner)
        self.article_list.set_articles(articles)
        if not articles:
            self.article_list.empty_label.setText(
                self.i18n.t("ticker.related_empty").replace("{name}", label or symbol)
            )

    def _on_ticker_hover(self, symbol: str, label: str) -> None:
        if self._ticker_pin:
            return
        self._apply_ticker_filter(symbol, label, pin=False)

    def _on_ticker_click(self, symbol: str, label: str) -> None:
        if self._ticker_pin and self._ticker_pin[0] == symbol:
            self._clear_ticker_pin()
            self.article_list.set_context_banner("")
            self.article_list.empty_label.setText(self.i18n.t("app.empty_feed"))
            self._reload_articles()
            return
        self._ticker_pin = (symbol, label)
        if hasattr(self.ticker, "set_pinned_symbol"):
            self.ticker.set_pinned_symbol(symbol)
        self._apply_ticker_filter(symbol, label, pin=True)

    def _on_ticker_leave(self) -> None:
        if self._ticker_pin:
            return
        self.article_list.set_context_banner("")
        self.article_list.empty_label.setText(self.i18n.t("app.empty_feed"))
        self._reload_articles()

    def _toggle_chat(self) -> None:
        visible = not self.chat_panel.isVisible()
        self.chat_panel.setVisible(visible)
        self.chat_panel.setMinimumWidth(280 if visible else 0)
        self._balance_panes()
        if visible:
            self.chat_panel.input.setFocus()

    def _open_chat_url(self, url: str) -> None:
        if url.startswith("http://") or url.startswith("https://"):
            QDesktopServices.openUrl(QUrl(url))

    def _on_chat_message(self, message: str) -> None:
        if self._ai_busy():
            self.chat_panel.append_assistant(self.i18n.t("chat.busy"))
            return
        self.chat_panel.set_busy(True)
        self.statusBar().showMessage(self.i18n.t("chat.thinking"))
        history = self.chat_panel.history()[:-1]
        selected = self.article_list.current_article_id()
        self._chat_worker = ChatWorker(
            self.db,
            message,
            self.i18n.native_name(),
            history,
            selected,
            self.article_list.date_sort(),
            self.sidebar.current_module_id() or "economy_markets",
            self.sidebar.current_topic_id(),
            self,
        )
        self._chat_worker.finished_ok.connect(self._on_chat_result)
        self._chat_worker.failed.connect(self._on_chat_error)
        self._chat_worker.start()

    def _on_chat_result(self, payload: object) -> None:
        self.chat_panel.set_busy(False)
        self.statusBar().clearMessage()
        data = payload if isinstance(payload, dict) else {}
        import_notes = self._format_import_notes(data.get("imported_sources") or [])
        imported_ok = any(
            isinstance(item, dict) and item.get("status") in {"added", "duplicate"}
            for item in (data.get("imported_sources") or [])
        )
        if imported_ok:
            self._reload_articles(recount=True)
        in_scope = bool(data.get("in_scope", True))
        reply = str(data.get("reply") or "").strip()
        if import_notes:
            reply = f"{import_notes}\n\n{reply}".strip() if reply else import_notes
        if not in_scope:
            reply = reply or self.i18n.t("chat.refuse")
            self.chat_panel.append_assistant(reply)
            self.chat_panel.set_suggestions(
                [
                    self.i18n.t("chat.suggest_markets"),
                    self.i18n.t("chat.suggest_crypto"),
                    self.i18n.t("chat.suggest_world"),
                ]
            )
            return
        article_ids: list[int] = []
        for item in data.get("article_ids") or []:
            try:
                article_ids.append(int(item))
            except (TypeError, ValueError):
                continue
        articles = self.db.get_articles_by_ids(article_ids) if article_ids else []
        links = [(article.id, article.title) for article in articles[:8]]
        if not reply:
            reply = self.i18n.t("chat.empty_match") if not articles else self.i18n.t("chat.done")
        self.chat_panel.append_assistant(reply, links)
        suggestions = [str(item) for item in data.get("suggestions") or [] if str(item).strip()]
        if suggestions:
            self.chat_panel.set_suggestions(suggestions)
        if articles:
            self.article_list.set_context_banner(self.i18n.t("chat.results"))
            self.article_list.set_articles(articles)
            self._prefetch_thumbnails(articles)
        open_id = data.get("open_article_id")
        if open_id:
            self._show_article(int(open_id))
        open_url = str(data.get("open_url") or "").strip()
        if open_url:
            self._open_chat_url(open_url)
        summarize_id = data.get("summarize_article_id")
        if summarize_id:
            self._summarize(int(summarize_id))

    def _format_import_notes(self, items: object) -> str:
        if not isinstance(items, list):
            return ""
        lines: list[str] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or item.get("url") or "").strip()
            status = str(item.get("status") or "")
            count = str(item.get("count") or 0)
            error = str(item.get("error") or "").strip()
            if status == "added":
                text = self.i18n.t("chat.source_added")
            elif status == "duplicate":
                text = self.i18n.t("chat.source_duplicate")
            else:
                text = self.i18n.t("chat.source_failed")
            lines.append(
                text.replace("{name}", name)
                .replace("{count}", count)
                .replace("{error}", error or self.i18n.t("sources.test_empty"))
            )
        return "\n".join(lines)

    def _on_chat_error(self, message: str) -> None:
        self.chat_panel.set_busy(False)
        self.statusBar().clearMessage()
        self.chat_panel.append_assistant(self._ai_error_text(message))

    def refresh_feeds(self, force: bool = True) -> None:
        if self._feed_worker and self._feed_worker.isRunning():
            return
        self.statusBar().showMessage(self.i18n.t("app.loading"))
        self._feed_worker = FeedRefreshWorker(self.db, self, force=force)
        self._feed_worker.finished_ok.connect(self._on_feeds)
        self._feed_worker.failed.connect(self._on_feed_error)
        self._feed_worker.start()

    def _on_feeds(self, count: int) -> None:
        self.db.set_setting("last_feed_refresh", datetime.now().astimezone().isoformat())
        failed = sum(1 for s in self.db.list_sources(active_only=True) if (s.last_error or "").strip())
        if failed:
            self.statusBar().showMessage(
                self.i18n.t("app.feeds_partial")
                .replace("{ok}", str(count))
                .replace("{fail}", str(failed)),
                8000,
            )
        else:
            self.statusBar().showMessage(self.i18n.t("app.feeds_updated"), 4000)
        self._reload_articles(recount=True)
        self._refresh_last_update_ui()

    def _on_feed_error(self, message: str) -> None:
        from core.app_extras import humanize_source_error

        text = self.i18n.t("app.feeds_failed").replace(
            "{error}",
            humanize_source_error(message, self.i18n),
        )
        self.statusBar().showMessage(text, 8000)
        self._refresh_last_update_ui()

    def _apply_feed_refresh_timer(self) -> None:
        if os.environ.get("GNT_SKIP_NETWORK") == "1":
            self._feed_timer.stop()
            return
        minutes = parse_feed_refresh_minutes(self.db.get_setting("feed_refresh_minutes"))
        if minutes <= 0:
            self._feed_timer.stop()
            return
        self._feed_timer.start(minutes * 60 * 1000)

    def _refresh_last_update_ui(self) -> None:
        raw = (self.db.get_setting("last_feed_refresh") or "").strip()
        when = self.i18n.t("app.last_update_never")
        if raw:
            try:
                parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                when = parsed.astimezone().strftime("%d %b %Y %H:%M")
            except ValueError:
                when = raw
        text = self.i18n.t("app.last_update").replace("{time}", when)
        self._last_update_label.setText(text)
        self.article_list.set_last_update_text(text)

    def _summarize(self, article_id: int) -> None:
        if self._ai_busy():
            self._ai_queue.append(article_id)
            return
        self.article_detail.set_busy(True)
        self.statusBar().showMessage(self.i18n.t("ai.summarizing"))
        self._ai_worker = AiWorker(self.db, article_id, self.i18n.english_name(), self)
        self._ai_worker.finished_ok.connect(self._on_ai)
        self._ai_worker.failed.connect(self._on_ai_error)
        self._ai_worker.start()

    def _translate(self, article_id: int, silent: bool = False, title_only: bool = False) -> None:
        if self._ai_busy():
            return
        if not silent and not self._can_auto_translate():
            QMessageBox.information(self, self.i18n.t("app.settings"), self.i18n.t("ai.no_key"))
            return
        self._translate_silent = silent
        self.article_detail.set_busy(True, "translate")
        self.statusBar().showMessage(self.i18n.t("ai.translating"))
        self._translate_worker = TranslateWorker(
            self.db,
            article_id,
            self.i18n.english_name(),
            self.i18n.language,
            self,
            title_only=title_only,
        )
        self._translate_worker.finished_ok.connect(self._on_translate)
        self._translate_worker.failed.connect(self._on_translate_error)
        self._translate_worker.start()

    def _ai_busy(self) -> bool:
        return bool(
            (self._ai_worker and self._ai_worker.isRunning())
            or (self._briefing_worker and self._briefing_worker.isRunning())
            or (self._translate_worker and self._translate_worker.isRunning())
            or (self._chat_worker and self._chat_worker.isRunning())
        )

    def _on_translate(self, article_id: int) -> None:
        self.article_detail.set_busy(False)
        self.statusBar().clearMessage()
        article = self.db.get_article(article_id)
        if article:
            self.article_detail.show_article(article, show_translation=True)

    def _on_translate_error(self, message: str) -> None:
        self.article_detail.set_busy(False)
        self.statusBar().clearMessage()
        if self._translate_silent:
            return
        QMessageBox.warning(self, self.i18n.t("app.settings"), self._ai_error_text(message))

    def _ai_error_text(self, message: str) -> str:
        if "missing_api_key" in message or "missing_openai_key" in message:
            return self.i18n.t("ai.no_key")
        return f"{self.i18n.t('ai.error')} {message}"

    def _current_heading_label(self) -> str:
        module_id = self.sidebar.current_module_id()
        topic_id = self.sidebar.current_topic_id() if hasattr(self.sidebar, "current_topic_id") else None
        archived = bool(getattr(self.sidebar, "is_archive", lambda: False)())
        archive = self.i18n.t("app.archive")
        if not module_id:
            return archive if archived else self.i18n.t("app.all_news")
        if topic_id:
            heading = topic_id
            for topic in self.db.list_topics(module_id, active_only=False):
                if topic.id == topic_id:
                    heading = self.i18n.t(topic.name_key, topic.id)
                    break
            else:
                heading = self.i18n.t(f"topics.{topic_id}", topic_id)
        else:
            heading = self.i18n.t(f"modules.{module_id}", module_id.title())
        if archived:
            return f"{archive} · {heading}"
        return heading

    def _on_save_toggled(self, article_id: int, saved: bool) -> None:
        self.db.set_article_saved(article_id, saved)
        article = self.db.get_article(article_id)
        if article:
            article.is_saved = saved
            showing = getattr(self.article_detail, "_article", None)
            if showing and showing.id == article_id:
                showing.is_saved = saved
                self.article_detail.show_article(showing)
        self._reload_articles(recount=True)

    def _on_emoji_selected(self, article_id: int, emoji: str) -> None:
        self.db.set_article_emoji(article_id, emoji or None)
        article = self.db.get_article(article_id)
        if article:
            showing = getattr(self.article_detail, "_article", None)
            if showing and showing.id == article_id:
                showing.emoji = emoji or None
                self.article_detail.show_article(showing)
        self._reload_articles(recount=True)

    def _brief_current(self, hours: int) -> None:
        if self._ai_busy():
            return
        archived = bool(getattr(self.sidebar, "is_archive", lambda: False)())
        module_id = self.sidebar.current_module_id()
        topic_ids = self.sidebar.current_topic_ids() if hasattr(self.sidebar, "current_topic_ids") else None
        self._run_briefing(
            module_id,
            hours=hours,
            article_ids=None,
            topic_ids=topic_ids,
            heading=self._current_heading_label(),
            saved_only=archived,
        )

    def _brief_selected(self, article_ids: list) -> None:
        if self._ai_busy():
            return
        if not article_ids:
            QMessageBox.information(self, self.i18n.t("ai.summary"), self.i18n.t("ai.brief_need_selection"))
            return
        module_id = self.sidebar.current_module_id() or "economy_markets"
        self._run_briefing(
            module_id,
            hours=self.article_list.hours(),
            article_ids=list(article_ids),
            heading=self._current_heading_label(),
        )

    def _run_briefing(
        self,
        module_id: str | None,
        hours: int,
        article_ids: list[int] | None,
        topic_ids: list[str] | None = None,
        heading: str | None = None,
        saved_only: bool = False,
    ) -> None:
        if heading:
            scope_name = heading
        elif module_id:
            scope_name = self.i18n.t(f"modules.{module_id}", module_id.title())
        else:
            scope_name = self.i18n.t("app.all_news")
        self.article_list.set_busy(True)
        self.article_detail.set_busy(True)
        self.statusBar().showMessage(self.i18n.t("ai.summarizing"))
        self._briefing_worker = BriefingWorker(
            self.db,
            language_name=self.i18n.english_name(),
            module_id=module_id,
            module_name=scope_name,
            hours=hours,
            article_ids=article_ids,
            topic_ids=topic_ids,
            saved_only=saved_only,
            parent=self,
        )
        self._briefing_worker.finished_ok.connect(self._on_briefing)
        self._briefing_worker.failed.connect(self._on_briefing_error)
        self._briefing_worker.start()

    def _on_briefing(self, payload: dict) -> None:
        self.article_list.set_busy(False)
        self.article_detail.set_busy(False)
        self.article_detail.show_briefing(payload)
        self.statusBar().showMessage(
            self.i18n.t("ai.brief_count").replace("{count}", str(payload.get("count") or 0)),
            5000,
        )

    def _on_briefing_error(self, message: str) -> None:
        self.article_list.set_busy(False)
        self.article_detail.set_busy(False)
        if "empty_briefing_window" in message:
            text = self.i18n.t("ai.brief_empty")
        else:
            text = self._ai_error_text(message)
        QMessageBox.warning(self, self.i18n.t("ai.summary"), text)

    def _on_ai(self, article_id: int, _summary: str, _sentiment: str) -> None:
        self.article_detail.set_busy(False)
        article = self.db.get_article(article_id)
        if article:
            self.article_detail.show_article(article)
        if self._ai_queue:
            nxt = self._ai_queue.pop(0)
            self._summarize(nxt)

    def _on_ai_error(self, message: str) -> None:
        self.article_detail.set_busy(False)
        QMessageBox.warning(self, self.i18n.t("app.settings"), self._ai_error_text(message))
        if self._ai_queue:
            nxt = self._ai_queue.pop(0)
            self._summarize(nxt)

    def _on_quotes(self, quotes: list) -> None:
        self.ticker.set_quotes(quotes)
        if self._mini_tape is not None:
            self._mini_tape.ticker.set_quotes(quotes)
        if quotes and any(getattr(item, "stale", False) for item in quotes):
            if not any(
                not getattr(item, "missing", False) and not getattr(item, "stale", False) for item in quotes
            ):
                self.ticker.set_status(self.i18n.t("ticker.cached"))
        by_symbol = {item.symbol: item for item in self.db.list_tickers()}
        from core.app_extras import quiet_hours_active

        try:
            q_start = int(self.db.get_setting("quiet_start", "-1") or "-1")
            q_end = int(self.db.get_setting("quiet_end", "-1") or "-1")
        except ValueError:
            q_start, q_end = -1, -1
        quiet = quiet_hours_active(q_start, q_end)
        if self.db.get_setting("notify_alerts", "1") != "1" or self._tray is None or quiet:
            self._last_quotes = {q.symbol: q.change_pct for q in quotes if not getattr(q, "missing", False)}
            return
        default_threshold = parse_alert_pct(self.db.get_setting("ticker_alert_pct"))
        for quote in quotes:
            if getattr(quote, "missing", False):
                continue
            prev = self._last_quotes.get(quote.symbol)
            if prev is None:
                continue
            meta = by_symbol.get(quote.symbol)
            threshold = meta.alert_pct if meta and meta.alert_pct else default_threshold
            if threshold <= 0:
                continue
            if abs(quote.change_pct) >= threshold and abs(quote.change_pct - prev) >= 0.2:
                self._tray.showMessage(
                    quote.label,
                    f"{quote.change_pct:+.2f}%",
                    QSystemTrayIcon.MessageIcon.Information,
                    4000,
                )
                if self.db.get_setting("alert_beep", "1") == "1":
                    QApplication.beep()
        self._last_quotes = {q.symbol: q.change_pct for q in quotes if not getattr(q, "missing", False)}

    def _mark_visible_read(self) -> None:
        ids: list[int] = []
        for row in range(self.article_list.list_widget.count()):
            item = self.article_list.list_widget.item(row)
            if item is None:
                continue
            value = item.data(Qt.ItemDataRole.UserRole)
            if value is not None:
                ids.append(int(value))
        self.db.mark_all_read(ids)
        self._reload_articles(busy=False)

    def _fetch_fulltext(self, article_id: int) -> None:
        self.statusBar().showMessage(self.i18n.t("app.loading"))
        self._fulltext_worker = FullTextWorker(self.db, article_id, self)
        self._fulltext_worker.finished_ok.connect(self._on_fulltext)
        self._fulltext_worker.failed.connect(lambda msg: self.statusBar().showMessage(str(msg), 4000))
        self._fulltext_worker.start()

    def _on_fulltext(self, article_id: int) -> None:
        self.statusBar().clearMessage()
        article = self.db.get_article(article_id)
        if article:
            self.article_detail.show_article(article)

    def _export_article(self, article_id: int) -> None:
        article = self.db.get_article(article_id)
        if article is None:
            return
        path, _filter = QFileDialog.getSaveFileName(
            self, self.i18n.t("app.export_md"), f"{article.title[:40]}.md", "Markdown (*.md)"
        )
        if not path:
            return
        body = article.ai_summary or article.content or ""
        text = f"# {article.title}\n\n{article.link or ''}\n\n{body}\n"
        Path(path).write_text(text, encoding="utf-8")

    def _maybe_scheduled_briefing(self) -> None:
        try:
            hour = int(self.db.get_setting("scheduled_briefing_hour", "-1") or "-1")
        except ValueError:
            return
        if hour < 0:
            return
        now = datetime.now()
        if now.hour != hour or now.minute > 1:
            return
        stamp = now.strftime("%Y-%m-%d")
        if self.db.get_setting("last_scheduled_briefing") == stamp:
            return
        if self._ai_busy():
            return
        self.db.set_setting("last_scheduled_briefing", stamp)
        self._brief_current(self.article_list.hours())

    def _setup_tray(self) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        icon = self.windowIcon()
        tray = QSystemTrayIcon(icon if not icon.isNull() else QIcon(), self)
        menu = QMenu()
        show_act = menu.addAction(self.i18n.t("app.title"))
        show_act.triggered.connect(self.showNormal)
        quit_act = menu.addAction(self.i18n.t("app.close"))
        quit_act.triggered.connect(QApplication.instance().quit)
        tray.setContextMenu(menu)
        tray.activated.connect(lambda reason: self.showNormal() if reason == QSystemTrayIcon.ActivationReason.Trigger else None)
        tray.setToolTip(self.i18n.t("app.title"))
        tray.show()
        self._tray = tray

    def _restore_window(self) -> None:
        geo = self.db.get_setting("window_geometry")
        if geo:
            self.restoreGeometry(QByteArray.fromHex(geo.encode("ascii")))
        QTimer.singleShot(0, self._balance_panes)

    def _balanced_sizes(self, total: int | None = None) -> list[int]:
        width = int(total or self.splitter.width() or self.width() or 1280)
        side_on = self.sidebar.isVisible()
        chat_on = self.chat_panel.isVisible()
        side = 240 if side_on else 0
        chat = 300 if chat_on else 0
        rest = max(340 + 400, width - side - chat)
        detail = min(680, max(420, int(rest * 0.38)))
        list_w = rest - detail
        if list_w < 340:
            list_w = 340
            detail = max(400, rest - list_w)
        if detail > 680:
            list_w += detail - 680
            detail = 680
        return [side, list_w, detail, chat]

    def _balance_panes(self) -> None:
        if not hasattr(self, "splitter"):
            return
        target = self._balanced_sizes()
        current = self.splitter.sizes()
        if current and len(current) == len(target) and all(abs(a - b) < 24 for a, b in zip(current, target)):
            return
        self.splitter.setSizes(target)

    def closeEvent(self, event) -> None:  # noqa: N802
        self.db.set_setting("window_geometry", bytes(self.saveGeometry().toHex()).decode("ascii"))
        self.db.set_setting("splitter_sizes", ",".join(str(value) for value in self.splitter.sizes()))
        from core.app_extras import sync_database_copy

        sync_database_copy(self.db.get_setting("sync_folder") or "")
        if self.db.get_setting("minimize_to_tray", "1") == "1" and self._tray is not None:
            event.ignore()
            self.hide()
            return
        super().closeEvent(event)

    def _apply_layout_prefs(self) -> None:
        two = self.db.get_setting("two_pane", "0") == "1"
        self.sidebar.setVisible(not two)
        self._sync_ticker_tape()
        self._balance_panes()

    def _first_run_and_restore(self) -> None:
        if self.db.get_setting("first_run_done", "0") != "1":
            from ui.components.extra_windows import FirstRunWizard

            wizard = FirstRunWizard(self.db, self.i18n, self)
            if wizard.exec() == FirstRunWizard.DialogCode.Accepted:
                self.db.set_setting("first_run_done", "1")
                self._on_language(self.i18n.language)
                self.sidebar.reload_modules()
                if wizard.pack_id:
                    self.refresh_feeds(force=True)
            else:
                self.db.set_setting("first_run_done", "1")
        last = self.db.get_setting("last_article_id")
        if last:
            try:
                self._show_article(int(last))
            except ValueError:
                pass
        self._check_updates()

    def _check_updates(self) -> None:
        if self.db.get_setting("auto_update_check", "0") != "1":
            return
        from config import APP_PROMO_URL, APP_VERSION, GITHUB_UPDATE_REPO
        from core.app_extras import latest_github_release

        repo = (self.db.get_setting("github_repo") or GITHUB_UPDATE_REPO or "").strip()
        if not repo:
            url = (APP_PROMO_URL or "https://younews.media").rstrip("/")
            self.statusBar().showMessage(
                self.i18n.t("app.update_check_site").replace("{url}", url),
                7000,
            )
            return
        tag = latest_github_release(repo)
        if tag and tag != APP_VERSION.lstrip("v"):
            self.statusBar().showMessage(self.i18n.t("app.update_available").replace("{version}", tag), 8000)

    def _refresh_offline(self) -> None:
        import socket

        try:
            socket.create_connection(("1.1.1.1", 53), timeout=1.5).close()
            self._offline.hide()
        except OSError:
            self._offline.setText(self.i18n.t("app.offline"))
            self._offline.show()

    def _select_next(self) -> None:
        row = min(self.article_list.list_widget.currentRow() + 1, self.article_list.list_widget.count() - 1)
        if row >= 0:
            self.article_list.list_widget.setCurrentRow(row)

    def _select_prev(self) -> None:
        row = max(self.article_list.list_widget.currentRow() - 1, 0)
        self.article_list.list_widget.setCurrentRow(row)

    def _open_current_link(self) -> None:
        article_id = self.article_list.current_article_id()
        article = self.db.get_article(article_id) if article_id else None
        if article and article.link:
            QDesktopServices.openUrl(QUrl(article.link))

    def _unread_current(self) -> None:
        article_id = self.article_list.current_article_id()
        if article_id:
            self.db.mark_unread(article_id)
            self._reload_articles(busy=False)

    def _copy_link(self, url: str) -> None:
        QApplication.clipboard().setText(url or "")

    def _share_current(self) -> None:
        from core.share import briefing_as_article
        from ui.components.extra_windows import ShareDialog

        article = self.article_detail.share_article()
        if article is None:
            payload = self.article_detail.share_briefing()
            if payload:
                article = briefing_as_article(payload, self.i18n)
        if article is None:
            return
        dialog = ShareDialog(article, self.i18n, self)
        dialog.exec()

    def _print_article(self, article_id: int) -> None:
        article = self.db.get_article(article_id)
        if article is None:
            return
        try:
            from PySide6.QtPrintSupport import QPrintDialog, QPrinter
        except ImportError:
            return
        printer = QPrinter()
        dialog = QPrintDialog(printer, self)
        if dialog.exec():
            doc = QTextDocument()
            doc.setPlainText(f"{article.title}\n\n{article.content or ''}")
            doc.print_(printer)

    def _pdf_article(self, article_id: int) -> None:
        article = self.db.get_article(article_id)
        if article is None:
            return
        path, _filter = QFileDialog.getSaveFileName(self, self.i18n.t("app.pdf"), f"{article.title[:40]}.pdf", "PDF (*.pdf)")
        if not path:
            return
        try:
            from PySide6.QtPrintSupport import QPrinter
        except ImportError:
            Path(path).write_text(f"{article.title}\n\n{article.content or ''}", encoding="utf-8")
            return
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        printer.setOutputFileName(path)
        doc = QTextDocument()
        doc.setPlainText(f"{article.title}\n\n{article.content or ''}")
        doc.print_(printer)

    def _open_in_app(self, article_id: int) -> None:
        article = self.db.get_article(article_id)
        if article is None or not (article.link or "").startswith("http"):
            self.statusBar().showMessage(self.i18n.t("app.read_failed"), 4000)
            return
        from ui.components.extra_windows import ReaderDialog

        dialog = ReaderDialog(article.title, article.link, self.i18n, self)
        worker = PageReadWorker(article.link, self)
        worker.finished_ok.connect(dialog.set_html)
        worker.failed.connect(dialog.set_error)
        self._page_worker = worker
        worker.start()
        dialog.exec()

    def _lightbox(self, path: str) -> None:
        from ui.components.extra_windows import LightboxDialog

        LightboxDialog(path, self).exec()

    def _show_mini_tape(self) -> None:
        from ui.components.extra_windows import MiniTapeWindow

        if self._mini_tape is None:
            self._mini_tape = MiniTapeWindow()
        self._mini_tape.show()
        self._mini_tape.raise_()

