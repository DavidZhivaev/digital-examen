from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import List


class ClassCreate(BaseModel):
    parallel: int = Field(ge=1, le=12)
    litera: str = Field(min_length=1, max_length=8)
    corpus: int = Field(default=1, ge=1)
    teacher_id: int | None = None


class ClassUpdate(BaseModel):
    parallel: int | None = Field(None, ge=1, le=12)
    litera: str | None = Field(None, min_length=1, max_length=8)
    corpus: int | None = Field(None, ge=1)


class AssignTeacherRequest(BaseModel):
    teacher_id: int


class StudentInviteRequest(BaseModel):
    email: EmailStr
    first_name: str = Field(min_length=1, max_length=255)
    last_name: str = Field(min_length=1, max_length=255)
    middle_name: str | None = Field(None, max_length=255)
    sex: int | None = Field(None, ge=1, le=2)
    group: int = Field(ge=1, le=2)

    @field_validator("group")
    @classmethod
    def validate_group(cls, v):
        if v not in (1, 2):
            raise ValueError("group must be 1 or 2")
        return v


class MoveGroupRequest(BaseModel):
    group: int = Field(ge=1, le=2)


class TransferStudentRequest(BaseModel):
    target_class_id: int
    group: int = Field(ge=1, le=2)


class AddExistingStudentRequest(BaseModel):
    user_id: int
    group: int = Field(ge=1, le=2)


class ClassImportRow(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    group: int = Field(ge=1, le=2)

    @field_validator("first_name", "last_name")
    @classmethod
    def not_empty(cls, v: str):
        if not v.strip():
            raise ValueError("empty value")
        return v.strip()


class ClassImportRequest(BaseModel):
    rows: List[ClassImportRow]

    @field_validator("rows")
    @classmethod
    def no_duplicates(cls, rows):
        emails = [r.email for r in rows]
        if len(emails) != len(set(emails)):
            raise ValueError("Duplicate emails in file")
        return rows


class ClassExportFilter(BaseModel):
    group: int | None = Field(None, ge=1, le=2)


class ClassResponse(BaseModel):
    id: int
    teacher_id: int | None
    parallel: int
    litera: str
    group_first: list[int]
    group_second: list[int]
    history: list[int]
    corpus: int
    display_name: str
    students_count: int = 0

    model_config = {"from_attributes": True}


class ClassStudentResponse(BaseModel):
    id: int
    person_id: str
    email: str
    login: str
    first_name: str
    last_name: str
    middle_name: str | None
    group: int | None
    must_set_password: bool = False,
    role: int


class StudentInviteResponse(BaseModel):
    user_id: int
    login: str
    email: str
    class_id: int
    group: int
    password_link_sent: bool = False


class AssignTeacherExtended(BaseModel):
    teacher_id: int
    group: int | None = None