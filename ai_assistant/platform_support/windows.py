"""Windows clipboard backend.

Uses the Qt clipboard which maps to the Win32 clipboard API. Optionally
falls back to ``pyperclip`` if available.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class WindowsClipboardBackend:
    def __init__(self) -> None:
        try:
            import pyperclip  # type: ignore
            self._pyperclip = pyperclip
        except Exception:
            self._pyperclip = None
        logger.info(
            "Using Windows clipboard (pyperclip=%s, qt-fallback=always)",
            "yes" if self._pyperclip else "no",
        )

    def _qt_clipboard(self):
        from PyQt6.QtWidgets import QApplication
        return QApplication.clipboard()

    def read_text(self) -> str:
        if self._pyperclip is not None:
            try:
                return self._pyperclip.paste() or ""
            except Exception:
                logger.exception("pyperclip read failed")
        cb = self._qt_clipboard()
        return cb.text() if cb is not None else ""

    def write_text(self, text: str) -> None:
        if self._pyperclip is not None:
            try:
                self._pyperclip.copy(text)
                return
            except Exception:
                logger.exception("pyperclip write failed")
        cb = self._qt_clipboard()
        if cb is not None:
            cb.setText(text)
