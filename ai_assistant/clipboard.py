from __future__ import annotations

import logging
import os
import shutil
import subprocess
import time
import uuid
from pathlib import Path

from PyQt6.QtGui import QClipboard
from PyQt6.QtWidgets import QApplication
from pynput.keyboard import Controller, Key

logger = logging.getLogger(__name__)


def _find_xclip() -> str | None:
    system = shutil.which("xclip")
    if system:
        return system
    project_root = Path(__file__).resolve().parents[1]
    local = project_root / ".local-lib" / "usr" / "bin" / "xclip"
    if local.is_file():
        return str(local)
    return None


def _xclip_env(xclip_path: str) -> dict[str, str]:
    env = os.environ.copy()
    local_lib = Path(xclip_path).resolve().parents[1] / "lib" / "x86_64-linux-gnu"
    if local_lib.is_dir():
        existing = env.get("LD_LIBRARY_PATH", "")
        env["LD_LIBRARY_PATH"] = f"{local_lib}:{existing}" if existing else str(local_lib)
    env.setdefault("DISPLAY", ":0")
    return env


class ClipboardManager:
    PRE_COPY_WAIT_S = 0.2
    POLL_INTERVAL_S = 0.05
    POLL_TIMEOUT_S = 1.5

    def __init__(self) -> None:
        self._keyboard = Controller()
        self._xclip = _find_xclip()
        self._env = _xclip_env(self._xclip) if self._xclip else None
        if self._xclip:
            logger.info("Using xclip at %s", self._xclip)
        else:
            logger.warning("xclip not found – falling back to Qt clipboard")

    def _qt_clipboard(self) -> QClipboard:
        return QApplication.clipboard()

    def read_text(self) -> str:
        if self._xclip:
            try:
                result = subprocess.run(
                    [self._xclip, "-selection", "clipboard", "-o"],
                    capture_output=True,
                    env=self._env,
                    timeout=2,
                )
                if result.returncode == 0:
                    return result.stdout.decode("utf-8", errors="replace")
            except subprocess.TimeoutExpired:
                logger.warning("xclip read timeout")
            except Exception:
                logger.exception("xclip read failed")
        return self._qt_clipboard().text() or ""

    def write_text(self, text: str) -> None:
        if self._xclip:
            try:
                proc = subprocess.Popen(
                    [self._xclip, "-selection", "clipboard", "-i"],
                    stdin=subprocess.PIPE,
                    env=self._env,
                )
                proc.communicate(input=text.encode("utf-8"), timeout=2)
                return
            except subprocess.TimeoutExpired:
                logger.warning("xclip write timeout")
            except Exception:
                logger.exception("xclip write failed")
        self._qt_clipboard().setText(text)

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
        try:
            with self._keyboard.pressed(Key.ctrl):
                self._keyboard.press("c")
                self._keyboard.release("c")
        except Exception:
            logger.exception("Failed to simulate Ctrl+C")
