import io
import json
import math
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import HTTPException, UploadFile
from openpyxl import Workbook
from tortoise.expressions import Q

from classes.models import SchoolClass, TeacherAssignment
from core.config import settings
from files.models import WorkScan
from rooms.models import Room
from seating.services import SeatingService
from subjects.models import Subject
from tasks.models import TaskBank, TaskPosition
from users.models import User
from works.models import Work, WorkParticipant, WorkRecognitionItem, WorkRoom, WorkTestReviewer


WORKS_BASE_DIR = Path("storage/works")
WORKS_BASE_DIR.mkdir(parents=True, exist_ok=True)


def default_grading_scale() -> list[dict[str, float]]:
    return [
        {"from_percent": 0, "grade": 2},
        {"from_percent": 50, "grade": 3},
        {"from_percent": 70, "grade": 4},
        {"from_percent": 85, "grade": 5},
    ]


def paginate(items: list[Any], page: int = 1, limit: int = 20) -> dict:
    page = max(page, 1)
    limit = max(1, min(limit, 100))
    total = len(items)
    start = (page - 1) * limit
    end = start + limit

    return {
        "page": page,
        "limit": limit,
        "total": total,
        "pages": math.ceil(total / limit) if total else 0,
        "items": items[start:end],
    }


def student_fio(user: User) -> str:
    middle = f" {user.middle_name}" if user.middle_name else ""
    return f"{user.last_name} {user.first_name}{middle}"


async def class_map_for_users(users: list[User]) -> dict[int, SchoolClass]:
    class_ids = list({user.class_id for user in users if user.class_id})
    classes = await SchoolClass.filter(id__in=class_ids)
    return {school_class.id: school_class for school_class in classes}


async def ensure_one_parallel(students: list[User]) -> int:
    if any(student.class_id is None for student in students):
        raise HTTPException(400, "У всех участников работы должен быть указан класс")

    class_map = await class_map_for_users(students)
    if len(class_map) != len({student.class_id for student in students}):
        raise HTTPException(400, "Не удалось найти классы всех участников работы")

    parallels = {
        class_map[student.class_id].parallel
        for student in students
        if student.class_id in class_map
    }

    if len(parallels) != 1:
        raise HTTPException(400, "В одной работе может участвовать только одна параллель")

    if not parallels:
        raise HTTPException(400, "У участников не найден класс/параллель")

    return parallels.pop()


async def subject_admin_or_operator(user: User, subject: Subject) -> bool:
    return user.role >= settings.OPERATOR_ROLE or await subject.admins.filter(id=user.id).exists()


async def can_moderate_work(user: User, work: Work) -> bool:
    if work.creator_id == user.id:
        return True

    subject = await Subject.get(id=work.subject_id)
    return await subject_admin_or_operator(user, subject)


async def can_review_test_part(user: User, work: Work) -> bool:
    if await can_moderate_work(user, work):
        return True

    return await WorkTestReviewer.filter(work=work, user=user).exists()


async def can_teacher_create_for_students(user: User, subject: Subject, students: list[User]) -> bool:
    if await subject_admin_or_operator(user, subject):
        return True

    if user.role < settings.TEACHER_ROLE:
        return False

    class_ids = {student.class_id for student in students if student.class_id}
    if len(class_ids) != 1:
        return False

    class_id = next(iter(class_ids))
    school_class = await SchoolClass.get_or_none(id=class_id)
    if not school_class:
        return False

    if school_class.teacher_id == user.id:
        return True

    return await TeacherAssignment.filter(
        teacher_id=user.id,
        school_class_id=class_id,
        subject=subject.id,
    ).exists()


async def can_view_work(user: User, work: Work) -> bool:
    if await can_moderate_work(user, work):
        return True

    if work.creator_id == user.id:
        return True

    if await WorkParticipant.filter(work=work, student=user).exists():
        return True

    participants = await WorkParticipant.filter(work=work).select_related("student")
    students = [participant.student for participant in participants]
    subject = await Subject.get(id=work.subject_id)
    return await can_teacher_create_for_students(user, subject, students)


