"""Ready-made RSS packs: 10 countries, 5 continents, 5 topic branches (≤20)."""

from __future__ import annotations

# (module_id, topic_id, display name, feed url)
SOURCE_PACKS: dict[str, list[tuple[str, str | None, str, str]]] = {
    # —— 10 countries ——
    "tr": [
        ("economy_markets", "economy_markets.stocks.bist", "Anadolu Ajansı", "https://www.aa.com.tr/tr/rss/default?cat=guncel"),
        ("economy_markets", "economy_markets.stocks.bist", "Bloomberg HT", "https://www.bloomberght.com/rss"),
        ("global_politics", "global_politics.geopolitics", "BBC Türkçe", "https://feeds.bbci.co.uk/turkce/rss.xml"),
    ],
    "us": [
        ("global_politics", "global_politics.elections", "NPR News", "https://feeds.npr.org/1001/rss.xml"),
        ("global_politics", "global_politics.elections", "Politico", "https://rss.politico.com/politics-news.xml"),
    ],
    "uk": [
        ("economy_markets", "economy_markets.macro", "BBC Business", "https://feeds.bbci.co.uk/news/business/rss.xml"),
        ("sports_entertainment", "sports_entertainment.football", "BBC Football", "https://feeds.bbci.co.uk/sport/football/rss.xml"),
    ],
    "de": [
        ("global_politics", "global_politics.geopolitics", "Der Spiegel", "https://www.spiegel.de/schlagzeilen/index.rss"),
    ],
    "fr": [
        ("global_politics", "global_politics.geopolitics", "Le Monde", "https://www.lemonde.fr/rss/une.xml"),
    ],
    "jp": [
        ("global_politics", "global_politics.geopolitics", "NHK World", "https://www3.nhk.or.jp/rss/news/cat0.xml"),
    ],
    "kr": [
        ("global_politics", "global_politics.geopolitics", "Yonhap", "https://en.yna.co.kr/RSS/news.xml"),
        ("global_politics", "global_politics.geopolitics", "Korea Times", "https://www.koreatimes.co.kr/www/rss/nation.xml"),
        ("global_politics", "global_politics.geopolitics", "KBS World", "https://world.kbs.co.kr/rss/rss_news.htm?lang=e"),
    ],
    "in": [
        ("global_politics", "global_politics.geopolitics", "Times of India", "https://timesofindia.indiatimes.com/rssfeedstopstories.cms"),
    ],
    "cn": [
        ("global_politics", "global_politics.geopolitics", "South China Morning Post", "https://www.scmp.com/rss/91/feed"),
        ("global_politics", "global_politics.geopolitics", "BBC Asia", "https://feeds.bbci.co.uk/news/world/asia/rss.xml"),
    ],
    "br": [
        ("global_politics", "global_politics.geopolitics", "Agência Brasil", "https://agenciabrasil.ebc.com.br/rss/ultimasnoticias/feed.xml"),
        ("global_politics", "global_politics.geopolitics", "Folha de S.Paulo", "https://feeds.folha.uol.com.br/emcimadahora/rss091.xml"),
        ("global_politics", "global_politics.geopolitics", "G1", "https://g1.globo.com/rss/g1/"),
        ("global_politics", "global_politics.geopolitics", "BBC Brasil", "https://feeds.bbci.co.uk/portuguese/rss.xml"),
    ],
    # —— 5 continents / regions ——
    "eu": [
        ("economy_markets", "economy_markets.stocks.europe", "BBC Business", "https://feeds.bbci.co.uk/news/business/rss.xml"),
        ("global_politics", "global_politics.geopolitics", "Der Spiegel", "https://www.spiegel.de/schlagzeilen/index.rss"),
        ("global_politics", "global_politics.geopolitics", "The Guardian World", "https://www.theguardian.com/world/rss"),
    ],
    "asia": [
        ("global_politics", "global_politics.geopolitics", "BBC Asia", "https://feeds.bbci.co.uk/news/world/asia/rss.xml"),
        ("global_politics", "global_politics.geopolitics", "NHK World", "https://www3.nhk.or.jp/rss/news/cat0.xml"),
        ("global_politics", "global_politics.geopolitics", "Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml"),
    ],
    "latam": [
        ("global_politics", "global_politics.geopolitics", "Clarín", "https://www.clarin.com/rss/lo-ultimo/"),
        ("global_politics", "global_politics.geopolitics", "La Nación", "https://www.lanacion.com.ar/arc/outboundfeeds/rss/?outputType=xml"),
        ("global_politics", "global_politics.geopolitics", "BBC Mundo", "https://feeds.bbci.co.uk/mundo/rss.xml"),
    ],
    "africa": [
        ("global_politics", "global_politics.geopolitics", "BBC Africa", "https://feeds.bbci.co.uk/news/world/africa/rss.xml"),
        ("global_politics", "global_politics.geopolitics", "Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml"),
    ],
    "me": [
        ("global_politics", "global_politics.geopolitics", "BBC Middle East", "https://feeds.bbci.co.uk/news/world/middle_east/rss.xml"),
        ("global_politics", "global_politics.geopolitics", "Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml"),
    ],
    # —— 5 main news branches ——
    "tech": [
        ("tech_mobility", "tech_mobility.consumer", "The Verge", "https://www.theverge.com/rss/index.xml"),
        ("tech_mobility", "tech_mobility.consumer", "Wired", "https://www.wired.com/feed/rss"),
        ("tech_mobility", "tech_mobility.cyber", "Hacker News", "https://hnrss.org/frontpage"),
    ],
    "science": [
        ("science_environment", "science_environment.space", "Phys.org", "https://phys.org/rss-feed/"),
        ("science_environment", "science_environment.space", "Ars Technica", "https://feeds.arstechnica.com/arstechnica/index"),
    ],
    "crypto": [
        ("crypto_web3", "crypto_web3.assets", "CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/"),
        ("crypto_web3", "crypto_web3.assets", "CoinTelegraph", "https://cointelegraph.com/rss"),
    ],
    "sport": [
        ("sports_entertainment", "sports_entertainment.us_sports", "ESPN Top News", "https://www.espn.com/espn/rss/news"),
        ("sports_entertainment", "sports_entertainment.football", "Guardian Football", "https://www.theguardian.com/football/rss"),
    ],
    "politics": [
        ("global_politics", "global_politics.geopolitics", "The Guardian World", "https://www.theguardian.com/world/rss"),
        ("global_politics", "global_politics.geopolitics", "Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml"),
        ("global_politics", "global_politics.elections", "Politico", "https://rss.politico.com/politics-news.xml"),
    ],
}

# Display order in Settings (must stay ≤20 and match SOURCE_PACKS keys).
PACK_ORDER: tuple[str, ...] = (
    "tr", "us", "uk", "de", "fr", "jp", "kr", "in", "cn", "br",
    "eu", "asia", "latam", "africa", "me",
    "tech", "science", "crypto", "sport", "politics",
)

assert len(PACK_ORDER) <= 20
assert set(PACK_ORDER) == set(SOURCE_PACKS)


def apply_source_pack(db, pack_id: str) -> int:
    added = 0
    for module_id, topic_id, name, url in SOURCE_PACKS.get(pack_id, []):
        if db.find_source_by_url(url):
            continue
        try:
            db.add_user_source(name=name, url=url, module_id=module_id, is_rss=True, topic_id=topic_id)
            added += 1
        except Exception:
            continue
    return added
