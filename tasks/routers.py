from datetime import datetime, timezone
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from core.deps import get_current_user
from core.permissions import min_perms
from subjects.models import Subject
import os
import shutil
from docx import Document
from lxml import etree
from pathlib import Path
from tasks.audit import log_audit
from tasks.permissions import assert_subject_access, can_create_bank, can_create_task, can_moderate_subject
from core.config import settings
from tasks.schemas import TaskBankCreate, TaskCreate, TaskMove, TaskPositionUpdate
from tasks.service import TaskBankService, TaskVisibilityService, convert_docx_to_math_text, convert_pdf_to_math_text, create_review, create_revision, reorder_positions
from users.models import User

from tasks.models import TaskBank, TaskPosition, Task, TaskReview, TaskRevision
from tasks.schemas import *

router = APIRouter()


@router.post("/banks")
@min_perms(1)
async def create_bank(body: TaskBankCreate, current_user: User):
    subject = await Subject.get(id=body.subject_id)

    await assert_subject_access(current_user, subject)

    if not await can_create_bank(current_user, subject):
        raise HTTPException(403)

    bank = await TaskBank.create(
        subject=subject,
        parallel=body.parallel,
        is_open=body.is_open,
        visibility_percent=body.visibility_percent,
        positions_count=body.positions_count,
        created_by=current_user,
    )

    await TaskBankService.init_positions(bank, body.positions_count)

    return await TaskBankService.full_response(bank)


@router.get("/banks/subject/{subject_id}")
@min_perms(1)
async def list_banks(subject_id: int, current_user: User):

    subject = await Subject.get(id=subject_id)
    await assert_subject_access(current_user, subject)

    banks = await TaskBank.filter(subject_id=subject_id)

    return banks

@router.post("/tasks")
@min_perms(2)
async def create_task(body: TaskCreate, current_user: User):
    position = await TaskPosition.get(id=body.position_id).prefetch_related("bank__subject")
    subject = position.bank.subject

    if not await can_create_task(current_user, subject):
        raise HTTPException(403)

    status = 1 if current_user.role < settings.OPERATOR_ROLE else 2

    task = await Task.create(
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
        bank_id=position.bank_id,
        subject_id=subject.id,
        details={"status_allocated": status}
    )

    return task

@router.get("/banks/{bank_id}")
@min_perms(1)
async def get_bank(bank_id: int, current_user: User):
    bank = await TaskBank.get(id=bank_id).prefetch_related("subject", "positions")
    subject = bank.subject

    await assert_subject_access(current_user, subject)
    
    is_op, is_adm, is_tech = await TaskVisibilityService.get_user_context(current_user, subject)
    
    is_student = not (is_op or is_adm or is_tech)
    if is_student and current_user.parallel != bank.parallel:
        raise HTTPException(403, "У вас нет доступа к банку задач другой параллели")

    positions = []
    for p in await bank.positions.all().order_by("order"):
        tasks = await Task.filter(
            position=p,
            is_deleted=False
        )
        
        serialized_tasks = TaskVisibilityService.filter_and_serialize(
            tasks, current_user, bank, is_op, is_adm, is_tech
        )

        positions.append({
            "id": p.id,
            "order": p.order,
            "min_score": p.min_score,
            "max_score": p.max_score,
            "tasks": serialized_tasks
        })

    return {
        "id": bank.id,
        "subject_id": bank.subject_id,
        "parallel": bank.parallel,
        "is_open": bank.is_open,
        "visibility_percent": bank.visibility_percent,
        "positions": positions
    }

@router.post("/banks/{bank_id}/positions/reorder")
@min_perms(settings.OPERATOR_ROLE)
async def reorder(bank_id: int, order: list[int], current_user: User):
    bank = await TaskBank.get(id=bank_id).prefetch_related("subject")
    await assert_subject_access(current_user, bank.subject)

    await reorder_positions(bank, order)
    return {"status": "ok"}

@router.patch("/positions/{position_id}")
@min_perms(settings.OPERATOR_ROLE)
async def update_position(position_id: int, body: TaskPositionUpdate):
    pos = await TaskPosition.get(id=position_id)

    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(pos, k, v)

    await pos.save()
    return pos


