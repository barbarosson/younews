"""OPML, full text, dedupe, Windows desktop helpers."""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from xml.sax.saxutils import escape

from config import APP_NAME, APP_ORG, DB_PATH, RSS_USER_AGENT


def normalize_headline(title: str) -> str:
    text = re.sub(r"\s+", " ", (title or "").casefold())
    text = re.sub(r"[^\w\s]", "", text, flags=re.UNICODE)
    return text.strip()[:96]


def cluster_articles(articles: list, *, enabled: bool = True) -> list:
    if not enabled:
        return list(articles)
    seen: set[str] = set()
    kept = []
    for article in articles:
        key = normalize_headline(getattr(article, "title", "") or "")
        if not key:
            kept.append(article)
            continue
        if key in seen:
            continue
        seen.add(key)
        kept.append(article)
    return kept


def search_tokens(query: str) -> list[str]:
    return [part for part in re.split(r"\s+", (query or "").strip()) if len(part) >= 2][:8]


def export_opml(sources: list, dest: Path) -> None:
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<opml version="2.0">',
        "<head>",
        f"<title>{escape(APP_NAME)}</title>",
        "</head>",
        "<body>",
    ]
    for source in sources:
        if getattr(source, "module_id", "") == "social_media":
            continue
        url = escape(source.url or "")
        name = escape(source.name or url)
        lines.append(f'<outline text="{name}" title="{name}" type="rss" xmlUrl="{url}" />')
    lines.extend(["</body>", "</opml>"])
    dest.write_text("\n".join(lines), encoding="utf-8")


def parse_opml(path: Path) -> list[tuple[str, str]]:
    tree = ET.parse(path)
    found: list[tuple[str, str]] = []
    for node in tree.iter():
        tag = node.tag.split("}")[-1].lower()
        if tag != "outline":
            continue
        url = (node.attrib.get("xmlUrl") or node.attrib.get("xmlurl") or node.attrib.get("url") or "").strip()
        if not url.lower().startswith("http"):
            continue
        name = (node.attrib.get("title") or node.attrib.get("text") or urlparse(url).netloc or url).strip()
        found.append((name, url))
    return found


def fetch_full_text(url: str) -> str:
    if not (url or "").startswith("http"):
        return ""
    import httpx
    from bs4 import BeautifulSoup

    headers = {"User-Agent": RSS_USER_AGENT}
    with httpx.Client(headers=headers, follow_redirects=True, timeout=20.0, **httpx_proxy_kwargs()) as client:
        response = client.get(url)
        response.raise_for_status()
    soup = BeautifulSoup(response.text, "lxml")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
        tag.decompose()
    article = soup.find("article") or soup.find("main") or soup.body
    if article is None:
        return ""
    blocks = [p.get_text(" ", strip=True) for p in article.find_all(["p", "h2", "li"])]
    text = "\n\n".join(part for part in blocks if len(part) > 40)
    return text[:20000]


