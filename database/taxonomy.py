"""Canonical news modules, nested topics, and default RSS feeds."""

from __future__ import annotations

TAXONOMY_VERSION = "4"

CATALOG: list[dict] = [
    {
        "id": "economy_markets",
        "name_key": "modules.economy_markets",
        "icon": "trending-up",
        "sort": 10,
        "legacy_modules": ("economy",),
        "subcategories": [
            {
                "id": "economy_markets.macro",
                "name_key": "topics.economy_markets.macro",
                "topics": [
                    ("economy_markets.macro.calendar", "topics.economy_markets.macro.calendar"),
                    ("economy_markets.macro.central_banks", "topics.economy_markets.macro.central_banks"),
                    ("economy_markets.macro.inflation", "topics.economy_markets.macro.inflation"),
                    ("economy_markets.macro.rates", "topics.economy_markets.macro.rates"),
                    ("economy_markets.macro.debt", "topics.economy_markets.macro.debt"),
                ],
            },
            {
                "id": "economy_markets.stocks",
                "name_key": "topics.economy_markets.stocks",
                "topics": [
                    ("economy_markets.stocks.wall_street", "topics.economy_markets.stocks.wall_street"),
                    ("economy_markets.stocks.bist", "topics.economy_markets.stocks.bist"),
                    ("economy_markets.stocks.europe", "topics.economy_markets.stocks.europe"),
                    ("economy_markets.stocks.asia", "topics.economy_markets.stocks.asia"),
                ],
            },
            {
                "id": "economy_markets.commodities",
                "name_key": "topics.economy_markets.commodities",
                "topics": [
                    ("economy_markets.commodities.oil", "topics.economy_markets.commodities.oil"),
                    ("economy_markets.commodities.metals", "topics.economy_markets.commodities.metals"),
                    ("economy_markets.commodities.fx", "topics.economy_markets.commodities.fx"),
                ],
            },
            {
                "id": "economy_markets.corporate",
                "name_key": "topics.economy_markets.corporate",
                "topics": [
                    ("economy_markets.corporate.earnings", "topics.economy_markets.corporate.earnings"),
                    ("economy_markets.corporate.ma", "topics.economy_markets.corporate.ma"),
                    ("economy_markets.corporate.ipo", "topics.economy_markets.corporate.ipo"),
                ],
            },
        ],
    },
    {
        "id": "crypto_web3",
        "name_key": "modules.crypto_web3",
        "icon": "cpu",
        "sort": 20,
        "legacy_modules": ("economy",),
        "subcategories": [
            {
                "id": "crypto_web3.assets",
                "name_key": "topics.crypto_web3.assets",
                "topics": [
                    ("crypto_web3.assets.btc", "topics.crypto_web3.assets.btc"),
                    ("crypto_web3.assets.eth", "topics.crypto_web3.assets.eth"),
                    ("crypto_web3.assets.altcoins", "topics.crypto_web3.assets.altcoins"),
                ],
            },
            {
                "id": "crypto_web3.defi",
                "name_key": "topics.crypto_web3.defi",
                "topics": [
                    ("crypto_web3.defi.dex", "topics.crypto_web3.defi.dex"),
                    ("crypto_web3.defi.lending", "topics.crypto_web3.defi.lending"),
                    ("crypto_web3.defi.yield", "topics.crypto_web3.defi.yield"),
                ],
            },
            {
                "id": "crypto_web3.regulation",
                "name_key": "topics.crypto_web3.regulation",
                "topics": [
                    ("crypto_web3.regulation.sec", "topics.crypto_web3.regulation.sec"),
                    ("crypto_web3.regulation.etf", "topics.crypto_web3.regulation.etf"),
                    ("crypto_web3.regulation.cbdc", "topics.crypto_web3.regulation.cbdc"),
                ],
            },
            {
                "id": "crypto_web3.security",
                "name_key": "topics.crypto_web3.security",
                "topics": [
                    ("crypto_web3.security.exchanges", "topics.crypto_web3.security.exchanges"),
                    ("crypto_web3.security.hacks", "topics.crypto_web3.security.hacks"),
                    ("crypto_web3.security.nfts", "topics.crypto_web3.security.nfts"),
                ],
            },
        ],
    },
    {
        "id": "tech_mobility",
        "name_key": "modules.tech_mobility",
        "icon": "zap",
        "sort": 30,
        "legacy_modules": ("tech",),
        "subcategories": [
            {
                "id": "tech_mobility.ev",
                "name_key": "topics.tech_mobility.ev",
                "topics": [
                    ("tech_mobility.ev.makers", "topics.tech_mobility.ev.makers"),
                    ("tech_mobility.ev.battery", "topics.tech_mobility.ev.battery"),
                    ("tech_mobility.ev.autonomous", "topics.tech_mobility.ev.autonomous"),
                ],
            },
            {
                "id": "tech_mobility.ai",
                "name_key": "topics.tech_mobility.ai",
                "topics": [
                    ("tech_mobility.ai.llm", "topics.tech_mobility.ai.llm"),
                    ("tech_mobility.ai.chips", "topics.tech_mobility.ai.chips"),
                    ("tech_mobility.ai.robotics", "topics.tech_mobility.ai.robotics"),
                ],
            },
            {
                "id": "tech_mobility.consumer",
                "name_key": "topics.tech_mobility.consumer",
                "topics": [
                    ("tech_mobility.consumer.phones", "topics.tech_mobility.consumer.phones"),
                    ("tech_mobility.consumer.os", "topics.tech_mobility.consumer.os"),
                    ("tech_mobility.consumer.bigtech", "topics.tech_mobility.consumer.bigtech"),
                ],
            },
            {
                "id": "tech_mobility.cyber",
                "name_key": "topics.tech_mobility.cyber",
                "topics": [
                    ("tech_mobility.cyber.breaches", "topics.tech_mobility.cyber.breaches"),
                    ("tech_mobility.cyber.cloud", "topics.tech_mobility.cyber.cloud"),
                    ("tech_mobility.cyber.saas", "topics.tech_mobility.cyber.saas"),
                ],
            },
        ],
    },
    {
        "id": "global_politics",
        "name_key": "modules.global_politics",
        "icon": "globe",
        "sort": 40,
        "legacy_modules": ("politics",),
        "subcategories": [
            {
                "id": "global_politics.geopolitics",
                "name_key": "topics.global_politics.geopolitics",
                "topics": [
                    ("global_politics.geopolitics.us", "topics.global_politics.geopolitics.us"),
                    ("global_politics.geopolitics.eu", "topics.global_politics.geopolitics.eu"),
                    ("global_politics.geopolitics.mena", "topics.global_politics.geopolitics.mena"),
                    ("global_politics.geopolitics.indo_pacific", "topics.global_politics.geopolitics.indo_pacific"),
                ],
            },
            {
                "id": "global_politics.elections",
                "name_key": "topics.global_politics.elections",
                "topics": [
                    ("global_politics.elections.national", "topics.global_politics.elections.national"),
                    ("global_politics.elections.bills", "topics.global_politics.elections.bills"),
                    ("global_politics.elections.trade", "topics.global_politics.elections.trade"),
                ],
            },
            {
                "id": "global_politics.defense",
                "name_key": "topics.global_politics.defense",
                "topics": [
                    ("global_politics.defense.industry", "topics.global_politics.defense.industry"),
                    ("global_politics.defense.conflicts", "topics.global_politics.defense.conflicts"),
                    ("global_politics.defense.aerospace", "topics.global_politics.defense.aerospace"),
                ],
            },
        ],
    },
    {
        "id": "lifestyle_culture",
        "name_key": "modules.lifestyle_culture",
        "icon": "heart",
        "sort": 50,
        "legacy_modules": (),
        "subcategories": [
            {
                "id": "lifestyle_culture.arts",
                "name_key": "topics.lifestyle_culture.arts",
                "topics": [
                    ("lifestyle_culture.arts.contemporary", "topics.lifestyle_culture.arts.contemporary"),
                    ("lifestyle_culture.arts.market", "topics.lifestyle_culture.arts.market"),
                    ("lifestyle_culture.arts.museums", "topics.lifestyle_culture.arts.museums"),
                    ("lifestyle_culture.arts.digital", "topics.lifestyle_culture.arts.digital"),
                    ("lifestyle_culture.arts.performing", "topics.lifestyle_culture.arts.performing"),
                ],
            },
            {
                "id": "lifestyle_culture.health",
                "name_key": "topics.lifestyle_culture.health",
                "topics": [
                    ("lifestyle_culture.health.longevity", "topics.lifestyle_culture.health.longevity"),
                    ("lifestyle_culture.health.mental", "topics.lifestyle_culture.health.mental"),
                    ("lifestyle_culture.health.fitness", "topics.lifestyle_culture.health.fitness"),
                ],
            },
            {
                "id": "lifestyle_culture.design",
                "name_key": "topics.lifestyle_culture.design",
                "topics": [
                    ("lifestyle_culture.design.architecture", "topics.lifestyle_culture.design.architecture"),
                    ("lifestyle_culture.design.travel", "topics.lifestyle_culture.design.travel"),
                    ("lifestyle_culture.design.gastronomy", "topics.lifestyle_culture.design.gastronomy"),
                ],
            },
            {
                "id": "lifestyle_culture.work",
                "name_key": "topics.lifestyle_culture.work",
                "topics": [
                    ("lifestyle_culture.work.remote", "topics.lifestyle_culture.work.remote"),
                    ("lifestyle_culture.work.career", "topics.lifestyle_culture.work.career"),
                    ("lifestyle_culture.work.fire", "topics.lifestyle_culture.work.fire"),
                ],
            },
        ],
    },
    {
        "id": "sports_entertainment",
        "name_key": "modules.sports_entertainment",
        "icon": "activity",
        "sort": 60,
        "legacy_modules": ("sports",),
        "subcategories": [
            {
                "id": "sports_entertainment.football",
                "name_key": "topics.sports_entertainment.football",
                "topics": [
                    ("sports_entertainment.football.europe", "topics.sports_entertainment.football.europe"),
                    ("sports_entertainment.football.transfers", "topics.sports_entertainment.football.transfers"),
                    ("sports_entertainment.football.super_lig", "topics.sports_entertainment.football.super_lig"),
                ],
            },
            {
                "id": "sports_entertainment.motorsports",
                "name_key": "topics.sports_entertainment.motorsports",
                "topics": [
                    ("sports_entertainment.motorsports.f1", "topics.sports_entertainment.motorsports.f1"),
                    ("sports_entertainment.motorsports.motogp", "topics.sports_entertainment.motorsports.motogp"),
                    ("sports_entertainment.motorsports.wec", "topics.sports_entertainment.motorsports.wec"),
                ],
            },
            {
                "id": "sports_entertainment.us_sports",
                "name_key": "topics.sports_entertainment.us_sports",
                "topics": [
                    ("sports_entertainment.us_sports.nba", "topics.sports_entertainment.us_sports.nba"),
                    ("sports_entertainment.us_sports.nfl", "topics.sports_entertainment.us_sports.nfl"),
                ],
            },
            {
                "id": "sports_entertainment.entertainment",
                "name_key": "topics.sports_entertainment.entertainment",
                "topics": [
                    ("sports_entertainment.entertainment.gaming", "topics.sports_entertainment.entertainment.gaming"),
                    ("sports_entertainment.entertainment.cinema", "topics.sports_entertainment.entertainment.cinema"),
                ],
            },
        ],
    },
    {
        "id": "science_environment",
        "name_key": "modules.science_environment",
        "icon": "sun",
        "sort": 70,
        "legacy_modules": ("tech",),
        "subcategories": [
            {
                "id": "science_environment.space",
                "name_key": "topics.science_environment.space",
                "topics": [
                    ("science_environment.space.missions", "topics.science_environment.space.missions"),
                    ("science_environment.space.astronomy", "topics.science_environment.space.astronomy"),
                    ("science_environment.space.commercial", "topics.science_environment.space.commercial"),
                ],
            },
            {
                "id": "science_environment.climate",
                "name_key": "topics.science_environment.climate",
                "topics": [
                    ("science_environment.climate.renewables", "topics.science_environment.climate.renewables"),
                    ("science_environment.climate.nuclear", "topics.science_environment.climate.nuclear"),
                    ("science_environment.climate.carbon", "topics.science_environment.climate.carbon"),
                ],
            },
            {
                "id": "science_environment.disasters",
                "name_key": "topics.science_environment.disasters",
                "topics": [
                    ("science_environment.disasters.quakes", "topics.science_environment.disasters.quakes"),
                    ("science_environment.disasters.weather", "topics.science_environment.disasters.weather"),
                    ("science_environment.disasters.aid", "topics.science_environment.disasters.aid"),
                ],
            },
            {
                "id": "science_environment.podcasts",
                "name_key": "topics.science_environment.podcasts",
                "topics": [
                    ("science_environment.podcasts.news", "topics.science_environment.podcasts.news"),
                ],
            },
        ],
    },
    {
        "id": "social_media",
        "name_key": "modules.social_media",
        "icon": "globe",
        "sort": 80,
        "legacy_modules": (),
        "subcategories": [
            {
                "id": "social_media.youtube",
                "name_key": "topics.social_media.youtube",
                "topics": [
                    ("social_media.youtube.latest", "topics.social_media.youtube.latest"),
                ],
            },
            {
                "id": "social_media.substack",
                "name_key": "topics.social_media.substack",
                "topics": [
                    ("social_media.substack.latest", "topics.social_media.substack.latest"),
                ],
            },
            {
                "id": "social_media.bluesky",
                "name_key": "topics.social_media.bluesky",
                "topics": [
                    ("social_media.bluesky.latest", "topics.social_media.bluesky.latest"),
                ],
            },
        ],
    },
]

