from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ai_assistant.config import (
    AVAILABLE_MODELS,
    AppConfig,
    DEFAULT_HOTKEY,
    DEFAULT_TRANSLATOR_PROMPT,
    save_config,
)
from ai_assistant.modules.registry import ModuleRegistry
from ai_assistant.secrets import delete_openai_api_key, get_openai_api_key, set_openai_api_key


class SettingsDialog(QDialog):
    def __init__(self, config: AppConfig, registry: ModuleRegistry, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("AI Assistant – Einstellungen")
        self.resize(560, 460)

        self._config = config
        self._registry = registry

        layout = QVBoxLayout(self)
        self._tabs = QTabWidget()
        layout.addWidget(self._tabs)

        self._tabs.addTab(self._build_general_tab(), "Allgemein")
        self._tabs.addTab(self._build_openai_tab(), "OpenAI")
        self._tabs.addTab(self._build_translator_tab(), "Übersetzer")
        self._tabs.addTab(self._build_modules_tab(), "Module")

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _build_general_tab(self) -> QWidget:
        widget = QWidget()
        form = QFormLayout(widget)

        self._hotkey_input = QLineEdit(self._config.hotkey)
        self._hotkey_input.setPlaceholderText(DEFAULT_HOTKEY)
        form.addRow("Hotkey:", self._hotkey_input)

        hint = QLabel(
            "Standard: Ctrl+Shift+Leertaste\n"
            "Format: <ctrl>+<shift>+<space> (pynput-Syntax)\n"
            "Autostart: ~/.config/autostart/ai-assistant.desktop"
        )
        hint.setWordWrap(True)
        form.addRow(hint)

        return widget

    def _build_openai_tab(self) -> QWidget:
        widget = QWidget()
        form = QFormLayout(widget)

        self._api_key_input = QLineEdit()
        self._api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._api_key_input.setPlaceholderText("sk-...")
        existing = get_openai_api_key()
        if existing:
            self._api_key_input.setPlaceholderText("Key gespeichert – leer lassen zum Beibehalten")
        form.addRow("API-Key:", self._api_key_input)

        self._default_model = QComboBox()
        self._default_model.addItems(AVAILABLE_MODELS)
        current = self._config.openai_default_model
        if current in AVAILABLE_MODELS:
            self._default_model.setCurrentText(current)
        form.addRow("Standard-Modell:", self._default_model)

        clear_row = QHBoxLayout()
        clear_button = QDialogButtonBox()
        clear_btn = clear_button.addButton("Key löschen", QDialogButtonBox.ButtonRole.DestructiveRole)
        clear_btn.clicked.connect(self._clear_api_key)
        clear_row.addWidget(clear_btn)
        clear_row.addStretch()
        form.addRow(clear_row)

        return widget

    def _build_translator_tab(self) -> QWidget:
        widget = QWidget()
        form = QFormLayout(widget)

        module_settings = self._config.get_module_settings(
            "translator",
            DEFAULT_TRANSLATOR_PROMPT,
        )

        self._translator_model = QComboBox()
        self._translator_model.addItems(AVAILABLE_MODELS)
        if module_settings.model in AVAILABLE_MODELS:
            self._translator_model.setCurrentText(module_settings.model)
        form.addRow("Modell:", self._translator_model)

        self._translator_prompt = QPlainTextEdit(module_settings.prompt)
        self._translator_prompt.setPlaceholderText(
            "Platzhalter: {target_language}, {text}"
        )
        form.addRow("Prompt:", self._translator_prompt)

        return widget

    def _build_modules_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        lines = []
        for module in self._registry.all():
            action_count = len(module.actions())
            suffix = f" ({action_count} Aktionen)" if action_count else ""
            lines.append(f"• {module.label} [{module.id}]{suffix}")

        label = QLabel(
            "Registrierte Module:\n\n" + "\n".join(lines) + "\n\n"
            "Neue Module: Python-Datei in ai_assistant/modules/ anlegen "
            "und in registry.py registrieren."
        )
        label.setWordWrap(True)
        layout.addWidget(label)
        layout.addStretch()
        return widget

    def _clear_api_key(self) -> None:
        delete_openai_api_key()
        self._api_key_input.clear()
        QMessageBox.information(self, "API-Key", "OpenAI API-Key wurde gelöscht.")

    def _save(self) -> None:
        self._config.hotkey = self._hotkey_input.text().strip() or DEFAULT_HOTKEY
        self._config.openai_default_model = self._default_model.currentText()

        translator_settings = self._config.get_module_settings(
            "translator",
            DEFAULT_TRANSLATOR_PROMPT,
        )
        translator_settings.model = self._translator_model.currentText()
        translator_settings.prompt = self._translator_prompt.toPlainText().strip() or DEFAULT_TRANSLATOR_PROMPT

        api_key = self._api_key_input.text().strip()
        if api_key:
            try:
                set_openai_api_key(api_key)
            except RuntimeError as exc:
                QMessageBox.warning(self, "API-Key", str(exc))
                return

        save_config(self._config)
        self.accept()

    @property
    def config(self) -> AppConfig:
        return self._config
