from __future__ import annotations

from ai_assistant.config import ModuleSettings
from ai_assistant.modules.base import MenuNode, assets_dir


class SettingsModule:
    id = "settings"
    icon = str(assets_dir() / "settings.svg")
    label = "Einstellungen"
    display_mode = "window"

    def menu(self, settings: ModuleSettings) -> tuple[MenuNode, ...]:
        return ()

    def default_prompt(self) -> str:
        return ""

    def is_interactive(self) -> bool:
        return True

    async def run(
        self,
        text: str,
        path: tuple[str, ...],
        settings: ModuleSettings,
        extra_input: str = "",
    ) -> str:
        return ""
