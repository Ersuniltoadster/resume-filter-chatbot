from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any 
from app.api.deps import get_db
from app.db.models.file import File
from app.schemas.chat_ask import (

    ChatAskRequest, 
    ChatAskResponse, 
    ChatResumeMatch,
)
from app.services.chat.query_parser import parse_skill_and_years_smart
from app.services.chat.pinecone_search import pinecone_search, pinecone_vector_search
from app.services.chat.intent_classifier import classify_resume_intent
from app.services.processing.embeddings import embed_texts

router = APIRouter()


def _looks_like_jd(text: str) -> bool:
    t = (text or "").strip().lower()
    if len(t) >= 400:
        return True
    jd_keywords = [
        "job title", "responsibilities", "requirements", "qualifications",
        "must have", "nice to have", "we are looking", "role:", "experience with"
    ]
    return any(k in t for k in jd_keywords)


@router.post("/ask", response_model=ChatAskResponse)
async def ask(payload: ChatAskRequest, db: AsyncSession = Depends(get_db)) -> ChatAskResponse:
    intent_obj = await classify_resume_intent(
        payload.question,
        last_presented_question=payload.last_presented_question,
    )
    skill, min_years = intent_obj.skill, intent_obj.min_years

    if intent_obj.intent in ("GENERAL", "OTHER"):
        return ChatAskResponse(parsed_skill=None, parsed_min_years=None, matches=[])
    
    if intent_obj.intent == "RESUME_FILTER" and _looks_like_jd(payload.question):
        jd_vec = embed_texts([(payload.question or "").strip()])[0]
        pc = pinecone_vector_search(jd_vec, namespace=payload.namespace, top_k=payload.top_k)

        matches = [
            ChatResumeMatch(
                file_id=str(m.get("file_id") or ""),
                resume_name=str(m.get("resume_name") or ""),
            )
            for m in pc
            if m.get("resume_name")
        ]

        return ChatAskResponse(parsed_skill=None, parsed_min_years=None, matches=matches)

    # 1) DB filtering using resume_profile
    result = await db.execute(
        select(File).where(
            File.status == "succeeded",
            File.resume_profile.isnot(None),
        )
    )
    files = result.scalars().all()

    db_matches: list[ChatResumeMatch] = []
    for f in files:
        profile = f.resume_profile or {}
        # If user asked only years (no skill), filter by total experience
        if skill is None and min_years is not None:
            total_years = profile.get("total_years_experience")
            if total_years is None:
                continue
            try:
                if float(total_years) < float(min_years):
                    continue
            except Exception:
                continue

        if skill:
            skills = [s.lower() for s in (profile.get("skills") or [])]
            if skill not in skills:
                continue

            if min_years is not None:
                skill_years = profile.get("skill_experience_years") or {}
                yrs = skill_years.get(skill)
                if yrs is None:
                    continue
                if float(yrs) < float(min_years):
                    continue

        db_matches.append(
            ChatResumeMatch(
                file_id=str(f.id),
                resume_name=f.name,
            )
        )

    # If DB gave results, return them
    if db_matches:
        return ChatAskResponse(
            parsed_skill=skill,
            parsed_min_years=min_years,
            matches=db_matches[: payload.top_k],
        )

    # 2) Pinecone fallback if enabled
    if payload.use_pinecone_fallback:
        query_for_search = payload.question
        if payload.last_presented_question and payload.last_presented_question.strip():
            query_for_search = (
                f"last_presented_question: {payload.last_presented_question.strip()}\n"
                f"user_message: {(payload.question or '').strip()}"
                )
        pc = pinecone_search(query_for_search, namespace=payload.namespace, top_k=payload.top_k)
        pc_matches = [
            ChatResumeMatch(
                file_id=str(m.get("file_id") or ""),
                resume_name=str(m.get("resume_name") or ""),
            )
            for m in pc
            if m.get("resume_name")
        ]
        return ChatAskResponse(
            parsed_skill=skill,
            parsed_min_years=min_years,
            matches=pc_matches,
        )

    return ChatAskResponse(parsed_skill=skill, parsed_min_years=min_years, matches=[])


















