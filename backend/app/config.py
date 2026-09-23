import os
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_is_vercel = bool(os.environ.get("VERCEL"))


class Settings(BaseSettings):
    app_name: str = "VisuLogic"
    environment: str = "production" if _is_vercel else "development"
    database_url: str = "sqlite:////tmp/visulogic.db" if _is_vercel else "sqlite:///./visulogic.db"
    upload_dir: Path = Path("/tmp/uploads") if _is_vercel else Path("./uploads")
    session_ttl_minutes: int = 15
    max_upload_bytes: int = 8 * 1024 * 1024
    max_image_pixels: int = 24_000_000
    allowed_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://*.vercel.app",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="VISULOGIC_",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
