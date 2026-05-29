"""Windows clipboard backend.

Uses the Qt clipboard which maps to the Win32 clipboard API. Optionally
falls back to ``pyperclip`` if available.
"""

from __future__ import annotations

import ctypes
import logging
import time
from ctypes import wintypes

logger = logging.getLogger(__name__)


# ----- Win32 SendInput for a rock-solid Ctrl+C -----------------------------
# pynput's keyboard.Controller on Windows has a few known flakiness issues
# around modifier keys and the active keyboard layout, which is why we
# manually emit the four input events via SendInput instead. This bypasses
# pynput entirely for the Ctrl+C path on Windows.

_VK_CONTROL = 0x11
_VK_C = 0x43
_INPUT_KEYBOARD = 1
_KEYEVENTF_KEYUP = 0x0002


class _KEYBDINPUT(ctypes.Structure):
    _fields_ = (
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG)),
    )


class _INPUT_UNION(ctypes.Union):
    _fields_ = (("ki", _KEYBDINPUT),)


class _INPUT(ctypes.Structure):
    _anonymous_ = ("u",)
    _fields_ = (
        ("type", wintypes.DWORD),
        ("u", _INPUT_UNION),
    )


def _make_key_event(vk: int, key_up: bool) -> _INPUT:
    flags = _KEYEVENTF_KEYUP if key_up else 0
    inp = _INPUT()
    inp.type = _INPUT_KEYBOARD
    inp.ki = _KEYBDINPUT(vk, 0, flags, 0, None)
    return inp


def send_ctrl_c() -> bool:
    """Inject a Ctrl+C key chord via Win32 ``SendInput``.

    Returns True on success (all 4 events accepted by the system). Failures
    are logged and return False so the caller can fall back if needed.
    """
    events = (_INPUT * 4)(
        _make_key_event(_VK_CONTROL, key_up=False),
        _make_key_event(_VK_C, key_up=False),
        _make_key_event(_VK_C, key_up=True),
        _make_key_event(_VK_CONTROL, key_up=True),
    )
    sent = ctypes.windll.user32.SendInput(
        len(events), ctypes.byref(events), ctypes.sizeof(_INPUT)
    )
    if sent != len(events):
        logger.warning("SendInput sent only %d/%d events for Ctrl+C", sent, len(events))
        return False
    return True


# Virtual key codes for modifier keys we want to wait for before simulating
# Ctrl+C. If e.g. Shift is still physically held from the hotkey, our injected
# Ctrl+C would actually be interpreted as Ctrl+Shift+C by the target window.
_MODIFIER_VKS = (
    0x10,  # VK_SHIFT (covers L+R)
    0x11,  # VK_CONTROL (covers L+R)
    0x12,  # VK_MENU (Alt, covers L+R)
    0x5B,  # VK_LWIN
    0x5C,  # VK_RWIN
)


def _any_modifier_held() -> bool:
    user32 = ctypes.windll.user32
    for vk in _MODIFIER_VKS:
        if user32.GetAsyncKeyState(vk) & 0x8000:
            return True
    return False


def wait_for_modifier_release(timeout_s: float = 0.6, poll_s: float = 0.005) -> bool:
    """Block until Ctrl/Shift/Alt/Win are all physically released.

    Returns True if all modifiers were released within the timeout, False if
    we gave up and returned anyway. This is needed on Windows so that a
    subsequently simulated Ctrl+C is not mangled into Ctrl+Shift+C (or similar)
    by modifiers the user still holds down from the activating hotkey.

    The poll interval is intentionally tight (5 ms) so that as soon as the
    user lets go of the hotkey, we proceed without adding perceptible lag.
    """
    if not _any_modifier_held():
        return True
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if not _any_modifier_held():
            return True
        time.sleep(poll_s)
    logger.debug("wait_for_modifier_release: timeout, modifiers still held")
    return False


def _get_clipboard_sequence_number() -> int:
    user32 = ctypes.windll.user32
    user32.GetClipboardSequenceNumber.restype = ctypes.c_uint
    return int(user32.GetClipboardSequenceNumber())


def capture_selection_via_sequence(
    clipboard_manager,
    poll_timeout_s: float = 0.3,
    poll_interval_s: float = 0.005,
    retry_timeout_s: float = 0.5,
) -> tuple[str, str | None]:
    """Windows-only fast capture using ``GetClipboardSequenceNumber``.

    Unlike the sentinel-based :meth:`ClipboardManager.capture_selection`, this
    does **not** write into the clipboard before the copy. We just remember
    the system's monotonically-increasing clipboard sequence number, simulate
    Ctrl+C, and wait for the number to change – that is the most reliable
    indicator on Windows that *something* (typically the foreground app
    responding to our Ctrl+C) actually wrote into the clipboard.

    Benefits over the sentinel approach:

    * No extra write round-trip, so no PRE_COPY_WAIT_S is needed.
    * The user's previous clipboard contents stay untouched if Ctrl+C fails.
    * Polling a 32-bit counter is essentially free, so we can poll tightly.

    If the first attempt times out, a single retry with a slightly longer
    window is performed – some apps (browsers, electron apps, IDEs) are
    occasionally slow to react to the very first injected Ctrl+C.
    """
    previous = clipboard_manager.read_text()

    for attempt, timeout in ((1, poll_timeout_s), (2, retry_timeout_s)):
        seq_before = _get_clipboard_sequence_number()
        clipboard_manager.simulate_copy()

        deadline = time.monotonic() + timeout
        while (
            _get_clipboard_sequence_number() == seq_before
            and time.monotonic() < deadline
        ):
            time.sleep(poll_interval_s)

        if _get_clipboard_sequence_number() != seq_before:
            selected = clipboard_manager.read_text().strip()
            if attempt > 1:
                logger.info("Ctrl+C succeeded on attempt %d", attempt)
            return selected, previous

        if attempt == 1:
            logger.debug("First Ctrl+C did not change clipboard; retrying...")
            time.sleep(0.04)

    logger.warning("Clipboard sequence did not change after Ctrl+C (retry failed)")
    return "", previous


class WindowsClipboardBackend:
    def __init__(self) -> None:
        try:
            import pyperclip  # type: ignore
            self._pyperclip = pyperclip
        except Exception:
            self._pyperclip = None
        logger.info(
            "Using Windows clipboard (pyperclip=%s, qt-fallback=always)",
            "yes" if self._pyperclip else "no",
        )

    def _qt_clipboard(self):
        from PyQt6.QtWidgets import QApplication
        return QApplication.clipboard()

    def read_text(self) -> str:
        if self._pyperclip is not None:
            try:
                return self._pyperclip.paste() or ""
            except Exception:
                logger.exception("pyperclip read failed")
        cb = self._qt_clipboard()
        return cb.text() if cb is not None else ""

    def write_text(self, text: str) -> None:
        if self._pyperclip is not None:
            try:
                self._pyperclip.copy(text)
                return
            except Exception:
                logger.exception("pyperclip write failed")
        cb = self._qt_clipboard()
        if cb is not None:
            cb.setText(text)

    def send_ctrl_c(self) -> bool:
        """Send Ctrl+C to the foreground window via Win32 SendInput.

        Used by :class:`ClipboardManager` instead of pynput on Windows because
        SendInput is significantly more reliable across apps (browsers, IDEs,
        text editors) and keyboard layouts.
        """
        return send_ctrl_c()
