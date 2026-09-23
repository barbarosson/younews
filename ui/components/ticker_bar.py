"""Scrolling, color-coded live market tape."""

from __future__ import annotations

from types import SimpleNamespace

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QFontMetrics, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QFrame, QHBoxLayout, QPushButton, QSizePolicy, QWidget

from config import DEFAULT_THEME, MARKET_TICKERS, normalize_theme
from core.ticker_catalog import aliases_for

ACCENTS = {
    "^GSPC": QColor("#58a6ff"),
    "^DJI": QColor("#79c0ff"),
    "^IXIC": QColor("#d2a8ff"),
    "^RUT": QColor("#a371f7"),
    "^FTSE": QColor("#58a6ff"),
    "^GDAXI": QColor("#d2a8ff"),
    "^FCHI": QColor("#79c0ff"),
    "^STOXX50E": QColor("#58a6ff"),
    "^N225": QColor("#ff7b72"),
    "^HSI": QColor("#ff7b72"),
    "000001.SS": QColor("#f85149"),
    "^BSESN": QColor("#e3b341"),
    "^NSEI": QColor("#e3b341"),
    "^AXJO": QColor("#3fb950"),
    "^KS11": QColor("#ff7b72"),
    "^TWII": QColor("#79c0ff"),
    "XU100.IS": QColor("#e3b341"),
    "EURUSD=X": QColor("#79c0ff"),
    "USDJPY=X": QColor("#58a6ff"),
    "GBPUSD=X": QColor("#d2a8ff"),
    "DX-Y.NYB": QColor("#3fb950"),
    "GC=F": QColor("#e3b341"),
    "SI=F": QColor("#c9d1d9"),
    "CL=F": QColor("#8b949e"),
    "BZ=F": QColor("#6e7681"),
    "BTC-USD": QColor("#f7931a"),
    "ETH-USD": QColor("#627eea"),
    "SOL-USD": QColor("#9945ff"),
}
_FALLBACK_ACCENTS = [
    QColor("#58a6ff"),
    QColor("#d2a8ff"),
    QColor("#79c0ff"),
    QColor("#e3b341"),
    QColor("#f7931a"),
    QColor("#ff7b72"),
    QColor("#3fb950"),
    QColor("#a371f7"),
    QColor("#39c5cf"),
]
PALETTES = {
    "dark": {
        "tape_bg": QColor("#05080d"),
        "up_bg": QColor("#0f3d28"),
        "up_fg": QColor("#7CFFB2"),
        "down_bg": QColor("#5a1018"),
        "down_fg": QColor("#FF9AA3"),
        "flat_bg": QColor("#243044"),
        "flat_fg": QColor("#E6EDF3"),
        "price": QColor("#FFFFFF"),
        "label": QColor("#FFFFFF"),
        "status": QColor("#ffb347"),
        "top_line": QColor("#3dff8f"),
        "bottom_line": QColor("#e3b341"),
        "badge_bg": QColor("#121b2e"),
        "badge_border": QColor("#1f6feb"),
        "badge_text": QColor("#ffd166"),
        "fade": QColor(5, 8, 13),
        "glow": (
            QColor(31, 111, 235, 50),
            QColor(227, 179, 65, 32),
            QColor(63, 185, 80, 40),
        ),
    },
    "light": {
        "tape_bg": QColor("#eef2f7"),
        "up_bg": QColor("#c8f0d6"),
        "up_fg": QColor("#055d2b"),
        "down_bg": QColor("#ffd5d8"),
        "down_fg": QColor("#9b1c1c"),
        "flat_bg": QColor("#dbe4ee"),
        "flat_fg": QColor("#1f2328"),
        "price": QColor("#0d1117"),
        "label": QColor("#0d1117"),
        "status": QColor("#9a6700"),
        "top_line": QColor("#1a7f37"),
        "bottom_line": QColor("#9a6700"),
        "badge_bg": QColor("#ffffff"),
        "badge_border": QColor("#0969da"),
        "badge_text": QColor("#0969da"),
        "fade": QColor(238, 242, 247),
        "glow": (
            QColor(9, 105, 218, 28),
            QColor(154, 103, 0, 18),
            QColor(26, 127, 55, 22),
        ),
    },
}
NEWS_TERMS = {
    "^GSPC": ["S&P", "S&P 500", "SPX", "Wall Street", "US stock"],
    "^DJI": ["Dow", "Dow Jones", "DJIA"],
    "^IXIC": ["Nasdaq"],
    "^RUT": ["Russell"],
    "^FTSE": ["FTSE", "London stock", "UK stock"],
    "^GDAXI": ["DAX", "Frankfurt", "German stock"],
    "^FCHI": ["CAC 40", "Paris stock"],
    "^STOXX50E": ["Euro Stoxx", "European stock"],
    "^N225": ["Nikkei", "Tokyo", "Japan stock"],
    "^HSI": ["Hang Seng", "Hong Kong"],
    "000001.SS": ["Shanghai", "China stock"],
    "^BSESN": ["Sensex", "Mumbai", "India stock"],
    "^NSEI": ["Nifty", "India stock"],
    "^AXJO": ["ASX", "Australia stock"],
    "^KS11": ["KOSPI", "Korea stock"],
    "^TWII": ["Taiwan", "TAIEX"],
    "XU100.IS": ["BIST", "Borsa Istanbul", "Türkiye"],
    "EURUSD=X": ["EUR/USD", "EURUSD", "euro dollar"],
    "USDJPY=X": ["yen", "USD/JPY", "USDJPY"],
    "GBPUSD=X": ["sterling", "pound", "GBP"],
    "DX-Y.NYB": ["dollar index", "DXY"],
    "GC=F": ["gold", "XAU"],
    "SI=F": ["silver", "XAG"],
    "CL=F": ["oil", "crude", "WTI"],
    "BZ=F": ["Brent", "oil"],
    "BTC-USD": ["Bitcoin", "BTC", "crypto"],
    "ETH-USD": ["Ethereum", "ETH"],
    "SOL-USD": ["Solana", "SOL"],
}


