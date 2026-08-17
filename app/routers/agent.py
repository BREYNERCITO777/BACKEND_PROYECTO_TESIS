from __future__ import annotations

import base64
import binascii
import re
import time
from datetime import datetime
from typing import Any, Dict, Optional

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, Header, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field, field_validator

from app.core.config import settings
from app.core.database import get_db
from app.core.ws_manager import ws_manager
from app.repositories.alert_repository import alert_repo
from app.repositories.incident_repository import IncidentRepository
from app.repositories.settings_repository import settings_repo


router = APIRouter(prefix="/agent", tags=["Agent YOLO"])


# Marca de tiempo de la última detección aceptada, por cámara.
# Vive en memoria del proceso: alcanza para un uvicorn de un solo worker.
# Si algún día se despliega con varios workers, esto debe moverse a Mongo.
_ultima_deteccion: Dict[str, float] = {}

# Prefijo opcional que algunos clientes anteponen: "data:image/jpeg;base64,..."
_PREFIJO_DATA_URI = re.compile(r"^data:image/[a-zA-Z0-9.+-]+;base64,")


class AgentDetectionIn(BaseModel):
    camera_id: str = Field(min_length=1, max_length=100)
    camera_name: str = Field(min_length=1, max_length=200)
    type: str = Field(min_length=1, max_length=50)
    # La confianza es una probabilidad, no un porcentaje: el frontend la
    # multiplica por 100 para mostrarla.
    confidence: float = Field(ge=0.0, le=1.0)
    timestamp: Optional[str] = None
    source: str = Field(default="docker-local-agent", max_length=100)
    image_base64: Optional[str] = None

    @field_validator("timestamp")
    @classmethod
    def validar_timestamp(cls, v: Optional[str]) -> Optional[str]:
        if v is None or not v.strip():
            return None

        crudo = v.strip()
        # datetime.fromisoformat() de Python 3.9 no acepta el sufijo "Z".
        normalizado = crudo[:-1] + "+00:00" if crudo.endswith("Z") else crudo
        try:
            datetime.fromisoformat(normalizado)
        except ValueError:
            raise ValueError(
                "timestamp debe ser ISO 8601, por ejemplo 2026-08-17T12:00:00+00:00"
            )
        return crudo

    @field_validator("image_base64")
    @classmethod
    def validar_imagen(cls, v: Optional[str]) -> Optional[str]:
        if v is None or not v.strip():
            return None

        # Se valida sobre una copia limpia, pero se conserva el valor original
        # para no alterar lo que ya consume el frontend.
        limpio = _PREFIJO_DATA_URI.sub("", v.strip())
        limpio = "".join(limpio.split())

        try:
            crudo = base64.b64decode(limpio, validate=True)
        except (binascii.Error, ValueError):
            raise ValueError("image_base64 no es base64 válido")

        limite = int(settings.AGENT_MAX_EVIDENCE_MB * 1024 * 1024)
        if len(crudo) > limite:
            raise ValueError(
                "la evidencia pesa {:.1f} MB y el límite es {} MB".format(
                    len(crudo) / (1024 * 1024), settings.AGENT_MAX_EVIDENCE_MB
                )
            )
        return v


def validate_agent_token(authorization: Optional[str]) -> None:
    expected_token = settings.AGENT_TOKEN.strip()

    # Defensa en profundidad: lifecycle.py ya impide arrancar sin AGENT_TOKEN.
    if not expected_token:
        raise HTTPException(status_code=500, detail="AGENT_TOKEN no configurado en el servidor")

    if not authorization:
        raise HTTPException(status_code=401, detail="Falta token")

    if authorization != "Bearer {}".format(expected_token):
        raise HTTPException(status_code=401, detail="Token inválido")


async def _buscar_camara(
    db: AsyncIOMotorDatabase,
    camera_id: str,
    camera_name: str,
) -> Optional[Dict[str, Any]]:
    """
    Busca la cámara que reporta el agente.

    Primero por el ObjectId de Mongo, que es como el resto del sistema
    identifica cámaras. Como respaldo se intenta por nombre, porque el agente
    local puede estar usando un identificador propio (ej. "cam-001").
    """
    col = db[settings.CAMERAS_COL]

    try:
        doc = await col.find_one({"_id": ObjectId(camera_id)})
        if doc:
            return doc
    except (InvalidId, TypeError):
        pass

    return await col.find_one({"name": camera_name})


@router.post("/detections")
async def receive_detection(
    payload: AgentDetectionIn,
    authorization: Optional[str] = Header(default=None),
    db: AsyncIOMotorDatabase = Depends(get_db),
):
    validate_agent_token(authorization)

    # ------------------------------------------------------------------
    # 1) Umbral de confianza: sale de /settings, no de una constante.
    #    Mover el control en el panel cambia de verdad el comportamiento.
    # ------------------------------------------------------------------
    config = await settings_repo.get_or_create(db)
    umbral = float(config.get("confidence_threshold", settings.CONF_TH))

    if payload.confidence < umbral:
        return {
            "ok": True,
            "ignorada": True,
            "motivo": "confianza_bajo_umbral",
            "confidence": payload.confidence,
            "umbral": umbral,
            "message": "Detección descartada: confianza por debajo del umbral configurado",
        }

    # ------------------------------------------------------------------
    # 2) Anti-avalancha: una detección aceptada por cámara cada N segundos.
    # ------------------------------------------------------------------
    cooldown = float(settings.AGENT_COOLDOWN_SECONDS)
    ahora = time.monotonic()
    ultima = _ultima_deteccion.get(payload.camera_id)

    if cooldown > 0 and ultima is not None and (ahora - ultima) < cooldown:
        return {
            "ok": True,
            "ignorada": True,
            "motivo": "cooldown_activo",
            "segundos_restantes": round(cooldown - (ahora - ultima), 2),
            "message": "Detección descartada: esa cámara ya reportó hace menos de {}s".format(
                cooldown
            ),
        }

    _ultima_deteccion[payload.camera_id] = ahora

    # ------------------------------------------------------------------
    # 3) ¿La cámara existe en el sistema?
    #    No se rechaza la detección (perder una alerta real es peor que
    #    registrarla con datos incompletos), pero queda marcada.
    # ------------------------------------------------------------------
    camara = await _buscar_camara(db, payload.camera_id, payload.camera_name)
    camara_registrada = camara is not None
    camera_id_final = str(camara["_id"]) if camara_registrada else payload.camera_id

    image_base64 = payload.image_base64
    evidence_type = "base64" if image_base64 else None

    incident = await IncidentRepository(db).create(
        weapon_type=payload.type,
        confidence=payload.confidence,
        camera_id=camera_id_final,
        camera_name=payload.camera_name,
        source=payload.source,
        status="new",
        timestamp=payload.timestamp,
        image_base64=image_base64,
        evidence_type=evidence_type,
        camera_registered=camara_registrada,
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
        camera_id=camera_id_final,
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
        "ignorada": False,
        "message": "Detección recibida correctamente",
        "incident_id": incident["_id"],
        "alert_id": alert["_id"],
        "camera_registered": camara_registrada,
        "umbral_aplicado": umbral,
        "evidence_url": None,
        "image_base64_saved": True if image_base64 else False,
        "websocket_broadcast": True,
    }
