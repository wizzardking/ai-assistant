from __future__ import annotations

from ai_assistant.modules.base import Module
from ai_assistant.modules.explain import ExplainModule
from ai_assistant.modules.reply import ReplyModule
from ai_assistant.modules.rewriter import RewriterModule
from ai_assistant.modules.settings import SettingsModule
from ai_assistant.modules.summarize import SummarizeModule
from ai_assistant.modules.translator import TranslatorModule


class ModuleRegistry:
    def __init__(self) -> None:
        self._modules: dict[str, Module] = {}

    def register(self, module: Module) -> None:
        self._modules[module.id] = module

    def all(self) -> list[Module]:
        return list(self._modules.values())

    def get(self, module_id: str) -> Module | None:
        return self._modules.get(module_id)


def create_default_registry() -> ModuleRegistry:
    registry = ModuleRegistry()
    registry.register(TranslatorModule())
    registry.register(RewriterModule())
    registry.register(ReplyModule())
    registry.register(SummarizeModule())
    registry.register(ExplainModule())
    registry.register(SettingsModule())
    return registry
