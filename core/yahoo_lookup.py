"""Live Yahoo Finance symbol search via yfinance (Lookup + Search)."""

from __future__ import annotations

from time import time

from PySide6.QtCore import QThread, Signal

from core.ticker_catalog import CatalogTicker, _fold, search_catalog

_CACHE: dict[str, tuple[float, list[CatalogTicker]]] = {}
_CACHE_TTL = 600.0

_TYPE_TO_CATEGORY = {
    "equity": "stocks",
    "etf": "etf",
    "index": "indices",
    "currency": "fx",
    "cryptocurrency": "crypto",
    "future": "commodities",
    "commodity": "commodities",
    "mutualfund": "other",
    "option": "other",
}

_QUERY_ALIASES = {
    "petrol": "crude oil",
    "ham petrol": "crude oil",
    "altin": "gold",
    "gumus": "silver",
    "dolar": "USD TRY",
    "euro": "EUR USD",
    "sterlin": "GBP USD",
    "turkiye": "XU100",
    "borsa": "XU100",
    "borsa istanbul": "XU100",
    "kripto": "bitcoin",
    "kur": "USD TRY",
}


def expand_yahoo_query(query: str) -> str:
    folded = _fold(query)
    return _QUERY_ALIASES.get(folded, (query or "").strip())


def _category_for(quote_type: str) -> str:
    key = (quote_type or "").strip().casefold()
    return _TYPE_TO_CATEGORY.get(key, "stocks")


def _clean(value: object) -> str:
    text = "" if value is None else str(value).strip()
    if not text or text.casefold() in {"nan", "none"}:
        return ""
    return text


def _from_row(payload: dict) -> CatalogTicker | None:
    symbol = _clean(payload.get("symbol"))
    if not symbol:
        return None
    label = (
        _clean(payload.get("shortName"))
        or _clean(payload.get("shortname"))
        or _clean(payload.get("longname"))
        or _clean(payload.get("longName"))
        or symbol
    )
    exchange = (
        _clean(payload.get("exchDisp"))
        or _clean(payload.get("exchange"))
        or ""
    )
    quote_type = _clean(payload.get("quoteType") or payload.get("typeDisp"))
    aliases = tuple(
        part
        for part in (label, exchange, quote_type, _clean(payload.get("industryName")))
        if part
    )
    return CatalogTicker(
        symbol=symbol,
        label=label,
        category=_category_for(quote_type),
        country=exchange or "Yahoo",
        aliases=aliases,
    )


def lookup_yahoo(query: str, *, limit: int = 40) -> list[CatalogTicker]:
    raw = (query or "").strip()
    if len(_fold(raw)) < 2:
        return []
    yahoo_q = expand_yahoo_query(raw)
    if not yahoo_q:
        return []
    cached = _CACHE.get(yahoo_q.casefold())
    if cached and time() - cached[0] < _CACHE_TTL:
        return cached[1][:limit]

    import yfinance as yf

    found: list[CatalogTicker] = []
    seen: set[str] = set()

    def _add(item: CatalogTicker | None) -> None:
        if item is None:
            return
        key = item.symbol.casefold()
        if key in seen:
            return
        seen.add(key)
        found.append(item)

    try:
        frame = yf.Lookup(yahoo_q, timeout=8, raise_errors=False).get_all(count=limit)
    except Exception:
        frame = None
    if frame is not None and hasattr(frame, "empty") and not frame.empty:
        try:
            records = frame.reset_index().to_dict("records")
        except Exception:
            records = []
        for row in records:
            if isinstance(row, dict):
                _add(_from_row(row))

    if len(found) < 8:
        try:
            search = yf.Search(yahoo_q, max_results=limit, news_count=0)
            quotes = getattr(search, "quotes", None) or []
        except Exception:
            quotes = []
        if not quotes:
            try:
                search = yf.Search(expand_yahoo_query(raw) or raw, max_results=limit, news_count=0, timeout=8)
                quotes = getattr(search, "quotes", None) or []
            except Exception:
                quotes = []
        for row in quotes:
            if isinstance(row, dict):
                _add(_from_row(row))

    result = found[:limit]
    _CACHE[yahoo_q.casefold()] = (time(), result)
    return result


def merge_ticker_search(
    query: str,
    yahoo_hits: list[CatalogTicker] | None = None,
    *,
    catalog_limit: int = 48,
    total_limit: int = 80,
) -> list[CatalogTicker]:
    local = search_catalog(query, limit=catalog_limit)
    seen = {item.symbol.casefold() for item in local}
    extra: list[CatalogTicker] = []
    for item in yahoo_hits or []:
        key = item.symbol.casefold()
        if key in seen:
            continue
        seen.add(key)
        extra.append(item)
    room = max(0, total_limit - len(local))
    return [*local, *extra[:room]]


class YahooLookupWorker(QThread):
    finished_ok = Signal(str, list)

    def __init__(self, query: str, parent=None) -> None:
        super().__init__(parent)
        self.query = query

    def run(self) -> None:
        try:
            items = lookup_yahoo(self.query)
        except Exception:
            items = []
        self.finished_ok.emit(self.query, items)
