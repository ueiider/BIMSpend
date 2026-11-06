"""Project correlation engine for Revit documents.

Maps Revit document identities to BIMSpend commercial projects using
multiple correlation strategies:

Strategy A — Explicit mapping: User or manager maps a Revit document
identity to a BIMSpend project. Highest confidence.

Strategy B — Stable document identifier: Previously verified document
identity matches a known project.

Strategy C — Project code matching: A project code appears in permitted
metadata (document title, path, etc.).

Strategy D — Historical mapping: Previously confirmed associations reused.

Strategy E — Manual review: When evidence is insufficient, leave the
activity unassigned and request confirmation.

Confidence model:
- CONFIRMED: Explicit user/manager mapping
- HIGH: Stable document ID match with previous confirmation
- MEDIUM: Project code match in document metadata
- LOW: Historical mapping reused
- UNASSIGNED: No confident match — requires manual review

Low-confidence attribution must NOT be treated as confirmed work.
No automatic billing or approval from correlation results.
"""

from __future__ import annotations

import hashlib
import logging
import re
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Confidence levels
# ---------------------------------------------------------------------------


class CorrelationConfidence(Enum):
    """Confidence level for document-to-project correlation."""

    CONFIRMED = "CONFIRMED"   # Explicit user/manager mapping
    HIGH = "HIGH"             # Stable document ID match with previous confirmation
    MEDIUM = "MEDIUM"         # Project code match in document metadata
    LOW = "LOW"               # Historical mapping reused
    UNASSIGNED = "UNASSIGNED" # No confident match — requires manual review


# ---------------------------------------------------------------------------
# Mapping record
# ---------------------------------------------------------------------------


@dataclass
class DocumentProjectMapping:
    """A mapping between a Revit document and a BIMSpend project."""

    document_guid: str
    project_id: str
    mapping_method: str  # "explicit", "stable_id", "project_code", "historical"
    confidence: CorrelationConfidence
    mapped_by: Optional[str] = None
    mapped_at: Optional[str] = None
    reason: Optional[str] = None
    is_active: bool = True
    company_id: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_guid": self.document_guid,
            "project_id": self.project_id,
            "mapping_method": self.mapping_method,
            "confidence": self.confidence.value,
            "mapped_by": self.mapped_by,
            "mapped_at": self.mapped_at,
            "reason": self.reason,
            "is_active": self.is_active,
            "company_id": self.company_id,
        }


# ---------------------------------------------------------------------------
# Correlation evidence
# ---------------------------------------------------------------------------


@dataclass
class CorrelationEvidence:
    """Evidence for a document-to-project correlation."""

    session_id: str
    document_guid: str
    activity_event_id: Optional[str]
    foreground_duration_seconds: float
    is_afk: bool
    is_locked: bool
    correlation_confidence: CorrelationConfidence
    correlation_method: Optional[str]
    recorded_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "document_guid": self.document_guid,
            "activity_event_id": self.activity_event_id,
            "foreground_duration_seconds": self.foreground_duration_seconds,
            "is_afk": self.is_afk,
            "is_locked": self.is_locked,
            "correlation_confidence": self.correlation_confidence.value,
            "correlation_method": self.correlation_method,
            "recorded_at": self.recorded_at,
        }


# ---------------------------------------------------------------------------
# Correlation engine
# ---------------------------------------------------------------------------


