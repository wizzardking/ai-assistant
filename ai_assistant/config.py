from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

CONFIG_DIR = Path.home() / ".config" / "ai-assistant"
CONFIG_PATH = CONFIG_DIR / "config.json"

DEFAULT_HOTKEY = "<ctrl>+<shift>+<space>"
AVAILABLE_MODELS = ["gpt-5.5", "gpt-5.4-nano"]
DEFAULT_MODEL = "gpt-5.5"
DEFAULT_PROVIDER = "openai"

DEFAULT_TRANSLATOR_PROMPT = (
    "Übersetze den folgenden Text ins {target_language}. "
    "Gib nur die Übersetzung zurück, ohne Erklärung.\n\n{text}"
)


class ModuleSettings(BaseModel):
    provider: str = DEFAULT_PROVIDER
    model: str = DEFAULT_MODEL
    prompt: str = DEFAULT_TRANSLATOR_PROMPT


class AppConfig(BaseModel):
    hotkey: str = DEFAULT_HOTKEY
    openai_default_model: str = DEFAULT_MODEL
    modules: dict[str, ModuleSettings] = Field(default_factory=dict)

    def get_module_settings(self, module_id: str, default_prompt: str) -> ModuleSettings:
        if module_id not in self.modules:
            self.modules[module_id] = ModuleSettings(prompt=default_prompt)
        return self.modules[module_id]


def ensure_config_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> AppConfig:
    ensure_config_dir()
    if not CONFIG_PATH.exists():
        config = AppConfig()
        save_config(config)
        return config

    data: dict[str, Any] = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return AppConfig.model_validate(data)


def save_config(config: AppConfig) -> None:
    ensure_config_dir()
    CONFIG_PATH.write_text(
        config.model_dump_json(indent=2),
        encoding="utf-8",
    )
