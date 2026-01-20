import asyncio
import traceback
import uuid
from datetime import datetime

from sqlalchemy import select

from app.db.models.file import File
from app.db.models.job import Job
from app.db.session import AsyncSessionLocal
from app.services.gdrive.client import get_drive_service
from app.services.gdrive.listing import list_files_in_folder
from app.services.gdrive.parse import extract_folder_id
from app.services.processing.embeddings import embed_texts
from app.services.processing.text_extract import get_text_for_drive_file
from app.core.config import settings
from app.services.resume.profile_builder import build_resume_profile
from app.services.resume.llm_profile_builder import llm_build_resume_profile
from app.services.vectors.pinecone_client import get_index
from app.services.vectors.upsert import upsert_resume_embedding

async def _run_ingest_job(job_id: uuid.UUID, namespace: str) -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()
        if job is None:
            return

        job.status = "running"
        job.started_at = datetime.utcnow()
        job.error = None
        await session.commit()

        any_failed = False

        try:
            folder_id = extract_folder_id(job.folder_url)
            service = get_drive_service()
            files = list_files_in_folder(service, folder_id)

            for f in files:
                SHORTCUT_MIME = "application/vnd.google-apps.shortcut"
                original_meta = f
                original_file_id = original_meta.get("id")
                original_name = original_meta.get("name") or ""
                original_mime = original_meta.get("mimeType")

                file_meta = f
                mime_type = file_meta.get("mimeType")

                # Shortcut resolution must not fail the whole job.
                try:
                    if mime_type == SHORTCUT_MIME:
                        details = file_meta.get("shortcutDetails") or {}
                        target_id = details.get("targetId")
                        if not target_id:
                            raise ValueError("Drive shortcut missing targetId")

                        # fetch the actual file metadata (this is the real resume)
                        file_meta = (
                            service.files()
                            .get(fileId=target_id, fields="id,name,mimeType,size,modifiedTime")
                            .execute()
                        )
                except Exception:
                    any_failed = True

                    # Record failure on the shortcut itself (best-effort)
                    if original_file_id:
                        file_row_result = await session.execute(
                            select(File).where(
                                File.job_id == job_id,
                                File.gdrive_file_id == original_file_id,
                            )
                        )
                        file_row = file_row_result.scalar_one_or_none()

                        if file_row is None:
                            file_row = File(
                                job_id=job_id,
                                gdrive_file_id=original_file_id,
                                name=original_name,
                                mime_type=original_mime,
                                status="failed",
                                error=traceback.format_exc(),
                            )
                            session.add(file_row)
                        else:
                            file_row.status = "failed"
                            file_row.error = traceback.format_exc()

                        await session.commit()

                    continue


                gdrive_file_id = file_meta["id"]
                name = file_meta.get("name") or ""
                mime_type = file_meta.get("mimeType")

                size = int(file_meta.get("size") or 0)
                print(
                    f"PROCESSING name={name!r} mime={mime_type!r} size={size}",
                    flush=True,
                )

                file_row_result = await session.execute(
                    select(File).where(File.job_id == job_id, File.gdrive_file_id == gdrive_file_id)
                )
                file_row = file_row_result.scalar_one_or_none()

                if file_row is None:
                    file_row = File(
                        job_id=job_id,
                        gdrive_file_id=gdrive_file_id,
                        name=name,
                        mime_type=mime_type,
                        status="running",
                    )
                    session.add(file_row)
                    await session.commit()
                    await session.refresh(file_row)
                else:
                    file_row.status = "running"
                    file_row.error = None
                    await session.commit()

                try:
                    if mime_type == "application/pdf" and size > 15 * 1024 * 1024:
                        raise ValueError(f"PDF too large ({size} bytes), skipping to avoid OOM/crash")

                    text = get_text_for_drive_file(service, file_meta)

                    try:
                        if settings.groq_api_key:
                            profile = await llm_build_resume_profile(text)
                        else:
                            profile = build_resume_profile(text)
                    except Exception:
                        profile = build_resume_profile(text)

                    try:
                        if profile.overall_summary and profile.overall_summary.strip():
                            profile.overall_summary_embedding = embed_texts(
                                [profile.overall_summary.strip()]
                            )[0]
                        else:
                            profile.overall_summary_embedding = []
                    except Exception:
                        profile.overall_summary_embedding = []
                    
                    try:
                        if not (settings.pinecone_api_key and settings.pinecone_index_host):
                            raise ValueError("Pinecone is not configured (missing PINECONE_API_KEY or PINECONE_INDEX_HOST)")

                        if not (profile.overall_summary_embedding and len(profile.overall_summary_embedding) > 0):
                            raise ValueError("overall_summary_embedding is empty; cannot upsert to Pinecone")

                        index = get_index()
                        upsert_resume_embedding(
                            index=index,
                            namespace=namespace,
                            file_id=str(file_row.id),
                            file_name=name,
                            vector=profile.overall_summary_embedding,
                            job_id=str(job_id),
                        )
                    except Exception:
                        any_failed = True

                        # Vectors must be stored only in Pinecone.
                        # On Pinecone failure, do NOT store vectors in Postgres.
                        profile.overall_summary_embedding = []
                        file_row.resume_profile = profile.model_dump(
                            mode="json",
                            exclude_none=True,
                            exclude={"overall_summary_embedding"},
                        )
                        file_row.status = "failed"
                        file_row.error = "Pinecone upsert failed:\n" + traceback.format_exc()
                        await session.commit()
                        continue

                    # Pinecone upsert succeeded; clear embedding so it is never persisted to Postgres.
                    profile.overall_summary_embedding = []


                    file_row.resume_profile = profile.model_dump(
                        mode="json", 
                        exclude_none=True,
                        exclude={"overall_summary_embedding"},
                    )
                    await session.commit()

                    file_row.status = "succeeded"
                    file_row.num_chunks = 0
                    await session.commit()

                except Exception as e:
                    any_failed = True
                    await session.rollback()
                    file_row.status = "failed"
                    file_row.error = traceback.format_exc()
                    await session.commit()

            job.status = "failed" if any_failed else "succeeded"
            job.finished_at = datetime.utcnow()
            await session.commit()

        except Exception as e:
            job.status = "failed"
            job.error = str(e)
            job.finished_at = datetime.utcnow()
            await session.commit()


def run_ingest_job(job_id: str, namespace: str) -> None:
    asyncio.run(_run_ingest_job(uuid.UUID(job_id), namespace))