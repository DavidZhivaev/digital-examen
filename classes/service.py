import re

from fastapi import HTTPException, status
from tortoise.exceptions import IntegrityError

from auth.password_service import (
    UNUSABLE_PASSWORD_HASH,
    build_password_link,
    create_password_token,
)
from auth.session_service import revoke_all_user_sessions
from classes.models import SchoolClass
from classes.permissions import (
    ensure_can_invite_to_class,
    ensure_can_manage_class,
    ensure_can_manage_student,
    is_operator_or_above,
)
from core.roles import ROLE_STUDENT, ROLE_TEACHER
from mail.gmail_service import send_password_email
from users.models import User

_LOGIN_RE = re.compile(r"[^a-z0-9._-]")


def _normalize_group_ids(ids: list) -> list[int]:
    return [int(x) for x in ids if x is not None]


def _active_student_ids(school_class: SchoolClass) -> list[int]:
    first = _normalize_group_ids(school_class.group_first or [])
    second = _normalize_group_ids(school_class.group_second or [])
    return list(dict.fromkeys(first + second))


def _class_to_response(school_class: SchoolClass) -> dict:
    group_first = _normalize_group_ids(school_class.group_first or [])
    group_second = _normalize_group_ids(school_class.group_second or [])
    return {
        "id": school_class.id,
        "teacher_id": school_class.teacher_id,
        "parallel": school_class.parallel,
        "litera": school_class.litera,
        "group_first": group_first,
        "group_second": group_second,
        "history": _normalize_group_ids(school_class.history or []),
        "corpus": school_class.corpus,
        "display_name": school_class.display_name,
        "students_count": len(group_first) + len(group_second),
    }


async def get_class_or_404(class_id: int) -> SchoolClass:
    school_class = await SchoolClass.get_or_none(id=class_id)
    if school_class is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Класс не найден")
    return school_class


async def _generate_login(email: str) -> str:
    base = email.split("@")[0].lower()
    base = _LOGIN_RE.sub("", base.replace(".", ".")) or "user"
    candidate = base
    suffix = 1
    while await User.exists(login=candidate):
        candidate = f"{base}{suffix}"
        suffix += 1
    return candidate


def _remove_from_groups(school_class: SchoolClass, user_id: int) -> None:
    first = _normalize_group_ids(school_class.group_first or [])
    second = _normalize_group_ids(school_class.group_second or [])
    if user_id in first:
        first.remove(user_id)
    if user_id in second:
        second.remove(user_id)
    school_class.group_first = first
    school_class.group_second = second


def _add_to_group(school_class: SchoolClass, user_id: int, group: int) -> None:
    _remove_from_groups(school_class, user_id)
    if group == 1:
        ids = _normalize_group_ids(school_class.group_first or [])
        if user_id not in ids:
            ids.append(user_id)
        school_class.group_first = ids
    else:
        ids = _normalize_group_ids(school_class.group_second or [])
        if user_id not in ids:
            ids.append(user_id)
        school_class.group_second = ids


def _add_to_history(school_class: SchoolClass, user_id: int) -> None:
    history = _normalize_group_ids(school_class.history or [])
    if user_id not in history:
        history.append(user_id)
    school_class.history = history


async def invite_student(
    *,
    actor: User,
    school_class: SchoolClass,
    email: str,
    first_name: str,
    last_name: str,
    middle_name: str | None,
    sex: int | None,
    group: int,
) -> tuple[User, bool]:
    ensure_can_invite_to_class(actor, school_class)

    login = await _generate_login(email)
    try:
        user = await User.create(
            email=email,
            login=login,
            first_name=first_name,
            last_name=last_name,
            middle_name=middle_name,
            sex=sex,
            role=ROLE_STUDENT,
            class_id=school_class.id,
            class_group=group,
            password_hash=UNUSABLE_PASSWORD_HASH,
            must_set_password=True,
        )
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Пользователь с таким email уже существует",
        )

    _add_to_group(school_class, user.id, group)
    await school_class.save()

    link_sent = False
    raw_token = await create_password_token(user, purpose="setup")
    link = build_password_link(raw_token)
    try:
        await send_password_email(
            to=email,
            subject="Установка пароля — Школа 1580",
            greeting=f"Здравствуйте, {last_name} {first_name}!",
            link=link,
        )
        link_sent = True
    except Exception:
        link_sent = False

    return user, link_sent


async def add_existing_student(
    *,
    actor: User,
    school_class: SchoolClass,
    user_id: int,
    group: int,
) -> User:
    ensure_can_manage_class(actor, school_class)
    student = await User.get_or_none(id=user_id)
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")
    if student.role != ROLE_STUDENT:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="В класс можно добавить только учащегося")

    if not is_operator_or_above(actor):
        if student.class_id and student.class_id != school_class.id:
            old_class = await get_class_or_404(student.class_id)
            ensure_can_manage_student(actor, student, old_class)

    if student.class_id and student.class_id != school_class.id:
        old_class = await get_class_or_404(student.class_id)
        _remove_from_groups(old_class, student.id)
        _add_to_history(old_class, student.id)
        await old_class.save()

    student.class_id = school_class.id
    student.class_group = group
    await student.save(update_fields=["class_id", "class_group"])

    _add_to_group(school_class, student.id, group)
    await school_class.save()
    return student


