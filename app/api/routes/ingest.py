from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.db.models.job import Job
from app.schemas.ingest import IngestGDriveFolderRequest, IngestResponse
from app.tasks.ingest import ingest_job

router = APIRouter()


@router.post("/gdrive-folder", response_model=IngestResponse)
async def ingest_gdrive_folder(
    payload: IngestGDriveFolderRequest,
    db: AsyncSession = Depends(get_db),
) -> IngestResponse:
    job = Job(folder_url=payload.gdrive_folder_url, status="queued")
    db.add(job)
    await db.commit()
    await db.refresh(job)

    ingest_job.apply_async(args=[str(job.id), payload.namespace], queue="ingest")

    return IngestResponse(job_id=str(job.id), status=job.status)