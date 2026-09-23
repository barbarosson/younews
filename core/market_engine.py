"""Global market ticker worker using yfinance, Yahoo chart fallback, and last-good cache."""

from __future__ import annotations

import json
from dataclasses import dataclass
from time import time

import httpx
import yfinance as yf
from PySide6.QtCore import QObject, QThread, QTimer, Signal

from config import BROWSER_USER_AGENT, DATA_DIR, DEFAULT_MARKET_TICKERS, MARKET_REFRESH_SECONDS
from core.app_extras import httpx_proxy_kwargs
from database.db import Database

_CACHE_PATH = DATA_DIR / "quote_cache.json"
_CACHE_MAX_AGE = 24 * 3600
_CHUNK = 8


@dataclass
class TickerQuote:
    symbol: str
    label: str
    price: float
    change_pct: float
    spark: tuple[float, ...] = ()
    delayed: bool = True
    missing: bool = False
    after_hours: bool = False
    stale: bool = False


def _closes_from_history(history) -> list[float]:
    if history is None or getattr(history, "empty", True) or "Close" not in history:
        return []
    return [float(value) for value in history["Close"].dropna().tolist()]


def _quote_from_closes(
    symbol: str,
    label: str,
    closes: list[float],
    *,
    delayed: bool = True,
    after_hours: bool = False,
    stale: bool = False,
) -> TickerQuote | None:
    if not closes:
        return None
    price = closes[-1]
    prev = closes[-2] if len(closes) > 1 else price
    change = 0.0 if prev == 0 else ((price - prev) / prev) * 100.0
    spark = tuple(closes[-12:])
    return TickerQuote(
        symbol=symbol,
        label=label or symbol,
        price=price,
        change_pct=change,
        spark=spark,
        delayed=delayed or stale,
        missing=False,
        after_hours=after_hours,
        stale=stale,
    )


def _load_quote_cache() -> dict[str, dict]:
    try:
        payload = json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    now = time()
    kept: dict[str, dict] = {}
    for symbol, row in payload.items():
        if not isinstance(row, dict):
            continue
        stamp = float(row.get("ts") or 0)
        if stamp and now - stamp > _CACHE_MAX_AGE:
            continue
        kept[str(symbol).upper()] = row
    return kept


def _save_quote_cache(quotes: list[TickerQuote]) -> None:
    previous = _load_quote_cache()
    now = time()
    for quote in quotes:
        if quote.missing or quote.stale:
            continue
        previous[quote.symbol.upper()] = {
            "symbol": quote.symbol,
            "label": quote.label,
            "price": quote.price,
            "change_pct": quote.change_pct,
            "spark": list(quote.spark),
            "delayed": quote.delayed,
            "after_hours": quote.after_hours,
            "ts": now,
        }
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        _CACHE_PATH.write_text(json.dumps(previous), encoding="utf-8")
    except OSError:
        pass


def quote_from_cache(symbol: str, label: str, cache: dict[str, dict] | None = None) -> TickerQuote | None:
    row = (cache or _load_quote_cache()).get(symbol.upper())
    if not row:
        return None
    spark = row.get("spark") or []
    try:
        numbers = tuple(float(value) for value in spark)
    except (TypeError, ValueError):
        numbers = ()
    try:
        price = float(row.get("price") or 0)
        change = float(row.get("change_pct") or 0)
    except (TypeError, ValueError):
        return None
    if price <= 0:
        return None
    return TickerQuote(
        symbol=symbol,
        label=label or str(row.get("label") or symbol),
        price=price,
        change_pct=change,
        spark=numbers,
        delayed=True,
        missing=False,
        after_hours=bool(row.get("after_hours")),
        stale=True,
    )


def _download_chunk(symbols: list[str], period: str, interval: str):
    if not symbols:
        return None
    try:
        return yf.download(
            symbols,
            period=period,
            interval=interval,
            group_by="ticker",
            threads=False,
            progress=False,
            auto_adjust=True,
            timeout=18,
        )
    except TypeError:
        try:
            return yf.download(
                symbols,
                period=period,
                interval=interval,
                group_by="ticker",
                threads=False,
                progress=False,
                auto_adjust=True,
            )
        except Exception:
            return None
    except Exception:
        return None


def _ingest_frame(frame, symbols: list[str], labels: dict[str, str], delayed: bool) -> dict[str, TickerQuote]:
    quotes: dict[str, TickerQuote] = {}
    if frame is None or getattr(frame, "empty", True):
        return quotes
    if len(symbols) == 1:
        item = _quote_from_closes(symbols[0], labels[symbols[0]], _closes_from_history(frame), delayed=delayed)
        if item:
            quotes[symbols[0]] = item
        return quotes
    for symbol in symbols:
        try:
            history = frame[symbol] if symbol in frame.columns.get_level_values(0) else None
        except Exception:
            history = None
        item = _quote_from_closes(symbol, labels[symbol], _closes_from_history(history), delayed=delayed)
        if item:
            quotes[symbol] = item
    return quotes


def _chart_closes(symbol: str, *, interval: str, range_: str) -> list[float]:
    headers = {"User-Agent": BROWSER_USER_AGENT, "Accept": "application/json"}
    params = {"interval": interval, "range": range_, "events": "div,splits"}
    last: list[float] = []
    for host in ("query1.finance.yahoo.com", "query2.finance.yahoo.com"):
        url = f"https://{host}/v8/finance/chart/{symbol}"
        try:
            with httpx.Client(
                headers=headers,
                timeout=12.0,
                follow_redirects=True,
                **httpx_proxy_kwargs(),
            ) as client:
                response = client.get(url, params=params)
                if response.status_code >= 400:
                    continue
                payload = response.json()
        except Exception:
            continue
        rows = ((payload.get("chart") or {}).get("result")) or []
        if not rows:
            continue
        quote = ((rows[0].get("indicators") or {}).get("quote") or [{}])[0]
        closes = [float(value) for value in (quote.get("close") or []) if value is not None]
        if closes:
            return closes
        last = closes
    return last


