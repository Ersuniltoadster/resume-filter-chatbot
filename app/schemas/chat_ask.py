from __future__ import annotations

from pydantic import BaseModel, Field


class ChatAskRequest(BaseModel):
    question: str = Field(..., min_length=1)
    last_presented_question: str | None = None
    namespace: str = "default-384"
    top_k: int = 5
    use_pinecone_fallback: bool = False


class ChatResumeMatch(BaseModel):
    file_id: str
    resume_name: str


class ChatAskResponse(BaseModel):
    parsed_skill: str | None = None
    parsed_min_years: float | None = None
    matches: list[ChatResumeMatch]

class JdSearchRequest(BaseModel):
    jd_text: str = Field(..., min_length = 1) 
    namespace: str = "default-384"
    top_k: int = 5

class JdSearchMatch(BaseModel):
    file_id: str 
    resume_name: str 
    score: float 

class JdSearchResponse(BaseModel):
    matches: list[JdSearchMatch]


