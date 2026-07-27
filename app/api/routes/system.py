from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.version import APP_VERSION
from app.storage.db import check_database

router = APIRouter(tags=["system"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
def ready() -> JSONResponse:
    if check_database():
        return JSONResponse({"status": "ready", "database": "ok"})
    return JSONResponse(
        {"status": "not_ready", "database": "unavailable"},
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    )


@router.get("/version")
def version() -> dict[str, str]:
    settings = get_settings()
    return {
        "application_version": APP_VERSION,
        "git_commit": settings.git_commit,
        "build_time": settings.build_time,
        "environment": settings.env,
    }
