from __future__ import annotations

from ai_assistant.config import ModuleSettings
from ai_assistant.modules.base import ModuleAction, assets_dir


class SettingsModule:
    id = "settings"
    icon = str(assets_dir() / "settings.svg")
    label = "Einstellungen"

    def actions(self) -> list[ModuleAction]:
        return []

    def default_prompt(self) -> str:
        return ""

    def is_interactive(self) -> bool:
        return True

    async def run(
        self,
        text: str,
        action_id: str | None,
        settings: ModuleSettings,
    ) -> str:
        return ""
