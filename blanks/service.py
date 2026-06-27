import io
from pathlib import Path

from fastapi import HTTPException
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from blanks.models import BlankIssue
from tasks.models import Task
from works.models import Work, WorkParticipant
from works.service import can_moderate_work, get_test_config, student_fio


IDS_PATH = Path("blanks/ids.txt")


def _read_ids() -> list[str]:
    if not IDS_PATH.exists():
        raise HTTPException(500, "Файл blanks/ids.txt не найден")

    return [
        line.strip()
        for line in IDS_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip().isdigit() and len(line.strip()) == 13
    ]


async def reserve_blank_code(work: Work, kind: str, user, participant: WorkParticipant | None = None, payload: dict | None = None) -> BlankIssue:
    used_codes = set(await BlankIssue.filter(work=work).values_list("code", flat=True))

    for code in _read_ids():
        if code in used_codes:
            continue

        return await BlankIssue.create(
            work=work,
            participant=participant,
            code=code,
            kind=kind,
            print_type="duplex" if kind in {"solution", "variant"} else "single-sided",
            issued_by=user,
            payload=payload or {},
        )

    raise HTTPException(409, "Свободные 13-значные номера для этой работы закончились")


async def ensure_participant_code(work: Work, participant: WorkParticipant, user) -> str:
    if participant.participant_code:
        return participant.participant_code

    issue = await reserve_blank_code(work, "participant", user, participant)
    participant.participant_code = issue.code
    await participant.save()
    return issue.code


async def select_participants(work: Work, participant_ids=None, participant_codes=None, room_id=None) -> list[WorkParticipant]:
    query = WorkParticipant.filter(work=work).select_related("student", "room")

    if participant_ids:
        query = query.filter(id__in=participant_ids)
    if participant_codes:
        query = query.filter(participant_code__in=participant_codes)
    if room_id:
        query = query.filter(room_id=room_id)

    participants = await query.order_by("room_id", "seat", "work_number")
    if not participants:
        raise HTTPException(404, "Участники для печати не найдены")
    return participants


def _write_simple_pdf(title: str, rows: list[str]) -> io.BytesIO:
    stream = io.BytesIO()
    pdf = canvas.Canvas(stream, pagesize=A4)
    width, height = A4

    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(40, height - 50, title)
    pdf.setFont("Helvetica", 10)
    y = height - 80

    for row in rows:
        if y < 50:
            pdf.showPage()
            pdf.setFont("Helvetica", 10)
            y = height - 50
        pdf.drawString(40, y, row[:110])
        y -= 16

    pdf.save()
    stream.seek(0)
    return stream


async def solution_blanks_pdf(work: Work, user, participant_ids=None, participant_codes=None, copies_per_participant: int = 1) -> tuple[io.BytesIO, dict]:
    if not await can_moderate_work(user, work):
        raise HTTPException(403, "Недостаточно прав администратора работы")

    participants = await select_participants(work, participant_ids, participant_codes)
    rows: list[str] = []
    issues: list[dict] = []

    for participant in participants:
        await ensure_participant_code(work, participant, user)
        chain = dict(participant.blank_chain or {})

        for _ in range(copies_per_participant):
            issue = await reserve_blank_code(work, "solution", user, participant)
            chain[issue.code] = participant.participant_code
            issues.append({"participant_code": participant.participant_code, "blank_code": issue.code})
            rows.append(f"{student_fio(participant.student)} | participant {participant.participant_code} | blank {issue.code}")

        participant.blank_chain = chain
        await participant.save()

    return _write_simple_pdf("Solution blanks", rows), {"print_type": "duplex", "issues": issues}


async def title_blanks_pdf(work: Work, user, participant_ids=None, participant_codes=None) -> tuple[io.BytesIO, dict]:
    if not await can_moderate_work(user, work):
        raise HTTPException(403, "Недостаточно прав администратора работы")

    participants = await select_participants(work, participant_ids, participant_codes)
    rows: list[str] = []
    issues: list[dict] = []
    test_config = get_test_config(work.test_config_key)

    for participant in participants:
        await ensure_participant_code(work, participant, user)
        issue = await reserve_blank_code(
            work,
            "title",
            user,
            participant,
            payload={"test_config": test_config},
        )
        rows.append(f"{student_fio(participant.student)} | participant {participant.participant_code} | title {issue.code}")
        issues.append({"participant_code": participant.participant_code, "blank_code": issue.code})

    return _write_simple_pdf("Title blanks", rows), {"print_type": "single-sided", "issues": issues, "test_config": test_config}


async def variants_payload(work: Work, user, participant_ids=None, participant_codes=None, room_id=None) -> dict:
    if not await can_moderate_work(user, work):
        raise HTTPException(403, "Недостаточно прав администратора работы")

    participants = await select_participants(work, participant_ids, participant_codes, room_id)
    result = []

    for participant in participants:
        tasks_payload = []
        for position, task_id in sorted((participant.variant_tasks or {}).items(), key=lambda item: int(item[0])):
            task = await Task.get_or_none(id=task_id)
            if task:
                tasks_payload.append(
                    {
                        "position": int(position),
                        "task_id": str(task.id),
                        "text": task.text,
                        "image_url": task.image_url,
                        "image_scale": task.image_scale,
                        "image_position": task.image_position,
                    }
                )

        room = participant.room
        place = None
        if room and participant.seat:
            place = f"{room.corpus}-{room.number}-{participant.seat}"

        result.append(
            {
                "participant_code": participant.participant_code,
                "student_id": participant.student_id,
                "fio": student_fio(participant.student),
                "work_title": work.title,
                "place": place,
                "tasks": tasks_payload,
            }
        )

    return {
        "work_id": str(work.id),
        "print_type": "duplex",
        "participants": result,
        "generator_contract": {
            "input": "work_title, participant_code, place, tasks[position,text,image_*]",
            "output": "pdf bytes + print_type",
        },
    }