async def require_work_view(user: User, work: Work):
    if not await can_view_work(user, work):
        raise HTTPException(403, "Нет доступа к работе")


async def require_work_moderator(user: User, work: Work):
    if not await can_moderate_work(user, work):
        raise HTTPException(403, "Недостаточно прав модератора работы")


async def load_students(student_ids: list[int]) -> list[User]:
    students = await User.filter(id__in=student_ids, role=settings.STUDENT_ROLE)
    if len(students) != len(set(student_ids)):
        raise HTTPException(400, "Не все учащиеся найдены")
    return students


async def load_rooms(room_ids: list[int]) -> list[Room]:
    rooms = await Room.filter(id__in=room_ids)
    if len(rooms) != len(set(room_ids)):
        raise HTTPException(400, "Не все аудитории найдены")
    return rooms


async def load_observers(observer_ids: list[int]) -> list[User]:
    if not observer_ids:
        return []

    observers = await User.filter(id__in=observer_ids, role__gte=settings.TEACHER_ROLE)
    if len(observers) != len(set(observer_ids)):
        raise HTTPException(400, "Не все наблюдатели найдены")
    return observers


async def resolve_task_count(subject: Subject, parallel: int, task_bank_id: int | None, task_count: int | None) -> tuple[TaskBank | None, int]:
    if task_bank_id is None:
        if not task_count:
            raise HTTPException(400, "Если банк задач не выбран, нужно указать количество заданий")
        return None, task_count

    bank = await TaskBank.get_or_none(id=task_bank_id).prefetch_related("subject")
    if not bank:
        raise HTTPException(404, "Банк задач не найден")
    if bank.subject_id != subject.id:
        raise HTTPException(400, "Банк задач относится к другому предмету")
    if bank.parallel != parallel:
        raise HTTPException(400, "Параллель банка задач не совпадает с параллелью работы")

    return bank, bank.positions_count


async def validate_seating(students: list[User], rooms: list[Room], observers: list[User]) -> list[dict]:
    data = await SeatingService.prepare_data(
        [student.person_id for student in students],
        [room.id for room in rooms],
        [observer.person_id for observer in observers],
    )
    can_arrange, reason, _, _ = await SeatingService.validate_seating(data)
    if not can_arrange:
        raise HTTPException(400, reason)

    return SeatingService.generate_seating_plan(data)


async def store_seating_plan(work: Work, seating_plan: list[dict]):
    await WorkParticipant.filter(work=work).delete()
    await WorkRoom.filter(work=work).delete()

    work_number = 1
    person_id_map = {user.person_id: user for user in await User.filter(person_id__in=[
        student["person_id"]
        for room in seating_plan
        for student in room.get("students", [])
    ])}

    for room_item in seating_plan:
        observer = None
        teachers = room_item.get("teachers") or []
        if teachers:
            observer = await User.get_or_none(person_id=teachers[0]["person_id"])

        room = await Room.get(id=room_item["room_id"])
        await WorkRoom.create(work=work, room=room, observer=observer)

        for student_item in sorted(room_item.get("students", []), key=lambda item: item["seat"]):
            student = person_id_map[student_item["person_id"]]
            await WorkParticipant.create(
                work=work,
                student=student,
                room=room,
                seat=student_item["seat"],
                work_number=work_number,
            )
            work_number += 1


