"""Windows session lock / unlock detector.

Detects Windows session lock (Win+L, screen saver, etc.) using
WTSRegisterSessionNotification for reliable event-driven notification,
with WTSQuerySessionInformation polling as a fallback.

States: LOCKED, UNLOCKED, UNKNOWN

This detector does not require administrator privileges.
It creates a hidden message-only window to receive session change
notifications, and falls back to polling when notification registration
is unavailable.

On non-Windows platforms or when WTSAPI32 functions are unavailable,
the detector operates in safe fail-safe mode: state transitions can be
set directly (for testing) but automatic detection always returns
UNKNOWN.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes as wintypes
import logging
import threading
import time
from enum import Enum
from typing import Callable, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Windows API availability detection
# ---------------------------------------------------------------------------

try:
    _user32 = ctypes.windll.user32
    _kernel32 = ctypes.windll.kernel32
    try:
        _wtsapi32 = ctypes.windll.wtsapi32
    except (AttributeError, OSError):
        _wtsapi32 = None
    _HAS_WTSAPI = _wtsapi32 is not None
except (AttributeError, OSError):
    _user32 = None
    _wtsapi32 = None
    _kernel32 = None
    _HAS_WTSAPI = False


def _require_wtsapi() -> None:
    """Raise a clear error if WTSAPI32 is not available."""
    if not _HAS_WTSAPI:
        raise ImportError(
            "WTSAPI32 is required for Windows session lock detection. "
            "This module is Windows-only."
        )


def _get_func(module, name):
    """Safely get a function from a Windows DLL, returning None if missing."""
    if module is None:
        return None
    try:
        return getattr(module, name)
    except (AttributeError, OSError):
        return None


# ---------------------------------------------------------------------------
# Windows API constants (from WtsApi32.h / WinUser.h)
# ---------------------------------------------------------------------------

WTS_SESSION_LOCK = 0x7
WTS_SESSION_UNLOCK = 0x8

NOTIFY_FOR_THIS_SESSION = 0

WM_WTSSESSION_CHANGE = 0x2B1

# WTS_CONNECTSTATE_CLASS values
WTSActive = 0
WTSConnected = 1
WTSConnectQuery = 2
WTSSend = 3
WTSDisconnected = 4
WTSIdle = 5
WTSListen = 6
WTSWait = 7
WTSInitial = 8


class SessionLockState(Enum):
    LOCKED = "locked"
    UNLOCKED = "unlocked"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Windows API structure definitions (defined before use)
# ---------------------------------------------------------------------------

class _WNDCLASSW(ctypes.Structure):
    _fields_ = [
        ("style", wintypes.UINT),
        ("lpfnWndProc", ctypes.c_void_p),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", ctypes.c_void_p),
        ("hIcon", ctypes.c_void_p),
        ("hCursor", ctypes.c_void_p),
        ("hbrBackground", ctypes.c_void_p),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
    ]


class _MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("message", wintypes.UINT),
        ("wParam", wintypes.WPARAM),
        ("lParam", wintypes.LPARAM),
        ("time", wintypes.DWORD),
        ("pt", wintypes.POINT),
    ]


# Window procedure callback type (LRESULT = c_long)
_WNDPROC = ctypes.WINFUNCTYPE(
    ctypes.c_long,
    wintypes.HWND,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
)


# ---------------------------------------------------------------------------
# Windows API function declarations (only set up if WTSAPI32 is available)
# ---------------------------------------------------------------------------

_set_argtypes: set = set()


def _safe_set_argtypes(func, argtypes, restype):
    """Safely set argtypes/restype on a Windows API function."""
    if func is None:
        return
    try:
        func.argtypes = argtypes
        func.restype = restype
        _set_argtypes.add(func.__name__)
    except (AttributeError, OSError):
        pass


if _HAS_WTSAPI:

    # WTSRegisterSessionNotification(HWND hWnd, DWORD dwFlags) -> BOOL
    _safe_set_argtypes(
        _get_func(_wtsapi32, "WTSRegisterSessionNotification"),
        [wintypes.HWND, wintypes.DWORD],
        wintypes.BOOL,
    )

    # WTSUnRegisterSessionNotification(HWND hWnd) -> BOOL
    _safe_set_argtypes(
        _get_func(_wtsapi32, "WTSUnRegisterSessionNotification"),
        [wintypes.HWND],
        wintypes.BOOL,
    )

    # WTSQuerySessionInformation(...) -> BOOL
    _safe_set_argtypes(
        _get_func(_wtsapi32, "WTSQuerySessionInformation"),
        [
            wintypes.HANDLE,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.POINTER(ctypes.c_void_p),
            ctypes.POINTER(wintypes.DWORD),
        ],
        wintypes.BOOL,
    )

    # WTSFreeMemory(PVOID pBuffer) -> None
    _safe_set_argtypes(
        _get_func(_wtsapi32, "WTSFreeMemory"),
        [ctypes.c_void_p],
        None,
    )

    # GetCurrentProcessId() -> DWORD
    _safe_set_argtypes(
        _kernel32.GetCurrentProcessId,
        [],
        wintypes.DWORD,
    )

    # GetMessageW(...) -> BOOL
    _safe_set_argtypes(
        _user32.GetMessageW,
        [
            ctypes.POINTER(wintypes.MSG),
            wintypes.HWND,
            wintypes.UINT,
            wintypes.UINT,
        ],
        wintypes.BOOL,
    )

    _safe_set_argtypes(
        _user32.TranslateMessage,
        [ctypes.POINTER(wintypes.MSG)],
        wintypes.BOOL,
    )

    _safe_set_argtypes(
        _user32.DispatchMessageW,
        [ctypes.POINTER(wintypes.MSG)],
        ctypes.c_long,
    )

    _safe_set_argtypes(
        _user32.PostQuitMessage,
        [wintypes.INT],
        None,
    )

    # DefWindowProcW(...) -> LRESULT (c_long)
    _safe_set_argtypes(
        _user32.DefWindowProcW,
        [
            wintypes.HWND,
            wintypes.UINT,
            wintypes.WPARAM,
            wintypes.LPARAM,
        ],
        ctypes.c_long,
    )

    # RegisterClassW(...) -> ATOM
    _safe_set_argtypes(
        _user32.RegisterClassW,
        [ctypes.POINTER(_WNDCLASSW)],
        wintypes.ATOM,
    )

    # CreateWindowExW(...) -> HWND
    _safe_set_argtypes(
        _user32.CreateWindowExW,
        [
            wintypes.DWORD,
            wintypes.LPCWSTR,
            wintypes.LPCWSTR,
            wintypes.DWORD,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            wintypes.HWND,
            wintypes.HMENU,
            wintypes.HINSTANCE,
            wintypes.LPVOID,
        ],
        wintypes.HWND,
    )

    # DestroyWindow(HWND) -> BOOL
    _safe_set_argtypes(
        _user32.DestroyWindow,
        [wintypes.HWND],
        wintypes.BOOL,
    )

    # UnregisterClassW(LPCWSTR, HINSTANCE) -> BOOL
    _safe_set_argtypes(
        _user32.UnregisterClassW,
        [wintypes.LPCWSTR, wintypes.HINSTANCE],
        wintypes.BOOL,
    )

    # GetModuleHandleW(LPCWSTR) -> HINSTANCE
    _safe_set_argtypes(
        _kernel32.GetModuleHandleW,
        [wintypes.LPCWSTR],
        wintypes.HINSTANCE,
    )


def _func_available(func) -> bool:
    """Check if a Windows API function was successfully configured."""
    return func is not None and func.__name__ in _set_argtypes


class SessionLockDetector:
    """Detects Windows session lock/unlock events.

    Uses WTSRegisterSessionNotification for event-driven notification
    of session lock (WTS_SESSION_LOCK) and unlock (WTS_SESSION_UNLOCK)
    events. Falls back to polling WTSQuerySessionInformation for
    WTSConnectState when notification registration is unavailable.

    States:
        LOCKED  - Workstation is locked (Win+L, screen saver, etc.)
        UNLOCKED - Workstation is unlocked and in use
        UNKNOWN - State cannot be determined (safe fail-safe)

    This detector does not require administrator privileges and does not
    create a permanently running external service. It uses a hidden
    message-only window for notification reception, with a polling
    fallback thread.

    When the session is locked or unknown, capture should NOT attribute
    time as active work.

    On non-Windows platforms or when WTSAPI32 functions are unavailable,
    state transitions can be set directly via _set_state() for testing,
    but automatic detection always returns UNKNOWN.
    """

    _CLASS_NAME = "BIMSpendSessionLockDetector"
    _registered_classes: set = set()

    def __init__(self, poll_interval: float = 10.0):
        self.poll_interval = poll_interval
        self.state = SessionLockState.UNKNOWN
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._notification_thread: Optional[threading.Thread] = None
        self._on_lock: Optional[Callable[[], None]] = None
        self._on_unlock: Optional[Callable[[], None]] = None
        self._last_known_state: Optional[SessionLockState] = None
        self._hwnd: Optional[int] = None
        self._notification_available: bool = False
        self._stop_event = threading.Event()

    # ------------------------------------------------------------------
    # Callback registration
    # ------------------------------------------------------------------

    def set_callbacks(
        self,
        on_lock: Optional[Callable[[], None]] = None,
        on_unlock: Optional[Callable[[], None]] = None,
    ) -> None:
        self._on_lock = on_lock
        self._on_unlock = on_unlock

    # ------------------------------------------------------------------
    # State queries
    # ------------------------------------------------------------------

    def is_locked(self) -> bool:
        return self.state == SessionLockState.LOCKED

    def is_unlocked(self) -> bool:
        return self.state == SessionLockState.UNLOCKED

    def is_unknown(self) -> bool:
        return self.state == SessionLockState.UNKNOWN

    # ------------------------------------------------------------------
    # State management (used internally and for testing)
    # ------------------------------------------------------------------

    def _set_state(self, new_state: SessionLockState) -> None:
        """Atomically update state and fire callbacks."""
        with self._lock:
            if new_state == self.state:
                return
            old_state = self.state
            self.state = new_state
            logger.info(
                "Session lock state transition: %s -> %s",
                old_state.value,
                new_state.value,
            )

        # Fire callbacks outside the lock to avoid deadlocks
        if new_state == SessionLockState.LOCKED and self._on_lock:
            try:
                self._on_lock()
            except Exception as exc:
                logger.error("Lock callback error: %s", exc)
        elif new_state == SessionLockState.UNLOCKED and self._on_unlock:
            try:
                self._on_unlock()
            except Exception as exc:
                logger.error("Unlock callback error: %s", exc)

    # ------------------------------------------------------------------
    # Notification window management
    # ------------------------------------------------------------------

    @classmethod
    def _register_window_class(cls) -> bool:
        """Register the hidden message window class (once per process)."""
        if not _HAS_WTSAPI:
            return False
        if not _func_available(_user32.RegisterClassW):
            return False
        if cls._CLASS_NAME in cls._registered_classes:
            return True

        hinstance = _kernel32.GetModuleHandleW(None)
        wndclass = _WNDCLASSW()
        wndproc = _WNDPROC(cls._window_proc)
        # Keep a reference so the callback isn't garbage collected
        cls._wndproc_ref = wndproc
        wndclass.lpfnWndProc = ctypes.cast(wndproc, ctypes.c_void_p)
        wndclass.hInstance = hinstance
        wndclass.lpszClassName = cls._CLASS_NAME

        atom = _user32.RegisterClassW(ctypes.byref(wndclass))
        if atom:
            cls._registered_classes.add(cls._CLASS_NAME)
            return True
        return False

    @staticmethod
    @_WNDPROC
    def _window_proc(
        hwnd: wintypes.HWND,
        msg: wintypes.UINT,
        wparam: wintypes.WPARAM,
        lparam: wintypes.LPARAM,
    ) -> ctypes.c_long:
        """Window procedure for session change notifications."""
        if msg == WM_WTSSESSION_CHANGE:
            event = wparam
            if event == WTS_SESSION_LOCK:
                logger.debug("WTS_SESSION_LOCK received via notification")
            elif event == WTS_SESSION_UNLOCK:
                logger.debug("WTS_SESSION_UNLOCK received via notification")
        return _user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    def _create_notification_window(self) -> Optional[int]:
        """Create a hidden message-only window for session notifications.

        Returns the window handle, or None if creation failed or WTSAPI32
        is not available.
        """
        if not _HAS_WTSAPI:
            return None
        if not _func_available(_user32.RegisterClassW):
            return None
        if not _func_available(_user32.CreateWindowExW):
            return None
        if not self._register_window_class():
            return None

        hinstance = _kernel32.GetModuleHandleW(None)
        # HWND_MESSAGE = (HWND)-1, used for message-only windows
        HWND_MESSAGE = ctypes.c_void_p(-1).value
        hwnd = _user32.CreateWindowExW(
            0,  # dwExStyle
            self._CLASS_NAME,
            None,  # lpWindowName
            0,  # dwStyle (no visible window)
            0, 0, 0, 0,  # x, y, nWidth, nHeight
            HWND_MESSAGE,  # hWndParent (message-only window)
            None,  # hMenu
            hinstance,  # hInstance
            None,  # lpParam
        )
        if not hwnd:
            logger.debug(
                "Failed to create notification window: error %d",
                _kernel32.GetLastError(),
            )
            return None

        # Register for session notifications
        reg_func = _get_func(_wtsapi32, "WTSRegisterSessionNotification")
        if _func_available(reg_func):
            if reg_func(hwnd, NOTIFY_FOR_THIS_SESSION):
                self._notification_available = True
                logger.debug(
                    "Session notification registered for window %d", hwnd
                )
            else:
                logger.debug(
                    "WTSRegisterSessionNotification failed: error %d",
                    _kernel32.GetLastError(),
                )
                self._notification_available = False
        else:
            self._notification_available = False

        return hwnd

    def _destroy_notification_window(self) -> None:
        """Destroy the notification window and unregister."""
        if self._hwnd is not None:
            unreg_func = _get_func(_wtsapi32, "WTSUnRegisterSessionNotification")
            if self._notification_available and _func_available(unreg_func):
                unreg_func(self._hwnd)
            if _func_available(_user32.DestroyWindow):
                _user32.DestroyWindow(self._hwnd)
            self._hwnd = None
            self._notification_available = False

    # ------------------------------------------------------------------
    # Polling fallback
    # ------------------------------------------------------------------

    def _query_lock_state_via_wts(self) -> SessionLockState:
        """Query session state via WTSQuerySessionInformation.

        Uses WTSConnectState to determine if the session is active
        (unlocked) or disconnected/locked.
        """
        qsi_func = _get_func(_wtsapi32, "WTSQuerySessionInformation")
        free_func = _get_func(_wtsapi32, "WTSFreeMemory")
        if not _HAS_WTSAPI or not _func_available(qsi_func):
            return SessionLockState.UNKNOWN
        try:
            session_id = _kernel32.GetCurrentProcessId()
            buffer = ctypes.c_void_p()
            bytes_returned = wintypes.DWORD()

            if qsi_func(
                wintypes.HANDLE(0),  # WTS_CURRENT_SERVER_HANDLE
                session_id,
                7,  # WTSConnectState
                ctypes.byref(buffer),
                ctypes.byref(bytes_returned),
            ):
                state = ctypes.cast(
                    buffer, ctypes.POINTER(wintypes.DWORD)
                ).contents.value
                if free_func:
                    free_func(buffer)

                # WTSActive or WTSConnected means unlocked
                # WTSDisconnected, WTSIdle, WTSWait, WTSInitial mean locked/unknown
                if state in (WTSActive, WTSConnected):
                    return SessionLockState.UNLOCKED
                else:
                    return SessionLockState.LOCKED
        except Exception as exc:
            logger.debug("WTSQuerySessionInformation failed: %s", exc)

        return SessionLockState.UNKNOWN

    # ------------------------------------------------------------------
    # Notification message pump thread
    # ------------------------------------------------------------------

    def _notification_pump(self) -> None:
        """Run a message pump for the notification window.

        This processes WM_WTSSESSION_CHANGE messages and updates
        the detector state accordingly.
        """
        if not _HAS_WTSAPI:
            return
        if not _func_available(_user32.GetMessageW):
            return
        if not _func_available(_user32.TranslateMessage):
            return
        if not _func_available(_user32.DispatchMessageW):
            return

        msg = _MSG()
        while self._running and not self._stop_event.is_set():
            result = _user32.GetMessageW(
                ctypes.byref(msg), None, 0, 0
            )
            if result == 0:
                # WM_QUIT received
                break
            if result == -1:
                # Error
                break

            if msg.message == WM_WTSSESSION_CHANGE:
                self._handle_session_change(msg.wParam)

            _user32.TranslateMessage(ctypes.byref(msg))
            _user32.DispatchMessageW(ctypes.byref(msg))

    def _handle_session_change(self, event: wintypes.WPARAM) -> None:
        """Handle a WM_WTSSESSION_CHANGE notification."""
        if event == WTS_SESSION_LOCK:
            self._set_state(SessionLockState.LOCKED)
        elif event == WTS_SESSION_UNLOCK:
            self._set_state(SessionLockState.UNLOCKED)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def poll(self) -> SessionLockState:
        """Poll current lock state.

        Uses the notification-based state if available, otherwise falls
        back to WTSQuerySessionInformation. Returns the current state.
        """
        # If we have notification-based state, trust it
        if self._notification_available:
            with self._lock:
                return self.state

        # Fall back to WTSQuerySessionInformation
        new_state = self._query_lock_state_via_wts()
        with self._lock:
            if new_state != self.state:
                old_state = self.state
                self.state = new_state
                logger.info(
                    "Session lock state transition (poll): %s -> %s",
                    old_state.value,
                    new_state.value,
                )
                if new_state == SessionLockState.LOCKED and self._on_lock:
                    try:
                        self._on_lock()
                    except Exception as exc:
                        logger.error("Lock callback error: %s", exc)
                elif new_state == SessionLockState.UNLOCKED and self._on_unlock:
                    try:
                        self._on_unlock()
                    except Exception as exc:
                        logger.error("Unlock callback error: %s", exc)
            return self.state

    def start(self) -> None:
        """Start the detector.

        Creates a notification window and starts the message pump thread.
        If notification registration fails, falls back to polling.
        On non-Windows platforms, this is a no-op that sets _running=True
        but does not create any windows or threads.
        """
        if self._running:
            return

        self._stop_event.clear()
        self._running = True

        if _HAS_WTSAPI:
            # Try to create notification window
            hwnd = self._create_notification_window()
            if hwnd is not None:
                self._hwnd = hwnd
                self._notification_thread = threading.Thread(
                    target=self._notification_pump, daemon=True
                )
                self._notification_thread.start()
            else:
                # Fall back to polling-only mode
                self._notification_available = False

            # Start polling thread as fallback/secondary check
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()

    def stop(self) -> None:
        """Stop the detector and clean up resources."""
        self._running = False
        self._stop_event.set()

        # Post quit message to notification pump if running
        if self._hwnd is not None and _func_available(
            _get_func(_user32, "PostQuitMessage")
        ):
            _user32.PostQuitMessage(0)

        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        if self._notification_thread is not None:
            self._notification_thread.join(timeout=2.0)
            self._notification_thread = None

        self._destroy_notification_window()

    def _run(self) -> None:
        """Polling fallback loop."""
        while self._running and not self._stop_event.is_set():
            try:
                if not self._notification_available:
                    # Only poll if notifications aren't available
                    self.poll()
            except Exception as exc:
                logger.error("Session lock poll error: %s", exc)
            # Sleep in small chunks to respond to stop quickly
            end = time.time() + self.poll_interval
            while time.time() < end and self._running and not self._stop_event.is_set():
                time.sleep(min(0.1, end - time.time()))
