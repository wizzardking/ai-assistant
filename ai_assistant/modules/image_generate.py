from __future__ import annotations

from ai_assistant.config import (
    DEFAULT_IMAGE_MODEL,
    DEFAULT_IMAGE_PROMPT,
    DEFAULT_IMAGE_SIZE,
    ModuleSettings,
)
from ai_assistant.modules.base import MenuNode, assets_dir
from ai_assistant.providers.openai import OpenAIProvider


class ImageGenerateModule:
    id = "image_generate"
    icon = str(assets_dir() / "image_generate.svg")
    label = "Bild generieren"
    display_mode = "image"
    requires_selection = False

    def menu(self, settings: ModuleSettings) -> tuple[MenuNode, ...]:
        # A single leaf-node that always asks for an extra-input prompt.
        return (
            MenuNode(
                id="prompt",
                label="Bild-Anweisung eingeben",
                icon=str(assets_dir() / "image_generate.svg"),
                needs_extra_input=True,
                extra_input_prompt=(
                    "Beschreibe das gewünschte Bild (z.B. 'Ein gemütliches Café "
                    "bei Nacht im Stil eines Aquarells')."
                ),
            ),
        )

    def default_prompt(self) -> str:
        return DEFAULT_IMAGE_PROMPT

    def is_interactive(self) -> bool:
        return False

    async def run(
        self,
        text: str,
        path: tuple[str, ...],
        settings: ModuleSettings,
        extra_input: str = "",
    ) -> bytes:
        prompt = extra_input.strip()
        if not prompt:
            raise ValueError("Bitte eine Bild-Anweisung eingeben.")

        prompt_template = settings.prompt or DEFAULT_IMAGE_PROMPT
        final_prompt = prompt_template.format(prompt=prompt)
        model = settings.model or DEFAULT_IMAGE_MODEL
        size = settings.image_size or DEFAULT_IMAGE_SIZE

        provider = OpenAIProvider()
        return await provider.generate_image(prompt=final_prompt, model=model, size=size)
