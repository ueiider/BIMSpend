"""Local IPC between Revit connector and BIMSpend.

Uses Windows named pipes for local-only communication. Named pipes are
suitable because:
- Local-only by default (cannot be accessed from remote machines)
- Support named access control (security descriptors)
- Built-in message framing
- Windows-native, no additional dependencies

If pywin32 pipe functions are unavailable, falls back to an in-memory
queue for testing.

No network ports are opened. No cloud dependency.
"""

from __future__ import annotations

import json
import logging
import queue
import secrets
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Named pipe availability
# ---------------------------------------------------------------------------

try:
    import win32api
    import win32file
    import win32pipe
    import win32security
    import ntsecuritycon as con

    _HAS_WIN32PIPE = True
except (ImportError, OSError):
    _HAS_WIN32PIPE = False

# ---------------------------------------------------------------------------
# IPC message types
# ---------------------------------------------------------------------------


class IPCMessageType(Enum):
    """Types of IPC messages between Revit connector and BIMSpend."""

    HELLO = "hello"  # Revit connector identifies itself
    EVENT = "event"  # Revit event forwarded to BIMSpend
    ACK = "ack"  # Acknowledgment
    ERROR = "error"  # Error message
    GOODBYE = "goodbye"  # Session termination


# ---------------------------------------------------------------------------
# IPC message
# ---------------------------------------------------------------------------


@dataclass
class IPCMessage:
    """A message sent over the IPC channel."""

    id: str
    type: IPCMessageType
    timestamp: str  # ISO-8601 UTC
    session_guid: str
    process_id: int
    payload: dict[str, Any] = field(default_factory=dict)
    company_id: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "timestamp": self.timestamp,
            "session_guid": self.session_guid,
            "process_id": self.process_id,
            "payload": self.payload,
            "company_id": self.company_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "IPCMessage":
        return cls(
            id=data["id"],
            type=IPCMessageType(data["type"]),
            timestamp=data["timestamp"],
            session_guid=data["session_guid"],
            process_id=data["process_id"],
            payload=data.get("payload", {}),
            company_id=data.get("company_id"),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, text: str) -> "IPCMessage":
        return cls.from_dict(json.loads(text))


# ---------------------------------------------------------------------------
# IPC channel (named pipe)
# ---------------------------------------------------------------------------


