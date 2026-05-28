from __future__ import annotations

import logging

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
    AVAILABLE_IMAGE_MODELS,
    AVAILABLE_MODELS,
    AppConfig,
    DEFAULT_CHAT_SYSTEM_PROMPT,
    DEFAULT_EXPLAIN_PROMPT,
    DEFAULT_HOTKEY,
    DEFAULT_IMAGE_MODEL,
    DEFAULT_IMAGE_PROMPT,
    DEFAULT_IMAGE_QUALITY,
    DEFAULT_IMAGE_SIZE,
    DEFAULT_LANGUAGES,
    DEFAULT_REPLY_PROMPT,
    DEFAULT_REWRITER_PROMPT,
    DEFAULT_SUMMARIZE_PROMPT,
    DEFAULT_TRANSLATOR_PROMPT,
    IMAGE_QUALITIES,
    IMAGE_SIZES,
    save_config,
)
from ai_assistant.modules.registry import ModuleRegistry
from ai_assistant.secrets import delete_openai_api_key, get_openai_api_key, set_openai_api_key

logger = logging.getLogger(__name__)


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
        self._tabs.addTab(self._build_summarize_tab(), "Zusammenfassen")
        self._tabs.addTab(self._build_explain_tab(), "Erklären")
        self._tabs.addTab(self._build_image_tab(), "Bildgenerierung")
        self._tabs.addTab(self._build_chat_tab(), "Chat")
        self._tabs.addTab(self._build_modules_tab(), "Module")

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _build_general_tab(self) -> QWidget:
        widget = QWidget()
        outer = QVBoxLayout(widget)

        label = QLabel("Auslöser (alle gleichzeitig aktiv – einer pro Zeile):")
        outer.addWidget(label)

        self._hotkeys_edit = QPlainTextEdit("\n".join(self._config.active_hotkeys()))
        self._hotkeys_edit.setPlaceholderText(DEFAULT_HOTKEY)
        outer.addWidget(self._hotkeys_edit, 1)

        hint = QLabel(
            "Maus-Buttons: mouse:back, mouse:forward, mouse:middle, mouse:button8 … mouse:button30\n"
            "Tastatur (pynput-Syntax): <f6>, <f13>, <ctrl>+<shift>+<space>, etc.\n"
            "Tipp: scripts/identify_keyboard_key.py liefert die korrekte Bezeichnung\n"
            "Autostart: ~/.config/autostart/ai-assistant.desktop"
        )
        hint.setWordWrap(True)
        outer.addWidget(hint)

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

    def _build_summarize_tab(self) -> QWidget:
        widget = QWidget()
        outer = QVBoxLayout(widget)

        module_settings = self._config.get_module_settings(
            "summarize",
            DEFAULT_SUMMARIZE_PROMPT,
        )

        form = QFormLayout()
        outer.addLayout(form)

        self._summarize_model = QComboBox()
        self._summarize_model.addItems(AVAILABLE_MODELS)
        if module_settings.model in AVAILABLE_MODELS:
            self._summarize_model.setCurrentText(module_settings.model)
        form.addRow("Modell:", self._summarize_model)

        prompt_label = QLabel("Prompt-Vorlage (Platzhalter: {text}):")
        outer.addWidget(prompt_label)
        self._summarize_prompt = QPlainTextEdit(module_settings.prompt or DEFAULT_SUMMARIZE_PROMPT)
        outer.addWidget(self._summarize_prompt)
        return widget

    def _build_explain_tab(self) -> QWidget:
        widget = QWidget()
        outer = QVBoxLayout(widget)

        module_settings = self._config.get_module_settings(
            "explain",
            DEFAULT_EXPLAIN_PROMPT,
        )

        form = QFormLayout()
        outer.addLayout(form)

        self._explain_model = QComboBox()
        self._explain_model.addItems(AVAILABLE_MODELS)
        if module_settings.model in AVAILABLE_MODELS:
            self._explain_model.setCurrentText(module_settings.model)
        form.addRow("Modell:", self._explain_model)

        prompt_label = QLabel("Prompt-Vorlage (Platzhalter: {text}):")
        outer.addWidget(prompt_label)
        self._explain_prompt = QPlainTextEdit(module_settings.prompt or DEFAULT_EXPLAIN_PROMPT)
        outer.addWidget(self._explain_prompt)
        return widget

    def _build_image_tab(self) -> QWidget:
        widget = QWidget()
        outer = QVBoxLayout(widget)

        module_settings = self._config.get_module_settings(
            "image_generate",
            DEFAULT_IMAGE_PROMPT,
        )
        if not module_settings.model or module_settings.model not in AVAILABLE_IMAGE_MODELS:
            module_settings.model = DEFAULT_IMAGE_MODEL
        if not module_settings.image_size:
            module_settings.image_size = DEFAULT_IMAGE_SIZE
        if not module_settings.image_quality:
            module_settings.image_quality = DEFAULT_IMAGE_QUALITY

        form = QFormLayout()
        outer.addLayout(form)

        self._image_model = QComboBox()
        self._image_model.addItems(AVAILABLE_IMAGE_MODELS)
        self._image_model.setEditable(True)
        self._image_model.setCurrentText(module_settings.model)
        form.addRow("Modell:", self._image_model)

        self._image_size = QComboBox()
        self._image_size.addItems(IMAGE_SIZES)
        self._image_size.setEditable(True)
        if module_settings.image_size in IMAGE_SIZES:
            self._image_size.setCurrentText(module_settings.image_size)
        else:
            self._image_size.setCurrentText(module_settings.image_size or DEFAULT_IMAGE_SIZE)
        form.addRow("Bildgröße (Vorauswahl):", self._image_size)

        self._image_quality = QComboBox()
        self._image_quality.addItems(IMAGE_QUALITIES)
        if module_settings.image_quality in IMAGE_QUALITIES:
            self._image_quality.setCurrentText(module_settings.image_quality)
        else:
            self._image_quality.setCurrentText(DEFAULT_IMAGE_QUALITY)
        form.addRow("Qualität (Vorauswahl):", self._image_quality)

        prompt_label = QLabel("Prompt-Vorlage (Platzhalter: {prompt}):")
        outer.addWidget(prompt_label)
        self._image_prompt = QPlainTextEdit(module_settings.prompt or DEFAULT_IMAGE_PROMPT)
        outer.addWidget(self._image_prompt)
        return widget

    def _build_chat_tab(self) -> QWidget:
        widget = QWidget()
        outer = QVBoxLayout(widget)

        module_settings = self._config.get_module_settings(
            "chat",
            DEFAULT_CHAT_SYSTEM_PROMPT,
        )

        form = QFormLayout()
        outer.addLayout(form)

        self._chat_model = QComboBox()
        self._chat_model.addItems(AVAILABLE_MODELS)
        if module_settings.model in AVAILABLE_MODELS:
            self._chat_model.setCurrentText(module_settings.model)
        form.addRow("Modell:", self._chat_model)

        prompt_label = QLabel("System-Prompt (legt Tonalität und Verhalten fest):")
        outer.addWidget(prompt_label)
        existing_system = module_settings.system_prompt or module_settings.prompt or DEFAULT_CHAT_SYSTEM_PROMPT
        self._chat_system_prompt = QPlainTextEdit(existing_system)
        outer.addWidget(self._chat_system_prompt)
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
        hotkey_lines = [
            line.strip()
            for line in self._hotkeys_edit.toPlainText().splitlines()
            if line.strip()
        ]
        if not hotkey_lines:
            hotkey_lines = [DEFAULT_HOTKEY]
        self._config.hotkeys = hotkey_lines
        self._config.hotkey = hotkey_lines[0]
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

        summarize = self._config.get_module_settings("summarize", DEFAULT_SUMMARIZE_PROMPT)
        summarize.model = self._summarize_model.currentText()
        summarize.prompt = self._summarize_prompt.toPlainText().strip() or DEFAULT_SUMMARIZE_PROMPT

        explain = self._config.get_module_settings("explain", DEFAULT_EXPLAIN_PROMPT)
        explain.model = self._explain_model.currentText()
        explain.prompt = self._explain_prompt.toPlainText().strip() or DEFAULT_EXPLAIN_PROMPT

        image = self._config.get_module_settings("image_generate", DEFAULT_IMAGE_PROMPT)
        image.model = self._image_model.currentText().strip() or DEFAULT_IMAGE_MODEL
        image.image_size = self._image_size.currentText().strip() or DEFAULT_IMAGE_SIZE
        image.image_quality = self._image_quality.currentText().strip() or DEFAULT_IMAGE_QUALITY
        image.prompt = self._image_prompt.toPlainText().strip() or DEFAULT_IMAGE_PROMPT

        chat = self._config.get_module_settings("chat", DEFAULT_CHAT_SYSTEM_PROMPT)
        chat.model = self._chat_model.currentText()
        chat.system_prompt = self._chat_system_prompt.toPlainText().strip() or DEFAULT_CHAT_SYSTEM_PROMPT
        chat.prompt = chat.system_prompt

        api_key = self._api_key_input.text().strip()
        if api_key:
            try:
                set_openai_api_key(api_key)
            except Exception as exc:
                logger.exception("Saving API key failed")
                QMessageBox.warning(
                    self,
                    "API-Key",
                    f"Speichern des API-Keys fehlgeschlagen:\n{exc}\n\n"
                    "Andere Einstellungen werden trotzdem gespeichert.",
                )

        try:
            save_config(self._config)
        except Exception as exc:
            logger.exception("Saving config failed")
            QMessageBox.warning(self, "Einstellungen", f"Speichern fehlgeschlagen:\n{exc}")
            return
        self.accept()

    @property
    def config(self) -> AppConfig:
        return self._config
