import os
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

from app.core.database import get_db


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
    expected_token = os.getenv("AGENT_TOKEN", "SentinelLocalAgent2026_MPSM")

    if not authorization:
        raise HTTPException(status_code=401, detail="Falta token")

    if authorization != f"Bearer {expected_token}":
        raise HTTPException(status_code=401, detail="Token inválido")


@router.post("/detections")
async def receive_detection(
    payload: AgentDetectionIn,
    authorization: Optional[str] = Header(default=None),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    validate_agent_token(authorization)

    created_at = datetime.utcnow()

    # Guardamos la imagen DIRECTAMENTE en MongoDB
    # Ya no dependemos de archivos /static/evidences
    image_base64 = payload.image_base64

    incident_doc = {
        "camera_id": payload.camera_id,
        "camera_name": payload.camera_name,
        "weapon_type": payload.type,
        "type": payload.type,
        "confidence": payload.confidence,
        "source": payload.source,
        "status": "new",
        "created_at": created_at,

        # Campos de evidencia
        "evidence_url": None,
        "image_base64": image_base64,
        "evidence_type": "base64" if image_base64 else None,
    }

    result = await db["incidents"].insert_one(incident_doc)

    alert_doc = {
        "title": "Arma detectada",
        "message": f"Se detectó {payload.type} en {payload.camera_name}",
        "severity": "high",
        "weapon_type": payload.type,
        "type": payload.type,
        "confidence": payload.confidence,
        "camera_id": payload.camera_id,
        "camera_name": payload.camera_name,
        "incident_id": str(result.inserted_id),
        "source": payload.source,
        "read": False,
        "created_at": created_at,

        # Campos de evidencia
        "evidence_url": None,
        "image_base64": image_base64,
        "evidence_type": "base64" if image_base64 else None,
    }

    alert_result = await db["alerts"].insert_one(alert_doc)

    return {
        "ok": True,
        "message": "Detección recibida correctamente",
        "incident_id": str(result.inserted_id),
        "alert_id": str(alert_result.inserted_id),
        "evidence_url": None,
        "image_base64_saved": True if image_base64 else False,
    }
