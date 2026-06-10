from tortoise.contrib.fastapi import register_tortoise

from core.config import settings


def init_db(app):
    register_tortoise(
        app,
        db_url=settings.DB_URL,
        modules={"models": ["users.models", "auth.models", "classes.models"]},
        generate_schemas=True,
        add_exception_handlers=True,
    )
