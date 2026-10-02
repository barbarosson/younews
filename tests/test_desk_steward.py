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

    def test_korea_sites_proposes_pack(self) -> None:
        result = self.handle(self.db, "bana güney kore için haber sitelerini öner", t=self.en)
        self.assertTrue(result["handled"])
        ops = (result.get("pending") or {}).get("ops") or []
        self.assertEqual(ops[0].get("id"), "kr")
        self.assertNotIn("Which country", result["reply"])

    def test_headline_question_not_stolen(self) -> None:
        result = self.handle(self.db, "Güney Kore'de bugün neler oluyor?", t=self.en)
        self.assertFalse(result.get("handled"))

    def test_argentina_sites_proposes_latam_pack(self) -> None:
        result = self.handle(self.db, "bana arjantin için haber sitesi öner", t=self.en)
        self.assertTrue(result["handled"])
        ops = (result.get("pending") or {}).get("ops") or []
        self.assertEqual(ops[0].get("id"), "latam")
        reply = result["reply"].casefold()
        self.assertTrue("clar" in reply or "nación" in reply or "nacion" in reply or "latin" in reply)

    def test_unknown_country_advice_left_to_ai(self) -> None:
        result = self.handle(self.db, "bana norveç için haber sitesi öner", t=self.en)
        self.assertFalse(result.get("handled"))

    def test_pack_count_cap(self) -> None:
        from core.source_packs import PACK_ORDER, SOURCE_PACKS

        self.assertLessEqual(len(PACK_ORDER), 20)
        self.assertEqual(set(PACK_ORDER), set(SOURCE_PACKS))

    def test_brazil_agencies_recommends_brazil_not_turkey(self) -> None:
        result = self.handle(self.db, "brezilya haber ajanslarından hangisini önerirsin", t=self.en)
        self.assertTrue(result["handled"])
        ops = (result.get("pending") or {}).get("ops") or []
        self.assertEqual(ops[0].get("id"), "br")
        reply = result["reply"].casefold()
        self.assertTrue("folha" in reply or "brasil" in reply or "g1" in reply)
        self.assertNotIn("anadolu", reply)


if __name__ == "__main__":
    unittest.main()
