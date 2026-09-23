"""Offline license keys and one-PC activation bind.

Keys look like YN1.<payload>.<hmac>. Verification uses HMAC-SHA256.
After a successful activate, the key is stored with this machine's fingerprint
so copying the data folder to another PC does not unlock the app.

Frozen builds require a valid local license unless YOU_NEWS_SKIP_LICENSE=1.
Source checkouts skip the gate unless YOU_NEWS_REQUIRE_LICENSE=1.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import platform
import sys
import time
import uuid
from pathlib import Path
from typing import Any

from config import DATA_DIR, delete_secret, get_secret, set_secret

LICENSE_PREFIX = "YN1"
LICENSE_KEY_ACCOUNT = "YOU_NEWS_LICENSE"
LICENSE_MACHINE_ACCOUNT = "YOU_NEWS_LICENSE_MACHINE"

class LicenseError(ValueError):
    """Invalid, expired, or machine-mismatched license."""


def _parse_hmac_material(value: str) -> bytes:
    text = "".join(value.split())
    if len(text) >= 32 and all(c in "0123456789abcdefABCDEF" for c in text):
        return bytes.fromhex(text)
    return text.encode("utf-8")


def _hmac_key() -> bytes:
    """Verification key. Never commit it.

    Order: YOU_NEWS_LICENSE_HMAC, secrets/license_hmac.txt (gitignored),
    then core/_embedded_hmac.py written only during a local exe build.
    A packaged exe still contains the key; this stops the public repo from minting keys.
    """
    override = (os.environ.get("YOU_NEWS_LICENSE_HMAC") or "").strip()
    if override:
        return _parse_hmac_material(override)
    secret_path = Path(__file__).resolve().parent.parent / "secrets" / "license_hmac.txt"
    if secret_path.is_file():
        line = ""
        for raw in secret_path.read_text(encoding="utf-8").splitlines():
            stripped = raw.strip()
            if stripped and not stripped.startswith("#"):
                line = stripped
                break
        if line:
            return _parse_hmac_material(line)
    try:
        from core._embedded_hmac import HEX as embedded
    except ImportError:
        embedded = ""
    if str(embedded or "").strip():
        return _parse_hmac_material(str(embedded))
    raise LicenseError("missing_secret")


def _b64url(raw: bytes) -> str:
    import base64

    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64url_decode(text: str) -> bytes:
    import base64

    pad = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + pad)


def normalize_key(value: str) -> str:
    return "".join(value.split())


def _store_dir() -> Path:
    override = os.environ.get("YOU_NEWS_HOME") or os.environ.get("YOU_NEWS_DATA")
    if override:
        return Path(override)
    return DATA_DIR


def _license_file() -> Path:
    return _store_dir() / "license.json"


def _file_blob() -> dict[str, str]:
    path = _license_file()
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _write_file_blob(data: dict[str, str]) -> None:
    folder = _store_dir()
    folder.mkdir(parents=True, exist_ok=True)
    path = _license_file()
    path.write_text(json.dumps(data, indent=0), encoding="utf-8")


def _file_only_store() -> bool:
    return bool(os.environ.get("YOU_NEWS_HOME") or os.environ.get("YOU_NEWS_DATA"))


def _get_stored(account: str) -> str | None:
    if not _file_only_store():
        value = get_secret(account)
        if value:
            return value
    blob = _file_blob()
    stored = blob.get(account)
    return stored or None


def _set_stored(account: str, value: str) -> None:
    if not _file_only_store():
        try:
            set_secret(account, value)
        except Exception:
            pass
    blob = _file_blob()
    blob[account] = value
    _write_file_blob(blob)


def _clear_stored(account: str) -> None:
    if not _file_only_store():
        try:
            delete_secret(account)
        except Exception:
            pass
    blob = _file_blob()
    if account in blob:
        del blob[account]
        if blob:
            _write_file_blob(blob)
        else:
            path = _license_file()
            if path.is_file():
                try:
                    path.unlink()
                except OSError:
                    pass


def machine_fingerprint() -> str:
    parts: list[str] = []
    if sys.platform == "win32":
        try:
            import winreg

            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography") as key:
                guid, _ = winreg.QueryValueEx(key, "MachineGuid")
                parts.append(str(guid))
        except OSError:
            pass
    parts.append(str(uuid.getnode()))
    parts.append(platform.node())
    raw = "|".join(parts).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def issue_key(email: str, *, issued_at: int | None = None, expires_at: int | None = None) -> str:
    email_clean = (email or "").strip().lower()
    if "@" not in email_clean:
        raise LicenseError("email required")
    payload: dict[str, Any] = {
        "e": email_clean,
        "i": int(issued_at if issued_at is not None else time.time()),
        "p": "YN",
    }
    if expires_at:
        payload["x"] = int(expires_at)
    body = _b64url(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    digest = hmac.new(_hmac_key(), body.encode("ascii"), hashlib.sha256).digest()
    return f"{LICENSE_PREFIX}.{body}.{_b64url(digest)}"


def parse_payload(key: str) -> dict[str, Any]:
    text = normalize_key(key)
    parts = text.split(".")
    if len(parts) != 3 or parts[0] != LICENSE_PREFIX:
        raise LicenseError("invalid")
    body, signature = parts[1], parts[2]
    expected = _b64url(hmac.new(_hmac_key(), body.encode("ascii"), hashlib.sha256).digest())
    if not hmac.compare_digest(expected, signature):
        raise LicenseError("invalid")
    try:
        payload = json.loads(_b64url_decode(body).decode("utf-8"))
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise LicenseError("invalid") from exc
    if not isinstance(payload, dict) or payload.get("p") != "YN":
        raise LicenseError("invalid")
    expires = payload.get("x")
    if expires is not None and int(time.time()) > int(expires):
        raise LicenseError("expired")
    return payload


def license_gate_required() -> bool:
    skip = (os.environ.get("YOU_NEWS_SKIP_LICENSE") or "").strip().lower()
    if skip in {"1", "true", "yes"}:
        return False
    require = (os.environ.get("YOU_NEWS_REQUIRE_LICENSE") or "").strip().lower()
    if require in {"1", "true", "yes"}:
        return True
    return bool(getattr(sys, "frozen", False))


def stored_key() -> str | None:
    return _get_stored(LICENSE_KEY_ACCOUNT)


def is_activated() -> bool:
    key = stored_key()
    if not key:
        return False
    try:
        parse_payload(key)
    except LicenseError:
        return False
    bound = _get_stored(LICENSE_MACHINE_ACCOUNT)
    current = machine_fingerprint()
    if bound and bound != current:
        return False
    if not bound:
        _set_stored(LICENSE_MACHINE_ACCOUNT, current)
    return True


def activate(key: str) -> dict[str, Any]:
    payload = parse_payload(key)
    current = machine_fingerprint()
    existing = stored_key()
    bound = _get_stored(LICENSE_MACHINE_ACCOUNT)
    if existing and normalize_key(existing) != normalize_key(key) and bound and bound != current:
        raise LicenseError("other_pc")
    if bound and bound != current:
        raise LicenseError("other_pc")
    _set_stored(LICENSE_KEY_ACCOUNT, normalize_key(key))
    _set_stored(LICENSE_MACHINE_ACCOUNT, current)
    return payload


def deactivate() -> None:
    _clear_stored(LICENSE_KEY_ACCOUNT)
    _clear_stored(LICENSE_MACHINE_ACCOUNT)


def masked_key(key: str | None = None) -> str:
    text = normalize_key(key or stored_key() or "")
    if len(text) < 12:
        return ""
    return f"{text[:8]}…{text[-6:]}"


def license_status() -> dict[str, Any]:
    activated = is_activated()
    payload: dict[str, Any] = {}
    key = stored_key()
    if key:
        try:
            payload = parse_payload(key)
        except LicenseError:
            payload = {}
    return {
        "activated": activated,
        "email": str(payload.get("e") or ""),
        "masked": masked_key(key) if activated else "",
        "machine": machine_fingerprint()[:12],
        "gate": license_gate_required(),
    }
