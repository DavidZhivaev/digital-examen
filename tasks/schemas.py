import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TaskBankCreate(BaseModel):
    title: str = Field(default="Банк задач", min_length=1, max_length=255)
    subject_id: int
    parallel: int = Field(ge=1, le=11)
    is_global: bool = True
    is_open: bool = True
    visibility_percent: int = Field(default=100, ge=0, le=100)
    positions_count: int = Field(ge=1)


class TaskBankUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    subject_id: int | None = None
    parallel: int | None = Field(default=None, ge=1, le=11)
    is_global: bool | None = None
    is_open: bool | None = None
    visibility_percent: int | None = Field(default=None, ge=0, le=100)
    positions_count: int | None = Field(default=None, ge=1)


class TaskBankTeacherAccess(BaseModel):
    teacher_ids: list[int] = Field(default_factory=list)


class TaskBankResponse(BaseModel):
    id: int
    title: str
    subject_id: int
    subject_name: str | None = None
    parallel: int
    is_global: bool
    is_open: bool
    visibility_percent: int
    positions_count: int
    available_tasks_count: int = 0
    created_by_id: int | None = None

    model_config = ConfigDict(from_attributes=True)


class TaskPositionUpdate(BaseModel):
    order: int | None = Field(default=None, ge=1)
    min_score: float | None = Field(default=None, ge=0)
    max_score: float | None = Field(default=None, ge=0, le=12)
    criteria_text: str | None = None
    scoring: list[dict[str, Any]] | None = None


class TaskCreate(BaseModel):
    position_id: int
    text: str = Field(min_length=1)
    solution: str | None = None
    answer: str | None = None
    image_url: str | None = None
    image_scale: float | None = None
    image_position: str | None = None


class TaskUpdate(BaseModel):
    position_id: int | None = None
    text: str | None = Field(default=None, min_length=1)
    solution: str | None = None
    answer: str | None = None
    image_url: str | None = None
    image_scale: float | None = None
    image_position: str | None = None


class TaskMove(BaseModel):
    new_position_id: int


class TaskResponse(BaseModel):
    id: uuid.UUID
    code: str
    position_id: int
    position_order: int | None = None
    text: str
    solution: str | None = None
    answer: str | None = None
    image_url: str | None = None
    image_scale: float | None = None
    image_position: str | None = None
    author_id: int | None = None
    status: int | None = None
    version: int | None = None
    latest_review_comment: str | None = None

    model_config = ConfigDict(from_attributes=True)


class TaskReviewCreate(BaseModel):
    comment: str = Field(min_length=1)
