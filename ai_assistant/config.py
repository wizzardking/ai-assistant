from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

try:
    from platformdirs import user_config_dir
    CONFIG_DIR = Path(user_config_dir("ai-assistant", appauthor=False))
except Exception:
    # Last-resort fallback: ~/.config/ai-assistant on POSIX, %APPDATA%\ai-assistant on Windows.
    if sys.platform.startswith("win"):
        import os
        CONFIG_DIR = Path(os.environ.get("APPDATA", str(Path.home()))) / "ai-assistant"
    else:
        CONFIG_DIR = Path.home() / ".config" / "ai-assistant"
CONFIG_PATH = CONFIG_DIR / "config.json"

# Default trigger differs per platform: Linux ships with a mouse-button mapping
# that the user can rebind via Input Remapper; Windows uses a plain modifier
# combo because mouse drivers (Logitech Options, etc.) often hijack extra
# mouse buttons before they reach the OS.
if sys.platform.startswith("win"):
    DEFAULT_HOTKEY = "<shift>+<ctrl>+<space>"
    DEFAULT_HOTKEYS: list[str] = ["<shift>+<ctrl>+<space>"]
else:
    DEFAULT_HOTKEY = "mouse:button11"
    DEFAULT_HOTKEYS = ["mouse:button11", "<ctrl>+<shift>+<cmd>+<space>"]
AVAILABLE_MODELS = ["gpt-5.5", "gpt-5.4-nano"]
AVAILABLE_IMAGE_MODELS = ["gpt-image-2", "gpt-image-1"]
DEFAULT_MODEL = "gpt-5.5"
DEFAULT_IMAGE_MODEL = "gpt-image-2"
DEFAULT_PROVIDER = "openai"

# Conservative context-window estimates per chat model (in tokens). When a
# conversation grows beyond this, the chat UI asks the user to start a new
# chat instead of silently truncating.
MODEL_TOKEN_LIMITS: dict[str, int] = {
    "gpt-5.5": 128_000,
    "gpt-5.4-nano": 128_000,
}
DEFAULT_TOKEN_LIMIT = 128_000
# Tokens we reserve for the model's response when evaluating the prompt size.
RESPONSE_TOKEN_RESERVE = 2_048


def token_limit_for(model: str) -> int:
    return MODEL_TOKEN_LIMITS.get(model, DEFAULT_TOKEN_LIMIT)
IMAGE_SIZES = [
    "1024x1024",
    "1024x1536",
    "1536x1024",
    "2560x1440",
    "3840x2160",
]
DEFAULT_IMAGE_SIZE = "1024x1024"
IMAGE_QUALITIES = ["auto", "high", "medium", "low"]
DEFAULT_IMAGE_QUALITY = "auto"

ALL_LANGUAGES: dict[str, str] = {
    "de": "Deutsch",
    "en": "Englisch",
    "fr": "Französisch",
    "it": "Italienisch",
    "es": "Spanisch",
    "pt": "Portugiesisch",
    "nl": "Niederländisch",
    "pl": "Polnisch",
    "tr": "Türkisch",
    "ru": "Russisch",
    "ja": "Japanisch",
    "zh": "Chinesisch",
}
DEFAULT_LANGUAGES = ["de", "en"]

TONES: dict[str, str] = {
    "plain": "Nur übersetzen",
    "formal": "Professionell sachlich",
    "warm": "Professionell warm",
    "personal": "Persönlich",
    "flirty": "Flirtig",
}

TONE_INSTRUCTIONS: dict[str, str] = {
    "plain": "",
    "formal": "Formuliere den Text in einem professionellen, sachlichen Ton.",
    "warm": "Formuliere den Text in einem professionellen, warmen und freundlichen Ton.",
    "personal": "Formuliere den Text in einem persönlichen, lockeren Ton.",
    "flirty": "Formuliere den Text in einem flirtenden, charmanten Ton.",
}

DEFAULT_TRANSLATOR_PROMPT = (
    "Übersetze den folgenden Text ins {target_language}. {tone_instruction}"
    "Gib nur das Ergebnis zurück, ohne Erklärung.\n\n{text}"
)

DEFAULT_REWRITER_PROMPT = (
    "Schreibe den folgenden Text um. {tone_instruction}"
    "Behalte die Sprache des Originals bei. Gib nur das Ergebnis zurück, ohne Erklärung.\n\n{text}"
)

DEFAULT_REPLY_PROMPT = (
    "Du verfasst eine Antwort{user_name_clause}. "
    "Falls die folgende Nachricht ein kompletter Gesprächsverlauf ist, "
    "{user_perspective_clause}"
    "{tone_instruction}"
    "Behalte die Sprache des Originals bei. "
    "{extra_instruction}"
    "Gib nur die Antwort zurück, ohne Meta-Kommentar oder Erklärung.\n\n"
    "Nachricht:\n{text}"
)