LEGACY_TOPIC_REMAP = {
    "economy.markets": "economy_markets.stocks",
    "economy.crypto": "crypto_web3.assets",
    "economy.business": "economy_markets.corporate",
    "tech.ai": "tech_mobility.ai",
    "tech.gadgets": "tech_mobility.consumer",
    "tech.science": "science_environment.space",
    "tech.hacker_news": "tech_mobility.cyber",
    "sports.football": "sports_entertainment.football",
    "sports.football.big5": "sports_entertainment.football.europe",
    "sports.football.premier_league": "sports_entertainment.football.europe",
    "sports.football.la_liga": "sports_entertainment.football.europe",
    "sports.football.bundesliga": "sports_entertainment.football.europe",
    "sports.football.serie_a": "sports_entertainment.football.europe",
    "sports.football.ligue_1": "sports_entertainment.football.europe",
    "sports.football.other": "sports_entertainment.football",
    "sports.basketball": "sports_entertainment.us_sports",
    "sports.basketball.nba": "sports_entertainment.us_sports.nba",
    "sports.basketball.fiba": "sports_entertainment.us_sports.nba",
    "sports.other": "sports_entertainment.entertainment",
    "politics.world": "global_politics.geopolitics",
    "politics.us": "global_politics.elections",
}

LEGACY_MODULE_REMAP = {
    "economy": "economy_markets",
    "tech": "tech_mobility",
    "sports": "sports_entertainment",
    "politics": "global_politics",
}

