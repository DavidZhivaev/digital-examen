from datetime import datetime, timezone
import math
from uuid import UUID
import secrets
import string

from fastapi import APIRouter, HTTPException, Query, status
from tortoise.exceptions import IntegrityError

from auth.password_service import build_password_link, mark_user_must_set_password
from auth.session_service import revoke_all_user_sessions
from mail.gmail_service import send_password_email
from core.config import settings
from core.permissions import min_perms
from classes.models import SchoolClass
from core.security import hash_password
from users.admin_service import validate_admin_can_manage, validate_assignable_role
from users.models import User
from users.role_service import validate_role_change
from core.roles import ROLE_TEACHER, ROLE_STUDENT
from classes.models import SchoolClass
from users.schemas import (
    PaginatedUsersResponse,
    RoleUpdate,
    UserCreate,
    UserResponse,
    UserSelfUpdate,
    UserUpdate,
)

router = APIRouter()

CYRILLIC_TO_LATIN = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo', 'ж': 'zh',
    'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n', 'о': 'o',
    'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u', 'ф': 'f', 'х': 'kh', 'ц': 'ts',
    'ч': 'ch', 'ш': 'sh', 'щ': 'shch', 'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
    'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'Yo', 'Ж': 'Zh',
    'З': 'Z', 'И': 'I', 'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M', 'Н': 'N', 'О': 'O',
    'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U', 'Ф': 'F', 'Х': 'Kh', 'Ц': 'Ts',
    'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Shch', 'Ъ': '', 'Ы': 'Y', 'Ь': '', 'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya'
}

def transliterate(text: str) -> str:
    return "".join(CYRILLIC_TO_LATIN.get(c, c) for c in text)

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

def generate_temp_password(length: int = 10) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))

def user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        person_id=user.person_id,
        email=user.email,
        login=user.login,
        role=user.role,
        register_at=user.register_at,
        class_id=user.class_id,
        class_group=user.class_group,
        must_set_password=user.must_set_password,
        first_name=user.first_name,
        last_name=user.last_name,
        middle_name=user.middle_name,
        sex=user.sex,
        email_accept=user.email_accept,
        last_do=user.last_do,
    )

def generate_temp_password(length: int) -> str:
    alphabet = string.ascii_letters + string.digits + string.punctuation

    password = [
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.digits),
        secrets.choice(string.punctuation),
    ]

    password += [secrets.choice(alphabet) for _ in range(length - 4)]
    secrets.SystemRandom().shuffle(password)

    return "".join(password)

@router.get("/health")
async def health():
    return {"service": "users", "status": "ok"}


@router.get("/me", response_model=UserResponse)
@min_perms(1)
async def get_me(current_user: User):
    return user_response(current_user)


@router.patch("/me", response_model=UserResponse)
@min_perms(1)
async def update_me(body: UserSelfUpdate, current_user: User):
    data = body.model_dump(exclude_unset=True)
    password_changed = "password" in data
    if password_changed:
        data["password_hash"] = hash_password(data.pop("password"))

    if current_user.role == 1 and ("first_name" in data or "last_name" in data or "middle_name" in data or "sex" in data):
        raise HTTPException(status_code=403, detail="Существенные изменения в УЗ могут вносить только сотрудники школы!")

    for field, value in data.items():
        setattr(current_user, field, value)

    current_user.last_do = utcnow()
    await current_user.save()

    if password_changed:
        await revoke_all_user_sessions(current_user.id)

    return user_response(current_user)


