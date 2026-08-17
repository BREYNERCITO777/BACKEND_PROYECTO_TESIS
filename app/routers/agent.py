from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

from app.core.config import settings
from app.core.database import get_db
from app.core.ws_manager import ws_manager
from app.repositories.alert_repository import alert_repo
from app.repositories.incident_repository import IncidentRepository


router = APIRouter(prefix="/agent", tags=["Agent YOLO"])


class AgentDetectionIn(BaseModel):
    camera_id: str
    camera_name: str
    type: str
    confidence: float
    timestamp: Optional[str] = None
    source: str = "docker-local-agent"
    image_base64: Optional[str] = None


def validate_agent_token(authorization: Optional[str]):
    expected_token = settings.AGENT_TOKEN.strip()

    # Defensa en profundidad: lifecycle.py ya impide arrancar sin AGENT_TOKEN.
    if not expected_token:
        raise HTTPException(status_code=500, detail="AGENT_TOKEN no configurado en el servidor")

    if not authorization:
        raise HTTPException(status_code=401, detail="Falta token")

    if authorization != "Bearer {}".format(expected_token):
        raise HTTPException(status_code=401, detail="Token inválido")


@router.post("/detections")
async def receive_detection(
    payload: AgentDetectionIn,
    authorization: Optional[str] = Header(default=None),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    validate_agent_token(authorization)

    image_base64 = payload.image_base64
    evidence_type = "base64" if image_base64 else None

    incident = await IncidentRepository(db).create(
        weapon_type=payload.type,
        confidence=payload.confidence,
        camera_id=payload.camera_id,
        camera_name=payload.camera_name,
        source=payload.source,
        status="new",
        timestamp=payload.timestamp,
        image_base64=image_base64,
        evidence_type=evidence_type,
    )

    alert = await alert_repo.create(
        db,
        title="Arma detectada",
        message="Se detectó {} en {}".format(
            payload.type,
            payload.camera_name,
        ),
        severity="high",
        weapon_type=payload.type,
        confidence=payload.confidence,
        camera_id=payload.camera_id,
        camera_name=payload.camera_name,
        incident_id=incident["_id"],
        source=payload.source,
        read=False,
        image_base64=image_base64,
        evidence_type=evidence_type,
        timestamp=payload.timestamp,
    )

    await ws_manager.broadcast(
        {
            "event": "new_alert",
            "data": alert,
        }
    )

    return {
        "ok": True,
        "message": "Detección recibida correctamente",
        "incident_id": incident["_id"],
        "alert_id": alert["_id"],
        "evidence_url": None,
        "image_base64_saved": True if image_base64 else False,
        "websocket_broadcast": True,
    }
