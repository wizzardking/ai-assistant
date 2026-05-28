from __future__ import annotations

import time

from PyQt6.QtGui import QClipboard
from PyQt6.QtWidgets import QApplication
from pynput.keyboard import Controller, Key


class ClipboardManager:
    COPY_DELAY_S = 0.15

    def __init__(self) -> None:
        self._keyboard = Controller()

    def _clipboard(self) -> QClipboard:
        return QApplication.clipboard()

    def read_text(self) -> str:
        return self._clipboard().text() or ""

    def write_text(self, text: str) -> None:
        self._clipboard().setText(text)

    def capture_selection(self) -> tuple[str, str | None]:
        """Simulate Ctrl+C and return selected text plus previous clipboard content."""
        previous = self.read_text()
        self._simulate_copy()
        selected = self.read_text().strip()
        return selected, previous

    def restore(self, previous: str | None) -> None:
        if previous is not None:
            self.write_text(previous)

    def _simulate_copy(self) -> None:
        with self._keyboard.pressed(Key.ctrl):
            self._keyboard.press("c")
            self._keyboard.release("c")
        time.sleep(self.COPY_DELAY_S)