SOURCE_URL_REMAP = {
    "https://www.coindesk.com/arc/outboundfeeds/rss/": ("crypto_web3", "crypto_web3.assets"),
    "https://feeds.arstechnica.com/arstechnica/index": ("science_environment", "science_environment.space"),
    "https://www.wired.com/feed/rss": ("tech_mobility", "tech_mobility.consumer"),
    "https://hnrss.org/frontpage": ("tech_mobility", "tech_mobility.cyber"),
    "https://electrek.co/feed/": ("tech_mobility", "tech_mobility.ev"),
}


MODULE_IDS: set[str] = {item["id"] for item in CATALOG}


def seed_modules() -> list[tuple[str, str, int, str, int]]:
    return [(item["id"], item["name_key"], 1, item["icon"], item["sort"]) for item in CATALOG]


def seed_topics() -> list[tuple[str, str, str | None, str, int]]:
    rows: list[tuple[str, str, str | None, str, int]] = []
    for module in CATALOG:
        for cat_order, category in enumerate(module["subcategories"], start=1):
            rows.append((category["id"], module["id"], None, category["name_key"], cat_order * 10))
            for topic_order, (topic_id, name_key) in enumerate(category["topics"], start=1):
                rows.append((topic_id, module["id"], category["id"], name_key, topic_order * 10))
    return rows


