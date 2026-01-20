from pydantic import BaseModel, Field


class IngestGDriveFolderRequest(BaseModel):
    gdrive_folder_url: str = Field(..., min_length=1)
    namespace: str = "default"


class IngestResponse(BaseModel):
    job_id: str
    status: str