"""Создание первого администратора. Запуск: python -m scripts.create_admin"""

import asyncio

from tortoise import Tortoise

from core.config import settings
from core.security import hash_password
from users.models import User


async def main():
    await Tortoise.init(
        db_url=settings.DB_URL,
        modules={"models": ["users.models", "auth.models"]},
    )
    await Tortoise.generate_schemas()

    login = input("Логин администратора: ").strip()
    password = input("Пароль (мин. 8 символов, буквы и цифры): ").strip()
    if len(password) < 8 or not any(c.isalpha() for c in password) or not any(c.isdigit() for c in password):
        print("Пароль не соответствует требованиям безопасности")
        return
    email = input("Email: ").strip()
    first_name = input("Фамилия: ").strip()
    last_name = input("Имя: ").strip()

    user = await User.create(
        login=login,
        password_hash=hash_password(password),
        email=email,
        first_name=first_name,
        last_name=last_name,
        role=settings.ADMIN_ROLE,
    )
    print(f"Администратор создан: id={user.id}, person_id={user.person_id}")
    await Tortoise.close_connections()


if __name__ == "__main__":
    asyncio.run(main())
