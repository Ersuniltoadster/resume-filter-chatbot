from __future__ import annotations

from pydantic import BaseModel

from app.services.chat.instructions import RESUME_INTENT_CLASSIFICATION
from app.services.llm.groq_llm import groq_chat_json


class IntentResult(BaseModel):
    intent: str  # FILTER_BY_SKILL | FILTER_BY_SKILL_AND_YEARS | FILTER_BY_TOTAL_EXPERIENCE | GENERAL | OTHER
    skill: str | None = None
    min_years: float | None = None


async def classify_resume_intent(user_message: str, last_presented_question: str | None = None,) -> IntentResult:
    prompt = RESUME_INTENT_CLASSIFICATION.format(
        user_message=(user_message or "").strip(),
        last_presented_question=(last_presented_question or "").strip(),
    )

    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": (user_message or "").strip()},
    ]

    data = await groq_chat_json(messages=messages, temperature=0.0, max_tokens=200)

    if not isinstance(data, dict):
        data = {}

    if data.get("intent") not in ("RESUME_FILTER", "GENERAL","OTHER"):
        data["intent"] = "GENERAL"

    # Normalize skill to lowercase if present
    if isinstance(data, dict) and isinstance(data.get("skill"), str):
        data["skill"] = data["skill"].strip().lower() or None

    return IntentResult.model_validate(data)