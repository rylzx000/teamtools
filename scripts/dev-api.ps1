$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location (Join-Path $root 'backend')

$dataRoot = Join-Path $root 'data'
$env:TEAMTOOLS_DATA_DIR = $dataRoot
$env:TEAMTOOLS_DB_PATH = Join-Path $dataRoot 'teamtools.db'
if (-not $env:TEAMTOOLS_SEED_DEV_USERS) {
  $env:TEAMTOOLS_SEED_DEV_USERS = 'false'
}

uv run uvicorn app.main:app `
  --reload `
  --reload-dir (Join-Path $root 'backend') `
  --reload-dir (Join-Path $root 'scripts') `
  --reload-dir (Join-Path $root 'data\modules\fpa\profile') `
  --host 127.0.0.1 `
  --port 8000
