from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )

    APP_NAME: str = "Школа 1580"
    DEBUG: bool = True

    DB_URL: str = "sqlite://db.sqlite3"

    ALGORITHM: str = "RS256"
    JWT_ISSUER: str = "digital-examen"
    JWT_AUDIENCE: str = "digital-examen-api"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    MAX_SESSIONS_PER_USER: int = 5

    PRIVATE_KEY_PATH: str = "keys/private.pem"
    PUBLIC_KEY_PATH: str = "keys/public.pem"

    BCRYPT_ROUNDS: int = 12

    LOGIN_RATE_LIMIT_MAX_ATTEMPTS: int = 10
    LOGIN_RATE_LIMIT_WINDOW_SECONDS: int = 60

    USERS_PAGE_SIZE_DEFAULT: int = 20
    USERS_PAGE_SIZE_MAX: int = 100

    API_PORT: int = 8000

    # role >= ADMIN_ROLE — администратор
    ADMIN_ROLE: int = 4


settings = Settings()