async def create_work_from_payload(user: User, payload) -> Work:
    subject = await Subject.get_or_none(id=payload.subject_id)
    if not subject:
        raise HTTPException(404, "Предмет не найден")

    students = await load_students(payload.student_ids)
    rooms = await load_rooms(payload.room_ids)
    observers = await load_observers(payload.observer_ids)
    parallel = await ensure_one_parallel(students)

    if not await can_teacher_create_for_students(user, subject, students):
        raise HTTPException(403, "Учитель может создать работу только для своего одного класса")

    bank, task_count = await resolve_task_count(subject, parallel, payload.task_bank_id, payload.task_count)
    seating_plan = await validate_seating(students, rooms, observers)

    grading_scale = [item.model_dump() for item in payload.grading_scale] or default_grading_scale()

    work = await Work.create(
        title=payload.title,
        subject=subject,
        task_bank=bank,
        task_count=task_count,
        scheduled_at=payload.scheduled_at,
        test_config_key=payload.test_config_key,
        send_notifications=payload.send_notifications,
        grading_scale=grading_scale,
        creator=user,
    )

    await store_seating_plan(work, seating_plan)
    (WORKS_BASE_DIR / str(work.id)).mkdir(parents=True, exist_ok=True)
    return work


async def update_work_from_payload(user: User, work: Work, payload) -> Work:
    await require_work_moderator(user, work)

    data = payload.model_dump(exclude_unset=True)

    if "title" in data:
        work.title = data["title"]
    if "scheduled_at" in data:
        work.scheduled_at = data["scheduled_at"]
    if "test_config_key" in data:
        work.test_config_key = data["test_config_key"]

    should_regenerate = "student_ids" in data or "room_ids" in data
    if should_regenerate:
        current_participants = await WorkParticipant.filter(work=work)
        current_rooms = await WorkRoom.filter(work=work)
        student_ids = data.get("student_ids") or [participant.student_id for participant in current_participants]
        room_ids = data.get("room_ids") or [room.room_id for room in current_rooms]

        students = await load_students(student_ids)
        rooms = await load_rooms(room_ids)
        await ensure_one_parallel(students)
        seating_plan = await validate_seating(students, rooms, [])
        await store_seating_plan(work, seating_plan)

    if "task_count" in data and work.task_bank_id is None:
        work.task_count = data["task_count"]

    await work.save()
    return work


async def regenerate_work_seating(user: User, work: Work, payload) -> Work:
    await require_work_moderator(user, work)

    students = await load_students(payload.student_ids)
    rooms = await load_rooms(payload.room_ids)
    await ensure_one_parallel(students)
    seating_plan = await validate_seating(students, rooms, [])
    await store_seating_plan(work, seating_plan)
    return work


async def max_points_by_position(work: Work) -> dict[int, float]:
    if work.task_bank_id:
        positions = await TaskPosition.filter(bank_id=work.task_bank_id).order_by("order")
        return {position.order: float(position.max_score) for position in positions}

    return {position: 1.0 for position in range(1, work.task_count + 1)}


def calculate_grade(percent: float, grading_scale: list[dict]) -> float:
    thresholds = sorted(
        grading_scale or default_grading_scale(),
        key=lambda item: float(item["from_percent"]),
    )
    grade = 2.0

    for item in thresholds:
        if percent >= float(item["from_percent"]):
            grade = float(item["grade"])

    return grade


async def update_scores(work: Work, items: list) -> list[WorkParticipant]:
    max_map = await max_points_by_position(work)
    max_total = sum(max_map.values())

    if max_total <= 0:
        raise HTTPException(400, "Максимальный балл работы должен быть больше 0")

    updated: list[WorkParticipant] = []
    for item in items:
        participant = await WorkParticipant.get_or_none(work=work, student_id=item.student_id)
        if not participant:
            raise HTTPException(404, f"Учащийся {item.student_id} не участвует в работе")

        clean_points: dict[str, float] = {}
        for raw_position, raw_points in item.points.items():
            position = int(raw_position)
            if position not in max_map:
                raise HTTPException(400, f"Позиции {position} нет в работе")
            if raw_points < 0 or raw_points > max_map[position]:
                raise HTTPException(400, f"Баллы за позицию {position} должны быть от 0 до {max_map[position]}")
            clean_points[str(position)] = float(raw_points)

        total = sum(clean_points.values())
        participant.points = clean_points
        participant.percent = round(total / max_total * 100, 2)
        participant.grade = calculate_grade(participant.percent, work.grading_scale)
        await participant.save()
        updated.append(participant)

    return updated


