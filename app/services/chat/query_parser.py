from __future__ import annotations

import re
from app.core.config import settings
from app.services.llm.groq_llm import groq_chat_json

# Keep this aligned with profile_builder _KNOWN_SKILLS for now
KNOWN_SKILLS = [
    "python", "django", "fastapi", "flask",
    "java", "spring", "javascript", "typescript",
    "react", "node", "nodejs", "express",
    "sql", "postgresql", "mysql", "mongodb",
    "redis", "kafka", "docker", "kubernetes",
    "aws", "azure", "gcp",
]


def parse_skill_and_years(question: str) -> tuple[str | None, float | None]:
    q = (question or "").lower()

    skill = None
    for s in KNOWN_SKILLS:
        if re.search(rf"\b{re.escape(s)}\b", q):
            skill = s
            break

    # Try to extract something like "3 years", "2.5 yrs", "5+ years"
    years = None
    m = re.search(r"(\d+(?:\.\d+)?)\s*\+?\s*(?:years|yrs)\b", q)
    if m:
        try:
            years = float(m.group(1))
        except Exception:
            years = None

    return skill, years

async def parse_skill_and_years_llm(question: str) -> tuple[str | None, float | None]:
    system = (
        "You extract structured filters from user questions about resumes.\n"
        "Return ONLY valid JSON (no markdown, no explanation).\n"
        "JSON schema:\n"
        '{ "skill": string|null, "min_years": number|null }\n'
        "Rules:\n"
        "- skill must be lowercase if present\n"
        "- If the user does not mention a specific skill, use null\n"
        "- If the user does not mention years, use null\n"
        "- min_years should be a number like 3 or 2.5\n"
    )

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": question or ""},
    ]

    data = await groq_chat_json(messages=messages, temperature=0.0, max_tokens=120)

    skill = data.get("skill")
    if isinstance(skill, str):
        skill = skill.strip().lower()
        if not skill:
            skill = None
    else:
        skill = None

    min_years = data.get("min_years")
    try:
        min_years = float(min_years) if min_years is not None else None
    except Exception:
        min_years = None

    return skill, min_years


async def parse_skill_and_years_smart(question: str) -> tuple[str | None, float | None]:
    # If Groq not configured, use existing heuristic parser
    if not settings.groq_api_key:
        return parse_skill_and_years(question)

    try:
        return await parse_skill_and_years_llm(question)
    except Exception:
        # On 429 / network / JSON issues, fallback to heuristic
        return parse_skill_and_years(question)