def news_terms_for(symbol: str, label: str) -> list[str]:
    terms = list(NEWS_TERMS.get(symbol, []))
    terms.extend(aliases_for(symbol))
    terms.append(label)
    cleaned = symbol.replace("^", " ").replace("=X", " ").replace("-USD", " ").replace("=F", " ")
    for part in cleaned.replace(".", " ").split():
        if len(part) >= 2:
            terms.append(part)
    seen: set[str] = set()
    unique: list[str] = []
    for term in terms:
        key = term.strip().lower()
        if len(key) < 3 and key not in {"dax", "btc", "eth", "oil", "dow"}:
            continue
        if key in seen:
            continue
        seen.add(key)
        unique.append(term.strip())
    return unique


CHIP_H = 58
GAP = 18
LABEL_PX = 16
PRICE_PX = 20
CHANGE_PX = 16


class TickerBar(QFrame):
    quote_hovered = Signal(str, str)
    quote_clicked = Signal(str, str)
    hover_cleared = Signal()
    watchlist_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("tickerBar")
        self.setFixedHeight(88)
        self.setFont(QFont("Segoe UI", 12))
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._tape = _TapeWidget(self)
        self._tape.quote_hovered.connect(self.quote_hovered)
        self._tape.quote_clicked.connect(self.quote_clicked)
        self._tape.hover_cleared.connect(self.hover_cleared)
        self.watchlist_btn = QPushButton()
        self.watchlist_btn.setObjectName("ghostButton")
        self.watchlist_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.watchlist_btn.setFixedWidth(128)
        self.watchlist_btn.clicked.connect(self.watchlist_requested.emit)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 10, 0)
        layout.setSpacing(8)
        layout.addWidget(self._tape, 1)
        layout.addWidget(self.watchlist_btn, 0, Qt.AlignmentFlag.AlignVCenter)

    def set_theme(self, theme: str | None) -> None:
        self._tape.set_theme(theme)

    def set_quotes(self, quotes: list) -> None:
        self._tape.set_quotes(quotes)

    def set_status(self, text: str) -> None:
        self._tape.set_status(text)

    def retranslate(self, live_label: str, waiting_label: str, watchlist_label: str = "") -> None:
        self._tape.set_labels(live_label, waiting_label)
        self.watchlist_btn.setText(watchlist_label or "+")

    def set_symbols(self, symbols: list[tuple[str, str]]) -> None:
        self._tape.set_symbols(symbols)

    def set_pinned_symbol(self, symbol: str = "") -> None:
        self._tape.set_pinned_symbol(symbol)

    def set_speed(self, percent: int) -> None:
        self._tape.set_speed(percent)

    def set_compact(self, compact: bool) -> None:
        self.setFixedHeight(56 if compact else 88)


