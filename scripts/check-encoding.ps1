$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$checker = Join-Path $root "tools\check_text_encoding.py"

python $checker --root $root

