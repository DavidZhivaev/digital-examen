from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Школа 1580"
    DEBUG: bool = True

    DB_URL: str = "sqlite://db.sqlite3"

    ALGORITHM: str = "RS256"

    ACCESS_TOKEN_EXPIRE_DAYS: int = 3
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    PRIVATE_KEY_PATH: str = "keys/private.pem"
    PUBLIC_KEY_PATH: str = "keys/public.pem"

    # role >= 5 — администратор
    ADMIN_ROLE: int = 5

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
