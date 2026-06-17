from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class WorkTypeListItem(BaseModel):
    type_id: str
    name: str
    has_test_part: bool
    questions: dict[str, str | None]


class WorkCreate(BaseModel):
    person_ids: list[str] = Field(..., min_length=1, description="person_id учащихся")
    work_type_id: str = Field(..., description="ID типа работы из конфига")
    subject_id: id = Field(..., description="Айди предмета")
    conduct_date: date
    room_ids: list[int] = Field(
        default_factory=list,
        description="Аудитории; если указаны — требуется рассадка",
    )
    supervisor_person_ids: list[str] = Field(
        default_factory=list,
        description="person_id учителей для надзора в аудиториях",
    )


class WorkParticipantsAdd(BaseModel):
    person_ids: list[str] = Field(..., min_length=1)


class WorkSupervisorsUpdate(BaseModel):
    supervisor_person_ids: list[str] = Field(..., min_length=1)


class ParticipantBrief(BaseModel):
    person_id: str
    first_name: str
    last_name: str
    middle_name: str | None
    class_id: int | None


class WorkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    work_id: str
    work_type_id: str
    work_type_name: str
    subject: str
    conduct_date: date
    has_test_part: bool
    questions: dict[str, str | None]
    is_global: bool
    seating_required: bool
    seating_generated: bool
    participant_count: int
    class_ids: list[int]
    room_ids: list[int]
    supervisor_person_ids: list[str]
    created_by_person_id: str
    created_at: Any
    participants: list[ParticipantBrief] | None = None


class WorkListItem(BaseModel):
    work_id: str
    work_type_id: str
    work_type_name: str
    subject: str
    conduct_date: date
    has_test_part: bool
    is_global: bool
    seating_required: bool
    seating_generated: bool
    participant_count: int
    class_ids: list[int]
    created_by_person_id: str
    created_at: Any


class SeatingValidationResponse(BaseModel):
    can_arrange: bool
    reason: str | None = None
    required_capacity: int | None = None
    available_capacity: int | None = None
    seating_required: bool


class SeatAssignmentResponse(BaseModel):
    person_id: str
    fio: str
    student_class: str
    seat: str
    room_id: int
    corpus: int
    number: int


class RoomSeatingResponse(BaseModel):
    room_id: int
    corpus: int
    number: int
    teachers: list[dict[str, str]]
    students: list[SeatAssignmentResponse]


class WorkSeatingResponse(BaseModel):
    work_id: str
    seating_required: bool
    generated: bool
    seating: list[RoomSeatingResponse] | None = None
    my_seat: SeatAssignmentResponse | None = None
