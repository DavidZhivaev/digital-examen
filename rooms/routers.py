import math

from fastapi import APIRouter, HTTPException, Query, status
from tortoise.exceptions import IntegrityError

from core.config import settings
from core.permissions import min_perms

from rooms.models import Room
from rooms.schemas import (
    PaginatedRoomsResponse,
    RoomCreate,
    RoomResponse,
    RoomUpdate,
)
from users.models import User

router = APIRouter()


def room_response(room: Room) -> RoomResponse:
    return RoomResponse(
        id=room.id,
        corpus=room.corpus,
        number=room.number,
        rows=room.rows,
        columns=room.columns,
        it=room.it,
        seats_count=room.rows * room.columns,
    )


@router.get("/health")
async def health():
    return {"service": "rooms", "status": "ok"}


@router.get("/all", response_model=PaginatedRoomsResponse)
@min_perms(3)
async def list_rooms(
    current_user: User,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
):
    total = await Room.all().count()

    pages = max(1, math.ceil(total / page_size)) if total else 1
    offset = (page - 1) * page_size

    rooms = (
        await Room.all()
        .order_by("corpus", "number", "-it")
        .offset(offset)
        .limit(page_size)
    )

    return PaginatedRoomsResponse(
        items=[room_response(room) for room in rooms],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/{room_id}", response_model=RoomResponse)
@min_perms(1)
async def get_room(current_user: User, room_id: int):
    room = await Room.get_or_none(id=room_id)

    if room is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Кабинет не найден",
        )

    return room_response(room)


@router.post(
    "/create",
    response_model=RoomResponse,
    status_code=status.HTTP_201_CREATED,
)
@min_perms(3)
async def create_room(current_user: User, body: RoomCreate):
    try:
        room = await Room.create(**body.model_dump())
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Такой кабинет уже существует",
        )

    return room_response(room)


@router.patch("/{room_id}", response_model=RoomResponse)
@min_perms(3)
async def update_room(
    current_user: User,
    room_id: int,
    body: RoomUpdate,
):
    room = await Room.get_or_none(id=room_id)

    if room is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Кабинет не найден",
        )

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(room, field, value)

    try:
        await room.save()
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Такой кабинет уже существует",
        )

    return room_response(room)


@router.delete("/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
@min_perms(3)
async def delete_room(current_user: User, room_id: int):
    room = await Room.get_or_none(id=room_id)

    if room is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Кабинет не найден",
        )

    await room.delete()

    return None