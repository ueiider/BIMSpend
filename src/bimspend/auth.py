"""Authentication and session management for BIMSpend.

Provides secure, company-scoped authentication with password hashing,
session expiration, and fail-closed behavior. No cloud identity provider;
all credentials stored locally with pbkdf2_hmac hashing.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional

from bimspend.db import Database
from bimspend.identity import Actor, Role, current_auth, require_actor


class SessionManager:
    """Manages authentication sessions for BIMSpend."""

    def __init__(self, db: Database):
        self.db = db

    def login(self, username: str, password: str) -> Actor:
        """Authenticate a user and create a session.

        Returns the authenticated Actor on success.
        Raises ValueError on authentication failure.
        """
        cred = self.db.get_credential_by_username(username)
        if cred is None or not cred["is_active"] or not cred["member_active"]:
            raise ValueError("Invalid username or password.")

        stored_hash = cred["password_hash"]
        if not verify_password(password, stored_hash):
            raise ValueError("Invalid username or password.")

        member = self.db.conn.execute(
            "SELECT id, name, role, is_active FROM team_members WHERE id = ?",
            (cred["member_id"],),
        ).fetchone()
        if member is None or member["is_active"] == 0:
            raise ValueError("Invalid username or password.")

        # Get the member's primary company (first company they belong to)
        company_row = self.db.conn.execute(
            """
            SELECT cm.company_id
            FROM company_members cm
            WHERE cm.member_id = ?
            ORDER BY cm.joined_at ASC
            LIMIT 1
            """,
            (cred["member_id"],),
        ).fetchone()

        company_id = company_row["company_id"] if company_row else None

        actor = Actor(
            id=cred["member_id"],
            role=Role(member["role"]),
            company_id=company_id,
        )

        session_id = self.db.create_session(actor.id, company_id)
        current_auth.set_actor(actor)
        return actor

    def logout(self) -> None:
        """Revoke the current session and clear the auth context."""
        if current_auth.actor is not None:
            self.db.revoke_all_sessions_for_member(current_auth.actor.id)
        current_auth.clear()

    def get_current_actor(self) -> Actor | None:
        """Return the currently authenticated actor, or None."""
        return current_auth.actor


def hash_password(password: str) -> str:
    """Hash a password using pbkdf2_hmac with a random salt.

    Returns a string in the format: pbkdf2_sha256$iterations$salt$hash
    """
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        100_000,
    )
    return f"pbkdf2_sha256$100000${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify a password against a stored hash."""
    try:
        parts = stored_hash.split("$")
        if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
            return False
        iterations = int(parts[1])
        salt = bytes.fromhex(parts[2])
        dk = bytes.fromhex(parts[3])
        computed = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            iterations,
        )
        return _constant_time_compare(computed, dk)
    except (ValueError, IndexError):
        return False


def _constant_time_compare(a: bytes, b: bytes) -> bool:
    """Constant-time comparison to prevent timing attacks."""
    if len(a) != len(b):
        return False
    result = 0
    for x, y in zip(a, b):
        result |= x ^ y
    return result == 0