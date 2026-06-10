from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    email: EmailStr
    login: str
    role: int = 1
    class_id: int | None = Field(None, alias="class")
    first_name: str
    last_name: str
    middle_name: str | None = None
    sex: int | None = None
    email_accept: bool = False

    model_config = ConfigDict(populate_by_name=True)


class UserCreate(UserBase):
    password: str = Field(min_length=6)


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    login: str | None = None
    password: str | None = Field(None, min_length=6)
    role: int | None = None
    class_id: int | None = Field(None, alias="class")
    first_name: str | None = None
    last_name: str | None = None
    middle_name: str | None = None
    sex: int | None = None
    email_accept: bool | None = None

    model_config = ConfigDict(populate_by_name=True)


class UserSelfUpdate(BaseModel):
    email: EmailStr | None = None
    password: str | None = Field(None, min_length=6)
    first_name: str | None = None
    last_name: str | None = None
    middle_name: str | None = None
    sex: int | None = None


class UserResponse(BaseModel):
    id: int
    person_id: str
    email: str
    login: str
    role: int
    register_at: datetime
    class_id: int | None = Field(None, alias="class")
    first_name: str
    last_name: str
    middle_name: str | None
    sex: int | None
    email_accept: bool
    last_do: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
