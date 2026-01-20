from sentence_transformers import SentenceTransformer
import traceback
from app.core.config import settings

_model: SentenceTransformer | None = None


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        try:
            _model = SentenceTransformer(settings.embedding_model_name)
        except Exception:
            print(traceback.format_exc())
            raise
            
    return _model


def embed_texts(texts: list[str]) -> list[list[float]]:
    model_name = (settings.embedding_model_name or "").lower()
    if "e5" in model_name:
        return embed_passages(texts)

    model = get_model()
    vectors = model.encode(texts, normalize_embeddings=True)
    return [v.tolist() for v in vectors]


def _prefix_texts(texts: list[str], prefix: str) -> list[str]:
    p = prefix.strip() + " "
    return [p + (t or "") for t in texts]


def embed_passages(texts: list[str]) -> list[list[float]]:
    model = get_model()
    vectors = model.encode(_prefix_texts(texts, "passage:"), normalize_embeddings=True)
    return [v.tolist() for v in vectors]


def embed_queries(texts: list[str]) -> list[list[float]]:
    model = get_model()
    vectors = model.encode(_prefix_texts(texts, "query:"), normalize_embeddings=True)
    return [v.tolist() for v in vectors]