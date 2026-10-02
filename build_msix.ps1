# Builds Store MSIX: dist\YouNews_<version>_x64.msix
# Requires: secrets\license_hmac.txt, Windows SDK makeappx + signtool
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$repo = Split-Path -Parent $root
$python = Join-Path $repo ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) { $python = "python" }

$identityPath = Join-Path $root "store\identity.json"
if (-not (Test-Path $identityPath)) { throw "Missing store\identity.json" }
$identity = Get-Content -Raw -Path $identityPath | ConvertFrom-Json
$version = [string]$identity.Version
$name = [string]$identity.Name
$publisher = [string]$identity.Publisher
$arch = [string]$identity.Architecture
if (-not $arch) { $arch = "x64" }

$secretFile = Join-Path $root "secrets\license_hmac.txt"
if (-not (Test-Path $secretFile)) {
    throw "Missing secrets\license_hmac.txt. Refusing to build a package that cannot verify licenses."
}
$hex = (Get-Content -Raw -Path $secretFile).Trim()
if ($hex.Length -lt 32) { throw "secrets\license_hmac.txt is too short." }
$embed = Join-Path $root "core\_embedded_hmac.py"
Set-Content -Path $embed -Encoding ascii -Value "HEX = `"$hex`"`n"

function Find-SdkTool([string]$exeName) {
    $cmd = Get-Command $exeName -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $kits = Get-ChildItem "C:\Program Files (x86)\Windows Kits\10\bin\*\x64\$exeName" -ErrorAction SilentlyContinue |
        Sort-Object FullName -Descending
    if ($kits) { return $kits[0].FullName }
    return $null
}

function Ensure-StoreAssets {
    param([string]$AssetsDir, [string]$SourcePng)
    New-Item -ItemType Directory -Force -Path $AssetsDir | Out-Null
    & $python -c @"
from pathlib import Path
try:
    from PIL import Image
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', 'pillow'])
    from PIL import Image

src = Path(r'$SourcePng')
out = Path(r'$AssetsDir')
img = Image.open(src).convert('RGBA')

def save(size, name, canvas=None):
    if canvas is None:
        canvas = size if isinstance(size, tuple) else (size, size)
    w, h = canvas if isinstance(canvas, tuple) else (canvas, canvas)
    side = size if isinstance(size, int) else min(size)
    logo = img.resize((side, side), Image.Resampling.LANCZOS)
    sheet = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    sheet.paste(logo, ((w - side) // 2, (h - side) // 2), logo)
    sheet.save(out / name, 'PNG')

save(50, 'StoreLogo.png')
save(44, 'Square44x44Logo.png')
save(150, 'Square150x150Logo.png')
save(150, 'Wide310x150Logo.png', (310, 150))
save(620, 'SplashScreen.png', (620, 300))
print('assets ok', out)
"@
}

try {
    Write-Host "Installing WinRT Store bindings (if needed)..."
    & $python -m pip install -q `
        "winrt-runtime" `
        "winrt-Windows.Foundation" `
        "winrt-Windows.Services.Store" `
        "winrt-Windows.ApplicationModel" `
        pillow

    Set-Location $root
    Write-Host "PyInstaller onedir..."
    & $python -m pip install -q pyinstaller
    & $python -m PyInstaller --noconfirm --clean YouNews.onedir.spec
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed ($LASTEXITCODE)" }

    $onedir = Join-Path $root "dist\YouNews"
    if (-not (Test-Path (Join-Path $onedir "YouNews.exe"))) {
        throw "Missing dist\YouNews\YouNews.exe"
    }

    $layout = Join-Path $root "dist\msix_layout"
    if (Test-Path $layout) { Remove-Item $layout -Recurse -Force }
    New-Item -ItemType Directory -Force -Path $layout | Out-Null
    Copy-Item -Path $onedir -Destination (Join-Path $layout "YouNews") -Recurse -Force

    $assets = Join-Path $layout "Assets"
    $iconPng = Join-Path $root "ui\assets\you_news_icon.png"
    Ensure-StoreAssets -AssetsDir $assets -SourcePng $iconPng

    $template = Get-Content -Raw -Path (Join-Path $root "store\AppxManifest.template.xml")
    $manifest = $template.
        Replace("{{Name}}", [string]$identity.Name).
        Replace("{{Publisher}}", [string]$identity.Publisher).
        Replace("{{PublisherDisplayName}}", [string]$identity.PublisherDisplayName).
        Replace("{{DisplayName}}", [string]$identity.DisplayName).
        Replace("{{Description}}", [string]$identity.Description).
        Replace("{{Version}}", $version).
        Replace("{{Architecture}}", $arch)
    Set-Content -Path (Join-Path $layout "AppxManifest.xml") -Value $manifest -Encoding utf8

    $makeappx = Find-SdkTool "makeappx.exe"
    if (-not $makeappx) { throw "makeappx.exe not found. Install the Windows SDK." }
    $signtool = Find-SdkTool "signtool.exe"
    if (-not $signtool) { throw "signtool.exe not found. Install the Windows SDK." }

    $msix = Join-Path $root "dist\YouNews_${version}_${arch}.msix"
    if (Test-Path $msix) { Remove-Item $msix -Force }
    & $makeappx pack /o /d $layout /p $msix
    if ($LASTEXITCODE -ne 0) { throw "makeappx failed ($LASTEXITCODE)" }

    $certDir = Join-Path $root "secrets"
    New-Item -ItemType Directory -Force -Path $certDir | Out-Null
    $cer = Join-Path $certDir "store_publisher.cer"
    $pfx = Join-Path $certDir "store_publisher.pfx"
    $pfxPass = "YouNewsStoreTemp!"
    if (-not (Test-Path $pfx)) {
        Write-Host "Creating self-signed cert for $publisher"
        $cert = New-SelfSignedCertificate `
            -Type Custom `
            -Subject $publisher `
            -KeyUsage DigitalSignature `
            -FriendlyName "You News Store packaging" `
            -CertStoreLocation "Cert:\CurrentUser\My" `
            -TextExtension @("2.5.29.37={text}1.3.6.1.5.5.7.3.3", "2.5.29.19={text}")
        $secure = ConvertTo-SecureString -String $pfxPass -Force -AsPlainText
        Export-PfxCertificate -Cert $cert -FilePath $pfx -Password $secure | Out-Null
        Export-Certificate -Cert $cert -FilePath $cer | Out-Null
    }
    & $signtool sign /fd SHA256 /a /f $pfx /p $pfxPass /tr http://timestamp.digicert.com /td SHA256 $msix
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Timestamp sign failed; signing without timestamp..."
        & $signtool sign /fd SHA256 /a /f $pfx /p $pfxPass $msix
        if ($LASTEXITCODE -ne 0) { throw "signtool failed ($LASTEXITCODE)" }
    }

    Write-Host "MSIX: $msix"
    Write-Host "Upload this file in Partner Center -> Packages."
}
finally {
    if (Test-Path $embed) { Remove-Item $embed -Force }
}
