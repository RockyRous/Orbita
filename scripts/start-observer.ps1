param(
    [int]$Port = 4173
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $repoRoot
python -m observer_app.server --port $Port --open
