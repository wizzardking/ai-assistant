from __future__ import annotations

import logging
import sys
from collections.abc import Callable, Iterable

from pynput import keyboard, mouse

logger = logging.getLogger(__name__)


# Symbolic aliases for virtual key codes used by the `combo:` hotkey syntax.
# The values differ between operating systems: pynput emits X11 keysyms on
# Linux and Win32 VK codes on Windows.
_VK_ALIASES_X11: dict[str, int] = {
    "shift": 65505, "shift_l": 65505, "shift_r": 65506,
    "ctrl": 65507, "control": 65507, "ctrl_l": 65507, "control_l": 65507,
    "ctrl_r": 65508, "control_r": 65508,
    "meta": 65511, "meta_l": 65511, "meta_r": 65512,
    "alt": 65513, "alt_l": 65513, "alt_r": 65514,
    "super": 65515, "super_l": 65515, "cmd": 65515, "win": 65515,
    "super_r": 65516, "cmd_r": 65516, "win_r": 65516,
    "space": 32,
    "tab": 65289, "return": 65293, "enter": 65293, "esc": 65307, "escape": 65307,
    "backspace": 65288,
    "f1": 65470, "f2": 65471, "f3": 65472, "f4": 65473, "f5": 65474,
    "f6": 65475, "f7": 65476, "f8": 65477, "f9": 65478, "f10": 65479,
    "f11": 65480, "f12": 65481, "f13": 65482, "f14": 65483, "f15": 65484,
    "f16": 65485, "f17": 65486, "f18": 65487, "f19": 65488, "f20": 65489,
}

_VK_ALIASES_WIN32: dict[str, int] = {
    "shift": 0x10, "shift_l": 0xA0, "shift_r": 0xA1,
    "ctrl": 0x11, "control": 0x11, "ctrl_l": 0xA2, "control_l": 0xA2,
    "ctrl_r": 0xA3, "control_r": 0xA3,
    "alt": 0x12, "alt_l": 0xA4, "alt_r": 0xA5,
    "win": 0x5B, "super": 0x5B, "super_l": 0x5B, "cmd": 0x5B,
    "super_r": 0x5C, "cmd_r": 0x5C, "win_r": 0x5C,
    "space": 0x20,
    "tab": 0x09, "return": 0x0D, "enter": 0x0D, "esc": 0x1B, "escape": 0x1B,
    "backspace": 0x08,
    "f1": 0x70, "f2": 0x71, "f3": 0x72, "f4": 0x73, "f5": 0x74,
    "f6": 0x75, "f7": 0x76, "f8": 0x77, "f9": 0x78, "f10": 0x79,
    "f11": 0x7A, "f12": 0x7B, "f13": 0x7C, "f14": 0x7D, "f15": 0x7E,
    "f16": 0x7F, "f17": 0x80, "f18": 0x81, "f19": 0x82, "f20": 0x83,
}

if sys.platform.startswith("win"):
    VK_ALIASES: dict[str, int] = _VK_ALIASES_WIN32
elif sys.platform == "darwin":
    # macOS pynput uses its own VK; we expose the X11-style names so existing
    # configs continue to parse, but `combo:` strings should generally be
    # avoided on macOS in favour of plain `<ctrl>+<…>` notation.
    VK_ALIASES = _VK_ALIASES_X11
else:
    VK_ALIASES = _VK_ALIASES_X11


def parse_combo(value: str) -> frozenset[int] | None:
    """Parse a `combo:` hotkey value into a set of X11 virtual key codes.

    Format: `combo:tok+tok+...` where each token is either a numeric vk
    or a name in :data:`VK_ALIASES` (case insensitive).
    """
    if not value.lower().startswith("combo:"):
        return None
    body = value.split(":", 1)[1]
    parts = [p.strip().lower() for p in body.split("+") if p.strip()]
    vks: set[int] = set()
    for part in parts:
        if part.isdigit():
            vks.add(int(part))
            continue
        vk = VK_ALIASES.get(part)
        if vk is None:
            logger.warning("Unknown combo token %r in %r", part, value)
            return None
        vks.add(vk)
    if not vks:
        return None
    return frozenset(vks)


def _mouse_buttons_by_name() -> dict[str, mouse.Button]:
    """Build alias map dynamically because pynput's Button enum differs per platform."""
    result: dict[str, mouse.Button] = {}
    members = {b.name: b for b in mouse.Button}
    for name in ("left", "right", "middle"):
        if name in members:
            result[name] = members[name]
    back = members.get("x1") or members.get("button8")
    forward = members.get("x2") or members.get("button9")
    if back is not None:
        result["back"] = back
        result["x1"] = back
        result["button8"] = back
    if forward is not None:
        result["forward"] = forward
        result["x2"] = forward
        result["button9"] = forward
    for name, btn in members.items():
        if name.startswith("button"):
            result[name] = btn
    return result


MOUSE_BUTTON_ALIASES: dict[str, mouse.Button] = _mouse_buttons_by_name()