async def participant_payload(participant: WorkParticipant, include_private: bool = False) -> dict:
    student = participant.student
    school_class = await SchoolClass.get_or_none(id=student.class_id) if student.class_id else None

    data = {
        "student_id": student.id,
        "person_id": student.person_id,
        "fio": student_fio(student),
        "class_id": student.class_id,
        "class_name": school_class.display_name if school_class else None,
        "room_id": participant.room_id,
        "seat": participant.seat,
        "work_number": participant.work_number,
        "points": participant.points,
        "percent": participant.percent,
        "grade": participant.grade,
    }

    if include_private:
        data["email"] = student.email

    return data


async def room_payload(work_room: WorkRoom, include_observer: bool) -> dict:
    room = work_room.room
    data = {
        "room_id": room.id,
        "corpus": room.corpus,
        "number": room.number,
        "capacity": room.rows * room.columns,
    }

    if include_observer:
        observer = work_room.observer
        data["observer"] = (
            {
                "id": observer.id,
                "person_id": observer.person_id,
                "fio": student_fio(observer),
            }
            if observer
            else None
        )

    return data


async def scan_payloads(work: Work, participant: WorkParticipant | None = None) -> list[dict]:
    query = WorkScan.filter(work_id=work.id)
    if participant is not None:
        query = query.filter(work_number=participant.work_number)

    scans = await query.order_by("work_number")
    return [
        {
            "work_id": str(scan.work_id),
            "scan_id": str(scan.id),
            "work_number": scan.work_number,
            "results": scan.results,
        }
        for scan in scans
    ]


async def work_summary(work: Work, user: User) -> dict:
    subject = await Subject.get(id=work.subject_id)
    rooms = await WorkRoom.filter(work=work).select_related("room").order_by("room__corpus", "room__number")
    participants = await WorkParticipant.filter(work=work).select_related("student")
    is_student = await WorkParticipant.filter(work=work, student=user).exists()

    first_room = rooms[0].room if rooms else None
    payload = {
        "id": str(work.id),
        "title": work.title,
        "subject_id": subject.id,
        "subject_name": subject.name,
        "scheduled_at": work.scheduled_at,
        "task_count": work.task_count,
        "creator_id": work.creator_id,
        "task_bank_id": work.task_bank_id,
        "test_config_key": work.test_config_key,
        "participants_count": len(participants),
        "corpus": first_room.corpus if first_room else None,
        "room": first_room.number if first_room else None,
    }

    if is_student:
        participant = await WorkParticipant.get(work=work, student=user).select_related("room")
        payload["seat"] = participant.seat
        payload["work_number"] = participant.work_number

    return payload


