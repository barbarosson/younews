"""Connection probe for a candidate RSS or HTML source."""

from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter

import feedparser
import httpx
from bs4 import BeautifulSoup

from config import RSS_USER_AGENT

HEADERS = {
    "User-Agent": RSS_USER_AGENT,
    "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, text/html",
}


@dataclass
class SourceProbeResult:
    ok: bool
    status_code: int | None = None
    elapsed_ms: int = 0
    item_count: int = 0
    feed_title: str = ""
    sample_titles: list[str] = field(default_factory=list)
    error: str = ""
    lines: list[str] = field(default_factory=list)


def probe_source(
    url: str,
    *,
    is_rss: bool = True,
    css_selector: str | None = None,
    sample_limit: int = 3,
) -> SourceProbeResult:
    started = perf_counter()
    result = SourceProbeResult(ok=False)
    result.lines.append(f"GET {url}")
    try:
        with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=20.0) as client:
            response = client.get(url)
        result.elapsed_ms = int((perf_counter() - started) * 1000)
        result.status_code = response.status_code
        result.lines.append(
            f"HTTP {response.status_code} · {result.elapsed_ms} ms · {len(response.content)} bytes"
        )
        if response.url and str(response.url) != url:
            result.lines.append(f"Redirect → {response.url}")
        response.raise_for_status()
        if is_rss:
            _probe_rss(result, response.content, sample_limit=sample_limit)
        else:
            _probe_html(result, response.text, css_selector or "", sample_limit=sample_limit)
    except Exception as exc:
        result.elapsed_ms = int((perf_counter() - started) * 1000)
        result.error = str(exc)
        result.ok = False
        result.lines.append(f"FAIL: {exc}")
    return result


def _probe_rss(result: SourceProbeResult, content: bytes, *, sample_limit: int = 3) -> None:
    parsed = feedparser.parse(content)
    feed = parsed.feed if isinstance(parsed.feed, dict) else {}
    result.feed_title = str(getattr(parsed.feed, "title", None) or feed.get("title") or "").strip()
    entries = list(parsed.entries or [])
    result.item_count = len(entries)
    if result.feed_title:
        result.lines.append(f"Feed title: {result.feed_title}")
    if getattr(parsed, "bozo", False) and getattr(parsed, "bozo_exception", None):
        result.lines.append(f"Parse warning: {parsed.bozo_exception}")
    result.lines.append(f"Items found: {result.item_count}")
    for entry in entries[: max(1, sample_limit)]:
        title = str(getattr(entry, "title", "") or "").strip() or "(untitled)"
        when = str(getattr(entry, "published", "") or getattr(entry, "updated", "") or "").strip()
        result.sample_titles.append(title)
        result.lines.append(f"  • {title}" + (f"  ({when})" if when else ""))
    if result.item_count <= 0:
        result.ok = False
        result.error = "empty_feed"
        result.lines.append("FAIL: connected, but the feed has no items")
        return
    result.ok = True
    result.lines.append("OK: connection successful")


def _probe_html(result: SourceProbeResult, html: str, selector: str, sample_limit: int = 3) -> None:
    if not selector.strip():
        result.ok = False
        result.error = "missing_selector"
        result.lines.append("FAIL: CSS selector required for HTML scrape")
        return
    soup = BeautifulSoup(html, "lxml")
    nodes = soup.select(selector)[:40]
    result.item_count = len(nodes)
    result.lines.append(f"Selector {selector!r} · matches: {result.item_count}")
    for node in nodes[: max(1, sample_limit)]:
        title = node.get_text(" ", strip=True)[:120] or "(empty)"
        result.sample_titles.append(title)
        result.lines.append(f"  • {title}")
    if result.item_count <= 0:
        result.ok = False
        result.error = "empty_feed"
        result.lines.append("FAIL: page loaded, but the selector matched nothing")
        return
    result.ok = True
    result.lines.append("OK: connection successful")


def _feed_candidates(url: str) -> list[str]:
    from urllib.parse import urlparse, urlunparse

    raw = url.strip()
    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return []
    cleaned = urlunparse(
        (parsed.scheme, parsed.netloc, parsed.path or "/", parsed.params, parsed.query, "")
    ).rstrip("/")
    lower = cleaned.lower()
    candidates = [raw.strip()]
    if any(token in lower for token in ("/rss", "/feed", "/atom", ".xml")):
        return _unique_urls(candidates)
    base = f"{parsed.scheme}://{parsed.netloc}"
    candidates.extend(
        [
            f"{cleaned}/feed",
            f"{cleaned}/rss",
            f"{cleaned}/rss.xml",
            f"{cleaned}/feed.xml",
            f"{cleaned}/atom.xml",
            f"{base}/feed",
            f"{base}/rss.xml",
        ]
    )
    return _unique_urls(candidates)[:6]


def _unique_urls(urls: list[str]) -> list[str]:
    seen: set[str] = set()
    items: list[str] = []
    for url in urls:
        key = url.rstrip("/").lower()
        if not url or key in seen:
            continue
        seen.add(key)
        items.append(url)
    return items


def import_news_feed(db, url: str, module_id: str, topic_id: str | None = None) -> dict:
    """Probe a user-supplied news URL, save it as an RSS source, and pull headlines."""
    import asyncio
    from urllib.parse import urlparse

    from core.rss_engine import refresh_one_rss
    from database.db import DuplicateSourceError, is_http_url

    if not is_http_url(url):
        return {"status": "failed", "name": url, "url": url, "count": 0, "error": "invalid_url"}
    last_error = "empty_feed"
    last_url = url.strip()
    for candidate in _feed_candidates(url):
        last_url = candidate
        probe = probe_source(candidate, is_rss=True)
        if not probe.ok:
            last_error = probe.error or "empty_feed"
            continue
        name = (probe.feed_title or urlparse(candidate).netloc or candidate).strip()[:80]
        status = "added"
        try:
            source_id = db.add_user_source(
                name=name,
                url=candidate,
                module_id=module_id,
                is_rss=True,
                topic_id=topic_id,
            )
        except DuplicateSourceError:
            existing = db.find_source_by_url(candidate)
            if existing is None:
                return {
                    "status": "duplicate",
                    "name": name,
                    "url": candidate,
                    "count": 0,
                    "error": "",
                }
            source_id = existing.id
            status = "duplicate"
        source = db.get_source(int(source_id))
        stored = 0
        if source is not None:
            try:
                stored = int(asyncio.run(refresh_one_rss(db, source)) or 0)
            except Exception as exc:
                last_error = str(exc)
                stored = 0
        return {
            "status": status,
            "name": source.name if source else name,
            "url": candidate,
            "count": stored,
            "error": "",
        }
    return {"status": "failed", "name": last_url, "url": last_url, "count": 0, "error": last_error}
