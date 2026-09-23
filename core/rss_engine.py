"""Async RSS fetcher using httpx + feedparser."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from time import struct_time
from typing import Any

import feedparser
import httpx

from config import BROWSER_USER_AGENT, RSS_USER_AGENT, parse_feed_refresh_minutes
from core.app_extras import httpx_proxy_kwargs, is_source_stale, sanitize_article_html
from core.image_engine import extract_entry_image
from database.db import Database
from database.models import Source

_RETRY_STATUSES = {403, 408, 429, 500, 502, 503, 504}
_ACCEPT = "application/rss+xml, application/atom+xml, application/xml;q=0.9, text/xml;q=0.8, */*;q=0.5"


def _to_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, struct_time):
        try:
            return datetime(*value[:6], tzinfo=timezone.utc)
        except Exception:
            return None
    if isinstance(value, str):
        try:
            return parsedate_to_datetime(value)
        except Exception:
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except Exception:
                return None
    return None


def _entry_html(entry: Any) -> str:
    chunks: list[str] = []
    for item in getattr(entry, "content", None) or []:
        if isinstance(item, dict):
            chunks.append(str(item.get("value") or ""))
        else:
            chunks.append(str(getattr(item, "value", None) or item or ""))
    summary = getattr(entry, "summary", None)
    if summary is None and hasattr(entry, "get"):
        summary = entry.get("description")
    chunks.append(str(summary or ""))
    body = max(chunks, key=lambda part: len(part or ""), default="")
    return sanitize_article_html(body)


def _looks_like_html(content: bytes) -> bool:
    head = content[:1200].lstrip().lower()
    return head.startswith(b"<!doctype html") or head.startswith(b"<html") or b"<html" in head[:400]


def _parse_items(source: Source, content: bytes) -> list[dict[str, Any]]:
    parsed = feedparser.parse(content)
    items: list[dict[str, Any]] = []
    for entry in parsed.entries:
        link = getattr(entry, "link", None) or entry.get("id")
        title = getattr(entry, "title", "") or ""
        summary = _entry_html(entry)
        published = _to_datetime(getattr(entry, "published", None)) or _to_datetime(
            getattr(entry, "updated", None)
        )
        if not published and getattr(entry, "published_parsed", None):
            published = _to_datetime(entry.published_parsed)
        items.append(
            {
                "title": title.strip() or "(untitled)",
                "content": summary,
                "link": link,
                "pub_date": published,
                "category": source.module_id,
                "image_url": extract_entry_image(entry),
            }
        )
    if items:
        return items
    if _looks_like_html(content):
        raise RuntimeError("html_not_rss")
    bozo = getattr(parsed, "bozo", 0)
    if bozo and not getattr(parsed, "feed", None):
        raise RuntimeError(str(getattr(parsed, "bozo_exception", None) or "bad_feed"))
    return []


async def fetch_feed(client: httpx.AsyncClient, source: Source) -> list[dict[str, Any]]:
    last_error: Exception | None = None
    for attempt in range(3):
        headers = {
            "User-Agent": BROWSER_USER_AGENT if attempt else RSS_USER_AGENT,
            "Accept": _ACCEPT,
            "Accept-Language": "en-US,en;q=0.8,tr;q=0.6",
        }
        try:
            response = await client.get(
                source.url,
                headers=headers,
                timeout=22.0,
                follow_redirects=True,
            )
            if response.status_code in _RETRY_STATUSES and attempt < 2:
                wait = 1.2 * (attempt + 1)
                retry_after = response.headers.get("Retry-After")
                try:
                    wait = max(wait, float(retry_after)) if retry_after else wait
                except (TypeError, ValueError):
                    pass
                await asyncio.sleep(min(wait, 8.0))
                last_error = httpx.HTTPStatusError(
                    f"{response.status_code} {source.url}",
                    request=response.request,
                    response=response,
                )
                continue
            response.raise_for_status()
            return _parse_items(source, response.content)
        except httpx.TimeoutException as exc:
            last_error = exc
            await asyncio.sleep(0.7 * (attempt + 1))
        except httpx.HTTPStatusError as exc:
            last_error = exc
            if exc.response is not None and exc.response.status_code in _RETRY_STATUSES and attempt < 2:
                await asyncio.sleep(1.0 * (attempt + 1))
                continue
            raise
        except RuntimeError:
            raise
        except Exception as exc:
            last_error = exc
            await asyncio.sleep(0.5 * (attempt + 1))
    if last_error:
        raise last_error
    return []


def _source_refresh_minutes(db: Database, source: Source) -> int:
    if int(source.refresh_minutes or 0) > 0:
        return int(source.refresh_minutes)
    return parse_feed_refresh_minutes(db.get_setting("feed_refresh_minutes")) or 15


def _store_items(db: Database, source: Source, items: list[dict[str, Any]]) -> int:
    stored = 0
    for item in items:
        db.upsert_article(
            source_id=source.id,
            title=item["title"],
            content=item["content"],
            link=item["link"],
            pub_date=item["pub_date"],
            category=item["category"],
            image_url=item.get("image_url"),
        )
        stored += 1
    return stored


async def refresh_all_rss(db: Database, force: bool = True) -> int:
    sources = [s for s in db.list_fetchable_sources() if s.is_rss]
    if not force:
        sources = [s for s in sources if is_source_stale(s.last_fetch_at, _source_refresh_minutes(db, s))]
    if not sources:
        return 0
    headers = {"User-Agent": RSS_USER_AGENT, "Accept": _ACCEPT}
    stored = 0
    sem = asyncio.Semaphore(6)

    async def _one(source: Source):
        async with sem:
            return await fetch_feed(client, source)

    async with httpx.AsyncClient(headers=headers, **httpx_proxy_kwargs()) as client:
        results = await asyncio.gather(
            *[_one(source) for source in sources],
            return_exceptions=True,
        )
    for source, result in zip(sources, results):
        if isinstance(result, Exception):
            db.set_source_health(source.id, ok=False, error=str(result)[:400])
            continue
        if not result:
            db.set_source_health(source.id, ok=True, error="")
            continue
        db.set_source_health(source.id, ok=True)
        stored += _store_items(db, source, result)
    return stored


async def refresh_one_rss(db: Database, source: Source) -> int:
    if not source.is_rss:
        return 0
    headers = {"User-Agent": RSS_USER_AGENT, "Accept": _ACCEPT}
    async with httpx.AsyncClient(headers=headers, **httpx_proxy_kwargs()) as client:
        try:
            items = await fetch_feed(client, source)
        except Exception as exc:
            db.set_source_health(source.id, ok=False, error=str(exc)[:400])
            return 0
    db.set_source_health(source.id, ok=True)
    return _store_items(db, source, items)
