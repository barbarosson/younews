from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Module:
    id: str
    name_key: str
    is_active: bool = True
    icon_name: str = ""


@dataclass
class Topic:
    id: str
    module_id: str
    parent_id: Optional[str]
    name_key: str
    is_active: bool = True
    sort_order: int = 0


@dataclass
class Source:
    id: int
    module_id: str
    name: str
    url: str
    is_rss: bool = True
    css_selector: Optional[str] = None
    is_active: bool = True
    user_added: bool = False
    topic_id: Optional[str] = None
    last_fetch_at: Optional[str] = None
    last_error: Optional[str] = None
    last_ok: bool = True
    refresh_minutes: int = 0
    muted_until: Optional[str] = None


@dataclass
class Article:
    id: int
    source_id: Optional[int]
    title: str
    content: Optional[str]
    link: Optional[str]
    pub_date: Optional[datetime]
    category: Optional[str]
    ai_summary: Optional[str]
    sentiment: Optional[str]
    is_read: bool
    created_at: Optional[datetime]
    source_name: Optional[str] = None
    module_id: Optional[str] = None
    ai_translation: Optional[str] = None
    translation_lang: Optional[str] = None
    image_url: Optional[str] = None
    image_path: Optional[str] = None
    source_topic_id: Optional[str] = None
    assigned_topic_id: Optional[str] = None
    is_saved: bool = False
    emoji: Optional[str] = None
    note: Optional[str] = None
    tags: Optional[str] = None
    folder: Optional[str] = None


@dataclass
class UserFilter:
    id: int
    keyword: str
    filter_type: str
    is_active: bool = True


@dataclass
class Ticker:
    id: int
    symbol: str
    label: str
    sort_order: int = 0
    alert_pct: Optional[float] = None
    watchlist: str = "main"