@router.post("/tasks/{task_id}/move")
@min_perms(2)
async def move_task(task_id: uuid.UUID, body: TaskMove, current_user: User):
    task = await Task.get(id=task_id).prefetch_related("position__bank__subject")
    new_position = await TaskPosition.get(id=body.new_position_id).prefetch_related("bank__subject")

    if task.status == 2:
        raise HTTPException(400, "Нельзя перемещать одобренную задачу")

    if task.position.bank_id != new_position.bank_id:
        raise HTTPException(400, "Cross-bank move not allowed")

    subject = new_position.bank.subject
    if not await can_create_task(current_user, subject):
        raise HTTPException(403)

    old_position_id = task.position_id
    task.position = new_position
    await task.save()

    log_audit(
        user_id=current_user.id,
        user_role=current_user.role,
        action="move",
        task_id=task.id,
        bank_id=new_position.bank_id,
        subject_id=subject.id,
        details={"from_position_id": old_position_id, "to_position_id": new_position.id}
    )

    return {"status": "moved"}


@router.delete("/tasks/{task_id}")
@min_perms(1)
async def delete_task(task_id: uuid.UUID, current_user: User):
    task = await Task.get(id=task_id).prefetch_related("position__bank__subject")
    subject = task.position.bank.subject
    
    await assert_subject_access(current_user, subject)

    if task.status == 2:
        raise HTTPException(400, "Удалить уже одобренное задание из банка нельзя")

    is_op = current_user.role >= settings.OPERATOR_ROLE
    is_adm = await subject.admins.filter(id=current_user.id).exists()

    if not (is_op or is_adm or task.author_id == current_user.id):
        raise HTTPException(403, "Вы можете удалять только собственные задачи")

    bank_id = task.position.bank_id
    subject_id = subject.id

    task.is_deleted = True
    task.deleted_at = datetime.now(timezone.utc)
    task.deleted_by = current_user

    await task.save()

    log_audit(
        user_id=current_user.id,
        user_role=current_user.role,
        action="soft_delete",
        task_id=task_id,
        bank_id=bank_id,
        subject_id=subject_id
    )

    return {
        "status": "deleted"
    }


@router.patch("/banks/{bank_id}")
@min_perms(2)
async def update_bank(bank_id: int, body: TaskBankCreate, current_user: User):

    bank = await TaskBank.get(id=bank_id).prefetch_related("subject")

    await assert_subject_access(current_user, bank.subject)

    if not await can_create_bank(current_user, bank.subject):
        raise HTTPException(403)

    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(bank, k, v)

    await bank.save()
    return await TaskBankService.full_response(bank)


@router.patch("/tasks/{task_id}")
@min_perms(2)
async def update_task(task_id: uuid.UUID, body: TaskCreate, current_user: User):
    task = await Task.get(id=task_id).prefetch_related("position__bank__subject")
    subject = task.position.bank.subject
    
    await assert_subject_access(current_user, subject)

    is_op = current_user.role >= settings.OPERATOR_ROLE
    is_adm = await subject.admins.filter(id=current_user.id).exists()
    is_moderator = is_op or is_adm

    if not is_moderator and task.author_id != current_user.id:
        raise HTTPException(403, "Вы не являетесь автором этой задачи")
    
    await create_revision(
        task,
        current_user
    )

    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(task, k, v)

    old_status = task.status

    if not is_moderator:
        task.status = 1

    task.version += 1
    await task.save()

    log_audit(
        user_id=current_user.id,
        user_role=current_user.role,
        action="update",
        task_id=task.id,
        bank_id=task.position.bank_id,
        subject_id=subject.id,
        details={"old_status": old_status, "new_status": task.status}
    )

    return task


@router.post("/tasks/{task_id}/submit")
@min_perms(2)
async def submit_task(task_id: uuid.UUID, current_user: User):
    task = await Task.get(id=task_id)
    subject = task.position.bank.subject

    if task.author_id != current_user.id:
        raise HTTPException(403)

    if not await can_moderate_subject(current_user, subject):
        task.status = 1
        await task.save()

        return {"status": "pending"}
    else:
        await create_revision(
            task,
            current_user
        )

        task.status = 2
        task.version += 1

        await task.save()

        log_audit(
            user_id=current_user.id,
            user_role=current_user.role,
            action="approve",
            task_id=task.id,
            bank_id=task.position.bank_id,
            subject_id=subject.id
        )

        return {"status": "approved"}


