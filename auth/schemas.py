from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    login: str
    password: str
    device_name: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class SetPasswordRequest(BaseModel):
    token: str
    password: str = Field(min_length=8, max_length=128)


class SessionResponse(BaseModel):
    id: int
    device_name: str | None
    user_agent: str | None
    created_at: datetime
    expires_at: datetime
    revoked_at: datetime | None
    is_active: bool = Field(alias="active")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
