from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, status

from auth.models import Session
from auth.schemas import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    SessionResponse,
    TokenResponse,
)
from core.config import settings
from core.permissions import min_perms
from core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_token,
    verify_password,
)
from users.models import User

router = APIRouter()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _session_to_response(session: Session) -> SessionResponse:
    return SessionResponse(
        id=session.id,
        device_name=session.device_name,
        user_agent=session.user_agent,
        created_at=session.created_at,
        expires_at=session.expires_at,
        revoked_at=session.revoked_at,
        active=session.is_active,
    )


async def _get_valid_session(session_id: int, refresh_token: str) -> Session:
    session = await Session.get_or_none(id=session_id).prefetch_related("user")
    if session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Сессия не найдена")

    if session.revoked_at is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Сессия отозвана")

    if session.expires_at < _utcnow():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Сессия истекла")

    if session.refresh_token_hash != hash_token(refresh_token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный refresh-токен")

    return session


@router.get("/health")
async def health():
    return {"service": "auth", "status": "ok"}


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, request: Request):
    user = await User.get_or_none(login=body.login)
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный логин или пароль")

    session = await Session.create(
        user=user,
        refresh_token_hash="",
        device_name=body.device_name,
        user_agent=request.headers.get("user-agent"),
        expires_at=_utcnow(),
    )

    refresh_token, expires_at = create_refresh_token(user_id=user.id, session_id=session.id)
    session.refresh_token_hash = hash_token(refresh_token)
    session.expires_at = expires_at
    await session.save()

    user.last_do = _utcnow()
    await user.save(update_fields=["last_do"])

    access_token = create_access_token(
        user_id=user.id,
        person_id=user.person_id,
        role=user.role,
    )
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest):
    try:
        payload = decode_token(body.refresh_token)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Недействительный токен")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Недействительный тип токена")

    session = await _get_valid_session(int(payload["sid"]), body.refresh_token)
    user = session.user

    new_refresh, expires_at = create_refresh_token(user_id=user.id, session_id=session.id)
    session.refresh_token_hash = hash_token(new_refresh)
    session.expires_at = expires_at
    await session.save()

    user.last_do = _utcnow()
    await user.save(update_fields=["last_do"])

    access_token = create_access_token(
        user_id=user.id,
        person_id=user.person_id,
        role=user.role,
    )
    return TokenResponse(access_token=access_token, refresh_token=new_refresh)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(body: LogoutRequest):
    try:
        payload = decode_token(body.refresh_token)
    except Exception:
        return None

    if payload.get("type") != "refresh":
        return None

    session = await Session.get_or_none(id=int(payload["sid"]))
    if session is None:
        return None

    if session.refresh_token_hash == hash_token(body.refresh_token) and session.revoked_at is None:
        session.revoked_at = _utcnow()
        await session.save(update_fields=["revoked_at"])

    return None


@router.get("/sessions", response_model=list[SessionResponse])
@min_perms(1)
async def list_sessions(current_user: User):
    sessions = await Session.filter(user_id=current_user.id).order_by("-created_at")
    return [_session_to_response(s) for s in sessions]


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
@min_perms(1)
async def revoke_session(session_id: int, current_user: User):
    session = await Session.get_or_none(id=session_id, user_id=current_user.id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Сессия не найдена")

    if session.revoked_at is None:
        session.revoked_at = _utcnow()
        await session.save(update_fields=["revoked_at"])

    return None


@router.post("/logout-all", status_code=status.HTTP_204_NO_CONTENT)
@min_perms(1)
async def logout_all(current_user: User):
    now = _utcnow()
    await Session.filter(user_id=current_user.id, revoked_at__isnull=True).update(revoked_at=now)
    return None


@router.delete("/sessions/user/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
@min_perms(settings.ADMIN_ROLE)
async def revoke_user_sessions(user_id: int, current_user: User):
    if not await User.exists(id=user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")

    now = _utcnow()
    await Session.filter(user_id=user_id, revoked_at__isnull=True).update(revoked_at=now)
    return None
