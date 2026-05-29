"""Platform-specific backends (clipboard, etc.).

Importing this package returns the appropriate backend factories for the
current operating system. Linux uses ``xclip`` for X11 clipboards, while
Windows and macOS rely on the Qt clipboard.
"""

from __future__ import annotations

import sys

from .base import ClipboardBackend, NullClipboardBackend  # noqa: F401


def get_clipboard_backend() -> ClipboardBackend:
    if sys.platform.startswith("win"):
        from .windows import WindowsClipboardBackend
        return WindowsClipboardBackend()
    if sys.platform == "darwin":
        from .macos import MacClipboardBackend
        return MacClipboardBackend()
    from .linux import LinuxClipboardBackend
    return LinuxClipboardBackend()


def is_windows() -> bool:
    return sys.platform.startswith("win")


def is_macos() -> bool:
    return sys.platform == "darwin"


def is_linux() -> bool:
    return sys.platform.startswith("linux")
