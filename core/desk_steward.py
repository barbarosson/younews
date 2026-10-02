"""Desk steward: propose and apply sources, social follows, tickers, and a few settings.

The assistant never invents RSS URLs. It only uses known packs, a pasted URL,
resolved social handles, and the local ticker catalog. Suggestions wait for a
yes; a direct “add/remove X” command applies immediately.
"""

from __future__ import annotations

import re
from typing import Any

from config import SOCIAL_FOLLOW_LIMIT, SOCIAL_MODULE_ID
from core.source_packs import SOURCE_PACKS, apply_source_pack
from core.ticker_catalog import TICKER_CATALOG, _fold, search_catalog
from database.db import Database, DuplicateSourceError

PACK_ALIASES: dict[str, tuple[str, ...]] = {
    "tr": ("tr", "turkiye", "turkiye haberi", "turk", "turkish", "istanbul"),
    "us": ("us", "usa", "abd", "amerika", "american"),
    "eu": ("eu", "avrupa", "europe", "european"),
    "uk": ("uk", "ingiltere", "britain", "british", "london"),
    "de": ("de", "almanya", "germany", "german"),
    "fr": ("fr", "fransa", "france", "french"),
    "jp": ("jp", "japonya", "japan", "japanese"),
    "tech": ("tech", "teknoloji", "technology", "gadget"),
    "science": ("science", "bilim", "uzay", "space"),
    "crypto": ("crypto", "kripto", "bitcoin", "web3"),
    "sport": ("sport", "spor", "football", "futbol"),
    "mastodon": ("mastodon", "newsletter", "bulten"),
}

PACK_TITLE_KEY = {
    "tr": "sources.pack_tr",
    "us": "sources.pack_us",
    "eu": "sources.pack_eu",
    "uk": "sources.pack_uk",
    "de": "sources.pack_de",
    "fr": "sources.pack_fr",
    "jp": "sources.pack_jp",
    "tech": "sources.pack_tech",
    "science": "sources.pack_science",
    "crypto": "sources.pack_crypto",
    "sport": "sources.pack_sport",
    "mastodon": "sources.pack_mastodon",
}

SOCIAL_SUGGESTIONS: tuple[tuple[str, str, str], ...] = (
    ("youtube", "@BBCNews", "BBC News"),
    ("youtube", "@AlJazeeraEnglish", "Al Jazeera English"),
    ("youtube", "@DWNews", "DW News"),
    ("youtube", "@CNBC", "CNBC"),
)

_CONFIRM = re.compile(
    r"\b(evet|yes|ok|okay|tamam|onayla|uygula|kabul|do it|go ahead|ekle bunlari|add them|hepsini ekle)\b",
    re.I,
)
_REJECT = re.compile(r"\b(hayir|hayır|no|iptal|vazgec|vazgeç|cancel|forget)\b", re.I)
_ADD = re.compile(r"\b(ekle|add|follow|takip|seride|şeride|watchlist)\b", re.I)
_REMOVE = re.compile(r"\b(sil|cikar|çıkar|remove|delete|unfollow|birak|bırak|drop)\b", re.I)
_PROPOSE = re.compile(r"\b(oner|öner|suggest|recommend|hangi|what pack|ne ekleyeyim)\b", re.I)
_DESK = re.compile(
    r"\b(kaynak|source|rss|paket|pack|serit|şerit|ticker|sembol|youtube|substack|bluesky|"
    r"takip|follow|sosyal|social|ulke|ülke|dal|branch|feed|besleme)\b",
    re.I,
)
_TAPE_HIDE = re.compile(r"\b(seridi gizle|şeridi gizle|hide tape|hide the tape)\b", re.I)
_TAPE_SHOW = re.compile(r"\b(seridi goster|şeridi göster|show tape|show the tape)\b", re.I)
_REFRESH = re.compile(r"\b(beslemeleri yenile|refresh feeds|yenile)\b", re.I)