@router.get("/", response_model=PaginatedUsersResponse)
@min_perms(settings.ADMIN_ROLE)
async def list_users(
    current_user: User,
    page: int = Query(1, ge=1),
    page_size: int = Query(settings.USERS_PAGE_SIZE_DEFAULT, ge=1, le=settings.USERS_PAGE_SIZE_MAX),
):
    total = await User.all().count()
    pages = max(1, math.ceil(total / page_size)) if total else 1
    offset = (page - 1) * page_size
    users = await User.all().order_by("id").offset(offset).limit(page_size)

    return PaginatedUsersResponse(
        items=[user_response(u) for u in users],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/roles")
@min_perms(1)
async def get_roles(current_user: User):
    return [
        {
            "role_id": 1,
            "name": "Учащийся"
        },
        {
            "role_id": 2,
            "name": "Учитель"
        },
        {
            "role_id": 3,
            "name": "Оператор"
        },
        {
            "role_id": 4,
            "name": "Администратор"
        }
    ]

@router.get("/subsystems")
@min_perms(1)
async def get_me(current_user: User):
    subsystems = []
    k = 1
    for name in ["Работы", "Банк задач", "Настройки", "Контингент", "Рассадка", "Аудитории", "Обработка ЭМ", "Аналитика"]:
        if k < 4:
            subsystems.append({
                "name": name,
                "id": k,
                "min_perms": 1 
            })
        elif k < 6:
            subsystems.append({
                "name": name,
                "id": k,
                "min_perms": 2
            })
        else:
            subsystems.append({
                "name": name,
                "id": k,
                "min_perms": 3
            })
        k += 1

    return {
        "subsystems": subsystems,
        "user_subsystems": [i for i in subsystems if current_user.role >= i["min_perms"]]
    }


@router.get("/{person_id}", response_model=UserResponse)
@min_perms(settings.ADMIN_ROLE)
async def get_user(person_id: UUID, current_user: User):
    user = await User.get_or_none(person_id=str(person_id))
    if user is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    validate_admin_can_manage(current_user, user)
    return user_response(user)


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@min_perms(ROLE_TEACHER)
async def create_user(body: UserCreate, current_user: User):
    if current_user.role == ROLE_TEACHER:
        if body.role != ROLE_STUDENT:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Учитель может создавать только учеников"
            )

        school_class = await SchoolClass.get_or_none(id=body.class_id)

        if not school_class or school_class.teacher_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Можно создавать учеников только в своём классе"
            )

        body.class_group = body.class_group

    else:
        validate_assignable_role(current_user, body.role)

    last_latin = transliterate(body.last_name).capitalize()
    first_initial = transliterate(body.first_name[0]).upper()
    middle_initial = transliterate(body.middle_name[0]).upper() if body.middle_name else ""

    base_login = f"{last_latin}{first_initial}{middle_initial}"
    generated_login = base_login

    counter = 2
    while await User.exists(login=generated_login):
        generated_login = f"{base_login}{counter}"
        counter += 1

    data = body.model_dump()

    if body.role != ROLE_STUDENT:
        data["class_id"] = None
        data["class_group"] = None

    data["login"] = generated_login

    temp_password = generate_temp_password(12)
    data["password_hash"] = hash_password(temp_password)
    data["must_set_password"] = False

    try:
        user = await User.create(**data)
    except IntegrityError:
        raise HTTPException(
            status_code=409,
            detail="Пользователь с таким email уже существует",
        )

    raw_token = await mark_user_must_set_password(user)
    link = build_password_link(raw_token)

    school_class = await SchoolClass.get_or_none(id=body.class_id)

    class_label = ""
    if school_class and body.role == ROLE_STUDENT:
        class_label = f"{school_class.parallel}{school_class.litera}-{body.class_group}"

    try:
        await send_password_email(
            to=user.email,
            subject="Создана новая учетная запись!",
            greeting=f"Здравствуйте, {user.last_name} {user.first_name}!",
            message=(
                f"Вам создана учетная запись.\n\n"
                f"Роль: ученик\n"
                f"Класс: {class_label}\n\n"
                f"Логин: {user.login}\n"
                f"Создал: {current_user.login}"
                f"Временный пароль: {temp_password}\n\n"
                f"Рекомендуем изменить временный пароль! Ссылку для смены прикрепили к письму."
            ),
            link=link
        )
    except Exception:
        raise HTTPException(
            status_code=201,
            detail=f"Пользователь создан (логин: {user.login}), но письмо не отправлено",
        )

    return user_response(user)

@router.patch("/{person_id}/role", response_model=UserResponse)
@min_perms(settings.ADMIN_ROLE)
async def update_user_role(person_id: UUID, body: RoleUpdate, current_user: User):
    user = await User.get_or_none(person_id=str(person_id))
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")

    await validate_role_change(current_user, user, body.role)

    if user.role != body.role:
        user.role = body.role
        user.last_do = utcnow()
        await user.save(update_fields=["role", "last_do"])
        await revoke_all_user_sessions(user.id)

    return user_response(user)


@router.patch("/{person_id}", response_model=UserResponse)
@min_perms(settings.ADMIN_ROLE)
async def update_user(person_id: UUID, body: UserUpdate, current_user: User):
    user = await User.get_or_none(person_id=str(person_id))
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")

    validate_admin_can_manage(current_user, user)

    data = body.model_dump(exclude_unset=True)
    password_changed = "password" in data
    role_changed = "role" in data

    if role_changed:
        await validate_role_change(current_user, user, data["role"])

    if "role" in data:
        validate_assignable_role(current_user, data["role"])

    if password_changed:
        data["password_hash"] = hash_password(data.pop("password"))

    for field, value in data.items():
        setattr(user, field, value)

    user.last_do = utcnow()
    try:
        await user.save()
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Пользователь с таким email или логином уже существует",
        )

    if password_changed or role_changed:
        await revoke_all_user_sessions(user.id)

    return user_response(user)


@router.post("/{person_id}/force-password-reset")
@min_perms(settings.OPERATOR_ROLE)
async def force_password_reset(person_id: UUID, current_user: User):
    user = await User.get_or_none(person_id=str(person_id))
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")

    raw_token = await mark_user_must_set_password(user)
    await revoke_all_user_sessions(user.id)

    link = build_password_link(raw_token)
    try:
        await send_password_email(
            to=user.email,
            subject="Смена пароля",
            greeting=f"Здравствуйте, {user.last_name} {user.first_name}!",
            link=link,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Не удалось отправить письмо: {exc}",
        )

    return {"detail": "Ссылка на смену пароля отправлена", "email": user.email}


@router.delete("/{person_id}", status_code=status.HTTP_204_NO_CONTENT)
@min_perms(settings.ADMIN_ROLE)
async def delete_user(person_id: UUID, current_user: User):
    user = await User.get_or_none(person_id=str(person_id))
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")
    
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя удалить собственную учётную запись!",
        )

    user = await User.get_or_none(id=user.id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")

    validate_admin_can_manage(current_user, user)

    if user.role >= settings.ADMIN_ROLE:
        admin_count = await User.filter(role__gte=settings.ADMIN_ROLE).count()
        if admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Нельзя удалить последнего администратора!",
            )

    await revoke_all_user_sessions(user.id)
    await user.delete()
    return None
