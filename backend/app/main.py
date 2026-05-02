"""
AI Agent Generation & Maintenance System — FastAPI entrypoint.

Run with:  uvicorn app.main:app --reload --port 8000
"""
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from . import models  # noqa: F401  (register tables)
from .database import Base, SessionLocal, engine
from .routers import (
    agents, ai_models, dashboard, endpoints, environment_settings, executions, prompts, system, workflows,
)
from .routers.system import BACKEND_VERSION
from .seed import seed_if_empty


def _ensure_task_columns():
    """Lightweight forward migrations for columns added after the initial schema.
    Idempotent: ignores 'duplicate column' errors so it's safe to run on every boot.
    """
    additions = [
        ("tasks", "condition", "TEXT"),
    ]
    with engine.begin() as conn:
        for table, column, coltype in additions:
            try:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}"))
            except Exception:
                # Column already exists, or table not yet created (create_all will handle).
                pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    _ensure_task_columns()
    db = SessionLocal()
    try:
        seed_if_empty(db)
    finally:
        db.close()
    app.state.started_at = datetime.now(timezone.utc)
    yield


app = FastAPI(
    title="AI Agent Generation & Maintenance System",
    description=(
        "A controlled platform for defining, building, versioning, deploying, "
        "and monitoring AI agents through configuration."
    ),
    version=BACKEND_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "name": "AI Agent Generation & Maintenance System",
        "version": BACKEND_VERSION,
        "docs": "/docs",
    }


@app.get("/api/health")
def health():
    return {"status": "ok"}


app.include_router(agents.router)
app.include_router(workflows.router)
app.include_router(endpoints.router)
app.include_router(ai_models.router)
app.include_router(prompts.router)
app.include_router(executions.router)
app.include_router(dashboard.router)
app.include_router(environment_settings.router)
app.include_router(system.router)
