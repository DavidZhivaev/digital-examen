from fastapi import HTTPException, status

from core.config import settings
from users.models import User


async def validate_role_change(actor: User, target: User, new_role: int) -> None:
    if target.id == actor.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя изменить собственную роль",
        )

    if 4 < new_role < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Некорректная роль",
        )

    if new_role >= actor.role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нельзя назначить роль выше или равную своей",
        )

    if target.role >= actor.role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нельзя изменить права пользователя с более высокими правами",
        )

    if target.role >= settings.ADMIN_ROLE and new_role < settings.ADMIN_ROLE:
        admin_count = await User.filter(role__gte=settings.ADMIN_ROLE).count()
        if admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Нельзя снять права у последнего администратора",
            )
