from fastapi import APIRouter, HTTPException, status, Query

from core.permissions import min_perms
from core.config import settings
from users.models import User
from users.models import User

from subjects.models import Subject
from subjects.schemas import (
    SubjectCreate,
    SubjectUpdate,
    SubjectResponse,
    SubjectAssignUsers,
)
from subjects.services import (
    add_teachers,
    remove_teachers,
    add_admins,
    remove_admins,
)

router = APIRouter()


def subject_response(subject: Subject) -> SubjectResponse:
    return SubjectResponse(
        id=subject.id,
        name=subject.name,
        creator_id=subject.creator_id,
        teachers=[u.id for u in getattr(subject, "_prefetched_teachers", [])],
        admins=[u.id for u in getattr(subject, "_prefetched_admins", [])],
    )


@router.get("/", response_model=list[SubjectResponse])
@min_perms(1)
async def list_subjects(current_user: User):
    subjects = await Subject.all().prefetch_related("teachers", "admins")
    return [
        SubjectResponse(
            id=s.id,
            name=s.name,
            creator_id=s.creator_id,
            teachers=[t.id for t in await s.teachers.all()],
            admins=[a.id for a in await s.admins.all()],
        )
        for s in subjects
    ]


@router.post("/", response_model=SubjectResponse, status_code=status.HTTP_201_CREATED)
@min_perms(settings.OPERATOR_ROLE)
async def create_subject(body: SubjectCreate, current_user: User):
    subject = await Subject.create(
        name=body.name,
        creator_id=current_user.id,
    )

    return SubjectResponse(
        id=subject.id,
        name=subject.name,
        creator_id=subject.creator_id,
        teachers=[],
        admins=[],
    )


@router.get("/{subject_id}", response_model=SubjectResponse)
@min_perms(1)
async def get_subject(subject_id: int, current_user: User):
    subject = await Subject.get_or_none(id=subject_id).prefetch_related("teachers", "admins")

    if not subject:
        raise HTTPException(status_code=404, detail="Предмет не найден")

    return SubjectResponse(
        id=subject.id,
        name=subject.name,
        creator_id=subject.creator_id,
        teachers=[t.id for t in await subject.teachers.all()],
        admins=[a.id for a in await subject.admins.all()],
    )


@router.patch("/{subject_id}", response_model=SubjectResponse)
@min_perms(settings.OPERATOR_ROLE)
async def update_subject(subject_id: int, body: SubjectUpdate, current_user: User):
    subject = await Subject.get_or_none(id=subject_id)

    if not subject:
        raise HTTPException(status_code=404, detail="Предмет не найден")

    if body.name is not None:
        subject.name = body.name

    await subject.save()

    return await get_subject(subject_id, current_user)


@router.delete("/{subject_id}", status_code=status.HTTP_204_NO_CONTENT)
@min_perms(settings.OPERATOR_ROLE)
async def delete_subject(subject_id: int, current_user: User):
    subject = await Subject.get_or_none(id=subject_id)

    if not subject:
        raise HTTPException(status_code=404, detail="Предмет не найден")

    await subject.delete()
    return None


@router.post("/{subject_id}/teachers/add")
@min_perms(settings.OPERATOR_ROLE)
async def add_subject_teachers(
    subject_id: int,
    body: SubjectAssignUsers,
    current_user: User,
):
    subject = await Subject.get_or_none(id=subject_id)

    if not subject:
        raise HTTPException(status_code=404, detail="Предмет не найден")

    users = await User.filter(id__in=body.user_ids)

    await add_teachers(subject, users)

    return {"detail": "Учителя добавлены"}


@router.post("/{subject_id}/teachers/remove")
@min_perms(settings.OPERATOR_ROLE)
async def remove_subject_teachers(
    subject_id: int,
    body: SubjectAssignUsers,
    current_user: User,
):
    subject = await Subject.get_or_none(id=subject_id)

    if not subject:
        raise HTTPException(status_code=404, detail="Предмет не найден")

    users = await User.filter(id__in=body.user_ids)

    await remove_teachers(subject, users)

    return {"detail": "Учителя удалены"}


@router.post("/{subject_id}/admins/add")
@min_perms(settings.OPERATOR_ROLE)
async def add_subject_admins(
    subject_id: int,
    body: SubjectAssignUsers,
    current_user: User,
):
    subject = await Subject.get_or_none(id=subject_id)

    if not subject:
        raise HTTPException(status_code=404, detail="Предмет не найден")

    users = await User.filter(id__in=body.user_ids)

    await add_admins(subject, users)

    return {"detail": "Администраторы добавлены"}


@router.post("/{subject_id}/admins/remove")
@min_perms(settings.OPERATOR_ROLE)
async def remove_subject_admins(
    subject_id: int,
    body: SubjectAssignUsers,
    current_user: User,
):
    subject = await Subject.get_or_none(id=subject_id)

    if not subject:
        raise HTTPException(status_code=404, detail="Предмет не найден")

    users = await User.filter(id__in=body.user_ids)

    await remove_admins(subject, users)

    return {"detail": "Администраторы удалены"}