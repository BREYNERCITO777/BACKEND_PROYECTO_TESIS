from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel

from app.core.database import get_db
from app.core.ws_manager import ws_manager


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

    if authorization != "Bearer {}".format(expected_token):
        raise HTTPException(status_code=401, detail="Token inválido")


@router.post("/detections")
async def receive_detection(
    payload: AgentDetectionIn,
    authorization: Optional[str] = Header(default=None),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    validate_agent_token(authorization)

    created_at = datetime.now(timezone.utc).isoformat()

    image_base64 = payload.image_base64

    incident_doc = {
        "camera_id": payload.camera_id,
        "camera_name": payload.camera_name,
        "weapon_type": payload.type,
        "type": payload.type,
        "confidence": payload.confidence,
        "source": payload.source,
        "status": "new",
        "timestamp": payload.timestamp,
        "created_at": created_at,
        "evidence_url": None,
        "image_base64": image_base64,
        "evidence_type": "base64" if image_base64 else None,
    }

    incident_result = await db["incidents"].insert_one(incident_doc)

    alert_doc = {
        "type": payload.type,
        "title": "Arma detectada",
        "message": "Se detectó {} en {}".format(
            payload.type,
            payload.camera_name,
        ),
        "severity": "high",
        "weapon_type": payload.type,
        "confidence": payload.confidence,
        "camera_id": payload.camera_id,
        "camera_name": payload.camera_name,
        "incident_id": str(incident_result.inserted_id),
        "source": payload.source,
        "read": False,
        "timestamp": payload.timestamp,
        "created_at": created_at,
        "evidence_url": None,
        "image_base64": image_base64,
        "evidence_type": "base64" if image_base64 else None,
    }

    alert_result = await db["alerts"].insert_one(alert_doc)

    alert_payload = {
        "_id": str(alert_result.inserted_id),
        "type": alert_doc.get("type"),
        "title": alert_doc.get("title"),
        "message": alert_doc.get("message"),
        "severity": alert_doc.get("severity"),
        "weapon_type": alert_doc.get("weapon_type"),
        "confidence": alert_doc.get("confidence"),
        "camera_id": alert_doc.get("camera_id"),
        "camera_name": alert_doc.get("camera_name"),
        "incident_id": alert_doc.get("incident_id"),
        "source": alert_doc.get("source"),
        "read": alert_doc.get("read", False),
        "timestamp": alert_doc.get("timestamp"),
        "created_at": alert_doc.get("created_at"),
        "evidence_url": alert_doc.get("evidence_url"),
        "image_base64": alert_doc.get("image_base64"),
        "evidence_type": alert_doc.get("evidence_type"),
    }

    await ws_manager.broadcast(
        {
            "event": "new_alert",
            "data": alert_payload,
        }
    )

    return {
        "ok": True,
        "message": "Detección recibida correctamente",
        "incident_id": str(incident_result.inserted_id),
        "alert_id": str(alert_result.inserted_id),
        "evidence_url": None,
        "image_base64_saved": True if image_base64 else False,
        "websocket_broadcast": True,
    }
