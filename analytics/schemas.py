from pydantic import BaseModel


class AuditEventResponse(BaseModel):
    id: int
    user_id: int | None
    person_id: str | None
    role: int | None
    method: str
    path: str
    status: int
    action: str
    details: dict
    created_at: str
