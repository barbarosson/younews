"""Searchable market catalog: names, countries, and companies — not Yahoo codes."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CatalogTicker:
    symbol: str
    label: str
    category: str
    country: str
    aliases: tuple[str, ...] = ()


def _t(
    symbol: str,
    label: str,
    category: str,
    country: str,
    *aliases: str,
) -> CatalogTicker:
    return CatalogTicker(symbol, label, category, country, aliases)


TICKER_CATALOG: tuple[CatalogTicker, ...] = (
    _t("^GSPC", "S&P 500", "indices", "ABD", "spx", "sp500", "wall street", "abd borsa", "us stocks"),
    _t("^DJI", "Dow Jones", "indices", "ABD", "dow", "djia"),
    _t("^IXIC", "NASDAQ", "indices", "ABD", "nasdaq", "tech"),
    _t("^RUT", "Russell 2000", "indices", "ABD", "russell"),
    _t("XU100.IS", "BIST 100", "indices", "Türkiye", "xu100", "borsa istanbul", "istanbul", "türkiye borsa", "bist"),
    _t("XU030.IS", "BIST 30", "indices", "Türkiye", "xu030", "bist 30"),
    _t("^FTSE", "FTSE 100", "indices", "Birleşik Krallık", "london", "uk"),
    _t("^GDAXI", "DAX", "indices", "Almanya", "frankfurt", "alman borsa"),
    _t("^FCHI", "CAC 40", "indices", "Fransa", "paris"),
    _t("^STOXX50E", "Euro Stoxx 50", "indices", "Avrupa", "avrupa borsa"),
    _t("^N225", "Nikkei 225", "indices", "Japonya", "tokyo", "nikkei"),
    _t("^HSI", "Hang Seng", "indices", "Hong Kong", "hong kong"),
    _t("000001.SS", "Shanghai Composite", "indices", "Çin", "shanghai", "china"),
    _t("^BSESN", "BSE Sensex", "indices", "Hindistan", "mumbai", "sensex"),
    _t("^NSEI", "Nifty 50", "indices", "Hindistan", "nifty"),
    _t("^AXJO", "ASX 200", "indices", "Avustralya", "sydney"),
    _t("^KS11", "KOSPI", "indices", "Güney Kore", "seoul", "korea"),
    _t("^TWII", "TAIEX", "indices", "Tayvan", "taiwan"),
    _t("^GSPTSE", "S&P/TSX", "indices", "Kanada", "toronto"),
    _t("^BVSP", "Bovespa", "indices", "Brezilya", "sao paulo"),
    _t("^MXX", "IPC Mexico", "indices", "Meksika", "mexico"),
    _t("^IBEX", "IBEX 35", "indices", "İspanya", "madrid"),
    _t("^AEX", "AEX", "indices", "Hollanda", "amsterdam"),
    _t("^SSMI", "SMI", "indices", "İsviçre", "zurich"),
    _t("USDTRY=X", "USD/TRY", "fx", "Türkiye", "dolar", "dolar/tl", "usd try", "amerikan doları", "kur"),
    _t("EURTRY=X", "EUR/TRY", "fx", "Türkiye", "euro", "euro/tl", "avro"),
    _t("GBPTRY=X", "GBP/TRY", "fx", "Türkiye", "sterlin", "pound"),
    _t("EURUSD=X", "EUR/USD", "fx", "Avrupa", "euro dollar"),
    _t("GBPUSD=X", "GBP/USD", "fx", "Birleşik Krallık", "cable", "pound dollar"),
    _t("USDJPY=X", "USD/JPY", "fx", "Japonya", "yen"),
    _t("USDCHF=X", "USD/CHF", "fx", "İsviçre", "franc"),
    _t("AUDUSD=X", "AUD/USD", "fx", "Avustralya", "aussie"),
    _t("USDCNY=X", "USD/CNY", "fx", "Çin", "yuan", "renminbi"),
    _t("USDSEK=X", "USD/SEK", "fx", "İsveç", "kron"),
    _t("DX-Y.NYB", "US Dollar Index", "fx", "ABD", "dxy", "dolar endeksi"),
    _t("CL=F", "WTI Crude", "commodities", "ABD", "petrol", "oil", "ham petrol", "wti", "crude", "texas"),
    _t("BZ=F", "Brent Crude", "commodities", "Birleşik Krallık", "brent", "petrol", "oil", "kuzey denizi"),
    _t("HO=F", "Heating Oil", "commodities", "ABD", "kalorifer yakıtı", "heating oil"),
    _t("NG=F", "Natural Gas", "commodities", "ABD", "doğalgaz", "gas", "lng"),
    _t("GC=F", "Gold", "commodities", "Küresel", "altın", "gold", "gram altın", "ons", "xau"),
    _t("SI=F", "Silver", "commodities", "Küresel", "gümüş", "silver", "xag"),
    _t("HG=F", "Copper", "commodities", "Küresel", "bakır", "copper"),
    _t("ZC=F", "Corn", "commodities", "ABD", "mısır"),
    _t("ZW=F", "Wheat", "commodities", "ABD", "buğday"),
    _t("BTC-USD", "Bitcoin", "crypto", "Küresel", "btc", "bitcoin"),
    _t("ETH-USD", "Ethereum", "crypto", "Küresel", "eth", "ether"),
    _t("SOL-USD", "Solana", "crypto", "Küresel", "sol"),
    _t("AAPL", "Apple", "stocks", "ABD", "apple", "iphone"),
    _t("MSFT", "Microsoft", "stocks", "ABD", "microsoft"),
    _t("NVDA", "NVIDIA", "stocks", "ABD", "nvidia", "chip"),
    _t("GOOGL", "Alphabet", "stocks", "ABD", "google"),
    _t("AMZN", "Amazon", "stocks", "ABD", "amazon"),
    _t("META", "Meta", "stocks", "ABD", "facebook", "meta"),
    _t("TSLA", "Tesla", "stocks", "ABD", "tesla"),
    _t("JPM", "JPMorgan", "stocks", "ABD", "jpmorgan", "bank"),
    _t("XOM", "Exxon Mobil", "stocks", "ABD", "exxon", "petrol şirketi"),
    _t("CVX", "Chevron", "stocks", "ABD", "chevron"),
    _t("SHEL", "Shell", "stocks", "Birleşik Krallık", "shell", "petrol"),
    _t("BP", "BP", "stocks", "Birleşik Krallık", "british petroleum"),
    _t("TTE", "TotalEnergies", "stocks", "Fransa", "total"),
    _t("BMW.DE", "BMW", "stocks", "Almanya", "bmw"),
    _t("VOW3.DE", "Volkswagen", "stocks", "Almanya", "vw", "volkswagen"),
    _t("SAP.DE", "SAP", "stocks", "Almanya", "sap"),
    _t("GARAN.IS", "Garanti BBVA", "stocks", "Türkiye", "garanti", "banka"),
    _t("AKBNK.IS", "Akbank", "stocks", "Türkiye", "akbank"),
    _t("YKBNK.IS", "Yapı Kredi", "stocks", "Türkiye", "yapı kredi", "ykb"),
    _t("ISCTR.IS", "İş Bankası", "stocks", "Türkiye", "iş bankası", "isbank"),
    _t("HALKB.IS", "Halkbank", "stocks", "Türkiye", "halkbank"),
    _t("VAKBN.IS", "VakıfBank", "stocks", "Türkiye", "vakıfbank"),
    _t("THYAO.IS", "Türk Hava Yolları", "stocks", "Türkiye", "thy", "turkish airlines"),
    _t("PGSUS.IS", "Pegasus", "stocks", "Türkiye", "pegasus"),
    _t("TUPRS.IS", "Tüpraş", "stocks", "Türkiye", "tüpraş", "tupras", "rafineri", "petrol"),
    _t("PETKM.IS", "Petkim", "stocks", "Türkiye", "petkim", "petrokimya"),
    _t("BIMAS.IS", "BİM", "stocks", "Türkiye", "bim"),
    _t("MGROS.IS", "Migros", "stocks", "Türkiye", "migros"),
    _t("EREGL.IS", "Ereğli Demir Çelik", "stocks", "Türkiye", "ereğli", "erdemir", "çelik"),
    _t("KCHOL.IS", "Koç Holding", "stocks", "Türkiye", "koç", "koc"),
    _t("SAHOL.IS", "Sabancı Holding", "stocks", "Türkiye", "sabancı"),
    _t("ASELS.IS", "Aselsan", "stocks", "Türkiye", "aselsan", "savunma"),
    _t("TCELL.IS", "Turkcell", "stocks", "Türkiye", "turkcell"),
    _t("TTKOM.IS", "Türk Telekom", "stocks", "Türkiye", "türk telekom"),
    _t("SISE.IS", "Şişecam", "stocks", "Türkiye", "şişecam", "sisecam"),
    _t("FROTO.IS", "Ford Otosan", "stocks", "Türkiye", "ford otosan", "otosans"),
    _t("TOASO.IS", "Tofaş", "stocks", "Türkiye", "tofaş", "fiat"),
    _t("AEFES.IS", "Anadolu Efes", "stocks", "Türkiye", "efes"),
    _t("ENKAI.IS", "Enka", "stocks", "Türkiye", "enka"),
)

QUICK_FILTERS: tuple[tuple[str, str], ...] = (
    ("oil", "petrol"),
    ("turkey", "türkiye"),
    ("fx", "kur"),
    ("gold", "altın"),
    ("bist", "bist"),
    ("crypto", "kripto"),
)

_BY_SYMBOL = {item.symbol.casefold(): item for item in TICKER_CATALOG}


_FOLD_MAP = str.maketrans(
    {
        "ı": "i",
        "ü": "u",
        "ö": "o",
        "ş": "s",
        "ğ": "g",
        "ç": "c",
        "â": "a",
        "î": "i",
        "û": "u",
        "é": "e",
        "á": "a",
        "ó": "o",
        "ñ": "n",
    }
)


def _fold(text: str) -> str:
    raw = (text or "").casefold().translate(_FOLD_MAP)
    return " ".join(raw.split())


def search_catalog(query: str, *, limit: int = 48) -> list[CatalogTicker]:
    needle = _fold(query)
    if not needle:
        return list(TICKER_CATALOG[:limit])
    tokens = [part for part in needle.split() if part]
    ranked: list[tuple[int, CatalogTicker]] = []
    for item in TICKER_CATALOG:
        hay = _fold(
            " ".join(
                (item.symbol, item.label, item.country, item.category, " ".join(item.aliases))
            )
        )
        if not all(token in hay for token in tokens):
            continue
        score = 0
        label = _fold(item.label)
        country = _fold(item.country)
        if needle == label or needle == _fold(item.symbol):
            score += 50
        if needle in label:
            score += 20
        if needle in country:
            score += 12
        if any(needle in _fold(alias) for alias in item.aliases):
            score += 16
        if needle in _fold(item.symbol):
            score += 8
        ranked.append((score, item))
    ranked.sort(key=lambda row: (-row[0], row[1].label))
    return [item for _score, item in ranked[:limit]]


def catalog_by_symbol(symbol: str) -> CatalogTicker | None:
    return _BY_SYMBOL.get((symbol or "").strip().casefold())


def aliases_for(symbol: str) -> list[str]:
    item = catalog_by_symbol(symbol)
    if item is None:
        return []
    return [item.label, item.country, *item.aliases]


def country_i18n_key(country: str) -> str:
    mapping = {
        "ABD": "country.us",
        "Türkiye": "country.tr",
        "Birleşik Krallık": "country.uk",
        "Almanya": "country.de",
        "Fransa": "country.fr",
        "Avrupa": "country.eu",
        "Japonya": "country.jp",
        "Hong Kong": "country.hk",
        "Çin": "country.cn",
        "Hindistan": "country.in",
        "Avustralya": "country.au",
        "Güney Kore": "country.kr",
        "Tayvan": "country.tw",
        "Kanada": "country.ca",
        "Brezilya": "country.br",
        "Meksika": "country.mx",
        "İspanya": "country.es",
        "Hollanda": "country.nl",
        "İsviçre": "country.ch",
        "Küresel": "country.global",
    }
    return mapping.get(country or "", "")
