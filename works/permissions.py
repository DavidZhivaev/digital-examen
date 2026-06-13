from fastapi import HTTPException, status

from classes.models import SchoolClass
from classes.permissions import is_homeroom_teacher, is_operator_or_above
from core.roles import ROLE_STUDENT, ROLE_TEACHER
from users.models import User
from works.models import Work, WorkParticipant


async def get_participant_users(work: Work) -> list[User]:
    participants = await WorkParticipant.filter(work_id=work.id).prefetch_related("user")
    return [p.user for p in participants]


async def get_participant_class_ids(work: Work) -> set[int]:
    users = await get_participant_users(work)
    return {u.class_id for u in users if u.class_id is not None}


async def is_work_global(work: Work) -> bool:
    class_ids = await get_participant_class_ids(work)
    return len(class_ids) > 1


async def is_homeroom_of_work(user: User, work: Work) -> bool:
    if user.role != ROLE_TEACHER:
        return False
    class_ids = await get_participant_class_ids(work)
    if not class_ids:
        return False
    classes = await SchoolClass.filter(id__in=class_ids)
    return any(is_homeroom_teacher(user, cls) for cls in classes)


async def is_work_participant(user: User, work: Work) -> bool:
    return await WorkParticipant.filter(work_id=work.id, user_id=user.id).exists()


async def can_view_work(user: User, work: Work) -> bool:
    if is_operator_or_above(user):
        return True

    if work.created_by_id == user.id:
        return True

    if await is_work_participant(user, work):
        return True

    if user.role >= ROLE_TEACHER and await is_homeroom_of_work(user, work):
        return True

    return False


async def can_manage_work(user: User, work: Work) -> bool:
    if is_operator_or_above(user):
        return True

    if work.created_by_id == user.id:
        return True

    if user.role >= ROLE_TEACHER and await is_homeroom_of_work(user, work):
        return True

    return False


async def can_view_full_seating(user: User, work: Work) -> bool:
    if user.role >= ROLE_TEACHER and await can_view_work(user, work):
        return True
    return False


async def can_download_seating(user: User, work: Work) -> bool:
    return user.role >= ROLE_TEACHER and await can_view_work(user, work)


async def ensure_can_view_work(user: User, work: Work) -> None:
    if not await can_view_work(user, work):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к этой работе",
        )


async def ensure_can_manage_work(user: User, work: Work) -> None:
    if not await can_manage_work(user, work):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для управления работой",
        )


async def ensure_teacher_single_class(actor: User, students: list[User]) -> None:
    if is_operator_or_above(actor):
        return

    if actor.role < ROLE_TEACHER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав",
        )

    class_ids = {s.class_id for s in students if s.class_id is not None}
    if len(class_ids) != 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Учитель может назначать работу только учащимся одного класса",
        )

    if any(s.class_id is None for s in students):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Все учащиеся должны быть привязаны к классу",
        )

    if any(s.role != ROLE_STUDENT for s in students):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Участниками могут быть только учащиеся",
        )


async def ensure_valid_students(students: list[User], person_ids: list[str]) -> None:
    found_ids = {s.person_id for s in students}
    missing = set(person_ids) - found_ids
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Учащиеся не найдены: {', '.join(sorted(missing))}",
        )

    if any(s.role != ROLE_STUDENT for s in students):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Участниками могут быть только учащиеся",
        )

    if any(s.class_id is None for s in students):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Все учащиеся должны быть привязаны к классу",
        )
