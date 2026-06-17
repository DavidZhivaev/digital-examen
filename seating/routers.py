from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from core.permissions import min_perms
from seating.schemas import SeatingRequest, ValidationResponse, SeatingResponse
from seating.services import SeatingService
from users.models import User

router = APIRouter()

@router.post("/validate", response_model=ValidationResponse, summary="Предварительная проверка возможности рассадки")
@min_perms(2)
async def validate_seating(current_user: User, payload: SeatingRequest):
    data = await SeatingService.prepare_data(payload.person_ids, payload.room_ids, payload.teacher_ids)
    can_arrange, reason, req, avail = await SeatingService.validate_seating(data)
    return ValidationResponse(
        can_arrange=can_arrange,
        reason=reason,
        required_capacity=req,
        available_capacity=avail
    )

@router.post("/generate/json", response_model=SeatingResponse, summary="Генерация рассадки в формате JSON (Python)")
@min_perms(2)
async def generate_seating_json(current_user: User, payload: SeatingRequest):
    data = await SeatingService.prepare_data(payload.person_ids, payload.room_ids, payload.teacher_ids)
    can_arrange, reason, _, _ = await SeatingService.validate_seating(data)
    if not can_arrange:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=reason)
        
    plan = SeatingService.generate_seating_plan(data)
    return SeatingResponse(status="success", seating=plan)

@router.post("/generate/excel", summary="Генерация и выгрузка Excel-файла с рассадкой")
@min_perms(2)
async def generate_seating_excel(current_user: User, payload: SeatingRequest):
    data = await SeatingService.prepare_data(payload.person_ids, payload.room_ids, payload.teacher_ids)
    can_arrange, reason, _, _ = await SeatingService.validate_seating(data)
    if not can_arrange:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=reason)
        
    plan = SeatingService.generate_seating_plan(data)
    excel_file = SeatingService.generate_excel(plan)
    
    return StreamingResponse(
        excel_file,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=seating_plan.xlsx"}
    )