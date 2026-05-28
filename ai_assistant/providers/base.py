from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class AIProvider(Protocol):
    async def complete(self, prompt: str, model: str) -> str: ...
