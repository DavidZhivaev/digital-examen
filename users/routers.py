from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from tortoise.exceptions import IntegrityError

from core.config import settings
from core.permissions import min_perms
from core.security import hash_password
from users.models import User
from users.schemas import UserCreate, UserResponse, UserSelfUpdate, UserUpdate

router = APIRouter()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _user_to_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        person_id=user.person_id,
        email=user.email,
        login=user.login,
        role=user.role,
        register_at=user.register_at,
        class_id=user.class_id,
        first_name=user.first_name,
        last_name=user.last_name,
        middle_name=user.middle_name,
        sex=user.sex,
        email_accept=user.email_accept,
        last_do=user.last_do,
    )


@router.get("/health")
async def health():
    return {"service": "users", "status": "ok"}


@router.get("/me", response_model=UserResponse)
@min_perms(1)
async def get_me(current_user: User):
    return _user_to_response(current_user)


@router.patch("/me", response_model=UserResponse)
@min_perms(1)
async def update_me(body: UserSelfUpdate, current_user: User):
    data = body.model_dump(exclude_unset=True)
    if "password" in data:
        data["password_hash"] = hash_password(data.pop("password"))

    for field, value in data.items():
        setattr(current_user, field, value)

    current_user.last_do = _utcnow()
    await current_user.save()
    return _user_to_response(current_user)


@router.get("/", response_model=list[UserResponse])
@min_perms(settings.ADMIN_ROLE)
async def list_users(current_user: User):
    users = await User.all().order_by("id")
    return [_user_to_response(u) for u in users]


@router.get("/{user_id}", response_model=UserResponse)
@min_perms(settings.ADMIN_ROLE)
async def get_user(user_id: int, current_user: User):
    user = await User.get_or_none(id=user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")
    return _user_to_response(user)


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@min_perms(settings.ADMIN_ROLE)
async def create_user(body: UserCreate, current_user: User):
    data = body.model_dump()
    password = data.pop("password")
    data["password_hash"] = hash_password(password)

    try:
        user = await User.create(**data)
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Пользователь с таким email или логином уже существует",
        )

    return _user_to_response(user)


@router.patch("/{user_id}", response_model=UserResponse)
@min_perms(settings.ADMIN_ROLE)
async def update_user(user_id: int, body: UserUpdate, current_user: User):
    user = await User.get_or_none(id=user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")

    data = body.model_dump(exclude_unset=True)
    if "password" in data:
        data["password_hash"] = hash_password(data.pop("password"))

    for field, value in data.items():
        setattr(user, field, value)

    user.last_do = _utcnow()
    try:
        await user.save()
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Пользователь с таким email или логином уже существует",
        )

    return _user_to_response(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
@min_perms(settings.ADMIN_ROLE)
async def delete_user(user_id: int, current_user: User):
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя удалить собственную учётную запись",
        )

    deleted = await User.filter(id=user_id).delete()
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")

    return None
