import uuid

from pydantic import BaseModel


class TaskBankResponse(BaseModel):
    id: int
    subject_id: int
    parallel: int
    is_open: bool
    visibility_percent: int
    positions_count: int

class TaskBankCreate(BaseModel):
    subject_id: int
    parallel: int
    is_open: bool
    visibility_percent: int
    positions_count: int

class TaskPositionUpdate(BaseModel):
    order: int | None = None
    min_score: float | None = None
    max_score: float | None = None

class TaskCreate(BaseModel):
    position_id: int
    text: str
    solution: str | None = None
    answer: str | None = None
    image_url: str | None = None
    image_scale: float | None = None
    image_position: str | None = None

class TaskMove(BaseModel):
    new_position_id: int

class TaskResponse(BaseModel):
    id: uuid.UUID 
    position_id: int
    text: str
    solution: str | None = None
    answer: str | None = None
    image_url: str | None = None
    image_scale: float | None = None
    image_position: str | None = None
    author_id: int | None = None
    status: int | None = None

    class Config:
        from_attributes = True