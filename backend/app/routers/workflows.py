"""Workflows + tasks management."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/api/workflows", tags=["workflows"])


@router.get("", response_model=list[schemas.WorkflowOut])
def list_workflows(
    agent_id: int | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(models.Workflow)
    if agent_id is not None:
        q = q.filter(models.Workflow.agent_id == agent_id)
    return q.order_by(models.Workflow.updated_at.desc()).all()


@router.post("", response_model=schemas.WorkflowOut, status_code=status.HTTP_201_CREATED)
def create_workflow(payload: schemas.WorkflowCreate, db: Session = Depends(get_db)):
    if not db.get(models.Agent, payload.agent_id):
        raise HTTPException(404, "Agent not found")
    wf = models.Workflow(
        agent_id=payload.agent_id,
        name=payload.name,
        description=payload.description,
        status=payload.status,
    )
    db.add(wf)
    db.flush()
    for t in payload.tasks:
        db.add(models.Task(workflow_id=wf.id, **t.model_dump()))
    db.commit()
    db.refresh(wf)
    return wf


@router.get("/{workflow_id}", response_model=schemas.WorkflowOut)
def get_workflow(workflow_id: int, db: Session = Depends(get_db)):
    wf = db.get(models.Workflow, workflow_id)
    if not wf:
        raise HTTPException(404, "Workflow not found")
    return wf


@router.patch("/{workflow_id}", response_model=schemas.WorkflowOut)
def update_workflow(
    workflow_id: int,
    payload: schemas.WorkflowUpdate,
    db: Session = Depends(get_db),
):
    wf = db.get(models.Workflow, workflow_id)
    if not wf:
        raise HTTPException(404, "Workflow not found")
    data = payload.model_dump(exclude_unset=True)
    tasks = data.pop("tasks", None)
    for k, v in data.items():
        setattr(wf, k, v)
    if tasks is not None:
        # Replace tasks atomically
        for old in list(wf.tasks):
            db.delete(old)
        db.flush()
        for t in tasks:
            db.add(models.Task(workflow_id=wf.id, **t))
    db.commit()
    db.refresh(wf)
    return wf


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workflow(workflow_id: int, db: Session = Depends(get_db)):
    wf = db.get(models.Workflow, workflow_id)
    if not wf:
        raise HTTPException(404, "Workflow not found")
    db.delete(wf)
    db.commit()


@router.post("/{workflow_id}/tasks", response_model=schemas.TaskOut)
def add_task(
    workflow_id: int,
    payload: schemas.TaskCreate,
    db: Session = Depends(get_db),
):
    wf = db.get(models.Workflow, workflow_id)
    if not wf:
        raise HTTPException(404, "Workflow not found")
    task = models.Task(workflow_id=workflow_id, **payload.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.delete("/{workflow_id}/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(workflow_id: int, task_id: int, db: Session = Depends(get_db)):
    task = db.get(models.Task, task_id)
    if not task or task.workflow_id != workflow_id:
        raise HTTPException(404, "Task not found")
    db.delete(task)
    db.commit()
