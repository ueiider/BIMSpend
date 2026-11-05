param([string]$Python = "python")
$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Push-Location $repoRoot
try {
    $env:PYTHONPATH = Join-Path $repoRoot "src"
    New-Item -ItemType Directory -Force -Path ".preview" | Out-Null
    & $Python -m compileall -q src tests
    if ($LASTEXITCODE -ne 0) { throw "Python compileall failed." }
    & $Python -m pytest tests -q --basetemp=.preview/pytest-tmp
    if ($LASTEXITCODE -ne 0) { throw "BIMSpend tests failed." }
} finally {
    Pop-Location
}
