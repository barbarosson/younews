"""Unified BYOK client for OpenAI, Anthropic, Gemini, Groq, and local Ollama."""

from __future__ import annotations

import json
import re
from urllib.parse import quote

import httpx
from openai import OpenAI

from config import (
    DEFAULT_AI_MODELS,
    DEFAULT_OLLAMA_URL,
    get_provider_api_key,
    normalize_ai_provider,
    provider_model_setting_key,
)
from database.db import Database

JSON_SYSTEM = "You are a financial news analyst. Always reply with compact JSON."
ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"
GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"
GEMINI_GENERATE_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

SENTIMENT_VALUES = ("bullish/positive", "bearish/negative", "neutral")


def _build_prompt(article_title: str, article_body: str, language_name: str) -> str:
    body = (article_body or "")[:6000]
    return (
        f"Summarize the following article in 2 concise sentences in {language_name} "
        "and classify market sentiment as (bullish/positive, bearish/negative, neutral).\n"
        "Return JSON only with keys summary and sentiment.\n\n"
        f"Title: {article_title}\n\n{body}"
    )


def _parse_result(text: str) -> tuple[str, str]:
    cleaned = text.strip()
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        try:
            payload = json.loads(match.group(0))
            summary = str(payload.get("summary") or cleaned)
            sentiment = str(payload.get("sentiment") or "neutral")
            if sentiment not in SENTIMENT_VALUES:
                sentiment = "neutral"
            return summary, sentiment
        except json.JSONDecodeError:
            pass
    lowered = cleaned.lower()
    sentiment = "neutral"
    if "bearish" in lowered or "negative" in lowered:
        sentiment = "bearish/negative"
    elif "bullish" in lowered or "positive" in lowered:
        sentiment = "bullish/positive"
    return cleaned, sentiment


def analyze_article(db: Database, title: str, body: str, language_name: str) -> tuple[str, str]:
    return _parse_result(_generate_raw(db, _build_prompt(title, body, language_name)))


def translate_headline(db: Database, title: str, target_language_name: str) -> str:
    prompt = (
        f"Translate this news headline into {target_language_name}.\n"
        "Return JSON only with key title. Do not add commentary.\n"
        "Keep names, numbers, and tickers unchanged.\n\n"
        f"Headline: {title}"
    )
    raw = _generate_raw(db, prompt, timeout=40.0)
    translated, _body = _parse_translation(raw, title, "")
    return translated or title


def translate_article(db: Database, title: str, body: str, target_language_name: str) -> tuple[str, str]:
    snippet = (body or "")[:8000]
    prompt = (
        f"Translate the following news article into {target_language_name}.\n"
        "Return JSON only with keys title and body.\n"
        "If the article is already in that language, still return a clean, readable title and body "
        "in the same language without inventing facts.\n"
        "Preserve meaning, numbers, names, and ticker symbols. Use plain text paragraphs in body.\n\n"
        f"Title: {title}\n\n{snippet}"
    )
    raw = _generate_raw(db, prompt, timeout=90.0)
    return _parse_translation(raw, title, body)


def _parse_translation(text: str, fallback_title: str, fallback_body: str) -> tuple[str, str]:
    cleaned = text.strip()
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        try:
            payload = json.loads(match.group(0))
            translated_title = str(
                payload.get("title") or payload.get("translated_title") or fallback_title
            ).strip()
            translated_body = str(
                payload.get("body") or payload.get("translated_body") or payload.get("text") or ""
            ).strip()
            if translated_title and translated_body:
                return translated_title, translated_body
            if translated_title:
                return translated_title, (fallback_body or "").strip()
        except json.JSONDecodeError:
            pass
    return fallback_title, cleaned or (fallback_body or "")


def analyze_briefing(
    db: Database,
    articles: list,
    language_name: str,
    module_name: str,
    hours: int,
) -> tuple[str, str, list[str]]:
    lines: list[str] = []
    for index, article in enumerate(articles, start=1):
        snippet = (article.content or "").replace("\n", " ").strip()[:500]
        source = article.source_name or "Unknown"
        lines.append(f"{index}. [{source}] {article.title}\n{snippet}")
    bundle = "\n\n".join(lines)[:18000]
    prompt = (
        f"Review these {len(articles)} {module_name} news items from the last {hours} hours. "
        f"Write the briefing in {language_name}.\n"
        "Return JSON only with keys:\n"
        "- summary: 5 to 8 sentences covering themes, risks, and market implications\n"
        "- sentiment: one of bullish/positive, bearish/negative, neutral\n"
        "- takeaways: array of 3 to 5 short bullets\n\n"
        f"{bundle}"
    )
    raw = _generate_raw(db, prompt, timeout=120.0)
    summary, sentiment = _parse_result(raw)
    return summary, sentiment, _extract_takeaways(raw)


