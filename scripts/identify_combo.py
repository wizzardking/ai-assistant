"""Logs keyboard presses AND releases with exact timestamps to diagnose
multi-key combos that may arrive too fast for pynput.GlobalHotKeys.

Writes to /tmp/combo.log.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from time import perf_counter

from pynput import keyboard

LOG_PATH = Path("/tmp/combo.log")
_t0 = perf_counter()


def _emit(line: str) -> None:
    print(line, flush=True)
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def _pretty(key) -> str:
    if isinstance(key, keyboard.Key):
        return f"<{key.name}>"
    char = getattr(key, "char", None)
    if char:
        return char
    return f"<vk={getattr(key, 'vk', '?')}>"


def _on_press(key) -> None:
    dt = (perf_counter() - _t0) * 1000
    _emit(f"[{dt:8.2f} ms] PRESS   {_pretty(key)}   (repr={key!r})")


def _on_release(key) -> None:
    dt = (perf_counter() - _t0) * 1000
    _emit(f"[{dt:8.2f} ms] RELEASE {_pretty(key)}")


def main() -> None:
    LOG_PATH.write_text("", encoding="utf-8")
    _emit("Listening for keyboard press+release. Press Ctrl+C to stop.\n")
    with keyboard.Listener(on_press=_on_press, on_release=_on_release) as listener:
        listener.join()


if __name__ == "__main__":
    main()
