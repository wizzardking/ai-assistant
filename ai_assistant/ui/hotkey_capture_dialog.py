"""Dialog that records a key combination or mouse button to use as a hotkey.

Recording rules:
    - Tracks all simultaneously pressed virtual key codes; the largest set
      seen during a press cycle becomes the captured combo.
    - Mouse movement is ignored.
    - Left/right mouse buttons are silently ignored (so the user can still
      click the dialog buttons).
    - Esc on its own cancels the dialog.
    - Enter on its own is rejected with a hint.
"""

from __future__ import annotations

import logging
import sys

from PyQt6.QtCore import Qt, QMetaObject, Q_ARG, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)
from pynput import keyboard, mouse

from ai_assistant.hotkey import format_hotkey

logger = logging.getLogger(__name__)


# VK codes for keys that may not be assigned alone.
_ESC_VKS = {65307, 0x1B}
_ENTER_VKS = {65293, 0x0D}


class HotkeyCaptureDialog(QDialog):
    progress_signal = pyqtSignal(str)
    capture_signal = pyqtSignal(str)
    cancel_signal = pyqtSignal()
    info_signal = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Hotkey aufnehmen")
        self.setModal(True)
        self.resize(440, 260)

        self._captured_value: str = ""
        self._pressed: set[int] = set()
        self._high_water: set[int] = set()

        self._build_ui()

        self._kb_listener: keyboard.Listener | None = None
        self._mouse_listener: mouse.Listener | None = None
        self._start_listeners()

        self.progress_signal.connect(self._on_progress)
        self.capture_signal.connect(self._on_capture)
        self.cancel_signal.connect(self.reject)
        self.info_signal.connect(self._on_info)

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 12)
        layout.setSpacing(10)

        intro = QLabel(
            "Drücke jetzt die gewünschte Tastenkombination oder einen Maus-Button.\n"
            "Linke/rechte Maustaste, Esc und Enter sind nicht zulässig.\n"
            "Esc allein bricht ab."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        self._display = QLabel("…")
        big = QFont(self.font())
        big.setBold(True)
        big.setPointSize(big.pointSize() + 4)
        self._display.setFont(big)
        self._display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._display.setStyleSheet(
            "padding: 14px; background: #1f1f1f; color: #f0f0f0; border-radius: 4px;"
        )
        layout.addWidget(self._display, 1)

        self._info = QLabel("")
        self._info.setStyleSheet("color: #ffaa66;")
        layout.addWidget(self._info)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self._ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        self._ok_btn.setEnabled(False)
        # Important: don't make OK the default button – otherwise pressing Enter
        # to cancel would actually accept whatever is currently captured.
        self._ok_btn.setAutoDefault(False)
        self._ok_btn.setDefault(False)
        cancel_btn = buttons.button(QDialogButtonBox.StandardButton.Cancel)
        cancel_btn.setAutoDefault(False)
        cancel_btn.setDefault(False)

        retry_btn = QPushButton("Zurücksetzen")
        retry_btn.setAutoDefault(False)
        retry_btn.clicked.connect(self._reset_capture)

        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        row = QHBoxLayout()
        row.addWidget(retry_btn)
        row.addStretch()
        row.addWidget(buttons)
        layout.addLayout(row)

    @pyqtSlot(str)
    def _on_progress(self, text: str) -> None:
        self._display.setText(text or "…")

    @pyqtSlot(str)
    def _on_capture(self, hotkey: str) -> None:
        self._captured_value = hotkey
        self._display.setText(format_hotkey(hotkey))
        self._info.setText("Hotkey erfasst – mit OK übernehmen oder erneut drücken.")
        self._ok_btn.setEnabled(bool(hotkey))

    @pyqtSlot(str)
    def _on_info(self, text: str) -> None:
        self._info.setText(text)

    def _reset_capture(self) -> None:
        self._captured_value = ""
        self._pressed.clear()
        self._high_water.clear()
        self._display.setText("…")
        self._info.setText("")
        self._ok_btn.setEnabled(False)

    # ------------------------------------------------------------------
    # Result
    # ------------------------------------------------------------------
    def hotkey(self) -> str:
        return self._captured_value

    # ------------------------------------------------------------------
    # Listener lifecycle
    # ------------------------------------------------------------------
    def _start_listeners(self) -> None:
        self._stop_listeners()
        try:
            self._kb_listener = keyboard.Listener(
                on_press=self._on_press, on_release=self._on_release
            )
            self._kb_listener.start()
        except Exception:
            logger.exception("Failed to start keyboard listener for capture")
        try:
            self._mouse_listener = mouse.Listener(on_click=self._on_click)
            self._mouse_listener.start()
        except Exception:
            logger.exception("Failed to start mouse listener for capture")

    def _stop_listeners(self) -> None:
        for attr in ("_kb_listener", "_mouse_listener"):
            listener = getattr(self, attr, None)
            if listener is not None:
                try:
                    listener.stop()
                except Exception:
                    pass
                setattr(self, attr, None)

    def closeEvent(self, event) -> None:
        self._stop_listeners()
        super().closeEvent(event)

    def reject(self) -> None:
        self._stop_listeners()
        super().reject()

    def accept(self) -> None:
        self._stop_listeners()
        super().accept()

    # ------------------------------------------------------------------
    # Listener callbacks (run on background threads)
    # ------------------------------------------------------------------
    @staticmethod
    def _vk_of(key) -> int | None:
        vk = getattr(key, "vk", None)
        if vk is not None:
            return vk
        value = getattr(key, "value", None)
        if value is not None:
            return getattr(value, "vk", None)
        return None

    def _on_press(self, key) -> None:
        try:
            vk = self._vk_of(key)
            if vk is None:
                return

            # Esc allein → Cancel.
            if vk in _ESC_VKS and not self._pressed:
                self.cancel_signal.emit()
                return
            # Enter allein → ablehnen.
            if vk in _ENTER_VKS and not self._pressed:
                self.info_signal.emit("Enter ist als Hotkey nicht zulässig.")
                return

            self._pressed.add(vk)
            if len(self._pressed) > len(self._high_water):
                self._high_water = set(self._pressed)

            from ai_assistant.hotkey import _vk_label  # type: ignore[attr-defined]
            label = " + ".join(_vk_label(v) for v in sorted(self._high_water))
            self.progress_signal.emit(label)
        except Exception:
            logger.exception("on_press failed")

    def _on_release(self, key) -> None:
        try:
            vk = self._vk_of(key)
            if vk is None:
                return
            self._pressed.discard(vk)

            if self._pressed:
                return  # still pressing other keys
            if not self._high_water:
                return

            # Sanity check: don't accept Esc/Enter alone (they were rejected
            # in on_press already, but be defensive).
            if (
                self._high_water.issubset(_ESC_VKS | _ENTER_VKS)
                and len(self._high_water) <= 1
            ):
                self._high_water = set()
                return

            value = "combo:" + "+".join(str(v) for v in sorted(self._high_water))
            self._high_water = set()
            self.capture_signal.emit(value)
        except Exception:
            logger.exception("on_release failed")

    def _on_click(self, x, y, button, pressed) -> None:
        try:
            if not pressed:
                return
            name = button.name if hasattr(button, "name") else str(button)
            if name in ("left", "right"):
                # Silently ignore so the user can still click the OK/Cancel buttons.
                return
            self.capture_signal.emit(f"mouse:{name}")
        except Exception:
            logger.exception("on_click failed")
