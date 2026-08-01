[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [string]$Python = "python",

    [Parameter(Mandatory = $true)]
    [switch]$Replace
)

$ErrorActionPreference = "Stop"
$backendRoot = Split-Path -Parent $PSScriptRoot
$runner = Join-Path $PSScriptRoot "run_database_import.py"

if (-not (Test-Path -LiteralPath $runner)) {
    throw "Import runner not found: $runner"
}

Push-Location $backendRoot
try {
    & $Python $runner --replace
    if ($LASTEXITCODE -ne 0) {
        throw "Team database import failed with exit code $LASTEXITCODE"
    }
}
finally {
    Pop-Location
}
