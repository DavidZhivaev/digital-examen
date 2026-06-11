from pydantic import BaseModel, Field
from typing import List, Dict, Optional

class SeatingRequest(BaseModel):
    person_ids: List[str] = Field(..., description="Список person_id учащихся")
    room_ids: List[int] = Field(..., description="Список ID аудиторий (rooms)")
    teacher_ids: List[str] = Field(..., description="Список person_id учителей")

class ValidationResponse(BaseModel):
    can_arrange: bool
    reason: Optional[str] = None
    required_capacity: Optional[int] = None
    available_capacity: Optional[int] = None

class SeatAssignment(BaseModel):
    person_id: str
    fio: str
    student_class: str
    seat: str

class RoomSeating(BaseModel):
    room_id: int
    corpus: int
    number: int
    teachers: List[Dict[str, str]]
    students: List[SeatAssignment]

class SeatingResponse(BaseModel):
    status: str
    seating: List[RoomSeating]