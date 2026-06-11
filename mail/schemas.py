from pydantic import BaseModel, EmailStr, Field


class SendEmailRequest(BaseModel):
    to: EmailStr
    subject: str = Field(min_length=1, max_length=255)
    message: str = Field(min_length=1)
    html: str | None = None