def fetch_quotes(tickers: list[tuple[str, str]] | None = None, *, intraday: bool = False) -> list[TickerQuote]:
    pairs = list(tickers) if tickers is not None else list(DEFAULT_MARKET_TICKERS)
    labels = {symbol: label for symbol, label in pairs}
    symbols = [symbol for symbol, _label in pairs]
    quotes: dict[str, TickerQuote] = {}
    period, interval = ("1d", "5m") if intraday else ("5d", "1d")
    delayed = not intraday
    for index in range(0, len(symbols), _CHUNK):
        chunk = symbols[index : index + _CHUNK]
        quotes.update(_ingest_frame(_download_chunk(chunk, period, interval), chunk, labels, delayed))
    cache = _load_quote_cache()
    for symbol, label in pairs:
        if symbol in quotes:
            continue
        try:
            history = yf.Ticker(symbol).history(period=period, interval=interval, auto_adjust=True)
            item = _quote_from_closes(symbol, label, _closes_from_history(history), delayed=delayed)
            if item:
                quotes[symbol] = item
                continue
        except Exception:
            pass
        if intraday:
            try:
                history = yf.Ticker(symbol).history(period="5d", interval="1d", auto_adjust=True)
                item = _quote_from_closes(symbol, label, _closes_from_history(history), delayed=True, after_hours=True)
                if item:
                    quotes[symbol] = item
                    continue
            except Exception:
                pass
        chart_interval, chart_range = ("5m", "1d") if intraday else ("1d", "5d")
        item = _quote_from_closes(
            symbol,
            label,
            _chart_closes(symbol, interval=chart_interval, range_=chart_range),
            delayed=True,
        )
        if item:
            quotes[symbol] = item
            continue
        if intraday:
            item = _quote_from_closes(
                symbol,
                label,
                _chart_closes(symbol, interval="1d", range_="5d"),
                delayed=True,
                after_hours=True,
            )
            if item:
                quotes[symbol] = item
                continue
        cached = quote_from_cache(symbol, label, cache)
        quotes[symbol] = cached or TickerQuote(
            symbol=symbol,
            label=label or symbol,
            price=0.0,
            change_pct=0.0,
            missing=True,
        )
    live = [quotes[symbol] for symbol, _label in pairs]
    _save_quote_cache(live)
    return live


class MarketEngine(QObject):
    quotes_ready = Signal(list)
    failed = Signal(str)

    def __init__(self, db: Database, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._db = db
        self._timer = QTimer(self)
        self._timer.setInterval(MARKET_REFRESH_SECONDS * 1000)
        self._timer.timeout.connect(self.refresh)
        self._busy = False
        self._fails = 0

    def start(self) -> None:
        self.refresh()
        self._timer.start()

    def stop(self) -> None:
        self._timer.stop()

    def refresh(self) -> None:
        if self._busy:
            return
        self._busy = True
        pairs = [(item.symbol, item.label) for item in self._db.list_tickers(self._db.get_setting("active_watchlist") or "main")]
        worker = _QuoteThread(pairs, self._db.get_setting("intraday_quotes", "1") == "1", self)
        worker.finished_ok.connect(self._on_ok)
        worker.finished_err.connect(self._on_err)
        worker.start()
        self._thread = worker

    def _restore_interval(self) -> None:
        self._timer.setInterval(MARKET_REFRESH_SECONDS * 1000)

    def _on_ok(self, quotes: list) -> None:
        self._busy = False
        live = [item for item in quotes if not getattr(item, "missing", False) and not getattr(item, "stale", False)]
        if live:
            self._fails = 0
            self._restore_interval()
        else:
            self._fails += 1
            delay = min(300, MARKET_REFRESH_SECONDS * (2 ** min(self._fails, 3)))
            self._timer.setInterval(delay * 1000)
        self.quotes_ready.emit(quotes)

    def _on_err(self, message: str) -> None:
        self._busy = False
        self._fails += 1
        delay = min(300, MARKET_REFRESH_SECONDS * (2 ** min(self._fails, 3)))
        self._timer.setInterval(delay * 1000)
        pairs = [(item.symbol, item.label) for item in self._db.list_tickers(self._db.get_setting("active_watchlist") or "main")]
        cache = _load_quote_cache()
        cached = []
        for symbol, label in pairs:
            item = quote_from_cache(symbol, label, cache)
            cached.append(
                item
                or TickerQuote(symbol=symbol, label=label or symbol, price=0.0, change_pct=0.0, missing=True)
            )
        if any(not item.missing for item in cached):
            self.quotes_ready.emit(cached)
        self.failed.emit(message)


class _QuoteThread(QThread):
    finished_ok = Signal(list)
    finished_err = Signal(str)

    def __init__(self, pairs: list[tuple[str, str]], intraday: bool, parent=None) -> None:
        super().__init__(parent)
        self._pairs = pairs
        self._intraday = intraday

    def run(self) -> None:
        try:
            self.finished_ok.emit(fetch_quotes(self._pairs, intraday=self._intraday))
        except Exception as exc:
            self.finished_err.emit(str(exc))
