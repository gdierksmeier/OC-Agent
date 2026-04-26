"""Execution endpoints — run an agent and inspect history."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import execution_engine, models, schemas
from ..database import get_db

router = APIRouter(prefix="/api/executions", tags=["executions"])


@router.get("", response_model=list[schemas.ExecutionOut])
def list_executions(
    agent_id: int | None = None,
    status_filter: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    q = db.query(models.Execution)
    if agent_id is not None:
        q = q.filter(models.Execution.agent_id == agent_id)
    if status_filter:
        q = q.filter(models.Execution.status == status_filter)
    return q.order_by(models.Execution.started_at.desc()).limit(limit).all()


@router.get("/{execution_id}", response_model=schemas.ExecutionDetailOut)
def get_execution(execution_id: int, db: Session = Depends(get_db)):
    ex = db.get(models.Execution, execution_id)
    if not ex:
        raise HTTPException(404, "Execution not found")
    return ex


@router.post("/run/{agent_id}", response_model=schemas.ExecutionDetailOut)
def run_agent(
    agent_id: int,
    payload: schemas.ExecuteAgentRequest,
    db: Session = Depends(get_db),
):
    """Run an agent's published workflow with the supplied input data."""
    agent = db.get(models.Agent, agent_id)
    if not agent:
        raise HTTPException(404, "Agent not found")
    if agent.status == "archived":
        raise HTTPException(400, "Cannot execute archived agent")

    execution = execution_engine.execute_agent(
        db=db,
        agent=agent,
        input_data=payload.input_data,
        user_id=payload.user_id,
    )
    return execution
