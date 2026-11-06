"""Capture screenshots of the packaged BIMSpend Windows preview.

This script launches the packaged BIMSpend.exe, logs in with synthetic demo
credentials, navigates to each major screen, and captures screenshots for
visual review. All data is synthetic; no real employee, client, or financial
information is used.

Usage:
    python scripts/Capture-Preview-Screenshots.py
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import pyautogui

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
BINARY = REPO_ROOT / ".preview" / "dist" / "BIMSpend" / "BIMSpend.exe"
SCREENSHOT_DIR = REPO_ROOT / ".preview" / "screenshots"
LOCALAPPDATA_DIR = REPO_ROOT / ".preview" / "screenshot-profile"

# Demo credentials (seeded in shell.py _seed_demo_auth_and_financials)
DEMO_COMPANY = "BIMSpend Demo Company (demo_co)"
DEMO_USERNAME = "bob_demo"
DEMO_PASSWORD = "DemoPass123!"

# Screens to capture (screen_id -> human-readable label)
SCREENS = [
    ("overview", "01-executive-dashboard"),
    ("activity_timeline", "02-live-activity"),
    ("timesheet_review", "03-timesheets"),
    ("designer_review", "04-designer-review"),
    ("manager_approval", "05-manager-approval"),
    ("projects", "06-projects"),
    ("project_financial_detail", "07-project-financial-detail"),
    ("financial_dashboard", "08-financial-management"),
    ("financial_reports", "09-reports-and-analytics"),
    ("integrations", "10-integrations-and-capture"),
    ("team", "11-employees-and-teams"),
]


def log(message: str) -> None:
    print(f"[Capture-Preview-Screenshots] {message}", flush=True)


def launch_app() -> subprocess.Popen:
    """Launch the packaged BIMSpend executable."""
    if not BINARY.exists():
        raise FileNotFoundError(f"Packaged executable not found: {BINARY}")
    log(f"Launching {BINARY}")
    proc = subprocess.Popen(
        [str(BINARY)],
        cwd=str(BINARY.parent),
        env={**os.environ, "LOCALAPPDATA": str(LOCALAPPDATA_DIR)},
    )
    LOCALAPPDATA_DIR.mkdir(parents=True, exist_ok=True)
    return proc


def wait_for_window(timeout_seconds: int = 60) -> None:
    """Wait for the BIMSpend window to appear."""
    log("Waiting for application window...")
    # pyautogui doesn't have window management; just wait and hope the app appears.
    # The app will show a login dialog; we send keys to it.
    time.sleep(5)  # Give the app time to start


def send_login() -> None:
    """Send login credentials to the login dialog."""
    log("Sending login credentials...")

    # The login dialog has: Company dropdown, Username, Password, Sign In button
    # Tab order: Company -> Username -> Password -> Sign In

    # Tab to company dropdown (first field after window focus)
    pyautogui.press("tab")
    time.sleep(0.5)

    # Type the company name to select it (dropdown is editable/readonly)
    # For a readonly combobox, we may need to type or use arrow keys
    pyautogui.typewrite("BIMSpend Demo", interval=0.05)
    time.sleep(0.5)
    pyautogui.press("enter")
    time.sleep(0.5)

    # Tab to username field
    pyautogui.press("tab")
    time.sleep(0.3)
    pyautogui.typewrite(DEMO_USERNAME, interval=0.05)
    time.sleep(0.3)

    # Tab to password field
    pyautogui.press("tab")
    time.sleep(0.3)
    pyautogui.typewrite(DEMO_PASSWORD, interval=0.05)
    time.sleep(0.3)

    # Tab to Sign In button and press Enter
    pyautogui.press("tab")
    time.sleep(0.3)
    pyautogui.press("enter")
    time.sleep(3.0)  # Wait for shell to load


def capture_screenshot(screen_label: str) -> None:
    """Capture a full-screen screenshot and save it."""
    screenshot = pyautogui.screenshot()
    output_path = SCREENSHOT_DIR / f"{screen_label}.png"
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    screenshot.save(str(output_path))
    log(f"Captured {output_path}")


def navigate_to_screen(screen_id: str) -> None:
    """Navigate to a screen by clicking the sidebar nav button.

    We use keyboard navigation: Tab through sidebar buttons until we reach
    the target, then press Enter. This is approximate; sidebar button order
    depends on role. For the demo manager role, the order is defined in
    docs/ui-modernization/UI_PROGRESS_TRACKER.md.
    """
    log(f"Navigating to {screen_id}...")
    # Approximate: press Tab multiple times to cycle through nav buttons,
    # then Enter to activate. This is best-effort for visual capture.
    # The sidebar has: overview, activity_timeline, timesheet_review,
    # designer_review, manager_approval, projects, project_financial_detail,
    # financial_dashboard, financial_reports, integrations, team
    # Plus Settings and Sign Out at the bottom.

    # Map screen_id to approximate tab position (0-indexed from first nav button)
    nav_order = [
        "overview",
        "activity_timeline",
        "timesheet_review",
        "designer_review",
        "manager_approval",
        "projects",
        "project_financial_detail",
        "financial_dashboard",
        "financial_reports",
        "integrations",
        "team",
    ]
    try:
        position = nav_order.index(screen_id)
    except ValueError:
        log(f"Unknown screen {screen_id}, skipping navigation")
        return

    # Tab to first nav button (after session info)
    # The sidebar order: logo, subtitle, session info, separator, nav heading,
    # nav buttons..., separator, Settings, Sign Out
    # We need to tab past logo/subtitle/session info to reach nav buttons
    for _ in range(6):  # Approximate tab count to reach first nav button
        pyautogui.press("tab")
        time.sleep(0.1)

    # Tab to the target position
    for _ in range(position):
        pyautogui.press("tab")
        time.sleep(0.1)

    # Activate
    pyautogui.press("enter")
    time.sleep(2.0)


def main() -> int:
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

    proc = None
    try:
        proc = launch_app()
        wait_for_window()
        send_login()

        # Capture overview first (it's the default screen)
        capture_screenshot(SCREENS[0][1])

        # Navigate to and capture each remaining screen
        for screen_id, label in SCREENS[1:]:
            navigate_to_screen(screen_id)
            capture_screenshot(label)

        log("All screenshots captured successfully.")
        return 0

    except Exception as exc:  # noqa: BLE001
        log(f"ERROR: {exc}")
        return 1
    finally:
        if proc is not None and proc.poll() is None:
            log("Terminating application...")
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()


if __name__ == "__main__":
    sys.exit(main())
