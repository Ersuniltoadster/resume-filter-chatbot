from __future__ import annotations

import re

from app.services.resume.profile_schema import Project, ResumeProfile


_KNOWN_SKILLS = [
    "python", "django", "fastapi", "flask",
    "java", "spring", "javascript", "typescript",
    "react", "node", "nodejs", "express",
    "sql", "postgresql", "mysql", "mongodb",
    "redis", "kafka", "docker", "kubernetes",
    "aws", "azure", "gcp",
]


def _first_n_words(text: str, n: int) -> str:
    words = re.split(r"\s+", (text or "").strip())
    words = [w for w in words if w]
    return " ".join(words[:n]).strip()


def _extract_total_years(text: str) -> float | None:
    t = (text or "").lower()

    # Examples: "3 years", "2.5 yrs", "5+ years"
    matches = re.findall(r"(\d+(?:\.\d+)?)\s*\+?\s*(?:years|yrs)\b", t)
    if not matches:
        return None

    nums = []
    for m in matches:
        try:
            nums.append(float(m))
        except Exception:
            pass
    return max(nums) if nums else None


def _extract_skills(text: str) -> list[str]:
    t = (text or "").lower()
    found = []
    for s in _KNOWN_SKILLS:
        if re.search(rf"\b{re.escape(s)}\b", t):
            found.append(s)
    # de-dup while preserving order
    seen = set()
    out = []
    for s in found:
        if s not in seen:
            out.append(s)
            seen.add(s)
    return out


def _extract_skill_years(text: str, skills: list[str]) -> dict[str, float]:
    # Best-effort for patterns like:
    # "Python - 3 years", "Django: 1.5 yrs"
    t = (text or "").lower()
    out: dict[str, float] = {}
    for s in skills:
        m = re.search(rf"\b{re.escape(s)}\b\s*[:\-–]\s*(\d+(?:\.\d+)?)\s*(?:years|yrs)\b", t)
        if m:
            try:
                out[s] = float(m.group(1))
            except Exception:
                pass
    return out


def _extract_companies(text: str) -> dict[str, float]:
    # Heuristic only. This does NOT reliably compute durations for all formats.
    # Captures lines like: "Company: Infosys (2 years)" OR "Infosys - 2 yrs"
    out: dict[str, float] = {}
    for line in (text or "").splitlines():
        l = line.strip()
        if not l:
            continue

        m1 = re.search(r"Company\s*[:\-]\s*([A-Za-z0-9 &.,]+).*?(\d+(?:\.\d+)?)\s*(?:years|yrs)\b", l, re.I)
        if m1:
            name = m1.group(1).strip()
            yrs = float(m1.group(2))
            out[name] = max(out.get(name, 0.0), yrs)
            continue

        m2 = re.search(r"^([A-Za-z0-9 &.,]{2,})\s*[-–]\s*(\d+(?:\.\d+)?)\s*(?:years|yrs)\b", l, re.I)
        if m2:
            name = m2.group(1).strip()
            yrs = float(m2.group(2))
            out[name] = max(out.get(name, 0.0), yrs)

    return out


def _extract_projects(text: str) -> list[Project]:
    # Minimal heuristic:
    # Look for "Projects" section and take next lines with "Project" / ":" patterns.
    lines = (text or "").splitlines()
    projects: list[Project] = []

    idx = None
    for i, ln in enumerate(lines):
        if re.search(r"\bprojects?\b", ln, re.I):
            idx = i
            break
    if idx is None:
        return projects

    chunk = lines[idx : idx + 60]  # small window after Projects heading
    for ln in chunk:
        l = ln.strip()
        if not l:
            continue

        # Example: "Project: CRM System - Built APIs..."
        m = re.match(r"^(?:project\s*[:\-]\s*)?(.{3,80}?)(?:\s*[:\-]\s*(.+))?$", l, re.I)
        if not m:
            continue

        name = (m.group(1) or "").strip()
        desc = (m.group(2) or "").strip() if m.group(2) else None

        # Avoid capturing the heading itself
        if re.fullmatch(r"projects?", name, re.I):
            continue

        projects.append(Project(domain=None, project_name=name, project_description=desc))

        if len(projects) >= 5:
            break

    return projects


def build_resume_profile(text: str) -> ResumeProfile:
    total_years = _extract_total_years(text)
    skills = _extract_skills(text)
    skill_years = _extract_skill_years(text, skills)
    companies = _extract_companies(text)
    projects = _extract_projects(text)

    summary = _first_n_words(text, 200)
    overview = _first_n_words(text, 120)

    return ResumeProfile(
        total_years_experience=total_years,
        skills=skills,
        skill_experience_years=skill_years,
        overall_summary=summary or None,
        overview_for_rag=overview or None,
        company_experience_years=companies,
        projects=projects,
    )