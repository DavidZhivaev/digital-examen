import uuid
from datetime import datetime
from pydantic import BaseModel

class UploadFileResponse(BaseModel):
    file_id: uuid.UUID
    filename: str
    uploaded_at: datetime

    class Config:
        from_attributes = True


class WorkUploadResponse(BaseModel):
    work_id: uuid.UUID
    scans_processed: int
    status: str