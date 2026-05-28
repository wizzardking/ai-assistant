from __future__ import annotations

from ai_assistant.config import DEFAULT_TRANSLATOR_PROMPT, ModuleSettings
from ai_assistant.modules.base import ModuleAction, assets_dir
from ai_assistant.providers.openai import OpenAIProvider

TARGET_LANGUAGES = {
    "de": "Deutsch",
    "en": "Englisch",
}


class TranslatorModule:
    id = "translator"
    icon = str(assets_dir() / "translate.svg")
    label = "Übersetzer"

    def actions(self) -> list[ModuleAction]:
        return [
            ModuleAction(id="de", label="Deutsch", icon=str(assets_dir() / "de.svg")),
            ModuleAction(id="en", label="Englisch", icon=str(assets_dir() / "en.svg")),
        ]

    def default_prompt(self) -> str:
        return DEFAULT_TRANSLATOR_PROMPT

    def is_interactive(self) -> bool:
        return False

    async def run(
        self,
        text: str,
        action_id: str | None,
        settings: ModuleSettings,
    ) -> str:
        if not action_id or action_id not in TARGET_LANGUAGES:
            raise ValueError("Keine gültige Zielsprache ausgewählt.")

        target_language = TARGET_LANGUAGES[action_id]
        prompt = settings.prompt.format(target_language=target_language, text=text)
        provider = OpenAIProvider()
        return await provider.complete(prompt=prompt, model=settings.model)
