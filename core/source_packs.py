"""Regional RSS packs the user can enable in Settings."""

from __future__ import annotations

SOURCE_PACKS: dict[str, list[tuple[str, str, str, str]]] = {
    "tr": [
        ("economy_markets", "economy_markets.stocks.bist", "Anadolu Ajansı", "https://www.aa.com.tr/tr/rss/default?cat=guncel"),
        ("economy_markets", "economy_markets.stocks.bist", "Bloomberg HT", "https://www.bloomberght.com/rss"),
        ("global_politics", "global_politics.geopolitics", "BBC Türkçe", "https://feeds.bbci.co.uk/turkce/rss.xml"),
    ],
    "us": [
        ("global_politics", "global_politics.elections", "NPR News", "https://feeds.npr.org/1001/rss.xml"),
        ("global_politics", "global_politics.elections", "Politico", "https://rss.politico.com/politics-news.xml"),
    ],
    "eu": [
        ("economy_markets", "economy_markets.stocks.europe", "BBC Business", "https://feeds.bbci.co.uk/news/business/rss.xml"),
        ("global_politics", "global_politics.geopolitics", "Der Spiegel", "https://www.spiegel.de/schlagzeilen/index.rss"),
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
    "mastodon": [
        ("social_media", None, "Mastodon News", "https://mastodon.social/tags/news.rss"),
        ("science_environment", "science_environment.podcasts.news", "404 Media", "https://www.404media.co/rss"),
    ],
}


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
