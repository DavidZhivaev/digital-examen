import uuid

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from core.config import settings
from core.deps import get_current_user
from core.permissions import min_perms
from users.models import User
from works.models import Work
from blanks.schemas import SolutionBlanksRequest, TitleBlanksRequest, VariantBlanksRequest
from blanks.service import solution_blanks_pdf, title_blanks_pdf, variants_payload


router = APIRouter()


async def get_work_or_404(work_id: uuid.UUID) -> Work:
    work = await Work.get_or_none(id=work_id)
    if not work:
        from fastapi import HTTPException
        raise HTTPException(404, "Работа не найдена")
    return work


@router.post("/works/{work_id}/solutions")
@min_perms(settings.TEACHER_ROLE)
async def print_solution_blanks(work_id: uuid.UUID, payload: SolutionBlanksRequest, current_user: User = Depends(get_current_user)):
    work = await get_work_or_404(work_id)
    stream, meta = await solution_blanks_pdf(
        work,
        current_user,
        payload.participant_ids,
        payload.participant_codes,
        payload.copies_per_participant,
    )
    return StreamingResponse(
        stream,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=work_{work.id}_solution_blanks.pdf",
            "X-Print-Type": meta["print_type"],
        },
    )


@router.post("/works/{work_id}/titles")
@min_perms(settings.TEACHER_ROLE)
async def print_title_blanks(work_id: uuid.UUID, payload: TitleBlanksRequest, current_user: User = Depends(get_current_user)):
    work = await get_work_or_404(work_id)
    stream, meta = await title_blanks_pdf(work, current_user, payload.participant_ids, payload.participant_codes)
    return StreamingResponse(
        stream,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=work_{work.id}_title_blanks.pdf",
            "X-Print-Type": meta["print_type"],
        },
    )


@router.post("/works/{work_id}/variants/payload")
@min_perms(settings.TEACHER_ROLE)
async def print_variants_payload(work_id: uuid.UUID, payload: VariantBlanksRequest, current_user: User = Depends(get_current_user)):
    work = await get_work_or_404(work_id)
    return await variants_payload(work, current_user, payload.participant_ids, payload.participant_codes, payload.room_id)