def backup_database(dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(DB_PATH, dest)
    return dest


def restore_database(src: Path) -> None:
    if not src.is_file():
        raise FileNotFoundError(src)
    shutil.copy2(src, DB_PATH)


def set_windows_startup(enabled: bool) -> None:
    if os.name != "nt":
        return
    try:
        import winreg
    except ImportError:
        return
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    exe = sys.executable
    script = str(Path(__file__).resolve().parents[1] / "main.py")
    if getattr(sys, "frozen", False):
        command = f'"{sys.executable}"'
    else:
        command = f'"{exe}" "{script}"'
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
        if enabled:
            winreg.SetValueEx(key, APP_ORG, 0, winreg.REG_SZ, command)
        else:
            try:
                winreg.DeleteValue(key, APP_ORG)
            except FileNotFoundError:
                pass


CHAT_SAFE = 80


def dump_chat(messages: list[dict]) -> str:
    return json.dumps(messages[-CHAT_SAFE:], ensure_ascii=False)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def relative_time(value: datetime | None, now: datetime | None = None) -> str:
    if value is None:
        return ""
    current = now or datetime.now(timezone.utc)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    delta = current - value.astimezone(timezone.utc)
    seconds = int(delta.total_seconds())
    if seconds < 0:
        seconds = 0
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m"
    if seconds < 86400:
        return f"{seconds // 3600}h"
    return f"{seconds // 86400}d"


def looks_like_paywall(text: str) -> bool:
    sample = (text or "").casefold()
    if len(sample) > 1200:
        return False
    needles = ("subscribe to continue", "become a subscriber", "abone olun", "paywall", "metered")
    return any(token in sample for token in needles)


_TAG_RE = re.compile(r"</?(p|div|br|span|a|ul|ol|li|h[1-6]|strong|em|b|i|article|section|blockquote)\b", re.I)
_KEEP_TAGS = {"p", "br", "a", "strong", "b", "em", "i", "ul", "ol", "li", "h2", "h3", "blockquote"}
_BYLINE_RE = re.compile(
    r"\s*(This article was written by .+?(?:\.|$))(\s*$)",
    re.IGNORECASE,
)


def fully_unescape(text: str) -> str:
    from html import unescape

    current = (text or "").replace("\xa0", " ")
    for _ in range(4):
        nxt = unescape(current).replace("\xa0", " ")
        if nxt == current:
            break
        current = nxt
    return current


def sanitize_article_html(raw: str) -> str:
    """Turn RSS/HTML blobs into readable Qt-rich-text paragraphs (no raw tags)."""
    from html import escape as html_escape

    from bs4 import BeautifulSoup, NavigableString

    text = fully_unescape(raw).strip()
    if not text:
        return ""
    text = _BYLINE_RE.sub("", text).strip()
    if not _TAG_RE.search(text):
        blocks = [part.strip() for part in re.split(r"\n{2,}", text) if part.strip()]
        if not blocks:
            return ""
        return "".join(
            f"<p>{html_escape(block).replace(chr(10), '<br>')}</p>" for block in blocks
        )

    soup = BeautifulSoup(text, "lxml")
    for tag in soup(["script", "style", "iframe", "noscript", "svg"]):
        tag.decompose()

    def render(node) -> str:
        if isinstance(node, NavigableString):
            return html_escape(str(node))
        name = (getattr(node, "name", None) or "").lower()
        if name in {"html", "body", "[document]"}:
            return "".join(render(child) for child in node.children)
        if name == "br":
            return "<br>"
        inner = "".join(render(child) for child in node.children)
        if name not in _KEEP_TAGS:
            return inner
        if name == "a":
            href = str(node.get("href") or "").strip()
            if href.startswith("http://") or href.startswith("https://"):
                return f'<a href="{html_escape(href, quote=True)}">{inner}</a>'
            return inner
        if name in {"b", "strong"}:
            return f"<b>{inner}</b>"
        if name in {"i", "em"}:
            return f"<i>{inner}</i>"
        if name == "li":
            return f"<li>{inner}</li>"
        if name in {"ul", "ol"}:
            return f"<{name}>{inner}</{name}>"
        if name in {"h2", "h3", "blockquote"}:
            return f"<{name}>{inner}</{name}>"
        return f"<p>{inner}</p>"

    html = render(soup)
    html = re.sub(r"(?:<p>\s*</p>)+", "", html)
    html = re.sub(r"(<br>\s*){3,}", "<br><br>", html)
    plain = BeautifulSoup(html, "lxml").get_text(" ", strip=True) if html else ""
    if len(plain) < 8:
        fallback = soup.get_text("\n", strip=True)
        if not fallback:
            return ""
        return "".join(
            f"<p>{html_escape(part)}</p>" for part in fallback.split("\n") if part.strip()
        )
    return html


def discover_rss(page_url: str) -> list[str]:
    if not (page_url or "").startswith("http"):
        return []
    import httpx
    from bs4 import BeautifulSoup

    headers = {"User-Agent": RSS_USER_AGENT}
    with httpx.Client(headers=headers, follow_redirects=True, timeout=12.0, proxy=_proxy()) as client:
        response = client.get(page_url)
        response.raise_for_status()
    soup = BeautifulSoup(response.text, "lxml")
    found: list[str] = []
    for link in soup.find_all("link"):
        rel = " ".join(link.get("rel") or []).lower()
        typ = (link.get("type") or "").lower()
        href = link.get("href") or ""
        if "rss" in typ or "atom" in typ or "alternate" in rel and "rss" in typ:
            if href:
                found.append(href)
    return found[:8]


def _proxy() -> str | None:
    return os.environ.get("YOU_NEWS_PROXY") or os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY") or None


def httpx_proxy_kwargs() -> dict:
    proxy = _proxy()
    return {"proxy": proxy} if proxy else {}


def apply_proxy_setting(url: str) -> None:
    cleaned = (url or "").strip()
    if cleaned:
        os.environ["YOU_NEWS_PROXY"] = cleaned
        os.environ["HTTPS_PROXY"] = cleaned
        os.environ["HTTP_PROXY"] = cleaned
    else:
        os.environ.pop("YOU_NEWS_PROXY", None)


def quotes_to_csv(quotes: list, dest: Path) -> None:
    lines = ["symbol,label,price,change_pct,missing"]
    for quote in quotes:
        lines.append(
            ",".join(
                [
                    str(getattr(quote, "symbol", "")),
                    '"' + str(getattr(quote, "label", "")).replace('"', "'") + '"',
                    str(getattr(quote, "price", "")),
                    str(getattr(quote, "change_pct", "")),
                    str(int(bool(getattr(quote, "missing", False)))),
                ]
            )
        )
    dest.write_text("\n".join(lines), encoding="utf-8")


def sync_database_copy(folder: str) -> None:
    target = (folder or "").strip()
    if not target:
        return
    path = Path(target)
    path.mkdir(parents=True, exist_ok=True)
    shutil.copy2(DB_PATH, path / "terminal.db")


def clear_image_cache() -> int:
    from config import IMAGE_CACHE_DIR

    if not IMAGE_CACHE_DIR.exists():
        return 0
    removed = 0
    for item in IMAGE_CACHE_DIR.rglob("*"):
        if item.is_file():
            item.unlink(missing_ok=True)
            removed += 1
    return removed


def vacuum_database() -> None:
    import sqlite3

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("VACUUM")
        conn.commit()
    finally:
        conn.close()


def setup_logging() -> Path:
    import logging

    from config import DATA_DIR

    folder = DATA_DIR / "logs"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "app.log"
    logging.basicConfig(
        filename=str(path),
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        encoding="utf-8",
    )

    def _hook(exc_type, exc, tb):
        logging.exception("unhandled", exc_info=(exc_type, exc, tb))
        sys.__excepthook__(exc_type, exc, tb)

    sys.excepthook = _hook
    return path


def acquire_single_instance():
    from PySide6.QtCore import QLockFile

    from config import DATA_DIR

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    lock = QLockFile(str(DATA_DIR / "younews.lock"))
    lock.setStaleLockTime(10_000)
    if not lock.tryLock(100):
        return None
    return lock


def is_source_stale(last_fetch_at: str | None, minutes: int) -> bool:
    if not last_fetch_at or minutes <= 0:
        return True
    stamp = None
    try:
        stamp = datetime.fromisoformat(last_fetch_at.replace("Z", "+00:00"))
    except ValueError:
        return True
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    age = (datetime.now(timezone.utc) - stamp).total_seconds()
    return age >= minutes * 60


def source_is_muted(muted_until: str | None) -> bool:
    if not muted_until:
        return False
    try:
        stamp = datetime.fromisoformat(muted_until.replace("Z", "+00:00"))
    except ValueError:
        return False
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    return stamp > datetime.now(timezone.utc)


def quiet_hours_active(start_hour: int, end_hour: int, now: datetime | None = None) -> bool:
    if start_hour < 0 or end_hour < 0:
        return False
    hour = (now or datetime.now()).hour
    if start_hour == end_hour:
        return False
    if start_hour < end_hour:
        return start_hour <= hour < end_hour
    return hour >= start_hour or hour < end_hour


def local_search_score(query: str, title: str, body: str) -> int:
    tokens = search_tokens(query)
    if not tokens:
        return 0
    hay = f"{title} {body}".casefold()
    return sum(hay.count(token.casefold()) for token in tokens)


def source_domain(url: str) -> str:
    return (urlparse(url or "").netloc or "").removeprefix("www.")


def briefing_markdown(title: str, body: str) -> str:
    return f"# {title}\n\n{body}\n"


def humanize_source_error(raw: str, i18n=None) -> str:
    """Turn httpx/feedparser noise into a short customer-facing line."""
    text = (raw or "").strip()
    low = text.lower()

    def t(key: str, default: str) -> str:
        if i18n is None:
            return default
        return i18n.t(key, default)

    if not text:
        return t("sources.error_generic", "Could not fetch this source.")
    if "timed out" in low or "timeout" in low:
        return t("sources.error_timeout", "Timed out — the site did not answer in time.")
    if "name or service not known" in low or "getaddrinfo" in low or "nodename" in low:
        return t("sources.error_dns", "Could not find that host. Check the URL.")
    if "ssl" in low or "certificate" in low:
        return t("sources.error_ssl", "Secure connection failed. Check the URL or try later.")
    if "not well-formed" in low or ("syntax error" in low) or ("xml" in low and "parse" in low):
        return t("sources.error_parse", "The feed could not be read. It may not be a valid RSS/Atom URL.")
    match = re.search(r"\b([45]\d{2})\b", text)
    if match and ("http" in low or "status" in low or "client error" in low or "server error" in low):
        return t("sources.error_http", "The site returned an error (HTTP {code}).").replace(
            "{code}", match.group(1)
        )
    if len(text) > 160:
        text = text[:157].rstrip() + "…"
    return text


def latest_github_release(repo: str) -> str:
    cleaned = (repo or "").strip().strip("/")
    if cleaned.count("/") != 1:
        return ""
    import httpx

    url = f"https://api.github.com/repos/{cleaned}/releases/latest"
    try:
        with httpx.Client(timeout=8.0, headers={"User-Agent": RSS_USER_AGENT}, **httpx_proxy_kwargs()) as client:
            response = client.get(url)
            if response.status_code != 200:
                return ""
            payload = response.json()
    except Exception:
        return ""
    return str(payload.get("tag_name") or payload.get("name") or "").lstrip("v")


def fetch_page_html(url: str) -> str:
    """Readable article HTML for the in-app reader (not the raw page)."""
    if not (url or "").startswith("http"):
        return ""
    from html import escape
    from urllib.parse import urljoin

    import httpx
    from bs4 import BeautifulSoup

    headers = {
        "User-Agent": RSS_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en,tr;q=0.9",
    }
    with httpx.Client(headers=headers, follow_redirects=True, timeout=25.0, **httpx_proxy_kwargs()) as client:
        response = client.get(url)
        response.raise_for_status()
    soup = BeautifulSoup(response.content, "lxml")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form", "iframe", "noscript", "svg", "button"]):
        tag.decompose()
    root = (
        soup.find("article")
        or soup.find("main")
        or soup.find(attrs={"role": "main"})
        or soup.find(class_=lambda value: bool(value) and "article" in str(value).lower())
        or soup.body
    )
    if root is None:
        return ""
    title = ""
    if soup.title:
        title = soup.title.get_text(" ", strip=True)
    heading_node = root.find("h1")
    heading = heading_node.get_text(" ", strip=True) if heading_node else title
    chunks: list[str] = []
    if heading:
        chunks.append(f"<h1>{escape(heading)}</h1>")
    chunks.append(f'<p><a href="{escape(url, quote=True)}">{escape(url)}</a></p>')
    seen: set[str] = set()
    for node in root.find_all(["h2", "h3", "p", "li", "blockquote", "img", "figcaption"]):
        if node.name == "img":
            src = (node.get("src") or node.get("data-src") or node.get("data-original") or "").strip()
            if src.startswith("data:"):
                continue
            if src:
                abs_src = urljoin(url, src)
                if abs_src not in seen:
                    seen.add(abs_src)
                    alt = escape(node.get("alt") or "")
                    chunks.append(f'<p><img src="{escape(abs_src, quote=True)}" alt="{alt}" /></p>')
            continue
        text = node.get_text(" ", strip=True)
        if len(text) < 25:
            continue
        key = text[:120]
        if key in seen:
            continue
        seen.add(key)
        safe = escape(text)
        if node.name in {"h2", "h3"}:
            chunks.append(f"<{node.name}>{safe}</{node.name}>")
        elif node.name == "li":
            chunks.append(f"<p>• {safe}</p>")
        elif node.name == "blockquote":
            chunks.append(f"<blockquote><p>{safe}</p></blockquote>")
        else:
            chunks.append(f"<p>{safe}</p>")
    html = "\n".join(chunks)
    plain = BeautifulSoup(html, "lxml").get_text(" ", strip=True)
    if len(plain) < 80:
        fallback = fetch_full_text(url)
        if not fallback:
            return ""
        paras = "".join(f"<p>{escape(part)}</p>" for part in fallback.split("\n\n") if part.strip())
        return f"<h1>{escape(heading or url)}</h1><p><a href=\"{escape(url, quote=True)}\">{escape(url)}</a></p>{paras}"
    return html[:400000]
