from __future__ import annotations

from ai_assistant.config import DEFAULT_CHAT_SYSTEM_PROMPT, ModuleSettings
from ai_assistant.modules.base import MenuNode, assets_dir


class ChatModule:
    """Interactive module: opens a free-form chat dialog handled by the controller."""

    id = "chat"
    icon = str(assets_dir() / "chat.svg")
    label = "Chat"
    display_mode = "window"
    requires_selection = False

    def menu(self, settings: ModuleSettings) -> tuple[MenuNode, ...]:
        return ()

    def default_prompt(self) -> str:
        return DEFAULT_CHAT_SYSTEM_PROMPT

    def is_interactive(self) -> bool:
        return True

    async def run(
        self,
        text: str,
        path: tuple[str, ...],
        settings: ModuleSettings,
        extra_input: str = "",
    ) -> str:
        # The chat module is interactive; the AppController opens ChatWindow
        # instead of calling run() through the normal pipeline.
        return ""