class _TapeWidget(QWidget):
    quote_hovered = Signal(str, str)
    quote_clicked = Signal(str, str)
    hover_cleared = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._quotes: list = []
        self._symbols: list[tuple[str, str]] = list(MARKET_TICKERS)
        self._theme = DEFAULT_THEME
        self._offset = 0.0
        self._paused = False
        self._pulse = 0
        self._live = "LIVE MARKETS"
        self._waiting = "Loading S&P 500 · NASDAQ · EUR/USD · Gold · BTC · Nikkei 225"
        self._status = ""
        self._live_w = 150.0
        self._hover_symbol = ""
        self._pinned_symbol = ""
        self._flash_symbol = ""
        self._speed = 1.6
        self._scroll = QTimer(self)
        self._scroll.setInterval(16)
        self._scroll.timeout.connect(self._tick)
        self._scroll.start()
        self._blink = QTimer(self)
        self._blink.setInterval(80)
        self._blink.timeout.connect(self._pulse_tick)
        self._blink.start()
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_theme(self, theme: str | None) -> None:
        self._theme = normalize_theme(theme)
        self.update()

    def _palette(self) -> dict:
        return PALETTES.get(self._theme, PALETTES[DEFAULT_THEME])

    def set_labels(self, live: str, waiting: str) -> None:
        self._live = live
        self._waiting = waiting
        self.update()

    def set_symbols(self, symbols: list[tuple[str, str]]) -> None:
        self._symbols = list(symbols) if symbols else list(MARKET_TICKERS)
        self.update()

    def set_quotes(self, quotes: list) -> None:
        self._quotes = list(quotes)
        self._status = ""
        self.update()

    def set_status(self, text: str) -> None:
        self._status = text
        self.update()

    def set_pinned_symbol(self, symbol: str = "") -> None:
        self._pinned_symbol = symbol or ""
        self.update()

    def set_speed(self, percent: int) -> None:
        self._speed = max(0.4, min(4.0, (percent or 100) / 100 * 1.6))

    def _clear_flash(self) -> None:
        self._flash_symbol = ""
        self.update()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            chip = self._chip_at(event.position().x())
            if chip:
                self._flash_symbol = str(chip["symbol"])
                self.update()
                QTimer.singleShot(160, self._clear_flash)
                self.quote_clicked.emit(str(chip["symbol"]), str(chip["label"]))
                event.accept()
                return
        super().mousePressEvent(event)

    def enterEvent(self, event) -> None:  # noqa: N802
        self._paused = True
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self._paused = False
        if self._hover_symbol:
            self._hover_symbol = ""
            self.hover_cleared.emit()
            self.update()
        super().leaveEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        chip = self._chip_at(event.position().x())
        if not chip:
            if self._hover_symbol:
                self._hover_symbol = ""
                self.hover_cleared.emit()
                self.update()
            super().mouseMoveEvent(event)
            return
        symbol = str(chip["symbol"])
        if symbol != self._hover_symbol:
            self._hover_symbol = symbol
            self.quote_hovered.emit(chip["symbol"], chip["label"])
            self.update()
        super().mouseMoveEvent(event)

    def _tick(self) -> None:
        if self._paused:
            return
        rtl = self.layoutDirection() == Qt.LayoutDirection.RightToLeft
        step = self._speed
        self._offset += -step if rtl else step
        loop = max(self._strip_width(), 1.0)
        if abs(self._offset) >= loop:
            self._offset = 0.0
        self.update()

    def _pulse_tick(self) -> None:
        self._pulse = (self._pulse + 8) % 360
        self.update()

    def _strip_width(self) -> float:
        return sum(chip["width"] + GAP for chip in self._chips()) + 24

    def _format_price(self, quote) -> str:
        symbol = str(getattr(quote, "symbol", ""))
        if symbol.endswith("=X"):
            return f"{quote.price:.4f}"
        if symbol.endswith("-USD") and quote.price >= 200:
            return f"{quote.price:,.0f}"
        return f"{quote.price:,.2f}"

    def _accent_for(self, symbol: str) -> QColor:
        if symbol in ACCENTS:
            return ACCENTS[symbol]
        return _FALLBACK_ACCENTS[sum(ord(ch) for ch in symbol) % len(_FALLBACK_ACCENTS)]

    def _chips(self) -> list[dict]:
        source = self._quotes or [
            SimpleNamespace(symbol=sym, label=label, price=0.0, change_pct=0.0)
            for sym, label in (self._symbols or MARKET_TICKERS)
        ]
        font = QFont("Segoe UI")
        font.setPixelSize(LABEL_PX)
        font.setBold(True)
        fm = QFontMetrics(font)
        items: list[dict] = []
        for quote in source:
            up = quote.change_pct > 0.005
            down = quote.change_pct < -0.005
            arrow = "▲" if up else "▼" if down else "●"
            sign = "+" if quote.change_pct >= 0 else ""
            if getattr(quote, "missing", False):
                change = "—"
                price = "—"
            elif getattr(quote, "stale", False):
                change = f"{arrow} {sign}{quote.change_pct:.2f}% ·"
                price = self._format_price(quote)
            elif getattr(quote, "after_hours", False):
                change = f"{arrow} {sign}{quote.change_pct:.2f}% AH"
                price = self._format_price(quote)
            elif self._quotes:
                change = f"{arrow} {sign}{quote.change_pct:.2f}%"
                price = self._format_price(quote)
            else:
                change = "—"
                price = "…"
            sample = f"{quote.label}  {price}  {change}"
            width = max(fm.horizontalAdvance(sample) + 72, 240)
            spark = tuple(getattr(quote, "spark", ()) or ())
            items.append(
                {
                    "symbol": quote.symbol,
                    "label": quote.label,
                    "price": price,
                    "change": change,
                    "up": up,
                    "down": down,
                    "accent": self._accent_for(quote.symbol),
                    "width": width,
                    "spark": spark,
                    "missing": bool(getattr(quote, "missing", False)),
                }
            )
        return items

    def _chip_at(self, pos_x: float) -> dict | None:
        if pos_x < self._live_w + 8:
            return None
        chips = self._chips()
        if not chips:
            return None
        strip_w = max(self._strip_width(), 1.0)
        start = self._live_w + 16 - self._offset
        x = start
        copies = max(4, int(self.width() / strip_w) + 4)
        for _ in range(copies):
            cx = x
            for chip in chips:
                if cx <= pos_x <= cx + chip["width"]:
                    return chip
                cx += chip["width"] + GAP
            x += strip_w
        return None

    def paintEvent(self, event) -> None:  # noqa: N802
        palette = self._palette()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), palette["tape_bg"])

        glow = QLinearGradient(0, 0, self.width(), 0)
        glow_colors = palette["glow"]
        glow.setColorAt(0.0, glow_colors[0])
        glow.setColorAt(0.45, glow_colors[1])
        glow.setColorAt(1.0, glow_colors[2])
        painter.fillRect(self.rect(), glow)

        painter.setPen(QPen(palette["top_line"], 2))
        painter.drawLine(0, 0, self.width(), 0)
        painter.setPen(QPen(palette["bottom_line"], 2))
        painter.drawLine(0, self.height() - 1, self.width(), self.height() - 1)

        live_w = self._draw_live_badge(painter)
        self._live_w = float(live_w)
        clip = QRectF(live_w + 8, 8, self.width() - live_w - 16, self.height() - 16)
        painter.setClipRect(clip)

        chips = self._chips()
        strip_w = max(self._strip_width(), 1.0)
        y = (self.height() - CHIP_H) / 2
        start = live_w + 16 - self._offset
        x = start
        copies = max(4, int(self.width() / strip_w) + 4)
        for _ in range(copies):
            cx = x
            for chip in chips:
                self._draw_chip(painter, cx, y, chip)
                cx += chip["width"] + GAP
            x += strip_w

        painter.setClipping(False)
        fade = QLinearGradient(live_w, 0, live_w + 28, 0)
        fade_base = palette["fade"]
        fade.setColorAt(0, QColor(fade_base.red(), fade_base.green(), fade_base.blue(), 220))
        fade.setColorAt(1, QColor(fade_base.red(), fade_base.green(), fade_base.blue(), 0))
        painter.fillRect(QRectF(live_w, 0, 28, self.height()), fade)

        if self._status:
            painter.setPen(palette["status"])
            painter.drawText(
                self.rect().adjusted(8, 0, -8, 0),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                self._status,
            )

    def _draw_live_badge(self, painter: QPainter) -> int:
        pulse = 120 + int(90 * abs((self._pulse % 180) - 90) / 90)
        font = QFont("Segoe UI")
        font.setBold(True)
        font.setPixelSize(12)
        text_w = QFontMetrics(font).horizontalAdvance(self._live)
        badge = QRectF(10, 14, max(132.0, text_w + 58), 36)
        path = QPainterPath()
        palette = self._palette()
        path.addRoundedRect(badge, 8, 8)
        painter.fillPath(path, QBrush(palette["badge_bg"]))
        painter.setPen(QPen(palette["badge_border"], 1))
        painter.drawPath(path)
        painter.setBrush(QColor(255, 59, 48, pulse))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QRectF(22, 26, 12, 12))
        painter.setPen(palette["badge_text"])
        painter.setFont(font)
        painter.drawText(
            QRectF(40, 14, badge.width() - 36, 36),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            self._live,
        )
        return int(badge.right()) + 6

    def _draw_chip(self, painter: QPainter, x: float, y: float, chip: dict) -> None:
        palette = self._palette()
        hovered = chip["symbol"] == self._hover_symbol
        pinned = chip["symbol"] == self._pinned_symbol
        flashed = chip["symbol"] == self._flash_symbol
        rect = QRectF(x, y, chip["width"], CHIP_H)
        if flashed:
            rect.adjust(2, 2, -2, -2)
        bg = palette["up_bg"] if chip["up"] else palette["down_bg"] if chip["down"] else palette["flat_bg"]
        fg = palette["up_fg"] if chip["up"] else palette["down_fg"] if chip["down"] else palette["flat_fg"]
        path = QPainterPath()
        path.addRoundedRect(rect, 12, 12)
        painter.fillPath(path, QBrush(bg))
        painter.setPen(QPen(QColor("#ffffff") if hovered or pinned or flashed else chip["accent"], 4 if flashed else 3 if hovered or pinned else 2))
        painter.drawPath(path)
        painter.fillRect(QRectF(rect.left(), rect.top(), 6, rect.height()), chip["accent"])

        label_font = QFont("Segoe UI")
        label_font.setPixelSize(LABEL_PX)
        label_font.setBold(True)
        painter.setFont(label_font)
        painter.setPen(palette.get("label", palette["price"]))
        painter.drawText(
            rect.adjusted(16, 4, -12, -CHIP_H / 2),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            chip["label"],
        )
        price_font = QFont("Segoe UI")
        price_font.setPixelSize(PRICE_PX)
        price_font.setBold(True)
        painter.setFont(price_font)
        painter.setPen(palette["price"])
        painter.drawText(
            rect.adjusted(16, CHIP_H / 2 - 4, -12, -6),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            chip["price"],
        )
        change_font = QFont("Segoe UI")
        change_font.setPixelSize(CHANGE_PX)
        change_font.setBold(True)
        painter.setFont(change_font)
        painter.setPen(fg)
        painter.drawText(
            rect.adjusted(16, CHIP_H / 2 - 4, -14, -6),
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            chip["change"],
        )
        spark = chip.get("spark") or ()
        if len(spark) >= 2:
            lo = min(spark)
            hi = max(spark)
            span = hi - lo or 1.0
            area = QRectF(rect.right() - 58, rect.top() + 8, 44, 18)
            points = []
            for index, value in enumerate(spark):
                px = area.left() + (area.width() * index / (len(spark) - 1))
                py = area.bottom() - ((value - lo) / span) * area.height()
                points.append(QPointF(px, py))
            painter.setPen(QPen(chip["accent"], 1.4))
            for start, end in zip(points, points[1:]):
                painter.drawLine(start, end)
