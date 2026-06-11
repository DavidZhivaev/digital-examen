from fastapi import APIRouter, HTTPException, status
from fastapi import UploadFile, File
from fastapi.responses import StreamingResponse
import io
from openpyxl import Workbook, load_workbook

from classes.models import SchoolClass
from fastapi import Query
from users.routers import transliterate
from tortoise.transactions import in_transaction
from classes.service import (
    add_student_to_class,
    move_student_group,
    transfer_student,
    remove_student_from_class,
    list_class_students,
    create_class,
    update_class_fields,
    delete_class,
    get_class_or_404,
)
from classes.permissions import (
    ensure_can_manage_class,
    is_homeroom_teacher,
    is_operator_or_above,
)
from classes.schemas import (
    ClassCreate,
    ClassImportRow,
    ClassUpdate,
    ClassResponse,
    ClassStudentResponse,
    AssignTeacherRequest,
    StudentInviteRequest,
    StudentInviteResponse,
    AddExistingStudentRequest,
    MoveGroupRequest,
    TransferStudentRequest,
)
from core.config import settings
from core.permissions import min_perms
from core.roles import ROLE_TEACHER, ROLE_STUDENT
from users.models import User

router = APIRouter()


def _ensure_homeroom_or_operator(user: User, school_class: SchoolClass) -> None:
    if is_operator_or_above(user):
        return
    if not is_homeroom_teacher(user, school_class):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа",
        )


def _to_class_response(c: SchoolClass, students_count: int = 0) -> ClassResponse:
    return ClassResponse(
        id=c.id,
        teacher_id=c.teacher_id,
        parallel=c.parallel,
        litera=c.litera,
        corpus=c.corpus,
        display_name=c.display_name,
        students_count=students_count,
    )



@router.get("/health")
async def health():
    return {"service": "classes", "status": "ok"}


@router.get("/", response_model=list[ClassResponse])
@min_perms(ROLE_TEACHER)
async def list_classes(current_user: User):
    if is_operator_or_above(current_user):
        classes = await SchoolClass.all().order_by("corpus", "parallel", "litera")
    else:
        classes = await SchoolClass.filter(
            teacher_id=current_user.id
        ).order_by("corpus", "parallel", "litera")

    result = []
    for c in classes:
        students = await list_class_students(c)
        result.append(_to_class_response(c, len(students)))

    return result


@router.post("/", response_model=ClassResponse, status_code=status.HTTP_201_CREATED)
@min_perms(settings.OPERATOR_ROLE)
async def create_class_endpoint(body: ClassCreate, current_user: User):
    school_class = await create_class(
        parallel=body.parallel,
        litera=body.litera,
        corpus=body.corpus,
    )
    return _to_class_response(school_class)


@router.get("/{class_id}", response_model=ClassResponse)
@min_perms(ROLE_TEACHER)
async def get_class(class_id: int, current_user: User):
    school_class = await get_class_or_404(class_id)
    ensure_can_manage_class(current_user, school_class)

    students = await list_class_students(school_class)
    return _to_class_response(school_class, len(students))


@router.patch("/{class_id}", response_model=ClassResponse)
@min_perms(ROLE_TEACHER)
async def update_class(class_id: int, body: ClassUpdate, current_user: User):
    school_class = await get_class_or_404(class_id)
    ensure_can_manage_class(current_user, school_class)

    school_class = await update_class_fields(
        school_class,
        body.model_dump(exclude_unset=True),
    )

    students = await list_class_students(school_class)
    return _to_class_response(school_class, len(students))


@router.delete("/{class_id}", status_code=status.HTTP_204_NO_CONTENT)
@min_perms(settings.OPERATOR_ROLE)
async def delete_class_endpoint(
    class_id: int, 
    current_user: User, 
    delete_students: bool = Query(False, description="Удалить ли всех учащихся из этого класса?")
):
    school_class = await get_class_or_404(class_id)
    
    async with in_transaction():
        if delete_students:
            await User.filter(class_id=class_id).delete()
            
        await delete_class(school_class)
        
    return None



