# Install the latest DocsForge VS Code extension from GitHub releases.
# Usage: powershell -ExecutionPolicy Bypass -File install.ps1
# This script downloads the .vsix and its published .sha256 checksum,
# verifies the checksum, and installs the extension with `code.cmd`.

$repo = 'QQSHI13/docsforge'
$apiUrl = "https://api.github.com/repos/$repo/releases/latest"
$tmpDir = Join-Path $env:TEMP ('docsforge-install-' + [Guid]::NewGuid().ToString())
New-Item -ItemType Directory -Path $tmpDir -Force | Out-Null

try {
    Write-Host "Fetching latest release info from $apiUrl ..."
    $release = Invoke-RestMethod -Uri $apiUrl -UseBasicParsing

    $vsixAsset = $release.assets | Where-Object { $_.name -like '*.vsix' } | Select-Object -First 1
    $shaAsset = $release.assets | Where-Object { $_.name -like '*.vsix.sha256' } | Select-Object -First 1

    if (-not $vsixAsset) {
        throw 'Could not find a .vsix asset in the latest release.'
    }
    if (-not $shaAsset) {
        throw 'Could not find a .vsix.sha256 checksum asset in the latest release.'
    }

    $vsixPath = Join-Path $tmpDir $vsixAsset.name
    $shaPath = Join-Path $tmpDir $shaAsset.name

    Write-Host "Downloading $($vsixAsset.name) ..."
    Invoke-WebRequest -Uri $vsixAsset.browser_download_url -OutFile $vsixPath -UseBasicParsing

    Write-Host "Downloading $($shaAsset.name) ..."
    Invoke-WebRequest -Uri $shaAsset.browser_download_url -OutFile $shaPath -UseBasicParsing

    Write-Host 'Verifying checksum ...'
    $expectedLine = Get-Content -Path $shaPath -Raw
    $expected = ($expectedLine -split '\s+')[0]
    $actual = (Get-FileHash -Path $vsixPath -Algorithm SHA256).Hash
    if ($expected -ne $actual) {
        throw "SHA256 checksum mismatch.`nExpected: $expected`nActual:   $actual"
    }
    Write-Host 'Checksum OK.'

    & code.cmd --install-extension $vsixPath --force
    Write-Host 'Installed!'
}
finally {
    Remove-Item -Recurse -Force -Path $tmpDir -ErrorAction SilentlyContinue
}
