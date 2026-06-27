from datetime import datetime, timezone
from pathlib import Path
import os
import shutil
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile

from core.config import settings
from core.deps import get_current_user
from core.permissions import min_perms
from subjects.models import Subject
from tasks.audit import log_audit
from tasks.models import Task, TaskBank, TaskPosition, TaskReview, TaskRevision
from tasks.permissions import (
    assert_bank_access,
    assert_subject_access,
    can_create_bank,
    can_create_task,
    can_manage_bank,
    can_moderate_subject,
    can_view_bank,
)
from tasks.schemas import (
    TaskBankCreate,
    TaskBankTeacherAccess,
    TaskBankUpdate,
    TaskCreate,
    TaskMove,
    TaskPositionUpdate,
    TaskReviewCreate,
    TaskUpdate,
)
from tasks.service import (
    TASK_STATUS_APPROVED,
    TASK_STATUS_PENDING,
    TASK_STATUS_REJECTED,
    TaskBankService,
    TaskVisibilityService,
    convert_docx_to_math_text,
    convert_pdf_to_math_text,
    create_review,
    create_revision,
    generate_unique_task_code,
    is_public_task,
    paginate,
    reorder_positions,
    validate_latex_content,
)
from users.models import User


router = APIRouter()


async def get_bank_or_404(bank_id: int) -> TaskBank:
    bank = await TaskBank.get_or_none(id=bank_id).prefetch_related("subject", "access_teachers")
    if not bank:
        raise HTTPException(404, "Банк задач не найден")
    return bank


async def get_task_or_404(task_id: uuid.UUID) -> Task:
    task = await Task.get_or_none(id=task_id).prefetch_related("position__bank__subject")
    if not task:
        raise HTTPException(404, "Задача не найдена")
    return task


async def require_bank_manager(user: User, bank: TaskBank):
    if not await can_manage_bank(user, bank):
        raise HTTPException(403, "Недостаточно прав для управления банком задач")


async def serialize_single_task(task: Task, user: User) -> dict:
    bank = task.position.bank
    context = await TaskVisibilityService.get_bank_context(user, bank)

    if not await can_view_bank(user, bank):
        raise HTTPException(404, "Задача не найдена")

    if not context["is_bank_admin"] and task.author_id != user.id and not is_public_task(bank, task):
        raise HTTPException(404, "Задача не найдена")

    items = await TaskVisibilityService.serialize_tasks([task], user, bank, context)
    if not items:
        raise HTTPException(404, "Задача не найдена")
    return items[0]


def position_payload(position: TaskPosition, show_criteria: bool = False, tasks: list[dict] | None = None) -> dict:
    payload = {
        "id": position.id,
        "order": position.order,
        "min_score": position.min_score,
        "max_score": position.max_score,
    }

    if show_criteria:
        payload["criteria_text"] = position.criteria_text
        payload["scoring"] = position.scoring

    if tasks is not None:
        payload["tasks"] = tasks

    return payload


@router.post("/banks")
@min_perms(settings.TEACHER_ROLE)
async def create_bank(body: TaskBankCreate, current_user: User):
    subject = await Subject.get_or_none(id=body.subject_id)
    if not subject:
        raise HTTPException(404, "Предмет не найден")

    if not await can_create_bank(current_user, subject, body.is_global):
        raise HTTPException(403, "Недостаточно прав для создания такого банка задач")

    bank = await TaskBank.create(
        title=body.title,
        subject=subject,
        parallel=body.parallel,
        is_global=body.is_global,
        is_open=body.is_open if body.is_global else False,
        visibility_percent=body.visibility_percent,
        positions_count=body.positions_count,
        created_by=current_user,
    )

    if not bank.is_global:
        await bank.access_teachers.add(current_user)

    await TaskBankService.init_positions(bank, body.positions_count)

    log_audit(
        user_id=current_user.id,
        user_role=current_user.role,
        action="create_bank",
        bank_id=bank.id,
        subject_id=subject.id,
        details={"is_global": bank.is_global},
    )

    return await TaskBankService.full_response(bank, current_user)


