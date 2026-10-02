"""News desk assistant: free advice on outlets + grounded answers from stored headlines."""

from __future__ import annotations

import json
import re
from datetime import datetime

from core.ai_engine import generate_raw
from database.db import Database
from database.models import Article

CHAT_SYSTEM = (
    "You are You News, a news-desk editor. Answer like a normal knowledgeable assistant "
    "whenever the topic is news media, outlets, agencies, countries, beats, markets, "
    "geopolitics, sports, or science/tech. Give opinions and comparisons freely. "
    "You may recommend well-known newspapers and agencies for ANY country or topic "
    "(Argentina, Chile, Nigeria, etc.) even when they are not in a source pack. "
    "Refuse only clearly off-topic asks (recipes, homework, medical advice, unrelated coding, personal life). "
    "Never invent today's headlines, quotes, dates, or article ids — those come only from the catalog. "
    "Never answer Country A with an unrelated Country B pack list. "
    "If a matching source pack exists, mention it and set propose_pack_id so the user can say yes to add feeds. "
    "Only put an RSS URL in the reply if it appears in the source-pack list. "
    "Always reply with compact JSON."
)

_STOP = {
    "the", "and", "for", "with", "that", "this", "from", "what", "about", "show", "tell",
    "please", "open", "link", "summarize", "summary", "news", "latest",
    "bir", "bu", "şu", "ve", "ile", "icin", "için", "nedir", "neler", "hakkinda",
    "hakkında", "goster", "göster", "ac", "aç", "ozet", "özet", "özetle", "ozetle",
    "haber", "haberler", "bana", "olan", "hangi", "nasil", "nasıl",
}

_OUTLET_ADVICE = re.compile(
    r"\b("
    r"öner\w*|oner\w*|suggest|recommend|tavsiye|"
    r"ajans\w*|agenc\w*|haber sitesi|news site|outlet|gazete|"
    r"hangi.*(kaynak|site|ajans)|which.*(source|outlet|agency)|"
    r"kaynak öner|site öner"
    r")\b",
    re.I,
)


def answer_news_chat(
    db: Database,
    message: str,
    language_name: str,
    history: list[dict[str, str]] | None = None,
    selected_article_id: int | None = None,
    date_order: str | None = None,
    module_id: str | None = None,
    topic_id: str | None = None,
    pending: dict | None = None,
    translator=None,
) -> dict:
    text = (message or "").strip()
    selected = db.get_article(selected_article_id) if selected_article_id else None
    imported = _import_urls_from_message(db, text, module_id or "economy_markets", topic_id)
    if translator is not None and not imported:
        from core.desk_steward import handle_desk

        desk = handle_desk(db, text, t=translator, pending=pending)
        if desk.get("handled"):
            return desk

    advice = _is_outlet_advice(text)
    catalog = [] if advice else _retrieve(db, text, selected, date_order=date_order)
    if not advice and selected and selected not in catalog:
        catalog = [selected] + catalog
    allowed_ids = {article.id for article in catalog}
    allowed_urls = {str(article.link).strip() for article in catalog if article.link}

    prompt = _build_prompt(
        text,
        language_name,
        catalog,
        history or [],
        selected,
        imported,
        outlet_advice=advice,
    )
    raw = generate_raw(db, prompt, timeout=90.0, system=CHAT_SYSTEM)
    parsed = _parse_chat_json(raw)
    in_scope = bool(parsed.get("in_scope", True)) or bool(imported) or advice
    reply = str(parsed.get("reply") or "").strip()
    if not in_scope:
        return {
            "in_scope": False,
            "reply": reply,
            "article_ids": [],
            "open_article_id": None,
            "open_url": None,
            "summarize_article_id": None,
            "suggestions": _clean_suggestions(parsed.get("suggestions")),
            "imported_sources": [],
        }

    article_ids = _filter_ids(parsed.get("article_ids"), allowed_ids)
    if not article_ids and not advice:
        article_ids = [article.id for article in catalog[:12]]
    open_id = _as_int(parsed.get("open_article_id"))
    if open_id not in allowed_ids:
        open_id = None
    summarize_id = _as_int(parsed.get("summarize_article_id"))
    if summarize_id not in allowed_ids:
        summarize_id = None
    if summarize_id is None and selected and _wants_summary(text):
        summarize_id = selected.id
    open_url = str(parsed.get("open_url") or "").strip()
    if open_url not in allowed_urls:
        if _wants_open(text) and selected and selected.link:
            open_url = selected.link
        else:
            open_url = None
    if open_id is None and _wants_open(text) and selected:
        open_id = selected.id

    pending_out = None
    pack_id = _safe_pack_id(parsed.get("propose_pack_id"))
    if pack_id and translator is not None:
        from core.desk_steward import propose_pack_pending

        pending_out = propose_pack_pending(pack_id)
        if advice and pack_id:
            hint = translator("chat.confirm_hint")
            if hint and hint not in reply:
                reply = f"{reply}\n\n{hint}".strip()

    return {
        "in_scope": True,
        "reply": reply,
        "article_ids": article_ids,
        "open_article_id": open_id,
        "open_url": open_url,
        "summarize_article_id": summarize_id,
        "suggestions": _clean_suggestions(parsed.get("suggestions")),
        "imported_sources": imported,
        "pending": pending_out,
    }


