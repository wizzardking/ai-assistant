from __future__ import annotations

import asyncio

from openai import AsyncOpenAI

from ai_assistant.secrets import get_openai_api_key


class OpenAIProvider:
    async def complete(self, prompt: str, model: str) -> str:
        api_key = get_openai_api_key()
        if not api_key:
            raise RuntimeError("Kein OpenAI API-Key hinterlegt. Bitte in den Einstellungen konfigurieren.")

        client = AsyncOpenAI(api_key=api_key)
        response = await client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
        )
        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("Leere Antwort von OpenAI erhalten.")
        return content.strip()


def run_async(coro):
    """Run async coroutine from sync context, reusing event loop if present."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    else:
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        return future.result()
