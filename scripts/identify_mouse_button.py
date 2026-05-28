"""Helper: prints every mouse-button press so you can identify a custom button.

Output is written both to stdout (line-buffered) and to /tmp/mouse-buttons.log
so we can read it later even if the terminal swallows output.

Usage:
    DISPLAY=:0 .venv/bin/python -u scripts/identify_mouse_button.py
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

from pynput import mouse

LOG_PATH = Path("/tmp/mouse-buttons.log")


def _emit(line: str) -> None:
    print(line, flush=True)
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def _on_click(x: int, y: int, button: mouse.Button, pressed: bool) -> None:
    if not pressed:
        return
    ts = datetime.now().strftime("%H:%M:%S")
    _emit(f"[{ts}] PRESSED: {button.name}  (value={button.value})")


def main() -> None:
    LOG_PATH.write_text("", encoding="utf-8")
    _emit("Listening for mouse clicks (writing to /tmp/mouse-buttons.log)...")
    _emit("Press any mouse button now. Press Ctrl+C to stop.\n")
    with mouse.Listener(on_click=_on_click) as listener:
        listener.join()


if __name__ == "__main__":
    main()