@router.patch("/{class_id}/teacher", response_model=ClassResponse)
@min_perms(settings.OPERATOR_ROLE)
async def set_class_teacher(class_id: int, body: AssignTeacherRequest, current_user: User):
    school_class = await get_class_or_404(class_id)

    teacher = await User.get_or_none(id=body.teacher_id)
    if not teacher:
        raise HTTPException(404, "Учитель не найден")

    if teacher.role != ROLE_TEACHER:
        raise HTTPException(400, "Пользователь не учитель")

    school_class.teacher_id = teacher.id
    await school_class.save()

    students = await list_class_students(school_class)
    return _to_class_response(school_class, len(students))


@router.delete("/{class_id}/teacher", response_model=ClassResponse)
@min_perms(settings.OPERATOR_ROLE)
async def remove_class_teacher(class_id: int, current_user: User):
    school_class = await get_class_or_404(class_id)

    school_class.teacher_id = None
    await school_class.save()

    students = await list_class_students(school_class)
    return _to_class_response(school_class, len(students))


@router.get("/{class_id}/students", response_model=list[ClassStudentResponse])
@min_perms(ROLE_TEACHER)
async def get_class_students(class_id: int, current_user: User):
    school_class = await get_class_or_404(class_id)
    ensure_can_manage_class(current_user, school_class)

    return await list_class_students(school_class)


@router.post("/{class_id}/students", response_model=StudentInviteResponse)
@min_perms(ROLE_TEACHER)
async def add_student(class_id: int, body: AddExistingStudentRequest, current_user: User):
    school_class = await get_class_or_404(class_id)
    student = await User.get_or_none(id=body.user_id)

    if not student:
        raise HTTPException(404, "Пользователь не найден")

    await add_student_to_class(
        actor=current_user,
        school_class=school_class,
        student=student,
        group=body.group,
    )

    return StudentInviteResponse(
        user_id=student.id,
        login=student.login,
        email=student.email,
        class_id=school_class.id,
        group=body.group,
        password_link_sent=False,
    )


@router.patch("/{class_id}/students/{user_id}/group", response_model=StudentInviteResponse)
@min_perms(ROLE_TEACHER)
async def move_group(class_id: int, user_id: int, body: MoveGroupRequest, current_user: User):
    school_class = await get_class_or_404(class_id)
    student = await User.get_or_none(id=user_id)

    if not student:
        raise HTTPException(404, "Пользователь не найден")

    await move_student_group(
        actor=current_user,
        school_class=school_class,
        student=student,
        group=body.group,
    )

    return StudentInviteResponse(
        user_id=student.id,
        login=student.login,
        email=student.email,
        class_id=school_class.id,
        group=body.group,
        password_link_sent=False,
    )


@router.post("/{class_id}/students/{user_id}/transfer", response_model=StudentInviteResponse)
@min_perms(ROLE_TEACHER)
async def transfer(
    class_id: int,
    user_id: int,
    body: TransferStudentRequest,
    current_user: User,
):
    source_class = await get_class_or_404(class_id)
    target_class = await get_class_or_404(body.target_class_id)
    student = await User.get_or_none(id=user_id)

    if not student:
        raise HTTPException(404, "Пользователь не найден")

    await transfer_student(
        actor=current_user,
        source_class=source_class,
        target_class=target_class,
        student=student,
        group=body.group,
    )

    return StudentInviteResponse(
        user_id=student.id,
        login=student.login,
        email=student.email,
        class_id=target_class.id,
        group=body.group,
        password_link_sent=False,
    )


