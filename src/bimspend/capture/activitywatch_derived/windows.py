"""Windows foreground-window capture primitives.

Adapted from ActivityWatch aw-watcher-window/aw_watcher_window/windows.py
(upstream commit 12000f58d16b8fc1376af42755c688b3d7157280, MPL-2.0).

Original copyright: ActivityWatch contributors.
See docs/open-source/ACTIVITYWATCH_SOURCE_MANIFEST.md for full provenance.

This module provides low-level Windows API access for detecting the active
foreground window, its title, and the owning application. It uses pywin32
with a WMI fallback for elevated/admin processes where direct process
access is restricted.
"""

from __future__ import annotations

import os
import time
from typing import Optional

try:
    import win32api
    import win32gui
    import win32process
    _HAS_WIN32 = True
except ImportError:
    _HAS_WIN32 = False

try:
    import wmi
    _HAS_WMI = True
except ImportError:
    _HAS_WMI = False


def _require_win32() -> None:
    """Raise a clear error if pywin32 is not available."""
    if not _HAS_WIN32:
        raise ImportError(
            "pywin32 is required for Windows window capture. "
            "Install with: pip install pywin32"
        )


def get_active_window_handle() -> Optional[int]:
    """Return the handle of the current foreground window, or None."""
    _require_win32()
    hwnd = win32gui.GetForegroundWindow()
    if not hwnd:
        return None
    return hwnd


def get_window_title(hwnd: int) -> str:
    """Return the window title text for the given handle."""
    _require_win32()
    return win32gui.GetWindowText(hwnd) or ""


def get_app_path(hwnd: int) -> Optional[str]:
    """Return the executable path for the window's owning process."""
    _require_win32()
    try:
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        process = win32api.OpenProcess(0x0400, False, pid)  # PROCESS_QUERY_INFORMATION
        try:
            path = win32process.GetModuleFileNameEx(process, 0)
        finally:
            win32api.CloseHandle(process)
        return path
    except Exception:
        return None


def get_app_name(hwnd: int) -> Optional[str]:
    """Return the executable filename for the window's owning process."""
    path = get_app_path(hwnd)
    if path is None:
        return None
    return os.path.basename(path)


FRAME_HOST_APP = "applicationframehost.exe"


def get_uwp_app_window(hwnd: int) -> Optional[int]:
    """Return the child window of a UWP frame host, or None.

    UWP apps (Settings, Calculator, ...) run inside ApplicationFrameHost.exe.
    The real app window is a child of that frame. Returns None if no child
    is found (e.g. during activation delay).
    """
    _require_win32()
    _, host_pid = win32process.GetWindowThreadProcessId(hwnd)
    children: list[int] = []

    def collect(child: int, _: int) -> bool:
        _, child_pid = win32process.GetWindowThreadProcessId(child)
        if child_pid != host_pid:
            children.append(child)
        return True

    win32gui.EnumChildWindows(hwnd, collect, None)
    return children[0] if children else None


# WMI singleton for elevated-process fallback (lazy initialized).
_c = None


def _get_wmi():
    """Return the WMI client, initializing it lazily."""
    global _c
    if _c is None and _HAS_WMI:
        import wmi
        _c = wmi.WMI()
    return _c


def get_app_name_wmi(hwnd: int) -> Optional[str]:
    """Return application name via WMI query (fallback for elevated processes)."""
    _require_win32()
    try:
        wmi_client = _get_wmi()
        if wmi_client is None:
            return None
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        for p in wmi_client.query(f"SELECT Name FROM Win32_Process WHERE ProcessId = {pid}"):
            return p.Name
    except Exception:
        return None
    return None


def get_app_path_wmi(hwnd: int) -> Optional[str]:
    """Return executable path via WMI query (fallback for elevated processes)."""
    _require_win32()
    try:
        wmi_client = _get_wmi()
        if wmi_client is None:
            return None
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        for p in wmi_client.query(
            f"SELECT ExecutablePath FROM Win32_Process WHERE ProcessId = {pid}"
        ):
            return p.ExecutablePath
    except Exception:
        return None
    return None


def get_current_window() -> dict:
    """Return a dict describing the current foreground window.

    Keys:
        hwnd: int - window handle (may be None)
        app: str - application executable name
        app_path: str | None - full executable path
        title: str - window title text
        timestamp: str - ISO-8601 UTC timestamp of observation
        process_terminated: bool - whether the process could not be queried

    Never raises; returns a safe empty dict on total failure.
    """
    if not _HAS_WIN32:
        return {
            "hwnd": None,
            "app": None,
            "app_path": None,
            "title": "",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "process_terminated": True,
        }

    now = time.time()
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now))

    hwnd = get_active_window_handle()
    if hwnd is None:
        return {
            "hwnd": None,
            "app": None,
            "app_path": None,
            "title": "",
            "timestamp": timestamp,
            "process_terminated": True,
        }

    # Check if UWP frame host; use real child window if available.
    app_name = get_app_name(hwnd)
    if app_name == FRAME_HOST_APP:
        child = get_uwp_app_window(hwnd)
        if child is not None:
            hwnd = child
            app_name = get_app_name(hwnd) or app_name

    title = get_window_title(hwnd)
    app_path = get_app_path(hwnd)

    # Fallback to WMI for elevated/admin processes where OpenProcess fails.
    if app_name is None:
        app_name = get_app_name_wmi(hwnd)
        app_path = get_app_path_wmi(hwnd)

    process_terminated = app_name is None and app_path is None

    return {
        "hwnd": hwnd,
        "app": app_name,
        "app_path": app_path,
        "title": title,
        "timestamp": timestamp,
        "process_terminated": process_terminated,
    }


if __name__ == "__main__":
    while True:
        info = get_current_window()
        print(
            f"Title: {info['title']!r}"
            f" App: {info['app']!r}"
            f" Path: {info['app_path']!r}"
            f" Terminated: {info['process_terminated']}"
        )
        time.sleep(1.0)
