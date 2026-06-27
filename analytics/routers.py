from fastapi import APIRouter, Query

from core.config import settings
from core.models import AuditEvent
from core.permissions import min_perms
from users.models import User

router = APIRouter()


@router.get("/health")
async def health():
    return {"service": "analytics", "status": "ok"}


@router.get("/audit")
@min_perms(settings.OPERATOR_ROLE)
async def audit_events(
    current_user: User,
    user_id: int | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
):
    query = AuditEvent.all()
    if user_id is not None:
        query = query.filter(user_id=user_id)

    total = await query.count()
    items = await query.order_by("-created_at").offset((page - 1) * limit).limit(limit)

    return {
        "page": page,
        "limit": limit,
        "total": total,
        "items": [
            {
                "id": item.id,
                "user_id": item.user_id,
                "person_id": item.person_id,
                "role": item.role,
                "action": item.action,
                "status": item.status,
                "details": item.details,
                "created_at": item.created_at,
            }
            for item in items
        ],
    }
