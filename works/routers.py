import uuid
from datetime import date

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse

from core.config import settings
from core.deps import get_current_user
from core.permissions import min_perms
from users.models import User
from works.models import Work
from works.schemas import (
    TestConfigUpdate,
    WorkAnswersPrintRequest,
    WorkCreate,
    WorkRecognitionAssign,
    WorkRecognitionConfirm,
    WorkScanUploadResponse,
    WorkScoresUpdate,
    WorkSeatingRequest,
    WorkUpdate,
    WorkVariantPrintRequest,
)
from works.service import (
    answers_print_payload,
    assign_test_reviewers,
    can_view_work,
    create_work_from_payload,
    load_test_configs,
    paginate,
    recognition_batch,
    recognition_report,
    regenerate_work_seating,
    require_work_moderator,
    save_test_configs,
    seating_excel,
    test_sections_list,
    update_scores,
    update_work_from_payload,
    upload_work_scans,
    variant_print_payload,
    work_card,
    work_summary,
    confirm_recognition_item,
)


router = APIRouter()


async def get_work_or_404(work_id: uuid.UUID) -> Work:
    work = await Work.get_or_none(id=work_id)
    if not work:
        raise HTTPException(404, "Работа не найдена")
    return work


@router.get("/")
@min_perms(1)
async def list_works(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
):
    works = await Work.all().order_by("scheduled_at")
    visible = []

    for work in works:
        if await can_view_work(current_user, work):
            visible.append(await work_summary(work, current_user))

    if current_user.role == settings.STUDENT_ROLE:
        visible.sort(key=lambda item: item["scheduled_at"])
        return paginate(visible, page, limit)

    today = date.today()
    new_items = [item for item in visible if item["scheduled_at"].date() >= today]
    old_items = [item for item in visible if item["scheduled_at"].date() < today]
    my_items = [item for item in visible if item["creator_id"] == current_user.id]

    return {
        "new": paginate(new_items, page, limit),
        "old": paginate(old_items, page, limit),
        "my": paginate(my_items, page, limit),
    }


@router.post("/")
@min_perms(settings.TEACHER_ROLE)
async def create_work(payload: WorkCreate, current_user: User):
    work = await create_work_from_payload(current_user, payload)
    return await work_card(work, current_user)


@router.get("/test-configs")
@min_perms(settings.TEACHER_ROLE)
async def get_test_configs(current_user: User):
    return load_test_configs()


@router.post("/test-configs")
@min_perms(settings.OPERATOR_ROLE)
async def update_test_configs(payload: TestConfigUpdate, current_user: User):
    save_test_configs(payload.configs)
    return {"status": "ok", "configs": payload.configs}


@router.get("/test-sections")
@min_perms(settings.TEACHER_ROLE)
async def get_test_sections(current_user: User):
    return await test_sections_list(current_user)


@router.get("/{work_id}")
@min_perms(1)
async def get_work(work_id: uuid.UUID, current_user: User):
    work = await get_work_or_404(work_id)
    return await work_card(work, current_user)


@router.patch("/{work_id}")
@min_perms(settings.TEACHER_ROLE)
async def update_work(work_id: uuid.UUID, payload: WorkUpdate, current_user: User):
    work = await get_work_or_404(work_id)
    work = await update_work_from_payload(current_user, work, payload)
    return await work_card(work, current_user)


@router.get("/{work_id}/student/{student_id}")
@min_perms(settings.TEACHER_ROLE)
async def get_student_view(work_id: uuid.UUID, student_id: int, current_user: User):
    work = await get_work_or_404(work_id)
    await require_work_moderator(current_user, work)
    return await work_card(work, current_user, student_view_for=student_id)


@router.post("/{work_id}/seating/regenerate")
@min_perms(settings.TEACHER_ROLE)
async def regenerate_seating(work_id: uuid.UUID, payload: WorkSeatingRequest, current_user: User):
    work = await get_work_or_404(work_id)
    work = await regenerate_work_seating(current_user, work, payload)
    return await work_card(work, current_user)


@router.get("/{work_id}/seating/download")
@min_perms(settings.TEACHER_ROLE)
async def download_seating(
    work_id: uuid.UUID,
    sorted_view: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
):
    work = await get_work_or_404(work_id)
    await require_work_moderator(current_user, work)

    stream = await seating_excel(work, sorted_view=sorted_view)
    suffix = "sorted" if sorted_view else "rooms"
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=work_{work.id}_{suffix}.xlsx"},
    )


@router.post("/{work_id}/scores")
@min_perms(settings.TEACHER_ROLE)
async def update_work_scores(work_id: uuid.UUID, payload: WorkScoresUpdate, current_user: User):
    work = await get_work_or_404(work_id)
    await require_work_moderator(current_user, work)
    updated = await update_scores(work, payload.items)
    return {
        "status": "ok",
        "items": [
            {
                "student_id": item.student_id,
                "points": item.points,
                "percent": item.percent,
                "grade": item.grade,
            }
            for item in updated
        ],
    }


@router.post("/{work_id}/variants/print")
@min_perms(settings.TEACHER_ROLE)
async def print_variants(work_id: uuid.UUID, payload: WorkVariantPrintRequest, current_user: User):
    work = await get_work_or_404(work_id)
    await require_work_moderator(current_user, work)
    return await variant_print_payload(work, payload.student_id, payload.room_id)


@router.post("/{work_id}/variants/answers")
@min_perms(settings.TEACHER_ROLE)
async def print_answers(work_id: uuid.UUID, payload: WorkAnswersPrintRequest, current_user: User):
    work = await get_work_or_404(work_id)
    await require_work_moderator(current_user, work)
    return await answers_print_payload(work, payload.copies)


@router.post("/{work_id}/scans/upload", response_model=WorkScanUploadResponse)
@min_perms(settings.OPERATOR_ROLE)
async def upload_scans(work_id: uuid.UUID, current_user: User, file: UploadFile = File(...)):
    work = await get_work_or_404(work_id)
    return await upload_work_scans(work, file)


@router.post("/{work_id}/recognition/reviewers")
@min_perms(settings.TEACHER_ROLE)
async def assign_reviewers(work_id: uuid.UUID, payload: WorkRecognitionAssign, current_user: User):
    work = await get_work_or_404(work_id)
    user_ids = await assign_test_reviewers(work, current_user, payload.user_ids)
    return {"status": "ok", "user_ids": user_ids}


@router.get("/{work_id}/recognition/batch")
@min_perms(1)
async def get_recognition_batch(
    work_id: uuid.UUID,
    limit: int = Query(default=5, ge=1, le=20),
    current_user: User = Depends(get_current_user),
):
    work = await get_work_or_404(work_id)
    return await recognition_batch(work, current_user, limit)


@router.post("/{work_id}/recognition/{item_id}/confirm")
@min_perms(1)
async def confirm_recognition(
    work_id: uuid.UUID,
    item_id: int,
    payload: WorkRecognitionConfirm,
    current_user: User,
):
    work = await get_work_or_404(work_id)
    return await confirm_recognition_item(work, item_id, current_user, payload.text)


@router.get("/{work_id}/recognition/report")
@min_perms(settings.TEACHER_ROLE)
async def download_recognition_report(work_id: uuid.UUID, current_user: User):
    work = await get_work_or_404(work_id)
    await require_work_moderator(current_user, work)

    stream = await recognition_report(work)
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=work_{work.id}_recognition.xlsx"},
    )
