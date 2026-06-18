import uuid
from datetime import datetime
from pydantic import BaseModel

class UploadFileResponse(BaseModel):
    file_id: uuid.UUID
    filename: str
    uploaded_at: datetime

    class Config:
        from_attributes = True