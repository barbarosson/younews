"""Background QThread workers so the UI stays responsive."""

from __future__ import annotations

import asyncio
import json

from PySide6.QtCore import QThread, Signal

from core.ai_engine import analyze_article, analyze_briefing, translate_article, translate_headline
from core.chat_engine import answer_news_chat
from core.rss_engine import refresh_all_rss
from core.scraper_engine import refresh_scrapers
from database.db import Database
from config import BRIEFING_ARTICLE_LIMIT, BRIEFING_HOURS_DEFAULT


class FeedRefreshWorker(QThread):
    finished_ok = Signal(int)
    failed = Signal(str)

    def __init__(self, db: Database, parent=None, force: bool = True) -> None:
        super().__init__(parent)
        self._db = db
        self._force = force

    def run(self) -> None:
        try:
            count = asyncio.run(_refresh(self._db, self._force))
            self._db.purge_expired_articles()
            self.finished_ok.emit(count)
        except Exception as exc:
            self.failed.emit(str(exc))


async def _refresh(db: Database, force: bool = True) -> int:
    rss = await refresh_all_rss(db, force=force)
    scraped = await refresh_scrapers(db, force=force)
    return rss + scraped


class AiWorker(QThread):
    finished_ok = Signal(int, str, str)
    failed = Signal(str)

    def __init__(self, db: Database, article_id: int, language_name: str, parent=None) -> None:
        super().__init__(parent)
        self._db = db
        self._article_id = article_id
        self._language_name = language_name

    def run(self) -> None:
        try:
            article = self._db.get_article(self._article_id)
            if article is None:
                raise RuntimeError("Article not found")
            summary, sentiment = analyze_article(
                self._db,
                article.title,
                article.content or "",
                self._language_name,
            )
            self._db.save_ai_result(self._article_id, summary, sentiment)
            self.finished_ok.emit(self._article_id, summary, sentiment)
        except Exception as exc:
            self.failed.emit(str(exc))


class TranslateWorker(QThread):
    finished_ok = Signal(int)
    failed = Signal(str)

    def __init__(
        self,
        db: Database,
        article_id: int,
        language_name: str,
        language_code: str,
        parent=None,
        title_only: bool = False,
    ) -> None:
        super().__init__(parent)
        self._db = db
        self._article_id = article_id
        self._language_name = language_name
        self._language_code = language_code
        self._title_only = title_only

    def run(self) -> None:
        try:
            article = self._db.get_article(self._article_id)
            if article is None:
                raise RuntimeError("Article not found")
            if self._title_only:
                title = translate_headline(self._db, article.title, self._language_name)
                body = ""
            else:
                title, body = translate_article(
                    self._db,
                    article.title,
                    article.content or "",
                    self._language_name,
                )
            payload = json.dumps({"title": title, "body": body}, ensure_ascii=False)
            self._db.save_translation(self._article_id, payload, self._language_code)
            self.finished_ok.emit(self._article_id)
        except Exception as exc:
            self.failed.emit(str(exc))


class BriefingWorker(QThread):
    finished_ok = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        db: Database,
        *,
        language_name: str,
        module_id: str | None,
        module_name: str,
        hours: int = BRIEFING_HOURS_DEFAULT,
        article_ids: list[int] | None = None,
        topic_ids: list[str] | None = None,
        saved_only: bool = False,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._db = db
        self._language_name = language_name
        self._module_id = module_id
        self._module_name = module_name
        self._hours = hours
        self._article_ids = article_ids or []
        self._topic_ids = list(topic_ids) if topic_ids is not None else None
        self._saved_only = saved_only

    def run(self) -> None:
        try:
            if self._article_ids:
                articles = self._db.get_articles_by_ids(self._article_ids)
                hours = 0
            else:
                articles = self._db.list_articles_since(
                    self._module_id,
                    self._hours,
                    BRIEFING_ARTICLE_LIMIT,
                    topic_ids=self._topic_ids,
                    saved_only=self._saved_only,
                )
                hours = self._hours
            if not articles:
                raise RuntimeError("empty_briefing_window")
            summary, sentiment, takeaways = analyze_briefing(
                self._db,
                articles,
                self._language_name,
                self._module_name,
                hours or self._hours,
            )
            self.finished_ok.emit(
                {
                    "summary": summary,
                    "sentiment": sentiment,
                    "takeaways": takeaways,
                    "count": len(articles),
                    "hours": hours or self._hours,
                    "module_name": self._module_name,
                    "selected": bool(self._article_ids),
                    "headlines": [
                        {
                            "id": article.id,
                            "title": article.title,
                            "source": article.source_name or "",
                            "url": article.link or "",
                        }
                        for article in articles
                    ],
                }
            )
        except Exception as exc:
            self.failed.emit(str(exc))


class ChatWorker(QThread):
    finished_ok = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        db: Database,
        message: str,
        language_name: str,
        history: list[dict[str, str]],
        selected_article_id: int | None,
        date_order: str | None = None,
        module_id: str | None = None,
        topic_id: str | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._db = db
        self._message = message
        self._language_name = language_name
        self._history = list(history)
        self._selected_article_id = selected_article_id
        self._date_order = date_order
        self._module_id = module_id
        self._topic_id = topic_id

    def run(self) -> None:
        try:
            result = answer_news_chat(
                self._db,
                self._message,
                self._language_name,
                history=self._history,
                selected_article_id=self._selected_article_id,
                date_order=self._date_order,
                module_id=self._module_id,
                topic_id=self._topic_id,
            )
            self.finished_ok.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))


class ImagePrefetchWorker(QThread):
    thumbnail_ready = Signal(int, str)
    finished_ok = Signal()

    def __init__(self, db: Database, articles: list, parent=None) -> None:
        super().__init__(parent)
        self._db = db
        self._articles = list(articles)

    def run(self) -> None:
        try:
            from core.image_engine import prefetch_article_images

            prefetch_article_images(
                self._db,
                self._articles,
                on_ready=lambda article_id, path: self.thumbnail_ready.emit(int(article_id), str(path)),
            )
        except Exception:
            pass
        self.finished_ok.emit()


class FullTextWorker(QThread):
    finished_ok = Signal(int)
    failed = Signal(str)

    def __init__(self, db: Database, article_id: int, parent=None) -> None:
        super().__init__(parent)
        self._db = db
        self._article_id = article_id

    def run(self) -> None:
        try:
            from core.app_extras import fetch_full_text

            article = self._db.get_article(self._article_id)
            if article is None or not article.link:
                raise RuntimeError("no_link")
            text = fetch_full_text(article.link)
            if not text:
                raise RuntimeError("empty")
            self._db.update_article_content(self._article_id, text)
            self.finished_ok.emit(self._article_id)
        except Exception as exc:
            self.failed.emit(str(exc))


class PageReadWorker(QThread):
    finished_ok = Signal(str)
    failed = Signal(str)

    def __init__(self, url: str, parent=None) -> None:
        super().__init__(parent)
        self._url = url

    def run(self) -> None:
        try:
            from core.app_extras import fetch_page_html

            html = fetch_page_html(self._url)
            if not (html or "").strip():
                raise RuntimeError("empty")
            self.finished_ok.emit(html)
        except Exception as exc:
            self.failed.emit(str(exc))
