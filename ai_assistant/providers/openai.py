from __future__ import annotations

import asyncio
import base64
from typing import Any

from openai import AsyncOpenAI

from ai_assistant.config import reasoning_effort_for
from ai_assistant.secrets import get_openai_api_key


def _require_client() -> AsyncOpenAI:
    api_key = get_openai_api_key()
    if not api_key:
        raise RuntimeError(
            "Kein OpenAI API-Key hinterlegt. Bitte in den Einstellungen konfigurieren."
        )
    return AsyncOpenAI(api_key=api_key)


def _chat_kwargs(model: str) -> dict[str, Any]:
    kwargs: dict[str, Any] = {"model": model}
    effort = reasoning_effort_for(model)
    if effort:
        kwargs["reasoning_effort"] = effort
    return kwargs


class OpenAIProvider:
    async def complete(self, prompt: str, model: str) -> str:
        client = _require_client()
        response = await client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            **_chat_kwargs(model),
        )
        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("Leere Antwort von OpenAI erhalten.")
        return content.strip()

    async def chat(self, messages: list[dict[str, Any]], model: str) -> str:
        """Send a message history (list of {role, content} dicts) and return the assistant reply."""
        client = _require_client()
        response = await client.chat.completions.create(
            messages=messages,
            **_chat_kwargs(model),
        )
        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("Leere Antwort von OpenAI erhalten.")
        return content.strip()

    async def generate_image(
        self,
        prompt: str,
        model: str = "gpt-image-2",
        size: str = "1024x1024",
        quality: str = "auto",
    ) -> bytes:
        client = _require_client()
        kwargs: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "size": size,
            "n": 1,
        }
        if quality:
            kwargs["quality"] = quality
        response = await client.images.generate(**kwargs)
        # OpenAI returns base64 in `b64_json` when no `response_format` URL is requested
        data = response.data[0]
        b64 = getattr(data, "b64_json", None)
        if b64:
            return base64.b64decode(b64)
        url = getattr(data, "url", None)
        if url:
            # Fallback: fetch image via httpx
            import httpx
            async with httpx.AsyncClient() as http:
                r = await http.get(url)
                r.raise_for_status()
                return r.content
        raise RuntimeError("Bild-Antwort enthielt weder Base64 noch URL.")


def run_async(coro):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    else:
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        return future.result()
