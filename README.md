# BIMSpend — Windows desktop development preview

Development was authorized on 2026-11-05. The independent B2-A audit was deferred, **not approved**. This preview uses synthetic fixtures only; it does not collect employee activity, connect to Revit, synchronize with Miru or deploy to production.

## Download the Windows preview

Open the latest successful [Package Windows synthetic preview](https://github.com/ueiider/BIMSpend/actions/workflows/windows-preview.yml) run on `main` and download the `BIMSpend-Windows-Synthetic-Preview` artifact. Extract the **entire** folder, keeping `BIMSpend.exe` beside its `_internal` directory. Run `BIMSpend.exe` on Windows. The source SHA is in `SOURCE_COMMIT.txt` in the extracted folder. The synthetic database is stored under `%LOCALAPPDATA%\BIMSpend\preview\bimspend.db`; keep a backup before deleting or resetting it. The artifact is a one-folder preview, not a signed installer or a production build.

## Run from source (Windows, Python 3.11+)

From the repository root in PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\scripts\Test-BIMSpend.ps1 -Python .\.venv\Scripts\python.exe
.\scripts\Launch-BIMSpend.ps1 -Python .\.venv\Scripts\python.exe
```

The source launcher stores the synthetic database at `.preview/bimspend.db` unless `-DatabasePath` is supplied. To build the same Windows preview folder locally, install the pinned packager with `.\.venv\Scripts\python.exe -m pip install pyinstaller==6.16.0`, then run `.\scripts\Package-BIMSpend.ps1 -Python .\.venv\Scripts\python.exe`; output is `.preview/dist/BIMSpend/`. Windows CI runs automated domain, Tkinter and packaged startup checks. Interactive visual testing remains a separate task.

## Working functionality

- Tkinter dashboard, projects (create, edit, archive), synthetic activity timeline and manual attribution.
- Designer confirmation, timesheet submission, manager approval or rejection, explicit billing, and persisted audit history. Domain checks enforce synthetic role permissions; these IDs are not secure user authentication.
- Team roster and project assignments, project budgets and approved labor cost, date-filtered reports and CSV exports, historical hour estimates from approved synthetic records.
- SQLite persistence with idempotent synthetic activity ingestion and redacted window titles.

ActivityWatch, Miru and Revit interfaces currently use synthetic boundaries or are not integrated with the desktop preview. No real monitoring is enabled. See `docs/RUNBOOK.md` for the original vertical-slice runbook and `docs/product-design/` for product specifications; those documents may describe future features.

