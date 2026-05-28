from __future__ import annotations

from ai_assistant.config import (
    DEFAULT_REPLY_PROMPT,
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
    return str(assets_dir() / "reply.svg")


def _build_extra_choice(tone_id: str, tone_label: str) -> tuple[MenuNode, ...]:
    return (
        MenuNode(
            id="no_extra",
            label="Ohne Zusatzinfos",
            icon=str(assets_dir() / "extra_no.svg"),
        ),
        MenuNode(
            id="with_extra",
            label="Mit Zusatzinfos",
            icon=str(assets_dir() / "extra_yes.svg"),
            needs_extra_input=True,
            extra_input_prompt=(
                f"Welche Zusatzinformationen sollen in die Antwort einfließen "
                f"(Schreibstil: {tone_label})?"
            ),
        ),
    )


class ReplyModule:
    id = "reply"
    icon = str(assets_dir() / "reply.svg")
    label = "Antwort verfassen"
    display_mode = "clipboard"

    def menu(self, settings: ModuleSettings) -> tuple[MenuNode, ...]:
        nodes: list[MenuNode] = []
        for tone_id, label in TONES.items():
            if tone_id == "plain":
                tone_label = "Neutral"
            else:
                tone_label = label
            nodes.append(
                MenuNode(
                    id=tone_id,
                    label=tone_label,
                    icon=_tone_icon(tone_id),
                    children=_build_extra_choice(tone_id, tone_label),
                )
            )
        return tuple(nodes)

    def default_prompt(self) -> str:
        return DEFAULT_REPLY_PROMPT

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
            raise ValueError("Pfad muss Schreibstil und Zusatzinfo-Auswahl enthalten.")

        tone_id = path[0]
        tone_instruction = TONE_INSTRUCTIONS.get(tone_id, "")
        if tone_id == "plain":
            tone_instruction = "Verfasse die Antwort in einem neutralen Ton."
        if tone_instruction:
            tone_instruction = tone_instruction + " "

        extra_instruction = ""
        if extra_input.strip():
            extra_instruction = (
                "Berücksichtige beim Verfassen der Antwort folgende Zusatzinformationen "
                f"des Nutzers: {extra_input.strip()}. "
            )

        prompt_template = settings.prompt or DEFAULT_REPLY_PROMPT
        prompt = prompt_template.format(
            tone_instruction=tone_instruction,
            extra_instruction=extra_instruction,
            text=text,
        )

        provider = OpenAIProvider()
        return await provider.complete(prompt=prompt, model=settings.model)
