# DocsForge migration — converts mkdocs/properdocs/zensical config to
# docsforge.yml. One-liner (PowerShell):
#   irm https://raw.githubusercontent.com/QQSHI13/docsforge/main/scripts/migrate.ps1 | iex
$ErrorActionPreference = 'Stop'

$MigrateUrl = $env:DOCSFORGE_MIGRATE_URL
if (-not $MigrateUrl) {
  $MigrateUrl = 'https://raw.githubusercontent.com/QQSHI13/docsforge/main/scripts/migrate.py'
}

function Fail($msg) {
  Write-Error "docsforge-migrate: $msg"
  exit 1
}

# 1. Python?
$python = Get-Command python3 -ErrorAction SilentlyContinue
if (-not $python) { $python = Get-Command python -ErrorAction SilentlyContinue }
if (-not $python) { Fail 'python not found — install Python 3.11+ (https://www.python.org/downloads/)' }
$py = $python.Source

# 2. Download migrate.py
$tmp = New-Item -ItemType Directory -Path ([System.IO.Path]::GetTempPath()) -Name ("docsforge-migrate-" + [guid]::NewGuid().ToString('N'))
try {
  Invoke-WebRequest -Uri $MigrateUrl -OutFile (Join-Path $tmp.FullName 'migrate.py') -UseBasicParsing
} catch {
  Fail "could not download $MigrateUrl — check your connection"
}

# 3. Ensure PyYAML
$runPy = $py
$hasYaml = & $py -c 'import yaml' 2>$null
if ($LASTEXITCODE -ne 0) {
  Write-Host 'docsforge-migrate: PyYAML not found — installing…'
  & $py -m pip install --user --quiet pyyaml
  $runPy = $py
}

& $runPy (Join-Path $tmp.FullName 'migrate.py') @args
$code = $LASTEXITCODE
Remove-Item -Recurse -Force $tmp.FullName
exit $code
