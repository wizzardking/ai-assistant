from __future__ import annotations

import asyncio
import logging

from PyQt6.QtCore import QThread, pyqtSignal

logger = logging.getLogger(__name__)


class ModuleWorker(QThread):
    finished_ok = pyqtSignal(str)
    finished_error = pyqtSignal(str)

    def __init__(self, coroutine) -> None:
        super().__init__()
        self._coroutine = coroutine

    def run(self) -> None:
        try:
            result = asyncio.run(self._coroutine)
            self.finished_ok.emit(result)
        except Exception as exc:
            logger.exception("Module execution failed")
            self.finished_error.emit(str(exc))


class ClipboardCaptureWorker(QThread):
    """Performs `ClipboardManager.capture_selection()` off the UI thread."""

    finished_capture = pyqtSignal(str, object)  # selected, previous

    def __init__(self, clipboard_manager) -> None:
        super().__init__()
        self._clipboard = clipboard_manager

    def run(self) -> None:
        try:
            selected, previous = self._clipboard.capture_selection()
        except Exception:
            logger.exception("Clipboard capture failed")
            selected, previous = "", None
        self.finished_capture.emit(selected, previous)
