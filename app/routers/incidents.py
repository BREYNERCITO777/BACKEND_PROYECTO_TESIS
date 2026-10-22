"""Historial de incidentes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_db
from app.core.security import require_roles
from app.repositories.incident_repository import IncidentRepository

router = APIRouter(prefix="/incidents", tags=["Incidents"])


@router.get("")
async def listar_incidentes(
    limit: int = 50,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _user=Depends(require_roles("admin", "operator")),
):
    """Incidentes más recientes primero."""
    return await IncidentRepository(db).list(limit=limit)


@router.delete("/{incident_id}")
async def borrar_incidente(
    incident_id: str,
    db: AsyncIOMotorDatabase = Depends(get_db),
    _user=Depends(require_roles("admin")),
):
    """Borra un incidente."""
    ok = await IncidentRepository(db).delete(incident_id)
    if not ok:
        raise HTTPException(404, "Incidente no encontrado")
    return {"deleted": True, "incident_id": incident_id}