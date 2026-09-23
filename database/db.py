"""SQLite initialization, seed data, and thread-safe helpers."""

from __future__ import annotations

import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Optional
from urllib.parse import urlparse

from config import (
    DATA_DIR,
    DB_PATH,
    DEFAULT_AI_PROVIDER,
    DEFAULT_ARTICLE_DATE_SORT,
    DEFAULT_FEED_REFRESH_MINUTES,
    DEFAULT_LANGUAGE,
    DEFAULT_MARKET_TICKERS,
    DEFAULT_OLLAMA_MODEL,
    DEFAULT_OLLAMA_URL,
    DEFAULT_THEME,
    ARTICLE_LIST_LIMIT,
    ARTICLE_RETENTION_HOURS,
    CHAT_HISTORY_LIMIT,
    parse_article_list_limit,
    parse_retention_hours,
    normalize_article_date_sort,
)
from database.models import Article, Module, Source, Ticker, Topic, UserFilter
from collections import defaultdict

from database.taxonomy import (
    CATALOG,
    LEGACY_MODULE_REMAP,
    LEGACY_TOPIC_REMAP,
    SOURCE_URL_REMAP,
    TAXONOMY_VERSION,
    current_module_ids,
    current_topic_ids,
    legacy_modules_for,
    module_leaf_ids,
    parent_topic_id,
    seed_modules,
    seed_sources,
    seed_topics,
    topic_leaf_ids,
    topic_module_id,
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS modules (
    id TEXT PRIMARY KEY,
    name_key TEXT NOT NULL,
    is_active BOOLEAN DEFAULT 1,
    icon_name TEXT,
    sort_order INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS topics (
    id TEXT PRIMARY KEY,
    module_id TEXT NOT NULL,
    parent_id TEXT,
    name_key TEXT NOT NULL,
    is_active BOOLEAN DEFAULT 1,
    sort_order INTEGER DEFAULT 0,
    FOREIGN KEY(module_id) REFERENCES modules(id) ON DELETE CASCADE,
    FOREIGN KEY(parent_id) REFERENCES topics(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    module_id TEXT NOT NULL,
    name TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    is_rss BOOLEAN DEFAULT 1,
    css_selector TEXT,
    is_active BOOLEAN DEFAULT 1,
    user_added BOOLEAN DEFAULT 0,
    topic_id TEXT,
    FOREIGN KEY(module_id) REFERENCES modules(id) ON DELETE CASCADE,
    FOREIGN KEY(topic_id) REFERENCES topics(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER,
    title TEXT NOT NULL,
    content TEXT,
    link TEXT UNIQUE,
    pub_date DATETIME,
    category TEXT,
    ai_summary TEXT,
    sentiment TEXT CHECK(sentiment IN ('bullish/positive', 'bearish/negative', 'neutral') OR sentiment IS NULL),
    ai_translation TEXT,
    translation_lang TEXT,
    image_url TEXT,
    image_path TEXT,
    is_read BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(source_id) REFERENCES sources(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS user_filters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword TEXT NOT NULL,
    filter_type TEXT CHECK(filter_type IN ('whitelist', 'blacklist')),
    is_active BOOLEAN DEFAULT 1
);

CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS tickers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL UNIQUE,
    label TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0
);
"""

SEED_MODULES = seed_modules()
SEED_TOPICS = seed_topics()
SEED_SOURCES = seed_sources()

SEED_SETTINGS = {
    "language": DEFAULT_LANGUAGE,
    "theme": DEFAULT_THEME,
    "ai_provider": DEFAULT_AI_PROVIDER,
    "ai_model": "gpt-4o-mini",
    "ollama_url": DEFAULT_OLLAMA_URL,
    "ollama_model": DEFAULT_OLLAMA_MODEL,
    "auto_ai_summary": "0",
    "feed_refresh_minutes": str(DEFAULT_FEED_REFRESH_MINUTES),
    "article_date_sort": DEFAULT_ARTICLE_DATE_SORT,
    "dedupe_headlines": "1",
    "article_retention_hours": str(ARTICLE_RETENTION_HOURS),
    "ticker_alert_pct": "2",
    "ui_font_scale": "100",
    "start_with_windows": "0",
    "minimize_to_tray": "1",
    "notify_alerts": "1",
    "scheduled_briefing_hour": "-1",
    "cluster_headlines": "1",
    "article_list_limit": str(ARTICLE_LIST_LIMIT),
    "first_run_done": "0",
    "two_pane": "0",
    "low_data": "0",
    "hide_tape": "0",
    "compact_tape": "0",
    "compact_list": "0",
    "relative_time": "1",
    "tape_speed": "100",
    "quiet_start": "-1",
    "quiet_end": "-1",
    "alert_beep": "1",
    "proxy_url": "",
    "sync_folder": "",
    "intraday_quotes": "1",
    "active_watchlist": "main",
    "github_repo": "",
    "auto_update_check": "0",
}


class DuplicateSourceError(Exception):
    pass


class InvalidSourceUrlError(Exception):
    pass


def is_http_url(value: str) -> bool:
    parsed = urlparse((value or "").strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


class Database:
    def __init__(self, path: Path = DB_PATH) -> None:
        self.path = path
        self._lock = threading.RLock()
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._init_schema()
        hours = parse_retention_hours(self.get_setting("article_retention_hours"))
        if hours:
            self.purge_expired_articles(hours)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

    def _init_schema(self) -> None:
        with self._lock:
            conn = self.connect()
            try:
                conn.executescript(SCHEMA)
                self._migrate(conn)
                self._seed(conn)
                conn.commit()
            finally:
                conn.close()

    def _migrate(self, conn: sqlite3.Connection) -> None:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(articles)")}
        if "ai_translation" not in columns:
            conn.execute("ALTER TABLE articles ADD COLUMN ai_translation TEXT")
        if "translation_lang" not in columns:
            conn.execute("ALTER TABLE articles ADD COLUMN translation_lang TEXT")
        if "image_url" not in columns:
            conn.execute("ALTER TABLE articles ADD COLUMN image_url TEXT")
        if "image_path" not in columns:
            conn.execute("ALTER TABLE articles ADD COLUMN image_path TEXT")
        if "is_saved" not in columns:
            conn.execute("ALTER TABLE articles ADD COLUMN is_saved BOOLEAN DEFAULT 0")
        if "emoji" not in columns:
            conn.execute("ALTER TABLE articles ADD COLUMN emoji TEXT")
        if "note" not in columns:
            conn.execute("ALTER TABLE articles ADD COLUMN note TEXT")
        if "tags" not in columns:
            conn.execute("ALTER TABLE articles ADD COLUMN tags TEXT")
        if "folder" not in columns:
            conn.execute("ALTER TABLE articles ADD COLUMN folder TEXT")
        if "note" not in columns:
            conn.execute("ALTER TABLE articles ADD COLUMN note TEXT")
        if "tags" not in columns:
            conn.execute("ALTER TABLE articles ADD COLUMN tags TEXT")
        if "folder" not in columns:
            conn.execute("ALTER TABLE articles ADD COLUMN folder TEXT")
        source_columns = {row[1] for row in conn.execute("PRAGMA table_info(sources)")}
        if "user_added" not in source_columns:
            conn.execute("ALTER TABLE sources ADD COLUMN user_added BOOLEAN DEFAULT 0")
        if "topic_id" not in source_columns:
            conn.execute("ALTER TABLE sources ADD COLUMN topic_id TEXT")
        if "last_fetch_at" not in source_columns:
            conn.execute("ALTER TABLE sources ADD COLUMN last_fetch_at TEXT")
        if "last_error" not in source_columns:
            conn.execute("ALTER TABLE sources ADD COLUMN last_error TEXT")
        if "last_ok" not in source_columns:
            conn.execute("ALTER TABLE sources ADD COLUMN last_ok INTEGER DEFAULT 1")
        if "refresh_minutes" not in source_columns:
            conn.execute("ALTER TABLE sources ADD COLUMN refresh_minutes INTEGER DEFAULT 0")
        if "muted_until" not in source_columns:
            conn.execute("ALTER TABLE sources ADD COLUMN muted_until TEXT")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                body TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        module_columns = {row[1] for row in conn.execute("PRAGMA table_info(modules)")}
        if "sort_order" not in module_columns:
            conn.execute("ALTER TABLE modules ADD COLUMN sort_order INTEGER DEFAULT 0")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS topics (
                id TEXT PRIMARY KEY,
                module_id TEXT NOT NULL,
                parent_id TEXT,
                name_key TEXT NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                sort_order INTEGER DEFAULT 0,
                FOREIGN KEY(module_id) REFERENCES modules(id) ON DELETE CASCADE,
                FOREIGN KEY(parent_id) REFERENCES topics(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tickers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL UNIQUE,
                label TEXT NOT NULL,
                sort_order INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        ticker_columns = {row[1] for row in conn.execute("PRAGMA table_info(tickers)")}
        if "alert_pct" not in ticker_columns:
            conn.execute("ALTER TABLE tickers ADD COLUMN alert_pct REAL")
        if "watchlist" not in ticker_columns:
            conn.execute("ALTER TABLE tickers ADD COLUMN watchlist TEXT DEFAULT 'main'")

    def _seed(self, conn: sqlite3.Connection) -> None:
        for module_id, name_key, active, icon, sort_order in SEED_MODULES:
            conn.execute(
                """
                INSERT OR IGNORE INTO modules (id, name_key, is_active, icon_name, sort_order)
                VALUES (?, ?, ?, ?, ?)
                """,
                (module_id, name_key, active, icon, sort_order),
            )
            conn.execute(
                "UPDATE modules SET name_key = ?, icon_name = ?, sort_order = ? WHERE id = ?",
                (name_key, icon, sort_order, module_id),
            )
        for topic_id, module_id, parent_id, name_key, sort_order in SEED_TOPICS:
            conn.execute(
                """
                INSERT OR IGNORE INTO topics (id, module_id, parent_id, name_key, is_active, sort_order)
                VALUES (?, ?, ?, ?, 1, ?)
                """,
                (topic_id, module_id, parent_id, name_key, sort_order),
            )
            conn.execute(
                """
                UPDATE topics SET module_id = ?, parent_id = ?, name_key = ?, sort_order = ?
                WHERE id = ?
                """,
                (module_id, parent_id, name_key, sort_order, topic_id),
            )
        for module_id, name, url, is_rss, selector, topic_id in SEED_SOURCES:
            conn.execute(
                """
                INSERT OR IGNORE INTO sources (module_id, name, url, is_rss, css_selector, is_active, topic_id)
                VALUES (?, ?, ?, ?, ?, 1, ?)
                """,
                (module_id, name, url, is_rss, selector, topic_id),
            )
            conn.execute(
                """
                UPDATE sources SET module_id = ?, topic_id = ?, name = ?
                WHERE url = ? AND IFNULL(user_added, 0) = 0
                """,
                (module_id, topic_id, name, url),
            )
        for key, value in SEED_SETTINGS.items():
            conn.execute(
                "INSERT OR IGNORE INTO app_settings (key, value) VALUES (?, ?)",
                (key, value),
            )
        row = conn.execute(
            "SELECT value FROM app_settings WHERE key = 'article_list_limit'"
        ).fetchone()
        if row and str(row["value"] or "") == "400":
            conn.execute(
                "UPDATE app_settings SET value = ? WHERE key = 'article_list_limit'",
                (str(ARTICLE_LIST_LIMIT),),
            )
        self._migrate_taxonomy(conn)
        self._seed_tickers_if_empty(conn)

    def _migrate_taxonomy(self, conn: sqlite3.Connection) -> None:
        row = conn.execute(
            "SELECT value FROM app_settings WHERE key = 'taxonomy_version'"
        ).fetchone()
        current = row["value"] if row else None
        if current == TAXONOMY_VERSION:
            return
        keep_modules = current_module_ids()
        keep_topics = current_topic_ids()
        legacy_active = {
            row["id"]: bool(row["is_active"])
            for row in conn.execute("SELECT id, is_active FROM modules")
        }
        for module_id, *_rest in SEED_MODULES:
            flags = [legacy_active[lid] for lid in legacy_modules_for(module_id) if lid in legacy_active]
            if flags:
                conn.execute(
                    "UPDATE modules SET is_active = ? WHERE id = ?",
                    (int(flags[0]), module_id),
                )
        for source in conn.execute("SELECT id, url, module_id, topic_id FROM sources"):
            url = source["url"]
            topic_id = source["topic_id"]
            module_id = source["module_id"]
            if url in SOURCE_URL_REMAP:
                module_id, topic_id = SOURCE_URL_REMAP[url]
            elif topic_id in LEGACY_TOPIC_REMAP:
                topic_id = LEGACY_TOPIC_REMAP[topic_id]
                module_id = topic_module_id(topic_id) or LEGACY_MODULE_REMAP.get(module_id, module_id)
            elif module_id in LEGACY_MODULE_REMAP:
                module_id = LEGACY_MODULE_REMAP[module_id]
                if topic_id not in keep_topics:
                    topic_id = None
            if module_id not in keep_modules:
                continue
            conn.execute(
                "UPDATE sources SET module_id = ?, topic_id = ? WHERE id = ?",
                (module_id, topic_id if topic_id in keep_topics else None, source["id"]),
            )
        stale_topics = [
            row["id"]
            for row in conn.execute("SELECT id FROM topics")
            if row["id"] not in keep_topics
        ]
        for topic_id in sorted(stale_topics, key=lambda value: value.count("."), reverse=True):
            conn.execute("DELETE FROM topics WHERE id = ?", (topic_id,))
        for row in conn.execute("SELECT id FROM modules"):
            if row["id"] not in keep_modules:
                conn.execute("DELETE FROM modules WHERE id = ?", (row["id"],))
        conn.execute(
            "INSERT INTO app_settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            ("taxonomy_version", TAXONOMY_VERSION),
        )

    def _seed_tickers_if_empty(self, conn: sqlite3.Connection) -> None:
        count = conn.execute("SELECT COUNT(*) AS n FROM tickers").fetchone()["n"]
        if count:
            return
        for order, (symbol, label) in enumerate(DEFAULT_MARKET_TICKERS):
            conn.execute(
                "INSERT INTO tickers (symbol, label, sort_order) VALUES (?, ?, ?)",
                (symbol, label, order),
            )

    def list_tickers(self, watchlist: str | None = None) -> list[Ticker]:
        items = [
            Ticker(
                id=row["id"],
                symbol=row["symbol"],
                label=row["label"],
                sort_order=int(row["sort_order"] or 0),
                alert_pct=float(row["alert_pct"]) if _row_col(row, "alert_pct") not in (None, "") else None,
                watchlist=str(_row_col(row, "watchlist") or "main"),
            )
            for row in self.query("SELECT * FROM tickers ORDER BY sort_order, id")
        ]
        if watchlist:
            filtered = [item for item in items if (item.watchlist or "main") == watchlist]
            return filtered or items
        return items

    def list_watchlist_names(self) -> list[str]:
        names = sorted({item.watchlist or "main" for item in self.list_tickers()})
        return names or ["main"]

    def add_ticker(self, symbol: str, label: str) -> bool:
        symbol = (symbol or "").strip()
        if not symbol:
            return False
        rows = [(item.symbol, item.label) for item in self.list_tickers()]
        if any(existing.casefold() == symbol.casefold() for existing, _label in rows):
            return False
        rows.append((symbol, (label or "").strip() or symbol))
        self.replace_tickers(rows)
        return True

    def remove_ticker_symbol(self, symbol: str) -> None:
        target = (symbol or "").strip().casefold()
        rows = [
            (item.symbol, item.label)
            for item in self.list_tickers()
            if item.symbol.casefold() != target
        ]
        self.replace_tickers(rows)

    def replace_tickers(self, items: list[tuple[str, str]]) -> None:
        existing = {item.symbol.casefold(): item for item in self.list_tickers()}
        cleaned: list[tuple[str, str]] = []
        seen: set[str] = set()
        for symbol, label in items:
            sym = symbol.strip()
            if not sym:
                continue
            key = sym.casefold()
            if key in seen:
                continue
            seen.add(key)
            cleaned.append((sym, (label or "").strip() or sym))
        with self._lock:
            conn = self.connect()
            try:
                conn.execute("DELETE FROM tickers")
                for order, (symbol, label) in enumerate(cleaned):
                    prior = existing.get(symbol.casefold())
                    conn.execute(
                        """
                        INSERT INTO tickers (symbol, label, sort_order, alert_pct, watchlist)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            symbol,
                            label,
                            order,
                            prior.alert_pct if prior else None,
                            prior.watchlist if prior else "main",
                        ),
                    )
                conn.commit()
            finally:
                conn.close()

    def execute(self, sql: str, params: Iterable[Any] = ()) -> None:
        with self._lock:
            conn = self.connect()
            try:
                conn.execute(sql, tuple(params))
                conn.commit()
            finally:
                conn.close()

    def query(self, sql: str, params: Iterable[Any] = ()) -> list[sqlite3.Row]:
        with self._lock:
            conn = self.connect()
            try:
                cur = conn.execute(sql, tuple(params))
                return cur.fetchall()
            finally:
                conn.close()

    def get_setting(self, key: str, default: str | None = None) -> str | None:
        rows = self.query("SELECT value FROM app_settings WHERE key = ?", (key,))
        if not rows:
            return default
        return rows[0]["value"]

    def article_list_limit(self) -> int:
        return parse_article_list_limit(self.get_setting("article_list_limit"))

    def set_setting(self, key: str, value: str) -> None:
        self.execute(
            "INSERT INTO app_settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )

    def list_modules(self, active_only: bool = False) -> list[Module]:
        sql = "SELECT * FROM modules"
        if active_only:
            sql += " WHERE is_active = 1"
        sql += " ORDER BY IFNULL(sort_order, 0), id"
        return [
            Module(
                id=row["id"],
                name_key=row["name_key"],
                is_active=bool(row["is_active"]),
                icon_name=row["icon_name"] or "",
            )
            for row in self.query(sql)
        ]

    def set_module_active(self, module_id: str, active: bool) -> None:
        self.execute("UPDATE modules SET is_active = ? WHERE id = ?", (int(active), module_id))

    def set_topic_active(self, topic_id: str, active: bool) -> None:
        self.execute("UPDATE topics SET is_active = ? WHERE id = ?", (int(active), topic_id))

    def list_sources(self, active_only: bool = True) -> list[Source]:
        sql = "SELECT * FROM sources"
        if active_only:
            sql += " WHERE is_active = 1"
        sql += " ORDER BY module_id, name COLLATE NOCASE"
        return [_source_from_row(row) for row in self.query(sql)]

    def list_fetchable_sources(self) -> list[Source]:
        active_modules = {item.id for item in self.list_modules(active_only=True)}
        topics = {item.id: item for item in self.list_topics(active_only=False)}
        fetchable: list[Source] = []
        for source in self.list_sources(active_only=True):
            if source.module_id not in active_modules:
                continue
            topic = topics.get(source.topic_id or "")
            skipped = False
            while topic is not None:
                if not topic.is_active:
                    skipped = True
                    break
                topic = topics.get(topic.parent_id) if topic.parent_id else None
            if not skipped:
                from core.app_extras import source_is_muted

                if source_is_muted(source.muted_until):
                    continue
                fetchable.append(source)
        return fetchable

    def get_source(self, source_id: int) -> Source | None:
        rows = self.query("SELECT * FROM sources WHERE id = ?", (source_id,))
        if not rows:
            return None
        return _source_from_row(rows[0])

    def find_source_by_url(self, url: str) -> Source | None:
        target = (url or "").strip().rstrip("/").lower()
        if not target:
            return None
        for source in self.list_sources(active_only=False):
            if source.url.strip().rstrip("/").lower() == target:
                return source
        return None

    def list_topics(self, module_id: str | None = None, active_only: bool = False) -> list[Topic]:
        tables = self.query("SELECT name FROM sqlite_master WHERE type='table' AND name='topics'")
        if not tables:
            return []
        sql = "SELECT * FROM topics"
        clauses: list[str] = []
        params: list[Any] = []
        if module_id:
            clauses.append("module_id = ?")
            params.append(module_id)
        if active_only:
            clauses.append("is_active = 1")
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY sort_order, name_key"
        topics: list[Topic] = []
        for row in self.query(sql, params):
            topics.append(
                Topic(
                    id=row["id"],
                    module_id=row["module_id"],
                    parent_id=_row_col(row, "parent_id"),
                    name_key=row["name_key"],
                    is_active=bool(row["is_active"]),
                    sort_order=int(_row_col(row, "sort_order", 0) or 0),
                )
            )
        return topics

    def topic_subtree_ids(self, topic_id: str) -> list[str]:
        children: dict[str | None, list[str]] = {}
        for topic in self.list_topics(active_only=False):
            children.setdefault(topic.parent_id, []).append(topic.id)
        collected: list[str] = []
        stack = [topic_id]
        while stack:
            current = stack.pop()
            collected.append(current)
            stack.extend(children.get(current, []))
        return collected

    def add_user_source(
        self,
        *,
        name: str,
        url: str,
        module_id: str,
        is_rss: bool = True,
        css_selector: str | None = None,
        topic_id: str | None = None,
    ) -> int:
        name = name.strip()
        url = url.strip()
        if not name:
            raise ValueError("name")
        if not is_http_url(url):
            raise InvalidSourceUrlError(url)
        columns = {row["name"] for row in self.query("PRAGMA table_info(sources)")}
        fields = ["module_id", "name", "url", "is_rss", "css_selector", "is_active", "user_added"]
        values: list[Any] = [module_id, name, url, int(is_rss), css_selector or None, 1, 1]
        if "topic_id" in columns:
            fields.append("topic_id")
            values.append(topic_id)
        placeholders = ", ".join("?" for _ in fields)
        sql = f"INSERT INTO sources ({', '.join(fields)}) VALUES ({placeholders})"
        with self._lock:
            conn = self.connect()
            try:
                cur = conn.execute(sql, tuple(values))
                conn.commit()
                return int(cur.lastrowid)
            except sqlite3.IntegrityError as exc:
                raise DuplicateSourceError(url) from exc
            finally:
                conn.close()

    def set_source_health(self, source_id: int, *, ok: bool, error: str = "") -> None:
        from core.app_extras import utc_now_iso

        self.execute(
            """
            UPDATE sources SET last_ok = ?, last_error = ?, last_fetch_at = ?
            WHERE id = ?
            """,
            (int(ok), (error or "")[:400] if not ok else None, utc_now_iso(), source_id),
        )

    def mark_all_read(self, article_ids: list[int]) -> None:
        if not article_ids:
            return
        placeholders = ",".join("?" for _ in article_ids)
        self.execute(f"UPDATE articles SET is_read = 1 WHERE id IN ({placeholders})", article_ids)

    def list_chat_messages(self) -> list[dict[str, str]]:
        rows = self.query(
            "SELECT role, body FROM chat_messages ORDER BY id DESC LIMIT ?",
            (CHAT_HISTORY_LIMIT,),
        )
        return [{"role": row["role"], "text": row["body"]} for row in reversed(rows)]

    def append_chat_message(self, role: str, body: str) -> None:
        self.execute("INSERT INTO chat_messages (role, body) VALUES (?, ?)", (role, body))
        rows = self.query("SELECT id FROM chat_messages ORDER BY id DESC")
        stale = [row["id"] for row in rows[CHAT_HISTORY_LIMIT:]]
        for message_id in stale:
            self.execute("DELETE FROM chat_messages WHERE id = ?", (message_id,))

    def clear_chat_messages(self) -> None:
        self.execute("DELETE FROM chat_messages")

    def update_article_content(self, article_id: int, content: str) -> None:
        self.execute("UPDATE articles SET content = ? WHERE id = ?", (content, article_id))

    def retention_hours(self) -> int:
        return parse_retention_hours(self.get_setting("article_retention_hours"))

    def set_source_active(self, source_id: int, active: bool) -> None:
        self.execute("UPDATE sources SET is_active = ? WHERE id = ?", (int(active), source_id))

    def delete_user_source(self, source_id: int) -> bool:
        rows = self.query("SELECT user_added FROM sources WHERE id = ?", (source_id,))
        if not rows or not bool(rows[0]["user_added"]):
            return False
        self.execute("DELETE FROM sources WHERE id = ? AND user_added = 1", (source_id,))
        return True

    def upsert_article(
        self,
        *,
        source_id: int,
        title: str,
        content: str | None,
        link: str | None,
        pub_date: datetime | None,
        category: str | None,
        image_url: str | None = None,
    ) -> None:
        self.execute(
            """
            INSERT INTO articles (source_id, title, content, link, pub_date, category, image_url)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(link) DO UPDATE SET
                title = excluded.title,
                content = COALESCE(excluded.content, articles.content),
                pub_date = COALESCE(excluded.pub_date, articles.pub_date),
                image_url = COALESCE(excluded.image_url, articles.image_url)
            """,
            (
                source_id,
                title,
                content,
                link,
                pub_date.isoformat() if pub_date else None,
                category,
                image_url,
            ),
        )

    def save_article_image(
        self,
        article_id: int,
        *,
        image_url: str | None = None,
        image_path: str | None = None,
    ) -> None:
        self.execute(
            """
            UPDATE articles SET
                image_url = COALESCE(?, image_url),
                image_path = COALESCE(?, image_path)
            WHERE id = ?
            """,
            (image_url, image_path, article_id),
        )

    def list_filters(self, active_only: bool = True) -> list[UserFilter]:
        sql = "SELECT * FROM user_filters"
        if active_only:
            sql += " WHERE is_active = 1"
        sql += " ORDER BY filter_type, keyword COLLATE NOCASE"
        return [
            UserFilter(
                id=row["id"],
                keyword=row["keyword"],
                filter_type=row["filter_type"],
                is_active=bool(row["is_active"]),
            )
            for row in self.query(sql)
        ]

    def add_filter(self, keyword: str, filter_type: str) -> bool:
        text = keyword.strip()
        if not text or filter_type not in {"whitelist", "blacklist"}:
            return False
        existing = self.query(
            "SELECT id FROM user_filters WHERE lower(keyword) = lower(?) AND filter_type = ?",
            (text, filter_type),
        )
        if existing:
            return False
        self.execute(
            "INSERT INTO user_filters (keyword, filter_type, is_active) VALUES (?, ?, 1)",
            (text, filter_type),
        )
        return True

    def delete_filter(self, filter_id: int) -> None:
        self.execute("DELETE FROM user_filters WHERE id = ?", (filter_id,))

    def list_articles(
        self,
        module_id: str | None,
        search: str = "",
        topic_ids: list[str] | None = None,
        date_order: str | None = None,
        source_ids: list[int] | None = None,
        saved_only: bool = False,
        unread_only: bool = False,
        max_age_hours: int | None = ARTICLE_RETENTION_HOURS,
        limit: int | None = None,
        classify: bool | None = None,
        folder: str | None = None,
    ) -> list[Article]:
        filters = self.list_filters()
        where_sql, params = self._article_scope_sql(
            module_id, search, topic_ids=topic_ids, source_ids=source_ids, saved_only=saved_only
        )
        direction = "ASC" if normalize_article_date_sort(date_order) == "oldest" else "DESC"
        sql = f"""
            SELECT a.*, s.name AS source_name, s.module_id AS module_id, s.topic_id AS source_topic_id
            FROM articles a
            LEFT JOIN sources s ON s.id = a.source_id
            LEFT JOIN modules m ON m.id = s.module_id
            {where_sql}
            ORDER BY COALESCE(a.pub_date, a.created_at) {direction}, a.id {direction}
        """
        articles = [_row_to_article(row) for row in self.query(sql, params)]
        need_classify = (
            True
            if classify is True
            else False
            if classify is False
            else topic_ids is not None
            or self._module_needs_topic_filter(module_id)
            or len(self._leaf_ids_for_scope(module_id, topic_ids)) > 1
        )
        kept: list[Article] = []
        for article in articles:
            if _apply_keyword_filters(article, filters) is None:
                continue
            if need_classify:
                _classify_article(article)
            kept.append(article)
        kept = self._filter_articles_by_topic(kept, module_id, topic_ids)
        if saved_only:
            kept = [article for article in kept if article.is_saved]
        if unread_only:
            kept = [article for article in kept if not article.is_read]
        if folder:
            kept = [article for article in kept if (article.folder or "") == folder]
        if self.get_setting("cluster_headlines", "1") == "1":
            from core.app_extras import cluster_articles

            kept = cluster_articles(kept, enabled=True)
        if max_age_hours:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=max(1, max_age_hours))
            kept = [article for article in kept if _is_within_story_window(article, cutoff)]
        if limit is None:
            limit = self.article_list_limit()
        if limit <= 0:
            return kept
        return self._apply_branch_article_limit(kept, module_id, topic_ids, limit, date_order)

    def _module_needs_topic_filter(self, module_id: str | None) -> bool:
        if not module_id:
            return False
        return any(not topic.is_active for topic in self.list_topics(module_id, active_only=False))

    def list_feed_sources(
        self,
        module_id: str | None,
        topic_ids: list[str] | None = None,
        saved_only: bool = False,
        max_age_hours: int | None = ARTICLE_RETENTION_HOURS,
    ) -> list[tuple[int, str]]:
        seen: set[int] = set()
        rows: list[tuple[int, str]] = []
        for article in self.list_articles(
            module_id,
            "",
            topic_ids=topic_ids,
            saved_only=saved_only,
            max_age_hours=None if saved_only else max_age_hours,
        ):
            if article.source_id is None or article.source_id in seen:
                continue
            seen.add(article.source_id)
            rows.append((article.source_id, (article.source_name or "").strip() or f"#{article.source_id}"))
        rows.sort(key=lambda item: item[1].casefold())
        return rows

    def headline_counts(self, max_age_hours: int | None = ARTICLE_RETENTION_HOURS) -> dict[str, int]:
        counts: dict[str, int] = defaultdict(int)
        cap = self.article_list_limit()
        cutoff = None
        if max_age_hours:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=max(1, max_age_hours))
            cutoff_text = cutoff.isoformat()
        else:
            cutoff_text = None
        where_live = "WHERE (m.is_active = 1 OR m.id IS NULL)"
        params: list[Any] = []
        if cutoff_text:
            where_live += " AND COALESCE(a.pub_date, a.created_at) >= ?"
            params.append(cutoff_text)
        rows = self.query(
            f"""
            SELECT s.module_id AS module_id, s.topic_id AS topic_id, COUNT(*) AS n
            FROM articles a
            LEFT JOIN sources s ON s.id = a.source_id
            LEFT JOIN modules m ON m.id = s.module_id
            {where_live}
            GROUP BY s.module_id, s.topic_id
            """,
            params,
        )
        live_total = 0
        for row in rows:
            module_id = row["module_id"]
            topic_id = row["topic_id"]
            total = int(row["n"] or 0)
            live_total += total
            if module_id:
                counts[module_id] += total
            if topic_id:
                counts[topic_id] += total
                parent = parent_topic_id(topic_id)
                if parent:
                    counts[parent] += total
        counts["all"] = live_total
        saved_rows = self.query(
            """
            SELECT s.module_id AS module_id, s.topic_id AS topic_id, COUNT(*) AS n
            FROM articles a
            LEFT JOIN sources s ON s.id = a.source_id
            WHERE IFNULL(a.is_saved, 0) = 1
            GROUP BY s.module_id, s.topic_id
            """
        )
        archive_total = 0
        for row in saved_rows:
            total = int(row["n"] or 0)
            archive_total += total
            module_id = row["module_id"]
            topic_id = row["topic_id"]
            if module_id:
                counts[f"archive:{module_id}"] += total
            if topic_id:
                counts[f"archive:{topic_id}"] += total
                parent = parent_topic_id(topic_id)
                if parent:
                    counts[f"archive:{parent}"] += total
        counts["archive"] = archive_total
        return self._cap_headline_counts(dict(counts), cap)

    def _leaf_ids_for_scope(self, module_id: str | None, topic_ids: list[str] | None) -> list[str]:
        found: list[str] = []
        seen: set[str] = set()

        def add_leaf(topic_id: str) -> None:
            for leaf in topic_leaf_ids(topic_id):
                if leaf not in seen:
                    seen.add(leaf)
                    found.append(leaf)

        if topic_ids:
            for topic_id in topic_ids:
                add_leaf(topic_id)
            return found
        if module_id:
            return list(module_leaf_ids(module_id))
        for module in CATALOG:
            for leaf in module_leaf_ids(str(module["id"])):
                if leaf not in seen:
                    seen.add(leaf)
                    found.append(leaf)
        return found

    def _article_leaf_key(self, article: Article, leaf_set: set[str]) -> str:
        assigned = (article.assigned_topic_id or article.source_topic_id or "").strip()
        if assigned in leaf_set:
            return assigned
        if assigned:
            leaves = topic_leaf_ids(assigned)
            for leaf in leaves:
                if leaf in leaf_set:
                    return leaf
        return f"_other:{(article.module_id or 'none')}"

    def _apply_branch_article_limit(
        self,
        articles: list[Article],
        module_id: str | None,
        topic_ids: list[str] | None,
        cap: int,
        date_order: str | None,
    ) -> list[Article]:
        if cap <= 0:
            return articles
        leaves = self._leaf_ids_for_scope(module_id, topic_ids)
        if len(leaves) <= 1:
            return articles[:cap]
        leaf_set = set(leaves)
        buckets: dict[str, list[Article]] = defaultdict(list)
        for article in articles:
            key = self._article_leaf_key(article, leaf_set)
            if len(buckets[key]) < cap:
                buckets[key].append(article)
        merged: list[Article] = []
        for bucket in buckets.values():
            merged.extend(bucket)
        newest_first = normalize_article_date_sort(date_order) != "oldest"

        def sort_key(article: Article) -> tuple:
            instant = _article_instant(article) or datetime.min.replace(tzinfo=timezone.utc)
            return (instant, int(article.id or 0))

        merged.sort(key=sort_key, reverse=newest_first)
        return merged

    def _cap_headline_counts(self, counts: dict[str, int], cap: int) -> dict[str, int]:
        leaf_ids = {leaf for module in CATALOG for leaf in module_leaf_ids(str(module["id"]))}
        capped = dict(counts)
        for leaf in leaf_ids:
            if leaf in capped:
                capped[leaf] = _visible_count(capped[leaf], cap)
            archive_key = f"archive:{leaf}"
            if archive_key in capped:
                capped[archive_key] = _visible_count(capped[archive_key], cap)
        all_live = 0
        all_archive = 0
        for module in CATALOG:
            module_id = str(module["id"])
            leaves = module_leaf_ids(module_id)
            leaf_total = sum(capped.get(leaf, 0) for leaf in leaves)
            leftover = max(0, int(counts.get(module_id, 0)) - sum(int(counts.get(leaf, 0)) for leaf in leaves))
            capped[module_id] = leaf_total + _visible_count(leftover, cap)
            all_live += capped[module_id]
            archive_leaves = sum(capped.get(f"archive:{leaf}", 0) for leaf in leaves)
            archive_leftover = max(
                0,
                int(counts.get(f"archive:{module_id}", 0)) - sum(int(counts.get(f"archive:{leaf}", 0)) for leaf in leaves),
            )
            capped[f"archive:{module_id}"] = archive_leaves + _visible_count(archive_leftover, cap)
            all_archive += capped[f"archive:{module_id}"]
            for category in module.get("subcategories") or []:
                category_id = str(category["id"])
                child_leaves = [leaf for leaf, _name in category.get("topics") or []]
                capped[category_id] = sum(capped.get(leaf, 0) for leaf in child_leaves)
                capped[f"archive:{category_id}"] = sum(capped.get(f"archive:{leaf}", 0) for leaf in child_leaves)
        capped["all"] = all_live
        capped["archive"] = all_archive
        return capped

    def _filter_articles_by_topic(
        self,
        articles: list[Article],
        module_id: str | None,
        topic_ids: list[str] | None,
    ) -> list[Article]:
        if topic_ids is not None:
            allowed = set(topic_ids)
            if not allowed:
                return []
            return [article for article in articles if article.assigned_topic_id in allowed]
        if not module_id:
            return articles
        inactive: set[str] = set()
        for topic in self.list_topics(module_id, active_only=False):
            if topic.is_active:
                continue
            inactive.update(self.topic_subtree_ids(topic.id))
        if not inactive:
            return articles
        return [article for article in articles if article.assigned_topic_id not in inactive]

    def _article_scope_sql(
        self,
        module_id: str | None,
        search: str = "",
        topic_ids: list[str] | None = None,
        source_ids: list[int] | None = None,
        saved_only: bool = False,
    ) -> tuple[str, list[Any]]:
        params: list[Any] = []
        sql = "WHERE (m.is_active = 1 OR m.id IS NULL)"
        if module_id:
            sql += " AND s.module_id = ?"
            params.append(module_id)
        if saved_only:
            sql += " AND IFNULL(a.is_saved, 0) = 1"
        if source_ids:
            placeholders = ",".join("?" for _ in source_ids)
            sql += f" AND a.source_id IN ({placeholders})"
            params.extend(int(item) for item in source_ids)
        if search.strip():
            from core.app_extras import search_tokens

            tokens = search_tokens(search) or [search.strip()]
            for token in tokens:
                sql += " AND (a.title LIKE ? OR IFNULL(a.content, '') LIKE ?)"
                like = f"%{token}%"
                params.extend([like, like])
        return sql, params

    def list_articles_matching(
        self,
        terms: list[str],
        limit: int = 80,
        date_order: str | None = None,
    ) -> list[Article]:
        needles = []
        seen: set[str] = set()
        for term in terms:
            key = term.strip().lower()
            if len(key) < 3 and key not in {"dax", "btc", "eth", "oil", "dow"}:
                continue
            if key in seen:
                continue
            seen.add(key)
            needles.append(key)
        if not needles:
            return []
        scored: list[tuple[int, Article]] = []
        for article in self.list_articles(None, "", date_order=date_order):
            text = f"{article.title} {article.content or ''}".lower()
            hits = sum(1 for needle in needles if needle in text)
            if hits:
                scored.append((hits, article))
        newest_first = normalize_article_date_sort(date_order) == "newest"

        def sort_key(item: tuple[int, Article]) -> tuple:
            instant = _article_instant(item[1]) or datetime.min.replace(tzinfo=timezone.utc)
            return (instant, item[0])

        scored.sort(key=sort_key, reverse=newest_first)
        return [article for _, article in scored[:limit]]

    def list_articles_since(
        self,
        module_id: str | None,
        hours: int,
        limit: int = 30,
        topic_ids: list[str] | None = None,
        saved_only: bool = False,
    ) -> list[Article]:
        recent: list[Article] = []
        for article in self.list_articles(
            module_id,
            "",
            topic_ids=topic_ids,
            date_order="newest",
            saved_only=saved_only,
            max_age_hours=None if saved_only else max(1, hours),
        ):
            recent.append(article)
            if len(recent) >= limit:
                break
        return recent

    def get_articles_by_ids(self, article_ids: list[int]) -> list[Article]:
        found: list[Article] = []
        for article_id in article_ids:
            article = self.get_article(article_id)
            if article:
                found.append(article)
        return found

    def get_article(self, article_id: int) -> Article | None:
        rows = self.query(
            """
            SELECT a.*, s.name AS source_name, s.module_id AS module_id, s.topic_id AS source_topic_id
            FROM articles a
            LEFT JOIN sources s ON s.id = a.source_id
            WHERE a.id = ?
            """,
            (article_id,),
        )
        if not rows:
            return None
        return _row_to_article(rows[0])

    def mark_unread(self, article_id: int) -> None:
        self.execute("UPDATE articles SET is_read = 0 WHERE id = ?", (article_id,))

    def set_article_note(self, article_id: int, note: str) -> None:
        self.execute("UPDATE articles SET note = ? WHERE id = ?", (note, article_id))

    def set_article_tags(self, article_id: int, tags: str) -> None:
        self.execute("UPDATE articles SET tags = ? WHERE id = ?", (tags, article_id))

    def set_article_folder(self, article_id: int, folder: str) -> None:
        self.execute("UPDATE articles SET folder = ? WHERE id = ?", (folder or None, article_id))

    def mute_source(self, source_id: int, hours: int = 24) -> None:
        until = datetime.now(timezone.utc) + timedelta(hours=max(1, hours))
        self.execute("UPDATE sources SET muted_until = ? WHERE id = ?", (until.isoformat(), source_id))

    def set_source_refresh_minutes(self, source_id: int, minutes: int) -> None:
        self.execute("UPDATE sources SET refresh_minutes = ? WHERE id = ?", (max(0, int(minutes)), source_id))

    def list_article_folders(self) -> list[str]:
        rows = self.query(
            "SELECT DISTINCT folder FROM articles WHERE folder IS NOT NULL AND folder != '' ORDER BY folder"
        )
        return [str(row["folder"]) for row in rows]

    def set_ticker_meta(self, symbol: str, *, alert_pct: float | None = None, watchlist: str | None = None) -> None:
        if alert_pct is not None:
            self.execute("UPDATE tickers SET alert_pct = ? WHERE symbol = ?", (alert_pct, symbol))
        if watchlist:
            self.execute("UPDATE tickers SET watchlist = ? WHERE symbol = ?", (watchlist, symbol))

    def mark_read(self, article_id: int) -> None:
        self.execute("UPDATE articles SET is_read = 1 WHERE id = ?", (article_id,))

    def set_article_saved(self, article_id: int, saved: bool) -> None:
        self.execute("UPDATE articles SET is_saved = ? WHERE id = ?", (int(saved), article_id))

    def set_article_emoji(self, article_id: int, emoji: str | None) -> None:
        self.execute("UPDATE articles SET emoji = ? WHERE id = ?", (emoji or None, article_id))

    def purge_expired_articles(self, hours: int | None = None) -> int:
        if hours is None:
            hours = self.retention_hours()
        if not hours:
            return 0
        cutoff = datetime.now(timezone.utc) - timedelta(hours=max(1, hours))
        stale: list[int] = []
        for row in self.query("SELECT id, pub_date, created_at, is_saved FROM articles"):
            if bool(_row_col(row, "is_saved", 0)):
                continue
            stamp = _aware(_parse_dt(row["created_at"])) or _aware(_parse_dt(row["pub_date"]))
            if stamp is not None and stamp < cutoff:
                stale.append(int(row["id"]))
        for article_id in stale:
            self.execute("DELETE FROM articles WHERE id = ? AND IFNULL(is_saved, 0) = 0", (article_id,))
        return len(stale)

    def save_ai_result(self, article_id: int, summary: str, sentiment: str | None) -> None:
        self.execute(
            "UPDATE articles SET ai_summary = ?, sentiment = ? WHERE id = ?",
            (summary, sentiment, article_id),
        )

    def save_translation(self, article_id: int, translation: str, language_code: str) -> None:
        self.execute(
            "UPDATE articles SET ai_translation = ?, translation_lang = ? WHERE id = ?",
            (translation, language_code, article_id),
        )


def _parse_dt(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        try:
            return datetime.strptime(text[:19], "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            return None


def _row_col(row: sqlite3.Row, name: str, default: Any = None) -> Any:
    return row[name] if name in row.keys() else default


def _source_from_row(row: sqlite3.Row) -> Source:
    return Source(
        id=row["id"],
        module_id=row["module_id"],
        name=row["name"],
        url=row["url"],
        is_rss=bool(row["is_rss"]),
        css_selector=row["css_selector"],
        is_active=bool(row["is_active"]),
        user_added=bool(_row_col(row, "user_added", 0)),
        topic_id=_row_col(row, "topic_id"),
        last_fetch_at=_row_col(row, "last_fetch_at"),
        last_error=_row_col(row, "last_error"),
        last_ok=bool(_row_col(row, "last_ok", 1)),
        refresh_minutes=int(_row_col(row, "refresh_minutes", 0) or 0),
        muted_until=_row_col(row, "muted_until"),
    )


def _row_to_article(row: sqlite3.Row) -> Article:
    return Article(
        id=row["id"],
        source_id=row["source_id"],
        title=row["title"],
        content=row["content"],
        link=row["link"],
        pub_date=_parse_dt(row["pub_date"]),
        category=row["category"],
        ai_summary=row["ai_summary"],
        sentiment=row["sentiment"],
        is_read=bool(row["is_read"]),
        created_at=_parse_dt(row["created_at"]),
        source_name=_row_col(row, "source_name"),
        module_id=_row_col(row, "module_id"),
        ai_translation=_row_col(row, "ai_translation"),
        translation_lang=_row_col(row, "translation_lang"),
        image_url=_row_col(row, "image_url"),
        image_path=_row_col(row, "image_path"),
        source_topic_id=_row_col(row, "source_topic_id"),
        is_saved=bool(_row_col(row, "is_saved", 0)),
        emoji=_row_col(row, "emoji"),
        note=_row_col(row, "note"),
        tags=_row_col(row, "tags"),
        folder=_row_col(row, "folder"),
    )


def _classify_article(article: Article) -> Article:
    from core.topic_classifier import assign_leaf_topic

    article.assigned_topic_id = assign_leaf_topic(
        article.module_id,
        article.source_topic_id,
        article.title,
        article.content,
    )
    return article


def _story_instant(article: Article) -> Optional[datetime]:
    return _aware(article.pub_date) or _aware(article.created_at)


def _article_instant(article: Article) -> Optional[datetime]:
    return _story_instant(article)


def _retention_instant(article: Article) -> Optional[datetime]:
    return _aware(article.created_at) or _aware(article.pub_date)


def _visible_count(total: int, limit: int) -> int:
    return min(max(0, total), max(1, limit))


def _is_within_story_window(article: Article, cutoff: datetime) -> bool:
    instant = _story_instant(article)
    if instant is None:
        return False
    return instant >= cutoff


def _is_within_retention(article: Article, cutoff: datetime) -> bool:
    instant = _retention_instant(article)
    if instant is None:
        return True
    return instant >= cutoff


def _aware(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _apply_keyword_filters(article: Article, filters: list[UserFilter]) -> Article | None:
    text = f"{article.title} {article.content or ''}".lower()
    whitelist = [f.keyword.lower() for f in filters if f.filter_type == "whitelist"]
    blacklist = [f.keyword.lower() for f in filters if f.filter_type == "blacklist"]
    if blacklist and any(word in text for word in blacklist):
        return None
    if whitelist and not any(word in text for word in whitelist):
        return None
    return article
