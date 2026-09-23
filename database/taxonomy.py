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
        "sources": [
            ("Reuters Business", "https://feeds.reuters.com/reuters/businessNews", "economy_markets.stocks"),
            ("Bloomberg Markets", "https://feeds.bloomberg.com/markets/news.rss", "economy_markets.stocks"),
            ("CNBC Top News", "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114", "economy_markets.stocks"),
            ("Yahoo Finance", "https://finance.yahoo.com/news/rssindex", "economy_markets.stocks"),
            ("BBC Business", "https://feeds.bbci.co.uk/news/business/rss.xml", "economy_markets.macro"),
            ("ForexLive", "https://www.forexlive.com/feed/news", "economy_markets.macro.calendar"),
            ("NPR Business", "https://feeds.npr.org/1014/rss.xml", "economy_markets.corporate"),
            ("NYT Business", "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml", "economy_markets.corporate"),
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
        "sources": [
            ("CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/", "crypto_web3.assets"),
            ("CoinTelegraph", "https://cointelegraph.com/rss", "crypto_web3.assets"),
            ("Decrypt", "https://decrypt.co/feed", "crypto_web3.assets"),
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
        "sources": [
            ("The Verge", "https://www.theverge.com/rss/index.xml", "tech_mobility.consumer"),
            ("TechCrunch", "https://techcrunch.com/feed/", "tech_mobility.ai"),
            ("Electrek", "https://electrek.co/feed/", "tech_mobility.ev"),
            ("Wired", "https://www.wired.com/feed/rss", "tech_mobility.consumer"),
            ("Hacker News", "https://hnrss.org/frontpage", "tech_mobility.cyber"),
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
        "sources": [
            ("Anadolu Ajansı", "https://www.aa.com.tr/tr/rss/default?cat=gundem", "global_politics.geopolitics"),
            ("TRT Haber", "https://www.trthaber.com/sitene-ekle/rss/manset/", "global_politics.geopolitics"),
            ("The New York Times", "https://rss.nytimes.com/services/xml/rss/nyt/World.xml", "global_politics.geopolitics"),
            ("CNN International", "https://rss.cnn.com/rss/edition_world.rss", "global_politics.geopolitics"),
            ("BBC News", "https://feeds.bbci.co.uk/news/world/rss.xml", "global_politics.geopolitics"),
            ("The Guardian", "https://www.theguardian.com/world/rss", "global_politics.geopolitics"),
            ("Deutsche Welle (DW)", "https://rss.dw.com/rdf/rss-en-all", "global_politics.geopolitics"),
            ("Der Spiegel", "https://www.spiegel.de/schlagzeilen/index.rss", "global_politics.geopolitics"),
            ("France 24", "https://www.france24.com/en/rss", "global_politics.geopolitics"),
            ("Le Monde", "https://www.lemonde.fr/rss/une.xml", "global_politics.geopolitics"),
            ("CGTN", "https://www.cgtn.com/subscribe/rss/world.xml", "global_politics.geopolitics"),
            ("NHK World", "https://www3.nhk.or.jp/rss/news/cat0.xml", "global_politics.geopolitics"),
            ("The Times of India", "https://timesofindia.indiatimes.com/rssfeedstopstories.cms", "global_politics.geopolitics"),
            ("The Hindu", "https://www.thehindu.com/feeder/default.rss", "global_politics.geopolitics"),
            ("ANSA", "https://www.ansa.it/sito/ansait_rss.xml", "global_politics.geopolitics"),
            ("CBC News", "https://rss.cbc.ca/lineup/topstories.xml", "global_politics.geopolitics"),
            ("Yonhap News Agency", "https://en.yna.co.kr/RSS/news.xml", "global_politics.geopolitics"),
            ("ABC News", "https://www.abc.net.au/news/feed/51120/rss.xml", "global_politics.geopolitics"),
            ("G1 (Globo)", "https://g1.globo.com/rss/g1/", "global_politics.geopolitics"),
            ("El País", "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada", "global_politics.geopolitics"),
            ("El Universal", "https://www.eluniversal.com.mx/rss.xml", "global_politics.geopolitics"),
            ("TASS", "https://tass.com/rss/v2.xml", "global_politics.geopolitics"),
            ("Antara News", "https://www.antaranews.com/rss/terkini.xml", "global_politics.geopolitics"),
            ("Arab News", "https://www.arabnews.com/cat/1/rss.xml", "global_politics.geopolitics"),
            ("NOS News", "https://feeds.nos.nl/nosnieuws", "global_politics.geopolitics"),
            ("SWI swissinfo.ch", "https://www.swissinfo.ch/eng/rss/index", "global_politics.geopolitics"),
            ("TVN24", "https://tvn24.pl/najnowsze.xml", "global_politics.geopolitics"),
            ("Clarín", "https://www.clarin.com/rss/lo-ultimo/", "global_politics.geopolitics"),
            ("Sveriges Radio", "https://sverigesradio.se/rssfeed/rssfeed.aspx?elfeed=2054", "global_politics.geopolitics"),
            ("VRT NWS", "https://www.vrt.be/vrtnws/nl.rss.headlines.xml", "global_politics.geopolitics"),
            ("Premium Times", "https://www.premiumtimesng.com/feed", "global_politics.geopolitics"),
            ("Ahram Online", "https://english.ahram.org.eg/rss/World.aspx", "global_politics.geopolitics"),
            ("ORF", "https://rss.orf.at/news.xml", "global_politics.geopolitics"),
            ("RTÉ News", "https://www.rte.ie/news/rss/news-headlines.xml", "global_politics.geopolitics"),
            ("The Times of Israel", "https://www.timesofisrael.com/feed/", "global_politics.geopolitics"),
            ("NRK", "https://www.nrk.no/toppsaker.rss", "global_politics.geopolitics"),
            ("The National", "https://www.thenationalnews.com/arc/outboundfeeds/rss/", "global_politics.geopolitics"),
            ("CNA (Channel NewsAsia)", "https://www.channelnewsasia.com/api/v1/rss-outbound/rssnews/posts.xml", "global_politics.geopolitics"),
            ("DR Nyheder", "https://www.dr.dk/nyheder/service/feeds/alleneheder", "global_politics.geopolitics"),
            ("Bernama", "https://www.bernama.com/en/rss/news.php", "global_politics.geopolitics"),
            ("News24", "http://feeds.news24.com/articles/news24/World/rss", "global_politics.geopolitics"),
            ("Philippine News Agency", "https://www.pna.gov.ph/rss", "global_politics.geopolitics"),
            ("El Tiempo", "https://www.eltiempo.com/rss/mundo.xml", "global_politics.geopolitics"),
            ("Yle News", "https://feeds.yle.fi/uutiset/v1/majorHeadlines/YLE_UUTISET.rss", "global_politics.geopolitics"),
            ("RTP Notícias", "https://www.rtp.pt/noticias/rss", "global_politics.geopolitics"),
            ("AMNA (Athens News Agency)", "https://www.amna.gr/rss/feed", "global_politics.geopolitics"),
            ("Bangkok Post", "https://www.bangkokpost.com/rss/data/topstories.xml", "global_politics.geopolitics"),
            ("VnExpress", "https://vnexpress.net/rss/tin-moi-nhat.rss", "global_politics.geopolitics"),
            ("Dawn", "https://www.dawn.com/feeds/home/", "global_politics.geopolitics"),
            ("The Kyiv Independent", "https://kyivindependent.com/feed/", "global_politics.geopolitics"),
            ("RNZ (Radio New Zealand)", "https://www.rnz.co.nz/rss/news.xml", "global_politics.geopolitics"),
            ("Radio Prague International", "https://english.radio.cz/rss/news", "global_politics.geopolitics"),
            ("Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml", "global_politics.geopolitics"),
            ("Daily Nation", "https://nation.africa/kenya/rss", "global_politics.geopolitics"),
            ("Foreign Policy", "https://foreignpolicy.com/feed/", "global_politics.geopolitics"),
            ("Reuters World", "https://feeds.reuters.com/Reuters/worldNews", "global_politics.geopolitics"),
            ("NPR News", "https://feeds.npr.org/1001/rss.xml", "global_politics.elections"),
            ("Politico", "https://rss.politico.com/politics-news.xml", "global_politics.elections"),
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
        "sources": [
            ("The Art Newspaper", "https://www.theartnewspaper.com/rss.xml", "lifestyle_culture.arts"),
            ("Hyperallergic", "https://hyperallergic.com/feed/", "lifestyle_culture.arts"),
            ("Wired Culture", "https://www.wired.com/feed/category/culture/latest/rss", "lifestyle_culture.arts"),
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
        "sources": [
            ("ESPN Top News", "https://www.espn.com/espn/rss/news", "sports_entertainment.us_sports"),
            ("Autosport F1", "https://www.autosport.com/rss/f1/news/", "sports_entertainment.motorsports.f1"),
            ("BBC Sport", "https://feeds.bbci.co.uk/sport/rss.xml", "sports_entertainment.football"),
            ("Reuters Sport", "https://feeds.reuters.com/reuters/sportsNews", "sports_entertainment.us_sports"),
            ("Sky Sports", "https://www.skysports.com/rss/12040", "sports_entertainment.football"),
            ("BBC Premier League", "https://feeds.bbci.co.uk/sport/football/premier-league/rss.xml", "sports_entertainment.football.europe"),
            ("Guardian Premier League", "https://www.theguardian.com/football/premierleague/rss", "sports_entertainment.football.europe"),
            ("Guardian La Liga", "https://www.theguardian.com/football/laligafootball/rss", "sports_entertainment.football.europe"),
            ("Guardian Bundesliga", "https://www.theguardian.com/football/bundesligafootball/rss", "sports_entertainment.football.europe"),
            ("Guardian Serie A", "https://www.theguardian.com/football/serieafootball/rss", "sports_entertainment.football.europe"),
            ("Guardian Ligue 1", "https://www.theguardian.com/football/ligue1football/rss", "sports_entertainment.football.europe"),
            ("BBC Football", "https://feeds.bbci.co.uk/sport/football/rss.xml", "sports_entertainment.football"),
            ("ESPN Soccer", "https://www.espn.com/espn/rss/soccer/news", "sports_entertainment.football"),
            ("Guardian Football", "https://www.theguardian.com/football/rss", "sports_entertainment.football"),
            ("ESPN NBA", "https://www.espn.com/espn/rss/nba/news", "sports_entertainment.us_sports.nba"),
            ("BBC Basketball", "https://feeds.bbci.co.uk/sport/basketball/rss.xml", "sports_entertainment.us_sports.nba"),
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
        "sources": [
            ("Phys.org", "https://phys.org/rss-feed/", "science_environment.space"),
            ("Ars Technica Science", "https://feeds.arstechnica.com/arstechnica/science", "science_environment.space"),
            ("Ars Technica", "https://feeds.arstechnica.com/arstechnica/index", "science_environment.space"),
            ("USGS Quakes", "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_week.atom", "science_environment.disasters.quakes"),
            ("ReliefWeb", "https://reliefweb.int/updates/rss.xml", "science_environment.disasters.aid"),
            ("NPR News Podcast", "https://feeds.npr.org/500005/podcast.xml", "science_environment.podcasts.news"),
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
        "sources": [],
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


def seed_sources() -> list[tuple[str, str, str, int, None, str]]:
    rows: list[tuple[str, str, str, int, None, str]] = []
    for module in CATALOG:
        for name, url, topic_id in module["sources"]:
            rows.append((module["id"], name, url, 1, None, topic_id))
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
