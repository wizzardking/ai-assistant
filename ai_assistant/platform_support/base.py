from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ClipboardBackend(Protocol):
    """Minimal interface required by :class:`ClipboardManager`."""

    def read_text(self) -> str: ...
    def write_text(self, text: str) -> None: ...


class NullClipboardBackend:
    """Fallback that always returns an empty clipboard – used if no backend works."""

    def read_text(self) -> str:
        return ""

    def write_text(self, text: str) -> None:  # noqa: ARG002
        return
