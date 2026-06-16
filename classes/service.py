from datetime import datetime, timezone

from fastapi import HTTPException, status
from tortoise.transactions import in_transaction

from classes.models import SchoolClass, StudentClassHistory, TeacherAssignment
from classes.permissions import (
    can_manage_class,
    can_manage_student,
)
from core.roles import ROLE_STUDENT, ROLE_TEACHER
from users.models import User


def utcnow():
    return datetime.now(timezone.utc)


def validate_group(group: int):
    if group not in (1, 2):
        raise HTTPException(400, "Группа должна быть 1 или 2")

async def get_teacher_classes(user: User):
    assignments = await TeacherAssignment.filter(
        teacher_id=user.id
    ).prefetch_related("school_class")

    return list({a.school_class for a in assignments})

async def assign_teacher_to_class(
    *,
    actor: User,
    teacher_id: int,
    school_class: SchoolClass,
    group: int | None,
    subject: int
):
    can_manage_class(actor, school_class)

    teacher = await User.get_or_none(id=teacher_id)
    if not teacher:
        raise HTTPException(404, "Учитель не найден")

    if teacher.role != ROLE_TEACHER:
        raise HTTPException(400, "Не учитель")

    if group is not None:
        validate_group(group)

    assignment = await TeacherAssignment.create(
        teacher_id=teacher_id,
        school_class=school_class,
        group=group,
        subject=subject
    )

    return assignment

async def remove_teacher_assignment(
    *,
    actor: User,
    assignment_id: int,
):
    assignment = await TeacherAssignment.get_or_none(id=assignment_id)

    if not assignment:
        raise HTTPException(404, "Не найдено")

    can_manage_class(actor, assignment.school_class)

    await assignment.delete()

async def class_student_ids(school_class: SchoolClass) -> list[int]:
    students = await User.filter(
        class_id=school_class.id,
        role=ROLE_STUDENT,
    ).values_list("id", flat=True)

    return list(students)

async def class_student_objects(school_class: SchoolClass) -> list[User]:
    return await User.filter(
        class_id=school_class.id,
        role=ROLE_STUDENT,
    )

async def class_history_ids(school_class: SchoolClass) -> list[int]:
    return await StudentClassHistory.filter(
        school_class=school_class,
    ).values_list("id", flat=True)


async def class_history_objects(
    school_class: SchoolClass,
) -> list[StudentClassHistory]:
    return await StudentClassHistory.filter(
        school_class=school_class,
    ).prefetch_related(
        "user",
        "school_class",
    )

async def get_class_obj(class_id: int) -> SchoolClass:
    obj = await SchoolClass.get_or_none(id=class_id)
    if not obj:
        raise HTTPException(404, "Класс не найден")
    return obj


async def history_student_get(user: User, school_class: SchoolClass):
    await StudentClassHistory.filter(
        user=user,
        school_class=school_class,
        left_at=None,
    ).update(left_at=utcnow())


async def history_student_create(user: User, school_class: SchoolClass, group: int):
    await StudentClassHistory.create(
        user=user,
        school_class=school_class,
        group=group,
    )


async def add_student_class(
    *,
    actor: User,
    school_class: SchoolClass,
    student: User,
    group: int,
):
    can_manage_class(actor, school_class)
    validate_group(group)

    if student.role != ROLE_STUDENT:
        raise HTTPException(400, "Только ученик может быть добавлен")

    if student.class_id and student.class_id != school_class.id:
        raise HTTPException(400, "Ученик уже в другом классе")

    async with in_transaction():
        student.class_id = school_class.id
        student.class_group = group
        await student.save(update_fields=["class_id", "class_group"])

        await history_student_create(student, school_class, group)


async def move_student_group(
    *,
    actor: User,
    school_class: SchoolClass,
    student: User,
    group: int,
):
    can_manage_class(actor, school_class)
    validate_group(group)

    if student.class_id != school_class.id:
        raise HTTPException(400, "Ученик не в этом классе")

    async with in_transaction():
        student.class_group = group
        await student.save(update_fields=["class_group"])

        await history_student_create(student, school_class, group)


async def transfer_student(
    *,
    actor: User,
    source_class: SchoolClass,
    target_class: SchoolClass,
    student: User,
    group: int,
):
    can_manage_student(actor, student, source_class)
    validate_group(group)

    async with in_transaction():
        if student.class_id == source_class.id:
            await history_student_get(student, source_class)

        student.class_id = target_class.id
        student.class_group = group
        await student.save(update_fields=["class_id", "class_group"])

        await history_student_create(student, target_class, group)


async def remove_student_class(
    *,
    actor: User,
    school_class: SchoolClass,
    student: User,
):
    can_manage_class(actor, school_class)

    async with in_transaction():
        await history_student_get(student, school_class)

        student.class_id = None
        student.class_group = None
        await student.save(update_fields=["class_id", "class_group"])


async def class_students(school_class: SchoolClass):
    users = await User.filter(class_id=school_class.id, role=1)
    print(len(users))

    return [
        {
            "id": u.id,
            "person_id": u.person_id,
            "email": u.email,
            "login": u.login,
            "first_name": u.first_name,
            "last_name": u.last_name,
            "middle_name": u.middle_name,
            "group": u.class_group,
            "must_set_password": u.must_set_password,
            "role": 1
        }
        for u in users
    ]


async def create_class(parallel: int, litera: str, corpus: int):
    litera = litera.upper()

    exists = await SchoolClass.filter(
        parallel=parallel,
        litera=litera,
        corpus=corpus,
    ).exists()

    if exists:
        raise HTTPException(409, "Класс уже существует")

    return await SchoolClass.create(
        parallel=parallel,
        litera=litera,
        corpus=corpus,
    )


async def update_class_obj(school_class: SchoolClass, data: dict):
    for k, v in data.items():
        if k == "litera":
            v = v.upper()
        setattr(school_class, k, v)

    await school_class.save()
    return school_class


async def delete_class(school_class: SchoolClass):
    students = await User.filter(class_id=school_class.id)

    async with in_transaction():
        for s in students:
            await history_student_get(s, school_class)
            s.class_id = None
            s.class_group = None
            await s.save(update_fields=["class_id", "class_group"])

        await school_class.delete()


def validate_import_rows(rows):
    emails = set()

    for r in rows:
        if r.email in emails:
            raise HTTPException(400, f"Duplicate email: {r.email}")
        emails.add(r.email)


async def remove_teacher_from_class(
    *,
    actor: User,
    teacher_id: int,
    class_id: int,
):
    school_class = await SchoolClass.get_or_none(id=class_id)
    if not school_class:
        raise HTTPException(404, "Класс не найден")

    can_manage_class(actor, school_class)

    await TeacherAssignment.filter(
        teacher_id=teacher_id,
        school_class_id=class_id,
    ).delete()