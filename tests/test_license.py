import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from core.license import (
    LicenseError,
    activate,
    deactivate,
    is_activated,
    issue_key,
    license_gate_required,
    parse_payload,
)


class LicenseTests(unittest.TestCase):
    def setUp(self) -> None:
        self._home = tempfile.TemporaryDirectory()
        self._env = patch.dict(
            os.environ,
            {
                "YOU_NEWS_HOME": self._home.name,
                "YOU_NEWS_SKIP_LICENSE": "",
                "YOU_NEWS_REQUIRE_LICENSE": "",
                "YOU_NEWS_LICENSE_HMAC": "ab" * 32,
            },
            clear=False,
        )
        self._env.start()
        deactivate()

    def tearDown(self) -> None:
        deactivate()
        self._env.stop()
        self._home.cleanup()

    def test_round_trip(self) -> None:
        key = issue_key("Buyer@YouNews.media")
        payload = parse_payload(key)
        self.assertEqual(payload["e"], "buyer@younews.media")
        activate(key)
        self.assertTrue(is_activated())
        self.assertTrue((Path(self._home.name) / "license.json").is_file())

    def test_tamper_rejected(self) -> None:
        key = issue_key("buyer@younews.media")
        bad = key[:-2] + ("A" if key[-1] != "A" else "B")
        with self.assertRaises(LicenseError):
            parse_payload(bad)
        self.assertFalse(is_activated())

    def test_expired(self) -> None:
        key = issue_key("buyer@younews.media", expires_at=int(time.time()) - 10)
        with self.assertRaises(LicenseError):
            parse_payload(key)

    def test_other_machine(self) -> None:
        key = issue_key("buyer@younews.media")
        activate(key)
        with patch("core.license.machine_fingerprint", return_value="other-machine-hash"):
            self.assertFalse(is_activated())
            with self.assertRaises(LicenseError):
                activate(key)

    def test_deactivate_allows_reactivate(self) -> None:
        key = issue_key("buyer@younews.media")
        activate(key)
        deactivate()
        self.assertFalse(is_activated())
        activate(key)
        self.assertTrue(is_activated())

    def test_gate_env(self) -> None:
        with patch.dict(os.environ, {"YOU_NEWS_SKIP_LICENSE": "1"}, clear=False):
            self.assertFalse(license_gate_required())
        with patch.dict(os.environ, {"YOU_NEWS_SKIP_LICENSE": "", "YOU_NEWS_REQUIRE_LICENSE": "1"}, clear=False):
            self.assertTrue(license_gate_required())
        with patch.dict(os.environ, {"YOU_NEWS_SKIP_LICENSE": "", "YOU_NEWS_REQUIRE_LICENSE": ""}, clear=False):
            with patch("core.license.sys") as fake_sys:
                fake_sys.frozen = True
                self.assertTrue(license_gate_required())
                fake_sys.frozen = False
                self.assertFalse(license_gate_required())


if __name__ == "__main__":
    unittest.main()
