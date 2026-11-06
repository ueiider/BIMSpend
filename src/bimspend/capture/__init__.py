"""Capture package — BIMSpend native Windows activity capture.

Public API:
    CaptureController — lifecycle, consent, SQLite persistence
    CaptureState — lifecycle states
    CaptureConfig — configuration
    AFKDetector — Windows idle detection
    SessionLockDetector — Windows session lock detection
    HeartbeatManager — interval coordination
    RevitConnector — Read-only Revit API event observer
    StandaloneRevitObserver — Testable Revit observer (no Revit required)
    IPCChannel — Local named pipe IPC
    ProjectCorrelationEngine — Document-to-project correlation
    RevitEvent — Revit application/document event
    RevitDocumentIdentity — Revit document identity
    CorrelationConfidence — Correlation confidence level
    DocumentProjectMapping — Document-to-project mapping
    CorrelationEvidence — Correlation evidence record

ActivityWatch-derived code lives in capture/activitywatch_derived/
under MPL-2.0 license. See docs/open-source/ACTIVITYWATCH_SOURCE_MANIFEST.md.
"""

from .controller import CaptureController, CaptureState, CaptureConfig
from .afk_detector import AFKDetector, AFKState
from .session_lock import SessionLockDetector, SessionLockState
from .heartbeat import HeartbeatManager, HeartbeatEvent
from .revit_connector import (
    RevitConnector,
    StandaloneRevitObserver,
    RevitEvent,
    RevitDocumentIdentity,
)
from .revit_ipc import IPCChannel, IPCMessage, IPCMessageType
from .project_correlation import (
    ProjectCorrelationEngine,
    CorrelationConfidence,
    DocumentProjectMapping,
    CorrelationEvidence,
)

__all__ = [
    # Core capture
    "CaptureController",
    "CaptureState",
    "CaptureConfig",
    "AFKDetector",
    "AFKState",
    "SessionLockDetector",
    "SessionLockState",
    "HeartbeatManager",
    "HeartbeatEvent",
    # Revit connector
    "RevitConnector",
    "StandaloneRevitObserver",
    "RevitEvent",
    "RevitDocumentIdentity",
    # IPC
    "IPCChannel",
    "IPCMessage",
    "IPCMessageType",
    # Correlation
    "ProjectCorrelationEngine",
    "CorrelationConfidence",
    "DocumentProjectMapping",
    "CorrelationEvidence",
]
