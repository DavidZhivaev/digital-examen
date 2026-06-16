from fastapi import HTTPException, status

from users.models import User


def validate_admin_can_manage(actor: User, target: User) -> None:
    if target.id == actor.id:
        return
    if target.role >= actor.role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для управления этим пользователем",
        )


def validate_assignable_role(actor: User, role: int) -> None:
    if role >= actor.role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нельзя назначить роль выше своей и равную себе. Администраторов создает технический специалист первого корпуса вручную!",
        )