@router.get("/banks")
@min_perms(1)
async def list_available_banks(
    subject_id: int | None = None,
    parallel: int | None = Query(default=None, ge=1, le=11),
    current_user: User = Depends(get_current_user),
):
    query = TaskBank.all()
    if subject_id is not None:
        query = query.filter(subject_id=subject_id)
    if parallel is not None:
        query = query.filter(parallel=parallel)

    banks = await query.prefetch_related("subject", "access_teachers").order_by("subject_id", "parallel", "title")

    result = []
    for bank in banks:
        if await can_view_bank(current_user, bank):
            result.append(await TaskBankService.full_response(bank, current_user))

    return result


@router.get("/banks/subject/{subject_id}")
@min_perms(1)
async def list_banks(subject_id: int, current_user: User):
    subject = await Subject.get_or_none(id=subject_id)
    if not subject:
        raise HTTPException(404, "Предмет не найден")

    banks = await TaskBank.filter(subject_id=subject_id).prefetch_related("subject", "access_teachers")

    result = []
    for bank in banks:
        if await can_view_bank(current_user, bank):
            result.append(await TaskBankService.full_response(bank, current_user))

    return result


@router.get("/banks/{bank_id}")
@min_perms(1)
async def get_bank(
    bank_id: int,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=100),
    q: str | None = None,
    position_order: int | None = Query(default=None, ge=1),
    status: int | None = None,
    current_user: User = Depends(get_current_user),
):
    bank = await get_bank_or_404(bank_id)
    await assert_bank_access(current_user, bank)

    context = await TaskVisibilityService.get_bank_context(current_user, bank)

    if status is not None and not context["normal_view"]:
        raise HTTPException(403, "Фильтр по статусу доступен только администраторам банка и учителям параллели")

    if q and not context["normal_view"]:
        raise HTTPException(403, "Поиск доступен только администраторам банка и учителям параллели")

    query = Task.filter(position__bank_id=bank.id, is_deleted=False).prefetch_related("position")

    if position_order is not None:
        query = query.filter(position__order=position_order)
    if status is not None:
        query = query.filter(status=status)
    if q:
        query = query.filter(text__icontains=q)

    tasks = await query
    serialized_tasks = await TaskVisibilityService.serialize_tasks(tasks, current_user, bank, context)
    paged_tasks = paginate(serialized_tasks, page, limit)

    positions = await TaskPosition.filter(bank=bank).order_by("order")
    grouped_tasks: dict[int, list[dict]] = {}
    if context["normal_view"]:
        for item in serialized_tasks:
            grouped_tasks.setdefault(item["position_id"], []).append(item)

    response = await TaskBankService.full_response(bank, current_user)
    response.update(
        {
            "mode": "normal" if context["normal_view"] else "public",
            "tasks": paged_tasks,
            "positions": [
                position_payload(
                    position,
                    show_criteria=context["normal_view"],
                    tasks=grouped_tasks.get(position.id, []) if context["normal_view"] else None,
                )
                for position in positions
            ],
        }
    )

    return response


@router.patch("/banks/{bank_id}")
@min_perms(settings.TEACHER_ROLE)
async def update_bank(bank_id: int, body: TaskBankUpdate, current_user: User):
    bank = await get_bank_or_404(bank_id)
    await require_bank_manager(current_user, bank)

    data = body.model_dump(exclude_unset=True)

    if "subject_id" in data:
        subject = await Subject.get_or_none(id=data["subject_id"])
        if not subject:
            raise HTTPException(404, "Предмет не найден")

        target_is_global = data.get("is_global", bank.is_global)
        if not await can_create_bank(current_user, subject, target_is_global):
            raise HTTPException(403, "Недостаточно прав для переноса банка в этот предмет")
        bank.subject = subject

    if "positions_count" in data:
        await TaskBankService.sync_positions_count(bank, data.pop("positions_count"))

    for key, value in data.items():
        if key == "subject_id":
            continue
        setattr(bank, key, value)

    if not bank.is_global:
        bank.is_open = False

    await bank.save()

    log_audit(
        user_id=current_user.id,
        user_role=current_user.role,
        action="update_bank",
        bank_id=bank.id,
        subject_id=bank.subject_id,
        details=data,
    )

    return await TaskBankService.full_response(bank, current_user)


