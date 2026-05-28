from __future__ import annotations

import logging

from PyQt6.QtCore import Qt, QObject, pyqtSignal
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import QApplication, QInputDialog, QLineEdit, QMessageBox

from ai_assistant.clipboard import ClipboardManager
from ai_assistant.config import (
    AVAILABLE_IMAGE_MODELS,
    DEFAULT_CHAT_SYSTEM_PROMPT,
    DEFAULT_IMAGE_MODEL,
    DEFAULT_IMAGE_QUALITY,
    DEFAULT_IMAGE_SIZE,
    IMAGE_QUALITIES,
    IMAGE_SIZES,
    ModuleSettings,
    load_config,
)
from ai_assistant.hotkey import HotkeyListener
from ai_assistant.modules.base import DISPLAY_IMAGE, DISPLAY_WINDOW, MenuNode
from ai_assistant.modules.registry import create_default_registry
from ai_assistant.ui.chat_window import ChatWindow
from ai_assistant.ui.image_prompt_dialog import ImagePromptDialog
from ai_assistant.ui.image_result_window import ImageResultWindow
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
        self._active_extra_input = ""
        self._chat_windows: list[ChatWindow] = []

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
        elif module_id == "chat":
            self._open_chat()

    def _on_leaf_selected(self, module_id: str, path: tuple, leaf: MenuNode) -> None:
        logger.info(
            "Leaf selected: module=%s path=%s extra_input=%s",
            module_id, path, leaf.needs_extra_input,
        )
        module = self._registry.get(module_id)
        if module is None:
            logger.warning("Module %r not found", module_id)
            return

        requires_selection = getattr(module, "requires_selection", True)
        if requires_selection:
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

        settings = self._config.get_module_settings(module_id, module.default_prompt())
        display_mode = getattr(module, "display_mode", "clipboard")

        # Pick a sensible default model: image modules need an image model,
        # everything else falls back to the OpenAI chat default.
        if display_mode == DISPLAY_IMAGE:
            if not settings.model or settings.model not in AVAILABLE_IMAGE_MODELS:
                settings.model = DEFAULT_IMAGE_MODEL
        elif not settings.model:
            settings.model = self._config.openai_default_model

        extra_input = ""
        if leaf.needs_extra_input:
            if module_id == "image_generate":
                result = self._prompt_image_input(leaf.extra_input_prompt, settings)
                if result is None:
                    logger.info("Image prompt dialog cancelled")
                    return
                prompt_text, chosen_size, chosen_quality = result
                extra_input = prompt_text
                # Override size/quality for this run only.
                settings = settings.model_copy()
                settings.image_size = chosen_size or settings.image_size or DEFAULT_IMAGE_SIZE
                settings.image_quality = (
                    chosen_quality or settings.image_quality or DEFAULT_IMAGE_QUALITY
                )
            else:
                extra_input = self._prompt_extra_input(leaf.extra_input_prompt)
                if extra_input is None:
                    logger.info("Extra-input dialog cancelled")
                    return

        logger.info("Running module %s (model=%s, path=%s)", module_id, settings.model, path)
        self._active_module_id = module_id
        self._active_extra_input = extra_input
        self._status.show_at(
            self._cursor_x,
            self._cursor_y,
            StatusOverlay.LOADING,
            StatusOverlay.icon_path("loading"),
        )

        text_for_run = self._selected_text if requires_selection else ""
        coro = module.run(text_for_run, tuple(path), settings, extra_input)
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

    def _prompt_image_input(
        self,
        prompt_label: str,
        settings: ModuleSettings,
    ) -> tuple[str, str, str] | None:
        default_size = settings.image_size or DEFAULT_IMAGE_SIZE
        default_quality = settings.image_quality or DEFAULT_IMAGE_QUALITY
        dialog = ImagePromptDialog(
            prompt_label=prompt_label or "Beschreibe das gewünschte Bild.",
            default_size=default_size,
            available_sizes=list(IMAGE_SIZES),
            default_quality=default_quality,
            available_qualities=list(IMAGE_QUALITIES),
        )
        if not dialog.exec():
            return None
        prompt_text = dialog.prompt_text()
        if not prompt_text:
            return None
        return prompt_text, dialog.selected_size(), dialog.selected_quality()

    def _on_module_success(self, result) -> None:
        module = self._registry.get(self._active_module_id or "")
        display_mode = getattr(module, "display_mode", "clipboard")

        if display_mode == DISPLAY_IMAGE and module is not None:
            size = len(result) if isinstance(result, (bytes, bytearray)) else 0
            logger.info("Image module finished OK (%d bytes)", size)
            self._status.hide()
            self._show_image_window(self._active_extra_input, bytes(result))
            return

        text_result = result if isinstance(result, str) else str(result)
        logger.info("Module finished OK (%d chars)", len(text_result))

        if display_mode == DISPLAY_WINDOW and module is not None:
            self._status.hide()
            self._show_result_window(module.label, text_result)
            return

        self._clipboard.write_text(text_result)
        self._status.show_at(
            self._cursor_x,
            self._cursor_y,
            StatusOverlay.DONE,
            StatusOverlay.icon_path("done"),
            "In Zwischenablage kopiert",
        )

    def _show_image_window(self, prompt: str, image_bytes: bytes) -> None:
        window = ImageResultWindow(prompt=prompt, image_bytes=image_bytes)
        window.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        window.finished.connect(lambda _=None, w=window: self._result_windows.remove(w) if w in self._result_windows else None)
        self._result_windows.append(window)
        window.show()
        window.raise_()
        window.activateWindow()

    def _open_chat(self) -> None:
        module = self._registry.get("chat")
        if module is None:
            return
        settings = self._config.get_module_settings("chat", module.default_prompt())
        if not settings.model:
            settings.model = self._config.openai_default_model
        system_prompt = settings.system_prompt or settings.prompt or DEFAULT_CHAT_SYSTEM_PROMPT
        window = ChatWindow(model=settings.model, system_prompt=system_prompt)
        window.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        window.finished.connect(lambda _=None, w=window: self._chat_windows.remove(w) if w in self._chat_windows else None)
        self._chat_windows.append(window)
        window.show()
        window.raise_()
        window.activateWindow()

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
