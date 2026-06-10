from pydantic import BaseModel, EmailStr, Field


class SendEmailRequest(BaseModel):
    to: EmailStr
    subject: str = Field(min_length=1, max_length=255)
    body: str = Field(min_length=1)
    html: str | None = None


class UnreadEmailResponse(BaseModel):
    uid: str
    from_: str = Field(alias="from")
    to: str
    subject: str
    date: str
    body: str

    model_config = {"populate_by_name": True}