async def move_student_group(
    *,
    actor: User,
    school_class: SchoolClass,
    user_id: int,
    group: int,
) -> User:
    ensure_can_manage_class(actor, school_class)
    student = await User.get_or_none(id=user_id, class_id=school_class.id)
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ученик не найден в этом классе")

    _add_to_group(school_class, user_id, group)
    await school_class.save()

    student.class_group = group
    await student.save(update_fields=["class_group"])
    return student


async def transfer_student(
    *,
    actor: User,
    source_class: SchoolClass | None,
    student: User,
    target_class: SchoolClass,
    group: int,
) -> User:
    if source_class:
        ensure_can_manage_student(actor, student, source_class)
    elif not is_operator_or_above(actor):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")

    if not is_operator_or_above(actor):
        if not source_class or source_class.teacher_id != actor.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Классный руководитель может переводить только учеников своего класса",
            )

    if student.class_id and student.class_id != target_class.id:
        old_class = await get_class_or_404(student.class_id)
        _remove_from_groups(old_class, student.id)
        _add_to_history(old_class, student.id)
        await old_class.save()

    student.class_id = target_class.id
    student.class_group = group
    await student.save(update_fields=["class_id", "class_group"])

    _add_to_group(target_class, student.id, group)
    await target_class.save()
    return student


async def create_class(
    *,
    parallel: int,
    litera: str,
    corpus: int,
    teacher_id: int | None = None,
) -> SchoolClass:
    litera = litera.upper()
    exists = await SchoolClass.filter(parallel=parallel, litera=litera, corpus=corpus).exists()
    if exists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Класс {parallel}{litera} (корпус {corpus}) уже существует",
        )

    try:
        school_class = await SchoolClass.create(
            parallel=parallel,
            litera=litera,
            corpus=corpus,
            group_first=[],
            group_second=[],
            history=[],
        )
    except IntegrityError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Класс уже существует")

    if teacher_id is not None:
        school_class = await assign_teacher(school_class, teacher_id)
    return school_class


async def update_class_fields(school_class: SchoolClass, data: dict) -> SchoolClass:
    if "litera" in data:
        data["litera"] = data["litera"].upper()

    new_parallel = data.get("parallel", school_class.parallel)
    new_litera = data.get("litera", school_class.litera)
    new_corpus = data.get("corpus", school_class.corpus)

    if (new_parallel, new_litera, new_corpus) != (school_class.parallel, school_class.litera, school_class.corpus):
        duplicate = await SchoolClass.filter(
            parallel=new_parallel,
            litera=new_litera,
            corpus=new_corpus,
        ).exclude(id=school_class.id).exists()
        if duplicate:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Класс {new_parallel}{new_litera} (корпус {new_corpus}) уже существует",
            )

    for field, value in data.items():
        setattr(school_class, field, value)
    await school_class.save()
    return school_class


async def delete_class(school_class: SchoolClass) -> None:
    for user_id in _active_student_ids(school_class):
        student = await User.get_or_none(id=user_id)
        if student is None:
            continue
        _add_to_history(school_class, user_id)
        student.class_id = None
        student.class_group = None
        await student.save(update_fields=["class_id", "class_group"])

    await school_class.save()
    await school_class.delete()


async def unassign_teacher(school_class: SchoolClass) -> SchoolClass:
    school_class.teacher_id = None
    await school_class.save()
    return school_class


async def list_class_students(school_class: SchoolClass) -> list[dict]:
    result = []
    for group_num, ids in ((1, school_class.group_first or []), (2, school_class.group_second or [])):
        for user_id in _normalize_group_ids(ids):
            student = await User.get_or_none(id=user_id)
            if student is None:
                continue
            result.append(
                {
                    "id": student.id,
                    "person_id": student.person_id,
                    "email": student.email,
                    "login": student.login,
                    "first_name": student.first_name,
                    "last_name": student.last_name,
                    "middle_name": student.middle_name,
                    "group": group_num,
                    "must_set_password": student.must_set_password,
                }
            )
    return result


async def remove_student_from_class(
    *,
    actor: User,
    school_class: SchoolClass,
    user_id: int,
) -> None:
    ensure_can_manage_class(actor, school_class)
    student = await User.get_or_none(id=user_id, class_id=school_class.id)
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ученик не найден в этом классе")

    _remove_from_groups(school_class, user_id)
    _add_to_history(school_class, user_id)
    await school_class.save()

    student.class_id = None
    student.class_group = None
    await student.save(update_fields=["class_id", "class_group"])


async def assign_teacher(school_class: SchoolClass, teacher_id: int) -> SchoolClass:
    teacher = await User.get_or_none(id=teacher_id)
    if teacher is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Учитель не найден")
    if teacher.role != ROLE_TEACHER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Классным руководителем может быть только пользователь с ролью «Учитель»",
        )

    school_class.teacher_id = teacher.id
    await school_class.save()
    return school_class