def _is_outlet_advice(message: str) -> bool:
    return bool(_OUTLET_ADVICE.search(message or ""))


def _safe_pack_id(value: object) -> str | None:
    from core.source_packs import SOURCE_PACKS

    pack_id = str(value or "").strip().lower()
    return pack_id if pack_id in SOURCE_PACKS else None


def _extract_urls(message: str) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for match in re.findall(r"https?://[^\s<>\"')\]]+", message or "", flags=re.I):
        url = match.rstrip(".,;:!?")
        key = url.rstrip("/").lower()
        if key in seen:
            continue
        seen.add(key)
        found.append(url)
        if len(found) >= 2:
            break
    return found


def _import_urls_from_message(
    db: Database,
    message: str,
    module_id: str,
    topic_id: str | None,
) -> list[dict]:
    from core.source_probe import import_news_feed

    imported: list[dict] = []
    for url in _extract_urls(message):
        imported.append(import_news_feed(db, url, module_id, topic_id))
    return imported


def _retrieve(
    db: Database,
    message: str,
    selected: Article | None,
    date_order: str | None = None,
) -> list[Article]:
    found: list[Article] = []
    seen: set[int] = set()

    def add(articles: list[Article]) -> None:
        for article in articles:
            if article.id in seen:
                continue
            seen.add(article.id)
            found.append(article)

    if selected:
        add([selected])
    terms = _query_terms(message)
    if terms:
        add(db.list_articles_matching(terms, limit=24, date_order=date_order))
    if len(found) < 6 and message.strip():
        add(db.list_articles(None, message.strip(), date_order=date_order)[:20])
    if len(found) < 4:
        add(db.list_articles(None, "", date_order=date_order)[:12])
    from core.app_extras import local_search_score

    found.sort(
        key=lambda article: local_search_score(message, article.title, article.content or ""),
        reverse=True,
    )
    return found[:18]


def _query_terms(message: str) -> list[str]:
    tokens = re.findall(r"[A-Za-zÀ-ÿÇĞİÖŞÜçğıöşü0-9]{3,}", message or "")
    terms: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        key = token.casefold()
        if key in _STOP or key in seen:
            continue
        seen.add(key)
        terms.append(token)
    return terms[:12]


