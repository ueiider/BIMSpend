"""Capture package __init__.

Public API:
    CaptureController — lifecycle, consent, SQLite persistence
    CaptureState — lifecycle states
    CaptureConfig — configuration
    AFKDetector — Windows idle detection
    SessionLockDetector — Windows session lock detection
    HeartbeatManager — interval coordination
"""

from .controller import CaptureController, CaptureState, CaptureConfig
from .afk_detector import AFKDetector, AFKState
from .session_lock import SessionLockDetector, SessionLockState
from .heartbeat import HeartbeatManager, HeartbeatEvent

__all__ = [
    "CaptureController",
    "CaptureState",
    "CaptureConfig",
    "AFKDetector",
    "AFKState",
    "SessionLockDetector",
    "SessionLockState",
    "HeartbeatManager",
    "HeartbeatEvent",
]
