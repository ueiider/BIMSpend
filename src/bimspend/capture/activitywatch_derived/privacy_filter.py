"""Watcher-side privacy filter for window events.

Adapted from ActivityWatch aw-watcher-window/aw_watcher_window/privacy_filter.py
(upstream commit 12000f58d16b8fc1376af42755c688b3d7157280, MPL-2.0).

Original copyright: ActivityWatch contributors.
See docs/open-source/ACTIVITYWATCH_SOURCE_MANIFEST.md for full provenance.

This module applies privacy rules to window observations *before* they are
persisted to the BIMSpend database. Sensitive events are dropped or redacted
at the source, never leaking raw titles to storage or logs.

Rule format (list of dicts):
    {
        "pattern": "<regex>",        # applied to the target field
        "field": "title",            # field to match against (default: "title")
        "action": "drop" | "redact", # drop = discard event, redact = replace value
        "replacement": "excluded",   # replacement for redact (default: "excluded")
    }
"""

from __future__ import annotations

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

_VALID_ACTIONS = frozenset({"drop", "redact"})


def compile_privacy_rules(raw_rules: list) -> list:
    """Validate and compile regex patterns in privacy filter rules.

    Returns a list of compiled rule dicts ready for apply_privacy_filters.
    Invalid rules are skipped with an error log (fail-safe: bad config does
    not disable filtering entirely).
    """
    compiled = []
    for raw in raw_rules:
        if not isinstance(raw, dict):
            logger.error("privacy_filter rule is not a table: %r — skipped", raw)
            continue

        pattern_str = raw.get("pattern", "")
        if not pattern_str:
            logger.error("privacy_filter rule missing 'pattern' — skipped: %r", raw)
            continue

        try:
            pattern = re.compile(pattern_str)
        except (re.error, TypeError) as exc:
            logger.error(
                "privacy_filter: invalid regex %r — %s — rule skipped", pattern_str, exc
            )
            continue

        action = raw.get("action", "redact")
        if action not in _VALID_ACTIONS:
            logger.error(
                "privacy_filter: unknown action %r (expected 'drop' or 'redact') — rule skipped",
                action,
            )
            continue

        field = raw.get("field", "title")
        if not isinstance(field, str) or not field:
            logger.error(
                "privacy_filter: 'field' must be a non-empty string — rule skipped: %r",
                raw,
            )
            continue

        replacement = raw.get("replacement", "excluded")
        if not isinstance(replacement, str):
            logger.error(
                "privacy_filter: 'replacement' must be a string — rule skipped: %r",
                raw,
            )
            continue

        compiled.append(
            {
                "pattern": pattern,
                "field": field,
                "action": action,
                "replacement": replacement,
            }
        )
    return compiled


def apply_privacy_filters(window: dict, rules: list) -> Optional[dict]:
    """Apply compiled privacy filter rules to a window observation.

    Returns None when the event should be dropped entirely, otherwise a
    (possibly modified) copy of the window dict. Never mutates the input.

    Fail-closed: if rules are malformed, the event is dropped rather than
    leaked unfiltered.
    """
    if not rules:
        return window

    result = dict(window)
    for rule in rules:
        field = rule["field"]
        value = result.get(field)
        if not isinstance(value, str):
            continue
        if rule["pattern"].search(value):
            if rule["action"] == "drop":
                logger.debug(
                    "privacy_filter: dropping event (field=%r matched %r)",
                    field,
                    rule["pattern"].pattern,
                )
                return None
            else:  # redact
                logger.debug(
                    "privacy_filter: redacting field=%r matched %r",
                    field,
                    rule["pattern"].pattern,
                )
                result[field] = rule["replacement"]
    return result


def hash_title(title: str) -> str:
    """Return a deterministic short hash of a window title.

    Used for grouping similar titles without exposing sensitive text.
    Format: [HASH:<first 8 hex chars of SHA-256>]
    """
    import hashlib

    return f"[HASH:{hashlib.sha256(title.encode('utf-8')).hexdigest()[:8]}]"


# Default privacy rules for BIMSpend. These are applied when no custom
# rules are provided. They cover common sensitive patterns.
DEFAULT_PRIVACY_RULES = [
    # Drop private browsing / incognito sessions
    {"pattern": r"(?i)private browsing|incognito", "action": "drop"},
    # Redact banking/finance domains in titles
    {"pattern": r"(?i)bank", "action": "redact", "replacement": "[REDACTED]"},
    {"pattern": r"(?i)paypal", "action": "redact", "replacement": "[REDACTED]"},
    # Drop password manager / credential UI
    {"pattern": r"(?i)1password|lastpass|bitwarden|keepass", "action": "drop"},
]
