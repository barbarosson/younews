"""Regional RSS packs the user can enable in Settings."""

from __future__ import annotations

SOURCE_PACKS: dict[str, list[tuple[str, str, str, str]]] = {
    "tr": [
        ("economy_markets", "economy_markets.stocks.bist", "Anadolu Ajansı", "https://www.aa.com.tr/tr/rss/default?cat=guncel"),
        ("economy_markets", "economy_markets.stocks.bist", "Bloomberg HT", "https://www.bloomberght.com/rss"),
        ("global_politics", "global_politics.geopolitics", "BBC Türkçe", "https://feeds.bbci.co.uk/turkce/rss.xml"),
    ],
    "us": [
        ("economy_markets", "economy_markets.stocks.wall_street", "CNBC US", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114"),
        ("global_politics", "global_politics.elections", "NPR News", "https://feeds.npr.org/1001/rss.xml"),
    ],
    "eu": [
        ("economy_markets", "economy_markets.stocks.europe", "BBC Business", "https://feeds.bbci.co.uk/news/business/rss.xml"),
        ("global_politics", "global_politics.geopolitics", "The Guardian World", "https://www.theguardian.com/world/rss"),
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
