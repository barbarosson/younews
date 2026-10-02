import os
import tempfile
import unittest
from pathlib import Path


class DeskStewardTests(unittest.TestCase):
    def setUp(self) -> None:
        self._home = tempfile.mkdtemp(prefix="yn_desk_")
        os.environ["YOU_NEWS_HOME"] = self._home
        os.environ["GNT_SKIP_NETWORK"] = "1"
        from database.db import Database
        from core.desk_steward import handle_desk

        self.db = Database()
        self.handle = handle_desk
        self.en = self._dict("en")

    def tearDown(self) -> None:
        os.environ.pop("YOU_NEWS_HOME", None)

    def _dict(self, code: str):
        import json
        from config import LOCALES_DIR

        data = json.loads((LOCALES_DIR / f"{code}.json").read_text(encoding="utf-8"))
        return lambda key, default=None: data.get(key, default or key)

    def test_propose_then_confirm_adds_pack(self) -> None:
        first = self.handle(self.db, "Türkiye haber paketi öner", t=self.en)
        self.assertTrue(first["handled"])
        self.assertTrue(first["pending"])
        before = self.db.query("SELECT COUNT(*) n FROM sources")[0]["n"]
        second = self.handle(self.db, "evet", t=self.en, pending=first["pending"])
        after = self.db.query("SELECT COUNT(*) n FROM sources")[0]["n"]
        self.assertGreater(after, before)
        self.assertTrue(second["applied"]["sources"])

    def test_reject_leaves_sources(self) -> None:
        first = self.handle(self.db, "Suggest a tech pack", t=self.en)
        before = self.db.query("SELECT COUNT(*) n FROM sources")[0]["n"]
        self.handle(self.db, "hayır", t=self.en, pending=first["pending"])
        after = self.db.query("SELECT COUNT(*) n FROM sources")[0]["n"]
        self.assertEqual(before, after)

    def test_direct_ticker_add_and_remove(self) -> None:
        added = self.handle(self.db, "şeride BIST ekle", t=self.en)
        self.assertTrue(added["applied"]["tickers"])
        symbols = [item.symbol for item in self.db.list_tickers()]
        self.assertTrue(any(symbol.startswith("XU100") for symbol in symbols))
        removed = self.handle(self.db, "BIST 100 sil", t=self.en)
        symbols = [item.symbol for item in self.db.list_tickers()]
        self.assertFalse(any(symbol.startswith("XU100") for symbol in symbols))
        self.assertTrue(removed["applied"]["tickers"])

    def test_news_question_not_handled(self) -> None:
        result = self.handle(self.db, "What is moving global markets today?", t=self.en)
        self.assertFalse(result.get("handled"))


if __name__ == "__main__":
    unittest.main()
