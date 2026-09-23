"""App constants, keyring wrapper, and language settings."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import keyring

APP_NAME = "You News"
APP_ORG = "GlobalNewsTerminal"
APP_VERSION = "1.5.0"
APP_PROMO_URL = "https://younews.media"
APP_CHANGELOG = (
    "1.5.0 — Signed license keys and one-PC activation (required in packaged builds).\n"
    "1.4.0 — Single instance, logs, stale feeds, watchlists, keyboard, notes, "
    "relative time, RSS discover, about, 2-pane, mini tape, CI smoke tests, "
    "share to WhatsApp/Telegram/X and other apps with You News marketing copy."
)
KEYRING_SERVICE = "global_news_terminal"
OPENAI_KEY_ACCOUNT = "OPENAI_API_KEY"
ANTHROPIC_KEY_ACCOUNT = "ANTHROPIC_API_KEY"
GEMINI_KEY_ACCOUNT = "GEMINI_API_KEY"
GROQ_KEY_ACCOUNT = "GROQ_API_KEY"


def _bundle_dir() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent


def _user_data_dir() -> Path:
    override = os.environ.get("YOU_NEWS_HOME") or os.environ.get("YOU_NEWS_DATA")
    if override:
        return Path(override)
    if getattr(sys, "frozen", False):
        appdata = os.environ.get("APPDATA")
        base = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"
        return base / APP_ORG
    return Path(__file__).resolve().parent / "data"


ROOT_DIR = _bundle_dir()
LOCALES_DIR = ROOT_DIR / "locales"
STYLES_DIR = ROOT_DIR / "ui" / "styles"
ASSETS_DIR = ROOT_DIR / "ui" / "assets"
APP_ICON_PNG = ASSETS_DIR / "you_news_icon.png"
APP_ICON_ICO = ASSETS_DIR / "you_news_icon.ico"
APP_WORDMARK_PNG = ASSETS_DIR / "you_news_wordmark.png"
APP_MASCOT_PNG = ASSETS_DIR / "you_news_mascot.png"
APP_MASCOT_MARK_PNG = ASSETS_DIR / "you_news_mascot_mark.png"
DATA_DIR = _user_data_dir()
DB_PATH = DATA_DIR / "terminal.db"

DEFAULT_LANGUAGE = "en"
DEFAULT_THEME = "dark"
THEMES: dict[str, str] = {
    "dark": "dark_theme.qss",
    "light": "light_theme.qss",
    "high_contrast": "high_contrast.qss",
}
THEME_CHOICES: tuple[str, ...] = ("system", "dark", "light", "high_contrast")
SUPPORTED_LANGUAGES: dict[str, str] = {
    "en": "English",
    "fr": "Français",
    "es": "Español",
    "zh": "中文",
    "ja": "日本語",
    "tr": "Türkçe",
    "ar": "العربية",
    "de": "Deutsch",
    "pt": "Português",
}
# Picker until the other locale files catch up (license and legal strings).
UI_LANGUAGES: dict[str, str] = {
    "tr": "Türkçe",
    "en": "English",
}

DEFAULT_AI_PROVIDER = "openai"
DEFAULT_OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_OLLAMA_MODEL = "llama3"
AI_PROVIDERS: tuple[str, ...] = ("openai", "anthropic", "gemini", "groq", "ollama")
CLOUD_AI_PROVIDERS: tuple[str, ...] = ("openai", "anthropic", "gemini", "groq")
PROVIDER_KEY_ACCOUNTS: dict[str, str] = {
    "openai": OPENAI_KEY_ACCOUNT,
    "anthropic": ANTHROPIC_KEY_ACCOUNT,
    "gemini": GEMINI_KEY_ACCOUNT,
    "groq": GROQ_KEY_ACCOUNT,
}
DEFAULT_AI_MODELS: dict[str, str] = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-3-5-haiku-latest",
    "gemini": "gemini-2.5-flash",
    "groq": "llama-3.3-70b-versatile",
    "ollama": DEFAULT_OLLAMA_MODEL,
}

DEFAULT_FEED_REFRESH_MINUTES = 15
FEED_REFRESH_MINUTES = (0, 5, 15, 30, 60)
FEED_REFRESH_INTERVAL_KEYS: dict[int, str] = {
    0: "app.refresh_interval_off",
    5: "app.refresh_interval_5",
    15: "app.refresh_interval_15",
    30: "app.refresh_interval_30",
    60: "app.refresh_interval_60",
}


def parse_feed_refresh_minutes(value: str | None) -> int:
    try:
        minutes = int(str(value).strip())
    except (TypeError, ValueError):
        return DEFAULT_FEED_REFRESH_MINUTES
    if minutes in FEED_REFRESH_MINUTES:
        return minutes
    return DEFAULT_FEED_REFRESH_MINUTES


ARTICLE_LIST_LIMIT_OPTIONS = (100, 200, 400, 1000)
ARTICLE_LIST_LIMIT = 1000


def parse_article_list_limit(value: str | None) -> int:
    try:
        limit = int(str(value).strip())
    except (TypeError, ValueError):
        return ARTICLE_LIST_LIMIT
    if limit in ARTICLE_LIST_LIMIT_OPTIONS:
        return limit
    return ARTICLE_LIST_LIMIT


DEFAULT_ARTICLE_DATE_SORT = "newest"
ARTICLE_DATE_SORT_VALUES = {"newest", "oldest"}


def normalize_article_date_sort(value: str | None) -> str:
    key = str(value or "").strip().lower()
    if key in ARTICLE_DATE_SORT_VALUES:
        return key
    return DEFAULT_ARTICLE_DATE_SORT


DEFAULT_MARKET_TICKERS: list[tuple[str, str]] = [
    ("^GSPC", "S&P 500"),
    ("^IXIC", "NASDAQ"),
    ("EURUSD=X", "EUR/USD"),
    ("GC=F", "Gold"),
    ("BTC-USD", "Bitcoin"),
    ("^N225", "Nikkei 225"),
]
MARKET_TICKERS = DEFAULT_MARKET_TICKERS

# (category_key, yahoo_symbol, display_label) — yfinance / Yahoo Finance codes
TICKER_PRESETS: list[tuple[str, str, str]] = [
    ("indices", "^GSPC", "S&P 500"),
    ("indices", "^DJI", "Dow Jones"),
    ("indices", "^IXIC", "NASDAQ"),
    ("indices", "^RUT", "Russell 2000"),
    ("indices", "^FTSE", "FTSE 100"),
    ("indices", "^GDAXI", "DAX"),
    ("indices", "^FCHI", "CAC 40"),
    ("indices", "^STOXX50E", "Euro Stoxx 50"),
    ("indices", "^N225", "Nikkei 225"),
    ("indices", "^HSI", "Hang Seng"),
    ("indices", "000001.SS", "Shanghai Composite"),
    ("indices", "^BSESN", "BSE Sensex"),
    ("indices", "^NSEI", "Nifty 50"),
    ("indices", "^AXJO", "ASX 200"),
    ("indices", "^KS11", "KOSPI"),
    ("indices", "^TWII", "TAIEX"),
    ("indices", "^GSPTSE", "S&P/TSX"),
    ("indices", "^BVSP", "Bovespa"),
    ("indices", "^MXX", "IPC Mexico"),
    ("indices", "^IBEX", "IBEX 35"),
    ("indices", "^AEX", "AEX"),
    ("indices", "^SSMI", "SMI"),
    ("indices", "XU100.IS", "BIST 100"),
    ("fx", "EURUSD=X", "EUR/USD"),
    ("fx", "USDJPY=X", "USD/JPY"),
    ("fx", "GBPUSD=X", "GBP/USD"),
    ("fx", "USDCHF=X", "USD/CHF"),
    ("fx", "AUDUSD=X", "AUD/USD"),
    ("fx", "USDCNY=X", "USD/CNY"),
    ("fx", "USDTRY=X", "USD/TRY"),
    ("fx", "DX-Y.NYB", "US Dollar Index"),
    ("commodities", "GC=F", "Gold"),
    ("commodities", "SI=F", "Silver"),
    ("commodities", "CL=F", "WTI Crude"),
    ("commodities", "BZ=F", "Brent Crude"),
    ("commodities", "NG=F", "Natural Gas"),
    ("commodities", "HG=F", "Copper"),
    ("crypto", "BTC-USD", "Bitcoin"),
    ("crypto", "ETH-USD", "Ethereum"),
    ("crypto", "SOL-USD", "Solana"),
    ("stocks", "AAPL", "Apple"),
    ("stocks", "MSFT", "Microsoft"),
    ("stocks", "NVDA", "NVIDIA"),
    ("stocks", "BMW.DE", "BMW"),
]

GITHUB_UPDATE_REPO = ""
USER_QSS_PATH = DATA_DIR / "user.qss"
MARKET_REFRESH_SECONDS = 60
TICKER_ALERT_PCT_DEFAULT = 2.0
BRIEFING_HOURS_DEFAULT = 8
BRIEFING_HOURS_OPTIONS = (1, 2, 4, 8, 12, 24)
BRIEFING_ARTICLE_LIMIT = 30
ARTICLE_RETENTION_HOURS = 24
ARTICLE_RETENTION_OPTIONS = (24, 48, 72, 168, 0)
SOCIAL_FOLLOW_LIMIT = 100
FONT_SCALE_OPTIONS = (100, 115, 130)
CHAT_HISTORY_LIMIT = 80
SOCIAL_MODULE_ID = "social_media"
ARTICLE_EMOJIS = ("🔥", "📈", "📉", "⚠️", "💡", "✅", "⭐", "📌", "🌍", "💼")
RSS_USER_AGENT = (
    "Mozilla/5.0 (compatible; YouNews/1.5; +https://younews.media) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)
BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)
IMAGE_CACHE_DIR = DATA_DIR / "images"
IMAGE_MAX_BYTES = 500_000
IMAGE_FETCH_TIMEOUT = 6.0
IMAGE_PREFETCH_LIMIT = 36


def parse_retention_hours(value: str | None) -> int:
    try:
        hours = int(str(value).strip())
    except (TypeError, ValueError):
        return ARTICLE_RETENTION_HOURS
    if hours in ARTICLE_RETENTION_OPTIONS:
        return hours
    return ARTICLE_RETENTION_HOURS


def parse_font_scale(value: str | None) -> int:
    try:
        scale = int(str(value).strip())
    except (TypeError, ValueError):
        return 100
    if scale in FONT_SCALE_OPTIONS:
        return scale
    return 100


def parse_alert_pct(value: str | None) -> float:
    try:
        pct = float(str(value or "").replace(",", ".").strip())
    except (TypeError, ValueError):
        return TICKER_ALERT_PCT_DEFAULT
    return max(0.0, min(pct, 50.0))


def normalize_theme(value: str | None) -> str:
    if value in THEME_CHOICES:
        return value
    if value in THEMES:
        return value
    return DEFAULT_THEME


def resolve_theme(value: str | None) -> str:
    key = normalize_theme(value)
    if key != "system":
        return key if key in THEMES else DEFAULT_THEME
    try:
        from PySide6.QtGui import QGuiApplication
        from PySide6.QtCore import Qt

        hints = QGuiApplication.styleHints()
        scheme = hints.colorScheme()
        if scheme == Qt.ColorScheme.Light:
            return "light"
        return "dark"
    except Exception:
        return DEFAULT_THEME


def theme_stylesheet_path(theme: str | None) -> Path:
    filename = THEMES[resolve_theme(theme)]
    return STYLES_DIR / filename


def load_theme_stylesheet(theme: str | None) -> str:
    path = theme_stylesheet_path(theme)
    if path.exists():
        sheet = path.read_text(encoding="utf-8")
    else:
        fallback = STYLES_DIR / THEMES[DEFAULT_THEME]
        sheet = fallback.read_text(encoding="utf-8") if fallback.exists() else ""
    extra = USER_QSS_PATH
    if extra.is_file():
        sheet += "\n" + extra.read_text(encoding="utf-8")
    return sheet


def get_secret(account: str) -> str | None:
    try:
        value = keyring.get_password(KEYRING_SERVICE, account)
    except Exception:
        return None
    return value or None


def set_secret(account: str, value: str) -> None:
    keyring.set_password(KEYRING_SERVICE, account, value)


def delete_secret(account: str) -> None:
    try:
        keyring.delete_password(KEYRING_SERVICE, account)
    except keyring.errors.PasswordDeleteError:
        pass


def normalize_ai_provider(value: str | None) -> str:
    if value in AI_PROVIDERS:
        return value
    return DEFAULT_AI_PROVIDER


def provider_model_setting_key(provider: str) -> str:
    if provider == "ollama":
        return "ollama_model"
    return f"ai_model_{provider}"


def get_provider_api_key(provider: str) -> str | None:
    account = PROVIDER_KEY_ACCOUNTS.get(provider)
    if not account:
        return None
    return get_secret(account)


def set_provider_api_key(provider: str, value: str) -> None:
    account = PROVIDER_KEY_ACCOUNTS.get(provider)
    if not account:
        return
    cleaned = value.strip()
    if cleaned:
        set_secret(account, cleaned)


def get_openai_api_key() -> str | None:
    return get_provider_api_key("openai")


def set_openai_api_key(value: str) -> None:
    set_provider_api_key("openai", value)
