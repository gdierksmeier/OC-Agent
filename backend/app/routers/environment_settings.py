"""Environment settings registry for DEV/QA/PROD runtime configuration."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/api/environment-settings", tags=["environment-settings"])


def _mask_if_secret(setting: models.EnvironmentSetting) -> schemas.EnvironmentSettingOut:
    payload = {
        "id": setting.id,
        "environment": setting.environment,
        "key": setting.key,
        "value": "***MASKED***" if setting.is_secret else setting.value,
        "is_secret": setting.is_secret,
        "description": setting.description,
        "is_active": setting.is_active,
        "created_at": setting.created_at,
        "updated_at": setting.updated_at,
    }
    return schemas.EnvironmentSettingOut(**payload)


@router.get("", response_model=list[schemas.EnvironmentSettingOut])
def list_environment_settings(
    environment: str | None = None,
    key: str | None = None,
    is_active: bool | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(models.EnvironmentSetting)
    if environment:
        q = q.filter(models.EnvironmentSetting.environment == environment)
    if key:
        q = q.filter(models.EnvironmentSetting.key == key)
    if is_active is not None:
        q = q.filter(models.EnvironmentSetting.is_active == is_active)
    rows = q.order_by(models.EnvironmentSetting.environment.asc(), models.EnvironmentSetting.key.asc()).all()
    return [_mask_if_secret(row) for row in rows]


@router.post("", response_model=schemas.EnvironmentSettingOut, status_code=status.HTTP_201_CREATED)
def create_environment_setting(payload: schemas.EnvironmentSettingCreate, db: Session = Depends(get_db)):
    existing = (
        db.query(models.EnvironmentSetting)
        .filter(
            models.EnvironmentSetting.environment == payload.environment,
            models.EnvironmentSetting.key == payload.key,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Setting '{payload.key}' already exists for environment '{payload.environment}'",
        )

    row = models.EnvironmentSetting(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return _mask_if_secret(row)


@router.get("/{setting_id}", response_model=schemas.EnvironmentSettingOut)
def get_environment_setting(setting_id: int, db: Session = Depends(get_db)):
    row = db.get(models.EnvironmentSetting, setting_id)
    if not row:
        raise HTTPException(404, "Environment setting not found")
    return _mask_if_secret(row)


@router.patch("/{setting_id}", response_model=schemas.EnvironmentSettingOut)
def update_environment_setting(
    setting_id: int,
    payload: schemas.EnvironmentSettingUpdate,
    db: Session = Depends(get_db),
):
    row = db.get(models.EnvironmentSetting, setting_id)
    if not row:
        raise HTTPException(404, "Environment setting not found")

    updates = payload.model_dump(exclude_unset=True)
    new_environment = updates.get("environment", row.environment)
    new_key = updates.get("key", row.key)

    conflict = (
        db.query(models.EnvironmentSetting)
        .filter(
            models.EnvironmentSetting.id != setting_id,
            models.EnvironmentSetting.environment == new_environment,
            models.EnvironmentSetting.key == new_key,
        )
        .first()
    )
    if conflict:
        raise HTTPException(
            status_code=409,
            detail=f"Setting '{new_key}' already exists for environment '{new_environment}'",
        )

    for k, v in updates.items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return _mask_if_secret(row)


@router.delete("/{setting_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_environment_setting(setting_id: int, db: Session = Depends(get_db)):
    row = db.get(models.EnvironmentSetting, setting_id)
    if not row:
        raise HTTPException(404, "Environment setting not found")
    db.delete(row)
    db.commit()
