"""Prompt Library — reusable templates with versions and variables."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/api/prompts", tags=["prompts"])


@router.get("", response_model=list[schemas.PromptOut])
def list_prompts(
    category: str | None = None,
    status_filter: str | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(models.Prompt)
    if category:
        q = q.filter(models.Prompt.category == category)
    if status_filter:
        q = q.filter(models.Prompt.status == status_filter)
    return q.order_by(models.Prompt.updated_at.desc()).all()


@router.post("", response_model=schemas.PromptOut, status_code=status.HTTP_201_CREATED)
def create_prompt(payload: schemas.PromptCreate, db: Session = Depends(get_db)):
    p = models.Prompt(**payload.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


@router.get("/{prompt_id}", response_model=schemas.PromptOut)
def get_prompt(prompt_id: int, db: Session = Depends(get_db)):
    p = db.get(models.Prompt, prompt_id)
    if not p:
        raise HTTPException(404, "Prompt not found")
    return p


@router.patch("/{prompt_id}", response_model=schemas.PromptOut)
def update_prompt(
    prompt_id: int,
    payload: schemas.PromptUpdate,
    db: Session = Depends(get_db),
):
    p = db.get(models.Prompt, prompt_id)
    if not p:
        raise HTTPException(404, "Prompt not found")
    data = payload.model_dump(exclude_unset=True)
    if "template" in data and data["template"] != p.template:
        p.version = (p.version or 1) + 1
    for k, v in data.items():
        setattr(p, k, v)
    db.commit()
    db.refresh(p)
    return p


@router.delete("/{prompt_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_prompt(prompt_id: int, db: Session = Depends(get_db)):
    p = db.get(models.Prompt, prompt_id)
    if not p:
        raise HTTPException(404, "Prompt not found")
    db.delete(p)
    db.commit()
