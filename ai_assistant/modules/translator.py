from __future__ import annotations

from ai_assistant.config import (
    ALL_LANGUAGES,
    DEFAULT_LANGUAGES,
    DEFAULT_TRANSLATOR_PROMPT,
    ModuleSettings,
    TONE_INSTRUCTIONS,
    TONES,
)
from ai_assistant.modules.base import MenuNode, assets_dir
from ai_assistant.providers.openai import OpenAIProvider


def _language_icon(code: str) -> str:
    candidate = assets_dir() / f"{code}.svg"
    if candidate.is_file():
        return str(candidate)
    return str(assets_dir() / "lang_generic.svg")


def _tone_icon(tone_id: str) -> str:
    candidate = assets_dir() / f"tone_{tone_id}.svg"
    if candidate.is_file():
        return str(candidate)
    return str(assets_dir() / "translate.svg")


def _build_tone_children() -> tuple[MenuNode, ...]:
    return tuple(
        MenuNode(id=tone_id, label=label, icon=_tone_icon(tone_id))
        for tone_id, label in TONES.items()
    )


class TranslatorModule:
    id = "translator"
    icon = str(assets_dir() / "translate.svg")
    label = "Übersetzer"
    display_mode = "clipboard"
    requires_selection = True

    def menu(self, settings: ModuleSettings) -> tuple[MenuNode, ...]:
        languages = settings.languages or list(DEFAULT_LANGUAGES)
        nodes: list[MenuNode] = []
        for code in languages:
            label = ALL_LANGUAGES.get(code, code.upper())
            nodes.append(
                MenuNode(
                    id=code,
                    label=label,
                    icon=_language_icon(code),
                    children=_build_tone_children(),
                )
            )
        return tuple(nodes)

    def default_prompt(self) -> str:
        return DEFAULT_TRANSLATOR_PROMPT

    def is_interactive(self) -> bool:
        return False

    async def run(
        self,
        text: str,
        path: tuple[str, ...],
        settings: ModuleSettings,
        extra_input: str = "",
    ) -> str:
        if len(path) < 2:
            raise ValueError("Pfad muss Sprache und Schreibstil enthalten.")

        language_code, tone_id = path[0], path[1]
        target_language = ALL_LANGUAGES.get(language_code, language_code.upper())
        tone_instruction = TONE_INSTRUCTIONS.get(tone_id, "")
        if tone_instruction:
            tone_instruction = tone_instruction + " "

        prompt_template = settings.prompt or DEFAULT_TRANSLATOR_PROMPT
        prompt = prompt_template.format(
            target_language=target_language,
            tone_instruction=tone_instruction,
            text=text,
        )

        provider = OpenAIProvider()
        return await provider.complete(prompt=prompt, model=settings.model)
