from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from analytics.routers import router as analytics_router
from classes.routers import router as classes_router
from auth.routers import router as auth_router
from core.audit import AuthAuditMiddleware
from core.config import settings
from core.database import init_db
from core.logging_config import setup_logging
from core.middleware import AuthRequestLoggingMiddleware, SecurityHeadersMiddleware
from core.rate_limit import RateLimitMiddleware
from mail.routers import router as mail_router
from users.routers import router as users_router
from rooms.routers import router as rooms_router
from seating.routers import router as seating_router
from subjects.routers import router as subjects_router
from tasks.routers import router as tasks_router
from files.routers import router as files_router
from works.routers import router as works_router

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG,
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
)

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(AuthRequestLoggingMiddleware)
app.add_middleware(AuthAuditMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL] if not settings.DEBUG else ["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RateLimitMiddleware)

app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(users_router, prefix="/api/users", tags=["users"])
app.include_router(classes_router, prefix="/api/classes", tags=["classes"])
app.include_router(tasks_router, prefix="/api/tasks", tags=["tasks"])
app.include_router(works_router, prefix="/api/works", tags=["works"])
app.include_router(files_router, prefix="/api/files", tags=["files"])
app.include_router(analytics_router, prefix="/api/analytics", tags=["analytics"])
app.include_router(mail_router, prefix="/api/mail", tags=["mail"])
app.include_router(rooms_router, prefix="/api/classrooms", tags=["classrooms"])
app.include_router(subjects_router, prefix="/api/subjects", tags=["subjects"])
app.include_router(seating_router, prefix="/api/seating", tags=["seating"])

init_db(app)


@app.get("/api/health")
async def health():
    return {"status": "ok", "app": settings.APP_NAME}


if __name__ == "__main__":
    # dev port
    uvicorn.run(app, port=5001)
