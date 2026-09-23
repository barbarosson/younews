from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from config import (
    AI_PROVIDERS,
    CLOUD_AI_PROVIDERS,
    DEFAULT_AI_MODELS,
    DEFAULT_THEME,
    FEED_REFRESH_INTERVAL_KEYS,
    FEED_REFRESH_MINUTES,
    ARTICLE_LIST_LIMIT_OPTIONS,
    ARTICLE_RETENTION_OPTIONS,
    FONT_SCALE_OPTIONS,
    PROVIDER_KEY_ACCOUNTS,
    UI_LANGUAGES,
    SUPPORTED_LANGUAGES,
    get_provider_api_key,
    normalize_ai_provider,
    normalize_theme,
    parse_alert_pct,
    parse_feed_refresh_minutes,
    parse_article_list_limit,
    parse_font_scale,
    parse_retention_hours,
    provider_model_setting_key,
    set_provider_api_key,
)
from core.i18n_manager import I18nManager
from core.ticker_catalog import CatalogTicker, _fold, search_catalog
from core.yahoo_lookup import YahooLookupWorker, merge_ticker_search
from database.db import Database
from ui.components.social_tab import SocialFollowsTab
from ui.components.sources_tab import SourcesTab
from ui.components.tutorial_panel import TutorialPanel
from ui.theme import apply_app_theme

PROVIDER_LABEL_KEYS: tuple[tuple[str, str], ...] = (
    ("openai", "app.openai"),
    ("anthropic", "app.anthropic"),
    ("gemini", "app.gemini"),
    ("groq", "app.groq"),
    ("ollama", "app.ollama"),
)



