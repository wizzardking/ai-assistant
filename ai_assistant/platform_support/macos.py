"""macOS clipboard backend (uses pbcopy/pbpaste)."""

from __future__ import annotations

import logging
import subprocess

logger = logging.getLogger(__name__)


class MacClipboardBackend:
    def _qt_clipboard(self):
        from PyQt6.QtWidgets import QApplication
        return QApplication.clipboard()

    def read_text(self) -> str:
        try:
            result = subprocess.run(
                ["pbpaste"], capture_output=True, timeout=2
            )
            if result.returncode == 0:
                return result.stdout.decode("utf-8", errors="replace")
        except Exception:
            logger.exception("pbpaste failed")
        cb = self._qt_clipboard()
        return cb.text() if cb is not None else ""

    def write_text(self, text: str) -> None:
        try:
            proc = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
            proc.communicate(input=text.encode("utf-8"), timeout=2)
            return
        except Exception:
            logger.exception("pbcopy failed")
        cb = self._qt_clipboard()
        if cb is not None:
            cb.setText(text)
