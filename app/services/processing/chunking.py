import re


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 150) -> list[str]:
    cleaned = re.sub(r"\s+", " ", (text or "")).strip()
    if not cleaned:
        return []

    chunks: list[str] = []
    step = max(1, chunk_size - overlap)

    i = 0
    n = len(cleaned)
    while i < n:
        chunk = cleaned[i : i + chunk_size].strip()
        if chunk:
            chunks.append(chunk)
        i += step

    return chunks