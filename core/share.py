"""Share a headline to social apps, messengers, email, or the clipboard."""

from __future__ import annotations

from urllib.parse import quote

from config import APP_NAME, APP_PROMO_URL, APP_VERSION
from core.i18n_manager import I18nManager
from database.models import Article


def briefing_as_article(payload: dict, i18n: I18nManager) -> Article:
    hours = int(payload.get("hours") or 0)
    count = int(payload.get("count") or 0)
    module_name = str(payload.get("module_name") or "")
    if payload.get("selected"):
        title = i18n.t("ai.briefing_selected_title").replace("{count}", str(count))
    else:
        title = (
            i18n.t("ai.briefing_title")
            .replace("{hours}", str(hours))
            .replace("{module}", module_name)
        )
    summary = str(payload.get("summary") or "").strip()
    link = ""
    for item in payload.get("headlines") or []:
        if isinstance(item, dict):
            url = str(item.get("url") or "").strip()
            if url.startswith("http"):
                link = url
                break
    return Article(
        id=0,
        source_id=None,
        title=title,
        content=summary,
        link=link or None,
        pub_date=None,
        category=None,
        ai_summary=summary or None,
        sentiment=None,
        is_read=True,
        created_at=None,
        source_name=APP_NAME,
    )

TARGETS: tuple[tuple[str, str], ...] = (
    ("whatsapp", "share.whatsapp"),
    ("telegram", "share.telegram"),
    ("x", "share.x"),
    ("facebook", "share.facebook"),
    ("linkedin", "share.linkedin"),
    ("reddit", "share.reddit"),
    ("email", "share.email"),
    ("sms", "share.sms"),
    ("copy", "share.copy"),
)

_MAX_CHARS = 3500


def promo_line(i18n: I18nManager) -> str:
    line = i18n.t("share.promo")
    if APP_PROMO_URL:
        return f"{line} {APP_PROMO_URL}"
    return line


def share_text(article: Article, i18n: I18nManager) -> str:
    title = (article.title or "").strip()
    link = (article.link or "").strip()
    source = (article.source_name or "").strip()
    extra = (article.ai_summary or article.content or "").strip()
    if extra:
        extra = extra.replace("\n", " ").strip()
        if len(extra) > 280:
            extra = extra[:277].rstrip() + "…"
    parts = [title]
    if source:
        parts.append(source)
    if extra and extra != title:
        parts.append(extra)
    if link:
        parts.append(link)
    parts.append("")
    parts.append(promo_line(i18n))
    parts.append(
        i18n.t("share.tag").replace("{app}", APP_NAME).replace("{version}", APP_VERSION)
    )
    text = "\n".join(part for part in parts if part)
    if len(text) > _MAX_CHARS:
        return text[: _MAX_CHARS - 1].rstrip() + "…"
    return text


def share_url(target: str, text: str, *, link: str = "", title: str = "") -> str:
    encoded = quote(text, safe="")
    encoded_url = quote(link, safe="") if link else ""
    encoded_title = quote((title or APP_NAME)[:200], safe="")
    if target == "whatsapp":
        return f"https://wa.me/?text={encoded}"
    if target == "telegram":
        if link:
            caption = text.replace(link, "").strip()
            return f"https://t.me/share/url?url={encoded_url}&text={quote(caption, safe='')}"
        return f"https://t.me/share/url?url={encoded}"
    if target == "x":
        return f"https://twitter.com/intent/tweet?text={encoded}"
    if target == "facebook":
        if link:
            return f"https://www.facebook.com/sharer/sharer.php?u={encoded_url}&quote={encoded}"
        return f"https://www.facebook.com/sharer/sharer.php?u={encoded}"
    if target == "linkedin":
        if link:
            return f"https://www.linkedin.com/sharing/share-offsite/?url={encoded_url}"
        return f"https://www.linkedin.com/sharing/share-offsite/?url={encoded}"
    if target == "reddit":
        if link:
            return f"https://www.reddit.com/submit?url={encoded_url}&title={encoded_title}"
        return f"https://www.reddit.com/submit?title={encoded_title}&text={encoded}"
    if target == "email":
        return f"mailto:?subject={encoded_title}&body={encoded}"
    if target == "sms":
        return f"sms:?body={encoded}"
    return ""


def open_share(target: str, text: str, *, link: str = "", title: str = "") -> str:
    if target == "copy":
        from PySide6.QtGui import QGuiApplication

        clip = QGuiApplication.clipboard()
        if clip is not None:
            clip.setText(text)
        return "copied"
    url = share_url(target, text, link=link, title=title)
    if url:
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        QDesktopServices.openUrl(QUrl(url))
        return "opened"
    return ""
