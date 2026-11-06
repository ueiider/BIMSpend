"""ActivityWatch-derived capture module for BIMSpend.

This package contains code adapted from ActivityWatch (MPL-2.0 licensed)
for native Windows foreground-window capture. See
docs/open-source/ACTIVITYWATCH_SOURCE_MANIFEST.md for full provenance.

BIMSpend proprietary orchestration, consent management, SQLite integration,
and privacy policy enforcement live outside this package.
"""

__version__ = "0.1.0"

from .windows import get_current_window, get_active_window_handle
from .privacy_filter import compile_privacy_rules, apply_privacy_filters, hash_title

__all__ = [
    "get_current_window",
    "get_active_window_handle",
    "compile_privacy_rules",
    "apply_privacy_filters",
    "hash_title",
]
