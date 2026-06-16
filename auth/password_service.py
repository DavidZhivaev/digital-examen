import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status

from auth.models import PasswordToken
from core.config import settings
from core.security import hash_password, hash_token
from users.models import User

UNUSABLE_PASSWORD_HASH = hash_password(secrets.token_urlsafe(32))


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def create_password_token(user: User, purpose: str) -> str:
    raw_token = secrets.token_urlsafe(48)
    expires_at = utcnow() + timedelta(hours=settings.PASSWORD_TOKEN_EXPIRE_HOURS)
    await PasswordToken.create(
        user=user,
        token_hash=hash_token(raw_token),
        purpose=purpose,
        expires_at=expires_at,
    )
    return raw_token


def build_password_link(raw_token: str) -> str:
    base = settings.FRONTEND_URL.rstrip("/")
    return f"{base}/set-password?token={raw_token}"


async def consume_password_token(raw_token: str, *, expected_purpose: str | None = None) -> User:
    token_hash = hash_token(raw_token)
    record = await PasswordToken.get_or_none(token_hash=token_hash).prefetch_related("user")
    if record is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Недействительная ссылка")

    if record.is_used:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ссылка уже использована")

    if record.expires_at < utcnow():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ссылка истекла")

    if expected_purpose is not None and record.purpose != expected_purpose:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Недействительная ссылка")

    record.used_at = utcnow()
    await record.save(update_fields=["used_at"])
    return record.user


async def mark_user_must_set_password(user: User) -> str:
    user.must_set_password = True
    user.password_hash = UNUSABLE_PASSWORD_HASH
    await user.save(update_fields=["must_set_password", "password_hash"])
    return await create_password_token(user, purpose="reset")

async def revoke_user_password_tokens(user_id: int):
    await PasswordToken.filter(
        user_id=user_id,
        used_at__isnull=True,
    ).update(
        used_at=utcnow()
    )