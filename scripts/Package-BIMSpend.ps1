param([string]$Python = "python")
$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Push-Location $repoRoot
try {
    $env:PYTHONPATH = Join-Path $repoRoot "src"
    New-Item -ItemType Directory -Force -Path ".preview" | Out-Null
    & $Python -m PyInstaller --noconfirm --clean --onedir --windowed --name BIMSpend --paths src --add-data "$(Join-Path $repoRoot 'data/synthetic'):data/synthetic" --distpath ".preview/dist" --workpath ".preview/build" --specpath ".preview/spec" scripts/preview_entry.py
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed." }
    $binary = Join-Path $repoRoot ".preview/dist/BIMSpend/BIMSpend.exe"
    if (-not (Test-Path $binary)) { throw "Expected preview EXE is missing." }
    $sha = & git -C $repoRoot rev-parse HEAD
    if ($LASTEXITCODE -eq 0) {
        Set-Content -Path ".preview/dist/BIMSpend/SOURCE_COMMIT.txt" -Value $sha
    }
    Write-Host "Built local synthetic preview: $binary"
} finally {
    Pop-Location
}

