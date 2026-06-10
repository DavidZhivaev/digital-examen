from fastapi import FastAPI
from core.database import init_db

from services.users.routers import router as users_router
from services.auth.routers import router as auth_router

app = FastAPI()

app.include_router(users_router, prefix="/api/users")
app.include_router(auth_router, prefix="/api/auth")

init_db(app)