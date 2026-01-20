from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.api.routes.ingest import router as ingest_router
from app.api.routes.jobs import router as jobs_router
from app.api.routes.chat import router as chat_router
app = FastAPI(title="GDrive → Pinecone Ingest API")

app.include_router(health_router, prefix="/health", tags=["health"])
app.include_router(ingest_router, prefix="/ingest", tags=["ingest"])
app.include_router(jobs_router, prefix="/jobs", tags=["jobs"])
app.include_router(chat_router, prefix="/chat", tags=["chat"])