# Older default that hardcoded "Robin Hansson"; we migrate this to a blank
# prompt so the new default kicks in.
_LEGACY_REPLY_PROMPTS: list[str] = [
    (
        "Du verfasst eine Antwort im Namen von Robin Hansson. "
        "Falls die folgende Nachricht ein kompletter Gesprächsverlauf ist, "
        "ist Robin Hansson die antwortende Person – ignoriere also bisherige "
        "Nachrichten von Robin Hansson selbst und antworte nur auf die zuletzt "
        "an ihn gerichtete Nachricht. "
        "{tone_instruction}"
        "Behalte die Sprache des Originals bei. "
        "{extra_instruction}"
        "Gib nur die Antwort zurück, ohne Meta-Kommentar oder Erklärung.\n\n"
        "Nachricht:\n{text}"
    ),
]

DEFAULT_SUMMARIZE_PROMPT = (
    "Erstelle eine prägnante Zusammenfassung des folgenden Textes auf Deutsch. "
    "Fasse die wichtigsten Punkte verständlich zusammen. "
    "Antworte ausschließlich auf Deutsch und gib nur die Zusammenfassung zurück, "
    "ohne Vorspann oder Meta-Kommentar.\n\n{text}"
)

DEFAULT_EXPLAIN_PROMPT = (
    "Erkläre den folgenden Text verständlich auf Deutsch. "
    "Gehe davon aus, dass der Nutzer den Inhalt nicht versteht und eine klare, "
    "freundliche Erklärung benötigt. Verwende bei Bedarf einfache Beispiele. "
    "Antworte ausschließlich auf Deutsch und gib nur die Erklärung zurück, "
    "ohne Vorspann oder Meta-Kommentar.\n\n{text}"
)

DEFAULT_IMAGE_PROMPT = "{prompt}"

DEFAULT_CHAT_SYSTEM_PROMPT = (
    "Du bist ein hilfsbereiter Assistent. Antworte präzise, faktenbasiert und "
    "auf Deutsch (oder in der Sprache der Frage)."
)


class ModuleSettings(BaseModel):
    provider: str = DEFAULT_PROVIDER
    model: str = DEFAULT_MODEL
    prompt: str = ""
    languages: list[str] = Field(default_factory=lambda: list(DEFAULT_LANGUAGES))
    image_size: str = DEFAULT_IMAGE_SIZE
    image_quality: str = DEFAULT_IMAGE_QUALITY
    system_prompt: str = ""


class AppConfig(BaseModel):
    hotkey: str = DEFAULT_HOTKEY
    hotkeys: list[str] = Field(default_factory=lambda: list(DEFAULT_HOTKEYS))
    openai_default_model: str = DEFAULT_MODEL
    user_name: str = ""
    modules: dict[str, ModuleSettings] = Field(default_factory=dict)

    def active_hotkeys(self) -> list[str]:
        """Return all configured triggers, merging the legacy single-hotkey field."""
        triggers: list[str] = []
        if self.hotkeys:
            triggers.extend(self.hotkeys)
        if self.hotkey and self.hotkey not in triggers:
            triggers.append(self.hotkey)
        return triggers or list(DEFAULT_HOTKEYS)

    def get_module_settings(self, module_id: str, default_prompt: str) -> ModuleSettings:
        if module_id not in self.modules:
            self.modules[module_id] = ModuleSettings(prompt=default_prompt)
        else:
            settings = self.modules[module_id]
            if not settings.prompt:
                settings.prompt = default_prompt
        return self.modules[module_id]


def ensure_config_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def _migrate_legacy_prompts(config: AppConfig) -> bool:
    """Reset legacy hardcoded prompts so users pick up new defaults.

    Returns True if anything was changed (caller should persist).
    """
    changed = False
    reply = config.modules.get("reply")
    if reply is not None:
        normalized = (reply.prompt or "").strip()
        for legacy in _LEGACY_REPLY_PROMPTS:
            if normalized == legacy.strip():
                reply.prompt = ""
                changed = True
                break
    return changed


def load_config() -> AppConfig:
    ensure_config_dir()
    if not CONFIG_PATH.exists():
        config = AppConfig()
        save_config(config)
        return config

    data: dict[str, Any] = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    config = AppConfig.model_validate(data)
    if _migrate_legacy_prompts(config):
        save_config(config)
    return config


def save_config(config: AppConfig) -> None:
    ensure_config_dir()
    CONFIG_PATH.write_text(
        config.model_dump_json(indent=2),
        encoding="utf-8",
    )