@router.post("/tasks/{task_id}/approve")
@min_perms(2)
async def approve_task(
    task_id: uuid.UUID,
    current_user: User
):
    task = await Task.get(id=task_id).prefetch_related("position__bank__subject")
    subject = task.position.bank.subject

    if not await can_moderate_subject(current_user, subject):
        raise HTTPException(403)

    await create_revision(
        task,
        current_user
    )

    task.status = 2
    task.version += 1

    await task.save()

    log_audit(
        user_id=current_user.id,
        user_role=current_user.role,
        action="approve",
        task_id=task.id,
        bank_id=task.position.bank_id,
        subject_id=subject.id
    )

    return {"status": "approved"}


@router.post("/tasks/{task_id}/reject")
@min_perms(2)
async def reject_task(
    task_id: uuid.UUID,
    body: TaskReviewCreate,
    current_user: User
):
    task = await Task.get(id=task_id).prefetch_related("position__bank__subject")
    subject = task.position.bank.subject

    if not await can_moderate_subject(current_user, subject):
        raise HTTPException(403)

    await create_revision(
        task,
        current_user
    )

    task.status = 3
    task.version += 1

    await task.save()
    await create_review(
        task,
        current_user,
        "reject",
        body.comment
    )

    log_audit(
        user_id=current_user.id,
        user_role=current_user.role,
        action="reject",
        task_id=task.id,
        bank_id=task.position.bank_id,
        subject_id=subject.id
    )

    return {"status": "rejected"}


@router.post("/tasks/digitize")
@min_perms(2)
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
            "extracted_text": result_text
        }

    except Exception as e:
        raise HTTPException(500, f"Ошибка при обработке файла: {str(e)}")
    
    finally:
        if temp_file_path.exists():
            os.remove(temp_file_path)


@router.post("/tasks/{task_id}/restore")
@min_perms(2)
async def restore_task(
    task_id: uuid.UUID,
    current_user: User
):
    task = await Task.get(id=task_id).prefetch_related(
        "position__bank__subject"
    )

    subject = task.position.bank.subject

    await assert_subject_access(
        current_user,
        subject
    )

    is_op = current_user.role >= settings.OPERATOR_ROLE
    is_adm = await subject.admins.filter(
        id=current_user.id
    ).exists()

    if not (is_op or is_adm):
        raise HTTPException(
            403,
            "Недостаточно прав"
        )

    if not task.is_deleted:
        raise HTTPException(
            400,
            "Задача не удалена"
        )

    task.is_deleted = False
    task.deleted_at = None
    task.deleted_by = None

    await task.save()

    log_audit(
        user_id=current_user.id,
        user_role=current_user.role,
        action="restore",
        task_id=task.id,
        bank_id=task.position.bank_id,
        subject_id=subject.id
    )

    return {
        "status": "restored"
    }


@router.get("/tasks/deleted")
@min_perms(settings.OPERATOR_ROLE)
async def deleted_tasks(current_user: User):
    return await Task.filter(
        is_deleted=True
    )


@router.get("/tasks/{task_id}/history")
@min_perms(1)
async def task_history(task_id: uuid.UUID, current_user: User):
    return await TaskRevision.filter(
        task_id=task_id
    ).order_by(
        "-version"
    )


@router.get("/tasks/{task_id}/history/{version}")
@min_perms(1)
async def task_version(task_id: uuid.UUID, version: int, current_user: User):
    return await TaskRevision.get(
        task_id=task_id,
        version=version
    )


@router.post("/tasks/{task_id}/restore/{version}")
@min_perms(2)
async def restore_version(task_id: uuid.UUID, version: int, current_user: User):
    task = await Task.get(
        id=task_id
    )

    rev = await TaskRevision.get(
        task_id=task_id,
        version=version
    )

    await create_revision(
        task,
        current_user
    )

    task.text = rev.text
    task.solution = rev.solution
    task.answer = rev.answer

    task.image_url = rev.image_url
    task.image_scale = rev.image_scale
    task.image_position = rev.image_position

    task.status = rev.status

    task.version += 1

    await task.save()

    log_audit(
        user_id=current_user.id,
        user_role=current_user.role,
        action="restore_version",
        task_id=task.id,
        bank_id=task.position_id,
        details={
            "restored_version": version,
            "new_version": task.version
        }
    )

    return {
        "status": "ok"
    }