@router.post("/banks/{bank_id}/teachers/grant")
@min_perms(settings.TEACHER_ROLE)
async def grant_bank_access(bank_id: int, body: TaskBankTeacherAccess, current_user: User):
    bank = await get_bank_or_404(bank_id)
    await require_bank_manager(current_user, bank)

    if bank.is_global:
        raise HTTPException(400, "Доступ учителям настраивается только для закрытых банков")

    teachers = await User.filter(id__in=body.teacher_ids, role__gte=settings.TEACHER_ROLE)

    for teacher in teachers:
        if not await bank.subject.teachers.filter(id=teacher.id).exists():
            raise HTTPException(400, f"Пользователь {teacher.id} не является учителем предмета")

    if teachers:
        await bank.access_teachers.add(*teachers)

    return {"status": "ok", "teacher_ids": [teacher.id for teacher in teachers]}


@router.post("/banks/{bank_id}/teachers/revoke")
@min_perms(settings.TEACHER_ROLE)
async def revoke_bank_access(bank_id: int, body: TaskBankTeacherAccess, current_user: User):
    bank = await get_bank_or_404(bank_id)
    await require_bank_manager(current_user, bank)

    teachers = await User.filter(id__in=body.teacher_ids)
    for teacher in teachers:
        await bank.access_teachers.remove(teacher)

    return {"status": "ok", "teacher_ids": [teacher.id for teacher in teachers]}


@router.post("/banks/{bank_id}/positions/reorder")
@min_perms(settings.TEACHER_ROLE)
async def reorder(bank_id: int, order: list[int], current_user: User):
    bank = await get_bank_or_404(bank_id)
    await require_bank_manager(current_user, bank)

    await reorder_positions(bank, order)
    return {"status": "ok"}


@router.patch("/positions/{position_id}")
@min_perms(settings.TEACHER_ROLE)
async def update_position(position_id: int, body: TaskPositionUpdate, current_user: User):
    position = await TaskPosition.get_or_none(id=position_id).prefetch_related("bank__subject")
    if not position:
        raise HTTPException(404, "Позиция не найдена")

    await require_bank_manager(current_user, position.bank)

    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(position, key, value)

    await position.save()
    return position_payload(position, show_criteria=True)


@router.get("/banks/{bank_id}/positions")
@min_perms(1)
async def get_positions(bank_id: int, current_user: User):
    bank = await get_bank_or_404(bank_id)
    await assert_bank_access(current_user, bank)
    context = await TaskVisibilityService.get_bank_context(current_user, bank)

    positions = await TaskPosition.filter(bank_id=bank_id).order_by("order")
    return [position_payload(position, show_criteria=context["normal_view"]) for position in positions]


@router.post("/tasks")
@min_perms(settings.TEACHER_ROLE)
async def create_task(body: TaskCreate, current_user: User):
    position = await TaskPosition.get_or_none(id=body.position_id).prefetch_related("bank__subject")
    if not position:
        raise HTTPException(404, "Позиция не найдена")

    bank = position.bank
    subject = bank.subject

    if not await can_create_task(current_user, subject):
        raise HTTPException(403, "Недостаточно прав для предложения задачи")

    if not bank.is_global and not await can_manage_bank(current_user, bank):
        raise HTTPException(403, "Нет доступа к закрытому банку задач")

    is_direct_editor = await can_manage_bank(current_user, bank) or await can_moderate_subject(current_user, subject)
    status = TASK_STATUS_APPROVED if is_direct_editor else TASK_STATUS_PENDING
    validate_latex_content(body.text, body.solution, body.answer)

    task = await Task.create(
        code=await generate_unique_task_code(),
        position=position,
        author=current_user,
        text=body.text,
        solution=body.solution,
        answer=body.answer,
        image_url=body.image_url,
        image_scale=body.image_scale,
        image_position=body.image_position,
        status=status,
    )

    log_audit(
        user_id=current_user.id,
        user_role=current_user.role,
        action="create",
        task_id=task.id,
        bank_id=bank.id,
        subject_id=subject.id,
        details={"status_allocated": status, "code": task.code},
    )

    return await serialize_single_task(await get_task_or_404(task.id), current_user)


