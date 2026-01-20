from app.celery_app import celery_app
from app.workers.ingest_worker import run_ingest_job


@celery_app.task(name="app.tasks.ingest.ingest_job", bind=True, max_retries=2)
def ingest_job(self, job_id: str, namespace: str) -> None:
    try:
        run_ingest_job(job_id, namespace)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=10)
