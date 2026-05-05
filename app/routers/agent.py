import base64
import os
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

from app.core.database import get_db


router = APIRouter(prefix="/agent", tags=["Agent YOLO"])


# 📥 Modelo de entrada desde Docker YOLO
class AgentDetectionIn(BaseModel):
    camera_id: str
    camera_name: str
    type: str  # arma_fuego / arma_blanca
    confidence: float
    timestamp: Optional[str] = None
    source: str = "docker-local-agent"
    image_base64: Optional[str] = None


# 🔐 Validación de token del agente
def validate_agent_token(authorization: Optional[str]):
    expected_token = os.getenv("AGENT_TOKEN", "SentinelLocalAgent2026_MPSM")

    if not authorization:
        raise HTTPException(status_code=401, detail="Falta token")

    if authorization != f"Bearer {expected_token}":
        raise HTTPException(status_code=401, detail="Token inválido")


# 🚨 Endpoint principal
@router.post("/detections")
async def receive_detection(
    payload: AgentDetectionIn,
    authorization: Optional[str] = Header(default=None),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    validate_agent_token(authorization)

    evidence_url = None

    # 📸 Guardar imagen si viene en base64
    if payload.image_base64:
        os.makedirs("static/evidences", exist_ok=True)

        filename = f"{uuid.uuid4()}.jpg"
        filepath = os.path.join("static", "evidences", filename)

        image_bytes = base64.b64decode(payload.image_base64)

        with open(filepath, "wb") as f:
            f.write(image_bytes)

        evidence_url = f"/static/evidences/{filename}"

    # 🧾 Crear incidente
    incident_doc = {
        "camera_id": payload.camera_id,
        "camera_name": payload.camera_name,
        "weapon_type": payload.type,
        "confidence": payload.confidence,
        "source": payload.source,
        "evidence_url": evidence_url,
        "status": "new",
        "created_at": datetime.utcnow(),
    }

    result = await db["incidents"].insert_one(incident_doc)

    # 🔔 Crear alerta
    alert_doc = {
        "title": "Arma detectada",
        "message": f"Se detectó {payload.type} en {payload.camera_name}",
        "severity": "high",
        "weapon_type": payload.type,
        "confidence": payload.confidence,
        "camera_id": payload.camera_id,
        "camera_name": payload.camera_name,
        "incident_id": str(result.inserted_id),
        "evidence_url": evidence_url,
        "read": False,
        "created_at": datetime.utcnow(),
    }

    alert_result = await db["alerts"].insert_one(alert_doc)

    return {
        "ok": True,
        "message": "Detección recibida correctamente",
        "incident_id": str(result.inserted_id),
        "alert_id": str(alert_result.inserted_id),
        "evidence_url": evidence_url,
    }
