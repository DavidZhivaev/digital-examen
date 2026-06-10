from fastapi import APIRouter, HTTPException, status

from classes.models import SchoolClass
from classes.permissions import ensure_can_manage_class, is_homeroom_teacher, is_operator_or_above
from classes.schemas import (
    AddExistingStudentRequest,
    AssignTeacherRequest,
    ClassCreate,
    ClassResponse,
    ClassStudentResponse,
    ClassUpdate,
    MoveGroupRequest,
    StudentInviteRequest,
    StudentInviteResponse,
    TransferStudentRequest,
)
from classes.service import (
    _class_to_response,
    add_existing_student,
    assign_teacher,
    create_class,
    delete_class,
    get_class_or_404,
    invite_student,
    list_class_students,
    move_student_group,
    remove_student_from_class,
    transfer_student,
    unassign_teacher,
    update_class_fields,
)
from core.config import settings
from core.permissions import min_perms
from core.roles import ROLE_TEACHER
from users.models import User

router = APIRouter()


def _ensure_homeroom_or_operator(user: User, school_class: SchoolClass) -> None:
    if is_operator_or_above(user):
        return
    if not is_homeroom_teacher(user, school_class):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступно только классному руководителю этого класса или оператору",
        )


@router.get("/health")
async def health():
    return {"service": "classes", "status": "ok"}


# --- CRUD класса ---

@router.get("/", response_model=list[ClassResponse])
@min_perms(ROLE_TEACHER)
async def list_classes(current_user: User):
    if is_operator_or_above(current_user):
        classes = await SchoolClass.all().order_by("corpus", "parallel", "litera")
    else:
        classes = await SchoolClass.filter(teacher_id=current_user.id).order_by("corpus", "parallel", "litera")
    return [_class_to_response(c) for c in classes]


@router.post("/", response_model=ClassResponse, status_code=status.HTTP_201_CREATED)
@min_perms(settings.OPERATOR_ROLE)
async def create_class_endpoint(body: ClassCreate, current_user: User):
    school_class = await create_class(
        parallel=body.parallel,
        litera=body.litera,
        corpus=body.corpus,
        teacher_id=body.teacher_id,
    )
    return _class_to_response(school_class)


@router.get("/{class_id}", response_model=ClassResponse)
@min_perms(ROLE_TEACHER)
async def get_class(class_id: int, current_user: User):
    school_class = await get_class_or_404(class_id)
    ensure_can_manage_class(current_user, school_class)
    return _class_to_response(school_class)


@router.patch("/{class_id}", response_model=ClassResponse)
@min_perms(ROLE_TEACHER)
async def update_class(class_id: int, body: ClassUpdate, current_user: User):
    school_class = await get_class_or_404(class_id)
    ensure_can_manage_class(current_user, school_class)
    school_class = await update_class_fields(school_class, body.model_dump(exclude_unset=True))
    return _class_to_response(school_class)


@router.delete("/{class_id}", status_code=status.HTTP_204_NO_CONTENT)
@min_perms(settings.OPERATOR_ROLE)
async def delete_class_endpoint(class_id: int, current_user: User):
    school_class = await get_class_or_404(class_id)
    await delete_class(school_class)
    return None


# --- Классный руководитель ---

@router.patch("/{class_id}/teacher", response_model=ClassResponse)
@min_perms(settings.OPERATOR_ROLE)
async def set_class_teacher(class_id: int, body: AssignTeacherRequest, current_user: User):
    school_class = await get_class_or_404(class_id)
    school_class = await assign_teacher(school_class, body.teacher_id)
    return _class_to_response(school_class)


@router.delete("/{class_id}/teacher", response_model=ClassResponse)
@min_perms(settings.OPERATOR_ROLE)
async def remove_class_teacher(class_id: int, current_user: User):
    school_class = await get_class_or_404(class_id)
    school_class = await unassign_teacher(school_class)
    return _class_to_response(school_class)


# --- Ученики класса ---

@router.get("/{class_id}/students", response_model=list[ClassStudentResponse])
@min_perms(ROLE_TEACHER)
async def get_class_students(class_id: int, current_user: User):
    school_class = await get_class_or_404(class_id)
    ensure_can_manage_class(current_user, school_class)
    students = await list_class_students(school_class)
    return [ClassStudentResponse.model_validate(s) for s in students]


@router.post("/{class_id}/students/invite", response_model=StudentInviteResponse, status_code=status.HTTP_201_CREATED)
@min_perms(ROLE_TEACHER)
async def invite_class_student(class_id: int, body: StudentInviteRequest, current_user: User):
    school_class = await get_class_or_404(class_id)
    _ensure_homeroom_or_operator(current_user, school_class)

    user, link_sent = await invite_student(
        actor=current_user,
        school_class=school_class,
        email=body.email,
        first_name=body.first_name,
        last_name=body.last_name,
        middle_name=body.middle_name,
        sex=body.sex,
        group=body.group,
    )
    return StudentInviteResponse(
        user_id=user.id,
        login=user.login,
        email=user.email,
        class_id=school_class.id,
        group=body.group,
        password_link_sent=link_sent,
    )


@router.post("/{class_id}/students", response_model=StudentInviteResponse)
@min_perms(ROLE_TEACHER)
async def add_student_to_class(class_id: int, body: AddExistingStudentRequest, current_user: User):
    school_class = await get_class_or_404(class_id)
    _ensure_homeroom_or_operator(current_user, school_class)

    user = await add_existing_student(
        actor=current_user,
        school_class=school_class,
        user_id=body.user_id,
        group=body.group,
    )
    return StudentInviteResponse(
        user_id=user.id,
        login=user.login,
        email=user.email,
        class_id=school_class.id,
        group=body.group,
        password_link_sent=False,
    )


@router.delete("/{class_id}/students/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
@min_perms(ROLE_TEACHER)
async def remove_student_from_class_endpoint(class_id: int, user_id: int, current_user: User):
    school_class = await get_class_or_404(class_id)
    _ensure_homeroom_or_operator(current_user, school_class)
    await remove_student_from_class(actor=current_user, school_class=school_class, user_id=user_id)
    return None


@router.patch("/{class_id}/students/{user_id}/group", response_model=StudentInviteResponse)
@min_perms(ROLE_TEACHER)
async def move_student_between_groups(class_id: int, user_id: int, body: MoveGroupRequest, current_user: User):
    school_class = await get_class_or_404(class_id)
    _ensure_homeroom_or_operator(current_user, school_class)

    user = await move_student_group(
        actor=current_user,
        school_class=school_class,
        user_id=user_id,
        group=body.group,
    )
    return StudentInviteResponse(
        user_id=user.id,
        login=user.login,
        email=user.email,
        class_id=school_class.id,
        group=body.group,
        password_link_sent=False,
    )


@router.post("/{class_id}/students/{user_id}/transfer", response_model=StudentInviteResponse)
@min_perms(ROLE_TEACHER)
async def transfer_class_student(
    class_id: int,
    user_id: int,
    body: TransferStudentRequest,
    current_user: User,
):
    source_class = await get_class_or_404(class_id)
    _ensure_homeroom_or_operator(current_user, source_class)

    target_class = await get_class_or_404(body.target_class_id)
    student = await User.get_or_none(id=user_id)
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")

    user = await transfer_student(
        actor=current_user,
        source_class=source_class,
        student=student,
        target_class=target_class,
        group=body.group,
    )
    return StudentInviteResponse(
        user_id=user.id,
        login=user.login,
        email=user.email,
        class_id=target_class.id,
        group=body.group,
        password_link_sent=False,
    )
