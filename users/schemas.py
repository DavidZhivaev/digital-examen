from datetime import datetime
import re

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from core.config import Settings

_PASSWORD_RE = re.compile(r"^(?=.*[A-Za-z])(?=.*\d).{8,}$")


class UserBase(BaseModel):
    email: EmailStr
    login: str = Field(min_length=3, max_length=64)
    role: int = Field(default=1, ge=1)
    class_id: int | None = Field(None, alias="class")
    first_name: str = Field(min_length=1, max_length=255)
    last_name: str = Field(min_length=1, max_length=255)
    middle_name: str | None = Field(None, max_length=255)
    sex: int | None = Field(None, ge=1, le=2)
    email_accept: bool = False

    model_config = ConfigDict(populate_by_name=True)


class UserCreate(BaseModel):
    email: EmailStr
    role: int = Field(default=1, ge=1)
    class_id: int | None = Field(None, alias="class")
    class_group: int | None = None
    first_name: str = Field(min_length=1, max_length=255)
    last_name: str = Field(min_length=1, max_length=255)
    middle_name: str | None = Field(None, max_length=255)
    sex: int | None = Field(None, ge=1, le=2)
    email_accept: bool = False

    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode="after")
    def validate_student_class(self) -> "UserCreate":
        if self.role == 1:
            if not self.class_id or self.class_group is None:
                raise ValueError("Для ученика обязательно class_id и class_group")
        else:
            self.class_id = None
            self.class_group = None

        return self


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    login: str | None = Field(None, min_length=3, max_length=64)
    role: int | None = Field(None, ge=1)
    class_id: int | None = Field(None, alias="class")
    first_name: str | None = Field(None, min_length=1, max_length=255)
    last_name: str | None = Field(None, min_length=1, max_length=255)
    middle_name: str | None = Field(None, max_length=255)
    sex: int | None = Field(None, ge=1, le=2)
    email_accept: bool | None = None

    model_config = ConfigDict(populate_by_name=True)


class RoleUpdate(BaseModel):
    role: int = Field(ge=1)


class UserSelfUpdate(BaseModel):
    email: EmailStr | None = None
    password: str | None = Field(None, min_length=8, max_length=128)
    first_name: str | None = Field(None, min_length=1, max_length=255)
    last_name: str | None = Field(None, min_length=1, max_length=255)
    middle_name: str | None = Field(None, max_length=255)
    sex: int | None = Field(None, ge=1, le=2)

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str | None) -> str | None:
        if value is not None and not _PASSWORD_RE.match(value):
            raise ValueError("Пароль должен быть не короче 8 символов и содержать буквы и цифры")
        return value


class UserResponse(BaseModel):
    id: int
    person_id: str
    email: str
    login: str
    role: int
    register_at: datetime
    class_id: int | None = Field(None, alias="class")
    class_group: int | None = None
    must_set_password: bool = False
    first_name: str
    last_name: str
    middle_name: str | None
    sex: int | None
    email_accept: bool
    last_do: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class PaginatedUsersResponse(BaseModel):
    items: list[UserResponse]
    total: int
    page: int
    page_size: int
    pages: int
