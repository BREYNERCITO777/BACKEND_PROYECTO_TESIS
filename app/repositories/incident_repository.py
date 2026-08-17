from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.config import settings


def _oid(id_str: str) -> ObjectId:
    return ObjectId(id_str)


def _serialize(doc: Dict[str, Any]) -> Dict[str, Any]:
    doc["_id"] = str(doc["_id"])
    return doc


class IncidentRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.col = db[settings.INCIDENTS_COL]

    async def ensure_indexes(self) -> None:
        await self.col.create_index("timestamp")
        await self.col.create_index("camera_id")

    async def create(
        self,
        *,
        weapon_type: str,
        confidence: float,
        evidence_url: str | None = None,
        camera_id: str | None = None,
        camera_name: str | None = None,
        source: str | None = None,
        status: str = "new",
        timestamp: str | None = None,
        image_base64: str | None = None,
        evidence_type: str | None = None,
        camera_registered: bool | None = None,
    ) -> Dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        doc = {
            "weapon_type": weapon_type,
            # Alias legado: el frontend lee "type" en algunas vistas.
            "type": weapon_type,
            "confidence": float(confidence),
            "evidence_url": evidence_url,
            "camera_id": camera_id,
            "camera_name": camera_name,
            # None = no aplica (origen distinto al agente); False = el agente
            # reportó una cámara que no existe en la colección de cámaras.
            "camera_registered": camera_registered,
            "source": source,
            "status": status,
            "image_base64": image_base64,
            "evidence_type": evidence_type,
            "timestamp": timestamp or now,
            "created_at": now,
        }
        res = await self.col.insert_one(doc)
        doc["_id"] = res.inserted_id
        return _serialize(doc)

    async def list(self, limit: int = 50) -> List[Dict[str, Any]]:
        cursor = self.col.find({}).sort("timestamp", -1).limit(limit)
        docs = await cursor.to_list(length=limit)
        return [_serialize(d) for d in docs]

    async def get(self, incident_id: str) -> Optional[Dict[str, Any]]:
        try:
            d = await self.col.find_one({"_id": _oid(incident_id)})
            return _serialize(d) if d else None
        except Exception:
            return None

    async def delete(self, incident_id: str) -> bool:
        try:
            res = await self.col.delete_one({"_id": _oid(incident_id)})
            return res.deleted_count == 1
        except Exception:
            return False