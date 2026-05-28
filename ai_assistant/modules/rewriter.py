from __future__ import annotations

from ai_assistant.config import (
    DEFAULT_REWRITER_PROMPT,
    ModuleSettings,
    TONE_INSTRUCTIONS,
    TONES,
)
from ai_assistant.modules.base import MenuNode, assets_dir
from ai_assistant.providers.openai import OpenAIProvider


def _tone_icon(tone_id: str) -> str:
    candidate = assets_dir() / f"tone_{tone_id}.svg"
    if candidate.is_file():
        return str(candidate)
    return str(assets_dir() / "rewrite.svg")


class RewriterModule:
    id = "rewriter"
    icon = str(assets_dir() / "rewrite.svg")
    label = "Umschreiben"
    display_mode = "clipboard"
    requires_selection = True

    def menu(self, settings: ModuleSettings) -> tuple[MenuNode, ...]:
        nodes: list[MenuNode] = []
        for tone_id, label in TONES.items():
            # "plain" means "keep original" which is pointless for a rewrite module.
            if tone_id == "plain":
                continue
            nodes.append(MenuNode(id=tone_id, label=label, icon=_tone_icon(tone_id)))
        return tuple(nodes)

    def default_prompt(self) -> str:
        return DEFAULT_REWRITER_PROMPT

    def is_interactive(self) -> bool:
        return False

    async def run(
        self,
        text: str,
        path: tuple[str, ...],
        settings: ModuleSettings,
        extra_input: str = "",
    ) -> str:
        if not path:
            raise ValueError("Pfad muss Schreibstil enthalten.")

        tone_id = path[0]
        tone_instruction = TONE_INSTRUCTIONS.get(tone_id, "")
        if tone_instruction:
            tone_instruction = tone_instruction + " "

        prompt_template = settings.prompt or DEFAULT_REWRITER_PROMPT
        prompt = prompt_template.format(
            tone_instruction=tone_instruction,
            text=text,
        )

        provider = OpenAIProvider()
        return await provider.complete(prompt=prompt, model=settings.model)
