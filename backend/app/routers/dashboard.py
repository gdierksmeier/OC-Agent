"""KPI dashboard and cost validation endpoints (§7)."""
from collections import defaultdict
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/kpis", response_model=schemas.DashboardKPIs)
def get_kpis(days: int = 30, db: Session = Depends(get_db)):
    cutoff = datetime.utcnow() - timedelta(days=days)

    execs = (
        db.query(models.Execution)
        .filter(models.Execution.started_at >= cutoff)
        .all()
    )
    total = len(execs)
    success = sum(1 for e in execs if e.status == "success")
    failed = sum(1 for e in execs if e.status == "failed")
    escalated = sum(1 for e in execs if e.status == "escalated")
    schema_ok = sum(1 for e in execs if e.schema_compliant)
    avg_latency = (sum(e.total_latency_ms for e in execs) / total) if total else 0
    total_cost = sum(e.total_cost or 0 for e in execs)
    total_tokens = sum((e.total_tokens_input or 0) + (e.total_tokens_output or 0) for e in execs)

    # Endpoint failure rate from execution steps
    steps = (
        db.query(models.ExecutionStep)
        .filter(models.ExecutionStep.started_at >= cutoff)
        .all()
    )
    endpoint_steps = [s for s in steps if s.step_type in ("call_endpoint", "retrieve")]
    endpoint_fails = sum(1 for s in endpoint_steps if s.status == "failed")
    endpoint_failure_rate = (
        endpoint_fails / len(endpoint_steps) if endpoint_steps else 0
    )

    model_steps = [s for s in steps if s.step_type in ("call_model", "generate")]
    model_fails = sum(1 for s in model_steps if s.status == "failed")
    model_failure_rate = model_fails / len(model_steps) if model_steps else 0

    return schemas.DashboardKPIs(
        total_executions=total,
        success_rate=(success / total) if total else 0,
        average_latency_ms=avg_latency,
        endpoint_failure_rate=endpoint_failure_rate,
        model_failure_rate=model_failure_rate,
        human_escalation_rate=(escalated / total) if total else 0,
        schema_compliance_rate=(schema_ok / total) if total else 0,
        total_cost=total_cost,
        total_tokens=total_tokens,
        cost_per_successful_run=(total_cost / success) if success else 0,
        active_agents=db.query(models.Agent)
            .filter(models.Agent.status.in_(["test", "review", "published"]))
            .count(),
        active_endpoints=db.query(models.Endpoint)
            .filter(models.Endpoint.is_active.is_(True))
            .count(),
        active_models=db.query(models.AIModel)
            .filter(models.AIModel.status == "active")
            .count(),
    )


@router.get("/cost-summary", response_model=schemas.CostSummary)
def cost_summary(days: int = 30, db: Session = Depends(get_db)):
    cutoff = datetime.utcnow() - timedelta(days=days)

    records = (
        db.query(models.CostRecord)
        .filter(models.CostRecord.recorded_at >= cutoff)
        .all()
    )

    total_cost = sum(r.cost or 0 for r in records)

    # By model
    by_model_map: dict[int | None, float] = defaultdict(float)
    for r in records:
        by_model_map[r.model_id] += r.cost or 0
    by_model = []
    for mid, cost in sorted(by_model_map.items(), key=lambda x: -x[1]):
        m = db.get(models.AIModel, mid) if mid else None
        by_model.append({"model": m.name if m else "(orchestration)", "cost": round(cost, 6)})

    # By agent
    by_agent_map: dict[int | None, float] = defaultdict(float)
    for r in records:
        by_agent_map[r.agent_id] += r.cost or 0
    by_agent = []
    for aid, cost in sorted(by_agent_map.items(), key=lambda x: -x[1]):
        a = db.get(models.Agent, aid) if aid else None
        by_agent.append({"agent": a.name if a else "(unknown)", "cost": round(cost, 6)})

    # By environment
    by_env_map: dict[str, float] = defaultdict(float)
    for r in records:
        by_env_map[r.environment or "unknown"] += r.cost or 0
    by_environment = [
        {"environment": k, "cost": round(v, 6)}
        for k, v in sorted(by_env_map.items(), key=lambda x: -x[1])
    ]

    # Daily trend
    daily_map: dict[str, float] = defaultdict(float)
    for r in records:
        day = r.recorded_at.date().isoformat()
        daily_map[day] += r.cost or 0
    daily_trend = [
        {"date": k, "cost": round(v, 6)}
        for k, v in sorted(daily_map.items())
    ]

    return schemas.CostSummary(
        total_cost=round(total_cost, 6),
        by_model=by_model,
        by_agent=by_agent,
        by_environment=by_environment,
        daily_trend=daily_trend,
    )


@router.get("/budgets", response_model=list[schemas.BudgetOut])
def list_budgets(db: Session = Depends(get_db)):
    return db.query(models.Budget).order_by(models.Budget.created_at.desc()).all()


@router.post("/budgets", response_model=schemas.BudgetOut)
def create_budget(payload: schemas.BudgetCreate, db: Session = Depends(get_db)):
    b = models.Budget(**payload.model_dump())
    db.add(b)
    db.commit()
    db.refresh(b)
    return b