def handle_desk(
    db: Database,
    message: str,
    *,
    t,
    pending: dict | None = None,
) -> dict:
    text = (message or "").strip()
    folded = _fold(text)
    if pending and _REJECT.search(folded):
        return _result(t("chat.cancelled"), suggestions=_default_suggestions(t))
    if pending and _is_confirm(folded):
        return _apply(db, pending, t)
    if _TAPE_HIDE.search(folded):
        db.set_setting("hide_tape", "1")
        return _result(t("chat.tape_hidden"), applied={"tickers": True})
    if _TAPE_SHOW.search(folded):
        db.set_setting("hide_tape", "0")
        return _result(t("chat.tape_shown"), applied={"tickers": True})
    if _REFRESH.search(folded) and _DESK.search(folded):
        return _result(t("chat.refresh_queued"), applied={"refresh": True})

    if not _is_desk_intent(folded, pending):
        return {"handled": False}

    pack_id = _detect_pack(folded)
    tickers = _detect_tickers(text) if re.search(r"ticker|sembol|serit|bist|nasdaq|endeks", folded) else []
    sources = _match_sources(db, text) if _REMOVE.search(folded) else []
    follows = _detect_follows(text) if re.search(r"youtube|@|sosyal|social|substack|bluesky|takip", folded) else []
    want_remove = bool(_REMOVE.search(folded))
    want_add = bool(_ADD.search(folded)) and not want_remove
    want_propose = bool(_PROPOSE.search(folded)) or (not want_add and not want_remove)

    if want_remove:
        ops: list[dict] = []
        if pack_id:
            for _module, _topic, name, url in SOURCE_PACKS.get(pack_id, []):
                source = db.find_source_by_url(url)
                if source:
                    ops.append(_remove_op(source))
        for source in sources:
            op = _remove_op(source)
            if op not in ops:
                ops.append(op)
        for item in tickers:
            ops.append({"op": "ticker_remove", "symbol": item.symbol, "label": item.label})
        for platform, handle, label in follows:
            source = _find_follow(db, handle, label)
            if source:
                ops.append(_remove_op(source))
        if not ops:
            return _result(t("chat.no_match"), suggestions=_default_suggestions(t))
        pending_batch = {"ops": ops}
        if want_propose and len(ops) > 1:
            return _propose(pending_batch, t)
        return _apply(db, pending_batch, t)

    ops = []
    if pack_id:
        ops.append({"op": "pack", "id": pack_id})
    for platform, handle, label in follows:
        ops.append({"op": "follow", "platform": platform, "handle": handle, "label": label})
    for item in tickers:
        ops.append({"op": "ticker_add", "symbol": item.symbol, "label": item.label})
    if ops:
        pending_batch = {"ops": ops}
        if want_add and not want_propose:
            return _apply(db, pending_batch, t)
        return _propose(pending_batch, t)

    if "sosyal" in folded or "social" in folded or "youtube" in folded:
        pending_batch = {
            "ops": [
                {"op": "follow", "platform": p, "handle": h, "label": n}
                for p, h, n in SOCIAL_SUGGESTIONS
            ]
        }
        return _propose(pending_batch, t)
    if any(token in folded for token in ("ticker", "sembol", "serit", "bist", "nasdaq")):
        picks = search_catalog(_clean_query(text) or text, limit=6) or list(TICKER_CATALOG[:6])
        pending_batch = {
            "ops": [{"op": "ticker_add", "symbol": item.symbol, "label": item.label} for item in picks[:6]]
        }
        return _propose(pending_batch, t)
    if pack_id:
        return _propose({"ops": [{"op": "pack", "id": pack_id}]}, t)
    return _result(t("chat.desk_ask"), suggestions=_default_suggestions(t))


def _is_desk_intent(folded: str, pending: dict | None) -> bool:
    if pending and (_is_confirm(folded) or _REJECT.search(folded)):
        return True
    if _DESK.search(folded) or _PROPOSE.search(folded) or _ADD.search(folded) or _REMOVE.search(folded):
        return True
    return _detect_pack(folded) is not None


