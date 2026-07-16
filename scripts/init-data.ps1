$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$dataRoot = Join-Path $root 'data'

$dirs = @(
  $dataRoot,
  (Join-Path $dataRoot 'config'),
  (Join-Path $dataRoot 'config\modules'),
  (Join-Path $dataRoot 'config\modules\fpa'),
  (Join-Path $dataRoot 'modules'),
  (Join-Path $dataRoot 'modules\fpa'),
  (Join-Path $dataRoot 'modules\fpa\knowledge'),
  (Join-Path $dataRoot 'modules\fpa\examples'),
  (Join-Path $dataRoot 'modules\fpa\examples\input'),
  (Join-Path $dataRoot 'modules\fpa\examples\expected'),
  (Join-Path $dataRoot 'tasks'),
  (Join-Path $dataRoot 'tasks\fpa'),
  (Join-Path $dataRoot 'logs')
)

foreach ($dir in $dirs) {
  New-Item -ItemType Directory -Path $dir -Force | Out-Null
}

Write-Host "Initialized data directories at $dataRoot"
