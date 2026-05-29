from __future__ import annotations

import logging
import time
import uuid

from pynput.keyboard import Controller, Key

from ai_assistant.platform_support import get_clipboard_backend

logger = logging.getLogger(__name__)


class ClipboardManager:
    """Cross-platform clipboard manager with selection capture support.

    The actual read/write is delegated to a platform-specific backend
    (xclip on Linux/X11, Qt/Win32 on Windows, pbcopy/pbpaste on macOS).
    """

    PRE_COPY_WAIT_S = 0.03
    POLL_INTERVAL_S = 0.015
    POLL_TIMEOUT_S = 0.7

    def __init__(self) -> None:
        self._keyboard = Controller()
        self._backend = get_clipboard_backend()

    def read_text(self) -> str:
        return self._backend.read_text() or ""

    def write_text(self, text: str) -> None:
        self._backend.write_text(text)

    def simulate_copy(self) -> None:
        """Public alias of :meth:`_simulate_copy` for platform-specific helpers."""
        self._simulate_copy()

    def capture_selection(self) -> tuple[str, str | None]:
        """Simulate Ctrl+C and wait for the clipboard to change."""
        previous = self.read_text()
        sentinel = f"__ai_assistant_sentinel__{uuid.uuid4().hex}__"
        self.write_text(sentinel)

        time.sleep(self.PRE_COPY_WAIT_S)
        self._simulate_copy()

        deadline = time.monotonic() + self.POLL_TIMEOUT_S
        current = self.read_text()
        while current == sentinel and time.monotonic() < deadline:
            time.sleep(self.POLL_INTERVAL_S)
            current = self.read_text()

        if current == sentinel:
            logger.warning("Clipboard did not change after Ctrl+C – restoring previous")
            self.write_text(previous)
            return "", previous

        selected = current.strip()
        if not selected:
            self.write_text(previous)
        return selected, previous

    def restore(self, previous: str | None) -> None:
        if previous is not None:
            self.write_text(previous)

    def _simulate_copy(self) -> None:
        # Some backends (Windows) provide a more reliable, native Ctrl+C
        # implementation via direct OS API calls. Use it when available;
        # otherwise fall back to the original pynput path (Linux/macOS keep
        # using pynput so their behaviour is unchanged).
        backend_send = getattr(self._backend, "send_ctrl_c", None)
        if callable(backend_send):
            try:
                if backend_send():
                    return
            except Exception:
                logger.exception("Backend send_ctrl_c failed; falling back to pynput")
        try:
            with self._keyboard.pressed(Key.ctrl):
                self._keyboard.press("c")
                self._keyboard.release("c")
        except Exception:
            logger.exception("Failed to simulate Ctrl+C")