@router.get("/tasks")
@min_perms(1)
async def list_tasks(
    bank_id: int | None = None,
    position_id: int | None = None,
    status: int | None = None,
    q: str | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
):
    query = Task.filter(is_deleted=False).prefetch_related("position__bank__subject")

    if bank_id is not None:
        query = query.filter(position__bank_id=bank_id)
    if position_id is not None:
        query = query.filter(position_id=position_id)
    if status is not None:
        query = query.filter(status=status)
    if q:
        query = query.filter(text__icontains=q)

    tasks = await query
    grouped: dict[int, list[Task]] = {}

    for task in tasks:
        bank = task.position.bank
        if await can_view_bank(current_user, bank):
            grouped.setdefault(bank.id, []).append(task)

    serialized: list[dict] = []
    for tasks_group in grouped.values():
        bank = tasks_group[0].position.bank
        context = await TaskVisibilityService.get_bank_context(current_user, bank)
        serialized.extend(await TaskVisibilityService.serialize_tasks(tasks_group, current_user, bank, context))

    serialized.sort(key=lambda item: (item.get("position_order") or 0, item["code"]))
    return paginate(serialized, page, limit)


@router.get("/tasks/code/{code}")
@min_perms(1)
async def get_task_by_code(code: str, current_user: User):
    task = await Task.get_or_none(code=code.upper()).prefetch_related("position__bank__subject")
    if not task or task.is_deleted:
        raise HTTPException(404, "Задача не найдена")

    return await serialize_single_task(task, current_user)


@router.get("/tasks/proposals/my")
@min_perms(settings.TEACHER_ROLE)
async def my_task_proposals(
    status: int | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
):
    query = Task.filter(author_id=current_user.id, is_deleted=False).prefetch_related("position__bank__subject")

    if status is not None:
        query = query.filter(status=status)
    else:
        query = query.filter(status__in=[TASK_STATUS_PENDING, TASK_STATUS_REJECTED])

    tasks = await query
    serialized = []

    for task in tasks:
        serialized.append(await serialize_single_task(task, current_user))

    serialized.sort(key=lambda item: (item.get("status") or 0, item["code"]))
    return paginate(serialized, page, limit)


@router.get("/banks/{bank_id}/proposals")
@min_perms(settings.TEACHER_ROLE)
async def bank_proposals(
    bank_id: int,
    status: int | None = TASK_STATUS_PENDING,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
):
    bank = await get_bank_or_404(bank_id)
    await require_bank_manager(current_user, bank)

    query = Task.filter(position__bank_id=bank.id, is_deleted=False).prefetch_related("position")
    if status is not None:
        query = query.filter(status=status)

    tasks = await query
    context = await TaskVisibilityService.get_bank_context(current_user, bank)
    serialized = await TaskVisibilityService.serialize_tasks(tasks, current_user, bank, context)

    return paginate(serialized, page, limit)


@router.get("/positions/{position_id}/tasks")
@min_perms(1)
async def get_position_tasks(
    position_id: int,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=100),
    q: str | None = None,
    current_user: User = Depends(get_current_user),
):
    position = await TaskPosition.get_or_none(id=position_id).prefetch_related("bank__subject")
    if not position:
        raise HTTPException(404, "Позиция не найдена")

    bank = position.bank
    await assert_bank_access(current_user, bank)

    context = await TaskVisibilityService.get_bank_context(current_user, bank)
    if q and not context["normal_view"]:
        raise HTTPException(403, "Поиск доступен только администраторам банка и учителям параллели")

    query = Task.filter(position_id=position_id, is_deleted=False).prefetch_related("position")
    if q:
        query = query.filter(text__icontains=q)

    tasks = await query
    serialized = await TaskVisibilityService.serialize_tasks(tasks, current_user, bank, context)
    return paginate(serialized, page, limit)


