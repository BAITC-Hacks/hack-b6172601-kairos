"""Application entry point.

Run locally:   uvicorn app.main:app --reload
Run in Docker: docker compose up --build
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import app.tools  # noqa: F401 - registers tools on import
from app.api.routes import router
from app.api.viewer import router as viewer_router, snapshot
from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.core.logging import setup_logging

settings = get_settings()
setup_logging(settings.log_level)

@asynccontextmanager
async def lifespan(app):
    snapshot()
    yield


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

register_error_handlers(app)
app.include_router(router, prefix="/api")
app.include_router(viewer_router, prefix="/api")
app.mount("/", StaticFiles(directory="static", html=True), name="static")
