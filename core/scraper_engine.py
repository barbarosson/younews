"""Fallback HTML scraper using CSS selectors."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from config import BROWSER_USER_AGENT, RSS_USER_AGENT
from core.app_extras import httpx_proxy_kwargs, is_source_stale
from database.db import Database
from database.models import Source


async def scrape_source(client: httpx.AsyncClient, source: Source) -> list[dict]:
    if not source.css_selector:
        return []
    last_error: Exception | None = None
    for attempt in range(3):
        headers = {"User-Agent": BROWSER_USER_AGENT if attempt else RSS_USER_AGENT}
        try:
            response = await client.get(
                source.url,
                headers=headers,
                timeout=22.0,
                follow_redirects=True,
            )
            if response.status_code in {403, 429, 502, 503, 504} and attempt < 2:
                await asyncio.sleep(1.0 * (attempt + 1))
                last_error = httpx.HTTPStatusError(
                    f"{response.status_code}",
                    request=response.request,
                    response=response,
                )
                continue
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "lxml")
            break
        except httpx.TimeoutException as exc:
            last_error = exc
            await asyncio.sleep(0.7 * (attempt + 1))
            soup = None
        except Exception as exc:
            last_error = exc
            soup = None
            await asyncio.sleep(0.4)
    else:
        if last_error:
            raise last_error
        return []
    if soup is None:
        if last_error:
            raise last_error
        return []
    items: list[dict] = []
    now = datetime.now(timezone.utc)
    for node in soup.select(source.css_selector)[:40]:
        title = node.get_text(" ", strip=True)
        href = node.get("href") if node.name == "a" else None
        if not href:
            anchor = node.find("a")
            href = anchor.get("href") if anchor else None
        if not title:
            continue
        items.append(
            {
                "title": title,
                "content": title,
                "link": urljoin(source.url, href) if href else None,
                "pub_date": now,
                "category": source.module_id,
            }
        )
    return items


async def refresh_scrapers(db: Database, force: bool = True) -> int:
    sources = [s for s in db.list_fetchable_sources() if not s.is_rss]
    if not force:
        sources = [s for s in sources if is_source_stale(s.last_fetch_at, max(int(s.refresh_minutes or 0), 15))]
    if not sources:
        return 0
    stored = 0
    headers = {"User-Agent": RSS_USER_AGENT}
    async with httpx.AsyncClient(headers=headers, **httpx_proxy_kwargs()) as client:
        for source in sources:
            try:
                items = await scrape_source(client, source)
            except Exception as exc:
                db.set_source_health(source.id, ok=False, error=str(exc))
                continue
            db.set_source_health(source.id, ok=True)
            for item in items:
                db.upsert_article(
                    source_id=source.id,
                    title=item["title"],
                    content=item["content"],
                    link=item["link"],
                    pub_date=item["pub_date"],
                    category=item["category"],
                )
                stored += 1
    return stored
