import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import analysis, health, query, scan, upload
from app.config import get_settings
from app.db import init_db


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.1.0")
    dev_origin_regex = (
        r"https?://.*"
        if (settings.environment == "development" or os.environ.get("VERCEL"))
        else None
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_origin_regex=dev_origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    def on_startup() -> None:
        settings.upload_dir.mkdir(parents=True, exist_ok=True)
        init_db()

    app.include_router(health.router, prefix="/api")
    app.include_router(scan.router, prefix="/api")
    app.include_router(upload.router, prefix="/api")
    app.include_router(analysis.router, prefix="/api")
    app.include_router(query.router, prefix="/api")
    return app


app = create_app()