class SettingsDialog(QDialog):
    theme_changed = Signal(str)
    mini_tape_requested = Signal()

    def __init__(self, db: Database, i18n: I18nManager, parent=None, initial_tab: str | None = None) -> None:
        super().__init__(parent)
        self._db = db
        self._i18n = i18n
        self._draft_keys: dict[str, str] = {}
        self._draft_models: dict[str, str] = {}
        self._fields_provider: str | None = None
        self.setModal(True)
        self.setSizeGripEnabled(True)
        self._fitted = False

        self.tabs = QTabWidget()
        self.tabs.setUsesScrollButtons(True)
        self.tabs.setElideMode(Qt.TextElideMode.ElideRight)
        self.language_combo = QComboBox()
        for code, name in UI_LANGUAGES.items():
            self.language_combo.addItem(name, code)
        self.theme_combo = QComboBox()
        self.provider_combo = QComboBox()
        self.api_key = QLineEdit()
        self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_hint = QLabel()
        self.key_hint.setWordWrap(True)
        self.ollama_url = QLineEdit()
        self.ollama_model = QLineEdit()
        self.save_btn = QPushButton()
        self.close_btn = QPushButton()
        self.close_btn.setObjectName("ghostButton")

        self.lang_label = QLabel()
        self.theme_label = QLabel()
        self.refresh_interval_label = QLabel()
        self.refresh_interval_combo = QComboBox()
        self.list_limit_label = QLabel()
        self.list_limit_combo = QComboBox()
        self.provider_label = QLabel()
        self.key_label = QLabel()
        self.url_label = QLabel()
        self.model_label = QLabel()
        self.auto_ai_summary = QCheckBox()
        self.retention_label = QLabel()
        self.retention_combo = QComboBox()
        self.font_label = QLabel()
        self.font_combo = QComboBox()
        self.alert_label = QLabel()
        self.alert_edit = QLineEdit()
        self.briefing_hour_label = QLabel()
        self.briefing_hour_combo = QComboBox()
        self.cluster_headlines = QCheckBox()
        self.minimize_tray = QCheckBox()
        self.start_windows = QCheckBox()
        self.notify_alerts = QCheckBox()
        self.pack_tr = QPushButton()
        self.pack_us = QPushButton()
        self.pack_eu = QPushButton()
        self.pack_mastodon = QPushButton()
        self.backup_btn = QPushButton()
        self.restore_btn = QPushButton()
        self.backup_btn.setObjectName("ghostButton")
        self.restore_btn.setObjectName("ghostButton")
        self.proxy_edit = QLineEdit()
        self.quiet_start = QComboBox()
        self.quiet_end = QComboBox()
        self.tape_speed = QComboBox()
        self.hide_tape = QCheckBox()
        self.compact_tape = QCheckBox()
        self.compact_list = QCheckBox()
        self.two_pane = QCheckBox()
        self.low_data = QCheckBox()
        self.relative_time = QCheckBox()
        self.alert_beep = QCheckBox()
        self.intraday = QCheckBox()
        self.auto_update = QCheckBox()
        self.github_repo = QLineEdit()
        self.sync_folder = QLineEdit()
        self.vacuum_btn = QPushButton()
        self.cache_btn = QPushButton()
        self.about_btn = QPushButton()
        self.mini_tape_btn = QPushButton()
        self.help_site_btn = QPushButton()
        self.help_privacy_btn = QPushButton()
        self.help_refund_btn = QPushButton()
        self.help_email_btn = QPushButton()
        self.vacuum_btn.setObjectName("ghostButton")
        self.cache_btn.setObjectName("ghostButton")
        self.about_btn.setObjectName("ghostButton")
        self.mini_tape_btn.setObjectName("ghostButton")
        self.help_site_btn.setObjectName("ghostButton")
        self.help_privacy_btn.setObjectName("ghostButton")
        self.help_refund_btn.setObjectName("ghostButton")
        self.help_email_btn.setObjectName("ghostButton")
        self.github_repo.setVisible(False)
        self.modules_label = QLabel()
        self.modules_hint = QLabel()
        self.modules_hint.setWordWrap(True)
        self.catalog_tree = QTreeWidget()
        self.catalog_tree.setHeaderHidden(True)
        self.catalog_tree.setRootIsDecorated(True)
        self.catalog_tree.setAnimated(True)
        self._catalog_syncing = False
        self.filters_hint = QLabel()
        self.filters_hint.setWordWrap(True)
        self.filter_keyword = QLineEdit()
        self.filter_type = QComboBox()
        self.filter_add = QPushButton()
        self.filter_remove = QPushButton()
        self.filter_remove.setObjectName("ghostButton")
        self.filter_list = QListWidget()
        self.tickers_hint = QLabel()
        self.tickers_hint.setWordWrap(True)
        self.tickers_current_label = QLabel()
        self.ticker_list = QListWidget()
        self.ticker_list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.ticker_search = QLineEdit()
        self.ticker_preset = QComboBox()
        self.ticker_symbol = QLineEdit()
        self.ticker_label_edit = QLineEdit()
        self.ticker_add = QPushButton()
        self.ticker_remove = QPushButton()
        self.ticker_remove.setObjectName("ghostButton")
        self._ticker_rows: list[tuple[str, str]] = []
        self._yahoo_hits: list[CatalogTicker] = []
        self._yahoo_query = ""
        self._yahoo_thread: YahooLookupWorker | None = None
        self._ticker_debounce = QTimer(self)
        self._ticker_debounce.setSingleShot(True)
        self._ticker_debounce.setInterval(350)
        self._ticker_debounce.timeout.connect(self._start_yahoo_ticker_search)
        self.license_status = QLabel()
        self.license_status.setWordWrap(True)
        self.license_hint = QLabel()
        self.license_hint.setWordWrap(True)
        self.license_machine = QLabel()
        self.license_key = QLineEdit()
        self.license_activate = QPushButton()
        self.license_deactivate = QPushButton()
        self.license_deactivate.setObjectName("ghostButton")

        general = QWidget()
        form = QFormLayout(general)
        form.addRow(self.lang_label, self.language_combo)
        form.addRow(self.theme_label, self.theme_combo)
        form.addRow(self.refresh_interval_label, self.refresh_interval_combo)
        form.addRow(self.list_limit_label, self.list_limit_combo)
        form.addRow(self.provider_label, self.provider_combo)
        form.addRow(self.key_label, self.api_key)
        form.addRow(self.key_hint)
        form.addRow(self.url_label, self.ollama_url)
        form.addRow(self.model_label, self.ollama_model)
        form.addRow(self.auto_ai_summary)
        form.addRow(self.retention_label, self.retention_combo)
        form.addRow(self.font_label, self.font_combo)
        form.addRow(self.alert_label, self.alert_edit)
        form.addRow(self.briefing_hour_label, self.briefing_hour_combo)
        form.addRow(self.cluster_headlines)
        form.addRow(self.minimize_tray)
        form.addRow(self.start_windows)
        form.addRow(self.notify_alerts)
        form.addRow(self.proxy_edit)
        form.addRow(self.quiet_start)
        form.addRow(self.quiet_end)
        form.addRow(self.tape_speed)
        form.addRow(self.hide_tape)
        form.addRow(self.compact_tape)
        form.addRow(self.compact_list)
        form.addRow(self.two_pane)
        form.addRow(self.low_data)
        form.addRow(self.relative_time)
        form.addRow(self.alert_beep)
        form.addRow(self.intraday)
        form.addRow(self.auto_update)
        form.addRow(self.github_repo)
        form.addRow(self.sync_folder)
        help_row = QHBoxLayout()
        help_row.addWidget(self.help_site_btn)
        help_row.addWidget(self.help_privacy_btn)
        help_row.addWidget(self.help_refund_btn)
        help_row.addWidget(self.help_email_btn)
        form.addRow(help_row)
        extra_row = QHBoxLayout()
        extra_row.addWidget(self.vacuum_btn)
        extra_row.addWidget(self.cache_btn)
        extra_row.addWidget(self.about_btn)
        extra_row.addWidget(self.mini_tape_btn)
        form.addRow(extra_row)
        pack_row = QHBoxLayout()
        pack_row.addWidget(self.pack_tr)
        pack_row.addWidget(self.pack_us)
        pack_row.addWidget(self.pack_eu)
        pack_row.addWidget(self.pack_mastodon)
        form.addRow(pack_row)
        backup_row = QHBoxLayout()
        backup_row.addWidget(self.backup_btn)
        backup_row.addWidget(self.restore_btn)
        form.addRow(backup_row)

        general_scroll = QScrollArea()
        general_scroll.setWidgetResizable(True)
        general_scroll.setFrameShape(QFrame.Shape.NoFrame)
        general_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        general_scroll.setWidget(general)

        modules_tab = QWidget()
        modules_layout = QVBoxLayout(modules_tab)
        modules_layout.addWidget(self.modules_label)
        modules_layout.addWidget(self.modules_hint)
        modules_layout.addWidget(self.catalog_tree, 1)

        filters_tab = QWidget()
        filters_layout = QVBoxLayout(filters_tab)
        filters_layout.addWidget(self.filters_hint)
        add_row = QHBoxLayout()
        add_row.addWidget(self.filter_keyword, 1)
        add_row.addWidget(self.filter_type)
        add_row.addWidget(self.filter_add)
        filters_layout.addLayout(add_row)
        filters_layout.addWidget(self.filter_list, 1)
        filters_layout.addWidget(self.filter_remove, 0, Qt.AlignmentFlag.AlignLeft)

        self.tabs.addTab(general_scroll, "")
        self.tabs.addTab(modules_tab, "")
        self.tabs.addTab(filters_tab, "")
        self.sources_panel = SourcesTab(self._db, self._i18n)
        self._sources_tab_index = self.tabs.addTab(self.sources_panel, "")
        self.social_panel = SocialFollowsTab(self._db, self._i18n)
        self._social_tab_index = self.tabs.addTab(self.social_panel, "")
        self.tutorial_panel = TutorialPanel(self._i18n)
        self._tutorial_tab_index = self.tabs.addTab(self.tutorial_panel, "")
        tickers_tab = QWidget()
        tickers_layout = QVBoxLayout(tickers_tab)
        tickers_layout.addWidget(self.tickers_hint)
        tickers_layout.addWidget(self.tickers_current_label)
        tickers_layout.addWidget(self.ticker_list, 1)
        tickers_layout.addWidget(self.ticker_remove, 0, Qt.AlignmentFlag.AlignLeft)
        tickers_layout.addWidget(self.ticker_search)
        tickers_layout.addWidget(self.ticker_preset)
        ticker_add_row = QHBoxLayout()
        ticker_add_row.addWidget(self.ticker_symbol, 2)
        ticker_add_row.addWidget(self.ticker_label_edit, 2)
        ticker_add_row.addWidget(self.ticker_add)
        tickers_layout.addLayout(ticker_add_row)
        self._tickers_tab_index = self.tabs.addTab(tickers_tab, "")
        license_tab = QWidget()
        license_layout = QVBoxLayout(license_tab)
        license_layout.addWidget(self.license_status)
        license_layout.addWidget(self.license_machine)
        license_layout.addWidget(self.license_hint)
        license_layout.addWidget(self.license_key)
        license_row = QHBoxLayout()
        license_row.addWidget(self.license_activate)
        license_row.addWidget(self.license_deactivate)
        license_row.addStretch(1)
        license_layout.addLayout(license_row)
        license_layout.addStretch(1)
        self._license_tab_index = self.tabs.addTab(license_tab, "")

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(self.close_btn)
        buttons.addWidget(self.save_btn)

        layout = QVBoxLayout(self)
        layout.addWidget(self.tabs, 1)
        layout.addLayout(buttons)

        self.close_btn.clicked.connect(self.reject)
        self.save_btn.clicked.connect(self._save)
        self.filter_add.clicked.connect(self._add_filter)
        self.filter_remove.clicked.connect(self._remove_filter)
        self.filter_keyword.returnPressed.connect(self._add_filter)
        self.ticker_add.clicked.connect(self._add_ticker)
        self.ticker_remove.clicked.connect(self._remove_ticker)
        self.ticker_symbol.returnPressed.connect(self._add_ticker)
        self.ticker_preset.activated.connect(self._on_ticker_preset)
        self.ticker_search.textChanged.connect(self._on_ticker_search_changed)
        self.pack_tr.clicked.connect(lambda: self._apply_pack("tr"))
        self.pack_us.clicked.connect(lambda: self._apply_pack("us"))
        self.pack_eu.clicked.connect(lambda: self._apply_pack("eu"))
        self.pack_mastodon.clicked.connect(lambda: self._apply_pack("mastodon"))
        self.backup_btn.clicked.connect(self._backup)
        self.restore_btn.clicked.connect(self._restore)
        self.vacuum_btn.clicked.connect(self._vacuum)
        self.cache_btn.clicked.connect(self._clear_cache)
        self.about_btn.clicked.connect(self._about)
        self.mini_tape_btn.clicked.connect(self._mini_tape)
        self.help_site_btn.clicked.connect(lambda: self._open_help("https://younews.media"))
        self.help_privacy_btn.clicked.connect(lambda: self._open_help("https://younews.media/privacy.html"))
        self.help_refund_btn.clicked.connect(lambda: self._open_help("https://younews.media/refund.html"))
        self.help_email_btn.clicked.connect(lambda: self._open_help("mailto:hello@younews.media"))
        self.license_activate.clicked.connect(self._activate_license)
        self.license_deactivate.clicked.connect(self._deactivate_license)
        self.catalog_tree.itemChanged.connect(self._on_catalog_item_changed)

        self.retranslate()
        self._load()
        self.provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        self.theme_combo.currentIndexChanged.connect(self._on_theme)
        self.tutorial_panel.open_settings_requested.connect(self._show_tab)
        self.sources_changed = False
        self.setMinimumSize(480, 400)
        self._fit_to_screen()
        if initial_tab:
            self._show_tab(initial_tab)

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        if not self._fitted:
            self._fit_to_screen()
            self._fitted = True

    def _fit_to_screen(self) -> None:
        screen = self.screen() or QGuiApplication.primaryScreen()
        if screen is None:
            self.resize(680, 640)
            return
        avail = screen.availableGeometry()
        margin = 56
        max_w = max(520, avail.width() - margin)
        max_h = max(420, avail.height() - margin)
        width = min(720, max_w)
        height = min(640, max_h)
        self.setMaximumSize(max_w, max_h)
        self.resize(width, height)
        self.tabs.setMaximumWidth(max(400, max_w - 24))
        frame = self.frameGeometry()
        frame.moveCenter(avail.center())
        self.move(frame.topLeft())

    def _show_tab(self, name: str) -> None:
        mapping = {
            "filters": 2,
            "sources": self._sources_tab_index,
            "social": self._social_tab_index,
            "tickers": self._tickers_tab_index,
            "tutorials": self._tutorial_tab_index,
            "license": self._license_tab_index,
        }
        index = mapping.get(name)
        if index is not None:
            self.tabs.setCurrentIndex(index)

    def retranslate(self) -> None:
        self.setWindowTitle(self._i18n.t("app.settings"))
        self.tabs.setTabText(0, self._i18n.t("app.settings"))
        self.tabs.setTabText(1, self._i18n.t("app.module_manager"))
        self.tabs.setTabText(2, self._i18n.t("filters.title"))
        self.tabs.setTabText(self._sources_tab_index, self._i18n.t("sources.title"))
        self.tabs.setTabText(self._social_tab_index, self._i18n.t("social.title"))
        self.tabs.setTabText(self._tutorial_tab_index, self._i18n.t("tutorial.title"))
        self.tabs.setTabText(self._tickers_tab_index, self._i18n.t("tickers.title"))
        self.tabs.setTabText(self._license_tab_index, self._i18n.t("license.tab"))
        self.license_activate.setText(self._i18n.t("license.activate"))
        self.license_deactivate.setText(self._i18n.t("license.deactivate"))
        self.license_hint.setText(self._i18n.t("license.hint"))
        self.license_key.setPlaceholderText(self._i18n.t("license.placeholder"))
        self._refresh_license_tab()
        self.lang_label.setText(self._i18n.t("app.language"))
        self.theme_label.setText(self._i18n.t("app.theme"))
        self.refresh_interval_label.setText(self._i18n.t("app.refresh_interval"))
        self.list_limit_label.setText(self._i18n.t("app.list_limit"))
        self.provider_label.setText(self._i18n.t("app.provider"))
        self.key_label.setText(self._i18n.t("app.api_key"))
        self.key_hint.setText(self._i18n.t("app.api_key_hint"))
        self.url_label.setText(self._i18n.t("app.ollama_url"))
        self.model_label.setText(self._i18n.t("app.ollama_model"))
        self.auto_ai_summary.setText(self._i18n.t("ai.auto_summary"))
        self.retention_label.setText(self._i18n.t("app.retention"))
        self.font_label.setText(self._i18n.t("app.font_scale"))
        self.alert_label.setText(self._i18n.t("tickers.alert_pct"))
        self.briefing_hour_label.setText(self._i18n.t("ai.briefing_hour"))
        self.cluster_headlines.setText(self._i18n.t("app.cluster_headlines"))
        self.minimize_tray.setText(self._i18n.t("app.minimize_tray"))
        self.start_windows.setText(self._i18n.t("app.start_windows"))
        self.notify_alerts.setText(self._i18n.t("app.notify_alerts"))
        self.proxy_edit.setPlaceholderText(self._i18n.t("app.proxy"))
        self.hide_tape.setText(self._i18n.t("app.hide_tape"))
        self.compact_tape.setText(self._i18n.t("app.compact_tape"))
        self.compact_list.setText(self._i18n.t("app.compact_list"))
        self.two_pane.setText(self._i18n.t("app.two_pane"))
        self.low_data.setText(self._i18n.t("app.low_data"))
        self.relative_time.setText(self._i18n.t("app.relative_time"))
        self.alert_beep.setText(self._i18n.t("app.alert_beep"))
        self.intraday.setText(self._i18n.t("app.intraday"))
        self.auto_update.setText(self._i18n.t("app.auto_update"))
        self.github_repo.setPlaceholderText(self._i18n.t("app.github_repo"))
        self.github_repo.setVisible(False)
        self.sync_folder.setPlaceholderText(self._i18n.t("app.sync_folder"))
        self.vacuum_btn.setText(self._i18n.t("app.vacuum"))
        self.cache_btn.setText(self._i18n.t("app.clear_cache"))
        self.about_btn.setText(self._i18n.t("app.about"))
        self.mini_tape_btn.setText(self._i18n.t("app.mini_tape"))
        self.help_site_btn.setText(self._i18n.t("app.help_site"))
        self.help_privacy_btn.setText(self._i18n.t("app.help_privacy"))
        self.help_refund_btn.setText(self._i18n.t("app.help_refund"))
        self.help_email_btn.setText(self._i18n.t("app.help_email"))
        self.quiet_start.clear()
        self.quiet_end.clear()
        self.quiet_start.addItem(self._i18n.t("app.quiet_off"), -1)
        self.quiet_end.addItem(self._i18n.t("app.quiet_off"), -1)
        for hour in range(24):
            self.quiet_start.addItem(f"{hour:02d}:00", hour)
            self.quiet_end.addItem(f"{hour:02d}:00", hour)
        self.tape_speed.clear()
        for pct in (50, 100, 150, 200):
            self.tape_speed.addItem(f"{pct}%", pct)
        self.pack_tr.setText(self._i18n.t("sources.pack_tr"))
        self.pack_us.setText(self._i18n.t("sources.pack_us"))
        self.pack_eu.setText(self._i18n.t("sources.pack_eu"))
        self.pack_mastodon.setText(self._i18n.t("sources.pack_mastodon"))
        self.backup_btn.setText(self._i18n.t("app.backup"))
        self.restore_btn.setText(self._i18n.t("app.restore"))
        self.modules_label.setText(self._i18n.t("app.modules"))
        self.modules_hint.setText(self._i18n.t("app.modules_hint"))
        self.filters_hint.setText(self._i18n.t("filters.hint"))
        self.filter_keyword.setPlaceholderText(self._i18n.t("filters.keyword"))
        self.filter_add.setText(self._i18n.t("filters.add"))
        self.filter_remove.setText(self._i18n.t("filters.remove"))
        self.tickers_hint.setText(self._i18n.t("tickers.search_hint"))
        self.tickers_current_label.setText(self._i18n.t("tickers.current"))
        self.ticker_search.setPlaceholderText(self._i18n.t("tickers.search_placeholder"))
        self.ticker_symbol.setPlaceholderText(self._i18n.t("tickers.symbol_placeholder"))
        self.ticker_label_edit.setPlaceholderText(self._i18n.t("tickers.label_placeholder"))
        self.ticker_add.setText(self._i18n.t("tickers.add"))
        self.ticker_remove.setText(self._i18n.t("tickers.remove"))
        self._rebuild_ticker_presets()
        self.save_btn.setText(self._i18n.t("app.save"))
        self.close_btn.setText(self._i18n.t("app.close"))
        current_theme = self.theme_combo.currentData()
        self.theme_combo.blockSignals(True)
        self.theme_combo.clear()
        self.theme_combo.addItem(self._i18n.t("app.theme_system"), "system")
        self.theme_combo.addItem(self._i18n.t("app.theme_dark"), "dark")
        self.theme_combo.addItem(self._i18n.t("app.theme_light"), "light")
        self.theme_combo.addItem(self._i18n.t("app.theme_contrast"), "high_contrast")
        if current_theme:
            idx = self.theme_combo.findData(current_theme)
            if idx >= 0:
                self.theme_combo.setCurrentIndex(idx)
        self.theme_combo.blockSignals(False)
        current_provider = self.provider_combo.currentData()
        self.provider_combo.blockSignals(True)
        self.provider_combo.clear()
        for provider, label_key in PROVIDER_LABEL_KEYS:
            self.provider_combo.addItem(self._i18n.t(label_key), provider)
        if current_provider:
            idx = self.provider_combo.findData(current_provider)
            if idx >= 0:
                self.provider_combo.setCurrentIndex(idx)
        self.provider_combo.blockSignals(False)
        current_interval = self.refresh_interval_combo.currentData()
        self.refresh_interval_combo.blockSignals(True)
        self.refresh_interval_combo.clear()
        for minutes in FEED_REFRESH_MINUTES:
            self.refresh_interval_combo.addItem(self._i18n.t(FEED_REFRESH_INTERVAL_KEYS[minutes]), minutes)
        if current_interval is not None:
            idx = self.refresh_interval_combo.findData(int(current_interval))
            if idx >= 0:
                self.refresh_interval_combo.setCurrentIndex(idx)
        self.refresh_interval_combo.blockSignals(False)
        current_ret = self.retention_combo.currentData()
        self.retention_combo.blockSignals(True)
        self.retention_combo.clear()
        for hours in ARTICLE_RETENTION_OPTIONS:
            key = "app.retention_off" if hours == 0 else "app.retention_hours"
            label = self._i18n.t(key).replace("{hours}", str(hours))
            self.retention_combo.addItem(label, hours)
        if current_ret is not None:
            idx = self.retention_combo.findData(int(current_ret))
            if idx >= 0:
                self.retention_combo.setCurrentIndex(idx)
        self.retention_combo.blockSignals(False)
        current_font = self.font_combo.currentData()
        self.font_combo.blockSignals(True)
        self.font_combo.clear()
        for scale in FONT_SCALE_OPTIONS:
            self.font_combo.addItem(f"{scale}%", scale)
        if current_font is not None:
            idx = self.font_combo.findData(int(current_font))
            if idx >= 0:
                self.font_combo.setCurrentIndex(idx)
        self.font_combo.blockSignals(False)
        current_hour = self.briefing_hour_combo.currentData()
        self.briefing_hour_combo.blockSignals(True)
        self.briefing_hour_combo.clear()
        self.briefing_hour_combo.addItem(self._i18n.t("ai.briefing_hour_off"), -1)
        for hour in range(24):
            self.briefing_hour_combo.addItem(f"{hour:02d}:00", hour)
        if current_hour is not None:
            idx = self.briefing_hour_combo.findData(int(current_hour))
            if idx >= 0:
                self.briefing_hour_combo.setCurrentIndex(idx)
        self.briefing_hour_combo.blockSignals(False)
        current_limit = self.list_limit_combo.currentData()
        self.list_limit_combo.blockSignals(True)
        self.list_limit_combo.clear()
        for limit in ARTICLE_LIST_LIMIT_OPTIONS:
            self.list_limit_combo.addItem(
                self._i18n.t("app.list_limit_option").replace("{count}", str(limit)),
                limit,
            )
        if current_limit is not None:
            idx = self.list_limit_combo.findData(int(current_limit))
            if idx >= 0:
                self.list_limit_combo.setCurrentIndex(idx)
        self.list_limit_combo.blockSignals(False)
        current_filter = self.filter_type.currentData()
        self.filter_type.blockSignals(True)
        self.filter_type.clear()
        self.filter_type.addItem(self._i18n.t("filters.whitelist"), "whitelist")
        self.filter_type.addItem(self._i18n.t("filters.blacklist"), "blacklist")
        if current_filter:
            idx = self.filter_type.findData(current_filter)
            if idx >= 0:
                self.filter_type.setCurrentIndex(idx)
        self.filter_type.blockSignals(False)
        self._relabel_catalog_tree()
        self._reload_filters()
        self.sources_panel.retranslate()
        self.social_panel.retranslate()
        self.tutorial_panel.retranslate()
        self._apply_provider_fields(self.provider_combo.currentData() or "openai", stash=False)
        self._refresh_license_tab()

    def _load(self) -> None:
        lang = self._i18n.language
        if self.language_combo.findData(lang) < 0 and lang in SUPPORTED_LANGUAGES:
            self.language_combo.addItem(SUPPORTED_LANGUAGES[lang], lang)
        index = self.language_combo.findData(lang)
        if index >= 0:
            self.language_combo.setCurrentIndex(index)
        theme = normalize_theme(self._db.get_setting("theme", DEFAULT_THEME))
        t_index = self.theme_combo.findData(theme)
        if t_index >= 0:
            self.theme_combo.setCurrentIndex(t_index)
        provider = self._db.get_setting("ai_provider", "openai")
        p_index = self.provider_combo.findData(provider)
        if p_index >= 0:
            self.provider_combo.setCurrentIndex(p_index)
        minutes = parse_feed_refresh_minutes(self._db.get_setting("feed_refresh_minutes"))
        r_index = self.refresh_interval_combo.findData(minutes)
        if r_index >= 0:
            self.refresh_interval_combo.setCurrentIndex(r_index)
        limit = parse_article_list_limit(self._db.get_setting("article_list_limit"))
        l_index = self.list_limit_combo.findData(limit)
        if l_index >= 0:
            self.list_limit_combo.setCurrentIndex(l_index)
        provider = normalize_ai_provider(self._db.get_setting("ai_provider", "openai"))
        self._draft_keys = {pid: get_provider_api_key(pid) or "" for pid in CLOUD_AI_PROVIDERS}
        self._draft_models = {
            pid: self._db.get_setting(provider_model_setting_key(pid)) or "" for pid in AI_PROVIDERS
        }
        self.ollama_url.setText(self._db.get_setting("ollama_url") or "")
        self._fields_provider = None
        self._apply_provider_fields(provider, stash=False)
        self.auto_ai_summary.setChecked(self._db.get_setting("auto_ai_summary", "0") == "1")
        self.cluster_headlines.setChecked(self._db.get_setting("cluster_headlines", "1") == "1")
        self.minimize_tray.setChecked(self._db.get_setting("minimize_to_tray", "1") == "1")
        self.start_windows.setChecked(self._db.get_setting("start_with_windows", "0") == "1")
        self.notify_alerts.setChecked(self._db.get_setting("notify_alerts", "1") == "1")
        self.hide_tape.setChecked(self._db.get_setting("hide_tape", "0") == "1")
        self.compact_tape.setChecked(self._db.get_setting("compact_tape", "0") == "1")
        self.compact_list.setChecked(self._db.get_setting("compact_list", "0") == "1")
        self.two_pane.setChecked(self._db.get_setting("two_pane", "0") == "1")
        self.low_data.setChecked(self._db.get_setting("low_data", "0") == "1")
        self.relative_time.setChecked(self._db.get_setting("relative_time", "1") == "1")
        self.alert_beep.setChecked(self._db.get_setting("alert_beep", "1") == "1")
        self.intraday.setChecked(self._db.get_setting("intraday_quotes", "1") == "1")
        self.auto_update.setChecked(self._db.get_setting("auto_update_check", "0") == "1")
        self.proxy_edit.setText(self._db.get_setting("proxy_url") or "")
        self.github_repo.setText(self._db.get_setting("github_repo") or "")
        self.sync_folder.setText(self._db.get_setting("sync_folder") or "")
        try:
            qs = int(self._db.get_setting("quiet_start", "-1") or "-1")
            qe = int(self._db.get_setting("quiet_end", "-1") or "-1")
            sp = int(self._db.get_setting("tape_speed", "100") or "100")
        except ValueError:
            qs, qe, sp = -1, -1, 100
        idx = self.quiet_start.findData(qs)
        if idx >= 0:
            self.quiet_start.setCurrentIndex(idx)
        idx = self.quiet_end.findData(qe)
        if idx >= 0:
            self.quiet_end.setCurrentIndex(idx)
        idx = self.tape_speed.findData(sp)
        if idx >= 0:
            self.tape_speed.setCurrentIndex(idx)
        self.alert_edit.setText(self._db.get_setting("ticker_alert_pct", "2") or "2")
        r_hours = parse_retention_hours(self._db.get_setting("article_retention_hours"))
        idx = self.retention_combo.findData(r_hours)
        if idx >= 0:
            self.retention_combo.setCurrentIndex(idx)
        scale = parse_font_scale(self._db.get_setting("ui_font_scale"))
        idx = self.font_combo.findData(scale)
        if idx >= 0:
            self.font_combo.setCurrentIndex(idx)
        try:
            hour = int(self._db.get_setting("scheduled_briefing_hour", "-1") or "-1")
        except ValueError:
            hour = -1
        idx = self.briefing_hour_combo.findData(hour)
        if idx >= 0:
            self.briefing_hour_combo.setCurrentIndex(idx)
        self._load_catalog_tree()
        self._reload_filters()
        self._load_tickers()
        self.social_panel.reload()

    def _topic_label(self, topic) -> str:
        return self._i18n.t(topic.name_key, topic.id)

    def _load_catalog_tree(self) -> None:
        self._catalog_syncing = True
        self.catalog_tree.clear()
        flags = (
            Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsSelectable
            | Qt.ItemFlag.ItemIsUserCheckable
        )
        for module in self._db.list_modules():
            root = QTreeWidgetItem([self._i18n.t(module.name_key, module.id)])
            root.setFlags(flags)
            root.setCheckState(0, Qt.CheckState.Checked if module.is_active else Qt.CheckState.Unchecked)
            root.setData(0, Qt.ItemDataRole.UserRole, ("module", module.id))
            self.catalog_tree.addTopLevelItem(root)
            topics = self._db.list_topics(module.id, active_only=False)
            by_parent: dict[str | None, list] = {}
            for topic in topics:
                by_parent.setdefault(topic.parent_id, []).append(topic)

            def add_children(parent_item: QTreeWidgetItem, parent_id: str | None) -> None:
                for topic in by_parent.get(parent_id, []):
                    child = QTreeWidgetItem([self._topic_label(topic)])
                    child.setFlags(flags)
                    child.setCheckState(0, Qt.CheckState.Checked if topic.is_active else Qt.CheckState.Unchecked)
                    child.setData(0, Qt.ItemDataRole.UserRole, ("topic", topic.id))
                    parent_item.addChild(child)
                    add_children(child, topic.id)

            add_children(root, None)
            root.setExpanded(True)
            for index in range(root.childCount()):
                root.child(index).setExpanded(True)
        self._catalog_syncing = False

    def _relabel_catalog_tree(self) -> None:
        if self.catalog_tree.topLevelItemCount() == 0:
            return
        topics = {topic.id: topic for topic in self._db.list_topics()}
        modules = {module.id: module for module in self._db.list_modules()}

        def walk(item: QTreeWidgetItem) -> None:
            kind, ident = item.data(0, Qt.ItemDataRole.UserRole) or (None, None)
            if kind == "module" and ident in modules:
                module = modules[ident]
                item.setText(0, self._i18n.t(module.name_key, module.id))
            elif kind == "topic" and ident in topics:
                item.setText(0, self._topic_label(topics[ident]))
            for index in range(item.childCount()):
                walk(item.child(index))

        for index in range(self.catalog_tree.topLevelItemCount()):
            walk(self.catalog_tree.topLevelItem(index))

    def _set_item_tree_check(self, item: QTreeWidgetItem, state: Qt.CheckState) -> None:
        item.setCheckState(0, state)
        for index in range(item.childCount()):
            self._set_item_tree_check(item.child(index), state)

    def _on_catalog_item_changed(self, item: QTreeWidgetItem, _column: int) -> None:
        if self._catalog_syncing:
            return
        self._catalog_syncing = True
        state = item.checkState(0)
        for index in range(item.childCount()):
            self._set_item_tree_check(item.child(index), state)
        self._catalog_syncing = False

    def _walk_catalog(self) -> list[tuple[str, str, bool]]:
        rows: list[tuple[str, str, bool]] = []

        def walk(item: QTreeWidgetItem) -> None:
            payload = item.data(0, Qt.ItemDataRole.UserRole)
            if payload:
                kind, ident = payload
                rows.append((kind, ident, item.checkState(0) == Qt.CheckState.Checked))
            for index in range(item.childCount()):
                walk(item.child(index))

        for index in range(self.catalog_tree.topLevelItemCount()):
            walk(self.catalog_tree.topLevelItem(index))
        return rows

    def _catalog_module_states(self) -> dict[str, bool]:
        return {ident: active for kind, ident, active in self._walk_catalog() if kind == "module"}

    def _catalog_topic_states(self) -> dict[str, bool]:
        return {ident: active for kind, ident, active in self._walk_catalog() if kind == "topic"}

    def _on_provider_changed(self, _index: int = 0) -> None:
        self._apply_provider_fields(self.provider_combo.currentData() or "openai", stash=True)

    def _stash_provider_fields(self) -> None:
        provider = self._fields_provider
        if not provider:
            return
        if provider in PROVIDER_KEY_ACCOUNTS:
            self._draft_keys[provider] = self.api_key.text()
        self._draft_models[provider] = self.ollama_model.text()

    def _apply_provider_fields(self, provider: str, *, stash: bool) -> None:
        if stash:
            self._stash_provider_fields()
        self._fields_provider = provider
        needs_key = provider in PROVIDER_KEY_ACCOUNTS
        self.api_key.setVisible(needs_key)
        self.key_label.setVisible(needs_key)
        self.key_hint.setVisible(needs_key)
        self.ollama_url.setVisible(provider == "ollama")
        self.url_label.setVisible(provider == "ollama")
        self.api_key.setText(self._draft_keys.get(provider, "") if needs_key else "")
        self.ollama_model.setText(self._draft_models.get(provider, ""))
        self.ollama_model.setPlaceholderText(DEFAULT_AI_MODELS.get(provider, ""))
        if provider == "ollama":
            self.model_label.setText(self._i18n.t("app.ollama_model"))
        else:
            self.model_label.setText(self._i18n.t("app.ai_model"))

    def _reload_filters(self) -> None:
        self.filter_list.clear()
        for item in self._db.list_filters(active_only=False):
            kind = self._i18n.t("filters.whitelist" if item.filter_type == "whitelist" else "filters.blacklist")
            row = QListWidgetItem(f"{kind}: {item.keyword}")
            row.setData(Qt.ItemDataRole.UserRole, item.id)
            self.filter_list.addItem(row)

    def _add_filter(self) -> None:
        keyword = self.filter_keyword.text().strip()
        if not keyword:
            QMessageBox.information(self, self._i18n.t("filters.title"), self._i18n.t("filters.empty_keyword"))
            return
        added = self._db.add_filter(keyword, self.filter_type.currentData() or "blacklist")
        if added:
            self.filter_keyword.clear()
            self._reload_filters()

    def _remove_filter(self) -> None:
        row = self.filter_list.currentItem()
        if row is None:
            return
        filter_id = row.data(Qt.ItemDataRole.UserRole)
        if filter_id is not None:
            self._db.delete_filter(int(filter_id))
            self._reload_filters()

    def _on_ticker_search_changed(self, _text: str = "") -> None:
        query = self.ticker_search.text().strip()
        if _fold(query) != _fold(self._yahoo_query):
            self._yahoo_hits = []
            self._yahoo_query = ""
        self._rebuild_ticker_presets()
        if len(_fold(query)) < 2:
            self._ticker_debounce.stop()
            return
        self._ticker_debounce.start()

    def _start_yahoo_ticker_search(self) -> None:
        query = self.ticker_search.text().strip()
        if len(_fold(query)) < 2:
            return
        worker = YahooLookupWorker(query, self)
        worker.finished_ok.connect(self._on_yahoo_tickers)
        worker.finished.connect(worker.deleteLater)
        worker.start()
        self._yahoo_thread = worker

    def _on_yahoo_tickers(self, query: str, items: list) -> None:
        if _fold(query) != _fold(self.ticker_search.text()):
            return
        self._yahoo_query = query
        self._yahoo_hits = [item for item in items if isinstance(item, CatalogTicker)]
        self._rebuild_ticker_presets()

    def _rebuild_ticker_presets(self) -> None:
        current = self.ticker_preset.currentData()
        self.ticker_preset.blockSignals(True)
        self.ticker_preset.clear()
        self.ticker_preset.addItem(self._i18n.t("tickers.presets"), None)
        last_cat = None
        query = self.ticker_search.text() if hasattr(self, "ticker_search") else ""
        yahoo = self._yahoo_hits if _fold(self._yahoo_query) == _fold(query) else []
        local_symbols = {item.symbol.casefold() for item in search_catalog(query, limit=80)}
        items = merge_ticker_search(query, yahoo, catalog_limit=80, total_limit=120)
        yahoo_header_done = False
        for item in items:
            is_yahoo = item.symbol.casefold() not in local_symbols
            if is_yahoo and not yahoo_header_done:
                self.ticker_preset.addItem(f"— {self._i18n.t('tickers.yahoo_section')} —", None)
                header_item = self.ticker_preset.model().item(self.ticker_preset.count() - 1)
                if header_item is not None:
                    header_item.setEnabled(False)
                yahoo_header_done = True
                last_cat = None
            elif not is_yahoo and item.category != last_cat:
                header = self._i18n.t(f"tickers.cat.{item.category}", item.category.title())
                self.ticker_preset.addItem(f"— {header} —", None)
                header_item = self.ticker_preset.model().item(self.ticker_preset.count() - 1)
                if header_item is not None:
                    header_item.setEnabled(False)
                last_cat = item.category
            self.ticker_preset.addItem(f"{item.label}  ·  {item.country}", (item.symbol, item.label))
        if current:
            idx = self.ticker_preset.findData(current)
            if idx >= 0:
                self.ticker_preset.setCurrentIndex(idx)
        self.ticker_preset.blockSignals(False)

    def _load_tickers(self) -> None:
        self._ticker_rows = [(item.symbol, item.label) for item in self._db.list_tickers()]
        self._refresh_ticker_list()

    def _refresh_ticker_list(self) -> None:
        self.ticker_list.clear()
        for symbol, label in self._ticker_rows:
            row = QListWidgetItem(f"{label}  ({symbol})")
            row.setData(Qt.ItemDataRole.UserRole, (symbol, label))
            self.ticker_list.addItem(row)

    def _on_ticker_preset(self, _index: int) -> None:
        data = self.ticker_preset.currentData()
        if not data:
            return
        self.ticker_symbol.setText(str(data[0]))
        self.ticker_label_edit.setText(str(data[1]))

    def _add_ticker(self) -> None:
        typed = self.ticker_symbol.text().strip()
        label = self.ticker_label_edit.text().strip()
        preset = self.ticker_preset.currentData()
        symbol = typed
        yahoo_like = any(ch in typed for ch in "^=.") or (typed.isupper() and len(typed) <= 6)
        if preset and (
            not typed
            or typed.casefold() in {str(preset[0]).casefold(), str(preset[1]).casefold()}
        ):
            symbol = str(preset[0])
            label = label or str(preset[1])
        elif typed and not yahoo_like:
            query = self.ticker_search.text().strip() or typed
            yahoo = self._yahoo_hits if _fold(self._yahoo_query) == _fold(query) else []
            matches = merge_ticker_search(typed, yahoo, catalog_limit=8, total_limit=16)
            if matches:
                pick = next(
                    (
                        item
                        for item in matches
                        if item.label.casefold() == typed.casefold()
                        or item.symbol.casefold() == typed.casefold()
                    ),
                    matches[0],
                )
                symbol = pick.symbol
                label = label or pick.label
        if not symbol:
            QMessageBox.information(
                self, self._i18n.t("tickers.title"), self._i18n.t("tickers.empty_symbol")
            )
            return
        label = label or symbol
        if any(existing.casefold() == symbol.casefold() for existing, _ in self._ticker_rows):
            QMessageBox.information(
                self, self._i18n.t("tickers.title"), self._i18n.t("tickers.duplicate")
            )
            return
        self._ticker_rows.append((symbol, label))
        self.ticker_symbol.clear()
        self.ticker_label_edit.clear()
        self._refresh_ticker_list()

    def _remove_ticker(self) -> None:
        row = self.ticker_list.currentRow()
        if row < 0 or row >= len(self._ticker_rows):
            return
        del self._ticker_rows[row]
        self._refresh_ticker_list()

    def _on_theme(self) -> None:
        theme = normalize_theme(self.theme_combo.currentData())
        self._db.set_setting("theme", theme)
        apply_app_theme(theme)
        self.theme_changed.emit(theme)

    def _save(self) -> None:
        language = self.language_combo.currentData()
        provider = self.provider_combo.currentData()
        theme = normalize_theme(self.theme_combo.currentData())
        self._db.set_setting("theme", theme)
        apply_app_theme(theme)
        self.theme_changed.emit(theme)
        interval = self.refresh_interval_combo.currentData()
        self._db.set_setting(
            "feed_refresh_minutes",
            str(parse_feed_refresh_minutes(None if interval is None else str(interval))),
        )
        list_limit = self.list_limit_combo.currentData()
        self._db.set_setting(
            "article_list_limit",
            str(parse_article_list_limit(None if list_limit is None else str(list_limit))),
        )
        self._stash_provider_fields()
        provider = normalize_ai_provider(self.provider_combo.currentData())
        self._db.set_setting("ai_provider", provider)
        self._db.set_setting("ollama_url", self.ollama_url.text().strip())
        self._db.set_setting("auto_ai_summary", "1" if self.auto_ai_summary.isChecked() else "0")
        self._db.set_setting("cluster_headlines", "1" if self.cluster_headlines.isChecked() else "0")
        self._db.set_setting("minimize_to_tray", "1" if self.minimize_tray.isChecked() else "0")
        self._db.set_setting("start_with_windows", "1" if self.start_windows.isChecked() else "0")
        self._db.set_setting("notify_alerts", "1" if self.notify_alerts.isChecked() else "0")
        self._db.set_setting("hide_tape", "1" if self.hide_tape.isChecked() else "0")
        self._db.set_setting("compact_tape", "1" if self.compact_tape.isChecked() else "0")
        self._db.set_setting("compact_list", "1" if self.compact_list.isChecked() else "0")
        self._db.set_setting("two_pane", "1" if self.two_pane.isChecked() else "0")
        self._db.set_setting("low_data", "1" if self.low_data.isChecked() else "0")
        self._db.set_setting("relative_time", "1" if self.relative_time.isChecked() else "0")
        self._db.set_setting("alert_beep", "1" if self.alert_beep.isChecked() else "0")
        self._db.set_setting("intraday_quotes", "1" if self.intraday.isChecked() else "0")
        self._db.set_setting("auto_update_check", "1" if self.auto_update.isChecked() else "0")
        self._db.set_setting("proxy_url", self.proxy_edit.text().strip())
        self._db.set_setting("github_repo", self.github_repo.text().strip())
        self._db.set_setting("sync_folder", self.sync_folder.text().strip())
        self._db.set_setting("quiet_start", str(self.quiet_start.currentData()))
        self._db.set_setting("quiet_end", str(self.quiet_end.currentData()))
        self._db.set_setting("tape_speed", str(self.tape_speed.currentData() or 100))
        from core.app_extras import apply_proxy_setting, set_windows_startup

        apply_proxy_setting(self.proxy_edit.text().strip())
        set_windows_startup(self.start_windows.isChecked())
        self._db.set_setting("ui_font_scale", str(self.font_combo.currentData() or 100))
        self._db.set_setting("ticker_alert_pct", str(parse_alert_pct(self.alert_edit.text())))
        hour = self.briefing_hour_combo.currentData()
        self._db.set_setting("scheduled_briefing_hour", str(-1 if hour is None else hour))
        self._db.set_setting("article_retention_hours", str(self.retention_combo.currentData() or 24))
        for pid, key in self._draft_keys.items():
            if key.strip():
                set_provider_api_key(pid, key)
        for pid, model in self._draft_models.items():
            self._db.set_setting(provider_model_setting_key(pid), model.strip())
        current_model = (self._draft_models.get(provider) or "").strip()
        self._db.set_setting("ai_model", current_model or DEFAULT_AI_MODELS.get(provider, ""))
        for module_id, active in self._catalog_module_states().items():
            self._db.set_module_active(module_id, active)
        for topic_id, active in self._catalog_topic_states().items():
            self._db.set_topic_active(topic_id, active)
        ordered: list[tuple[str, str]] = []
        for row in range(self.ticker_list.count()):
            item = self.ticker_list.item(row)
            data = item.data(Qt.ItemDataRole.UserRole) if item else None
            if data:
                ordered.append((str(data[0]), str(data[1])))
        if ordered:
            self._ticker_rows = ordered
        self._db.replace_tickers(self._ticker_rows)
        if language:
            self._i18n.load(language)
        QMessageBox.information(self, self._i18n.t("app.settings"), self._i18n.t("app.saved"))
        self.accept()

    def _apply_pack(self, pack_id: str) -> None:
        from core.source_packs import apply_source_pack

        added = apply_source_pack(self._db, pack_id)
        self.sources_panel.reload()
        self.sources_changed = True
        QMessageBox.information(
            self,
            self._i18n.t("sources.title"),
            self._i18n.t("sources.opml_added").replace("{count}", str(added)),
        )

    def _backup(self) -> None:
        from pathlib import Path

        from core.app_extras import backup_database

        path, _filter = QFileDialog.getSaveFileName(self, self._i18n.t("app.backup"), "you-news-backup.db", "SQLite (*.db)")
        if not path:
            return
        backup_database(Path(path))

    def _restore(self) -> None:
        from pathlib import Path

        from core.app_extras import restore_database

        path, _filter = QFileDialog.getOpenFileName(self, self._i18n.t("app.restore"), "", "SQLite (*.db)")
        if not path:
            return
        restore_database(Path(path))
        QMessageBox.information(self, self._i18n.t("app.settings"), self._i18n.t("app.restore_done"))

    def _vacuum(self) -> None:
        from core.app_extras import vacuum_database

        vacuum_database()
        QMessageBox.information(self, self._i18n.t("app.settings"), self._i18n.t("app.vacuum_done"))

    def _clear_cache(self) -> None:
        from core.app_extras import clear_image_cache

        n = clear_image_cache()
        QMessageBox.information(self, self._i18n.t("app.settings"), self._i18n.t("app.cache_cleared").replace("{count}", str(n)))

    def _about(self) -> None:
        from ui.components.extra_windows import AboutDialog

        AboutDialog(self._i18n, self).exec()

    def _open_help(self, url: str) -> None:
        from PySide6.QtGui import QDesktopServices
        from PySide6.QtCore import QUrl

        QDesktopServices.openUrl(QUrl(url))

    def _mini_tape(self) -> None:
        self.mini_tape_requested.emit()

    def _refresh_license_tab(self) -> None:
        from core.license import license_status

        status = license_status()
        if status["activated"]:
            email = status["email"] or "—"
            self.license_status.setText(self._i18n.t("license.active").replace("{email}", email))
            if status["masked"]:
                self.license_key.setPlaceholderText(status["masked"])
        else:
            self.license_status.setText(self._i18n.t("license.inactive"))
        self.license_machine.setText(self._i18n.t("license.machine").replace("{id}", str(status["machine"])))
        self.license_deactivate.setEnabled(bool(status["activated"]))

    def _activate_license(self) -> None:
        from core.license import LicenseError, activate

        text = self.license_key.text()
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
        self.license_key.clear()
        self._refresh_license_tab()

    def _deactivate_license(self) -> None:
        from core.license import deactivate

        if QMessageBox.question(self, self._i18n.t("license.title"), self._i18n.t("license.deactivate_confirm")) != QMessageBox.StandardButton.Yes:
            return
        deactivate()
        self.license_key.clear()
        self._refresh_license_tab()
