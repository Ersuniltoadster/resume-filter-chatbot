from pinecone import Pinecone

from app.core.config import settings


def get_index():
    if not settings.pinecone_api_key:
        raise ValueError("PINECONE_API_KEY is not set")
    if not settings.pinecone_index_host:
        raise ValueError("PINECONE_INDEX_HOST is not set")

    pc = Pinecone(api_key=settings.pinecone_api_key)
    return pc.Index(host=settings.pinecone_index_host)