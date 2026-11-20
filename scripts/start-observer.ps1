param(
    [switch]$BrowserPreview
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $repoRoot
if ($BrowserPreview) {
    python -m observer_app.server --port 4173 --open
} else {
    python -m observer_app.desktop
}
