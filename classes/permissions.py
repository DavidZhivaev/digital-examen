from fastapi import HTTPException, status

from classes.models import SchoolClass, TeacherAssignment
from core.config import settings
from core.roles import ROLE_TEACHER
from users.models import User


def is_operator_or_above(user: User) -> bool:
    return user.role >= settings.OPERATOR_ROLE


def is_homeroom_teacher(user: User, school_class: SchoolClass) -> bool:
    return user.role == ROLE_TEACHER and school_class.teacher_id == user.id


def can_manage_class(actor: User, school_class: SchoolClass) -> None:
    if is_operator_or_above(actor):
        return
    if is_homeroom_teacher(actor, school_class):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Недостаточно прав для этого класса",
    )

async def can_view_class(actor: User, school_class: SchoolClass) -> None:
    if is_operator_or_above(actor):
        return

    if school_class.teacher_id == actor.id:
        return

    exists = await TeacherAssignment.filter(
        teacher_id=actor.id,
        school_class=school_class
    ).exists()

    if exists:
        return

    raise HTTPException(403, "Нет доступа к классу")

def can_manage_student(actor: User, student: User, school_class: SchoolClass) -> None:
    if is_operator_or_above(actor):
        return
    if is_homeroom_teacher(actor, school_class):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Недостаточно прав для ученика",
    )