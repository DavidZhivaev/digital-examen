from fastapi import HTTPException, status

from classes.models import SchoolClass
from users.models import User
from core.config import settings


def validate_admin_can_manage(actor: User, target: User) -> None:
    if target.id == actor.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нельзя изменять собстевенную учетную запись!",
        )
    if target.role >= actor.role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для управления этим пользователем!",
        )


def validate_assignable_role(actor: User, role: int) -> None:
    if role >= actor.role and actor.role != 4 and actor.role > 2:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нельзя назначить роль выше своей или равную себе!",
        )

async def validate_teacher_perms(actor: User, target: User) -> None:
    if actor.role < settings.OPERATOR_ROLE:
        school_class = await SchoolClass.get_or_none(teacher_id=actor.id)
        if not school_class or school_class.teacher_id != actor.id or school_class.id != target.class_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Учитель может получить доступ к таким действиям только для учащихся его класса"
            )