from datetime import datetime
from pydantic import BaseModel, ConfigDict
import uuid

class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    folder_url: str
    status: str

    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None

    error: str | None = None