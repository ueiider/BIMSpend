"""AFK (Away-From-Keyboard) detector for Windows.

Adapted from ActivityWatch aw-watcher-afk concepts (MPL-2.0).
Uses Windows GetLastInputInfo API to detect user inactivity.

States: ACTIVE, AFK

AFK threshold defaults to 5 minutes (configurable).
"""

from __future__ import annotations

import ctypes
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class AFKState(Enum):
    ACTIVE = "active"
    AFK = "afk"


@dataclass
class LASTINPUTINFO(ctypes.Structure):
    """Windows LASTINPUTINFO struct for GetLastInputInfo API."""
    cbSize: int = ctypes.sizeof(ctypes.c_uint) * 2
    dwTime: int = 0


class AFKDetector:
    """Detects Windows user inactivity using GetLastInputInfo.

    The Windows GetLastInputInfo API returns the tick count of the last
    input event. By comparing with GetTickCount64 we can compute idle
    duration. When idle duration exceeds the threshold, the user is AFK.
    """

    def __init__(self, afk_threshold_minutes: float = 5.0):
        self.afk_threshold_seconds = afk_threshold_minutes * 60.0
        self.state = AFKState.ACTIVE
        self._last_input_time: Optional[float] = None
        self._last_tick: Optional[float] = None
        self._state_changed_at: Optional[float] = None
        self._lock = __import__("threading").Lock()

    def _get_idle_seconds(self) -> float:
        """Return seconds since last user input, or 0 on failure."""
        try:
            lii = LASTINPUTINFO()
            lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
            if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
                last_input_tick = lii.dwTime
                current_tick = ctypes.windll.kernel32.GetTickCount64()
                # Handle tick count wraparound (49.7 days)
                if current_tick >= last_input_tick:
                    diff_ms = current_tick - last_input_tick
                else:
                    diff_ms = (2**32 - last_input_tick) + current_tick
                return diff_ms / 1000.0
        except Exception as exc:
            logger.debug("GetLastInputInfo failed: %s", exc)
        return 0.0

    def poll(self) -> AFKState:
        """Poll current AFK state. Returns the current state."""
        idle_seconds = self._get_idle_seconds()
        now = time.time()

        with self._lock:
            if idle_seconds >= self.afk_threshold_seconds:
                new_state = AFKState.AFK
            else:
                new_state = AFKState.ACTIVE

            if new_state != self.state:
                logger.info(
                    "AFK state transition: %s -> %s (idle %.1fs)",
                    self.state.value,
                    new_state.value,
                    idle_seconds,
                )
                self.state = new_state
                self._state_changed_at = now

            return self.state

    def is_afk(self) -> bool:
        return self.state == AFKState.AFK

    def is_active(self) -> bool:
        return self.state == AFKState.ACTIVE

    def get_idle_seconds(self) -> float:
        return self._get_idle_seconds()

    def get_state_duration_seconds(self) -> Optional[float]:
        """Return seconds in current state, or None if never transitioned."""
        if self._state_changed_at is None:
            return None
        return time.time() - self._state_changed_at

    def set_threshold_minutes(self, minutes: float) -> None:
        self.afk_threshold_seconds = minutes * 60.0
        logger.info("AFK threshold set to %.1f minutes", minutes)
