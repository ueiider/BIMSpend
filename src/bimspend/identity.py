"""Synthetic preview identities and domain authorization.

Actor IDs are demonstration inputs, not authenticated sessions. Never use
this registry with real employees or exposed network endpoints.
"""
from dataclasses import dataclass
from enum import Enum


class Role(str, Enum):
    DESIGNER = "designer"
    MANAGER = "manager"


@dataclass(frozen=True)
class Actor:
    id: str
    role: Role


PREVIEW_ACTORS = {
    "designer_01": Actor("designer_01", Role.DESIGNER),
    "designer_02": Actor("designer_02", Role.DESIGNER),
    "manager_01": Actor("manager_01", Role.MANAGER),
    "manager_demo": Actor("manager_demo", Role.MANAGER),
    "billing_demo": Actor("billing_demo", Role.MANAGER),
}


def require_actor(actor_id: str, role: Role, owner_id: str | None = None) -> Actor:
    actor = PREVIEW_ACTORS.get(actor_id)
    if actor is None or actor.role != role:
        raise PermissionError(f"Preview actor cannot perform {role.value} action.")
    if owner_id is not None and actor.id != owner_id:
        raise PermissionError("Designer can change only their own time.")
    return actor
