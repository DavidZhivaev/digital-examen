from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from analytics.routers import router as analytics_router
from auth.routers import router as auth_router
from core.config import settings
from core.database import init_db
from mail.routers import router as mail_router
from users.routers import router as users_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(users_router, prefix="/api/users", tags=["users"])
app.include_router(analytics_router, prefix="/api/analytics", tags=["analytics"])
app.include_router(mail_router, prefix="/api/mail", tags=["mail"])

init_db(app)


@app.get("/api/health")
async def health():
    return {"status": "ok", "app": settings.APP_NAME}
