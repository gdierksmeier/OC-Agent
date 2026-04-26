"""Model Registry — providers, parameters, costs, routing priorities."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/api/models", tags=["models"])


@router.get("", response_model=list[schemas.AIModelOut])
def list_models(
    provider: str | None = None,
    model_type: str | None = None,
    status_filter: str | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(models.AIModel)
    if provider:
        q = q.filter(models.AIModel.provider == provider)
    if model_type:
        q = q.filter(models.AIModel.model_type == model_type)
    if status_filter:
        q = q.filter(models.AIModel.status == status_filter)
    return q.order_by(models.AIModel.routing_priority.asc()).all()


@router.post("", response_model=schemas.AIModelOut, status_code=status.HTTP_201_CREATED)
def create_model(payload: schemas.AIModelCreate, db: Session = Depends(get_db)):
    m = models.AIModel(**payload.model_dump())
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


@router.get("/{model_id}", response_model=schemas.AIModelOut)
def get_model(model_id: int, db: Session = Depends(get_db)):
    m = db.get(models.AIModel, model_id)
    if not m:
        raise HTTPException(404, "Model not found")
    return m


@router.patch("/{model_id}", response_model=schemas.AIModelOut)
def update_model(
    model_id: int,
    payload: schemas.AIModelUpdate,
    db: Session = Depends(get_db),
):
    m = db.get(models.AIModel, model_id)
    if not m:
        raise HTTPException(404, "Model not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(m, k, v)
    db.commit()
    db.refresh(m)
    return m


@router.delete("/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_model(model_id: int, db: Session = Depends(get_db)):
    m = db.get(models.AIModel, model_id)
    if not m:
        raise HTTPException(404, "Model not found")
    db.delete(m)
    db.commit()
