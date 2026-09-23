# Build You News Windows exe via the canonical YouNews.spec
# Usage:  powershell -File scripts/pack_windows.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
& (Join-Path $root "build_exe.ps1")