@router.post("/tasks/{task_id}/request_changes")
@min_perms(2)
async def request_changes(
    task_id: uuid.UUID,
    body: TaskReviewCreate,
    current_user: User
):
    task = await Task.get(
        id=task_id
    ).prefetch_related(
        "position__bank__subject"
    )

    subject = task.position.bank.subject

    if not await can_moderate_subject(
        current_user,
        subject
    ):
        raise HTTPException(403)

    await create_revision(
        task,
        current_user
    )

    task.status = 1
    task.version += 1

    await task.save()

    await create_review(
        task,
        current_user,
        "request_changes",
        body.comment
    )

    log_audit(
        user_id=current_user.id,
        user_role=current_user.role,
        action="request_changes",
        task_id=task.id,
        bank_id=task.position.bank_id,
        subject_id=subject.id
    )

    return {
        "status": "changes_requested"
    }


@router.get("/tasks/{task_id}/reviews")
@min_perms(1)
async def task_reviews(task_id: uuid.UUID):
    return await TaskReview.filter(
        task_id=task_id
    ).order_by(
        "-created_at"
    )


@router.get("/banks/{bank_id}/positions")
@min_perms(1)
async def get_positions(bank_id: int, current_user: User):
    bank = await TaskBank.get(id=bank_id).prefetch_related("subject")

    await assert_subject_access(current_user, bank.subject)

    positions = await TaskPosition.filter(
        bank_id=bank_id
    ).order_by("order")

    return [
        {
            "id": p.id,
            "order": p.order,
            "min_score": p.min_score,
            "max_score": p.max_score
        }
        for p in positions
    ]


@router.get("/positions/{position_id}/tasks")
@min_perms(1)
async def get_position_tasks(
    position_id: int,
    page: int = 1,
    limit: int = 20,
    current_user: User = Depends(get_current_user)
):
    position = await TaskPosition.get(
        id=position_id
    ).prefetch_related("bank__subject")

    subject = position.bank.subject

    await assert_subject_access(current_user, subject)

    offset = (page - 1) * limit

    base_query = Task.filter(
        position_id=position_id,
        is_deleted=False
    )

    total = await base_query.count()

    tasks = await base_query.offset(offset).limit(limit)

    is_op, is_adm, is_tech = await TaskVisibilityService.get_user_context(
        current_user,
        subject
    )

    serialized = TaskVisibilityService.filter_and_serialize(
        tasks,
        current_user,
        position.bank,
        is_op,
        is_adm,
        is_tech
    )

    return {
        "page": page,
        "limit": limit,
        "total": total,
        "pages": (total + limit - 1) // limit,
        "items": serialized
    }


@router.get("/tasks")
@min_perms(1)
async def list_tasks(
    bank_id: int | None = None,
    position_id: int | None = None,
    status: int | None = None,
    q: str | None = None,
    page: int = 1,
    limit: int = 20,
    current_user: User = Depends(get_current_user)
):
    offset = (page - 1) * limit
    query = Task.filter(is_deleted=False)

    if bank_id:
        query = query.filter(position__bank_id=bank_id)
    if position_id:
        query = query.filter(position_id=position_id)
    if status is not None:
        query = query.filter(status=status)
    if q:
        query = query.filter(text__icontains=q)

    total = await query.count()
    tasks = await query.offset(offset).limit(limit).prefetch_related(
        "position__bank__subject"
    )

    subject = tasks[0].position.bank.subject if tasks else None

    if subject:
        is_op, is_adm, is_tech = await TaskVisibilityService.get_user_context(
            current_user,
            subject
        )
    else:
        is_op = is_adm = is_tech = False

    serialized = TaskVisibilityService.filter_and_serialize(
        tasks,
        current_user,
        tasks[0].position.bank if tasks else None,
        is_op,
        is_adm,
        is_tech
    )

    return {
        "page": page,
        "limit": limit,
        "total": total,
        "pages": (total + limit - 1) // limit,
        "items": serialized
    }