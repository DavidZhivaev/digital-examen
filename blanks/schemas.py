import uuid

from pydantic import BaseModel, Field


class SolutionBlanksRequest(BaseModel):
    participant_ids: list[int] | None = None
    participant_codes: list[str] | None = None
    copies_per_participant: int = Field(default=1, ge=1, le=20)


class TitleBlanksRequest(BaseModel):
    participant_ids: list[int] | None = None
    participant_codes: list[str] | None = None


class VariantBlanksRequest(BaseModel):
    participant_ids: list[int] | None = None
    participant_codes: list[str] | None = None
    room_id: int | None = None


class BlankIssueResponse(BaseModel):
    work_id: uuid.UUID
    print_type: str
    issues: list[dict]

