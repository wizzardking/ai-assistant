from __future__ import annotations

import logging

from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QCursor, QPainter
from PyQt6.QtWidgets import QApplication

from ai_assistant.clipboard import ClipboardManager
from ai_assistant.config import load_config
from ai_assistant.hotkey import HotkeyListener
from ai_assistant.modules.registry import create_default_registry
from ai_assistant.ui.radial_menu import RadialMenu
from ai_assistant.ui.settings_dialog import SettingsDialog
from ai_assistant.ui.status_overlay import StatusOverlay
from ai_assistant.worker import ModuleWorker

logger = logging.getLogger(__name__)


class AppController:
    def __init__(self, app: QApplication) -> None:
        self._app = app
        self._config = load_config()
        self._registry = create_default_registry()
        self._clipboard = ClipboardManager()
        self._radial_menu = RadialMenu()
        self._status = StatusOverlay()
        self._hotkey: HotkeyListener | None = None

        self._selected_text = ""
        self._cursor_x = 0
        self._cursor_y = 0
        self._menu_open = False

        self._radial_menu.module_selected.connect(self._on_module_selected)
        self._radial_menu.module_interactive.connect(self._on_module_interactive)
        self._radial_menu.dismissed.connect(self._on_menu_dismissed)

        self._register_hotkey()

    def _register_hotkey(self) -> None:
        if self._hotkey is not None:
            self._hotkey.stop()
        self._hotkey = HotkeyListener(self._config.hotkey, self._on_hotkey)
        self._hotkey.start()

    def _on_hotkey(self) -> None:
        QTimer.singleShot(0, self._toggle_menu)

    def _toggle_menu(self) -> None:
        if self._menu_open:
            self._radial_menu.close_menu()
            return

        cursor = QCursor.pos()
        self._cursor_x = cursor.x()
        self._cursor_y = cursor.y()

        selected, _previous = self._clipboard.capture_selection()
        self._selected_text = selected

        if not selected:
            self._status.show_at(
                self._cursor_x,
                self._cursor_y,
                StatusOverlay.INFO,
                StatusOverlay.icon_path("error"),
                "Kein Text ausgewählt – Einstellungen weiterhin verfügbar",
            )

        self._menu_open = True
        self._radial_menu.show_at(
            self._cursor_x,
            self._cursor_y,
            self._registry.all(),
        )

    def _on_menu_dismissed(self) -> None:
        self._menu_open = False

    def _on_module_interactive(self, module_id: str) -> None:
        self._menu_open = False
        if module_id == "settings":
            self._open_settings()

    def _on_module_selected(self, module_id: str, action_id: str) -> None:
        self._menu_open = False
        module = self._registry.get(module_id)
        if module is None:
            return

        if not self._selected_text.strip():
            self._status.show_at(
                self._cursor_x,
                self._cursor_y,
                StatusOverlay.ERROR,
                StatusOverlay.icon_path("error"),
                "Kein Text ausgewählt",
            )
            return

        settings = self._config.get_module_settings(module_id, module.default_prompt())
        if not settings.model:
            settings.model = self._config.openai_default_model

        self._status.show_at(
            self._cursor_x,
            self._cursor_y,
            StatusOverlay.LOADING,
            StatusOverlay.icon_path("loading"),
        )

        coro = module.run(self._selected_text, action_id or None, settings)
        worker = ModuleWorker(coro)
        worker.finished_ok.connect(self._on_module_success)
        worker.finished_error.connect(self._on_module_error)
        worker.finished.connect(worker.deleteLater)
        worker.start()

    def _on_module_success(self, result: str) -> None:
        self._clipboard.write_text(result)
        self._status.show_at(
            self._cursor_x,
            self._cursor_y,
            StatusOverlay.DONE,
            StatusOverlay.icon_path("done"),
            "In Zwischenablage kopiert",
        )

    def _on_module_error(self, message: str) -> None:
        self._status.show_at(
            self._cursor_x,
            self._cursor_y,
            StatusOverlay.ERROR,
            StatusOverlay.icon_path("error"),
            message,
        )

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self._config, self._registry)
        if dialog.exec():
            self._config = dialog.config
            self._register_hotkey()
