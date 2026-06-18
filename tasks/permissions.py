from fastapi import HTTPException

from core.config import settings


async def can_create_bank(user, subject) -> bool:
    return (
        user.role >= settings.OPERATOR_ROLE
        or await subject.admins.filter(id=user.id).exists()
    )


async def can_create_task(user, subject) -> bool:
    return (
        user.role >= settings.OPERATOR_ROLE
        or await subject.teachers.filter(id=user.id).exists()
    )


async def can_moderate_subject(user, subject) -> bool:
    return (
        user.role >= settings.OPERATOR_ROLE
        or await subject.admins.filter(id=user.id).exists()
    )


async def can_view_subject(user, subject) -> bool:
    if user.role >= settings.OPERATOR_ROLE:
        return True

    return (
        await subject.teachers.filter(id=user.id).exists()
        or await subject.admins.filter(id=user.id).exists()
    )


async def assert_subject_access(user, subject):
    if user.role >= settings.OPERATOR_ROLE:
        return

    is_teacher = await subject.teachers.filter(id=user.id).exists()
    is_admin = await subject.admins.filter(id=user.id).exists()

    if not (is_teacher or is_admin):
        raise HTTPException(403, "Нет доступа к предмету")