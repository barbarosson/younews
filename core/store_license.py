"""Microsoft Store license / trial for MSIX builds.

Unpackaged (website) builds keep using YN1 keys in core.license.
When running inside an MSIX installed from the Store, this module is the gate.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from typing import Any

_LOG = logging.getLogger(__name__)


def is_packaged_msix() -> bool:
    """True when this process runs inside an MSIX / Store package."""
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        from ctypes import wintypes

        GetCurrentPackageFullName = ctypes.windll.kernel32.GetCurrentPackageFullName
        GetCurrentPackageFullName.argtypes = [ctypes.POINTER(wintypes.UINT), wintypes.LPWSTR]
        GetCurrentPackageFullName.restype = wintypes.LONG
        length = wintypes.UINT(0)
        # APPMODEL_ERROR_NO_PACKAGE = 15700
        rc = GetCurrentPackageFullName(ctypes.byref(length), None)
        if rc == 15700 or length.value == 0:
            return False
        buf = ctypes.create_unicode_buffer(length.value)
        rc = GetCurrentPackageFullName(ctypes.byref(length), buf)
        return rc == 0 and bool(buf.value)
    except Exception:
        return False


def uses_store_licensing() -> bool:
    return is_packaged_msix()


def _run(coro):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(asyncio.run, coro).result(timeout=60)
        return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


async def _app_license():
    from winrt.windows.services.store import StoreContext

    context = StoreContext.get_default()
    return await context.get_app_license_async()


def store_license_status() -> dict[str, Any]:
    """Return Store license fields. Safe when WinRT is missing or unpackaged."""
    empty = {
        "store": True,
        "active": False,
        "trial": False,
        "is_active": False,
        "sku": "",
        "error": "",
    }
    if not is_packaged_msix():
        empty["store"] = False
        return empty
    try:
        license_obj = _run(_app_license())
    except Exception as exc:  # noqa: BLE001 — Store APIs fail outside Store context
        _LOG.warning("Store license check failed: %s", exc)
        empty["error"] = str(exc)
        return empty
    try:
        active = bool(getattr(license_obj, "is_active", False))
        trial = bool(getattr(license_obj, "is_trial", False))
        sku = str(getattr(license_obj, "sku_store_id", "") or "")
        return {
            "store": True,
            "active": active,
            "trial": trial,
            "is_active": active,
            "sku": sku,
            "error": "",
        }
    except Exception as exc:  # noqa: BLE001
        empty["error"] = str(exc)
        return empty


def is_store_licensed() -> bool:
    status = store_license_status()
    return bool(status.get("is_active"))


async def _request_purchase():
    from winrt.windows.services.store import StoreContext

    context = StoreContext.get_default()
    product_result = await context.get_store_product_for_current_app_async()
    product = getattr(product_result, "product", None)
    store_id = str(getattr(product, "store_id", "") or "") if product is not None else ""
    if not store_id:
        # Fall back: purchase may still work with empty for some contexts
        return await context.request_purchase_async("")
    return await context.request_purchase_async(store_id)


def request_store_purchase() -> dict[str, Any]:
    """Prompt the Store purchase / trial UI. Returns status dict."""
    if not is_packaged_msix():
        return {"ok": False, "error": "not_packaged"}
    try:
        result = _run(_request_purchase())
    except Exception as exc:  # noqa: BLE001
        _LOG.warning("Store purchase failed: %s", exc)
        return {"ok": False, "error": str(exc)}
    status = str(getattr(result, "status", "") or "")
    # StorePurchaseStatus: Succeeded=0, AlreadyPurchased=1, NotPurchased=2, NetworkError=3, ServerError=4
    ok = status in {"Succeeded", "AlreadyPurchased", "0", "1"} or getattr(result, "status", None) in (0, 1)
    return {"ok": bool(ok) or is_store_licensed(), "status": status, "error": "" if ok else status}
