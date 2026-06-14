from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    APP_NAME: str = "C2P Platform API"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True

    API_V1_PREFIX: str = "/api/v1"

    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/c2p_platform"

    SECRET_KEY: str = "your-super-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30 * 24 * 60

    BCRYPT_ROUNDS: int = 12

    # File storage
    UPLOAD_DIR: str = "uploads/contracts"
    INVOICES_UPLOAD_DIR: str = "uploads/invoices"
    MAX_FILE_SIZE_MB: int = 20


@lru_cache
def get_settings() -> Settings:
    return Settings()