param([string]$Python = "python")
$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$binary = Join-Path $repoRoot ".preview/dist/BIMSpend/BIMSpend.exe"
if (-not (Test-Path $binary)) { throw "Packaged BIMSpend.exe is missing." }

# Run the preview in an isolated, synthetic-only profile on the Windows runner.
$env:LOCALAPPDATA = Join-Path $repoRoot ".preview/smoke-profile"
New-Item -ItemType Directory -Force -Path $env:LOCALAPPDATA | Out-Null
$db = Join-Path $env:LOCALAPPDATA "BIMSpend/preview/bimspend.db"
$process = Start-Process -FilePath $binary -WorkingDirectory (Split-Path $binary) -WindowStyle Hidden -PassThru
try {
    $ready = $false
    for ($attempt = 0; $attempt -lt 60; $attempt++) {
        Start-Sleep -Seconds 1
        $process.Refresh()
        if ($process.HasExited) { throw "Packaged application exited before synthetic database was initialized (exit code $($process.ExitCode))." }
        if (-not (Test-Path $db)) { continue }
        & $Python -c "import sqlite3, sys; con=sqlite3.connect(sys.argv[1]); assert con.execute('select count(*) from projects').fetchone()[0] > 0; assert con.execute('select count(*) from activity_events').fetchone()[0] > 0" $db 2>$null
        if ($LASTEXITCODE -eq 0) { $ready = $true; break }
    }
    if (-not $ready) { throw "Packaged application did not initialize its synthetic SQLite fixtures within 60 seconds." }
    Write-Host "Packaged executable running; synthetic projects and events persisted in isolated SQLite profile."
} finally {
    if (-not $process.HasExited) { Stop-Process -Id $process.Id -Force }
}
