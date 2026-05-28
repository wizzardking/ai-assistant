"""Persistent storage for chat conversations.

Chats are stored in ``~/.config/ai-assistant/chats.json`` as a list of
``Chat`` records. Each message carries an ISO-8601 timestamp so that the
full conversation (with timestamps) can be re-supplied to the model on
subsequent turns.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from ai_assistant.config import CONFIG_DIR, ensure_config_dir

logger = logging.getLogger(__name__)

CHATS_PATH = CONFIG_DIR / "chats.json"


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


class ChatMessage(BaseModel):
    role: str
    content: str
    timestamp: str = Field(default_factory=_now_iso)


class Chat(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    title: str = "Neuer Chat"
    model: str = ""
    system_prompt: str = ""
    created_at: str = Field(default_factory=_now_iso)
    updated_at: str = Field(default_factory=_now_iso)
    messages: list[ChatMessage] = Field(default_factory=list)

    def touch(self) -> None:
        self.updated_at = _now_iso()

    def derive_title(self) -> str:
        for msg in self.messages:
            if msg.role == "user" and msg.content.strip():
                text = msg.content.strip().splitlines()[0]
                return text[:60] + ("…" if len(text) > 60 else "")
        return "Neuer Chat"


class ChatStore:
    """Loads, persists and mutates the chat list on disk."""

    def __init__(self, path: Path = CHATS_PATH) -> None:
        self._path = path
        self._chats: list[Chat] = []
        self._load()

    @property
    def chats(self) -> list[Chat]:
        return self._chats

    def _load(self) -> None:
        if not self._path.exists():
            self._chats = []
            return
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                raw = raw.get("chats", [])
            self._chats = [Chat.model_validate(c) for c in raw]
        except Exception:
            logger.exception("Failed to load chats from %s – starting empty", self._path)
            self._chats = []

    def save(self) -> None:
        ensure_config_dir()
        data = [c.model_dump() for c in self._chats]
        self._path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def create_chat(self, model: str, system_prompt: str) -> Chat:
        chat = Chat(model=model, system_prompt=system_prompt)
        self._chats.insert(0, chat)
        self.save()
        return chat

    def delete_chat(self, chat_id: str) -> None:
        self._chats = [c for c in self._chats if c.id != chat_id]
        self.save()

    def clear(self) -> None:
        self._chats = []
        self.save()

    def get(self, chat_id: str) -> Chat | None:
        for c in self._chats:
            if c.id == chat_id:
                return c
        return None

    def move_to_top(self, chat_id: str) -> None:
        for i, c in enumerate(self._chats):
            if c.id == chat_id:
                if i != 0:
                    self._chats.insert(0, self._chats.pop(i))
                return

    def update_chat(self, chat: Chat) -> None:
        for i, c in enumerate(self._chats):
            if c.id == chat.id:
                self._chats[i] = chat
                self.save()
                return
        self._chats.insert(0, chat)
        self.save()


# --- Token estimation -------------------------------------------------------


def estimate_tokens(text: str) -> int:
    """Very rough token estimate (~4 chars per token)."""
    if not text:
        return 0
    return max(1, int(len(text) / 4))


def messages_token_estimate(messages: list[dict[str, Any]]) -> int:
    """Sum estimated tokens across a list of role/content dicts."""
    total = 0
    for msg in messages:
        content = msg.get("content", "")
        total += estimate_tokens(content) + 4  # rough per-message overhead
    return total