@router.get("/banks/{bank_id}/positions/{position_order}/tasks")
@min_perms(1)
async def search_position_tasks(
    bank_id: int,
    position_order: int,
    q: str | None = None,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
):
    position = await TaskPosition.get_or_none(bank_id=bank_id, order=position_order).prefetch_related("bank__subject")
    if not position:
        raise HTTPException(404, "Позиция не найдена")

    return await get_position_tasks(position.id, page, limit, q, current_user)


@router.patch("/tasks/{task_id}")
@min_perms(settings.TEACHER_ROLE)
async def update_task(task_id: uuid.UUID, body: TaskUpdate, current_user: User):
    task = await get_task_or_404(task_id)
    bank = task.position.bank
    subject = bank.subject

    is_manager = await can_manage_bank(current_user, bank)
    if not is_manager and task.author_id != current_user.id:
        raise HTTPException(403, "Можно редактировать только свои предложения")

    data = body.model_dump(exclude_unset=True)
    validate_latex_content(data.get("text"), data.get("solution"), data.get("answer"))

    if "position_id" in data:
        new_position = await TaskPosition.get_or_none(id=data.pop("position_id")).prefetch_related("bank__subject")
        if not new_position:
            raise HTTPException(404, "Новая позиция не найдена")
        if new_position.bank_id != bank.id:
            raise HTTPException(400, "Перемещение между банками не разрешено")
        task.position = new_position

    await create_revision(task, current_user)

    for key, value in data.items():
        setattr(task, key, value)

    old_status = task.status
    if not is_manager:
        task.status = TASK_STATUS_PENDING

    task.version += 1
    await task.save()

    log_audit(
        user_id=current_user.id,
        user_role=current_user.role,
        action="update",
        task_id=task.id,
        bank_id=bank.id,
        subject_id=subject.id,
        details={"old_status": old_status, "new_status": task.status},
    )

    return await serialize_single_task(await get_task_or_404(task.id), current_user)


@router.post("/tasks/{task_id}/move")
@min_perms(settings.TEACHER_ROLE)
async def move_task(task_id: uuid.UUID, body: TaskMove, current_user: User):
    task = await get_task_or_404(task_id)
    new_position = await TaskPosition.get_or_none(id=body.new_position_id).prefetch_related("bank__subject")
    if not new_position:
        raise HTTPException(404, "Новая позиция не найдена")

    bank = task.position.bank
    is_manager = await can_manage_bank(current_user, bank)

    if task.position.bank_id != new_position.bank_id:
        raise HTTPException(400, "Перемещение между банками не разрешено")

    if not is_manager:
        if task.author_id != current_user.id:
            raise HTTPException(403, "Можно перемещать только свои предложения")
        if task.status == TASK_STATUS_APPROVED:
            raise HTTPException(400, "Нельзя перемещать уже одобренную задачу")

    await create_revision(task, current_user)

    old_position_id = task.position_id
    task.position = new_position
    if not is_manager:
        task.status = TASK_STATUS_PENDING
    task.version += 1
    await task.save()

    log_audit(
        user_id=current_user.id,
        user_role=current_user.role,
        action="move",
        task_id=task.id,
        bank_id=bank.id,
        subject_id=bank.subject_id,
        details={"from_position_id": old_position_id, "to_position_id": new_position.id},
    )

    return {"status": "moved"}


@router.delete("/tasks/{task_id}")
@min_perms(settings.TEACHER_ROLE)
async def delete_task(task_id: uuid.UUID, current_user: User):
    task = await get_task_or_404(task_id)
    bank = task.position.bank

    is_manager = await can_manage_bank(current_user, bank)
    if not is_manager:
        if task.author_id != current_user.id:
            raise HTTPException(403, "Можно удалять только свои предложения")
        if task.status == TASK_STATUS_APPROVED:
            raise HTTPException(400, "Одобренную задачу может удалить только администратор банка")

    task.is_deleted = True
    task.deleted_at = datetime.now(timezone.utc)
    task.deleted_by = current_user

    await task.save()

    log_audit(
        user_id=current_user.id,
        user_role=current_user.role,
        action="soft_delete",
        task_id=task_id,
        bank_id=bank.id,
        subject_id=bank.subject_id,
    )

    return {"status": "deleted"}


