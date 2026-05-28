from __future__ import annotations

from ai_assistant.config import DEFAULT_SUMMARIZE_PROMPT, ModuleSettings
from ai_assistant.modules.base import MenuNode, assets_dir
from ai_assistant.providers.openai import OpenAIProvider


class SummarizeModule:
    id = "summarize"
    icon = str(assets_dir() / "summarize.svg")
    label = "Zusammenfassen"
    display_mode = "window"

    def menu(self, settings: ModuleSettings) -> tuple[MenuNode, ...]:
        return ()

    def default_prompt(self) -> str:
        return DEFAULT_SUMMARIZE_PROMPT

    def is_interactive(self) -> bool:
        return False

    async def run(
        self,
        text: str,
        path: tuple[str, ...],
        settings: ModuleSettings,
        extra_input: str = "",
    ) -> str:
        prompt_template = settings.prompt or DEFAULT_SUMMARIZE_PROMPT
        prompt = prompt_template.format(text=text)
        provider = OpenAIProvider()
        return await provider.complete(prompt=prompt, model=settings.model)
