from datetime import datetime, timezone

from auth.models import Session
from core.config import settings
from core.security import verify_token_hash


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def trim_user_sessions(user_id: int, keep: int | None = None) -> None:
    limit = keep if keep is not None else settings.MAX_SESSIONS_PER_USER
    session_ids = (
        await Session.filter(user_id=user_id)
        .order_by("-created_at")
        .values_list("id", flat=True)
    )
    ids = list(session_ids)
    if len(ids) > limit:
        await Session.filter(id__in=ids[limit:]).delete()


async def revoke_all_user_sessions(user_id: int, *, except_session_id: int | None = None) -> None:
    now = _utcnow()
    query = Session.filter(user_id=user_id, revoked_at__isnull=True)
    if except_session_id is not None:
        query = query.exclude(id=except_session_id)
    await query.update(revoked_at=now)


async def get_active_session(session_id: int, user_id: int) -> Session | None:
    session = await Session.get_or_none(id=session_id, user_id=user_id)
    if session is None or session.revoked_at is not None:
        return None
    if session.expires_at < _utcnow():
        return None
    return session


async def handle_refresh_token_mismatch(session: Session, refresh_token: str) -> None:
    """При повторном использовании старого refresh-токена отзываем все сессии."""
    if session.revoked_at is not None:
        return
    if verify_token_hash(refresh_token, session.refresh_token_hash):
        return
    await revoke_all_user_sessions(session.user_id)
