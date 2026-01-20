from __future__ import annotations

import asyncio
import json
import re
from typing import Any

from groq import Groq

from app.core.config import settings


def _extract_first_json_object(text: str) -> dict[str, Any]:
    if not text:
        raise ValueError("Empty LLM response")

    # Try direct JSON first
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass

    # Fallback: find first {...} block
    m = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not m:
        raise ValueError("No JSON object found in LLM response")

    obj = json.loads(m.group(0))
    if not isinstance(obj, dict):
        raise ValueError("LLM JSON was not an object")

    return obj


def _sync_chat_completion(*, messages: list[dict[str, str]], model: str, temperature: float, max_tokens: int) -> str:
    if not settings.groq_api_key:
        raise ValueError("GROQ_API_KEY is not configured")

    client = Groq(api_key=settings.groq_api_key)
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return (resp.choices[0].message.content or "").strip()


async def groq_chat_completion(
    *,
    messages: list[dict[str, str]],
    model: str | None = None,
    temperature: float = 0.0,
    max_tokens: int = 512,
) -> str:
    chosen_model = model or settings.groq_model
    return await asyncio.to_thread(
        _sync_chat_completion,
        messages=messages,
        model=chosen_model,
        temperature=temperature,
        max_tokens=max_tokens,
    )


async def groq_chat_json(
    *,
    messages: list[dict[str, str]],
    model: str | None = None,
    temperature: float = 0.0,
    max_tokens: int = 512,
) -> dict[str, Any]:
    text = await groq_chat_completion(
        messages=messages,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return _extract_first_json_object(text)