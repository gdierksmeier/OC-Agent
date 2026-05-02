"""System / about info — version, uptime, and runtime stats."""
import platform
import sys
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db

router = APIRouter(prefix="/api/system", tags=["system"])

BACKEND_VERSION = "0.3.0"
BACKEND_BUILD_NAME = "Conditional Branching"
BACKEND_RELEASE_DATE = "2026-05-02"


def _backend_dependency(name: str) -> str | None:
    try:
        mod = __import__(name)
        return getattr(mod, "__version__", None) or getattr(mod, "VERSION", None)
    except Exception:
        return None


@router.get("/info")
def get_system_info(request: Request, db: Session = Depends(get_db)):
    started_at: datetime | None = getattr(request.app.state, "started_at", None)
    uptime_seconds = (
        (datetime.now(timezone.utc) - started_at).total_seconds()
        if started_at else None
    )

    counts = {
        "agents": db.query(models.Agent).count(),
        "workflows": db.query(models.Workflow).count(),
        "endpoints": db.query(models.Endpoint).count(),
        "models": db.query(models.AIModel).count(),
        "prompts": db.query(models.Prompt).count(),
        "executions": db.query(models.Execution).count(),
    }

    return {
        "name": "AI Agent Generation & Maintenance System",
        "short_name": "Agent Factory",
        "version": BACKEND_VERSION,
        "build_name": BACKEND_BUILD_NAME,
        "release_date": BACKEND_RELEASE_DATE,
        "phase": "Phase 1 Foundation",
        "stack": {
            "python": platform.python_version(),
            "fastapi": _backend_dependency("fastapi"),
            "sqlalchemy": _backend_dependency("sqlalchemy"),
            "pydantic": _backend_dependency("pydantic"),
            "platform": f"{platform.system()} {platform.release()}",
            "interpreter": sys.executable,
        },
        "started_at": started_at.isoformat() if started_at else None,
        "uptime_seconds": uptime_seconds,
        "counts": counts,
        "links": {
            "api_docs": "/docs",
            "repository": "https://github.com/gdierksmeier/OC-Agent",
        },
    }
