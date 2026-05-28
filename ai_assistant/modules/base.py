from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

from ai_assistant.config import ModuleSettings


@dataclass(frozen=True)
class ModuleAction:
    id: str
    label: str
    icon: str


@runtime_checkable
class Module(Protocol):
    id: str
    icon: str
    label: str

    def actions(self) -> list[ModuleAction]: ...

    def default_prompt(self) -> str: ...

    async def run(
        self,
        text: str,
        action_id: str | None,
        settings: ModuleSettings,
    ) -> str: ...

    def is_interactive(self) -> bool: ...


def assets_dir() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "assets" / "icons"
        if candidate.is_dir():
            return candidate
    raise FileNotFoundError("assets/icons directory not found")
