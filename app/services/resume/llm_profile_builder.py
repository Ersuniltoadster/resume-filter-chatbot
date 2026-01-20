from __future__ import annotations

from app.core.config import settings
from app.services.llm.groq_llm import groq_chat_json
from app.services.resume.profile_schema import ResumeProfile


async def llm_build_resume_profile(text: str) -> ResumeProfile:
    t = (text or "").strip()

    # Keep prompts within a reasonable size
    t = t[:12000]

    system = (
        "You are an expert resume parser.\n"
        "Return ONLY valid JSON (no markdown, no explanation, no extra text).\n"
        "The JSON MUST match this schema:\n"
        "{\n"
        '  "total_years_experience": number|null,\n'
        '  "skills": string[],\n'
        '  "skill_experience_years": { [skill: string]: number },\n'
        '  "overall_summary": string|null,\n'
        '  "company_experience_years": { [company: string]: number },\n'
        '  "projects": [ { "domain": string|null, "project_name": string, "project_description": string|null } ]\n'
        "}\n"
        "Rules:\n"
        "- skills must be lowercase\n"
        "- If unknown, use null or empty list/dict\n"
        "- Years must be numbers (example 2.5)\n"
        "- overall_summary must be an overall summary of the ENTIRE resume (not only the Summary section).\n"
        "- overall_summary must be between 190 and 200 words.\n"
        "- Do not use bullet points in overall_summary; write as a paragraph.\n"
        "- For skill_experience_years and company_experience_years: NEVER use null values. If unknown, omit the key or use an empty object {}.\n"
    )

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": f"Resume text:\n\n{t}"},
    ]

    if not settings.groq_api_key:
        raise ValueError("GROQ_API_KEY is not configured")

    data = await groq_chat_json(messages=messages, temperature=0.0, max_tokens=1200)

    def _clean_float_map(x):
        if not isinstance(x, dict):
            return {}
        out: dict[str, float] = {}
        for k, v in x.items():
            if v is None:
                continue
            try:
                out[str(k)] = float(v)
            except Exception:
                continue
        return out

    data["skill_experience_years"] = _clean_float_map(data.get("skill_experience_years"))
    data["company_experience_years"] = _clean_float_map(data.get("company_experience_years"))

    profile = ResumeProfile.model_validate(data)

    def _wc(s: str | None) -> int:
        return len((s or "").split())

    # Retry expansion once if too short
    if profile.overall_summary and _wc(profile.overall_summary) < 190:
        expand_system = (
            "Return ONLY valid JSON.\n"
            'Schema: { "overall_summary": string }\n'
            "Rules:\n"
            "- overall_summary must be between 190 and 200 words\n"
            "- single paragraph, no bullet points\n"
            "- must summarize the ENTIRE resume\n"
        )

        expand_user = (
            "Expand the summary to meet the 190-200 word requirement using the resume text.\n\n"
            f"RESUME TEXT:\n{t}\n\n"
            f"CURRENT SUMMARY:\n{profile.overall_summary}\n"
        )

        expand_data = await groq_chat_json(
            messages=[
                {"role": "system", "content": expand_system},
                {"role": "user", "content": expand_user},
            ],
            temperature=0.0,
            max_tokens=800,
        )

        new_summary = expand_data.get("overall_summary")
        if isinstance(new_summary, str) and new_summary.strip():
            profile.overall_summary = new_summary.strip()

    # Hard cap to 200 words
    if profile.overall_summary:
        words = profile.overall_summary.split()
        if len(words) > 200:
            profile.overall_summary = " ".join(words[:200])

    return profile