async def work_card(work: Work, user: User, student_view_for: int | None = None) -> dict:
    await require_work_view(user, work)
    moderator = await can_moderate_work(user, work)

    subject = await Subject.get(id=work.subject_id)
    rooms = await WorkRoom.filter(work=work).select_related("room", "observer").order_by("room__corpus", "room__number")
    participants = await WorkParticipant.filter(work=work).select_related("student", "room").order_by("work_number")

    selected_participant = None
    if student_view_for is not None:
        if not moderator:
            raise HTTPException(403, "Смотреть карточку учащегося может только модератор")
        selected_participant = await WorkParticipant.get_or_none(work=work, student_id=student_view_for).select_related("student", "room")
        if not selected_participant:
            raise HTTPException(404, "Учащийся не участвует в работе")
    elif await WorkParticipant.filter(work=work, student=user).exists() and not moderator:
        selected_participant = await WorkParticipant.get(work=work, student=user).select_related("student", "room")

    if selected_participant:
        room = selected_participant.room
        return {
            "id": str(work.id),
            "title": work.title,
            "subject_id": subject.id,
            "subject_name": subject.name,
            "scheduled_at": work.scheduled_at,
            "corpus": room.corpus if room else None,
            "room": room.number if room else None,
            "seat": selected_participant.seat,
            "work_number": selected_participant.work_number,
            "scores": {
                "points": selected_participant.points,
                "percent": selected_participant.percent,
                "grade": selected_participant.grade,
            },
            "scans": await scan_payloads(work, selected_participant),
        }

    class_map = await class_map_for_users([participant.student for participant in participants])
    class_ids = sorted({participant.student.class_id for participant in participants if participant.student.class_id})

    return {
        "id": str(work.id),
        "title": work.title,
        "subject_id": subject.id,
        "subject_name": subject.name,
        "scheduled_at": work.scheduled_at,
        "task_count": work.task_count,
        "task_bank_id": work.task_bank_id,
        "test_config_key": work.test_config_key,
        "send_notifications": work.send_notifications,
        "grading_scale": work.grading_scale,
        "creator_id": work.creator_id,
        "classes": [
            {
                "class_id": class_id,
                "display_name": class_map[class_id].display_name if class_id in class_map else None,
            }
            for class_id in class_ids
        ],
        "rooms": [await room_payload(work_room, include_observer=True) for work_room in rooms],
        "participants": [await participant_payload(participant, include_private=True) for participant in participants],
        "scans": await scan_payloads(work),
    }


def seating_plan_from_db(work_rooms: list[WorkRoom], participants: list[WorkParticipant], include_observers: bool) -> list[dict]:
    by_room: dict[int, list[WorkParticipant]] = {}
    for participant in participants:
        if participant.room_id:
            by_room.setdefault(participant.room_id, []).append(participant)

    result = []
    for work_room in work_rooms:
        room = work_room.room
        students = []
        for participant in sorted(by_room.get(room.id, []), key=lambda item: item.seat or ""):
            student = participant.student
            students.append(
                {
                    "person_id": student.person_id,
                    "fio": student_fio(student),
                    "student_class": "",
                    "seat": participant.seat,
                }
            )

        item = {
            "room_id": room.id,
            "corpus": room.corpus,
            "number": room.number,
            "teachers": [],
            "students": students,
        }

        if include_observers and work_room.observer:
            item["teachers"] = [
                {
                    "person_id": work_room.observer.person_id,
                    "fio": student_fio(work_room.observer),
                }
            ]

        result.append(item)

    return result


async def seating_excel(work: Work, sorted_view: bool) -> io.BytesIO:
    work_rooms = await WorkRoom.filter(work=work).select_related("room", "observer").order_by("room__corpus", "room__number")
    participants = await WorkParticipant.filter(work=work).select_related("student")
    plan = seating_plan_from_db(work_rooms, participants, include_observers=True)
    return SeatingService.sorted_generate_excel(plan) if sorted_view else SeatingService.generate_excel(plan)


async def variant_print_payload(work: Work, student_id: int | None, room_id: int | None) -> dict:
    warning = None
    now = datetime.now(timezone.utc)
    scheduled = work.scheduled_at
    if scheduled.tzinfo is None:
        scheduled = scheduled.replace(tzinfo=timezone.utc)
    if scheduled > now:
        warning = "Печатать задания пока может быть рано: работа еще не наступила"

    query = WorkParticipant.filter(work=work).select_related("student", "room")
    if student_id is not None:
        query = query.filter(student_id=student_id)
    if room_id is not None:
        query = query.filter(room_id=room_id)

    participants = await query.order_by("work_number")
    if not participants:
        raise HTTPException(404, "Не найдено участников для печати")

    return {
        "work_id": str(work.id),
        "title": work.title,
        "task_bank_id": work.task_bank_id,
        "warning": warning,
        "target": {"student_id": student_id, "room_id": room_id},
        "participants": [
            {
                "student_id": participant.student_id,
                "fio": student_fio(participant.student),
                "room_id": participant.room_id,
                "seat": participant.seat,
                "work_number": participant.work_number,
            }
            for participant in participants
        ],
    }