@router.post("/tasks/{task_id}/submit")
@min_perms(settings.TEACHER_ROLE)
async def submit_task(task_id: uuid.UUID, current_user: User):
    task = await get_task_or_404(task_id)
    bank = task.position.bank

    if task.author_id != current_user.id:
        raise HTTPException(403, "Можно отправить только свою задачу")

    if await can_manage_bank(current_user, bank):
        await create_revision(task, current_user)
        task.status = TASK_STATUS_APPROVED
        task.version += 1
        await task.save()

        log_audit(
            user_id=current_user.id,
            user_role=current_user.role,
            action="approve",
            task_id=task.id,
            bank_id=bank.id,
            subject_id=bank.subject_id,
        )

        return {"status": "approved"}

    task.status = TASK_STATUS_PENDING
    await task.save()
    return {"status": "pending"}


@router.post("/tasks/{task_id}/approve")
@min_perms(settings.TEACHER_ROLE)
async def approve_task(task_id: uuid.UUID, current_user: User):
    task = await get_task_or_404(task_id)
    bank = task.position.bank

    await require_bank_manager(current_user, bank)
    await create_revision(task, current_user)

    task.status = TASK_STATUS_APPROVED
    task.version += 1
    await task.save()

    log_audit(
        user_id=current_user.id,
        user_role=current_user.role,
        action="approve",
        task_id=task.id,
        bank_id=bank.id,
        subject_id=bank.subject_id,
    )

    return {"status": "approved"}


@router.post("/tasks/{task_id}/reject")
@min_perms(settings.TEACHER_ROLE)
async def reject_task(task_id: uuid.UUID, body: TaskReviewCreate, current_user: User):
    task = await get_task_or_404(task_id)
    bank = task.position.bank

    await require_bank_manager(current_user, bank)
    await create_revision(task, current_user)

    task.status = TASK_STATUS_REJECTED
    task.version += 1
    await task.save()

    await create_review(task, current_user, "reject", body.comment)

    log_audit(
        user_id=current_user.id,
        user_role=current_user.role,
        action="reject",
        task_id=task.id,
        bank_id=bank.id,
        subject_id=bank.subject_id,
        details={"comment": body.comment},
    )

    return {"status": "rejected"}


@router.post("/tasks/{task_id}/request_changes")
@min_perms(settings.TEACHER_ROLE)
async def request_changes(task_id: uuid.UUID, body: TaskReviewCreate, current_user: User):
    task = await get_task_or_404(task_id)
    bank = task.position.bank

    await require_bank_manager(current_user, bank)
    await create_revision(task, current_user)

    task.status = TASK_STATUS_PENDING
    task.version += 1
    await task.save()

    await create_review(task, current_user, "request_changes", body.comment)

    log_audit(
        user_id=current_user.id,
        user_role=current_user.role,
        action="request_changes",
        task_id=task.id,
        bank_id=bank.id,
        subject_id=bank.subject_id,
        details={"comment": body.comment},
    )

    return {"status": "changes_requested"}