def parse_mouse_button(value: str) -> mouse.Button | None:
    """Return the pynput mouse button for a hotkey-string like `mouse:back`."""
    if not value.lower().startswith("mouse:"):
        return None
    name = value.split(":", 1)[1].strip().lower()
    return MOUSE_BUTTON_ALIASES.get(name)


class HotkeyListener:
    """Listens for any number of keyboard combos and/or mouse-button triggers.

    Supports three trigger string formats simultaneously:
    - `mouse:<name>`   – a single mouse button (e.g. `mouse:button11`)
    - `combo:a+b+c`    – multiple keys held simultaneously, identified by vk
                         code or alias (e.g. `combo:shift+ctrl+meta+super+space`)
    - everything else  – passed to :class:`pynput.keyboard.GlobalHotKeys`
    """

    def __init__(self, hotkeys: Iterable[str], callback: Callable[[], None]) -> None:
        self._hotkeys: list[str] = [h for h in hotkeys if h]
        self._callback = callback
        self._keyboard_listener: keyboard.GlobalHotKeys | None = None
        self._mouse_listener: mouse.Listener | None = None
        self._combo_listener: keyboard.Listener | None = None
        self._mouse_buttons: set[mouse.Button] = set()
        self._combos: list[frozenset[int]] = []
        self._pressed_vks: set[int] = set()
        self._combos_already_fired: set[frozenset[int]] = set()

    def start(self) -> None:
        self.stop()

        keyboard_map: dict[str, Callable[[], None]] = {}
        mouse_buttons: set[mouse.Button] = set()
        combos: list[frozenset[int]] = []

        for trigger in self._hotkeys:
            mouse_btn = parse_mouse_button(trigger)
            if mouse_btn is not None:
                mouse_buttons.add(mouse_btn)
                continue
            combo = parse_combo(trigger)
            if combo is not None:
                combos.append(combo)
                continue
            keyboard_map[trigger] = self._on_keyboard_hotkey

        if keyboard_map:
            self._keyboard_listener = keyboard.GlobalHotKeys(keyboard_map)
            self._keyboard_listener.start()
            logger.info("Keyboard hotkeys registered: %s", list(keyboard_map))

        if mouse_buttons:
            self._mouse_buttons = mouse_buttons
            self._mouse_listener = mouse.Listener(on_click=self._on_mouse_click)
            self._mouse_listener.start()
            logger.info(
                "Mouse hotkeys registered: %s",
                [b.name for b in mouse_buttons],
            )

        if combos:
            self._combos = combos
            self._pressed_vks = set()
            self._combos_already_fired = set()
            self._combo_listener = keyboard.Listener(
                on_press=self._on_combo_press,
                on_release=self._on_combo_release,
            )
            self._combo_listener.start()
            logger.info(
                "Combo hotkeys registered: %s",
                [sorted(c) for c in combos],
            )

    def stop(self) -> None:
        for listener_attr in ("_keyboard_listener", "_mouse_listener", "_combo_listener"):
            listener = getattr(self, listener_attr, None)
            if listener is not None:
                listener.stop()
                setattr(self, listener_attr, None)
        self._mouse_buttons = set()
        self._combos = []
        self._pressed_vks = set()
        self._combos_already_fired = set()

    def update_hotkeys(self, hotkeys: Iterable[str]) -> None:
        self._hotkeys = [h for h in hotkeys if h]
        self.start()

    def _on_keyboard_hotkey(self) -> None:
        logger.debug("Keyboard hotkey triggered")
        try:
            self._callback()
        except Exception:
            logger.exception("Hotkey callback failed")

    def _on_mouse_click(self, x: int, y: int, button: mouse.Button, pressed: bool) -> None:
        if not pressed or button not in self._mouse_buttons:
            return
        logger.debug("Mouse hotkey triggered: %s", button)
        try:
            self._callback()
        except Exception:
            logger.exception("Hotkey callback failed")

    @staticmethod
    def _vk_of(key) -> int | None:
        vk = getattr(key, "vk", None)
        if vk is not None:
            return vk
        value = getattr(key, "value", None)
        if value is not None:
            return getattr(value, "vk", None)
        return None

    def _on_combo_press(self, key) -> None:
        vk = self._vk_of(key)
        if vk is None:
            return
        self._pressed_vks.add(vk)
        for combo in self._combos:
            if combo <= self._pressed_vks and combo not in self._combos_already_fired:
                self._combos_already_fired.add(combo)
                logger.debug("Combo hotkey triggered: %s", sorted(combo))
                try:
                    self._callback()
                except Exception:
                    logger.exception("Hotkey callback failed")

    def _on_combo_release(self, key) -> None:
        vk = self._vk_of(key)
        if vk is None:
            return
        self._pressed_vks.discard(vk)
        # Reset "already fired" flags for any combo that is no longer fully held.
        self._combos_already_fired = {
            c for c in self._combos_already_fired if c <= self._pressed_vks
        }
