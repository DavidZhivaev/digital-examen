from fastapi import HTTPException

from classes.models import SchoolClass, TeacherAssignment
from core.config import settings


async def is_subject_admin(user, subject) -> bool:
    return (
        user.role >= settings.OPERATOR_ROLE
        or await subject.admins.filter(id=user.id).exists()
    )


async def is_subject_teacher(user, subject) -> bool:
    return (
        await is_subject_admin(user, subject)
        or await subject.teachers.filter(id=user.id).exists()
    )


async def teacher_teaches_parallel(user, subject_id: int, parallel: int) -> bool:
    if user.role >= settings.OPERATOR_ROLE:
        return True

    return await TeacherAssignment.filter(
        teacher_id=user.id,
        subject=subject_id,
        school_class__parallel=parallel,
    ).exists()


async def get_student_parallel(user) -> int | None:
    if not user.class_id:
        return None

    school_class = await SchoolClass.get_or_none(id=user.class_id)
    return school_class.parallel if school_class else None


async def can_create_bank(user, subject, is_global: bool = True) -> bool:
    if is_global:
        return await is_subject_admin(user, subject)

    return await is_subject_teacher(user, subject)


async def can_create_task(user, subject) -> bool:
    return await is_subject_teacher(user, subject)


async def can_moderate_subject(user, subject) -> bool:
    return await is_subject_admin(user, subject)


async def can_manage_bank(user, bank) -> bool:
    subject = bank.subject

    if await is_subject_admin(user, subject):
        return True

    if bank.created_by_id == user.id:
        return True

    if not bank.is_global and await bank.access_teachers.filter(id=user.id).exists():
        return True

    return False


async def can_view_bank(user, bank) -> bool:
    subject = bank.subject

    if await can_manage_bank(user, bank):
        return True

    if not bank.is_global:
        return False

    if not bank.is_open:
        return False

    if await is_subject_teacher(user, subject):
        return True

    if user.role == settings.STUDENT_ROLE:
        return await get_student_parallel(user) == bank.parallel

    return False


async def assert_bank_access(user, bank):
    if not await can_view_bank(user, bank):
        raise HTTPException(403, "Нет доступа к банку задач")


async def assert_subject_access(user, subject):
    if not await is_subject_teacher(user, subject):
        raise HTTPException(403, "Нет доступа к предмету")
