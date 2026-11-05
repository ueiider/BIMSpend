param([string]$Python = "python")
$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Push-Location $repoRoot
try {
    & $Python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw "Virtual environment creation failed." }
    & .\.venv\Scripts\python.exe -m pip install -e ".[dev]"
    if ($LASTEXITCODE -ne 0) { throw "Development dependency installation failed." }
    Write-Host "Run: .\scripts\Test-BIMSpend.ps1 -Python .\.venv\Scripts\python.exe"
    Write-Host "Run: .\scripts\Launch-BIMSpend.ps1 -Python .\.venv\Scripts\python.exe"
} finally {
    Pop-Location
}
