# BIMSpend Windows Synthetic Preview

This document describes the BIMSpend Windows desktop preview built from the
`design/opencode-r1-08-desktop-ui-modernization` branch (commit
`e1196875b1c5a019a7edf2bf62fe4d64a78bde24`).

## What this preview is

A self-contained, desktop Tkinter application packaged with PyInstaller as a
one-folder Windows executable. It runs entirely on local synthetic data — no
real employee, client, or financial information is used, and no network
connections are made.

## What this preview is NOT

- **Not production-ready.** This is a development preview for visual review
  only. Do not deploy to production environments.
- **Not a billing system.** Approved time is never automatically invoiced.
  Billing is a separate explicit action and is not connected to any payment
  processor.
- **Not employee monitoring.** Activity capture is disabled by default and
  requires explicit consent. No live ActivityWatch, Miru, or Revit adapters
  are active in this preview.
- **Not multi-user.** This is a single-user desktop prototype.

## Demo credentials

The preview ships with synthetic demo data pre-seeded. Use these credentials
to sign in:

| Username | Password      | Role          | Company                  |
|----------|---------------|---------------|--------------------------|
| `alice_demo` | `DemoPass123!` | Designer      | BIMSpend Demo Company    |
| `bob_demo`   | `DemoPass123!` | Manager       | BIMSpend Demo Company    |
| `carol_demo` | `DemoPass123!` | Administrator | BIMSpend Demo Company    |

All accounts belong to the same synthetic company, `demo_co` ("BIMSpend Demo
Company").

## Screens included

The navigation sidebar shows role-appropriate screens. With the **manager**
role (`bob_demo`), all screens are visible:

1. **Executive Dashboard** — Observed vs attributed vs approved vs billed
   hours, project table with budget vs actual.
2. **Live Activity** — Observed activity events with project attribution
   suggestions, AFK detection, privacy-filtered window titles.
3. **Timesheets** — Pending review (designer submit) and submitted (manager
   approve/reject) panes.
4. **Designer Review** — Review, edit, submit, reject, split, and merge time
   suggestions.
5. **Manager Approval** — Approve, reject, return for correction, and bulk
   actions on submitted entries.
6. **Projects** — Project list with create/edit/archive.
7. **Project Financial Detail** — Budget consumption, labour cost by
   employee, deterministic forecast.
8. **Financial Management** — Budget vs actual, remaining budget,
   over-budget detection across all projects.
9. **Reports and Analytics** — Project cost summary, budget vs actual,
   employee labour cost, approved hours by project, financial variance —
   with CSV export.
10. **Integrations and Capture** — Mock ActivityWatch, Revit, and Miru
    integration console (live collection disabled).
11. **Employees and Teams** — Team roster, roles, rates, project assignments.

With the **designer** role (`alice_demo`), manager-only screens (Manager
Approval, Financial Management, Employees and Teams) are hidden.

## How to run the preview

### Option 1: Download from GitHub Actions

1. Go to the GitHub Actions page for this repository.
2. Find the "Package Windows synthetic preview" workflow run for the latest
   commit on `design/opencode-r1-08-desktop-ui-modernization`.
3. Download the `BIMSpend-Windows-Synthetic-Preview` artifact.
4. Extract the ZIP file.
5. Run `BIMSpend\BIMSpend.exe`.

### Option 2: Build from source

1. Clone the repository and checkout the UI branch:
   ```
   git clone https://github.com/ueiider/BIMSpend.git
   cd BIMSpend
   git checkout design/opencode-r1-08-desktop-ui-modernization
   ```
2. Install build dependencies:
   ```
   pip install -e . pyinstaller==6.16.0
   ```
3. Build the executable:
   ```
   .\scripts\Package-BIMSpend.ps1
   ```
4. Run the executable:
   ```
   .\.preview\dist\BIMSpend\BIMSpend.exe
   ```

## Security and privacy

- **No cloud identity provider.** All authentication is local, using
  PBKDF2-HMAC-SHA256 password hashing (210,000 iterations).
- **Session-based auth with fail-closed validation.** Every action validates
  the session against the local SQLite database.
- **Company-scoped authorization.** Users can only access data in their own
  company.
- **No automatic billing.** Approved time is never automatically invoiced.
- **No live activity capture.** ActivityWatch, Miru, and Revit adapters are
  mock-only in this preview.
- **Window titles are privacy-filtered.** Raw window titles are hashed before
  persistence; redacted titles are shown as `[REDACTED]`.

## Data locations

The preview stores its local SQLite database in:
```
%LOCALAPPDATA%\BIMSpend\preview\bimspend.db
```

The smoke test uses an isolated profile at:
```
.preview\smoke-profile\BIMSpend\preview\bimspend.db
```

## Known limitations

- **Screenshots require a graphical session.** On headless CI runners,
  screenshot capture may fail silently (the step is marked `continue-on-error`).
- **Keyboard navigation for screenshots is approximate.** The screenshot
  capture script uses Tab/Enter to navigate the sidebar; screen transitions
  may not always land on the intended screen.
- **Tkinter/Tcl runtime required.** The packaged executable includes the Tcl
  runtime, but on very minimal Windows systems additional dependencies may be
  needed.
- **Single-user desktop prototype.** No multi-user synchronization, no
  cloud sync, no remote API.

## Rollback

To roll back this preview:

1. **Uninstall:** Delete the `BIMSpend\` folder from the extracted artifact.
   No system-wide changes are made.
2. **Remove local data:** Delete `%LOCALAPPDATA%\BIMSpend\preview\` to remove
   the local SQLite database and all synthetic data.
3. **Revert code:** `git checkout main` or checkout any earlier commit to
   return to the previous code state.

## Artifact contents

| Artifact name                  | Contents                                  |
|--------------------------------|-------------------------------------------|
| `BIMSpend-Windows-Synthetic-Preview` | Packaged `BIMSpend.exe` folder (one-dir) |
| `BIMSpend-Windows-Screenshots`       | PNG screenshots of each screen            |

## CI workflow

The preview is built by the GitHub Actions workflow
`.github/workflows/windows-preview.yml`, which runs on Windows Server
(`windows-latest`) on pushes to `main` and
`design/opencode-r1-08-desktop-ui-modernization`, and can be triggered
manually via `workflow_dispatch`.

The workflow:
1. Checks out the repository
2. Installs Python 3.11, the package, PyInstaller, pyautogui, Pillow
3. Builds the one-folder executable with PyInstaller
4. Smoke-tests the executable (starts it, verifies SQLite initialization)
5. Captures screenshots of each screen (best-effort)
6. Uploads both the preview folder and screenshots as artifacts
