from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field, field_validator

from app.core.database import get_db
from app.core.security import require_roles
from app.repositories.settings_repository import settings_repo

router = APIRouter(prefix="/settings", tags=["Settings"])


EMAIL_NOTIFICATIONS_DOC = (
    "NO IMPLEMENTADO: el valor se persiste pero el backend no envía correos. "
    "Reservado para una futura integración SMTP."
)


class SettingsOut(BaseModel):
    confidence_threshold: float  # 0.0 - 1.0
    auto_alert: bool
    email_notifications: bool = Field(description=EMAIL_NOTIFICATIONS_DOC)
    sound_alerts: bool
    save_evidence: bool
    max_fps: int
    infer_every_n_frames: int
    updated_at: Optional[str] = None


class SettingsPatch(BaseModel):
    confidence_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    auto_alert: Optional[bool] = None
    email_notifications: Optional[bool] = Field(default=None, description=EMAIL_NOTIFICATIONS_DOC)
    sound_alerts: Optional[bool] = None
    save_evidence: Optional[bool] = None
    max_fps: Optional[int] = Field(default=None, ge=1, le=120)
    infer_every_n_frames: Optional[int] = Field(default=None, ge=1, le=120)

    @field_validator("confidence_threshold")
    @classmethod
    def clamp_threshold(cls, v):
        if v is None:
            return v
        return max(0.0, min(1.0, float(v)))


# ✅ GET /settings -> admin y operator
@router.get("", response_model=SettingsOut)
async def get_settings(
    db: AsyncIOMotorDatabase = Depends(get_db),
    _user=Depends(require_roles("admin", "operator")),
):
    doc = await settings_repo.get_or_create(db)
    doc.pop("_id", None)
    return doc


# ✅ PATCH /settings -> SOLO admin
@router.patch("", response_model=SettingsOut)
async def patch_settings(
    payload: SettingsPatch,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _user=Depends(require_roles("admin")),
):
    patch = {k: v for k, v in payload.model_dump().items() if v is not None}
    doc = await settings_repo.patch(db, patch)
    doc.pop("_id", None)
    return doc