"""Bounded thumbnail extraction and disk cache (never on the UI thread)."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from config import (
    IMAGE_CACHE_DIR,
    IMAGE_FETCH_TIMEOUT,
    IMAGE_MAX_BYTES,
    IMAGE_PREFETCH_LIMIT,
    RSS_USER_AGENT,
)
from database.db import Database
from database.models import Article

_IMG_TAG = re.compile(r'<img[^>]+src=["\']([^"\']+)["\']', re.IGNORECASE)
_IMAGE_TYPES = ("image/",)
_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif"}


def extract_entry_image(entry: Any) -> str | None:
    for thumb in _as_list(entry.get("media_thumbnail") if hasattr(entry, "get") else None):
        url = _dict_url(thumb)
        if url:
            return url
    media_thumb = getattr(entry, "media_thumbnail", None)
    for thumb in _as_list(media_thumb):
        url = _dict_url(thumb)
        if url:
            return url
    for item in _as_list(entry.get("media_content") if hasattr(entry, "get") else None):
        if _looks_like_image(_dict_url(item), item.get("type") if isinstance(item, dict) else None):
            url = _dict_url(item)
            if url:
                return url
    enclosures = getattr(entry, "enclosures", None)
    if not enclosures and hasattr(entry, "get"):
        enclosures = entry.get("enclosures")
    for enc in enclosures or []:
        href = ""
        mime = ""
        if isinstance(enc, dict):
            href = enc.get("href") or enc.get("url") or ""
            mime = enc.get("type") or ""
        else:
            href = getattr(enc, "href", "") or ""
            mime = getattr(enc, "type", "") or ""
        if href and _looks_like_image(href, mime):
            return href
    itunes = None
    if hasattr(entry, "get"):
        itunes = entry.get("itunes_image")
    if isinstance(itunes, dict):
        href = itunes.get("href") or itunes.get("url")
        if href:
            return href
    image_field = getattr(entry, "image", None)
    if isinstance(image_field, dict) and image_field.get("href"):
        return image_field["href"]
    if isinstance(image_field, str) and image_field.startswith("http"):
        return image_field
    summary = ""
    if hasattr(entry, "get"):
        summary = entry.get("summary") or entry.get("description") or ""
    summary = summary or getattr(entry, "summary", "") or getattr(entry, "description", "") or ""
    match = _IMG_TAG.search(str(summary))
    if match:
        return match.group(1)
    return None


def extract_og_image(html: str, page_url: str) -> str | None:
    soup = BeautifulSoup(html, "lxml")
    tag = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "og:image"})
    if not tag:
        tag = soup.find("meta", property="og:image:url")
    content = (tag.get("content") if tag else None) or ""
    if not content:
        return None
    return urljoin(page_url, content)


def cache_path_for(url: str) -> Path:
    digest = hashlib.sha256(url.encode("utf-8", errors="ignore")).hexdigest()[:32]
    suffix = Path(urlparse(url).path).suffix.lower()
    if suffix not in _IMAGE_EXTS:
        suffix = ".img"
    return IMAGE_CACHE_DIR / f"{digest}{suffix}"


def prefetch_article_images(
    db: Database,
    articles: list[Article],
    on_ready: Callable[[int, str], None] | None = None,
    limit: int = IMAGE_PREFETCH_LIMIT,
) -> int:
    IMAGE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    headers = {"User-Agent": RSS_USER_AGENT, "Accept": "image/*,text/html;q=0.8"}
    stored = 0
    with httpx.Client(headers=headers, follow_redirects=True, timeout=IMAGE_FETCH_TIMEOUT) as client:
        for article in articles[: max(1, limit)]:
            path = _ensure_thumbnail(client, db, article)
            if path:
                stored += 1
                if on_ready:
                    on_ready(article.id, str(path))
    return stored


def _ensure_thumbnail(client: httpx.Client, db: Database, article: Article) -> Path | None:
    if article.image_path:
        existing = Path(article.image_path)
        if existing.is_file() and existing.stat().st_size > 0:
            return existing
    image_url = article.image_url
    if not image_url and article.link:
        image_url = _fetch_og_image(client, article.link)
        if image_url:
            db.save_article_image(article.id, image_url=image_url)
    if not image_url:
        return None
    path = _download_image(client, image_url)
    if path is None:
        return None
    db.save_article_image(article.id, image_url=image_url, image_path=str(path))
    return path


def _fetch_og_image(client: httpx.Client, page_url: str) -> str | None:
    try:
        with client.stream("GET", page_url) as response:
            if response.status_code >= 400:
                return None
            chunks: list[bytes] = []
            total = 0
            for chunk in response.iter_bytes():
                chunks.append(chunk)
                total += len(chunk)
                if total >= 80_000:
                    break
            html = b"".join(chunks).decode(response.encoding or "utf-8", errors="ignore")
            page = str(response.url)
        return extract_og_image(html, page)
    except Exception:
        return None


def _download_image(client: httpx.Client, url: str) -> Path | None:
    dest = cache_path_for(url)
    if dest.is_file() and dest.stat().st_size > 0:
        return dest
    try:
        with client.stream("GET", url) as response:
            if response.status_code >= 400:
                return None
            content_type = (response.headers.get("content-type") or "").split(";")[0].strip().lower()
            if content_type and not content_type.startswith("image/") and content_type not in {
                "application/octet-stream",
                "binary/octet-stream",
            }:
                return None
            chunks: list[bytes] = []
            total = 0
            for chunk in response.iter_bytes():
                total += len(chunk)
                if total > IMAGE_MAX_BYTES:
                    return None
                chunks.append(chunk)
        data = b"".join(chunks)
        if len(data) < 32:
            return None
        dest.write_bytes(data)
        return dest
    except Exception:
        return None


def _as_list(value: Any) -> list[Any]:
    if not value:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _dict_url(value: Any) -> str | None:
    if isinstance(value, dict):
        url = value.get("url") or value.get("href")
        return str(url) if url else None
    return None


def _looks_like_image(url: str | None, mime: str | None = None) -> bool:
    if mime and any(mime.startswith(prefix) for prefix in _IMAGE_TYPES):
        return True
    if not url:
        return False
    path = urlparse(url).path.lower()
    return any(path.endswith(ext) for ext in _IMAGE_EXTS)
