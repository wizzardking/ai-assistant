"""Reads raw evdev input events from all mouse devices and logs every key/button press.

Requires read permission on /dev/input/event*. If your user is not in the `input`
group, run via sudo:

    sudo .venv/bin/python -u scripts/identify_mouse_evdev.py
"""

from __future__ import annotations

import select
from datetime import datetime
from pathlib import Path

import evdev

LOG_PATH = Path("/tmp/mouse-evdev.log")


def _emit(line: str) -> None:
    print(line, flush=True)
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def _is_mouse(device: evdev.InputDevice) -> bool:
    caps = device.capabilities()
    keys = caps.get(evdev.ecodes.EV_KEY, [])
    return any(0x110 <= k <= 0x117 for k in keys) or evdev.ecodes.EV_REL in caps


def main() -> None:
    LOG_PATH.write_text("", encoding="utf-8")
    devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
    mice = [d for d in devices if _is_mouse(d)]
    if not mice:
        _emit("No mouse-like devices found.")
        return

    _emit("Listening on:")
    for d in mice:
        _emit(f"  {d.path}  {d.name!r}")
    _emit("Press the desired button now. Ctrl+C to stop.\n")

    fd_to_dev = {d.fd: d for d in mice}
    try:
        while True:
            r, _, _ = select.select(fd_to_dev, [], [])
            for fd in r:
                for event in fd_to_dev[fd].read():
                    if event.type != evdev.ecodes.EV_KEY or event.value != 1:
                        continue
                    name = evdev.ecodes.bytype.get(evdev.ecodes.EV_KEY, {}).get(event.code, "?")
                    ts = datetime.now().strftime("%H:%M:%S")
                    _emit(
                        f"[{ts}] device={fd_to_dev[fd].name!r} code={event.code} "
                        f"name={name}"
                    )
    except KeyboardInterrupt:
        _emit("Stopped.")


if __name__ == "__main__":
    main()
