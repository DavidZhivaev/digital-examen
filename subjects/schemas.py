from pydantic import BaseModel, Field, ConfigDict


class SubjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class SubjectUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)


class SubjectResponse(BaseModel):
    id: int
    name: str
    creator_id: int

    teachers: list[int] = []
    admins: list[int] = []

    model_config = ConfigDict(from_attributes=True)


class SubjectAssignUsers(BaseModel):
    user_ids: list[int]