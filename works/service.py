import json
from datetime import date

from fastapi import HTTPException, status
from tortoise.transactions import in_transaction

from classes.models import SchoolClass
from classes.permissions import is_operator_or_above
from core.roles import ROLE_STUDENT, ROLE_TEACHER
from mail.gmail_service import send_notification_email
from rooms.models import Room
from seating.services import SeatingService
from users.models import User
from works.constants import SUBJECT_LABELS
from works.models import (
    Work,
    WorkParticipant,
    WorkRoom,
    WorkSeating,
    WorkSupervisor,
)
from works.permissions import (
    ensure_teacher_single_class,
    ensure_valid_students,
    get_participant_class_ids,
    get_participant_users,
    is_work_global,
)
from works.work_types import (
    get_work_type,
    has_test_part,
    questions_from_json,
    questions_to_json,
)


class WorkService:
    @staticmethod
    def user_fio(user: User) -> str:
        parts = [user.last_name, user.first_name]
        if user.middle_name:
            parts.append(user.middle_name)
        return " ".join(parts)

    @classmethod
    async def fetch_students(cls, person_ids: list[str]) -> list[User]:
        students = await User.filter(person_id__in=person_ids)
        await ensure_valid_students(students, person_ids)
        return students

    @classmethod
    async def fetch_supervisors(cls, person_ids: list[str]) -> list[User]:
        if not person_ids:
            return []

        supervisors = await User.filter(person_id__in=person_ids)
        found_ids = {u.person_id for u in supervisors}
        missing = set(person_ids) - found_ids
        if missing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Учителя не найдены: {', '.join(sorted(missing))}",
            )

        if any(u.role < ROLE_TEACHER for u in supervisors):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Наблюдателями могут быть только учителя и выше",
            )

        return supervisors

    @classmethod
    async def validate_rooms(cls, room_ids: list[int]) -> list[Room]:
        if not room_ids:
            return []

        rooms = await Room.filter(id__in=room_ids)
        found = {r.id for r in rooms}
        missing = set(room_ids) - found
        if missing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Аудитории не найдены: {', '.join(sorted(str(i) for i in missing))}",
            )
        return rooms

    @classmethod
    async def notify_global_participants(
        cls,
        work: Work,
        students: list[User],
    ) -> None:
        if not await is_work_global(work):
            return

        subject_label = SUBJECT_LABELS.get(work.subject, work.subject)
        work_label = work.work_type_name
        date_str = work.conduct_date.isoformat()

        for student in students:
            participant = await WorkParticipant.get_or_none(
                work_id=work.id,
                user_id=student.id,
            )
            if participant is None or participant.notified:
                continue

            if not student.email_accept:
                continue

            message = (
                f"Здравствуйте, {student.first_name}!\n\n"
                f"Вы приглашены на работу «{work_label}» "
                f"({subject_label}).\n"
                f"Дата проведения: {date_str}.\n\n"
                f"Подробности — в личном кабинете системы."
            )
            html = (
                f"<p>Здравствуйте, {student.first_name}!</p>"
                f"<p>Вы приглашены на работу «<b>{work_label}</b>» "
                f"({subject_label}).</p>"
                f"<p>Дата проведения: <b>{date_str}</b>.</p>"
                f"<p>Подробности — в личном кабинете системы.</p>"
            )

            try:
                await send_notification_email(
                    to=student.email,
                    subject=f"Приглашение: {work_label}",
                    message=message,
                    html=html,
                )
                participant.notified = True
                await participant.save(update_fields=["notified"])
            except HTTPException:
                pass

    @classmethod
    async def create_work(
        cls,
        *,
        actor: User,
        person_ids: list[str],
        work_type_id: str,
        subject: str,
        conduct_date: date,
        room_ids: list[int],
        supervisor_person_ids: list[str],
    ) -> Work:
        students = await cls.fetch_students(person_ids)
        await ensure_teacher_single_class(actor, students)
        await cls.validate_rooms(room_ids)

        if room_ids and not supervisor_person_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Укажите учителей-наблюдателей для аудиторий",
            )

        supervisors = await cls._fetch_supervisors(supervisor_person_ids)
        work_type = get_work_type(work_type_id)

        async with in_transaction():
            work = await Work.create(
                created_by_id=actor.id,
                subject=subject,
                conduct_date=conduct_date,
                work_type_id=work_type.type_id,
                work_type_name=work_type.name,
                questions=work_type.questions,
            )

            for student in students:
                await WorkParticipant.create(work_id=work.id, user_id=student.id)

            for room_id in room_ids:
                await WorkRoom.create(work_id=work.id, room_id=room_id)

            for supervisor in supervisors:
                await WorkSupervisor.create(work_id=work.id, user_id=supervisor.id)

        await cls.notify_global_participants(work, students)
        return work

    @classmethod
    async def add_participants(
        cls,
        *,
        work: Work,
        actor: User,
        person_ids: list[str],
    ) -> Work:
        existing = await WorkParticipant.filter(work_id=work.id).prefetch_related("user")
        existing_users = [p.user for p in existing]
        existing_person_ids = {u.person_id for u in existing_users}

        new_person_ids = [pid for pid in person_ids if pid not in existing_person_ids]
        if not new_person_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Все указанные учащиеся уже добавлены",
            )

        new_students = await cls.fetch_students(new_person_ids)
        all_students = existing_users + new_students
        await ensure_teacher_single_class(actor, all_students)

        if not is_operator_or_above(actor):
            work_class_ids = await get_participant_class_ids(work)
            if work_class_ids:
                new_class_ids = {s.class_id for s in new_students}
                if new_class_ids != work_class_ids:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Новые учащиеся должны быть из того же класса, что и работа",
                    )

        async with in_transaction():
            await WorkParticipant.bulk_create([
                WorkParticipant(work_id=work.id, user_id=student.id)
                for student in new_students
            ])

            await WorkSeating.filter(work_id=work.id).delete()

        await cls.notify_global_participants(work, new_students)
        return work

    @classmethod
    async def get_work_or_404(cls, work_id: str) -> Work:
        work = await Work.get_or_none(work_id=work_id).prefetch_related("created_by")
        if work is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Работа не найдена",
            )
        return work

    @classmethod
    async def get_room_ids(cls, work: Work) -> list[int]:
        rows = await WorkRoom.filter(work_id=work.id)
        return [r.room_id for r in rows]

    @classmethod
    async def get_supervisor_person_ids(cls, work: Work) -> list[str]:
        rows = await WorkSupervisor.filter(work_id=work.id).prefetch_related("user")
        return [r.user.person_id for r in rows]

    @classmethod
    async def seating_required(cls, work: Work) -> bool:
        return bool(await cls.get_room_ids(work))

    @classmethod
    async def seating_generated(cls, work: Work) -> bool:
        return await WorkSeating.filter(work_id=work.id).exists()

    @classmethod
    async def build_work_response(
        cls,
        work: Work,
        *,
        include_participants: bool = False,
    ) -> dict:
        participants = await WorkParticipant.filter(work_id=work.id).prefetch_related("user")
        created_by = await work.created_by
        class_ids = sorted({p.user.class_id for p in participants if p.user.class_id})
        room_ids = await cls.get_room_ids(work)
        supervisor_ids = await cls.get_supervisor_person_ids(work)
        questions = work.questions
        global_work = len(class_ids) > 1

        result = {
            "work_id": work.work_id,
            "work_type_id": work.work_type_id,
            "work_type_name": work.work_type_name,
            "subject": work.subject,
            "conduct_date": work.conduct_date,
            "has_test_part": has_test_part(questions),
            "questions": questions,
            "is_global": global_work,
            "seating_required": bool(room_ids),
            "seating_generated": await cls.seating_generated(work),
            "participant_count": len(participants),
            "class_ids": class_ids,
            "room_ids": room_ids,
            "supervisor_person_ids": supervisor_ids,
            "created_by_person_id": created_by.person_id,
            "created_at": work.created_at,
        }

        if include_participants:
            result["participants"] = [
                {
                    "person_id": p.user.person_id,
                    "first_name": p.user.first_name,
                    "last_name": p.user.last_name,
                    "middle_name": p.user.middle_name,
                    "class_id": p.user.class_id,
                }
                for p in participants
            ]

        return result

    @classmethod
    async def list_works_for_user(cls, user: User) -> list[Work]:
        if is_operator_or_above(user):
            return await Work.all().order_by("-conduct_date", "-created_at")

        work_ids: set[int] = set()

        created = await Work.filter(created_by_id=user.id)
        work_ids.update(w.id for w in created)

        if user.role == ROLE_STUDENT:
            participations = await WorkParticipant.filter(user_id=user.id)
            work_ids.update(p.work_id for p in participations)
        elif user.role >= ROLE_TEACHER:
            homeroom_classes = await SchoolClass.filter(teacher_id=user.id)
            homeroom_class_ids = {c.id for c in homeroom_classes}

            if homeroom_class_ids:
                all_participants = await WorkParticipant.filter(
                    user__class_id__in=homeroom_class_ids
                ).values_list("work_id", flat=True)

                work_ids.update(all_participants)

        if not work_ids:
            return []

        return await Work.filter(id__in=work_ids).order_by("-conduct_date", "-created_at")

    @classmethod
    async def validate_seating(cls, work: Work) -> tuple[bool, str, int, int, bool]:
        seating_required = await cls.seating_required(work)
        if not seating_required:
            return True, "Рассадка не требуется", 0, 0, False

        participants = await get_participant_users(work)
        person_ids = [u.person_id for u in participants]
        room_ids = await cls.get_room_ids(work)
        supervisor_ids = await cls.get_supervisor_person_ids(work)

        if not supervisor_ids:
            return False, "Не указаны учителя-наблюдатели", len(person_ids), 0, True

        data = await SeatingService.prepare_data(person_ids, room_ids, supervisor_ids)
        can_arrange, reason, req, avail = await SeatingService.validate_seating(data)
        return can_arrange, reason, req, avail, True

    @classmethod
    async def generate_seating(cls, work: Work, actor: User) -> WorkSeating:
        seating_required = await cls.seating_required(work)
        if not seating_required:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Для этой работы рассадка не требуется",
            )

        can_arrange, reason, _, _, _ = await cls.validate_seating(work)
        if not can_arrange:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=reason,
            )

        participants = await get_participant_users(work)
        person_ids = [u.person_id for u in participants]
        room_ids = await cls.get_room_ids(work)
        supervisor_ids = await cls.get_supervisor_person_ids(work)

        data = await SeatingService.prepare_data(person_ids, room_ids, supervisor_ids)
        plan = SeatingService.generate_seating_plan(data)

        clean_plan = []
        for room_data in plan:
            item = {k: v for k, v in room_data.items() if not k.startswith("_")}
            clean_plan.append(item)

        plan_json = json.dumps(clean_plan, ensure_ascii=False)

        async with in_transaction():
            existing = await WorkSeating.get_or_none(work_id=work.id)
            if existing:
                await existing.delete()

            seating = await WorkSeating.create(
                work_id=work.id,
                plan_json=plan_json,
                generated_by_id=actor.id,
            )

        return seating

    @classmethod
    async def load_seating_plan(cls, work: Work) -> list[dict] | None:
        seating = await WorkSeating.get_or_none(work_id=work.id)
        if seating is None:
            return None
        return json.loads(seating.plan_json)

    @classmethod
    def find_student_seat(
        cls,
        plan: list[dict],
        person_id: str,
    ) -> dict | None:
        for room_data in plan:
            for student in room_data.get("students", []):
                if student["person_id"] == person_id:
                    return {
                        "person_id": student["person_id"],
                        "fio": student["fio"],
                        "student_class": student["student_class"],
                        "seat": student["seat"],
                        "room_id": room_data["room_id"],
                        "corpus": room_data["corpus"],
                        "number": room_data["number"],
                    }
        return None

    @classmethod
    async def get_seating_response(
        cls,
        work: Work,
        user: User,
    ) -> dict:
        seating_required = await cls.seating_required(work)
        plan = await cls.load_seating_plan(work)
        generated = plan is not None

        from works.permissions import can_view_full_seating

        if user.role == ROLE_STUDENT:
            my_seat = cls.find_student_seat(plan, user.person_id) if plan else None
            return {
                "work_id": work.work_id,
                "seating_required": seating_required,
                "generated": generated,
                "seating": None,
                "my_seat": my_seat,
            }

        if await can_view_full_seating(user, work) and plan:
            rooms = []
            for room_data in plan:
                rooms.append({
                    "room_id": room_data["room_id"],
                    "corpus": room_data["corpus"],
                    "number": room_data["number"],
                    "teachers": room_data.get("teachers", []),
                    "students": [
                        {
                            "person_id": s["person_id"],
                            "fio": s["fio"],
                            "student_class": s["student_class"],
                            "seat": s["seat"],
                            "room_id": room_data["room_id"],
                            "corpus": room_data["corpus"],
                            "number": room_data["number"],
                        }
                        for s in room_data.get("students", [])
                    ],
                })

            return {
                "work_id": work.work_id,
                "seating_required": seating_required,
                "generated": generated,
                "seating": rooms,
                "my_seat": None,
            }

        return {
            "work_id": work.work_id,
            "seating_required": seating_required,
            "generated": generated,
            "seating": None,
            "my_seat": None,
        }

    @classmethod
    async def download_seating_excel(cls, work: Work):
        plan = await cls.load_seating_plan(work)
        if plan is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Рассадка ещё не сгенерирована",
            )
        return SeatingService.generate_excel(plan)
