from __future__ import annotations

from typing import Any

from app.services.processing.embeddings import embed_texts
from app.services.vectors.pinecone_client import get_index


def pinecone_search(question: str, namespace: str, top_k: int) -> list[dict[str, Any]]:
    index = get_index()
    qvec = embed_texts([question])[0]

    res = index.query(
        vector=qvec,
        top_k=top_k,
        include_metadata=True,
        namespace=namespace,
    )

    matches = []
    for m in (res.get("matches") or []):
        md = m.get("metadata") or {}
        matches.append(
            {
                "score": float(m.get("score") or 0.0),
                "file_id": md.get("file_id"),
                "resume_name": md.get("file_name"),
                "evidence": md.get("text_preview"),
            }
        )

    return matches

def pinecone_vector_search(vector: list[float], namespace: str, top_k: int) -> list[dict[str, Any]]:
    index = get_index()
    res = index.query(
        vector=vector,
        top_k=top_k,
        include_metadata=True,
        namespace=namespace,
    )

    matches = []
    for m in (res.get("matches") or []):
        md = m.get("metadata") or {}
        matches.append(
            {
                "score": float(m.get("score") or 0.0),
                "file_id": md.get("file_id") or m.get("id"),
                "resume_name": md.get("file_name"),
            }
        )

    return matches


