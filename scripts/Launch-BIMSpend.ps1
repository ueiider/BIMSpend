param(
    [string]$Python = "python",
    [string]$DatabasePath
)
$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if (-not $DatabasePath) {
    $previewDir = Join-Path $repoRoot ".preview"
    New-Item -ItemType Directory -Force -Path $previewDir | Out-Null
    $DatabasePath = Join-Path $previewDir "bimspend.db"
}
$dbFull = [IO.Path]::GetFullPath($DatabasePath)
New-Item -ItemType Directory -Force -Path (Split-Path $dbFull) | Out-Null
$env:PYTHONPATH = Join-Path $repoRoot "src"
if (Test-Path (Join-Path $repoRoot $Python)) { $Python = (Resolve-Path (Join-Path $repoRoot $Python)).Path }
Push-Location (Split-Path $dbFull)
try {
    & $Python --version
    if ($LASTEXITCODE -ne 0) { throw "Python 3.9+ is required." }
    $sourceSha = & git -C $repoRoot rev-parse HEAD 2>$null
    if ($LASTEXITCODE -eq 0) { Write-Host "Source commit: $sourceSha" }
    Write-Host "Development preview: synthetic fixtures only; local SQLite at $dbFull"
    & $Python -m bimspend.app.main
    if ($LASTEXITCODE -ne 0) { throw "BIMSpend exited with code $LASTEXITCODE" }
} finally {
    Pop-Location
}
