"""Authentication and domain authorization for BIMSpend.

Actor IDs are authenticated session identifiers, not raw employee
handles. Never use this registry with real employees or exposed network
endpoints.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Role(str, Enum):
    DESIGNER = "designer"
    MANAGER = "manager"
    ADMINISTRATOR = "administrator"


@dataclass(frozen=True)
class Actor:
    id: str
    role: Role
    company_id: str | None = None


class AuthContext:
    """Holds the authenticated actor and their company context."""

    def __init__(self, actor: Actor | None = None):
        self._actor = actor

    @property
    def actor(self) -> Actor | None:
        return self._actor

    @property
    def is_authenticated(self) -> bool:
        return self._actor is not None

    @property
    def role(self) -> Role | None:
        return self._actor.role if self._actor else None

    def set_actor(self, actor: Actor) -> None:
        self._actor = actor

    def clear(self) -> None:
        self._actor = None


# Module-level auth context for the vertical slice. In a multi-threaded
# GUI application this would be replaced by a per-thread or per-request
# context, but for the single-user desktop app a module-level context
# is sufficient and keeps the code simple.
current_auth: AuthContext = AuthContext()


def require_actor(
    role: Role | None = None,
    owner_id: str | None = None,
    company_id: str | None = None,
) -> Actor:
    """Require an authenticated actor with the given role and optional
    ownership/company constraints.

    Raises PermissionError if:
      - No actor is authenticated
      - The actor's role does not match the required role
      - owner_id is given and the actor is not that owner
      - company_id is given and the actor is not in that company
    """
    actor = current_auth.actor
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