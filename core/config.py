from pydantic_settings import BaseSettings, SettingsConfigDict

from core.roles import ROLE_ADMIN, ROLE_OPERATOR, ROLE_STUDENT, ROLE_TEACHER


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )

    APP_NAME: str = "Школа 1580"
    DEBUG: bool = True
    FRONTEND_URL: str = "http://localhost:3000"

    DB_URL: str = "sqlite://db.sqlite3"

    ALGORITHM: str = "RS256"
    JWT_ISSUER: str = "digital-examen"
    JWT_AUDIENCE: str = "digital-examen-api"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    MAX_SESSIONS_PER_USER: int = 5
    PASSWORD_TOKEN_EXPIRE_HOURS: int = 72

    PRIVATE_KEY_PATH: str = "keys/private.pem"
    PUBLIC_KEY_PATH: str = "keys/public.pem"

    BCRYPT_ROUNDS: int = 12

    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_IP_MAX_REQUESTS: int = 10_000
    RATE_LIMIT_IP_WINDOW_SECONDS: int = 60
    RATE_LIMIT_USER_MAX_REQUESTS: int = 3_000
    RATE_LIMIT_USER_WINDOW_SECONDS: int = 60

    LOGIN_RATE_LIMIT_MAX_ATTEMPTS: int = 60
    LOGIN_RATE_LIMIT_WINDOW_SECONDS: int = 60

    USERS_PAGE_SIZE_DEFAULT: int = 20
    USERS_PAGE_SIZE_MAX: int = 100

    API_PORT: int = 8000

    STUDENT_ROLE: int = ROLE_STUDENT
    TEACHER_ROLE: int = ROLE_TEACHER
    OPERATOR_ROLE: int = ROLE_OPERATOR
    ADMIN_ROLE: int = ROLE_ADMIN

    GMAIL_ENABLED: bool = False
    GMAIL_EMAIL: str = ""
    GMAIL_APP_PASSWORD: str = ""
    GMAIL_SMTP_HOST: str = "smtp.gmail.com"
    GMAIL_SMTP_PORT: int = 587
    GMAIL_IMAP_HOST: str = "imap.gmail.com"
    GMAIL_IMAP_PORT: int = 993
    GMAIL_FROM_NAME: str = "Школа 1580"

    WORK_TYPES_PATH: str = "works/work_types.json"


settings = Settings()
