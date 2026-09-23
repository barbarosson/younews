"""Main-screen watchlist: local presets plus live Yahoo Finance search."""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)

from core.i18n_manager import I18nManager
from core.ticker_catalog import QUICK_FILTERS, CatalogTicker, _fold, country_i18n_key, search_catalog
from core.yahoo_lookup import YahooLookupWorker, merge_ticker_search
from database.db import Database

ROLE_PAIR = Qt.ItemDataRole.UserRole


class WatchlistDialog(QDialog):
    watchlist_changed = Signal()

    def __init__(self, db: Database, i18n: I18nManager, parent=None) -> None:
        super().__init__(parent)
        self._db = db
        self._i18n = i18n
        self._yahoo_hits: list[CatalogTicker] = []
        self._yahoo_query = ""
        self._yahoo_thread: YahooLookupWorker | None = None
        self.setModal(True)
        self.resize(560, 640)

        self.hint = QLabel()
        self.hint.setWordWrap(True)
        self.search = QLineEdit()
        self.quick_row = QHBoxLayout()
        self._quick_buttons: list[tuple[QPushButton, str]] = []
        for _key, query in QUICK_FILTERS:
            button = QPushButton()
            button.setObjectName("ghostButton")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda _checked=False, text=query: self._apply_quick(text))
            self.quick_row.addWidget(button)
            self._quick_buttons.append((button, _key))
        self.quick_row.addStretch(1)
        self.results_label = QLabel()
        self.results = QListWidget()
        self.add_btn = QPushButton()
        self.current_label = QLabel()
        self.list_combo = QComboBox()
        self.alert_edit = QLineEdit()
        self.compare_a = QComboBox()
        self.compare_b = QComboBox()
        self.compare_btn = QPushButton()
        self.csv_btn = QPushButton()
        self.csv_btn.setObjectName("ghostButton")
        self.current = QListWidget()
        self.current.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self.current.model().rowsMoved.connect(self._persist_order)
        self.remove_btn = QPushButton()
        self.remove_btn.setObjectName("ghostButton")
        self.close_btn = QPushButton()

        layout = QVBoxLayout(self)
        layout.addWidget(self.hint)
        layout.addWidget(self.search)
        layout.addLayout(self.quick_row)
        layout.addWidget(self.results_label)
        layout.addWidget(self.results, 1)
        layout.addWidget(self.add_btn)
        layout.addWidget(self.current_label)
        layout.addWidget(self.list_combo)
        layout.addWidget(self.alert_edit)
        compare_row = QHBoxLayout()
        compare_row.addWidget(self.compare_a)
        compare_row.addWidget(self.compare_b)
        compare_row.addWidget(self.compare_btn)
        compare_row.addWidget(self.csv_btn)
        layout.addLayout(compare_row)
        layout.addWidget(self.current, 1)
        layout.addWidget(self.remove_btn)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(self.close_btn)
        layout.addLayout(buttons)

        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(350)
        self._debounce.timeout.connect(self._start_yahoo_search)

        self.search.textChanged.connect(self._on_search_changed)
        self.results.itemDoubleClicked.connect(lambda _item: self._add_selected())
        self.add_btn.clicked.connect(self._add_selected)
        self.remove_btn.clicked.connect(self._remove_selected)
        self.close_btn.clicked.connect(self.accept)
        self.list_combo.currentIndexChanged.connect(self._on_list_changed)
        self.compare_btn.clicked.connect(self._compare)
        self.csv_btn.clicked.connect(self._export_csv)
        self.current.itemSelectionChanged.connect(self._load_alert)
        self.alert_edit.editingFinished.connect(self._save_alert)

        self.retranslate()
        self._refresh_current()
        self._refresh_results()

    def retranslate(self) -> None:
        self.setWindowTitle(self._i18n.t("ticker.watchlist"))
        self.hint.setText(self._i18n.t("tickers.search_hint"))
        self.search.setPlaceholderText(self._i18n.t("tickers.search_placeholder"))
        self._set_results_caption(searching=False)
        self.add_btn.setText(self._i18n.t("tickers.add"))
        self.current_label.setText(self._i18n.t("tickers.current"))
        self.alert_edit.setPlaceholderText(self._i18n.t("tickers.alert_pct"))
        self.compare_btn.setText(self._i18n.t("tickers.compare"))
        self.csv_btn.setText(self._i18n.t("tickers.export_csv"))
        self.remove_btn.setText(self._i18n.t("tickers.remove"))
        self.close_btn.setText(self._i18n.t("app.close"))
        labels = {
            "oil": self._i18n.t("tickers.quick_oil"),
            "turkey": self._i18n.t("tickers.quick_turkey"),
            "fx": self._i18n.t("tickers.quick_fx"),
            "gold": self._i18n.t("tickers.quick_gold"),
            "bist": self._i18n.t("tickers.quick_bist"),
            "crypto": self._i18n.t("tickers.quick_crypto"),
        }
        for button, key in self._quick_buttons:
            button.setText(labels.get(key, key))

    def _set_results_caption(self, *, searching: bool) -> None:
        base = self._i18n.t("tickers.results")
        if searching:
            self.results_label.setText(f"{base}  ·  {self._i18n.t('tickers.searching')}")
        else:
            self.results_label.setText(base)

    def _apply_quick(self, query: str) -> None:
        self.search.setText(query)

    def _watch_symbols(self) -> set[str]:
        return {item.symbol.casefold() for item in self._db.list_tickers()}

    def _refresh_current(self) -> None:
        names = self._db.list_watchlist_names()
        current = self._db.get_setting("active_watchlist") or "main"
        self.list_combo.blockSignals(True)
        self.list_combo.clear()
        for name in names:
            self.list_combo.addItem(name, name)
        idx = self.list_combo.findData(current)
        if idx >= 0:
            self.list_combo.setCurrentIndex(idx)
        self.list_combo.blockSignals(False)
        self.current.clear()
        self.compare_a.clear()
        self.compare_b.clear()
        for item in self._db.list_tickers(current):
            row = QListWidgetItem(f"{item.label}  ·  {item.symbol}")
            row.setData(ROLE_PAIR, (item.symbol, item.label, item.alert_pct))
            self.current.addItem(row)
            self.compare_a.addItem(item.symbol, item.symbol)
            self.compare_b.addItem(item.symbol, item.symbol)

    def _on_list_changed(self) -> None:
        name = self.list_combo.currentData() or "main"
        self._db.set_setting("active_watchlist", str(name))
        self._refresh_current()
        self.watchlist_changed.emit()

    def _load_alert(self) -> None:
        item = self.current.currentItem()
        if not item:
            return
        data = item.data(ROLE_PAIR) or ()
        pct = data[2] if len(data) > 2 else None
        self.alert_edit.setText("" if pct in (None, "") else str(pct))

    def _save_alert(self) -> None:
        item = self.current.currentItem()
        if not item:
            return
        data = item.data(ROLE_PAIR) or ()
        if not data:
            return
        try:
            pct = float(self.alert_edit.text().strip()) if self.alert_edit.text().strip() else None
        except ValueError:
            return
        self._db.set_ticker_meta(str(data[0]), alert_pct=pct)

    def _compare(self) -> None:
        a = self.compare_a.currentData()
        b = self.compare_b.currentData()
        if not a or not b:
            return
        from core.market_engine import fetch_quotes

        quotes = fetch_quotes([(str(a), str(a)), (str(b), str(b))])
        lines = [f"{q.label}: {q.price} ({q.change_pct:+.2f}%)" for q in quotes]
        self.hint.setText("  |  ".join(lines) or self._i18n.t("tickers.search_hint"))

    def _export_csv(self) -> None:
        from pathlib import Path

        from core.app_extras import quotes_to_csv
        from core.market_engine import fetch_quotes

        path, _filter = QFileDialog.getSaveFileName(self, self._i18n.t("tickers.export_csv"), "quotes.csv", "CSV (*.csv)")
        if not path:
            return
        pairs = [(item.symbol, item.label) for item in self._db.list_tickers(self._db.get_setting("active_watchlist"))]
        quotes_to_csv(fetch_quotes(pairs), Path(path))

    def _on_search_changed(self, _text: str = "") -> None:
        query = self.search.text().strip()
        if _fold(query) != _fold(self._yahoo_query):
            self._yahoo_hits = []
            self._yahoo_query = ""
        self._refresh_results()
        if len(_fold(query)) < 2:
            self._debounce.stop()
            self._set_results_caption(searching=False)
            return
        self._set_results_caption(searching=True)
        self._debounce.start()

    def _start_yahoo_search(self) -> None:
        query = self.search.text().strip()
        if len(_fold(query)) < 2:
            self._set_results_caption(searching=False)
            return
        worker = YahooLookupWorker(query, self)
        worker.finished_ok.connect(self._on_yahoo)
        worker.finished.connect(worker.deleteLater)
        worker.start()
        self._yahoo_thread = worker

    def _on_yahoo(self, query: str, items: list) -> None:
        if _fold(query) != _fold(self.search.text()):
            return
        self._yahoo_query = query
        self._yahoo_hits = [item for item in items if isinstance(item, CatalogTicker)]
        self._set_results_caption(searching=False)
        self._refresh_results()

    def _refresh_results(self) -> None:
        watched = self._watch_symbols()
        query = self.search.text()
        yahoo = self._yahoo_hits if _fold(self._yahoo_query) == _fold(query) else []
        self.results.clear()
        hits = (
            merge_ticker_search(query, yahoo)
            if yahoo
            else search_catalog(query)
        )
        for item in hits:
            already = item.symbol.casefold() in watched
            suffix = self._i18n.t("tickers.on_tape") if already else ""
            country_key = country_i18n_key(item.country)
            country = self._i18n.t(country_key, item.country) if country_key else item.country
            text = f"{item.label}  ·  {country}  ·  {self._i18n.t(f'tickers.cat.{item.category}', item.category)}"
            if suffix:
                text = f"{text}  ({suffix})"
            row = QListWidgetItem(text)
            row.setData(ROLE_PAIR, item)
            if already:
                row.setFlags(row.flags() & ~Qt.ItemFlag.ItemIsEnabled)
            self.results.addItem(row)

    def _add_selected(self) -> None:
        row = self.results.currentItem()
        if row is None:
            return
        item = row.data(ROLE_PAIR)
        if not isinstance(item, CatalogTicker):
            return
        if not self._db.add_ticker(item.symbol, item.label):
            return
        self._db.set_ticker_meta(item.symbol, watchlist=str(self.list_combo.currentData() or "main"))
        self.watchlist_changed.emit()
        self._refresh_current()
        self._refresh_results()

    def _remove_selected(self) -> None:
        row = self.current.currentItem()
        if row is None:
            return
        pair = row.data(ROLE_PAIR)
        if not pair:
            return
        self._db.remove_ticker_symbol(str(pair[0]))
        self.watchlist_changed.emit()
        self._refresh_current()
        self._refresh_results()

    def _persist_order(self, *_args) -> None:
        current = str(self.list_combo.currentData() or "main")
        rows: list[tuple[str, str]] = []
        for index in range(self.current.count()):
            item = self.current.item(index)
            pair = item.data(ROLE_PAIR) if item else None
            if pair:
                rows.append((str(pair[0]), str(pair[1])))
        others = [
            (item.symbol, item.label)
            for item in self._db.list_tickers()
            if (item.watchlist or "main") != current
        ]
        merged = others + rows
        if merged:
            self._db.replace_tickers(merged)
            for symbol, _label in rows:
                self._db.set_ticker_meta(symbol, watchlist=current)
            self.watchlist_changed.emit()