@router.delete("/{class_id}/students/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
@min_perms(ROLE_TEACHER)
async def remove_student(class_id: int, user_id: int, current_user: User):
    school_class = await get_class_or_404(class_id)
    student = await User.get_or_none(id=user_id)

    if not student:
        raise HTTPException(404, "Пользователь не найден")

    await remove_student_from_class(
        actor=current_user,
        school_class=school_class,
        student=student,
    )

    return None


@router.get("/{class_id}/export")
@min_perms(ROLE_TEACHER)
async def export_class(class_id: int, group: int | None = None, current_user: User = None):
    school_class = await get_class_or_404(class_id)
    ensure_can_manage_class(current_user, school_class)

    students = await list_class_students(school_class)

    if group:
        students = [s for s in students if s["group"] == group]

    wb = Workbook()
    ws = wb.active
    ws.title = "students"

    ws.append(["email", "first_name", "last_name", "group"])

    for s in students:
        ws.append([
            s["email"],
            s["first_name"],
            s["last_name"],
            s["group"],
        ])

    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)

    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename=class_{class_id}.xlsx"
        },
    )


@router.post("/{class_id}/import")
@min_perms(settings.OPERATOR_ROLE)
async def import_class(
    class_id: int,
    file: UploadFile = File(...),
    dry_run: bool = False,
    current_user: User = None,
):
    school_class = await get_class_or_404(class_id)
    ensure_can_manage_class(current_user, school_class)

    if not file.filename.endswith(".xlsx"):
        raise HTTPException(400, "Only .xlsx allowed")

    wb = load_workbook(io.BytesIO(await file.read()))
    ws = wb.active

    rows = list(ws.iter_rows(values_only=True))

    if len(rows) < 2:
        raise HTTPException(400, "Empty file")

    header = [h.lower() for h in rows[0]]

    required = {"email", "first_name", "last_name", "group"}
    if not required.issubset(set(header)):
        raise HTTPException(400, f"Missing columns: {required}")

    idx = {k: i for i, k in enumerate(header)}

    parsed = []
    errors = []

    for i, row in enumerate(rows[1:], start=2):
        try:
            item = ClassImportRow(
                email=row[idx["email"]],
                first_name=row[idx["first_name"]],
                last_name=row[idx["last_name"]],
                group=row[idx["group"]],
            )
            parsed.append(item)
        except Exception as e:
            errors.append({"row": i, "error": str(e)})

    if errors:
        return {
            "status": "failed",
            "errors": errors,
        }

    emails = [r.email for r in parsed]
    if len(emails) != len(set(emails)):
        raise HTTPException(400, "Duplicate emails in file")

    if dry_run:
        return {
            "status": "ok",
            "rows": len(parsed),
        }

    created = 0

    async with in_transaction():
        for r in parsed:
            user = await User.get_or_none(email=r.email)

            if not user:
                last_latin = transliterate(r.last_name).capitalize()
                first_initial = transliterate(r.first_name[0]).upper() if r.first_name else ""
                
                base_login = f"{last_latin}{first_initial}"
                generated_login = base_login
                
                counter = 2
                while await User.exists(login=generated_login):
                    generated_login = f"{base_login}{counter}"
                    counter += 1

                user = await User.create(
                    email=r.email,
                    login=generated_login,
                    first_name=r.first_name,
                    last_name=r.last_name,
                    role=1,
                    class_id=school_class.id,
                    class_group=r.group,
                    password_hash="UNSET_PASSWORD_CHOSEN_BY_EMAIL",
                    must_set_password=True,
                )
                
                from auth.password_service import build_password_link, mark_user_must_set_password
                from mail.gmail_service import send_password_email

                raw_token = await mark_user_must_set_password(user)
                link = build_password_link(raw_token)
                try:
                    await send_password_email(
                        to=user.email,
                        subject="Активация аккаунта",
                        greeting=f"Здравствуйте, {user.last_name} {user.first_name}!",
                        link=link,
                    )
                except Exception:
                    pass

            await add_student_to_class(
                actor=current_user,
                school_class=school_class,
                student=user,
                group=r.group,
            )

            created += 1

    return {
        "status": "ok",
        "imported": created,
    }