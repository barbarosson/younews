"""Resolve a social handle or URL to a public RSS feed. No scraping of X/IG/TikTok."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

import httpx

from config import RSS_USER_AGENT, SOCIAL_MODULE_ID

SUPPORTED = ("youtube", "substack", "bluesky")
PLATFORMS = SUPPORTED

TOPIC_IDS = {
    "youtube": "social_media.youtube",
    "substack": "social_media.substack",
    "bluesky": "social_media.bluesky",
}

YOUTUBE_CHANNEL_ID_RE = re.compile(r"UC[\w-]{22}")
YOUTUBE_PAGE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
HEADERS = {
    "User-Agent": RSS_USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml,application/rss+xml",
}


class SocialResolveError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class ResolvedFollow:
    platform: str
    name: str
    feed_url: str
    topic_id: str


def detect_platform(raw: str) -> str | None:
    text = (raw or "").strip().lower()
    if not text:
        return None
    if "youtube.com" in text or "youtu.be" in text:
        return "youtube"
    if "bsky.app" in text or text.endswith(".bsky.social") or "/profile/" in text and "bsky" in text:
        return "bluesky"
    if "substack.com" in text:
        return "substack"
    return None


def resolve_follow(platform: str, raw: str) -> ResolvedFollow:
    platform = (platform or "").strip().lower()
    text = (raw or "").strip()
    detected = detect_platform(text)
    if detected:
        platform = detected
    if platform not in SUPPORTED:
        raise SocialResolveError("unsupported")
    if not text:
        raise SocialResolveError("empty")
    if platform == "youtube":
        return _youtube(text)
    if platform == "substack":
        return _substack(text)
    return _bluesky(text)


def _youtube(text: str) -> ResolvedFollow:
    raw = text.strip()
    page_url = _youtube_page_url(raw)
    if page_url:
        parsed = urlparse(page_url)
        query = parse_qs(parsed.query)
        channel_id = (query.get("channel_id") or [""])[0].strip()
        parts = [p for p in parsed.path.split("/") if p]
        if parts[:1] == ["channel"] and len(parts) >= 2 and _is_channel_id(parts[1]):
            channel_id = parts[1]
        if _is_channel_id(channel_id):
            return _youtube_follow(channel_id, channel_id)
        html = _fetch_youtube_html(page_url)
        channel_id = _channel_id_from_html(html)
        if not channel_id:
            raise SocialResolveError("not_found")
        name = _channel_title_from_html(html) or _youtube_handle_from_url(page_url) or channel_id
        return _youtube_follow(channel_id, name)
    handle = raw.lstrip("@").split("/")[0].split("?")[0].strip()
    if not handle or " " in handle:
        raise SocialResolveError("not_found")
    html = _fetch_youtube_html(f"https://www.youtube.com/@{handle}")
    channel_id = _channel_id_from_html(html)
    if not channel_id:
        raise SocialResolveError("not_found")
    name = _channel_title_from_html(html) or handle
    return _youtube_follow(channel_id, name)


def _youtube_follow(channel_id: str, name: str) -> ResolvedFollow:
    return ResolvedFollow(
        "youtube",
        name,
        f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}",
        TOPIC_IDS["youtube"],
    )


def _is_channel_id(value: str) -> bool:
    return bool(value) and bool(YOUTUBE_CHANNEL_ID_RE.fullmatch(value.strip()))


def _youtube_page_url(text: str) -> str | None:
    lower = text.lower()
    if "://" not in text:
        if lower.startswith(("www.youtube.", "youtube.", "m.youtube.", "youtu.be")):
            text = "https://" + text
            lower = text.lower()
        else:
            return None
    if "youtube.com" not in lower and "youtu.be" not in lower:
        return None
    return text.split()[0]


def _youtube_handle_from_url(url: str) -> str:
    if "/@" in url:
        return url.split("/@", 1)[1].split("/")[0].split("?")[0]
    parsed = urlparse(url)
    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) >= 2 and parts[0] in {"c", "user"}:
        return parts[1]
    return ""


def _channel_id_from_html(html: str) -> str:
    patterns = (
        r"feeds/videos\.xml\?channel_id=(UC[\w-]{22})",
        r'"rssUrl":"[^"]*channel_id=(UC[\w-]{22})"',
        r'"externalId":"(UC[\w-]{22})"',
        r'rel="canonical"[^>]*href="https://www\.youtube\.com/channel/(UC[\w-]{22})"',
        r'href="https://www\.youtube\.com/channel/(UC[\w-]{22})"',
        r'"ownerChannelId":"(UC[\w-]{22})"',
        r'"videoDetails":\{[^{}]*"channelId":"(UC[\w-]{22})"',
        r'"browseId":"(UC[\w-]{22})"',
    )
    for pattern in patterns:
        match = re.search(pattern, html)
        if match:
            return match.group(1)
    return ""


def _channel_title_from_html(html: str) -> str:
    match = re.search(r'"channelMetadataRenderer":\{"title":"([^"]+)"', html)
    if match:
        return _json_unescape(match.group(1)).strip()
    match = re.search(r"<meta[^>]+property=\"og:title\"[^>]+content=\"([^\"]+)\"", html, re.I)
    if match:
        return match.group(1).replace(" - YouTube", "").strip()
    return ""


def _json_unescape(value: str) -> str:
    try:
        return str(json.loads(f'"{value}"'))
    except Exception:
        return value.replace("\\/", "/")


def _fetch_youtube_html(url: str) -> str:
    try:
        with httpx.Client(headers=YOUTUBE_PAGE_HEADERS, follow_redirects=True, timeout=20.0) as client:
            response = client.get(url)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise SocialResolveError("not_found") from exc
    return response.text


def repair_youtube_follows(db) -> int:
    if db.get_setting("youtube_channel_fix", "0") == "1":
        return 0
    changed = 0
    for source in db.list_sources(active_only=False):
        if source.module_id != SOCIAL_MODULE_ID:
            continue
        url = source.url or ""
        if "youtube.com/feeds/videos.xml" not in url.lower():
            continue
        hint = (source.name or "").strip()
        if not hint or hint.startswith("UC"):
            continue
        try:
            resolved = _youtube(hint)
        except Exception:
            continue
        if resolved.feed_url.rstrip("/") == url.rstrip("/"):
            continue
        db.execute(
            "UPDATE sources SET url = ?, name = ? WHERE id = ?",
            (resolved.feed_url, resolved.name, source.id),
        )
        db.execute("DELETE FROM articles WHERE source_id = ?", (source.id,))
        changed += 1
    db.set_setting("youtube_channel_fix", "1")
    return changed


def _substack(text: str) -> ResolvedFollow:
    value = text.strip()
    if "://" not in value:
        host = value.replace("https://", "").replace("http://", "").split("/")[0]
        if "." not in host:
            host = f"{host}.substack.com"
        value = f"https://{host}"
    parsed = urlparse(value)
    host = parsed.netloc or parsed.path.split("/")[0]
    if not host:
        raise SocialResolveError("not_found")
    if not host.endswith("substack.com") and "substack.com" not in host:
        feed = f"https://{host}/feed"
    else:
        feed = f"https://{host}/feed"
    name = host.split(".")[0]
    return ResolvedFollow("substack", name, feed, TOPIC_IDS["substack"])


def _bluesky(text: str) -> ResolvedFollow:
    handle = text.strip()
    if "bsky.app/profile/" in handle:
        handle = handle.split("profile/", 1)[1].split("/")[0].split("?")[0]
    handle = handle.lstrip("@")
    if "." not in handle:
        handle = f"{handle}.bsky.social"
    feed = f"https://bsky.app/profile/{handle}/rss"
    try:
        with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=12.0) as client:
            response = client.get(feed)
    except httpx.HTTPError as exc:
        raise SocialResolveError("not_found") from exc
    if response.status_code >= 400:
        raise SocialResolveError("not_found")
    return ResolvedFollow("bluesky", handle, feed, TOPIC_IDS["bluesky"])
