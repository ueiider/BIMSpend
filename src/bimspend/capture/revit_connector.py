"""Native Revit activity detection connector.

Read-only Revit API integration that observes document and application
events without modifying any Revit data. All communication with BIMSpend
is via local IPC (named pipes or localhost socket).

MPL-2.0 engineering boundary: This module is BIMSpend proprietary code
that is *inspired by* ActivityWatch patterns but does not copy ActivityWatch
source code. It implements the Revit connector pattern described in the
PLAN_AUDIT_REPORT.md.

Design layers (kept separate):
1. Revit event capture (this file) — observes Revit API events
2. Local IPC (revit_ipc.py) — secure transport to BIMSpend
3. Project correlation (project_correlation.py) — maps documents to projects
4. SQLite persistence — via existing Database layer

No model geometry is read. No Revit transactions are started.
No project files are modified.
"""

from __future__ import annotations

import logging
import secrets
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Revit API availability
# ---------------------------------------------------------------------------

try:
    from Autodesk.Revit.DB import (
        Document,
        DocumentChangedEventArgs,
        DocumentClosingEventArgs,
        DocumentClosedEventArgs,
        DocumentOpenedEventArgs,
        ViewActivatedEventArgs,
    )
    from Autodesk.Revit.UI import UIApplication
    from Autodesk.Revit.UI.Events import ViewActivatedEventHandler

    _HAS_REVIT_API = True
except (ImportError, OSError):
    Document = None  # type: ignore
    DocumentChangedEventArgs = None  # type: ignore
    DocumentClosingEventArgs = None  # type: ignore
    DocumentClosedEventArgs = None  # type: ignore
    DocumentOpenedEventArgs = None  # type: ignore
    ViewActivatedEventArgs = None  # type: ignore
    UIApplication = None  # type: ignore
    ViewActivatedEventHandler = None  # type: ignore
    _HAS_REVIT_API = False


# ---------------------------------------------------------------------------
# Revit event types
# ---------------------------------------------------------------------------


class RevitEventType(Enum):
    """Types of Revit events that can be observed."""

    DOCUMENT_OPENED = "document_opened"
    DOCUMENT_CLOSING = "document_closing"
    DOCUMENT_CLOSED = "document_closed"
    DOCUMENT_CHANGED = "document_changed"
    VIEW_ACTIVATED = "view_activated"
    APPLICATION_IDLING = "application_idling"
    SESSION_STARTED = "session_started"
    SESSION_ENDED = "session_ended"


# ---------------------------------------------------------------------------
# Revit document identity
# ---------------------------------------------------------------------------


@dataclass
class RevitDocumentIdentity:
    """Identity of a Revit document.

    Uses multiple identifiers to avoid relying on any single one:
    - document_guid: Revit's internal UniqueId (stable across saves)
    - title_hash: Privacy-hashed document title
    - path_hash: Privacy-hashed document path (workshared central path)
    - process_id: Revit process ID
    - session_guid: BIMSpend session GUID
    """

    document_guid: str
    title_hash: str
    path_hash: Optional[str] = None
    central_path_hash: Optional[str] = None
    document_type: Optional[str] = None  # "workshared", "standalone", "cloud"
    process_id: Optional[int] = None
    session_guid: Optional[str] = None
    is_workshared: bool = False
    is_unsaved: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_guid": self.document_guid,
            "title_hash": self.title_hash,
            "path_hash": self.path_hash,
            "central_path_hash": self.central_path_hash,
            "document_type": self.document_type,
            "process_id": self.process_id,
            "session_guid": self.session_guid,
            "is_workshared": self.is_workshared,
            "is_unsaved": self.is_unsaved,
        }


def _hash_value(value: Optional[str]) -> Optional[str]:
    """Privacy hash a string value."""
    if value is None:
        return None
    import hashlib

    return f"[HASH:{hashlib.sha256(value.encode('utf-8')).hexdigest()[:8]}]"


# ---------------------------------------------------------------------------
# Revit event
# ---------------------------------------------------------------------------