async def answers_print_payload(work: Work, copies: int) -> dict:
    if not work.task_bank_id:
        raise HTTPException(400, "Ответы и решения можно печатать только для работы с банком задач")

    return {
        "work_id": str(work.id),
        "title": work.title,
        "task_bank_id": work.task_bank_id,
        "copies": copies,
    }


def test_configs_path() -> Path:
    return Path(settings.WORK_TYPES_PATH)


def load_test_configs() -> list[dict[str, dict[str, str]]]:
    path = test_configs_path()
    if not path.exists():
        return []

    return json.loads(path.read_text(encoding="utf-8"))


def save_test_configs(configs: list[dict[str, dict[str, str]]]):
    path = test_configs_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(configs, ensure_ascii=False, indent=2), encoding="utf-8")


def get_test_config(config_key: str | None) -> dict[str, str] | None:
    if not config_key:
        return None

    for item in load_test_configs():
        if config_key in item:
            return item[config_key]
    return None


async def upload_work_scans(work: Work, file: UploadFile) -> dict:
    work_dir = WORKS_BASE_DIR / str(work.id)
    work_dir.mkdir(parents=True, exist_ok=True)

    if not file.filename.lower().endswith(".zip"):
        raise HTTPException(400, "Разрешены только ZIP-архивы")

    zip_content = await file.read()
    zip_buffer = io.BytesIO(zip_content)
    warnings: list[str] = []
    scans_processed = 0
    recognition_items_created = 0
    known_numbers = set(await WorkParticipant.filter(work=work).values_list("work_number", flat=True))
    config = get_test_config(work.test_config_key)

    try:
        with zipfile.ZipFile(zip_buffer) as archive:
            names = archive.namelist()
            results_data = {}
            results_file = next((name for name in names if name.endswith("results.json")), None)
            if results_file:
                with archive.open(results_file) as results_stream:
                    results_data = json.load(results_stream)

            for name in names:
                if name.endswith("/") or name.endswith("results.json"):
                    continue

                path = Path(name)
                if path.suffix.lower() != ".pdf":
                    continue

                try:
                    work_number = int(path.stem)
                except ValueError:
                    warnings.append(f"Файл {name} пропущен: имя PDF должно быть номером работы")
                    continue

                if work_number not in known_numbers:
                    warnings.append(f"Скан {name} загружен, но участник с номером {work_number} не найден")

                pdf_data = archive.read(name)
                target_path = work_dir / f"{work_number}.pdf"
                target_path.write_bytes(pdf_data)

                scan_results = results_data.get(str(work_number)) or {}
                scan, _ = await WorkScan.update_or_create(
                    work_id=work.id,
                    work_number=work_number,
                    defaults={"results": scan_results},
                )
                scans_processed += 1

                if config:
                    await WorkRecognitionItem.filter(work=work, scan_id=scan.id).delete()
                    for position_raw, expected_chars in config.items():
                        position = int(position_raw)
                        result_value = scan_results.get(str(position)) or scan_results.get(position)
                        fragment_url = None
                        suggested_text = None

                        if isinstance(result_value, dict):
                            suggested_text = result_value.get("text") or result_value.get("value")
                            fragment_url = result_value.get("fragment_url")
                        elif result_value is not None:
                            suggested_text = str(result_value)

                        status = "pending"
                        if suggested_text and any(char not in expected_chars for char in suggested_text):
                            status = "disputed"

                        await WorkRecognitionItem.create(
                            work=work,
                            scan_id=scan.id,
                            work_number=work_number,
                            position=position,
                            expected_chars=expected_chars,
                            suggested_text=suggested_text,
                            fragment_url=fragment_url,
                            status=status,
                        )
                        recognition_items_created += 1

    except zipfile.BadZipFile as exc:
        raise HTTPException(400, "Передан некорректный ZIP-архив") from exc

    return {
        "work_id": work.id,
        "scans_processed": scans_processed,
        "recognition_items_created": recognition_items_created,
        "warnings": warnings,
        "status": "success" if not warnings else "warning",
    }


