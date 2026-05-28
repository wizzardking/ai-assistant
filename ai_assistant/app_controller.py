from __future__ import annotations

import logging

from PyQt6.QtCore import Qt, QObject, pyqtSignal
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import QApplication, QInputDialog, QLineEdit, QMessageBox

from ai_assistant.clipboard import ClipboardManager
from ai_assistant.config import ModuleSettings, load_config
from ai_assistant.hotkey import HotkeyListener
from ai_assistant.modules.base import DISPLAY_WINDOW, MenuNode
from ai_assistant.modules.registry import create_default_registry
from ai_assistant.ui.radial_menu import RadialMenu
from ai_assistant.ui.result_window import ResultWindow
from ai_assistant.ui.settings_dialog import SettingsDialog
from ai_assistant.ui.status_overlay import StatusOverlay
from ai_assistant.worker import ClipboardCaptureWorker, ModuleWorker

logger = logging.getLogger(__name__)


class AppController(QObject):
    hotkey_triggered = pyqtSignal()

    def __init__(self, app: QApplication) -> None:
        super().__init__()
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
        self._worker: ModuleWorker | None = None
        self._active_module_id: str | None = None
        self._result_windows: list[ResultWindow] = []
        self._capture_worker: ClipboardCaptureWorker | None = None
        self._capture_done = False

        self._radial_menu.leaf_selected.connect(self._on_leaf_selected)
        self._radial_menu.module_interactive.connect(self._on_module_interactive)
        self.hotkey_triggered.connect(self._open_menu)

        self._register_hotkey()

    def _register_hotkey(self) -> None:
        if self._hotkey is not None:
            self._hotkey.stop()
        self._hotkey = HotkeyListener(self._config.active_hotkeys(), self._on_hotkey)
        self._hotkey.start()

    def _on_hotkey(self) -> None:
        self.hotkey_triggered.emit()

    def _settings_for(self, module_id: str, default_prompt: str) -> ModuleSettings:
        return self._config.get_module_settings(module_id, default_prompt)

    def _open_menu(self) -> None:
        if self._radial_menu.isVisible():
            logger.debug("Menu already open, ignoring hotkey")
            return

        cursor = QCursor.pos()
        self._cursor_x = cursor.x()
        self._cursor_y = cursor.y()

        # Show the menu immediately and capture the selection on a worker thread
        # so the UI never blocks behind xclip / Ctrl+C polling.
        self._selected_text = ""
        self._capture_done = False
        self._radial_menu.show_at(
            self._cursor_x,
            self._cursor_y,
            self._registry.all(),
            self._settings_for,
        )

        worker = ClipboardCaptureWorker(self._clipboard)
        worker.finished_capture.connect(self._on_capture_finished)
        worker.finished.connect(worker.deleteLater)
        self._capture_worker = worker
        worker.start()

    def _on_capture_finished(self, selected: str, _previous) -> None:
        self._selected_text = selected
        self._capture_done = True
        logger.info("Capture finished (%d chars)", len(selected))

    def _on_module_interactive(self, module_id: str) -> None:
        if module_id == "settings":
            self._open_settings()

    def _on_leaf_selected(self, module_id: str, path: tuple, leaf: MenuNode) -> None:
        logger.info(
            "Leaf selected: module=%s path=%s extra_input=%s",
            module_id, path, leaf.needs_extra_input,
        )
        module = self._registry.get(module_id)
        if module is None:
            logger.warning("Module %r not found", module_id)
            return

        # The clipboard capture runs in the background; wait briefly if the
        # user clicked an action before it had a chance to finish.
        if not self._capture_done and self._capture_worker is not None:
            logger.info("Waiting for clipboard capture to finish...")
            self._capture_worker.wait(2000)

        if not self._selected_text.strip():
            self._status.show_at(
                self._cursor_x,
                self._cursor_y,
                StatusOverlay.ERROR,
                StatusOverlay.icon_path("error"),
                "Kein Text ausgewählt",
            )
            return

        extra_input = ""
        if leaf.needs_extra_input:
            extra_input = self._prompt_extra_input(leaf.extra_input_prompt)
            if extra_input is None:
                logger.info("Extra-input dialog cancelled")
                return

        settings = self._config.get_module_settings(module_id, module.default_prompt())
        if not settings.model:
            settings.model = self._config.openai_default_model

        logger.info("Running module %s (model=%s, path=%s)", module_id, settings.model, path)
        self._active_module_id = module_id
        self._status.show_at(
            self._cursor_x,
            self._cursor_y,
            StatusOverlay.LOADING,
            StatusOverlay.icon_path("loading"),
        )

        coro = module.run(self._selected_text, tuple(path), settings, extra_input)
        worker = ModuleWorker(coro)
        worker.finished_ok.connect(self._on_module_success)
        worker.finished_error.connect(self._on_module_error)
        worker.finished.connect(worker.deleteLater)
        self._worker = worker
        worker.start()

    def _prompt_extra_input(self, prompt: str) -> str | None:
        text, ok = QInputDialog.getMultiLineText(
            None,
            "AI Assistant – Zusatzinfos",
            prompt or "Welche Zusatzinformationen sollen einfließen?",
            "",
        )
        if not ok:
            return None
        return text or ""

    def _on_module_success(self, result: str) -> None:
        logger.info("Module finished OK (%d chars)", len(result))
        module = self._registry.get(self._active_module_id or "")
        display_mode = getattr(module, "display_mode", "clipboard")

        if display_mode == DISPLAY_WINDOW and module is not None:
            self._status.hide()
            self._show_result_window(module.label, result)
            return

        self._clipboard.write_text(result)
        self._status.show_at(
            self._cursor_x,
            self._cursor_y,
            StatusOverlay.DONE,
            StatusOverlay.icon_path("done"),
            "In Zwischenablage kopiert",
        )

    def _show_result_window(self, title: str, result: str) -> None:
        window = ResultWindow(
            title=title,
            text=result,
            copy_callback=self._clipboard.write_text,
        )
        window.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        window.finished.connect(lambda _=None, w=window: self._result_windows.remove(w) if w in self._result_windows else None)
        self._result_windows.append(window)
        window.show()
        window.raise_()
        window.activateWindow()

    def _on_module_error(self, message: str) -> None:
        logger.error("Module failed: %s", message)
        self._status.show_at(
            self._cursor_x,
            self._cursor_y,
            StatusOverlay.ERROR,
            StatusOverlay.icon_path("error"),
            message,
        )
        QMessageBox.warning(None, "AI Assistant – Fehler", message)

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self._config, self._registry)
        if dialog.exec():
            self._config = dialog.config
            self._register_hotkey()
