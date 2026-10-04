# Offline wheelhouse assembly only; never downloads, deploys or qualifies a ZIP.
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$Runtime,
    [Parameter(Mandatory)][string]$Platform,
    [Parameter(Mandatory)][string]$Architecture,
    [Parameter(Mandatory)][string]$Handler,
    [Parameter(Mandatory)][string]$Wheelhouse,
    [Parameter(Mandatory)][string]$WheelLock,
    [Parameter(Mandatory)][string]$LayersMetadata,
    [Parameter(Mandatory)][string]$OutputZip,
    [string]$Python = ""
)
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
if (-not $Python) { $Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe" }
& $Python -B (Join-Path $PSScriptRoot "lambda_package.py") `
    --root $ProjectRoot --runtime $Runtime --platform $Platform `
    --architecture $Architecture --handler $Handler --wheelhouse $Wheelhouse `
    --wheel-lock $WheelLock --layers-metadata $LayersMetadata --output $OutputZip
if ($LASTEXITCODE -ne 0) { throw "Lambda package validation/assembly failed; no existing artifact replaced." }