def _build_prompt(
    message: str,
    language_name: str,
    catalog: list[Article],
    history: list[dict[str, str]],
    selected: Article | None,
    imported: list[dict] | None = None,
    *,
    outlet_advice: bool = False,
) -> str:
    lines = []
    for article in catalog:
        when = ""
        if article.pub_date:
            instant = article.pub_date
            if isinstance(instant, datetime):
                when = instant.strftime("%Y-%m-%d")
        snippet = re.sub(r"\s+", " ", (article.content or "")[:280]).strip()
        lines.append(
            f"- id={article.id} | {article.source_name or 'Source'} | {when} | "
            f"{article.title} | url={article.link or ''} | {snippet}"
        )
    catalog_text = "\n".join(lines) if lines else "(no matching stored articles)"
    hist = []
    for item in history[-8:]:
        role = "User" if item.get("role") == "user" else "Assistant"
        hist.append(f"{role}: {item.get('text', '')[:800]}")
    history_text = "\n".join(hist) if hist else "(none)"
    selected_line = "none"
    if selected:
        selected_line = f"id={selected.id} title={selected.title} url={selected.link or ''}"
    import_lines = []
    for item in imported or []:
        import_lines.append(
            f"- {item.get('status')} | {item.get('name')} | {item.get('url')} | "
            f"headlines={item.get('count')} | error={item.get('error') or 'none'}"
        )
    import_text = "\n".join(import_lines) if import_lines else "(none)"
    from core.source_packs import SOURCE_PACKS

    pack_lines = []
    for pack_id, items in SOURCE_PACKS.items():
        names = ", ".join(name for _m, _t, name, _u in items)
        pack_lines.append(f"- {pack_id}: {names}")
    packs_text = "\n".join(pack_lines)
    mode = (
        "MODE: outlet recommendation. Answer like a standard AI news editor. "
        "Recommend concrete newspapers/agencies for the country or beat the user named. "
        "Explain briefly why. If a pack id matches that country/topic, set propose_pack_id to that id "
        "and invite the user to say yes so feeds are added. Leave article_ids empty. "
        "Do not refuse for lack of a pack. Do not list an unrelated country.\n"
        if outlet_advice
        else "MODE: news Q&A from the catalog when possible; still answer media questions freely.\n"
    )
    return (
        f"Write reply in {language_name}.\n"
        f"{mode}"
        "Return JSON only with keys:\n"
        "- in_scope: boolean (true for any news/media/outlet question)\n"
        "- reply: direct useful answer\n"
        "- article_ids: catalog ids to show (empty for pure outlet advice)\n"
        "- open_article_id: catalog id or null\n"
        "- open_url: exact catalog url or null\n"
        "- summarize_article_id: catalog id or null\n"
        "- propose_pack_id: pack id from the list if the user should be offered that pack, else null\n"
        "- suggestions: 3 short follow-ups\n\n"
        f"Selected story: {selected_line}\n\n"
        f"Imported feeds:\n{import_text}\n\n"
        f"Source packs (only these can be one-click added):\n{packs_text}\n\n"
        f"Recent chat:\n{history_text}\n\n"
        f"Catalog:\n{catalog_text}\n\n"
        f"User: {message}"
    )


def _parse_chat_json(text: str) -> dict:
    cleaned = (text or "").strip()
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not match:
        return {"in_scope": True, "reply": cleaned, "article_ids": [], "suggestions": []}
    try:
        payload = json.loads(match.group(0))
    except json.JSONDecodeError:
        return {"in_scope": True, "reply": cleaned, "article_ids": [], "suggestions": []}
    return payload if isinstance(payload, dict) else {}


def _filter_ids(value: object, allowed: set[int]) -> list[int]:
    if not isinstance(value, list):
        return []
    ids: list[int] = []
    for item in value:
        number = _as_int(item)
        if number in allowed and number not in ids:
            ids.append(number)
    return ids


def _as_int(value: object) -> int | None:
    try:
        number = int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _clean_suggestions(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    items: list[str] = []
    for item in value:
        text = str(item).strip()
        if text and text not in items:
            items.append(text)
        if len(items) >= 4:
            break
    return items


def _wants_summary(message: str) -> bool:
    return bool(re.search(r"\b(summarize|summary|özet|ozet|résume|resume|zusammenfass)\b", message, re.I))


def _wants_open(message: str) -> bool:
    return bool(re.search(r"\b(open|link|url|aç|ac|açıl|browser|tarayıcı)\b", message, re.I))