async def assign_test_reviewers(work: Work, actor: User, user_ids: list[int]) -> list[int]:
    await require_work_moderator(actor, work)
    users = await User.filter(id__in=user_ids)
    if len(users) != len(set(user_ids)):
        raise HTTPException(400, "Не все пользователи найдены")

    for user in users:
        await WorkTestReviewer.update_or_create(
            defaults={"assigned_by": actor},
            work=work,
            user=user,
        )

    return [user.id for user in users]


async def recognition_batch(work: Work, user: User, limit: int = 5) -> list[dict]:
    if not await can_review_test_part(user, work):
        raise HTTPException(403, "Нет доступа к проверке тестовой части")

    limit = max(1, min(limit, 20))
    query = WorkRecognitionItem.filter(work=work, status__in=["pending", "disputed"]).filter(
        Q(assigned_to_id=user.id) | Q(assigned_to_id=None)
    ).order_by("work_number", "position").limit(limit)

    items = await query
    for item in items:
        if item.assigned_to_id is None:
            item.assigned_to = user
            await item.save()

    return [recognition_item_payload(item) for item in items]


def recognition_item_payload(item: WorkRecognitionItem) -> dict:
    return {
        "id": item.id,
        "work_id": str(item.work_id),
        "scan_id": str(item.scan_id) if item.scan_id else None,
        "work_number": item.work_number,
        "position": item.position,
        "expected_chars": item.expected_chars,
        "suggested_text": item.suggested_text,
        "confirmed_text": item.confirmed_text,
        "fragment_url": item.fragment_url,
        "status": item.status,
        "assigned_to_id": item.assigned_to_id,
    }


async def confirm_recognition_item(work: Work, item_id: int, user: User, text: str) -> dict:
    if not await can_review_test_part(user, work):
        raise HTTPException(403, "Нет доступа к проверке тестовой части")

    item = await WorkRecognitionItem.get_or_none(id=item_id, work=work)
    if not item:
        raise HTTPException(404, "Элемент распознавания не найден")

    if item.assigned_to_id not in (None, user.id) and not await can_moderate_work(user, work):
        raise HTTPException(403, "Этот элемент сейчас проверяет другой пользователь")

    item.confirmed_text = text
    item.status = "confirmed"
    item.confirmed_by = user
    item.assigned_to = user
    await item.save()

    return recognition_item_payload(item)


async def test_sections_list(user: User) -> list[dict]:
    works = await Work.all().exclude(test_config_key=None).prefetch_related("subject").order_by("-scheduled_at")
    result = []

    for work in works:
        if not await can_review_test_part(user, work):
            continue

        pending = await WorkRecognitionItem.filter(work=work, status__in=["pending", "disputed"]).count()
        result.append(
            {
                "work_id": str(work.id),
                "title": work.title,
                "subject_id": work.subject_id,
                "scheduled_at": work.scheduled_at,
                "status": "Спорные случаи" if pending else "Скачать",
                "pending_count": pending,
            }
        )

    return result


async def recognition_report(work: Work) -> io.BytesIO:
    wb = Workbook()
    ws = wb.active
    ws.title = "recognition"
    ws.append(["work_number", "scan_id", "position", "suggested", "confirmed", "status"])

    items = await WorkRecognitionItem.filter(work=work).order_by("work_number", "position")
    for item in items:
        ws.append([
            item.work_number,
            str(item.scan_id) if item.scan_id else "",
            item.position,
            item.suggested_text,
            item.confirmed_text,
            item.status,
        ])

    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    return stream
