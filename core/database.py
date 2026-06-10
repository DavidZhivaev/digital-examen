from tortoise.contrib.fastapi import register_tortoise
from core.config import DB_URL

def init_db(app):
    register_tortoise(
        app,
        db_url=DB_URL,
        modules={"models": ["services.users.models", "services.auth.models"]},
        generate_schemas=True,
        add_exception_handlers=True,
    )