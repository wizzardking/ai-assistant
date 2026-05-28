from __future__ import annotations

import logging
from collections.abc import Callable

from pynput import keyboard

logger = logging.getLogger(__name__)


class HotkeyListener:
    def __init__(self, hotkey: str, callback: Callable[[], None]) -> None:
        self._hotkey = hotkey
        self._callback = callback
        self._listener: keyboard.GlobalHotKeys | None = None

    def start(self) -> None:
        self.stop()
        self._listener = keyboard.GlobalHotKeys({self._hotkey: self._on_hotkey})
        self._listener.start()
        logger.info("Hotkey registered: %s", self._hotkey)

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()
            self._listener = None

    def update_hotkey(self, hotkey: str) -> None:
        self._hotkey = hotkey
        self.start()

    def _on_hotkey(self) -> None:
        logger.debug("Hotkey triggered")
        try:
            self._callback()
        except Exception:
            logger.exception("Hotkey callback failed")