def _is_confirm(folded: str) -> bool:
    return bool(_CONFIRM.search(folded))


def _detect_pack(folded: str) -> str | None:
    for pack_id, aliases in PACK_ALIASES.items():
        for alias in aliases:
            if re.search(rf"\b{re.escape(alias)}\b", folded):
                return pack_id
    return None


_NOISE = re.compile(
    r"\b(ekle|add|sil|cikar|çıkar|remove|delete|oner|öner|suggest|recommend|paket|pack|"
    r"kaynak|source|serit|şerit|seride|şeride|ticker|sembol|symbol|haber|news|lutfen|lütfen)\b",
    re.I,
)


def _clean_query(text: str) -> str:
    return " ".join(_NOISE.sub(" ", text or "").split())


def _detect_tickers(text: str) -> list:
    found = []
    seen: set[str] = set()
    query = _clean_query(text) or text
    for item in search_catalog(query, limit=12):
        tokens = {_fold(item.label), _fold(item.symbol), *(_fold(alias) for alias in item.aliases)}
        hay = _fold(text)
        if any(token and (token == hay or f" {token} " in f" {hay} " or token in hay.split()) for token in tokens):
            if item.symbol.casefold() not in seen:
                seen.add(item.symbol.casefold())
                found.append(item)
    return found[:8]


def _detect_follows(text: str) -> list[tuple[str, str, str]]:
    found: list[tuple[str, str, str]] = []
    for match in re.findall(r"@[\w.-]+", text or ""):
        found.append(("youtube", match, match))
    lowered = (text or "").lower()
    for platform, handle, name in SOCIAL_SUGGESTIONS:
        if handle.lower() in lowered or _fold(name) in _fold(text):
            item = (platform, handle, name)
            if item not in found:
                found.append(item)
    return found[:6]


def _match_sources(db: Database, text: str) -> list:
    hay = _fold(_clean_query(text))
    tokens = [part for part in hay.split() if len(part) >= 3]
    if not tokens:
        return []
    hits = []
    for source in db.list_sources(active_only=False):
        blob = _fold(f"{source.name} {source.url} {source.module_id}")
        if all(token in blob for token in tokens) or any(len(token) >= 4 and token in blob for token in tokens):
            hits.append(source)
    return hits[:12]


def _find_follow(db: Database, handle: str, label: str):
    needle = _fold(handle.lstrip("@") + " " + label)
    for source in db.list_sources(active_only=False):
        if source.module_id != SOCIAL_MODULE_ID:
            continue
        if needle.split()[0] in _fold(source.name + " " + source.url):
            return source
    return None


def _remove_op(source) -> dict:
    return {
        "op": "source_remove",
        "id": source.id,
        "name": source.name,
        "deactivate": not bool(getattr(source, "user_added", False)),
    }


def _propose(pending: dict, t) -> dict:
    lines = [t("chat.propose_intro")]
    for op in pending.get("ops") or []:
        lines.append(f"• {_op_label(op, t)}")
    lines.append(t("chat.confirm_hint"))
    return _result(
        "\n".join(lines),
        pending=pending,
        suggestions=[t("chat.suggest_yes"), t("chat.suggest_no"), t("chat.suggest_pack")],
    )