@dataclass
class RevitEvent:
    """A Revit application/document event.

    Contains only metadata — no model geometry, no element data,
    no sensitive document content.
    """

    id: str
    event_type: RevitEventType
    timestamp: str  # ISO-8601 UTC
    process_id: int
    session_guid: str
    document_identity: Optional[RevitDocumentIdentity] = None
    view_name_hash: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp,
            "process_id": self.process_id,
            "session_guid": self.session_guid,
            "document_identity": (
                self.document_identity.to_dict() if self.document_identity else None
            ),
            "view_name_hash": self.view_name_hash,
            "metadata": self.metadata,
        }


# ---------------------------------------------------------------------------
# Revit connector
# ---------------------------------------------------------------------------


class RevitConnector:
    """Read-only Revit connector that observes application and document events.

    Subscribes to Revit API events and forwards them via a callback
    (typically to the local IPC layer for transmission to BIMSpend).

    Supports multiple Revit instances running simultaneously — each
    instance gets its own connector with its own session GUID.

    Design constraints:
    - Read-only: never starts Revit transactions, never modifies documents
    - No model geometry access
    - No high-frequency event processing (bounded payload)
    - Graceful degradation when Revit API is unavailable
    """

    def __init__(
        self,
        process_id: Optional[int] = None,
        session_guid: Optional[str] = None,
        on_event: Optional[Callable[[RevitEvent], None]] = None,
        company_id: Optional[str] = None,
    ):
        self.process_id = process_id or secrets.token_bytes(4).hex()
        self.session_guid = session_guid or secrets.token_urlsafe(16)
        self.company_id = company_id
        self.on_event = on_event

        self._revit_app: Optional[Any] = None
        self._document_lock = threading.Lock()
        self._active_documents: dict[str, RevitDocumentIdentity] = {}
        self._event_count = 0
        self._started_at: Optional[str] = None
        self._subscribed = False

        logger.info(
            "RevitConnector initialized: process_id=%s, session=%s",
            self.process_id,
            self.session_guid[:8],
        )

    # ------------------------------------------------------------------
    # Connection to Revit
    # ------------------------------------------------------------------

    def connect(self, revit_app: Any) -> bool:
        """Connect to a Revit UIApplication instance.

        Subscribes to document and view events. Returns True on success,
        False if Revit API is unavailable or subscription fails.
        """
        if not _HAS_REVIT_API:
            logger.warning("Revit API not available — connector runs in stub mode")
            self._started_at = datetime.now(timezone.utc).isoformat()
            self._emit_event(RevitEventType.SESSION_STARTED)
            return True

        if self._subscribed:
            logger.warning("Revit connector already subscribed")
            return True

        try:
            self._revit_app = revit_app

            # Subscribe to document events
            if hasattr(revit_app, "DocumentOpened"):
                revit_app.DocumentOpened += self._on_document_opened
            if hasattr(revit_app, "DocumentClosing"):
                revit_app.DocumentClosing += self._on_document_closing
            if hasattr(revit_app, "DocumentClosed"):
                revit_app.DocumentClosed += self._on_document_closed
            if hasattr(revit_app, "DocumentChanged"):
                revit_app.DocumentChanged += self._on_document_changed
            if hasattr(revit_app, "ViewActivated"):
                revit_app.ViewActivated += self._on_view_activated

            self._subscribed = True
            self._started_at = datetime.now(timezone.utc).isoformat()
            self._emit_event(RevitEventType.SESSION_STARTED)

            logger.info(
                "RevitConnector connected: session=%s, app=%s",
                self.session_guid[:8],
                type(revit_app).__name__,
            )
            return True

        except Exception as exc:
            logger.error("Failed to connect Revit connector: %s", exc)
            self._subscribed = False
            return False

    def disconnect(self) -> None:
        """Disconnect from Revit and unsubscribe from events."""
        if self._revit_app is not None and self._subscribed:
            try:
                if hasattr(self._revit_app, "DocumentOpened"):
                    self._revit_app.DocumentOpened -= self._on_document_opened
                if hasattr(self._revit_app, "DocumentClosing"):
                    self._revit_app.DocumentClosing -= self._on_document_closing
                if hasattr(self._revit_app, "DocumentClosed"):
                    self._revit_app.DocumentClosed -= self._on_document_closed
                if hasattr(self._revit_app, "DocumentChanged"):
                    self._revit_app.DocumentChanged -= self._on_document_changed
                if hasattr(self._revit_app, "ViewActivated"):
                    self._revit_app.ViewActivated -= self._on_view_activated
            except Exception as exc:
                logger.error("Error unsubscribing from Revit events: %s", exc)

        self._subscribed = False
        self._emit_event(RevitEventType.SESSION_ENDED)
        logger.info("RevitConnector disconnected: session=%s", self.session_guid[:8])

    # ------------------------------------------------------------------
    # Event handlers (Revlt API callbacks)
    # ------------------------------------------------------------------

    def _on_document_opened(
        self, sender: Any, args: DocumentOpenedEventArgs
    ) -> None:
        """Handle DocumentOpened event."""
        if not _HAS_REVIT_API or args is None:
            return

        doc = args.Document
        doc_identity = self._build_document_identity(doc)

        with self._document_lock:
            self._active_documents[doc_identity.document_guid] = doc_identity

        self._emit_event(
            RevitEventType.DOCUMENT_OPENED,
            document_identity=doc_identity,
            metadata={"is_workshared": doc_identity.is_workshared},
        )

    def _on_document_closing(
        self, sender: Any, args: DocumentClosingEventArgs
    ) -> None:
        """Handle DocumentClosing event."""
        if not _HAS_REVIT_API or args is None:
            return

        doc = args.Document
        doc_guid = doc.UniqueId if hasattr(doc, "UniqueId") else str(doc)

        with self._document_lock:
            self._active_documents.pop(doc_guid, None)

        self._emit_event(
            RevitEventType.DOCUMENT_CLOSING,
            document_identity=RevitDocumentIdentity(
                document_guid=doc_guid,
                title_hash=_hash_value(doc.Title if hasattr(doc, "Title") else ""),
            ),
        )

    def _on_document_closed(
        self, sender: Any, args: DocumentClosedEventArgs
    ) -> None:
        """Handle DocumentClosed event."""
        if not _HAS_REVIT_API or args is None:
            return

        doc = args.Document
        doc_guid = doc.UniqueId if hasattr(doc, "UniqueId") else str(doc)

        self._emit_event(
            RevitEventType.DOCUMENT_CLOSED,
            document_identity=RevitDocumentIdentity(
                document_guid=doc_guid,
                title_hash=_hash_value(doc.Title if hasattr(doc, "Title") else ""),
            ),
        )

    def _on_document_changed(
        self, sender: Any, args: DocumentChangedEventArgs
    ) -> None:
        """Handle DocumentChanged event.

        DocumentChanged fires frequently. We only record that a change
        occurred — we never read element data or geometry.
        """
        if not _HAS_REVIT_API or args is None:
            return

        doc = args.Document
        doc_guid = doc.UniqueId if hasattr(doc, "UniqueId") else str(doc)

        self._emit_event(
            RevitEventType.DOCUMENT_CHANGED,
            document_identity=RevitDocumentIdentity(
                document_guid=doc_guid,
                title_hash=_hash_value(doc.Title if hasattr(doc, "Title") else ""),
            ),
            metadata={"change_type": "document_changed"},
        )

    def _on_view_activated(
        self, sender: Any, args: ViewActivatedEventArgs
    ) -> None:
        """Handle ViewActivated event.

        Tracks which view is active within a document. Used to correlate
        document context with foreground window state.
        """
        if not _HAS_REVIT_API or args is None:
            return

        doc = args.Document
        doc_guid = doc.UniqueId if hasattr(doc, "UniqueId") else str(doc)

        view_name = ""
        if hasattr(args, "NewActiveView") and args.NewActiveView is not None:
            view_name = args.NewActiveView.Name or ""

        self._emit_event(
            RevitEventType.VIEW_ACTIVATED,
            document_identity=RevitDocumentIdentity(
                document_guid=doc_guid,
                title_hash=_hash_value(doc.Title if hasattr(doc, "Title") else ""),
            ),
            view_name_hash=_hash_value(view_name) if view_name else None,
        )

    # ------------------------------------------------------------------
    # Event emission
    # ------------------------------------------------------------------

    def _emit_event(
        self,
        event_type: RevitEventType,
        document_identity: Optional[RevitDocumentIdentity] = None,
        view_name_hash: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """Emit a Revit event to the callback."""
        event = RevitEvent(
            id=secrets.token_urlsafe(12),
            event_type=event_type,
            timestamp=datetime.now(timezone.utc).isoformat(),
            process_id=self.process_id,
            session_guid=self.session_guid,
            document_identity=document_identity,
            view_name_hash=view_name_hash,
            metadata=metadata or {},
        )

        self._event_count += 1

        if self.on_event is not None:
            try:
                self.on_event(event)
            except Exception as exc:
                logger.error("Error in Revit event callback: %s", exc)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_active_documents(self) -> list[RevitDocumentIdentity]:
        """Return list of currently active document identities."""
        with self._document_lock:
            return list(self._active_documents.values())

    def get_stats(self) -> dict[str, Any]:
        """Return connector statistics."""
        with self._document_lock:
            doc_count = len(self._active_documents)

        return {
            "session_guid": self.session_guid,
            "process_id": self.process_id,
            "company_id": self.company_id,
            "event_count": self._event_count,
            "active_document_count": doc_count,
            "subscribed": self._subscribed,
            "started_at": self._started_at,
            "has_revit_api": _HAS_REVIT_API,
        }


# ---------------------------------------------------------------------------
# Standalone Revit observer (for testing without Revit)
# ---------------------------------------------------------------------------


class StandaloneRevitObserver:
    """Standalone Revit observer for testing and non-Revit environments.

    Simulates Revit events for testing the correlation engine and IPC
    layer without requiring a Revit installation.
    """

    def __init__(
        self,
        process_id: str = "test-process",
        session_guid: Optional[str] = None,
        on_event: Optional[Callable[[RevitEvent], None]] = None,
        company_id: Optional[str] = None,
    ):
        self.connector = RevitConnector(
            process_id=process_id,
            session_guid=session_guid,
            on_event=on_event,
            company_id=company_id,
        )
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def simulate_document_opened(
        self, document_guid: str, title: str = "Test Document.rvt"
    ) -> None:
        """Simulate a document opened event."""
        doc_identity = RevitDocumentIdentity(
            document_guid=document_guid,
            title_hash=_hash_value(title),
            is_workshared=False,
            process_id=self.connector.process_id,
            session_guid=self.connector.session_guid,
        )
        self.connector._emit_event(
            RevitEventType.DOCUMENT_OPENED,
            document_identity=doc_identity,
        )

    def simulate_document_closed(self, document_guid: str) -> None:
        """Simulate a document closed event."""
        self.connector._emit_event(
            RevitEventType.DOCUMENT_CLOSED,
            document_identity=RevitDocumentIdentity(
                document_guid=document_guid,
                title_hash=_hash_value("Test Document.rvt"),
            ),
        )

    def simulate_view_activated(
        self, document_guid: str, view_name: str = "Level 1"
    ) -> None:
        """Simulate a view activated event."""
        self.connector._emit_event(
            RevitEventType.VIEW_ACTIVATED,
            document_identity=RevitDocumentIdentity(
                document_guid=document_guid,
                title_hash=_hash_value("Test Document.rvt"),
            ),
            view_name_hash=_hash_value(view_name),
        )

    def start(self) -> None:
        """Start the standalone observer."""
        self._running = True
        self.connector._emit_event(RevitEventType.SESSION_STARTED)
        self.connector._started_at = datetime.now(timezone.utc).isoformat()

    def stop(self) -> None:
        """Stop the standalone observer."""
        self._running = False
        self.connector._emit_event(RevitEventType.SESSION_ENDED)
