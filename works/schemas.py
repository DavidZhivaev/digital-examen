from datetime import datetime
from typing import Any
import uuid

from pydantic import BaseModel, Field, model_validator


class GradeRule(BaseModel):
    grade: float = Field(ge=2, le=5)
    min_points: float = Field(ge=0)
    min_clean_pluses: int | None = Field(default=None, ge=0)


class WorkCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    subject_id: int
    student_ids: list[int] = Field(min_length=1)
    room_ids: list[int] = Field(min_length=1)
    scheduled_at: datetime
    observer_ids: list[int] = Field(default_factory=list)
    task_bank_id: int | None = None
    task_count: int | None = Field(default=None, ge=1)
    written_task_count: int | None = Field(default=None, ge=0)
    variant_count: int | None = Field(default=None, ge=1)
    test_config_key: str | None = None
    send_notifications: bool = False
    grading_scale: list[GradeRule] = Field(default_factory=list)


class WorkUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    student_ids: list[int] | None = None
    room_ids: list[int] | None = None
    scheduled_at: datetime | None = None
    task_count: int | None = Field(default=None, ge=1)
    written_task_count: int | None = Field(default=None, ge=0)
    test_config_key: str | None = None


class WorkSeatingRequest(BaseModel):
    student_ids: list[int] = Field(min_length=1)
    room_ids: list[int] = Field(min_length=1)


class WorkScoreItem(BaseModel):
    student_id: int | None = None
    work_number: int | None = None
    participant_code: str | None = Field(default=None, pattern=r"^\d{13}$")
    blank_code: str | None = Field(default=None, pattern=r"^\d{13}$")
    points: dict[int, float]

    @model_validator(mode="after")
    def validate_identifier(self):
        if not any([self.student_id, self.work_number, self.participant_code, self.blank_code]):
            raise ValueError("Нужно указать student_id, work_number, participant_code или blank_code")
        return self


class WorkScoresUpdate(BaseModel):
    items: list[WorkScoreItem] = Field(min_length=1)


class WorkVariantPrintRequest(BaseModel):
    student_id: int | None = None
    room_id: int | None = None
    student_ids: list[int] | None = None

    @model_validator(mode="after")
    def validate_target(self):
        selected = [bool(self.student_id), bool(self.room_id), bool(self.student_ids)]
        if sum(selected) != 1:
            raise ValueError("Нужно выбрать одного учащегося, список учащихся или одну аудиторию")
        return self


class WorkAnswersPrintRequest(BaseModel):
    copies: int = Field(ge=1, le=500)


class WorkRecognitionConfirm(BaseModel):
    text: str = Field(min_length=1, max_length=255)


class WorkRecognitionAssign(BaseModel):
    user_ids: list[int] = Field(min_length=1)


class WorkAddStudent(BaseModel):
    student_id: int
    room_id: int | None = None


class WorkRegenerateVariants(BaseModel):
    variant_count: int | None = Field(default=None, ge=1)


class WorkScanUploadResponse(BaseModel):
    work_id: uuid.UUID
    scans_processed: int
    recognition_items_created: int
    warnings: list[str]
    status: str


class TestConfigUpdate(BaseModel):
    configs: list[dict[str, dict[str, str]]]


class WorkResponse(BaseModel):
    id: uuid.UUID
    title: str
    subject_id: int
    scheduled_at: datetime
    task_count: int
    written_task_count: int
    variant_count: int | None = None
    test_config_key: str | None = None
    send_notifications: bool
    creator_id: int
    task_bank_id: int | None = None
    grading_scale: list[dict[str, Any]]