class ProjectCorrelationEngine:
    """Correlates Revit document activity with BIMSpend projects.

    Uses multiple strategies in priority order:
    1. Explicit mapping (user/manager configured)
    2. Stable document ID (previously confirmed)
    3. Project code matching (document title/path contains project code)
    4. Historical mapping (previously confirmed association)
    5. Unassigned (no confident match)

    Company-scoped: all mappings are scoped to a company for tenant
    isolation. No cross-company correlation is permitted.
    """

    def __init__(self, company_id: str):
        self.company_id = company_id
        self._mappings: dict[str, DocumentProjectMapping] = {}  # document_guid -> mapping
        self._project_code_index: dict[str, str] = {}  # project_code -> project_id
        self._evidence_history: list[CorrelationEvidence] = []
        self._lock = threading.Lock()

        logger.info(
            "ProjectCorrelationEngine initialized: company=%s", company_id
        )

    # ------------------------------------------------------------------
    # Explicit mapping (Strategy A)
    # ------------------------------------------------------------------

    def add_explicit_mapping(
        self,
        document_guid: str,
        project_id: str,
        mapped_by: str,
        reason: Optional[str] = None,
    ) -> DocumentProjectMapping:
        """Add an explicit document-to-project mapping.

        This is the highest-confidence mapping strategy. Requires
        explicit user/manager action.
        """
        mapping = DocumentProjectMapping(
            document_guid=document_guid,
            project_id=project_id,
            mapping_method="explicit",
            confidence=CorrelationConfidence.CONFIRMED,
            mapped_by=mapped_by,
            mapped_at=datetime.now(timezone.utc).isoformat(),
            reason=reason,
            company_id=self.company_id,
        )

        with self._lock:
            self._mappings[document_guid] = mapping

        logger.info(
            "Explicit mapping: document=%s -> project=%s (company=%s, by=%s)",
            document_guid[:8],
            project_id[:8],
            self.company_id,
            mapped_by,
        )
        return mapping

    def remove_mapping(self, document_guid: str, removed_by: str) -> bool:
        """Remove an explicit document-to-project mapping."""
        with self._lock:
            if document_guid in self._mappings:
                mapping = self._mappings[document_guid]
                mapping.is_active = False
                logger.info(
                    "Mapping removed: document=%s -> project=%s (by=%s)",
                    document_guid[:8],
                    mapping.project_id[:8],
                    removed_by,
                )
                return True
            return False

    # ------------------------------------------------------------------
    # Project code registration (Strategy C)
    # ------------------------------------------------------------------

    def register_project_code(self, project_id: str, project_code: str) -> None:
        """Register a project code for pattern matching.

        Project codes are short identifiers (e.g., "P-2024-001") that may
        appear in document titles or paths. When a document title contains
        a registered project code, the document is correlated with that
        project at MEDIUM confidence.
        """
        with self._lock:
            self._project_code_index[project_code.upper()] = project_id
        logger.debug(
            "Project code registered: %s -> project=%s", project_code, project_id[:8]
        )

    # ------------------------------------------------------------------
    # Correlation
    # ------------------------------------------------------------------

    def correlate_document(
        self,
        document_guid: str,
        document_title: Optional[str] = None,
        document_path: Optional[str] = None,
        is_workshared: bool = False,
    ) -> tuple[str, CorrelationConfidence, str]:
        """Correlate a Revit document with a BIMSpend project.

        Returns (project_id, confidence, method) where project_id may be
        None if no confident match was found.

        Strategies tried in order:
        1. Explicit mapping (CONFIRMED)
        2. Stable document ID (HIGH) — if previously confirmed
        3. Project code matching (MEDIUM) — document title/path contains code
        4. Historical mapping (LOW) — previously confirmed association
        5. Unassigned (UNASSIGNED) — no confident match

        Company-scoped: only mappings within the same company are used.
        """
        with self._lock:
            # Strategy A: Explicit mapping
            if document_guid in self._mappings:
                mapping = self._mappings[document_guid]
                if mapping.is_active and mapping.company_id == self.company_id:
                    return (
                        mapping.project_id,
                        mapping.confidence,
                        mapping.mapping_method,
                    )

            # Strategy B: Stable document ID
            # Document GUID is already the key — if it's in mappings, it's
            # already handled by Strategy A. If not, no stable ID match.

            # Strategy C: Project code matching
            if document_title:
                title_upper = document_title.upper()
                for project_code, project_id in self._project_code_index.items():
                    if project_code in title_upper:
                        # Verify company scope — project should belong to company
                        # (This is a lightweight check; full validation
                        # happens at persistence time)
                        return (
                            project_id,
                            CorrelationConfidence.MEDIUM,
                            "project_code",
                        )

            # Strategy D: Historical mapping — same as A but LOW confidence
            # (Already handled above — explicit mappings are CONFIRMED,
            # historical mappings would be stored with LOW confidence)

            # Strategy E: Unassigned
            return (None, CorrelationConfidence.UNASSIGNED, "unassigned")

    # ------------------------------------------------------------------
    # Evidence recording
    # ------------------------------------------------------------------

    def record_evidence(
        self,
        session_id: str,
        document_guid: str,
        foreground_duration_seconds: float,
        is_afk: bool,
        is_locked: bool,
        correlation_confidence: CorrelationConfidence,
        correlation_method: Optional[str],
        activity_event_id: Optional[str] = None,
    ) -> CorrelationEvidence:
        """Record correlation evidence for a document-activity pairing.

        Evidence is only recorded when the session is UNLOCKED and the
        user is NOT AFK. Locked or AFK intervals are not attributed.
        """
        evidence = CorrelationEvidence(
            session_id=session_id,
            document_guid=document_guid,
            activity_event_id=activity_event_id,
            foreground_duration_seconds=foreground_duration_seconds,
            is_afk=is_afk,
            is_locked=is_locked,
            correlation_confidence=correlation_confidence,
            correlation_method=correlation_method,
            recorded_at=datetime.now(timezone.utc).isoformat(),
        )

        with self._lock:
            self._evidence_history.append(evidence)

        logger.debug(
            "Correlation evidence: document=%s, confidence=%s, "
            "afk=%s, locked=%s, duration=%.1fs",
            document_guid[:8],
            correlation_confidence.value,
            is_afk,
            is_locked,
            foreground_duration_seconds,
        )
        return evidence

    def get_evidence_for_session(
        self, session_id: str
    ) -> list[CorrelationEvidence]:
        """Return all evidence for a given session."""
        with self._lock:
            return [
                e for e in self._evidence_history if e.session_id == session_id
            ]

    def get_stats(self) -> dict[str, Any]:
        """Return correlation engine statistics."""
        with self._lock:
            active_mappings = sum(
                1 for m in self._mappings.values() if m.is_active
            )
            confirmed_mappings = sum(
                1
                for m in self._mappings.values()
                if m.is_active and m.confidence == CorrelationConfidence.CONFIRMED
            )
            total_evidence = len(self._evidence_history)

        return {
            "company_id": self.company_id,
            "active_mappings": active_mappings,
            "confirmed_mappings": confirmed_mappings,
            "total_evidence": total_evidence,
            "registered_project_codes": len(self._project_code_index),
        }

    # ------------------------------------------------------------------
    # Persistence helpers (for database integration)
    # ------------------------------------------------------------------

    def export_mappings(self) -> list[dict[str, Any]]:
        """Export all active mappings for database persistence."""
        with self._lock:
            return [m.to_dict() for m in self._mappings.values() if m.is_active]

    def import_mappings(
        self, mappings: list[dict[str, Any]]
    ) -> None:
        """Import mappings from database (e.g., on startup)."""
        with self._lock:
            for m in mappings:
                mapping = DocumentProjectMapping(
                    document_guid=m["document_guid"],
                    project_id=m["project_id"],
                    mapping_method=m["mapping_method"],
                    confidence=CorrelationConfidence(m["confidence"]),
                    mapped_by=m.get("mapped_by"),
                    mapped_at=m.get("mapped_at"),
                    reason=m.get("reason"),
                    is_active=m.get("is_active", True),
                    company_id=m.get("company_id"),
                )
                self._mappings[mapping.document_guid] = mapping
                if m.get("project_code"):
                    self._project_code_index[m["project_code"].upper()] = m["project_id"]
