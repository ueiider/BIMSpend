"""Main watcher loop adapted from ActivityWatch aw-watcher-window/main.py.

Upstream commit 12000f58d16b8fc1376af42755c688b3d7157280, MPL-2.0.
Original copyright: ActivityWatch contributors.
See docs/open-source/ACTIVITYWATCH_SOURCE_MANIFEST.md for full provenance.

Modifications from upstream:
- Removed aw-client dependency; events are returned as dicts for SQLite persistence
- Removed multiprocessing/freeze_support (single-process desktop app)
- Removed macOS/Linux strategy branches; Windows-only capture
- Removed heartbeat queuing to aw-server
- Added privacy filter integration
- Added configurable poll time and pulsetime computation
- Added error backoff and parent-death detection
"""

from __future__ import annotations

import logging
import os
import re
import time
from datetime import datetime, timezone
from typing import Callable, Optional

logger = logging.getLogger(__name__)


def compute_pulsetime(poll_time: float) -> float:
    """Scale pulsetime with poll_time so OS scheduling jitter doesn't break
    heartbeat chains.

    At poll_time=1s, jitter ~0.15s is well within 1s margin.
    At poll_time=5s, jitter ~0.75s exceeds the 1s margin ~10% of the time.
    max(poll_time*1.5, poll_time+1) keeps backward compatibility at poll_time<=2s
    while fixing the problem at higher polling intervals.
    """
    return max(poll_time * 1.5, poll_time + 1.0)


# How many identical consecutive poll errors between one-line summaries.
REPEATED_ERROR_SUMMARY_EVERY = 100
# Maximum distinct error signatures to retain per streak.
_MAX_SEEN_ERRORS = 50


def try_compile_regex(pattern: str) -> re.Pattern:
    """Compile a regex pattern case-insensitively, raising SystemExit on invalid."""
    try:
        return re.compile(pattern, re.IGNORECASE)
    except re.error as exc:
        logger.error("Invalid regex pattern: %s — %s", pattern, exc)
        raise SystemExit(1)


def transform_window(
    current_window: dict,
    exclude_title: bool = False,
    exclude_titles: Optional[list] = None,
    exclude_apps: Optional[list] = None,
    privacy_filter_rules: Optional[list] = None,
) -> Optional[dict]:
    """Apply privacy filters and exclusions to a window observation.

    Privacy filter runs first — sensitive events never reach other transforms.
    App exclusion is also a privacy guarantee and runs before any other
    transform.

    Returns None if the event should be dropped (excluded by privacy filter
    or app exclusion), otherwise the (possibly modified) window dict.
    """
    # Privacy filter runs first
    if privacy_filter_rules:
        from .privacy_filter import apply_privacy_filters

        current_window = apply_privacy_filters(current_window, privacy_filter_rules)
        if current_window is None:
            return None

    # App exclusion
    for pattern in exclude_apps or []:
        if pattern.search(current_window.get("app", "")):
            return None

    # Title exclusion
    for pattern in exclude_titles or []:
        if pattern.search(current_window.get("title", "")):
            current_window["title"] = "excluded"

    if exclude_title:
        current_window["title"] = "excluded"

    return current_window


class HeartbeatLoop:
    """Runs the foreground-window polling loop.

    This is the core capture loop adapted from ActivityWatch's main.py.
    It polls get_current_window() at poll_time intervals, applies privacy
    filters, and calls a callback with each accepted observation.

    Designed to be driven by CaptureController (in capture.controller) which
    manages lifecycle, consent, and database persistence.
    """

    def __init__(
        self,
        get_window_fn: Callable[[], dict],
        poll_time: float = 5.0,
        exclude_title: bool = False,
        exclude_titles: Optional[list] = None,
        exclude_apps: Optional[list] = None,
        privacy_filter_rules: Optional[list] = None,
        on_window: Optional[Callable[[dict], None]] = None,
    ):
        self.get_window_fn = get_window_fn
        self.poll_time = poll_time
        self.exclude_title = exclude_title
        self.exclude_titles = [
            try_compile_regex(t) for t in (exclude_titles or []) if t is not None
        ]
        self.exclude_apps = [
            try_compile_regex(a) for a in (exclude_apps or []) if a is not None
        ]
        self.privacy_filter_rules = privacy_filter_rules or []
        self.on_window = on_window

        # Error backoff state
        self._xconn_backoff = poll_time
        self._seen_errors: set = set()
        self._error_repeats = 0
        self._chain_broken_by_exclusion = False

        # Lifecycle
        self._running = False
        self._paused = False

    def start(self) -> None:
        """Start the polling loop (blocking). Call stop() to end."""
        self._running = True
        self._paused = False
        self._run_loop()

    def stop(self) -> None:
        """Request the loop to stop on the next iteration."""
        self._running = False

    def pause(self) -> None:
        """Pause polling without stopping the loop."""
        self._paused = True

    def resume(self) -> None:
        """Resume polling after pause."""
        self._paused = False

    def is_running(self) -> bool:
        return self._running

    def _run_loop(self) -> None:
        """Main polling loop. Blocks until stop() is called."""
        while self._running:
            # Check parent death (orphan detection)
            if os.getppid() == 1:
                logger.info("capture loop stopped because parent process died")
                break

            if self._paused:
                time.sleep(0.5)
                continue

            current_window = None
            try:
                current_window = self.get_window_fn()
                # Reset backoff on successful poll
                self._xconn_backoff = self.poll_time
                self._seen_errors = set()
                self._error_repeats = 0
            except Exception as exc:
                self._handle_poll_error(exc)
                continue

            if current_window is None:
                logger.debug("Unable to fetch window, retrying next poll")
                time.sleep(self.poll_time)
                continue

            # Apply privacy filters and exclusions
            filtered = transform_window(
                current_window,
                exclude_title=self.exclude_title,
                exclude_titles=self.exclude_titles,
                exclude_apps=self.exclude_apps,
                privacy_filter_rules=self.privacy_filter_rules,
            )

            if filtered is None:
                # Event excluded — mark chain broken so next event uses pulsetime=0
                logger.debug("Window excluded (privacy filter or exclude_apps)")
                self._chain_broken_by_exclusion = True
                time.sleep(self.poll_time)
                continue

            # Deliver the observation
            if self.on_window is not None:
                try:
                    self.on_window(filtered, self._chain_broken_by_exclusion)
                except Exception as exc:
                    logger.error("Error in window callback: %s", exc)
                self._chain_broken_by_exclusion = False

            time.sleep(self.poll_time)

    def _handle_poll_error(self, exc: Exception) -> None:
        """Handle a poll exception with bounded backoff and logging."""
        signature = (type(exc).__name__, str(exc))

        if signature not in self._seen_errors and len(self._seen_errors) < _MAX_SEEN_ERRORS:
            self._seen_errors.add(signature)
            logger.exception("Exception thrown while getting active window")
        else:
            if self._error_repeats % REPEATED_ERROR_SUMMARY_EVERY == 0:
                logger.error(
                    "Still failing to get active window (%d repeats): %s: %s",
                    self._error_repeats,
                    *signature,
                )

        self._error_repeats += 1

        # Back off on sustained failures (2+ consecutive errors), capped at 60s
        if self._error_repeats > 1:
            extra = min(self.poll_time * 2 ** min(self._error_repeats, 10), 60.0) - self.poll_time
            end = time.time() + extra
            while time.time() < end and self._running and os.getppid() != 1:
                time.sleep(min(1.0, end - time.time()))
