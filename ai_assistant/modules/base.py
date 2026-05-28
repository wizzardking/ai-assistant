from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable

from ai_assistant.config import ModuleSettings


@dataclass(frozen=True)
class MenuNode:
    """A node in a module's hierarchical menu tree.

    A node is either a *container* (has children) — clicking navigates into the
    sub-menu — or a *leaf* — clicking executes the action with the current path.
    Leaf nodes may optionally request a free-form extra-input dialog before
    running (used e.g. by the reply module to capture additional instructions).
    """

    id: str
    label: str
    icon: str
    children: tuple["MenuNode", ...] = field(default_factory=tuple)
    needs_extra_input: bool = False
    extra_input_prompt: str = ""

    @property
    def is_leaf(self) -> bool:
        return not self.children


DISPLAY_CLIPBOARD = "clipboard"
DISPLAY_WINDOW = "window"
DISPLAY_IMAGE = "image"


@runtime_checkable
class Module(Protocol):
    id: str
    icon: str
    label: str
    display_mode: str  # "clipboard" | "window" | "image"
    requires_selection: bool  # if False, the module runs without selected text

    def menu(self, settings: ModuleSettings) -> tuple[MenuNode, ...]: ...

    def default_prompt(self) -> str: ...

    async def run(
        self,
        text: str,
        path: tuple[str, ...],
        settings: ModuleSettings,
        extra_input: str = "",
    ): ...  # may return str or bytes

    def is_interactive(self) -> bool: ...


def assets_dir() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "assets" / "icons"
        if candidate.is_dir():
            return candidate
    raise FileNotFoundError("assets/icons directory not found")
