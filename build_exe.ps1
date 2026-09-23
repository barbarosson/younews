# Builds a one-file Windows exe: dist\YouNews.exe
# Signing runs only when a cert is configured:
#   YOU_NEWS_CODESIGN_THUMBPRINT  (cert in the Windows store)
#   or YOU_NEWS_CODESIGN_PFX + YOU_NEWS_CODESIGN_PFX_PASSWORD
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$repo = Split-Path -Parent $root
$python = Join-Path $repo ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    $python = "python"
}

$secretFile = Join-Path $root "secrets\license_hmac.txt"
if (-not (Test-Path $secretFile)) {
    throw "Missing secrets\license_hmac.txt. Refusing to build an exe that cannot verify licenses."
}
$hex = (Get-Content -Raw -Path $secretFile).Trim()
if ($hex.Length -lt 32) {
    throw "secrets\license_hmac.txt is too short."
}
$embed = Join-Path $root "core\_embedded_hmac.py"
Set-Content -Path $embed -Encoding ascii -Value "HEX = `"$hex`"`n"

function Find-SignTool {
    $cmd = Get-Command signtool -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $kits = Get-ChildItem "C:\Program Files (x86)\Windows Kits\10\bin\*\x64\signtool.exe" -ErrorAction SilentlyContinue |
        Sort-Object FullName -Descending
    if ($kits) { return $kits[0].FullName }
    return $null
}

Set-Location $root
try {
    & $python -m pip install -q pyinstaller
    & $python -m PyInstaller --noconfirm --clean YouNews.spec
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed ($LASTEXITCODE)" }
    $exe = Join-Path $root "dist\YouNews.exe"
    Write-Host "Exe: $exe"
    $thumb = [string]$env:YOU_NEWS_CODESIGN_THUMBPRINT
    $pfx = [string]$env:YOU_NEWS_CODESIGN_PFX
    if (-not $thumb -and -not $pfx) {
        Write-Host "Unsigned. Set YOU_NEWS_CODESIGN_THUMBPRINT or YOU_NEWS_CODESIGN_PFX before a customer build."
        return
    }
    $signtool = Find-SignTool
    if (-not $signtool) { throw "signtool.exe not found. Install the Windows SDK signing tools." }
    if ($pfx) {
        & $signtool sign /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 /f $pfx /p $env:YOU_NEWS_CODESIGN_PFX_PASSWORD $exe
    } else {
        & $signtool sign /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 /sha1 $thumb $exe
    }
    if ($LASTEXITCODE -ne 0) { throw "signtool failed ($LASTEXITCODE)" }
    Write-Host "Signed: $exe"
}
finally {
    if (Test-Path $embed) { Remove-Item $embed -Force }
}
