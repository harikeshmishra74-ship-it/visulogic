from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "VisuLogic"
    environment: str = "development"
    database_url: str = "sqlite:///./visulogic.db"
    upload_dir: Path = Path("./uploads")
    session_ttl_minutes: int = 15
    max_upload_bytes: int = 8 * 1024 * 1024
    max_image_pixels: int = 24_000_000
    allowed_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="VISULOGIC_",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
