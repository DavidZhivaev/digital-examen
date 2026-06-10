from fastapi import HTTPException, status

from classes.models import SchoolClass
from core.config import settings
from core.roles import ROLE_TEACHER
from users.models import User


def is_operator_or_above(user: User) -> bool:
    return user.role >= settings.OPERATOR_ROLE


def is_homeroom_teacher(user: User, school_class: SchoolClass) -> bool:
    """Классный руководитель: роль «Учитель» и прикреплён к классу как teacher."""
    return user.role == ROLE_TEACHER and school_class.teacher_id == user.id


def ensure_can_manage_class(actor: User, school_class: SchoolClass) -> None:
    if is_operator_or_above(actor):
        return
    if is_homeroom_teacher(actor, school_class):
        return
    if actor.role == ROLE_TEACHER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Вы не являетесь классным руководителем этого класса",
        )
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Недостаточно прав для этого класса",
    )


def ensure_can_invite_to_class(actor: User, school_class: SchoolClass) -> None:
    """Приглашать можно только в конкретный класс и только классному руководителю или оператору+."""
    ensure_can_manage_class(actor, school_class)


def ensure_can_manage_student(actor: User, student: User, school_class: SchoolClass | None) -> None:
    if is_operator_or_above(actor):
        return
    if school_class and is_homeroom_teacher(actor, school_class):
        return
    if actor.role == ROLE_TEACHER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для управления этим учеником",
        )
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Недостаточно прав для этого ученика",
    )
