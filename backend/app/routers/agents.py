"""Agents CRUD + lifecycle (draft → test → review → published → archived)."""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.get("", response_model=list[schemas.AgentOut])
def list_agents(
    skip: int = 0,
    limit: int = 200,
    status_filter: str | None = None,
    environment: str | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(models.Agent)
    if status_filter:
        q = q.filter(models.Agent.status == status_filter)
    if environment:
        q = q.filter(models.Agent.environment == environment)
    return q.order_by(models.Agent.updated_at.desc()).offset(skip).limit(limit).all()


@router.post("", response_model=schemas.AgentOut, status_code=status.HTTP_201_CREATED)
def create_agent(payload: schemas.AgentCreate, db: Session = Depends(get_db)):
    agent = models.Agent(**payload.model_dump())
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


@router.get("/{agent_id}", response_model=schemas.AgentDetailOut)
def get_agent(agent_id: int, db: Session = Depends(get_db)):
    agent = db.get(models.Agent, agent_id)
    if not agent:
        raise HTTPException(404, "Agent not found")
    return agent


@router.patch("/{agent_id}", response_model=schemas.AgentOut)
def update_agent(
    agent_id: int, payload: schemas.AgentUpdate, db: Session = Depends(get_db)
):
    agent = db.get(models.Agent, agent_id)
    if not agent:
        raise HTTPException(404, "Agent not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(agent, k, v)
    db.commit()
    db.refresh(agent)
    return agent


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_agent(agent_id: int, db: Session = Depends(get_db)):
    agent = db.get(models.Agent, agent_id)
    if not agent:
        raise HTTPException(404, "Agent not found")
    db.delete(agent)
    db.commit()


@router.post("/{agent_id}/clone", response_model=schemas.AgentOut)
def clone_agent(agent_id: int, db: Session = Depends(get_db)):
    src = db.get(models.Agent, agent_id)
    if not src:
        raise HTTPException(404, "Agent not found")
    clone = models.Agent(
        name=f"{src.name} (clone)",
        description=src.description,
        objective=src.objective,
        business_domain=src.business_domain,
        owner_id=src.owner_id,
        environment="dev",
        status="draft",
        system_prompt=src.system_prompt,
        business_instructions=src.business_instructions,
        constraints=src.constraints,
        response_format=src.response_format,
        fallback_behavior=src.fallback_behavior,
        input_schema=src.input_schema,
        output_schema=src.output_schema,
        default_model_id=src.default_model_id,
    )
    db.add(clone)
    db.commit()
    db.refresh(clone)
    return clone


@router.post("/{agent_id}/snapshot", response_model=schemas.AgentVersionOut)
def snapshot_agent(
    agent_id: int,
    changelog: str | None = None,
    db: Session = Depends(get_db),
):
    agent = db.get(models.Agent, agent_id)
    if not agent:
        raise HTTPException(404, "Agent not found")

    snapshot_payload = {
        "agent": {c.name: getattr(agent, c.name) for c in agent.__table__.columns},
        "workflows": [
            {
                "id": w.id,
                "name": w.name,
                "version": w.version,
                "tasks": [
                    {
                        "name": t.name,
                        "task_type": t.task_type,
                        "order_index": t.order_index,
                        "config": t.config,
                        "depends_on": t.depends_on,
                        "endpoint_id": t.endpoint_id,
                        "model_id": t.model_id,
                        "prompt_id": t.prompt_id,
                    }
                    for t in w.tasks
                ],
            }
            for w in agent.workflows
        ],
    }
    # JSON-safe (drop datetimes)
    snapshot_payload["agent"] = {
        k: (v.isoformat() if isinstance(v, datetime) else v)
        for k, v in snapshot_payload["agent"].items()
    }

    new_version = (agent.current_version or 0) + 1
    version = models.AgentVersion(
        agent_id=agent.id,
        version=new_version,
        snapshot=snapshot_payload,
        changelog=changelog,
        status=agent.status,
    )
    agent.current_version = new_version
    db.add(version)
    db.commit()
    db.refresh(version)
    return version


@router.get("/{agent_id}/versions", response_model=list[schemas.AgentVersionOut])
def list_versions(agent_id: int, db: Session = Depends(get_db)):
    return (
        db.query(models.AgentVersion)
        .filter(models.AgentVersion.agent_id == agent_id)
        .order_by(models.AgentVersion.version.desc())
        .all()
    )


@router.post("/{agent_id}/transition", response_model=schemas.AgentOut)
def transition_status(
    agent_id: int,
    new_status: str,
    db: Session = Depends(get_db),
):
    """Move agent through draft → test → review → published → archived."""
    valid = {"draft", "test", "review", "published", "archived"}
    if new_status not in valid:
        raise HTTPException(400, f"new_status must be one of {sorted(valid)}")
    agent = db.get(models.Agent, agent_id)
    if not agent:
        raise HTTPException(404, "Agent not found")
    agent.status = new_status
    db.commit()
    db.refresh(agent)
    return agent
