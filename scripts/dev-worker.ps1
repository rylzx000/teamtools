$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location (Join-Path $root 'backend')

$dataRoot = Join-Path $root 'data'
$env:TEAMTOOLS_DATA_DIR = $dataRoot
$env:TEAMTOOLS_DB_PATH = Join-Path $dataRoot 'teamtools.db'

uv run python -m app.worker