def _extract_takeaways(raw: str) -> list[str]:
    match = re.search(r"\{.*\}", raw.strip(), re.DOTALL)
    if not match:
        return []
    try:
        payload = json.loads(match.group(0))
    except json.JSONDecodeError:
        return []
    items = payload.get("takeaways") or []
    if not isinstance(items, list):
        return []
    return [str(item).strip() for item in items if str(item).strip()][:5]


def generate_raw(db: Database, prompt: str, timeout: float = 60.0, system: str | None = None) -> str:
    return _generate_raw(db, prompt, timeout=timeout, system=system)


def _provider_model(db: Database, provider: str) -> str:
    stored = (db.get_setting(provider_model_setting_key(provider)) or "").strip()
    return stored or DEFAULT_AI_MODELS.get(provider, DEFAULT_AI_MODELS["openai"])


def _require_api_key(provider: str) -> str:
    api_key = get_provider_api_key(provider)
    if not api_key:
        raise RuntimeError("missing_api_key")
    return api_key


def _http_error_message(response: httpx.Response) -> str:
    body = (response.text or "").strip().replace("\n", " ")[:300]
    if body:
        return f"HTTP {response.status_code}: {body}"
    return f"HTTP {response.status_code}"


def _post_json(url: str, *, headers: dict[str, str], payload: dict, timeout: float) -> dict:
    with httpx.Client(timeout=timeout) as client:
        response = client.post(url, headers=headers, json=payload)
        if response.status_code >= 400:
            raise RuntimeError(_http_error_message(response))
        data = response.json()
    if not isinstance(data, dict):
        raise RuntimeError("Unexpected AI response")
    return data


def _generate_openai(api_key: str, model: str, prompt: str, system: str, timeout: float) -> str:
    client = OpenAI(api_key=api_key, timeout=timeout)
    response = client.chat.completions.create(
        model=model,
        temperature=0.2,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message.content or ""


def _generate_anthropic(api_key: str, model: str, prompt: str, system: str, timeout: float) -> str:
    data = _post_json(
        ANTHROPIC_MESSAGES_URL,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        payload={
            "model": model,
            "max_tokens": 4096,
            "temperature": 0.2,
            "system": system,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=timeout,
    )
    parts = data.get("content") or []
    texts: list[str] = []
    for part in parts:
        if isinstance(part, dict):
            texts.append(str(part.get("text") or ""))
    return "".join(texts)


def _generate_gemini(api_key: str, model: str, prompt: str, system: str, timeout: float) -> str:
    url = GEMINI_GENERATE_URL.format(model=quote(model, safe=".-_"))
    data = _post_json(
        url,
        headers={
            "x-goog-api-key": api_key,
            "content-type": "application/json",
        },
        payload={
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2},
        },
        timeout=timeout,
    )
    texts: list[str] = []
    for candidate in data.get("candidates") or []:
        if not isinstance(candidate, dict):
            continue
        content = candidate.get("content") or {}
        for part in content.get("parts") or []:
            if isinstance(part, dict):
                texts.append(str(part.get("text") or ""))
    return "".join(texts)


def _generate_openai_compatible(
    url: str, api_key: str, model: str, prompt: str, system: str, timeout: float
) -> str:
    data = _post_json(
        url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "content-type": "application/json",
        },
        payload={
            "model": model,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        },
        timeout=timeout,
    )
    choices = data.get("choices") or []
    if not choices or not isinstance(choices[0], dict):
        return ""
    message = choices[0].get("message") or {}
    return str(message.get("content") or "")


def _generate_ollama(db: Database, model: str, prompt: str, system: str, timeout: float) -> str:
    url = db.get_setting("ollama_url", DEFAULT_OLLAMA_URL) or DEFAULT_OLLAMA_URL
    data = _post_json(
        url,
        headers={"content-type": "application/json"},
        payload={"model": model, "prompt": prompt, "system": system, "stream": False},
        timeout=timeout,
    )
    return str(data.get("response") or "")


def _generate_raw(
    db: Database,
    prompt: str,
    timeout: float = 60.0,
    system: str | None = None,
) -> str:
    provider = normalize_ai_provider(db.get_setting("ai_provider", "openai"))
    model = _provider_model(db, provider)
    system_prompt = system if system is not None else JSON_SYSTEM
    if provider == "ollama":
        return _generate_ollama(db, model, prompt, system_prompt, timeout)
    api_key = _require_api_key(provider)
    if provider == "anthropic":
        return _generate_anthropic(api_key, model, prompt, system_prompt, timeout)
    if provider == "gemini":
        return _generate_gemini(api_key, model, prompt, system_prompt, timeout)
    if provider == "groq":
        return _generate_openai_compatible(
            GROQ_CHAT_URL, api_key, model, prompt, system_prompt, timeout
        )
    return _generate_openai(api_key, model, prompt, system_prompt, timeout)