DEFAULT_SOURCES: list[tuple[str, str, str]] = [
    ("BBC News", "https://feeds.bbci.co.uk/news/world/rss.xml", "global_politics.geopolitics"),
    ("The Guardian", "https://www.theguardian.com/world/rss", "global_politics.geopolitics"),
    ("The New York Times", "https://rss.nytimes.com/services/xml/rss/nyt/World.xml", "global_politics.geopolitics"),
    ("Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml", "global_politics.geopolitics"),
    ("Deutsche Welle (DW)", "https://rss.dw.com/rdf/rss-en-all", "global_politics.geopolitics"),
    ("France 24", "https://www.france24.com/en/rss", "global_politics.geopolitics"),
    ("Bloomberg Markets", "https://feeds.bloomberg.com/markets/news.rss", "economy_markets.stocks"),
    ("CNBC Top News", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114", "economy_markets.stocks"),
    ("TechCrunch", "https://techcrunch.com/feed/", "tech_mobility.ai"),
    ("BBC Sport", "https://feeds.bbci.co.uk/sport/rss.xml", "sports_entertainment.football"),
]


def seed_sources() -> list[tuple[str, str, str, int, None, str]]:
    rows: list[tuple[str, str, str, int, None, str]] = []
    for name, url, topic_id in DEFAULT_SOURCES:
        rows.append((topic_module_id(topic_id), name, url, 1, None, topic_id))
    return rows


def topic_module_id(topic_id: str) -> str | None:
    for module in CATALOG:
        mid = module["id"]
        if topic_id == mid or topic_id.startswith(mid + "."):
            return mid
    return LEGACY_MODULE_REMAP.get(topic_id.split(".")[0] if topic_id else "")


def current_topic_ids() -> set[str]:
    return {row[0] for row in seed_topics()}


def current_module_ids() -> set[str]:
    return set(MODULE_IDS)


def parent_topic_id(topic_id: str) -> str | None:
    for module in CATALOG:
        for category in module["subcategories"]:
            if category["id"] == topic_id:
                return None
            for leaf_id, _name in category["topics"]:
                if leaf_id == topic_id:
                    return category["id"]
    return None


def module_leaf_ids(module_id: str) -> list[str]:
    leaves: list[str] = []
    for module in CATALOG:
        if module["id"] != module_id:
            continue
        for category in module["subcategories"]:
            for leaf_id, _name in category["topics"]:
                leaves.append(leaf_id)
    return leaves


def topic_leaf_ids(topic_id: str) -> list[str]:
    if not topic_id:
        return []
    for module in CATALOG:
        if topic_id == module["id"]:
            return module_leaf_ids(module["id"])
        for category in module["subcategories"]:
            if category["id"] == topic_id:
                return [leaf_id for leaf_id, _name in category["topics"]]
            for leaf_id, _name in category["topics"]:
                if leaf_id == topic_id:
                    return [leaf_id]
    return [topic_id]


def default_leaf_id(module_id: str | None, source_topic_id: str | None) -> str | None:
    if source_topic_id:
        leaves = topic_leaf_ids(source_topic_id)
        if leaves:
            return leaves[0]
    if module_id:
        leaves = module_leaf_ids(module_id)
        if leaves:
            return leaves[0]
    return None


def legacy_modules_for(module_id: str) -> tuple[str, ...]:
    for item in CATALOG:
        if item["id"] == module_id:
            return tuple(item.get("legacy_modules") or ())
    return ()