def _apply(db: Database, pending: dict, t) -> dict:
    notes: list[str] = []
    applied = {"sources": False, "tickers": False, "refresh": False}
    for op in pending.get("ops") or []:
        kind = op.get("op")
        if kind == "pack":
            added = apply_source_pack(db, str(op.get("id") or ""))
            title = t(PACK_TITLE_KEY.get(op.get("id"), ""), str(op.get("id") or ""))
            notes.append(t("chat.applied_pack").replace("{name}", title).replace("{count}", str(added)))
            applied["sources"] = True
            applied["refresh"] = True
        elif kind == "follow":
            notes.append(_add_follow(db, str(op.get("platform") or "youtube"), str(op.get("handle") or ""), t))
            applied["sources"] = True
            applied["refresh"] = True
        elif kind == "ticker_add":
            symbol = str(op.get("symbol") or "")
            label = str(op.get("label") or symbol)
            if db.add_ticker(symbol, label):
                notes.append(t("chat.added_ticker").replace("{name}", label))
            else:
                notes.append(t("chat.ticker_duplicate").replace("{name}", label))
            applied["tickers"] = True
        elif kind == "ticker_remove":
            symbol = str(op.get("symbol") or "")
            label = str(op.get("label") or symbol)
            db.remove_ticker_symbol(symbol)
            notes.append(t("chat.removed_ticker").replace("{name}", label))
            applied["tickers"] = True
        elif kind == "source_remove":
            source = db.get_source(int(op["id"]))
            name = str(op.get("name") or (source.name if source else op["id"]))
            if op.get("deactivate") and source:
                db.set_source_active(source.id, False)
                notes.append(t("chat.deactivated_source").replace("{name}", name))
            elif source and db.delete_user_source(source.id):
                notes.append(t("chat.removed_source").replace("{name}", name))
            else:
                notes.append(t("chat.cannot_remove").replace("{name}", name))
            applied["sources"] = True
            applied["refresh"] = True
    return _result("\n".join(notes) or t("chat.nothing_pending"), applied=applied, suggestions=_default_suggestions(t))


def _add_follow(db: Database, platform: str, handle: str, t) -> str:
    from core.social_resolve import SocialResolveError, resolve_follow

    used = sum(
        1
        for source in db.list_sources(active_only=False)
        if source.module_id == SOCIAL_MODULE_ID and source.user_added
    )
    if used >= SOCIAL_FOLLOW_LIMIT:
        return t("social.limit_reached")
    try:
        resolved = resolve_follow(platform, handle)
    except SocialResolveError as exc:
        return t(f"social.error.{exc.code}", t("social.error.not_found")).replace("{name}", handle)
    except Exception as exc:
        return t("chat.source_failed").replace("{name}", handle).replace("{error}", str(exc))
    try:
        db.add_user_source(
            name=resolved.name,
            url=resolved.feed_url,
            module_id=SOCIAL_MODULE_ID,
            is_rss=True,
            topic_id=resolved.topic_id,
        )
    except DuplicateSourceError:
        return t("chat.source_duplicate").replace("{name}", resolved.name).replace("{count}", "0")
    return t("chat.added_follow").replace("{name}", resolved.name)


def _op_label(op: dict, t) -> str:
    kind = op.get("op")
    if kind == "pack":
        return t(PACK_TITLE_KEY.get(op.get("id"), ""), str(op.get("id") or ""))
    if kind == "follow":
        return f"{op.get('label') or op.get('handle')} ({op.get('platform')})"
    if kind in {"ticker_add", "ticker_remove"}:
        prefix = "− " if kind == "ticker_remove" else ""
        return f"{prefix}{op.get('label') or op.get('symbol')}"
    if kind == "source_remove":
        return f"− {op.get('name')}"
    return str(kind)


def _default_suggestions(t) -> list[str]:
    return [
        t("chat.suggest_pack"),
        t("chat.suggest_topic"),
        t("chat.suggest_social"),
        t("chat.suggest_tickers"),
    ]


def _result(
    reply: str,
    *,
    pending: dict | None = None,
    applied: dict | None = None,
    suggestions: list[str] | None = None,
) -> dict:
    return {
        "handled": True,
        "in_scope": True,
        "reply": reply,
        "article_ids": [],
        "open_article_id": None,
        "open_url": None,
        "summarize_article_id": None,
        "suggestions": suggestions or [],
        "imported_sources": [],
        "pending": pending,
        "applied": applied or {},
    }
