import unittest
from datetime import datetime, timedelta, timezone

from core.app_extras import (
    local_search_score,
    looks_like_paywall,
    normalize_headline,
    quiet_hours_active,
    relative_time,
    sanitize_article_html,
    source_is_muted,
)
from database.taxonomy import TAXONOMY_VERSION
from core.share import share_url
from core.rss_engine import _looks_like_html


class SmokeTests(unittest.TestCase):
    def test_headline_normalize(self) -> None:
        self.assertEqual(normalize_headline("Hello!!  World"), normalize_headline("hello world"))

    def test_relative_time(self) -> None:
        now = datetime.now(timezone.utc)
        self.assertTrue(relative_time(now - timedelta(minutes=3), now).endswith("m"))

    def test_paywall_and_search(self) -> None:
        self.assertTrue(looks_like_paywall("Subscribe to continue reading"))
        self.assertGreaterEqual(local_search_score("oil prices", "Oil prices rise", "Brent crude"), 1)

    def test_quiet_and_mute(self) -> None:
        noon = datetime(2026, 1, 1, 12, 0, 0)
        self.assertFalse(quiet_hours_active(22, 7, noon))
        self.assertFalse(source_is_muted(None))

    def test_taxonomy_version(self) -> None:
        self.assertGreaterEqual(int(TAXONOMY_VERSION), 1)

    def test_share_urls(self) -> None:
        text = "Headline\nhttps://example.com/story\nYou News"
        url = share_url("whatsapp", text, link="https://example.com/story", title="Headline")
        self.assertIn("wa.me", url)
        self.assertIn("telegram", share_url("telegram", text, link="https://example.com/story", title="Headline"))
        self.assertIn("twitter.com", share_url("x", text, link="https://example.com/story", title="Headline"))
        self.assertTrue(share_url("email", text, link="https://example.com/story", title="Headline").startswith("mailto:"))

    def test_html_is_not_rss(self) -> None:
        self.assertTrue(_looks_like_html(b"<!DOCTYPE html><html><body>news</body></html>"))
        self.assertFalse(_looks_like_html(b"<?xml version='1.0'?><rss><channel></channel></rss>"))

    def test_sanitize_escaped_rss_html(self) -> None:
        raw = (
            "&lt;p class=&quot;isSelectedEnd&quot;&gt;US officials held talks"
            " in Oman.&amp;nbsp;Reuters reported.&lt;/p&gt;"
        )
        html = sanitize_article_html(raw)
        self.assertNotIn("&lt;", html)
        self.assertNotIn("isSelectedEnd", html)
        self.assertNotIn("&nbsp;", html)
        self.assertIn("US officials held talks", html)
        self.assertIn("<p>", html)


if __name__ == "__main__":
    unittest.main()
