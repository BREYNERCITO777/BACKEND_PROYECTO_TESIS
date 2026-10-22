"""Bandeja de alertas del operador."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import require_roles
from app.repositories.alert_repository import alert_repo

router = APIRouter(prefix="/alerts", tags=["alerts"])


class AlertCreate(BaseModel):
    title: str
    message: str
    severity: str = "medium"  # low | medium | high
    weapon_type: Optional[str] = None
    confidence: Optional[float] = None
    evidence_url: Optional[str] = None
    camera_id: Optional[str] = None


@router.get("", operation_id="alerts_list")
async def list_alerts(
    limit: int = 50,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _user=Depends(require_roles("admin", "operator")),  # ✅ operator puede ver
):
    """Alertas más recientes primero."""
    return await alert_repo.list(db, limit=limit)


@router.post("", operation_id="alerts_create")
async def create_alert(
    payload: AlertCreate,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _user=Depends(require_roles("admin")),  # ✅ operator NO crea
):
    """Crea una alerta manual."""
    return await alert_repo.create(
        db,
        title=payload.title,
        message=payload.message,
        severity=payload.severity,
        weapon_type=payload.weapon_type,
        confidence=payload.confidence,
        evidence_url=payload.evidence_url,
        camera_id=payload.camera_id,
        read=False,
    )


@router.get("/{alert_id}", operation_id="alerts_get")
async def get_alert(
    alert_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _user=Depends(require_roles("admin", "operator")),
):
    """Una alerta por id."""
    doc = await alert_repo.get(db, alert_id)
    if not doc:
        raise HTTPException(404, "Alerta no encontrada")
    return doc


@router.patch("/{alert_id}/read", operation_id="alerts_mark_read")
async def mark_read(
    alert_id: str,
    read: bool = True,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _user=Depends(require_roles("admin", "operator")),  # ✅ operator puede marcar leído si quieres
):
    """Marca una alerta como leída o no leída."""
    doc = await alert_repo.mark_read(db, alert_id, read=read)
    if not doc:
        raise HTTPException(404, "Alerta no encontrada")
    return doc


@router.delete("/{alert_id}", operation_id="alerts_delete")
async def delete_alert(
    alert_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _user=Depends(require_roles("admin")),  # ✅ solo admin borra
):
    """Borra una alerta."""
    ok = await alert_repo.delete(db, alert_id)
    if not ok:
        raise HTTPException(404, "Alerta no encontrada")
    return {"deleted": True, "alert_id": alert_id}