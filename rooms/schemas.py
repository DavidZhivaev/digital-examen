from pydantic import BaseModel, ConfigDict, Field


class RoomCreate(BaseModel):
    corpus: int = Field(ge=1, le=4)
    number: int = Field(ge=1)

    rows: int = Field(ge=1, le=20)
    columns: int = Field(ge=1, le=20)

    it: bool = False


class RoomUpdate(BaseModel):
    corpus: int | None = Field(None, ge=1)
    number: int | None = Field(None, ge=1)

    rows: int | None = Field(None, ge=1)
    columns: int | None = Field(None, ge=1)

    it: bool | None = None


class RoomResponse(BaseModel):
    id: int

    corpus: int
    number: int

    rows: int
    columns: int

    it: bool

    seats_count: int

    model_config = ConfigDict(from_attributes=True)


class PaginatedRoomsResponse(BaseModel):
    items: list[RoomResponse]
    total: int
    page: int
    page_size: int
    pages: int