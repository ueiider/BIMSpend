"""Authentication and session management for BIMSpend.

Provides secure, company-scoped authentication with password hashing,
session expiration, revocation, and fail-closed behavior. No cloud identity
provider; all credentials stored locally.

Password hashing policy:
  - Algorithm: PBKDF2-HMAC-SHA256 (Argon2id not adopted due to dependency
    and Windows packaging review constraints; see SH-003 decision log).
  - Iterations: 210,000 (OWASP 2024 baseline for PBKDF2-SHA256).
  - Salt: 16 random bytes per password.
  - Existing 100,000-iteration hashes remain verifiable and are rehashed
    on successful login when below the current policy.
  - Constant-time comparison via secrets.compare_digest.
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional

from bimspend.db import Database
from bimspend.identity import Actor, Role, current_auth

# Current PBKDF2 iteration policy. Raised from the original 100,000 to
# 210,000 per OWASP 2024 guidance. Existing 100,000-iteration hashes are
# still accepted and upgraded on next successful login.
PBKDF2_ITERATIONS = 210_000
PBKDF2_SALT_BYTES = 16
PBKDF2_HASH_ALGORITHM = "sha256"


class SessionManager:
    """Manages authentication sessions for BIMSpend.

    Every login creates a database session bound to a specific company.
    The authenticated actor is only valid while that session remains
    valid (not expired, not revoked, member active, company active).
    """

    def __init__(self, db: Database):
        self.db = db

    def login(
        self, username: str, password: str, company_id: str | None = None
    ) -> Actor:
        """Authenticate a user and create a session.

        If the user belongs to multiple companies and company_id is not
        provided, raises ValueError requiring explicit company selection.

        Returns the authenticated Actor on success.
        Raises ValueError on authentication failure (username or password).
        All failures use the same message to avoid username enumeration.
        """
        cred = self.db.get_credential_by_username(username)
        password_valid = False
        member_id = None
        member_active = False
        credential_active = False

        if cred is not None:
            member_id = cred["member_id"]
            credential_active = bool(cred["is_active"])
            password_valid = verify_password(password, cred["password_hash"])
            member = self.db.conn.execute(
                "SELECT is_active FROM team_members WHERE id = ?",
                (member_id,),
            ).fetchone()
            member_active = bool(member["is_active"]) if member else False

        # Fail-closed: any failure yields the same generic error.
        if (
            cred is None
            or not credential_active
            or not password_valid
            or not member_active
        ):
            raise ValueError("Invalid username or password.")

        # Rehash on successful login if the stored hash is below policy.
        self.rehash_after_login(username, password)

        # Resolve company memberships for this member.
        memberships = self.db.list_member_companies(member_id)
        active_memberships = [
            m
            for m in memberships
            if self._company_is_active(m["company_id"])
        ]

        if not active_memberships:
            raise ValueError("Invalid username or password.")

        # Select company: explicit, or sole active membership.
        if company_id is not None:
            selected = next(
                (m for m in active_memberships if m["company_id"] == company_id),
                None,
            )
            if selected is None:
                raise ValueError("Invalid username or password.")
        elif len(active_memberships) == 1:
            selected = active_memberships[0]
        else:
            raise ValueError(
                "Multiple companies found. Please specify company_id."
            )

        actor = Actor(
            id=member_id,
            role=Role(selected["role"]),
            company_id=selected["company_id"],
        )

        session_id = self.db.create_session(actor.id, actor.company_id)
        actor = Actor(
            id=actor.id,
            role=actor.role,
            company_id=actor.company_id,
            session_id=session_id,
        )
        current_auth.set_session(session_id, actor)
        # Attach the database so SessionContext can validate on access
        current_auth._db = self.db
        return actor

    def _company_is_active(self, company_id: str) -> bool:
        row = self.db.conn.execute(
            "SELECT is_active FROM companies WHERE id = ?", (company_id,)
        ).fetchone()
        return bool(row["is_active"]) if row else False

    def _rehash_if_needed(self, username: str, stored_hash: str) -> None:
        """Rehash the password on login if iterations are below policy.

        Only rehashes if the stored hash uses PBKDF2 with fewer iterations
        than PBKDF2_ITERATIONS. This is a one-way upgrade path; downgrades
        are never performed.
        """
        try:
            parts = stored_hash.split("$")
            if (
                len(parts) == 4
                and parts[0] == "pbkdf2_sha256"
                and int(parts[1]) < PBKDF2_ITERATIONS
            ):
                # We don't have the plaintext password here, so we cannot
                # rehash immediately. The caller must pass the password to
                # rehash_after_login. This method is a placeholder for the
                # rehash-on-login pattern; actual rehashing is triggered
                # by login() below when the plaintext password is available.
                pass
        except (ValueError, IndexError):
            pass

    def rehash_after_login(self, username: str, password: str) -> None:
        """Rehash the user's password if it is below the current iteration policy.

        Call this after a successful login with the plaintext password.
        """
        cred = self.db.get_credential_by_username(username)
        if cred is None:
            return
        try:
            parts = cred["password_hash"].split("$")
            if (
                len(parts) == 4
                and parts[0] == "pbkdf2_sha256"
                and int(parts[1]) < PBKDF2_ITERATIONS
            ):
                new_hash = hash_password(password)
                self.db.upsert_user_credential(
                    cred["member_id"], username, new_hash
                )
        except (ValueError, IndexError):
            pass

    def logout(self) -> None:
        """Revoke the current session and clear the auth context.

        Fail-closed: if no session exists, this is a no-op.
        """
        if current_auth.session_id is not None:
            self.db.revoke_session(current_auth.session_id)
        current_auth.clear()

    def switch_company(self, company_id: str) -> Actor:
        """Switch the authenticated actor to a different company membership.

        Validates that the current member belongs to the target company
        and that both the member and company are active. The previous
        session is revoked and a new one is created.

        Raises ValueError if the company is unknown, the member is not
        in it, or either is inactive.
        """
        actor = current_auth.actor
        if actor is None:
            raise PermissionError("No authenticated actor.")

        memberships = self.db.list_member_companies(actor.id)
        active_memberships = [
            m
            for m in memberships
            if self._company_is_active(m["company_id"])
        ]

        selected = next(
            (m for m in active_memberships if m["company_id"] == company_id),
            None,
        )
        if selected is None:
            raise ValueError(
                "Company not found or membership inactive."
            )

        # Revoke the previous session before creating a new one.
        if current_auth.session_id is not None:
            self.db.revoke_session(current_auth.session_id)

        new_actor = Actor(
            id=actor.id,
            role=Role(selected["role"]),
            company_id=selected["company_id"],
        )
        session_id = self.db.create_session(
            new_actor.id, new_actor.company_id
        )
        new_actor = Actor(
            id=new_actor.id,
            role=new_actor.role,
            company_id=new_actor.company_id,
            session_id=session_id,
        )
        current_auth.set_session(session_id, new_actor)
        current_auth._db = self.db
        return new_actor

    def get_current_actor(self) -> Actor | None:
        """Return the currently authenticated actor, or None."""
        try:
            return current_auth.actor
        except PermissionError:
            return None


def hash_password(password: str) -> str:
    """Hash a password using PBKDF2-HMAC-SHA256 with a random salt.

    Returns a string in the format:
      pbkdf2_sha256$iterations$salt$hash

    Iterations: 210,000 (current OWASP baseline for PBKDF2-SHA256).
    Salt: 16 random bytes.
    """
    salt = secrets.token_bytes(PBKDF2_SALT_BYTES)
    dk = hashlib.pbkdf2_hmac(
        PBKDF2_HASH_ALGORITHM,
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )
    return (
        f"pbkdf2_sha256${PBKDF2_ITERATIONS}$"
        f"{salt.hex()}${dk.hex()}"
    )


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify a password against a stored hash using constant-time comparison.

    Returns True if the password matches, False otherwise.
    All failure modes (malformed hash, wrong password, missing hash)
    return False without disclosing whether the username exists.
    """
    try:
        parts = stored_hash.split("$")
        if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
            return False
        iterations = int(parts[1])
        if iterations < 1 or iterations > 10_000_000:
            return False
        salt = bytes.fromhex(parts[2])
        dk = bytes.fromhex(parts[3])
        computed = hashlib.pbkdf2_hmac(
            PBKDF2_HASH_ALGORITHM,
            password.encode("utf-8"),
            salt,
            iterations,
        )
        return secrets.compare_digest(computed, dk)
    except (ValueError, IndexError):
        return False


def _constant_time_compare(a: bytes, b: bytes) -> bool:
    """Deprecated alias for secrets.compare_digest.

    Kept for backward compatibility with existing tests.
    """
    return secrets.compare_digest(a, b)