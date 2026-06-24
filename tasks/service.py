import hashlib
import uuid
from fastapi import HTTPException
from tortoise.transactions import in_transaction
from tasks.models import TaskBank, TaskPosition, Task, TaskReview, TaskRevision
import os
import shutil
from docx import Document
from pathlib import Path
from docx import Document
from pathlib import Path
import fitz

def stable_hash(bank_id: int, task_id: uuid.UUID) -> int:
    key = f"{bank_id}:{str(task_id)}"
    return int(hashlib.md5(key.encode()).hexdigest(), 16)

async def create_revision(
    task: Task,
    user
):
    await TaskRevision.create(
        task=task,
        version=task.version,
        text=task.text,
        solution=task.solution,
        answer=task.answer,
        image_url=task.image_url,
        image_scale=task.image_scale,
        image_position=task.image_position,
        status=task.status,
        changed_by=user
    )

async def create_review(
    task,
    moderator,
    action,
    comment
):
    await TaskReview.create(
        task=task,
        moderator=moderator,
        action=action,
        comment=comment
    )

async def reorder_positions(bank: TaskBank, new_order: list[int]):
    async with in_transaction():
        positions = await bank.positions.all()
        pos_map = {p.id: p for p in positions}
        
        if len(new_order) != len(positions) or set(new_order) != set(pos_map.keys()):
            raise HTTPException(400, "Передан некорректный список ID для сортировки")

        for p in positions:
            p.order = p.order + 10000
            await p.save()

        for idx, pos_id in enumerate(new_order, start=1):
            pos = pos_map[pos_id]
            pos.order = idx
            await pos.save()


class TaskVisibilityService:
    @staticmethod
    async def get_user_context(user, subject) -> tuple[bool, bool, bool]:
        is_operator = user.role >= 3
        is_admin = await subject.admins.filter(id=user.id).exists()
        is_teacher = await subject.teachers.filter(id=user.id).exists()
        return is_operator, is_admin, is_teacher

    @staticmethod
    def filter_and_serialize(tasks: list[Task], user, bank: TaskBank, is_op: bool, is_adm: bool, is_tech: bool) -> list[dict]:
        visible_tasks = []
        is_moderator = is_op or is_adm

        for t in tasks:
            if is_moderator:
                visible_tasks.append(TaskVisibilityService._to_dict(t, show_answers=True))
                continue

            if is_tech:
                if t.author_id == user.id:
                    visible_tasks.append(TaskVisibilityService._to_dict(t, show_answers=True))
                    continue
                if not bank.is_open:
                    continue
                if t.status == 2 and (stable_hash(bank.id, t.id) % 100 < bank.visibility_percent):
                    visible_tasks.append(TaskVisibilityService._to_dict(t, show_answers=True))
                continue

            if not bank.is_open or t.status != 2:
                continue

            if stable_hash(bank.id, t.id) % 100 < bank.visibility_percent:
                visible_tasks.append(TaskVisibilityService._to_dict(t, show_answers=False))

        return visible_tasks

    @staticmethod
    def _to_dict(t: Task, show_answers: bool) -> dict:
        data = {
            "id": str(t.id),
            "position_id": t.position_id,
            "text": t.text,
            "image_url": t.image_url,
            "image_scale": t.image_scale,
            "image_position": t.image_position,
        }
        if show_answers:
            data["solution"] = t.solution
            data["answer"] = t.answer
            data["author_id"] = t.author_id
            data["status"] = t.status
        return data