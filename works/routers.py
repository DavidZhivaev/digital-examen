from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from core.permissions import min_perms
from core.roles import ROLE_STUDENT, ROLE_TEACHER
from subjects.models import Subject
from users.models import User
from works.permissions import (
    can_download_seating,
    ensure_can_manage_work,
    ensure_can_view_work,
)
from works.schemas import (
    SeatingValidationResponse,
    WorkCreate,
    WorkListItem,
    WorkParticipantsAdd,
    WorkResponse,
    WorkSeatingResponse,
    WorkTypeListItem,
)
from works.service import WorkService
from works.work_types import has_test_part, list_work_types

router = APIRouter()


@router.get("/health")
async def health():
    return {"service": "works", "status": "ok"}


@router.get("/types", response_model=list[WorkTypeListItem])
@min_perms(ROLE_TEACHER)
async def list_work_types_endpoint():
    return [
        WorkTypeListItem(
            type_id=work_type.type_id,
            name=work_type.name,
            has_test_part=has_test_part(work_type.questions),
            questions=work_type.questions,
        )
        for work_type in list_work_types()
    ]


@router.post("/", response_model=WorkResponse, status_code=status.HTTP_201_CREATED)
@min_perms(ROLE_TEACHER)
async def create_work(body: WorkCreate, current_user: User):
    subject = await Subject.get_or_none(id=body.subject_id)

    if not subject:
        raise HTTPException(status_code=404, detail="Предмет не найден")

    work = await WorkService.create_work(
        actor=current_user,
        person_ids=body.person_ids,
        work_type_id=body.work_type_id,
        subject=subject,
        conduct_date=body.conduct_date,
        room_ids=body.room_ids,
        supervisor_person_ids=body.supervisor_person_ids,
    )
    data = await WorkService.build_work_response(work, include_participants=True)
    return WorkResponse(**data)


@router.get("/", response_model=list[WorkListItem])
@min_perms(ROLE_STUDENT)
async def list_works(current_user: User):
    works = await WorkService.list_works_for_user(current_user)
    items = []
    for work in works:
        data = await WorkService.build_work_response(work)
        items.append(WorkListItem(**data))
    return items


@router.get("/{work_id}", response_model=WorkResponse)
@min_perms(ROLE_STUDENT)
async def get_work(work_id: str, current_user: User):
    work = await WorkService.get_work_or_404(work_id)
    await ensure_can_view_work(current_user, work)
    data = await WorkService.build_work_response(work, include_participants=True)
    return WorkResponse(**data)


@router.post("/{work_id}/participants", response_model=WorkResponse)
@min_perms(ROLE_TEACHER)
async def add_participants(
    work_id: str,
    body: WorkParticipantsAdd,
    current_user: User,
):
    work = await WorkService.get_work_or_404(work_id)
    await ensure_can_manage_work(current_user, work)
    work = await WorkService.add_participants(
        work=work,
        actor=current_user,
        person_ids=body.person_ids,
    )
    data = await WorkService.build_work_response(work, include_participants=True)
    return WorkResponse(**data)


@router.get("/{work_id}/seating/validate", response_model=SeatingValidationResponse)
@min_perms(ROLE_TEACHER)
async def validate_work_seating(work_id: str, current_user: User):
    work = await WorkService.get_work_or_404(work_id)
    await ensure_can_manage_work(current_user, work)

    can_arrange, reason, req, avail, seating_required = await WorkService.validate_seating(work)
    return SeatingValidationResponse(
        can_arrange=can_arrange,
        reason=reason,
        required_capacity=req if seating_required else None,
        available_capacity=avail if seating_required else None,
        seating_required=seating_required,
    )


@router.post("/{work_id}/seating/generate", response_model=WorkSeatingResponse)
@min_perms(ROLE_TEACHER)
async def generate_work_seating(work_id: str, current_user: User):
    work = await WorkService.get_work_or_404(work_id)
    await ensure_can_manage_work(current_user, work)
    await WorkService.generate_seating(work, current_user)
    data = await WorkService.get_seating_response(work, current_user)
    return WorkSeatingResponse(**data)


@router.get("/{work_id}/seating", response_model=WorkSeatingResponse)
@min_perms(ROLE_STUDENT)
async def get_work_seating(work_id: str, current_user: User):
    work = await WorkService.get_work_or_404(work_id)
    await ensure_can_view_work(current_user, work)
    data = await WorkService.get_seating_response(work, current_user)
    return WorkSeatingResponse(**data)


@router.get("/{work_id}/seating/download")
@min_perms(ROLE_TEACHER)
async def download_work_seating(work_id: str, current_user: User):
    work = await WorkService.get_work_or_404(work_id)
    await ensure_can_view_work(current_user, work)

    if not await can_download_seating(current_user, work):
        raise HTTPException(status_code=403, detail="Нет доступа к скачиванию рассадки")

    excel_file = await WorkService.download_seating_excel(work)
    return StreamingResponse(
        excel_file,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=work_{work_id}_seating.xlsx"},
    )
