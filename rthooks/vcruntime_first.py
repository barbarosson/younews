"""Load the bundled MSVC C++ runtime before anything else can.

Some security suites (seen with McAfee Endpoint Security's AMSI provider) load an
old MSVCP140.dll from their own folder into every unsigned process. Windows then
reuses that copy for Qt, and Qt 6 crashes inside it. Loading ours first makes the
later by-name lookups resolve to the bundled, current runtime instead.
"""

import os
import sys

if sys.platform == "win32" and getattr(sys, "frozen", False):
    import ctypes

    _base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    for _name in ("MSVCP140.dll", "MSVCP140_1.dll", "MSVCP140_2.dll"):
        _path = os.path.join(_base, "PySide6", _name)
        if os.path.exists(_path):
            try:
                ctypes.WinDLL(_path)
            except OSError:
                pass
