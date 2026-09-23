# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for You News (Windows exe)."""

from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

block_cipher = None

datas = [
    ("locales", "locales"),
    ("ui/styles", "ui/styles"),
    ("ui/assets", "ui/assets"),
]
datas += collect_data_files("certifi")
datas += copy_metadata("feedparser")
datas += copy_metadata("yfinance")

hiddenimports = [
    "keyring.backends.Windows",
    "keyring.backends.null",
    "yfinance",
    "curl_cffi",
    "peewee",
    "lxml",
    "lxml.etree",
    "bs4",
    "feedparser",
    "httpx",
    "openai",
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "PySide6.QtNetwork",
    "core.license",
    "core._embedded_hmac",
]
hiddenimports += collect_submodules("keyring.backends")
hiddenimports += collect_submodules("yfinance")

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets",
        "PySide6.Qt3DCore",
        "tkinter",
        "matplotlib",
        "pytest",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="YouNews",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="ui/assets/you_news_icon.ico",
)
