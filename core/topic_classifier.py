"""Split module headlines into leaf topics so sidebar counts add up."""

from __future__ import annotations

from database.taxonomy import default_leaf_id, module_leaf_ids, topic_leaf_ids

_EXTRA: dict[str, tuple[str, ...]] = {
    "economy_markets.macro.central_banks": (
        "central bank", "federal reserve", "the fed", "fed ", "ecb", "boj", "bank of england",
        "tcmb", "powell", "lagarde", "merkez bank", "rate decision", "interest-rate decision",
    ),
    "economy_markets.macro.inflation": (
        "inflation", "cpi", "ppi", "consumer price", "enflasyon", "cost of living",
    ),
    "economy_markets.macro.rates": (
        "interest rate", "rate hike", "rate cut", "yield", "treasury yield", "faiz", "bond yield",
    ),
    "economy_markets.macro.debt": (
        "debt", "deficit", "treasury", "sovereign", "borrow", "bond sale", "borç",
    ),
    "economy_markets.stocks.wall_street": (
        "wall street", "dow", "nasdaq", "s&p", "nyse", "us stock", "u.s. stock", "wallstreet",
    ),
    "economy_markets.stocks.bist": (
        "bist", "borsa istanbul", "istanbul", "turkiye", "türkiye", "turkish stock", "xu100",
    ),
    "economy_markets.stocks.europe": (
        "europe stock", "european stock", "ftse", "dax", "cac 40", "stoxx", "london stock",
        "frankfurt", "euronext",
    ),
    "economy_markets.stocks.asia": (
        "asia stock", "nikkei", "hang seng", "shanghai", "kospi", "tokyo stock", "hong kong stock",
    ),
    "economy_markets.commodities.oil": (
        "oil", "brent", "wti", "crude", "opec", "petrol", "gasoline",
    ),
    "economy_markets.commodities.metals": (
        "gold", "silver", "copper", "metal", "platinum", "altın",
    ),
    "economy_markets.commodities.fx": (
        "forex", "fx ", "dollar", "euro", "yen", "sterling", "currency", "dolar", "kur",
    ),
    "economy_markets.corporate.earnings": (
        "earnings", "profit", "revenue", "quarterly", "results", "bilanço", "kazanç",
    ),
    "economy_markets.corporate.ma": (
        "merger", "acquisition", "takeover", "buyout", "m&a", "satın al",
    ),
    "economy_markets.corporate.ipo": (
        "ipo", "public offering", "debut", "spac", "halka arz",
    ),
    "crypto_web3.assets.btc": ("bitcoin", "btc", "satoshi"),
    "crypto_web3.assets.eth": ("ethereum", "ether", "eth "),
    "crypto_web3.assets.altcoins": ("altcoin", "solana", "xrp", "dogecoin", "cardano", "avalanche"),
    "crypto_web3.defi.dex": ("dex", "uniswap", "decentralized exchange"),
    "crypto_web3.defi.lending": ("aave", "lending", "borrow", "compound"),
    "crypto_web3.defi.yield": ("yield", "staking", "liquidity mining"),
    "crypto_web3.regulation.sec": ("sec", "securities and exchange", "gensler"),
    "crypto_web3.regulation.etf": ("etf", "spot bitcoin", "spot ether"),
    "crypto_web3.regulation.cbdc": ("cbdc", "digital euro", "digital dollar", "digital yuan"),
    "crypto_web3.security.exchanges": ("binance", "coinbase", "kraken", "exchange"),
    "crypto_web3.security.hacks": ("hack", "exploit", "stolen", "breach", "rug pull"),
    "crypto_web3.security.nfts": ("nft", "opensea", "collectible"),
    "tech_mobility.ev.makers": ("tesla", "rivian", "byd", "gm ev", "ford ev", "volkswagen ev"),
    "tech_mobility.ev.battery": ("battery", "lithium", "gigafactory", "solid-state"),
    "tech_mobility.ev.autonomous": ("autonomous", "self-driving", "robotaxi", "fsd", "waymo"),
    "tech_mobility.ai.llm": ("chatgpt", "openai", "llm", "gpt", "claude", "gemini", "anthropic"),
    "tech_mobility.ai.chips": ("nvidia", "semiconductor", "chip", "tsmc", "amd", "intel"),
    "tech_mobility.ai.robotics": ("robot", "humanoid", "boston dynamics"),
    "tech_mobility.consumer.phones": ("iphone", "android phone", "smartphone", "pixel", "galaxy"),
    "tech_mobility.consumer.os": ("ios", "android", "windows", "macos", "operating system"),
    "tech_mobility.consumer.bigtech": ("apple", "google", "microsoft", "amazon", "meta", "big tech"),
    "tech_mobility.cyber.breaches": ("breach", "ransomware", "cyberattack", "hack", "leak"),
    "tech_mobility.cyber.cloud": ("aws", "azure", "google cloud", "cloud"),
    "tech_mobility.cyber.saas": ("saas", "software as a service", "subscription software"),
    "global_politics.geopolitics.us": ("washington", "white house", "u.s.", "united states", "america"),
    "global_politics.geopolitics.eu": ("european union", "brussels", "eu ", "europe"),
    "global_politics.geopolitics.mena": (
        "middle east", "gaza", "israel", "iran", "saudi", "syria", "lebanon", "yemen",
    ),
    "global_politics.geopolitics.indo_pacific": (
        "china", "taiwan", "south china", "indo-pacific", "india", "japan", "korea",
    ),
    "global_politics.elections.national": ("election", "vote", "ballot", "poll", "seçim"),
    "global_politics.elections.bills": ("bill", "congress", "senate", "legislation", "lawmakers"),
    "global_politics.elections.trade": ("tariff", "trade war", "wto", "sanctions"),
    "global_politics.defense.industry": ("lockheed", "raytheon", "defense contractor", "arms"),
    "global_politics.defense.conflicts": ("war", "conflict", "invasion", "missile", "troops"),
    "global_politics.defense.aerospace": ("nato", "air force", "fighter", "f-35", "drone"),
    "lifestyle_culture.arts.contemporary": ("contemporary art", "artist", "exhibition"),
    "lifestyle_culture.arts.market": ("auction", "sotheby's", "christie's", "art market"),
    "lifestyle_culture.arts.museums": ("museum", "gallery", "curator"),
    "lifestyle_culture.arts.digital": ("nft art", "digital art", "ai art"),
    "lifestyle_culture.arts.performing": ("opera", "ballet", "theatre", "theater", "concert"),
    "lifestyle_culture.health.longevity": ("longevity", "aging", "lifespan"),
    "lifestyle_culture.health.mental": ("mental health", "anxiety", "depression"),
    "lifestyle_culture.health.fitness": ("fitness", "workout", "exercise"),
    "lifestyle_culture.design.architecture": ("architecture", "architect", "building"),
    "lifestyle_culture.design.travel": ("travel", "tourism", "hotel"),
    "lifestyle_culture.design.gastronomy": ("restaurant", "chef", "food", "cuisine"),
    "lifestyle_culture.work.remote": ("remote work", "work from home", "hybrid work"),
    "lifestyle_culture.work.career": ("career", "hiring", "job", "layoff"),
    "lifestyle_culture.work.fire": ("fire movement", "financial independence", "retire early"),
    "sports_entertainment.football.europe": (
        "premier league", "la liga", "bundesliga", "serie a", "ligue 1", "champions league",
        "uefa", "manchester", "real madrid", "barcelona", "bayern", "liverpool",
    ),
    "sports_entertainment.football.transfers": ("transfer", "signing", "contract", "loan deal"),
    "sports_entertainment.football.super_lig": (
        "süper lig", "super lig", "galatasaray", "fenerbahçe", "besiktas", "beşiktaş", "trabzonspor",
    ),
    "sports_entertainment.motorsports.f1": ("formula 1", "f1", "grand prix", "verstappen", "hamilton"),
    "sports_entertainment.motorsports.motogp": ("motogp", "moto gp"),
    "sports_entertainment.motorsports.wec": ("wec", "le mans", "endurance"),
    "sports_entertainment.us_sports.nba": ("nba", "lakers", "celtics", "basketball"),
    "sports_entertainment.us_sports.nfl": ("nfl", "super bowl", "quarterback"),
    "sports_entertainment.entertainment.gaming": ("game", "playstation", "xbox", "nintendo", "esports"),
    "sports_entertainment.entertainment.cinema": ("film", "movie", "hollywood", "oscar", "box office"),
    "science_environment.space.missions": ("nasa", "spacex", "launch", "mission", "rocket"),
    "science_environment.space.astronomy": ("telescope", "galaxy", "black hole", "jwst", "asteroid"),
    "science_environment.space.commercial": ("starlink", "blue origin", "commercial space"),
    "science_environment.climate.renewables": ("solar", "wind", "renewable", "clean energy"),
    "science_environment.climate.nuclear": ("nuclear", "reactor", "fusion"),
    "science_environment.climate.carbon": ("carbon", "emissions", "net zero", "climate"),
}


def assign_leaf_topic(module_id: str | None, source_topic_id: str | None, title: str, content: str | None) -> str | None:
    module_id = (module_id or "").strip() or None
    source_topic_id = (source_topic_id or "").strip() or None
    leaves = module_leaf_ids(module_id) if module_id else []
    if not leaves:
        return default_leaf_id(module_id, source_topic_id)
    preferred = set(topic_leaf_ids(source_topic_id)) if source_topic_id else set(leaves)
    haystack = f"{title or ''}\n{(content or '')[:1200]}".casefold()
    best_id = None
    best_score = -1
    for leaf in leaves:
        score = _score(leaf, haystack)
        if leaf in preferred:
            score += 2
        if score > best_score:
            best_score = score
            best_id = leaf
    if best_score <= 2:
        fallback = default_leaf_id(module_id, source_topic_id)
        if fallback:
            return fallback
    return best_id


def _score(topic_id: str, haystack: str) -> int:
    score = 0
    token = topic_id.split(".")[-1].replace("_", " ")
    if token and token in haystack:
        score += 3
    for keyword in _EXTRA.get(topic_id, ()):
        needle = keyword.casefold().strip()
        if needle and needle in haystack:
            score += 4 if " " in needle or len(needle) > 4 else 2
    return score
