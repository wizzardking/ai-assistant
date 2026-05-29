"""Linux/X11 clipboard backend (xclip-based)."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def _find_xclip() -> str | None:
    system = shutil.which("xclip")
    if system:
        return system
    project_root = Path(__file__).resolve().parents[2]
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


class LinuxClipboardBackend:
    """xclip-based clipboard. Falls back to Qt's clipboard if xclip is missing."""

    def __init__(self) -> None:
        self._xclip = _find_xclip()
        self._env = _xclip_env(self._xclip) if self._xclip else None
        if self._xclip:
            logger.info("Using xclip at %s", self._xclip)
        else:
            logger.warning("xclip not found – falling back to Qt clipboard")

    def _qt_clipboard(self):
        from PyQt6.QtWidgets import QApplication
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
        cb = self._qt_clipboard()
        return cb.text() if cb is not None else ""

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
        cb = self._qt_clipboard()
        if cb is not None:
            cb.setText(text)