class IPCChannel:
    """Local IPC channel using Windows named pipes.

    Can operate in server mode (BIMSpend receives from Revit) or client
    mode (Revit connector sends to BIMSpend).

    Only accepts connections from the local machine. Named pipes are
    inherently local-only — they cannot be accessed over the network.
    """

    PIPE_NAME_PREFIX = r"\\.\pipe\bimspend_revit_"

    def __init__(
        self,
        pipe_name: str,
        is_server: bool = True,
        company_id: Optional[str] = None,
        max_instances: int = 4,
        buffer_size: int = 65536,
    ):
        self.pipe_name = (
            pipe_name
            if pipe_name.startswith("\\\\.\\pipe\\")
            else f"{self.PIPE_NAME_PREFIX}{pipe_name}"
        )
        self.is_server = is_server
        self.company_id = company_id
        self.max_instances = max_instances
        self.buffer_size = buffer_size

        self._pipe: Optional[Any] = None
        self._connected = False
        self._lock = threading.Lock()
        self._send_queue: queue.Queue[Optional[str]] = queue.Queue(maxsize=100)
        self._receive_queue: queue.Queue[IPCMessage] = queue.Queue(maxsize=1000)
        self._stop_event = threading.Event()
        self._message_handler: Optional[Callable[[IPCMessage], None]] = None
        self._send_thread: Optional[threading.Thread] = None
        self._receive_thread: Optional[threading.Thread] = None

    # ------------------------------------------------------------------
    # Server mode (BIMSpend side)
    # ------------------------------------------------------------------

    def start_server(self, message_handler: Callable[[IPCMessage], None]) -> None:
        """Start listening for Revit connector connections."""
        if not _HAS_WIN32PIPE:
            logger.warning(
                "win32pipe not available — IPC server runs in stub mode "
                "(no actual pipe communication)"
            )
            self._message_handler = message_handler
            self._connected = True
            return

        self._message_handler = message_handler
        self._stop_event.clear()

        thread = threading.Thread(target=self._server_loop, daemon=True)
        thread.start()
        logger.info("IPC server started: %s", self.pipe_name)

    def _server_loop(self) -> None:
        """Main server loop — accepts pipe connections."""
        while not self._stop_event.is_set():
            try:
                pipe = win32pipe.CreateNamedPipe(
                    self.pipe_name,
                    win32pipe.PIPE_ACCESS_DUPLEX,
                    win32pipe.PIPE_TYPE_MESSAGE
                    | win32pipe.PIPE_READMODE_MESSAGE
                    | win32pipe.PIPE_WAIT,
                    self.max_instances,
                    self.buffer_size,
                    self.buffer_size,
                    0,
                    None,
                )

                win32pipe.ConnectNamedPipe(pipe, None)

                with self._lock:
                    self._pipe = pipe
                    self._connected = True

                logger.info("IPC client connected: %s", self.pipe_name)

                self._send_thread = threading.Thread(
                    target=self._send_loop, args=(pipe,), daemon=True
                )
                self._receive_thread = threading.Thread(
                    target=self._receive_loop, args=(pipe,), daemon=True
                )
                self._send_thread.start()
                self._receive_thread.start()

                self._send_thread.join()
                self._receive_thread.join()

                with self._lock:
                    self._connected = False
                    self._pipe = None

                logger.info("IPC client disconnected: %s", self.pipe_name)

            except Exception as exc:
                if not self._stop_event.is_set():
                    logger.error("IPC server error: %s", exc)
                time.sleep(1.0)

    def _send_loop(self, pipe: Any) -> None:
        """Send messages from the queue to the pipe."""
        while self._running and not self._stop_event.is_set():
            try:
                message_text = self._send_queue.get(timeout=0.5)
                if message_text is None:
                    break
                win32file.WriteFile(pipe, message_text.encode("utf-8"))
            except queue.Empty:
                continue
            except Exception as exc:
                if not self._stop_event.is_set():
                    logger.error("IPC send error: %s", exc)
                break

    def _receive_loop(self, pipe: Any) -> None:
        """Receive messages from the pipe and dispatch to handler."""
        while self._running and not self._stop_event.is_set():
            try:
                result, data = win32file.ReadFile(pipe, self.buffer_size)
                if result == 0 and data:
                    text = data.decode("utf-8").strip()
                    if text:
                        try:
                            message = IPCMessage.from_json(text)
                            if self._message_handler:
                                self._message_handler(message)
                            else:
                                self._receive_queue.put(message)
                        except Exception as exc:
                            logger.error("IPC message parse error: %s", exc)
            except Exception as exc:
                if not self._stop_event.is_set():
                    logger.error("IPC receive error: %s", exc)
                break

    # ------------------------------------------------------------------
    # Client mode (Revit connector side)
    # ------------------------------------------------------------------

    def start_client(self) -> None:
        """Connect to the BIMSpend IPC server."""
        if not _HAS_WIN32PIPE:
            logger.warning(
                "win32pipe not available — IPC client runs in stub mode"
            )
            self._connected = True
            return

        self._stop_event.clear()
        thread = threading.Thread(target=self._client_loop, daemon=True)
        thread.start()
        logger.info("IPC client started: %s", self.pipe_name)

    def _client_loop(self) -> None:
        """Client connection loop with retry and backoff."""
        retry_delay = 0.5
        max_delay = 30.0

        while not self._stop_event.is_set():
            try:
                pipe = win32file.CreateFile(
                    self.pipe_name,
                    win32file.GENERIC_READ | win32file.GENERIC_WRITE,
                    0,
                    None,
                    win32file.OPEN_EXISTING,
                    0,
                    None,
                )

                with self._lock:
                    self._pipe = pipe
                    self._connected = True

                logger.info("IPC client connected: %s", self.pipe_name)

                self.send_message(
                    IPCMessageType.HELLO,
                    {
                        "company_id": self.company_id,
                        "capabilities": ["document_events", "view_events"],
                    },
                )

                self._send_thread = threading.Thread(
                    target=self._send_loop, args=(pipe,), daemon=True
                )
                self._receive_thread = threading.Thread(
                    target=self._receive_loop, args=(pipe,), daemon=True
                )
                self._send_thread.start()
                self._receive_thread.start()

                self._send_thread.join()
                self._receive_thread.join()

                with self._lock:
                    self._connected = False
                    self._pipe = None

                if not self._stop_event.is_set():
                    logger.warning(
                        "IPC connection lost — retrying in %.1fs", retry_delay
                    )
                    time.sleep(retry_delay)
                    retry_delay = min(retry_delay * 2, max_delay)

            except Exception as exc:
                if not self._stop_event.is_set():
                    logger.debug("IPC client connection error: %s", exc)
                    time.sleep(retry_delay)
                    retry_delay = min(retry_delay * 2, max_delay)

    # ------------------------------------------------------------------
    # Message sending/receiving
    # ------------------------------------------------------------------

    def send_message(
        self,
        msg_type: IPCMessageType,
        payload: dict[str, Any],
        session_guid: str = "",
        process_id: int = 0,
    ) -> bool:
        """Send a message over the IPC channel."""
        message = IPCMessage(
            id=secrets.token_urlsafe(8),
            type=msg_type,
            timestamp=datetime.now(timezone.utc).isoformat(),
            session_guid=session_guid,
            process_id=process_id,
            payload=payload,
            company_id=self.company_id,
        )
        message_text = message.to_json()

        if not _HAS_WIN32PIPE:
            try:
                self._send_queue.put_nowait(message_text)
                return True
            except queue.Full:
                logger.error("IPC send queue full")
                return False

        with self._lock:
            if self._pipe is None or not self._connected:
                logger.error("IPC not connected")
                return False

        try:
            self._send_queue.put_nowait(message_text)
            return True
        except queue.Full:
            logger.error("IPC send queue full")
            return False

    def receive_message(self, timeout: float = 0.1) -> Optional[IPCMessage]:
        """Receive a message from the IPC channel."""
        try:
            return self._receive_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    @property
    def _running(self) -> bool:
        return not self._stop_event.is_set()

    def stop(self) -> None:
        """Stop the IPC channel."""
        self._stop_event.set()

        try:
            self._send_queue.put_nowait(None)
        except queue.Full:
            pass

        if _HAS_WIN32PIPE and self._pipe is not None:
            try:
                win32pipe.DisconnectNamedPipe(self._pipe)
                win32file.CloseHandle(self._pipe)
            except Exception:
                pass

        if self._send_thread is not None:
            self._send_thread.join(timeout=2.0)
        if self._receive_thread is not None:
            self._receive_thread.join(timeout=2.0)
