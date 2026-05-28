from __future__ import annotations

from ai_assistant.config import DEFAULT_EXPLAIN_PROMPT, ModuleSettings
from ai_assistant.modules.base import MenuNode, assets_dir
from ai_assistant.providers.openai import OpenAIProvider


class ExplainModule:
    id = "explain"
    icon = str(assets_dir() / "explain.svg")
    label = "Erklären"
    display_mode = "window"
    requires_selection = True

    def menu(self, settings: ModuleSettings) -> tuple[MenuNode, ...]:
        return ()

    def default_prompt(self) -> str:
        return DEFAULT_EXPLAIN_PROMPT

    def is_interactive(self) -> bool:
        return False

    async def run(
        self,
        text: str,
        path: tuple[str, ...],
        settings: ModuleSettings,
        extra_input: str = "",
    ) -> str:
        prompt_template = settings.prompt or DEFAULT_EXPLAIN_PROMPT
        prompt = prompt_template.format(text=text)
        provider = OpenAIProvider()
        return await provider.complete(prompt=prompt, model=settings.model)
