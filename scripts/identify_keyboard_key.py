"""Helper: prints every keyboard press, including pynput-style hotkey snippet.

Output goes to stdout AND /tmp/keyboard-keys.log.

Usage:
    DISPLAY=:0 .venv/bin/python -u scripts/identify_keyboard_key.py
Press the key you want to use; abort with Ctrl+C in the terminal.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pynput import keyboard

LOG_PATH = Path("/tmp/keyboard-keys.log")


def _emit(line: str) -> None:
    print(line, flush=True)
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def _pretty(key: keyboard.Key | keyboard.KeyCode) -> str:
    if isinstance(key, keyboard.Key):
        return f"<{key.name}>"
    char = getattr(key, "char", None)
    if char:
        return char
    vk = getattr(key, "vk", None)
    return f"<vk={vk}>"


def _on_press(key) -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    pretty = _pretty(key)
    _emit(f"[{ts}] {pretty}   (repr={key!r})")


def main() -> None:
    LOG_PATH.write_text("", encoding="utf-8")
    _emit("Listening for keyboard events (writing to /tmp/keyboard-keys.log)...")
    _emit("Press the desired key now. Ctrl+C to stop.\n")
    with keyboard.Listener(on_press=_on_press) as listener:
        listener.join()


if __name__ == "__main__":
    main()
