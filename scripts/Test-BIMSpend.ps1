param([string]$Python = "python")
$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Push-Location $repoRoot
try {
    $env:PYTHONPATH = Join-Path $repoRoot "src"
    New-Item -ItemType Directory -Force -Path ".preview" | Out-Null
    & $Python -m compileall -q src tests
    if ($LASTEXITCODE -ne 0) { throw "Python compileall failed." }
    & $Python -m pytest tests -q -m "not gui" --basetemp=.preview/pytest-domain
    if ($LASTEXITCODE -ne 0) { throw "Domain tests failed." }
    $guiTests = @(
        "tests/test_work_integration.py::test_desktop_initialization_navigation_seed_and_restart",
        "tests/test_work_integration.py::test_desktop_actions_project_attribution_and_review",
        "tests/test_team_management.py::test_team_screen_can_open_and_refresh",
        "tests/test_reporting.py::test_report_date_filter_grouping_csv_and_privacy",
        "tests/test_historical_estimates.py::test_estimating_screen_opens_with_no_history"
    )
    foreach ($test in $guiTests) {
        $path = ($test -split "::")[0]
        if (-not (Test-Path $path)) { continue }
        & $Python -m pytest $test -q --basetemp=.preview/pytest-gui
        if ($LASTEXITCODE -ne 0) { throw "GUI test failed: $test" }
    }
} finally {
    Pop-Location
}