@router.post("/tasks/digitize")
@min_perms(settings.TEACHER_ROLE)
async def digitize_document(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    extension = Path(file.filename).suffix.lower()

    if extension not in [".docx", ".pdf"]:
        raise HTTPException(400, "Разрешены только файлы форматов .docx и .pdf")

    temp_dir = Path("temp_uploads")
    temp_dir.mkdir(exist_ok=True)
    temp_file_path = temp_dir / f"{uuid.uuid4()}{extension}"

    try:
        with temp_file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        if extension == ".docx":
            result_text = convert_docx_to_math_text(str(temp_file_path))
        else:
            result_text = convert_pdf_to_math_text(str(temp_file_path))

        return {
            "filename": file.filename,
            "success": True,
            "extracted_text": result_text,
        }

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(500, f"Ошибка при обработке файла: {str(exc)}") from exc

    finally:
        if temp_file_path.exists():
            os.remove(temp_file_path)


@router.post("/tasks/{task_id}/restore")
@min_perms(settings.TEACHER_ROLE)
async def restore_task(task_id: uuid.UUID, current_user: User):
    task = await get_task_or_404(task_id)
    bank = task.position.bank

    await require_bank_manager(current_user, bank)

    if not task.is_deleted:
        raise HTTPException(400, "Задача не удалена")

    task.is_deleted = False
    task.deleted_at = None
    task.deleted_by = None

    await task.save()

    log_audit(
        user_id=current_user.id,
        user_role=current_user.role,
        action="restore",
        task_id=task.id,
        bank_id=bank.id,
        subject_id=bank.subject_id,
    )

    return {"status": "restored"}


@router.get("/tasks/deleted")
@min_perms(settings.TEACHER_ROLE)
async def deleted_tasks(bank_id: int | None = None, current_user: User = Depends(get_current_user)):
    if bank_id is None:
        if current_user.role < settings.OPERATOR_ROLE:
            raise HTTPException(403, "Укажите банк задач")
        tasks = await Task.filter(is_deleted=True).prefetch_related("position__bank__subject")
    else:
        bank = await get_bank_or_404(bank_id)
        await require_bank_manager(current_user, bank)
        tasks = await Task.filter(position__bank_id=bank_id, is_deleted=True).prefetch_related("position__bank__subject")

    result = []
    for task in tasks:
        bank = task.position.bank
        if await can_manage_bank(current_user, bank):
            result.append(
                TaskVisibilityService._to_dict(
                    task,
                    show_answers=True,
                    show_meta=True,
                )
            )
    return result


@router.get("/tasks/{task_id}/history")
@min_perms(settings.TEACHER_ROLE)
async def task_history(task_id: uuid.UUID, current_user: User):
    task = await get_task_or_404(task_id)
    bank = task.position.bank

    if not await can_manage_bank(current_user, bank) and task.author_id != current_user.id:
        raise HTTPException(403, "История доступна только администратору банка или автору задачи")

    return await TaskRevision.filter(task_id=task_id).order_by("-version")


@router.get("/tasks/{task_id}/history/{version}")
@min_perms(settings.TEACHER_ROLE)
async def task_version(task_id: uuid.UUID, version: int, current_user: User):
    task = await get_task_or_404(task_id)
    bank = task.position.bank

    if not await can_manage_bank(current_user, bank) and task.author_id != current_user.id:
        raise HTTPException(403, "История доступна только администратору банка или автору задачи")

    return await TaskRevision.get(task_id=task_id, version=version)


@router.post("/tasks/{task_id}/restore/{version}")
@min_perms(settings.TEACHER_ROLE)
async def restore_version(task_id: uuid.UUID, version: int, current_user: User):
    task = await get_task_or_404(task_id)
    bank = task.position.bank

    await require_bank_manager(current_user, bank)

    revision = await TaskRevision.get_or_none(task_id=task_id, version=version)
    if not revision:
        raise HTTPException(404, "Версия не найдена")

    await create_revision(task, current_user)

    task.text = revision.text
    task.solution = revision.solution
    task.answer = revision.answer
    task.image_url = revision.image_url
    task.image_scale = revision.image_scale
    task.image_position = revision.image_position
    task.status = revision.status
    task.version += 1

    await task.save()

    log_audit(
        user_id=current_user.id,
        user_role=current_user.role,
        action="restore_version",
        task_id=task.id,
        bank_id=bank.id,
        subject_id=bank.subject_id,
        details={"restored_version": version, "new_version": task.version},
    )

    return {"status": "ok", "version": task.version}


@router.get("/tasks/{task_id}/reviews")
@min_perms(settings.TEACHER_ROLE)
async def task_reviews(task_id: uuid.UUID, current_user: User):
    task = await get_task_or_404(task_id)
    bank = task.position.bank

    if not await can_manage_bank(current_user, bank) and task.author_id != current_user.id:
        raise HTTPException(403, "Отзывы доступны только администратору банка или автору задачи")

    return await TaskReview.filter(task_id=task_id).order_by("-created_at")
