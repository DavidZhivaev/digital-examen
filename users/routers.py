from datetime import datetime, timezone
import math

from fastapi import APIRouter, HTTPException, Query, status
from tortoise.exceptions import IntegrityError

from auth.password_service import build_password_link, mark_user_must_set_password
from auth.session_service import revoke_all_user_sessions
from mail.gmail_service import send_password_email
from core.config import settings
from core.permissions import min_perms
from core.security import hash_password
from users.admin_service import validate_admin_can_manage, validate_assignable_role
from users.models import User
from users.role_service import validate_role_change
from users.schemas import (
    PaginatedUsersResponse,
    RoleUpdate,
    UserCreate,
    UserResponse,
    UserSelfUpdate,
    UserUpdate,
)

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
        class_group=user.class_group,
        must_set_password=user.must_set_password,
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
    password_changed = "password" in data
    if password_changed:
        data["password_hash"] = hash_password(data.pop("password"))

    for field, value in data.items():
        setattr(current_user, field, value)

    current_user.last_do = _utcnow()
    await current_user.save()

    if password_changed:
        await revoke_all_user_sessions(current_user.id)

    return _user_to_response(current_user)


@router.get("/", response_model=PaginatedUsersResponse)
@min_perms(settings.ADMIN_ROLE)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(settings.USERS_PAGE_SIZE_DEFAULT, ge=1, le=settings.USERS_PAGE_SIZE_MAX),
):
    total = await User.all().count()
    pages = max(1, math.ceil(total / page_size)) if total else 1
    offset = (page - 1) * page_size
    users = await User.all().order_by("id").offset(offset).limit(page_size)

    return PaginatedUsersResponse(
        items=[_user_to_response(u) for u in users],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/{user_id}", response_model=UserResponse)
@min_perms(settings.ADMIN_ROLE)
async def get_user(user_id: int, current_user: User):
    user = await User.get_or_none(id=user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")

    validate_admin_can_manage(current_user, user)
    return _user_to_response(user)


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@min_perms(settings.ADMIN_ROLE)
async def create_user(body: UserCreate, current_user: User):
    validate_assignable_role(current_user, body.role)

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


@router.patch("/{user_id}/role", response_model=UserResponse)
@min_perms(settings.ADMIN_ROLE)
async def update_user_role(user_id: int, body: RoleUpdate, current_user: User):
    user = await User.get_or_none(id=user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")

    await validate_role_change(current_user, user, body.role)

    if user.role != body.role:
        user.role = body.role
        user.last_do = _utcnow()
        await user.save(update_fields=["role", "last_do"])
        await revoke_all_user_sessions(user.id)

    return _user_to_response(user)


@router.patch("/{user_id}", response_model=UserResponse)
@min_perms(settings.ADMIN_ROLE)
async def update_user(user_id: int, body: UserUpdate, current_user: User):
    user = await User.get_or_none(id=user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")

    validate_admin_can_manage(current_user, user)

    data = body.model_dump(exclude_unset=True)
    password_changed = "password" in data
    role_changed = "role" in data

    if role_changed:
        await validate_role_change(current_user, user, data["role"])

    if "role" in data:
        validate_assignable_role(current_user, data["role"])

    if password_changed:
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

    if password_changed or role_changed:
        await revoke_all_user_sessions(user.id)

    return _user_to_response(user)


@router.post("/{user_id}/force-password-reset")
@min_perms(settings.OPERATOR_ROLE)
async def force_password_reset(user_id: int, current_user: User):
    user = await User.get_or_none(id=user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")

    raw_token = await mark_user_must_set_password(user)
    await revoke_all_user_sessions(user.id)

    link = build_password_link(raw_token)
    try:
        await send_password_email(
            to=user.email,
            subject="Смена пароля — Школа 1580",
            greeting=f"Здравствуйте, {user.last_name} {user.first_name}!",
            link=link,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Не удалось отправить письмо: {exc}",
        )

    return {"detail": "Ссылка на смену пароля отправлена", "email": user.email}


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
@min_perms(settings.ADMIN_ROLE)
async def delete_user(user_id: int, current_user: User):
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя удалить собственную учётную запись",
        )

    user = await User.get_or_none(id=user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")

    validate_admin_can_manage(current_user, user)

    if user.role >= settings.ADMIN_ROLE:
        admin_count = await User.filter(role__gte=settings.ADMIN_ROLE).count()
        if admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Нельзя удалить последнего администратора",
            )

    await revoke_all_user_sessions(user.id)
    await user.delete()
    return None
