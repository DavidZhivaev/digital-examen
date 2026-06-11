import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, status
from jwt.exceptions import InvalidTokenError

from auth.models import Session
from auth.password_service import (
    consume_password_token,
    revoke_user_password_tokens,
)
from auth.schemas import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    SessionResponse,
    SetPasswordRequest,
    TokenResponse,
)
from auth.session_service import (
    handle_refresh_token_mismatch,
    revoke_all_user_sessions,
    trim_user_sessions,
)
from core.config import settings
from core.permissions import min_perms
from core.rate_limit import check_login_rate_limit
from core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_token,
    verify_password,
    verify_token_hash,
)
from users.models import User

router = APIRouter()

_LOGIN_FAIL_DELAY_SECONDS = 0.5


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

    if not verify_token_hash(refresh_token, session.refresh_token_hash):
        await handle_refresh_token_mismatch(session, refresh_token)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный refresh-токен")

    return session


@router.get("/health")
async def health():
    return {"service": "auth", "status": "ok"}


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, request: Request):
    check_login_rate_limit(request)

    user = await User.get_or_none(login=body.login)
    if user is None or not verify_password(body.password, user.password_hash):
        await asyncio.sleep(_LOGIN_FAIL_DELAY_SECONDS)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный логин или пароль")

    if user.must_set_password:
        await asyncio.sleep(_LOGIN_FAIL_DELAY_SECONDS)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Необходимо установить пароль по ссылке из письма",
        )

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

    await trim_user_sessions(user.id)

    user.last_do = _utcnow()
    await user.save(update_fields=["last_do"])

    access_token = create_access_token(
        user_id=user.id,
        person_id=user.person_id,
        role=user.role,
        session_id=session.id,
    )
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest):
    try:
        payload = decode_token(body.refresh_token)
    except InvalidTokenError:
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
        session_id=session.id,
    )
    return TokenResponse(access_token=access_token, refresh_token=new_refresh)


@router.post("/set-password")
async def set_password(body: SetPasswordRequest):
    if len(body.password) < 8:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Пароль слишком короткий")

    user = await consume_password_token(body.token)
    user.password_hash = hash_password(body.password)
    user.must_set_password = False
    await user.save(update_fields=["password_hash", "must_set_password"])
    await revoke_user_password_tokens(user.id)
    await revoke_all_user_sessions(user.id)
    return {"detail": "Пароль успешно установлен"}


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(body: LogoutRequest):
    try:
        payload = decode_token(body.refresh_token)
    except InvalidTokenError:
        return None

    if payload.get("type") != "refresh":
        return None

    session = await Session.get_or_none(id=int(payload["sid"]))
    if session is None:
        return None

    if verify_token_hash(body.refresh_token, session.refresh_token_hash) and session.revoked_at is None:
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
    await revoke_all_user_sessions(current_user.id)
    return None


@router.get("/sessions/user/{user_id}", response_model=list[SessionResponse])
@min_perms(settings.OPERATOR_ROLE)
async def list_user_sessions(user_id: int, current_user: User):
    if not await User.exists(id=user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")
    sessions = await Session.filter(user_id=user_id).order_by("-created_at")
    return [_session_to_response(s) for s in sessions]


@router.delete("/sessions/user/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
@min_perms(settings.OPERATOR_ROLE)
async def revoke_user_sessions(user_id: int, current_user: User):
    if not await User.exists(id=user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")

    await revoke_all_user_sessions(user_id)
    return None
