"""
AI Agent Generation & Maintenance System — FastAPI entrypoint.

Run with:  uvicorn app.main:app --reload --port 8000
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import models  # noqa: F401  (register tables)
from .database import Base, SessionLocal, engine
from .routers import (
    agents, ai_models, dashboard, endpoints, environment_settings, executions, prompts, workflows,
)
from .seed import seed_if_empty


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_if_empty(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title="AI Agent Generation & Maintenance System",
    description=(
        "A controlled platform for defining, building, versioning, deploying, "
        "and monitoring AI agents through configuration."
    ),
    version="0.1.0",
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
        "version": "0.1.0",
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
