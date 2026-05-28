from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ai_assistant.config import (
    ALL_LANGUAGES,
    AVAILABLE_MODELS,
    AppConfig,
    DEFAULT_HOTKEY,
    DEFAULT_LANGUAGES,
    DEFAULT_REPLY_PROMPT,
    DEFAULT_REWRITER_PROMPT,
    DEFAULT_TRANSLATOR_PROMPT,
    save_config,
)
from ai_assistant.modules.registry import ModuleRegistry
from ai_assistant.secrets import delete_openai_api_key, get_openai_api_key, set_openai_api_key


class SettingsDialog(QDialog):
    def __init__(self, config: AppConfig, registry: ModuleRegistry, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("AI Assistant – Einstellungen")
        self.resize(640, 560)

        self._config = config
        self._registry = registry

        layout = QVBoxLayout(self)
        self._tabs = QTabWidget()
        layout.addWidget(self._tabs)

        self._tabs.addTab(self._build_general_tab(), "Allgemein")
        self._tabs.addTab(self._build_openai_tab(), "OpenAI")
        self._tabs.addTab(self._build_translator_tab(), "Übersetzer")
        self._tabs.addTab(self._build_rewriter_tab(), "Umschreiben")
        self._tabs.addTab(self._build_reply_tab(), "Antwort verfassen")
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
        layout = QVBoxLayout(widget)
        form = QFormLayout()
        layout.addLayout(form)

        self._api_key_input = QLineEdit()
        self._api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        existing = get_openai_api_key()
        if existing:
            self._api_key_input.setPlaceholderText("Key gespeichert – leer lassen zum Beibehalten")
        else:
            self._api_key_input.setPlaceholderText("sk-...")
        form.addRow("API-Key:", self._api_key_input)

        self._default_model = QComboBox()
        self._default_model.addItems(AVAILABLE_MODELS)
        if self._config.openai_default_model in AVAILABLE_MODELS:
            self._default_model.setCurrentText(self._config.openai_default_model)
        form.addRow("Standard-Modell:", self._default_model)

        clear_btn = QPushButton("API-Key löschen")
        clear_btn.clicked.connect(self._clear_api_key)
        layout.addWidget(clear_btn)
        layout.addStretch()
        return widget

    def _build_translator_tab(self) -> QWidget:
        widget = QWidget()
        outer = QVBoxLayout(widget)

        module_settings = self._config.get_module_settings(
            "translator",
            DEFAULT_TRANSLATOR_PROMPT,
        )

        form = QFormLayout()
        outer.addLayout(form)

        self._translator_model = QComboBox()
        self._translator_model.addItems(AVAILABLE_MODELS)
        if module_settings.model in AVAILABLE_MODELS:
            self._translator_model.setCurrentText(module_settings.model)
        form.addRow("Modell:", self._translator_model)

        lang_box = QGroupBox("Verfügbare Sprachen im Radmenü")
        lang_layout = QGridLayout(lang_box)
        self._translator_lang_checkboxes: dict[str, QCheckBox] = {}
        current = set(module_settings.languages or DEFAULT_LANGUAGES)

        items = list(ALL_LANGUAGES.items())
        for index, (code, label) in enumerate(items):
            checkbox = QCheckBox(f"{label} ({code.upper()})")
            checkbox.setChecked(code in current)
            self._translator_lang_checkboxes[code] = checkbox
            lang_layout.addWidget(checkbox, index // 2, index % 2)
        outer.addWidget(lang_box)

        prompt_label = QLabel("Prompt-Vorlage (Platzhalter: {target_language}, {tone_instruction}, {text}):")
        outer.addWidget(prompt_label)
        self._translator_prompt = QPlainTextEdit(module_settings.prompt or DEFAULT_TRANSLATOR_PROMPT)
        outer.addWidget(self._translator_prompt)
        return widget

    def _build_rewriter_tab(self) -> QWidget:
        widget = QWidget()
        outer = QVBoxLayout(widget)

        module_settings = self._config.get_module_settings(
            "rewriter",
            DEFAULT_REWRITER_PROMPT,
        )

        form = QFormLayout()
        outer.addLayout(form)

        self._rewriter_model = QComboBox()
        self._rewriter_model.addItems(AVAILABLE_MODELS)
        if module_settings.model in AVAILABLE_MODELS:
            self._rewriter_model.setCurrentText(module_settings.model)
        form.addRow("Modell:", self._rewriter_model)

        prompt_label = QLabel("Prompt-Vorlage (Platzhalter: {tone_instruction}, {text}):")
        outer.addWidget(prompt_label)
        self._rewriter_prompt = QPlainTextEdit(module_settings.prompt or DEFAULT_REWRITER_PROMPT)
        outer.addWidget(self._rewriter_prompt)
        return widget

    def _build_reply_tab(self) -> QWidget:
        widget = QWidget()
        outer = QVBoxLayout(widget)

        module_settings = self._config.get_module_settings(
            "reply",
            DEFAULT_REPLY_PROMPT,
        )

        form = QFormLayout()
        outer.addLayout(form)

        self._reply_model = QComboBox()
        self._reply_model.addItems(AVAILABLE_MODELS)
        if module_settings.model in AVAILABLE_MODELS:
            self._reply_model.setCurrentText(module_settings.model)
        form.addRow("Modell:", self._reply_model)

        prompt_label = QLabel(
            "Prompt-Vorlage (Platzhalter: {tone_instruction}, {extra_instruction}, {text}):"
        )
        outer.addWidget(prompt_label)
        self._reply_prompt = QPlainTextEdit(module_settings.prompt or DEFAULT_REPLY_PROMPT)
        outer.addWidget(self._reply_prompt)
        return widget

    def _build_modules_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)

        lines = []
        for module in self._registry.all():
            lines.append(f"• {module.label} [{module.id}]")

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

        translator = self._config.get_module_settings("translator", DEFAULT_TRANSLATOR_PROMPT)
        translator.model = self._translator_model.currentText()
        translator.prompt = self._translator_prompt.toPlainText().strip() or DEFAULT_TRANSLATOR_PROMPT
        selected_langs = [
            code for code, checkbox in self._translator_lang_checkboxes.items()
            if checkbox.isChecked()
        ]
        if not selected_langs:
            selected_langs = list(DEFAULT_LANGUAGES)
        translator.languages = selected_langs

        rewriter = self._config.get_module_settings("rewriter", DEFAULT_REWRITER_PROMPT)
        rewriter.model = self._rewriter_model.currentText()
        rewriter.prompt = self._rewriter_prompt.toPlainText().strip() or DEFAULT_REWRITER_PROMPT

        reply = self._config.get_module_settings("reply", DEFAULT_REPLY_PROMPT)
        reply.model = self._reply_model.currentText()
        reply.prompt = self._reply_prompt.toPlainText().strip() or DEFAULT_REPLY_PROMPT

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
