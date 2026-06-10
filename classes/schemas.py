from pydantic import BaseModel, EmailStr, Field


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
    group: int = Field(default=1, ge=1, le=2)


class MoveGroupRequest(BaseModel):
    group: int = Field(ge=1, le=2)


class TransferStudentRequest(BaseModel):
    target_class_id: int
    group: int = Field(default=1, ge=1, le=2)


class AddExistingStudentRequest(BaseModel):
    user_id: int
    group: int = Field(default=1, ge=1, le=2)


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

    model_config = {"from_attributes": True}


class StudentInviteResponse(BaseModel):
    user_id: int
    login: str
    email: str
    class_id: int
    group: int
    password_link_sent: bool = False
