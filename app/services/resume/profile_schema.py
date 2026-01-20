from __future__ import annotations

from pydantic import BaseModel, Field


class Project(BaseModel):
    domain: str | None = None
    project_name: str
    project_description: str | None = None


class ResumeProfile(BaseModel):
    total_years_experience: float | None = None

    skills: list[str] = Field(default_factory=list)
    skill_experience_years: dict[str, float] = Field(default_factory=dict)

    overall_summary: str | None = None
    overall_summary_embedding: list[float] = Field(default_factory=list)
    overview_for_rag: str | None = None

    company_experience_years: dict[str, float] = Field(default_factory=dict)

    projects: list[Project] = Field(default_factory=list)