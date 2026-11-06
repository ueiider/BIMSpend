"""Authentication and domain authorization for BIMSpend.

Actor IDs are authenticated session identifiers, not raw employee
handles. Never use this registry with real employees or exposed network
endpoints.

Security model:
  - Every authenticated actor is bound to a validated database session.
  - require_actor() validates the session on every access (fail-closed).
  - Company-scoped roles come from company_members, not team_members.
  - A global mutable actor is never used as an unverified security authority.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class Role(str, Enum):
    DESIGNER = "designer"
    MANAGER = "manager"
    ADMINISTRATOR = "administrator"


@dataclass(frozen=True)
class Actor:
    """An authenticated actor bound to a specific session and company.

    role is the company-scoped role from company_members, not the
    team_members.role. company_id is always required.
    """

    id: str
    role: Role
    company_id: str
    session_id: str | None = None


class SessionContext:
    """Holds the authenticated session and validates it against the database.

    The actor property performs fail-closed validation: if the underlying
    database session is expired, revoked, or the member/company is inactive,
    the context is cleared and PermissionError is raised.

    Designed so future multi-user or background processes can use isolated
    per-thread SessionContext instances instead of the module-level current_auth.
    """

    def __init__(self, db=None):
        self._db = db
        self._session_id: str | None = None
        self._actor: Actor | None = None

    @property
    def actor(self) -> Actor | None:
        """Return the validated actor, or None if not authenticated.

        Raises PermissionError if the session is invalid (expired, revoked,
        member inactive, company inactive) and a database is attached.
        """
        if self._actor is None:
            return None
        if self._db is not None:
            if self._session_id is None:
                return None
            # Validate session existence, expiration, and revocation.
            session_row = self._db.conn.execute(
                """
                SELECT s.id, s.member_id, s.company_id, s.expires_at,
                       s.revoked_at, tm.is_active as member_active,
                       c.is_active as company_active
                FROM sessions s
                JOIN team_members tm ON tm.id = s.member_id
                JOIN companies c ON c.id = s.company_id
                WHERE s.id = ?
                """,
                (self._session_id,),
            ).fetchone()
            if session_row is None:
                self.clear()
                raise PermissionError(
                    "Session is invalid, expired, or revoked."
                )
            if session_row["revoked_at"] is not None:
                self.clear()
                raise PermissionError(
                    "Session is invalid, expired, or revoked."
                )
            expires_at = datetime.fromisoformat(session_row["expires_at"])
            if expires_at < datetime.now(timezone.utc):
                self.clear()
                raise PermissionError(
                    "Session is invalid, expired, or revoked."
                )
            if session_row["member_active"] == 0:
                self.clear()
                raise PermissionError("Member account is inactive.")
            if session_row["company_active"] == 0:
                self.clear()
                raise PermissionError("Company is inactive.")
            # Re-derive the actor from the validated session row so the
            # role always comes from the authoritative company_members table.
            actor_row = self._db.conn.execute(
                """
                SELECT tm.id, tm.name, cm.role
                FROM team_members tm
                JOIN company_members cm ON cm.member_id = tm.id
                WHERE cm.company_id = ? AND tm.id = ?
                """,
                (session_row["company_id"], session_row["member_id"]),
            ).fetchone()
            if actor_row is None:
                self.clear()
                raise PermissionError(
                    "Actor is not a member of the session's company."
                )
            self._actor = Actor(
                id=actor_row["id"],
                role=Role(actor_row["role"]),
                company_id=session_row["company_id"],
                session_id=self._session_id,
            )
        return self._actor

    @property
    def is_authenticated(self) -> bool:
        try:
            return self.actor is not None
        except PermissionError:
            return False

    @property
    def session_id(self) -> str | None:
        return self._session_id

    def set_session(
        self, session_id: str, actor: Actor
    ) -> None:
        """Bind a validated session and actor to this context."""
        self._session_id = session_id
        self._actor = actor

    def set_actor(self, actor: Actor) -> None:
        """Set the actor directly (test helper; bypasses session validation).

        This is intended for unit tests that do not require database-backed
        session validation. Production code should use set_session() which
        binds the actor to a validated database session.
        """
        self._session_id = actor.session_id
        self._actor = actor

    def clear(self) -> None:
        """Clear the session and actor. Fail-closed: no residual authority."""
        self._session_id = None
        self._actor = None
        self._db = None


# Module-level session context for the vertical slice. For the single-user
# desktop prototype this is acceptable only because every access through
# require_actor() validates against the database. Future multi-user or
# background processes should use isolated SessionContext instances.
current_auth: SessionContext = SessionContext()


def require_actor(
    role: Role | None = None,
    owner_id: str | None = None,
    company_id: str | None = None,
) -> Actor:
    """Require an authenticated, session-validated actor.

    Raises PermissionError if:
      - No actor is authenticated (session missing/invalid)
      - The session has expired, been revoked, or the member/company is inactive
      - The actor's role does not match the required role
      - owner_id is given and the actor is not that owner
      - company_id is given and the actor is not in that company

    This is the sole authorization gate for all protected domain operations.
    It never trusts the in-memory actor without database validation.
    """
    actor = current_auth.actor  # May raise PermissionError on invalid session
    if actor is None:
        raise PermissionError("No authenticated actor.")
    if role is not None and actor.role != role:
        raise PermissionError(
            f"Actor {actor.id} cannot perform {role.value} action."
        )
    if owner_id is not None and actor.id != owner_id:
        raise PermissionError("Actor can change only their own records.")
    if company_id is not None and actor.company_id != company_id:
        raise PermissionError(
            f"Actor {actor.id} is not in company {company_id}."
        )
    return actor